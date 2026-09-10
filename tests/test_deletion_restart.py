from __future__ import annotations

from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from kivi.enums import LifecycleStatus, PurgeStatus, QueryStatus
from kivi.models import Memory, Project, Take, Tombstone
from kivi.schemas import AskRequest, TakeCreate
from kivi.services.deletion import delete_take
from kivi.services.indexing import rebuild_memory_fts
from kivi.services.ingestion import ingest_take
from kivi.services.retrieval import ask

from conftest import FakeAnswerer, FakeEmbedder, FakeExtractor


def _migrate(database_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def test_deleted_take_stays_excluded_after_restart_and_index_rebuild(tmp_path):
    database_path = tmp_path / "restart.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    _migrate(database_url)
    engine = create_engine(database_url)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    content = "Project Harbor's release is Thursday at 4 PM."
    with sessions() as session:
        session.add(Project(id="project-harbor", name="Project Harbor", aliases=["Harbor"]))
        session.commit()
        result = ingest_take(session, TakeCreate(take_id="take_restart_delete", project_id="project-harbor", raw_asr=content.lower(), formatted_text=content, source_application="Notepad", event_ts=datetime.now(timezone.utc), metadata={}), FakeExtractor(), FakeEmbedder())
        memory_id = result.memories[0].id
        deletion = delete_take(session, "take_restart_delete")
        assert deletion.tombstone.purge_status == PurgeStatus.PURGED
    engine.dispose()

    reopened_engine = create_engine(database_url)
    reopened_sessions = sessionmaker(bind=reopened_engine, expire_on_commit=False)
    with reopened_sessions.begin() as session:
        assert rebuild_memory_fts(session) == 0
    with reopened_sessions() as session:
        take = session.get(Take, "take_restart_delete")
        tombstone = session.get(Tombstone, "take_restart_delete")
        memory = session.get(Memory, memory_id)
        assert take is not None and take.is_deleted
        assert take.raw_asr is take.formatted_text is take.embedding is None
        assert tombstone is not None and tombstone.purge_status == PurgeStatus.PURGED and tombstone.verified_at is not None
        assert memory is not None and memory.lifecycle_status == LifecycleStatus.INVALIDATED
        assert session.scalar(text("SELECT count(*) FROM memory_fts")) == 0
        response = ask(session, AskRequest(project_id="project-harbor", question="When is the Harbor release?"), FakeEmbedder(), FakeAnswerer())
        assert response.status == QueryStatus.NO_EVIDENCE
        assert response.supporting_take_ids == []
        assert session.scalar(select(Take.formatted_text).where(Take.id == "take_restart_delete")) is None
    reopened_engine.dispose()
