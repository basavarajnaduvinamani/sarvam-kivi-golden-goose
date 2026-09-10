from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import get_session
from .models import Project
from .providers import Embedder, GroundedAnswerer, MemoryExtractor, ProviderUnavailable
from .schemas import AskRequest, AskResponse, ProjectCreate, ProjectRead, TakeCreate, TakeIngestResult
from .services.ingestion import IngestionError, ingest_take
from .services.retrieval import ask


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


def create_app(
    providers: ProviderBundle | None = None,
    session_dependency: Any = get_session,
) -> FastAPI:
    bundle = providers or ProviderBundle(
        extractor=UnavailableProvider(),
        embedder=UnavailableProvider(),
        answerer=UnavailableProvider(),
    )
    app = FastAPI(title="Kivi Semantic Memory", version="0.1.0")

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

    @app.post("/takes", response_model=TakeIngestResult, status_code=status.HTTP_201_CREATED)
    def create_take(payload: TakeCreate, session: Session = Depends(session_dependency)) -> TakeIngestResult:
        try:
            return ingest_take(session, payload, bundle.extractor, bundle.embedder)
        except IngestionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ProviderUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/ask", response_model=AskResponse)
    def ask_kivi(payload: AskRequest, session: Session = Depends(session_dependency)) -> AskResponse:
        try:
            return ask(session, payload, bundle.embedder, bundle.answerer)
        except ProviderUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=f"grounding validation failed: {exc}") from exc

    return app


app = create_app()

