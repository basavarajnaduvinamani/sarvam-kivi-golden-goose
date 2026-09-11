from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .db import get_session
from .enums import LifecycleStatus
from .models import Memory, Project, Take
from .openai_provider import OpenAIProvider
from .providers import Embedder, GroundedAnswerer, MemoryExtractor, ProviderUnavailable
from .schemas import (
    AskRequest,
    AskResponse,
    BriefingRequest,
    CorpusImportResult,
    DeleteResult,
    EvaluationCaseResultRead,
    EvaluationRunRead,
    EvaluationRunRequest,
    ProjectCreate,
    ProjectRead,
    ProjectTimelineResponse,
    TakeCreate,
    TakeIngestResult,
    TakeRead,
    TombstoneRead,
)
from .presenters import present_memory
from .schemas import MemoryRead
from .services.deletion import DeletionError, delete_take, get_tombstone
from .services.corpus_import import import_takes
from .services.ingestion import IngestionError, ingest_take
from .services.retrieval import ask
from .services.timeline import TimelineError, get_project_timeline
from .settings import get_settings


class UnavailableProvider:
    def _raise(self):
        raise ProviderUnavailable("model provider is not configured")

    def extract(self, *_args, **_kwargs):
        self._raise()

    def embed(self, *_args, **_kwargs):
        self._raise()

    def answer(self, *_args, **_kwargs):
        self._raise()


@dataclass(frozen=True)
class ProviderBundle:
    extractor: MemoryExtractor
    embedder: Embedder
    answerer: GroundedAnswerer


def default_provider_bundle() -> ProviderBundle:
    settings = get_settings()
    if settings.model_provider != "openai" or not settings.openai_api_key:
        unavailable = UnavailableProvider()
        return ProviderBundle(extractor=unavailable, embedder=unavailable, answerer=unavailable)
    provider = OpenAIProvider(settings)
    return ProviderBundle(extractor=provider, embedder=provider, answerer=provider)


def create_app(
    providers: ProviderBundle | None = None,
    session_dependency: Any = get_session,
) -> FastAPI:
    bundle = providers or default_provider_bundle()
    app = FastAPI(title="Kivi Semantic Memory", version="0.1.0")
    app.state.bundle = bundle

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
    def create_project(payload: ProjectCreate, session: Session = Depends(session_dependency)) -> Project:
        project = Project(id=payload.id, name=payload.name, aliases=payload.aliases)
        session.add(project)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail="project ID or name already exists") from exc
        session.refresh(project)
        return project

    @app.get("/projects", response_model=list[ProjectRead])
    def list_projects(session: Session = Depends(session_dependency)) -> list[Project]:
        return list(session.scalars(select(Project).order_by(Project.name)))

    @app.get("/projects/{project_id}/timeline", response_model=ProjectTimelineResponse)
    def project_timeline(project_id: str, session: Session = Depends(session_dependency)) -> ProjectTimelineResponse:
        try:
            return get_project_timeline(session, project_id)
        except TimelineError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/takes", response_model=TakeIngestResult, status_code=status.HTTP_201_CREATED)
    def create_take(payload: TakeCreate, session: Session = Depends(session_dependency)) -> TakeIngestResult:
        try:
            return ingest_take(session, payload, bundle.extractor, bundle.embedder)
        except IngestionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ProviderUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/takes/import", response_model=CorpusImportResult)
    def import_corpus(records: list[TakeCreate], session: Session = Depends(session_dependency)) -> CorpusImportResult:
        return import_takes(session, records, bundle.extractor, bundle.embedder)

    @app.get("/takes", response_model=list[TakeRead])
    def list_takes(
        project_id: str | None = None,
        include_deleted: bool = False,
        session: Session = Depends(session_dependency),
    ) -> list[Take]:
        statement = select(Take).order_by(Take.event_ts.desc())
        if project_id is not None:
            statement = statement.where(Take.project_id == project_id)
        if not include_deleted:
            statement = statement.where(Take.is_deleted.is_(False))
        return list(session.scalars(statement))

    @app.get("/takes/{take_id}", response_model=TakeRead)
    def get_take(take_id: str, session: Session = Depends(session_dependency)) -> Take:
        take = session.get(Take, take_id)
        if take is None:
            raise HTTPException(status_code=404, detail="take not found")
        return take

    @app.get("/memories", response_model=list[MemoryRead])
    def list_memories(
        project_id: str | None = None,
        lifecycle_status: LifecycleStatus | None = None,
        session: Session = Depends(session_dependency),
    ) -> list[MemoryRead]:
        statement = select(Memory).options(selectinload(Memory.evidence_links)).order_by(Memory.created_at.desc())
        if project_id is not None:
            statement = statement.where(Memory.project_id == project_id)
        if lifecycle_status is not None:
            statement = statement.where(Memory.lifecycle_status == lifecycle_status)
        return [present_memory(memory) for memory in session.scalars(statement)]

    @app.get("/memories/{memory_id}", response_model=MemoryRead)
    def get_memory(memory_id: str, session: Session = Depends(session_dependency)) -> MemoryRead:
        memory = session.scalar(
            select(Memory)
            .where(Memory.id == memory_id)
            .options(selectinload(Memory.evidence_links))
        )
        if memory is None:
            raise HTTPException(status_code=404, detail="memory not found")
        return present_memory(memory)

    @app.post("/ask", response_model=AskResponse)
    def ask_kivi(payload: AskRequest, session: Session = Depends(session_dependency)) -> AskResponse:
        try:
            return ask(session, payload, bundle.embedder, bundle.answerer)
        except ProviderUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=f"grounding validation failed: {exc}") from exc

    @app.post("/briefings", response_model=AskResponse)
    def create_briefing(payload: BriefingRequest, session: Session = Depends(session_dependency)) -> AskResponse:
        return ask(
            session,
            AskRequest(project_id=payload.project_id, question=payload.focus),
            bundle.embedder,
            bundle.answerer,
        )

    @app.post("/evaluate/run", response_model=EvaluationRunRead)
    def evaluate(payload: EvaluationRunRequest) -> EvaluationRunRead:
        from .evaluation import run_evaluation

        try:
            return run_evaluation(payload.mode)
        except (RuntimeError, ProviderUnavailable) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/evaluate/latest", response_model=EvaluationRunRead)
    def latest_evaluation() -> EvaluationRunRead:
        from .evaluation import get_latest_run

        try:
            return get_latest_run()
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/evaluate/cases/{case_id}", response_model=EvaluationCaseResultRead)
    def evaluation_case(case_id: str) -> EvaluationCaseResultRead:
        from .evaluation import get_case_result

        try:
            return get_case_result(case_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="evaluation case not found") from exc

    @app.delete("/takes/{take_id}", response_model=DeleteResult)
    def remove_take(take_id: str, session: Session = Depends(session_dependency)) -> DeleteResult:
        try:
            return delete_take(session, take_id)
        except DeletionError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/deletions/{take_id}", response_model=TombstoneRead)
    def deletion_status(take_id: str, session: Session = Depends(session_dependency)) -> TombstoneRead:
        try:
            return get_tombstone(session, take_id)
        except DeletionError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()

