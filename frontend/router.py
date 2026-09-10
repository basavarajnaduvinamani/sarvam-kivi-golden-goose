from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from backend.kivi.schemas import AskRequest
from backend.kivi.app import default_provider_bundle
from backend.kivi.db import get_session
from sqlalchemy.orm import Session
from backend.kivi.services.retrieval import ask

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

@router.get("/")
def index(request: Request, session: Session = Depends(get_session)):
    from backend.kivi.models import Project
    from sqlalchemy import select
    projects = list(session.scalars(select(Project).order_by(Project.name)))
    return templates.TemplateResponse(request=request, name="index.html", context={"projects": projects})

from fastapi import Form

@router.post("/htmx/ask")
def htmx_ask(
    request: Request,
    project_id: str = Form(None),
    question: str = Form(...),
    session: Session = Depends(get_session)
):
    # This is a handler specifically for HTMX form submission
    bundle = request.app.state.bundle
    payload = AskRequest(project_id=project_id if project_id else None, question=question)
    try:
        # We can call the backend ask function directly
        response = ask(session, payload, bundle.embedder, bundle.answerer)
        return templates.TemplateResponse(request=request, name="components/ask_result.html", context={"response": response, "question": question})
    except Exception as e:
        import logging
        logging.exception("Error during /htmx/ask")
        # In a real scenario, handle ProviderUnavailable, ValueError etc. safely without leaking internals.
        return templates.TemplateResponse(request=request, name="components/ask_result.html", context={"error": "An internal service error occurred. Check server logs.", "question": question})

@router.get("/htmx/takes/{take_id}")
def htmx_get_take(take_id: str, request: Request, session: Session = Depends(get_session)):
    from backend.kivi.models import Take
    take = session.get(Take, take_id)
    return templates.TemplateResponse(request=request, name="components/evidence_drawer.html", context={"take": take})
