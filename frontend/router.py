from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from backend.kivi.schemas import AskRequest, TakeCreate
from backend.kivi.app import default_provider_bundle
from backend.kivi.db import get_session
from sqlalchemy.orm import Session
from backend.kivi.services.retrieval import ask
from backend.kivi.services.timeline import get_project_timeline
from backend.kivi.services.corpus_import import import_takes
from backend.kivi.services.deletion import delete_take
import json

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

@router.get("/")
def index(request: Request, session: Session = Depends(get_session)):
    from backend.kivi.models import Project
    from sqlalchemy import select
    projects = list(session.scalars(select(Project).order_by(Project.name)))
    return templates.TemplateResponse(request=request, name="index.html", context={"projects": projects})

@router.post("/htmx/ask")
def htmx_ask(
    request: Request,
    project_id: str = Form(None),
    question: str = Form(...),
    session: Session = Depends(get_session)
):
    bundle = request.app.state.bundle
    payload = AskRequest(project_id=project_id if project_id else None, question=question)
    try:
        response = ask(session, payload, bundle.embedder, bundle.answerer)
        return templates.TemplateResponse(request=request, name="components/ask_result.html", context={"response": response, "question": question})
    except Exception as e:
        import logging
        logging.exception("Error during /htmx/ask")
        return templates.TemplateResponse(request=request, name="components/ask_result.html", context={"error": "An internal service error occurred. Check server logs.", "question": question})

@router.get("/htmx/takes/{take_id}")
def htmx_get_take(take_id: str, request: Request, session: Session = Depends(get_session)):
    from backend.kivi.models import Take
    take = session.get(Take, take_id)
    return templates.TemplateResponse(request=request, name="components/evidence_drawer.html", context={"take": take})

@router.get("/timeline")
def timeline_index(request: Request, session: Session = Depends(get_session)):
    from backend.kivi.models import Project
    from sqlalchemy import select
    projects = list(session.scalars(select(Project).order_by(Project.name)))
    return templates.TemplateResponse(request=request, name="timeline.html", context={"projects": projects})

@router.get("/htmx/timeline/{project_id}")
def htmx_timeline(project_id: str, request: Request, session: Session = Depends(get_session)):
    try:
        response = get_project_timeline(session, project_id)
        return templates.TemplateResponse(request=request, name="components/timeline_view.html", context={"timeline": response})
    except Exception as e:
        return templates.TemplateResponse(request=request, name="components/timeline_view.html", context={"error": str(e)})

@router.get("/import-eval")
def import_eval_index(request: Request):
    return templates.TemplateResponse(request=request, name="import_eval.html")

@router.post("/htmx/import")
async def htmx_import_corpus(request: Request, corpus_file: UploadFile = File(...), session: Session = Depends(get_session)):
    content = await corpus_file.read()
    try:
        data = json.loads(content)
        records = [TakeCreate(**record) for record in data]
    except Exception as e:
        return templates.TemplateResponse(request=request, name="components/import_result.html", context={"error": f"Invalid JSON array: {e}"})

    bundle = request.app.state.bundle
    try:
        result = import_takes(session, records, bundle.extractor, bundle.embedder)
        return templates.TemplateResponse(request=request, name="components/import_result.html", context={"result": result})
    except Exception as e:
        return templates.TemplateResponse(request=request, name="components/import_result.html", context={"error": str(e)})

@router.get("/htmx/evaluate/latest")
def htmx_evaluate_latest(request: Request):
    from backend.kivi.evaluation import get_latest_run
    try:
        run = get_latest_run()
        return templates.TemplateResponse(request=request, name="components/eval_result.html", context={"run": run})
    except Exception as e:
        return templates.TemplateResponse(request=request, name="components/eval_result.html", context={"run": None, "error": str(e)})

@router.post("/htmx/evaluate/run")
def htmx_evaluate_run(request: Request, mode: str = Form("deterministic")):
    from backend.kivi.evaluation import run_evaluation
    try:
        run = run_evaluation(mode=mode)
        return templates.TemplateResponse(request=request, name="components/eval_result.html", context={"run": run})
    except Exception as e:
        return templates.TemplateResponse(request=request, name="components/eval_result.html", context={"run": None, "error": str(e)})

@router.get("/htmx/evaluate/cases/{case_id}")
def htmx_evaluate_case(case_id: str, request: Request):
    from backend.kivi.evaluation import get_case_result
    try:
        case = get_case_result(case_id)
        return templates.TemplateResponse(request=request, name="components/eval_case.html", context={"case": case})
    except Exception as e:
        return templates.TemplateResponse(request=request, name="components/eval_case.html", context={"case": None, "error": str(e)})

@router.delete("/htmx/takes/{take_id}")
def htmx_revoke_take(take_id: str, request: Request, session: Session = Depends(get_session)):
    try:
        result = delete_take(session, take_id)
        return templates.TemplateResponse(request=request, name="components/revoke_result.html", context={"result": result})
    except Exception as e:
        return templates.TemplateResponse(request=request, name="components/revoke_result.html", context={"error": str(e)})
