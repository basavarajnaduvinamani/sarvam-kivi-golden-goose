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
    import logging
    try:
        response = get_project_timeline(session, project_id)
        return templates.TemplateResponse(request=request, name="components/timeline_view.html", context={"timeline": response})
    except Exception as e:
        logging.exception("Error loading timeline")
        return templates.TemplateResponse(request=request, name="components/timeline_view.html", context={"error": "An internal error occurred while loading the timeline."})

@router.get("/import-eval")
def import_eval_index(request: Request):
    return templates.TemplateResponse(request=request, name="import_eval.html")

@router.post("/htmx/import")
async def htmx_import_corpus(request: Request, corpus_file: UploadFile = File(...), session: Session = Depends(get_session)):
    import logging
    content = await corpus_file.read()
    records = []
    
    try:
        text_content = content.decode('utf-8').strip()
        if text_content.startswith('['):
            # Fallback to array if someone provides a standard JSON array
            data = json.loads(text_content)
            for item in data:
                records.append(TakeCreate.model_validate(item))
        else:
            # Parse line by line
            for i, line in enumerate(text_content.splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(TakeCreate.model_validate_json(line))
                except Exception as ve:
                    # Provide safe user-facing error containing line number
                    logging.exception(f"Validation failed on line {i+1}")
                    return templates.TemplateResponse(request=request, name="components/import_result.html", context={"error": f"Validation failed on line {i+1}. Please check the corpus format."})
                    
    except Exception as e:
        logging.exception("Failed to parse corpus upload")
        return templates.TemplateResponse(request=request, name="components/import_result.html", context={"error": "Failed to parse the uploaded file. Ensure it is valid JSON or JSONL."})

    bundle = request.app.state.bundle
    try:
        result = import_takes(session, records, bundle.extractor, bundle.embedder)
        return templates.TemplateResponse(request=request, name="components/import_result.html", context={"result": result})
    except Exception as e:
        logging.exception("Import operation failed")
        return templates.TemplateResponse(request=request, name="components/import_result.html", context={"error": "An internal error occurred during import."})

@router.get("/htmx/evaluate/latest")
def htmx_evaluate_latest(request: Request):
    from backend.kivi.evaluation import get_latest_run
    import logging
    try:
        run = get_latest_run()
        return templates.TemplateResponse(request=request, name="components/eval_result.html", context={"run": run})
    except Exception as e:
        logging.exception("Error getting latest evaluation")
        return templates.TemplateResponse(request=request, name="components/eval_result.html", context={"run": None, "error": "An internal error occurred while fetching the evaluation."})

@router.post("/htmx/evaluate/run")
def htmx_evaluate_run(request: Request, mode: str = Form("deterministic")):
    from backend.kivi.evaluation import run_evaluation
    import logging
    try:
        run = run_evaluation(mode=mode)
        return templates.TemplateResponse(request=request, name="components/eval_result.html", context={"run": run})
    except Exception as e:
        logging.exception("Error running evaluation")
        return templates.TemplateResponse(request=request, name="components/eval_result.html", context={"run": None, "error": "An internal error occurred while running the evaluation."})

@router.get("/htmx/evaluate/cases/{case_id}")
def htmx_evaluate_case(case_id: str, request: Request):
    from backend.kivi.evaluation import get_case_result
    import logging
    try:
        case = get_case_result(case_id)
        return templates.TemplateResponse(request=request, name="components/eval_case.html", context={"case": case})
    except Exception as e:
        logging.exception("Error getting case detail")
        return templates.TemplateResponse(request=request, name="components/eval_case.html", context={"case": None, "error": "An internal error occurred while fetching case details."})

@router.delete("/htmx/takes/{take_id}")
def htmx_revoke_take(take_id: str, request: Request, session: Session = Depends(get_session)):
    import logging
    try:
        result = delete_take(session, take_id)
        return templates.TemplateResponse(request=request, name="components/revoke_result.html", context={"result": result})
    except Exception as e:
        logging.exception("Error revoking take")
        return templates.TemplateResponse(request=request, name="components/revoke_result.html", context={"error": "An internal error occurred while revoking."})
