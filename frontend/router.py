from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from backend.kivi.schemas import AskRequest
from backend.kivi.app import default_provider_bundle
from backend.kivi.db import get_session
from sqlalchemy.orm import Session
from backend.kivi.services.retrieval import ask

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")
bundle = default_provider_bundle()

@router.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

from fastapi import Form

@router.post("/htmx/ask")
def htmx_ask(
    request: Request,
    project_id: str = Form(None),
    question: str = Form(...),
    session: Session = Depends(get_session)
):
    # This is a handler specifically for HTMX form submission
    # It will parse the form data, call the backend logic directly (since we're in the same process),
    # and return an HTML fragment for the response.
    
    payload = AskRequest(project_id=project_id if project_id else None, question=question)
    try:
        # We can call the backend ask function directly
        response = ask(session, payload, bundle.embedder, bundle.answerer)
        return templates.TemplateResponse("components/ask_result.html", {"request": request, "response": response})
    except Exception as e:
        # In a real scenario, handle ProviderUnavailable, ValueError etc.
        return templates.TemplateResponse("components/ask_result.html", {"request": request, "error": str(e)})

@router.get("/htmx/takes/{take_id}")
def htmx_get_take(take_id: str, request: Request, session: Session = Depends(get_session)):
    from backend.kivi.models import Take
    take = session.get(Take, take_id)
    return templates.TemplateResponse("components/evidence_drawer.html", {"request": request, "take": take})
