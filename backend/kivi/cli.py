from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import delete, func, select

from .app import default_provider_bundle
from .db import SessionLocal
from .models import Memory, MemoryEvidence, Project, QueryClaim, QueryRun, Take, Tombstone
from .schemas import ProjectCreate, TakeCreate
from .services.corpus_import import import_takes
from .services.indexing import rebuild_memory_fts
from .settings import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kivi", description="Reviewer operations for Kivi semantic memory")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="start the local Kivi application")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    database = commands.add_parser("db", help="database lifecycle operations")
    database_commands = database.add_subparsers(dest="db_command", required=True)
    database_commands.add_parser("migrate", help="upgrade the configured database to the latest revision")
    reset = database_commands.add_parser("reset", help="remove local data and re-run migrations")
    reset.add_argument("--yes", action="store_true", help="confirm destructive local reset")
    database_commands.add_parser("rebuild-index", help="rebuild FTS from active, sufficiently evidenced memories")

    projects = commands.add_parser("projects", help="project registry operations")
    project_commands = projects.add_subparsers(dest="project_command", required=True)
    import_projects = project_commands.add_parser("import", help="import projects from a JSON array")
    import_projects.add_argument("path", type=Path)

    corpus = commands.add_parser("corpus", help="corpus validation and import")
    corpus_commands = corpus.add_subparsers(dest="corpus_command", required=True)
    validate = corpus_commands.add_parser("validate", help="validate a JSONL corpus without changing the database")
    validate.add_argument("path", type=Path)
    validate.add_argument("--expected-count", type=int, default=500)
    import_corpus_parser = corpus_commands.add_parser("import", help="validate and ingest a JSONL corpus")
    import_corpus_parser.add_argument("path", type=Path)
    import_corpus_parser.add_argument("--projects", type=Path)
    import_corpus_parser.add_argument("--expected-count", type=int, default=500)

    inspect = commands.add_parser("inspect", help="print reviewer-visible database counts as JSON")
    inspect.add_argument("--project-id")
    return parser


def _alembic_config() -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
    return config


def migrate_database() -> None:
    command.upgrade(_alembic_config(), "head")


def reset_database(*, confirmed: bool) -> None:
    if not confirmed:
        raise SystemExit("refusing to reset local data without --yes")
    migrate_database()
    with SessionLocal.begin() as session:
        for model in (QueryClaim, QueryRun, MemoryEvidence, Tombstone, Memory, Take, Project):
            session.execute(delete(model))
    rebuild_index()


def rebuild_index() -> int:
    with SessionLocal.begin() as session:
        return rebuild_memory_fts(session)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"could not read valid JSON from {path}: {exc}") from exc


def import_project_registry(path: Path) -> int:
    raw = _read_json(path)
    if not isinstance(raw, list):
        raise SystemExit("project registry must be a JSON array")
    try:
        projects = [ProjectCreate.model_validate(item) for item in raw]
    except ValidationError as exc:
        raise SystemExit(f"project registry validation failed: {exc}") from exc
    if len({project.id for project in projects}) != len(projects):
        raise SystemExit("project registry contains duplicate IDs")
    with SessionLocal.begin() as session:
        existing_ids = set(session.scalars(select(Project.id).where(Project.id.in_([item.id for item in projects]))))
        for payload in projects:
            if payload.id not in existing_ids:
                session.add(Project(id=payload.id, name=payload.name, aliases=payload.aliases))
    return len(projects)


def load_corpus(path: Path, expected_count: int) -> list[TakeCreate]:
    if expected_count < 1:
        raise SystemExit("expected count must be positive")
    records: list[TakeCreate] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    records.append(TakeCreate.model_validate_json(line))
                except ValidationError as exc:
                    raise SystemExit(f"corpus validation failed at line {line_number}: {exc}") from exc
    except OSError as exc:
        raise SystemExit(f"could not read corpus {path}: {exc}") from exc
    if len(records) != expected_count:
        raise SystemExit(f"expected {expected_count} records, found {len(records)}")
    if len({record.take_id for record in records}) != len(records):
        raise SystemExit("corpus contains duplicate take IDs")
    return records


def import_corpus(path: Path, expected_count: int) -> dict[str, Any]:
    records = load_corpus(path, expected_count)
    providers = default_provider_bundle()
    with SessionLocal() as session:
        return import_takes(session, records, providers.extractor, providers.embedder).model_dump(mode="json")


def inspect_database(project_id: str | None = None) -> dict[str, Any]:
    with SessionLocal() as session:
        take_filter = Take.project_id == project_id if project_id else True
        memory_filter = Memory.project_id == project_id if project_id else True
        query_statement = (
            select(func.count()).select_from(QueryRun).where(QueryRun.project_id == project_id)
            if project_id
            else select(func.count()).select_from(QueryRun)
        )
        return {
            "project_id": project_id,
            "projects": session.scalar(select(func.count()).select_from(Project)),
            "takes": session.scalar(select(func.count()).select_from(Take).where(take_filter)),
            "deleted_takes": session.scalar(select(func.count()).select_from(Take).where(take_filter, Take.is_deleted.is_(True))),
            "memories": session.scalar(select(func.count()).select_from(Memory).where(memory_filter)),
            "active_memories": session.scalar(select(func.count()).select_from(Memory).where(memory_filter, Memory.lifecycle_status == "ACTIVE")),
            "query_runs": session.scalar(query_statement),
        }


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "serve":
        import uvicorn

        uvicorn.run("kivi.main:app", host=args.host, port=args.port)
    elif args.command == "db":
        if args.db_command == "migrate":
            migrate_database()
            print("database migrated to head")
        elif args.db_command == "reset":
            reset_database(confirmed=args.yes)
            print("database reset and migrated")
        else:
            print(json.dumps({"indexed_memories": rebuild_index()}))
    elif args.command == "projects":
        print(json.dumps({"validated_projects": import_project_registry(args.path)}))
    elif args.command == "corpus":
        if args.corpus_command == "validate":
            print(json.dumps({"validated_records": len(load_corpus(args.path, args.expected_count))}))
        else:
            if args.projects:
                import_project_registry(args.projects)
            print(json.dumps(import_corpus(args.path, args.expected_count), ensure_ascii=False))
    else:
        print(json.dumps(inspect_database(args.project_id), ensure_ascii=False))


if __name__ == "__main__":
    main()

