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
from backend.kivi.services.memory_control import assign_take_scope, correct_memory
from backend.kivi.schemas import TakeScopeAssignmentRequest, MemoryCorrectionRequest
from backend.kivi.models import Take, Project
from sqlalchemy import select
import json

router = APIRouter()
templates = Jinja2Templates(directory='frontend/templates')

@router.get('/')
def index(request: Request, session: Session = Depends(get_session)):
    projects = list(session.scalars(select(Project).order_by(Project.name)))
    return templates.TemplateResponse(request=request, name='index.html', context={'projects': projects})

@router.post('/htmx/ask')
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
        return templates.TemplateResponse(request=request, name='components/ask_result.html', context={'response': response, 'question': question})
    except Exception as e:
        import logging
        logging.exception('Error during /htmx/ask')
        return templates.TemplateResponse(request=request, name='components/ask_result.html', context={'error': 'An internal service error occurred. Check server logs.', 'question': question})

@router.get('/htmx/takes/{take_id}')
def htmx_get_take(take_id: str, request: Request, session: Session = Depends(get_session)):
    take = session.get(Take, take_id)
    return templates.TemplateResponse(request=request, name='components/evidence_drawer.html', context={'take': take})

@router.get('/timeline')
def timeline_index(request: Request, session: Session = Depends(get_session)):
    projects = list(session.scalars(select(Project).order_by(Project.name)))
    return templates.TemplateResponse(request=request, name='timeline.html', context={'projects': projects})

@router.get('/htmx/timeline/{project_id}')
def htmx_timeline(project_id: str, request: Request, session: Session = Depends(get_session)):
    import logging
    try:
        response = get_project_timeline(session, project_id)
        return templates.TemplateResponse(request=request, name='components/timeline_view.html', context={'timeline': response, 'project_id': project_id})
    except Exception as e:
        logging.exception('Error loading timeline')
        return templates.TemplateResponse(request=request, name='components/timeline_view.html', context={'error': 'An internal error occurred while loading the timeline.', 'project_id': project_id})

@router.get('/import-eval')
def import_eval_index(request: Request):
    return templates.TemplateResponse(request=request, name='import_eval.html')

@router.post('/htmx/import')
async def htmx_import_corpus(request: Request, corpus_file: UploadFile = File(...), session: Session = Depends(get_session)):
    import logging
    content = await corpus_file.read()
    records = []

    try:
        text_content = content.decode('utf-8').strip()
        if text_content.startswith('['):
            data = json.loads(text_content)
            for item in data:
                records.append(TakeCreate.model_validate(item))
        else:
            for i, line in enumerate(text_content.splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(TakeCreate.model_validate_json(line))
                except Exception as ve:
                    logging.exception(f'Validation failed on line {i+1}')
                    return templates.TemplateResponse(request=request, name='components/import_result.html', context={'error': f'Validation failed on line {i+1}. Please check the corpus format.'})

    except Exception as e:
        logging.exception('Failed to parse corpus upload')
        return templates.TemplateResponse(request=request, name='components/import_result.html', context={'error': 'Failed to parse the uploaded file. Ensure it is valid JSON or JSONL.'})

    bundle = request.app.state.bundle
    try:
        result = import_takes(session, records, bundle.extractor, bundle.embedder)
        return templates.TemplateResponse(request=request, name='components/import_result.html', context={'result': result})
    except Exception as e:
        logging.exception('Import operation failed')
        return templates.TemplateResponse(request=request, name='components/import_result.html', context={'error': 'An internal error occurred during import.'})

@router.get('/htmx/evaluate/latest')
def htmx_evaluate_latest(request: Request):
    from backend.kivi.evaluation import get_latest_run
    import logging
    try:
        run = get_latest_run()
        return templates.TemplateResponse(request=request, name='components/eval_result.html', context={'run': run})
    except Exception as e:
        logging.exception('Error getting latest evaluation')
        return templates.TemplateResponse(request=request, name='components/eval_result.html', context={'run': None, 'error': 'An internal error occurred while fetching the evaluation.'})

@router.post('/htmx/evaluate/run')
def htmx_evaluate_run(request: Request, mode: str = Form('deterministic')):
    from backend.kivi.evaluation import run_evaluation
    import logging
    try:
        run = run_evaluation(mode=mode)
        return templates.TemplateResponse(request=request, name='components/eval_result.html', context={'run': run})
    except Exception as e:
        logging.exception('Error running evaluation')
        return templates.TemplateResponse(request=request, name='components/eval_result.html', context={'run': None, 'error': 'An internal error occurred while running the evaluation.'})

@router.get('/htmx/evaluate/cases/{case_id}')
def htmx_evaluate_case(case_id: str, request: Request):
    from backend.kivi.evaluation import get_case_result
    import logging
    try:
        case = get_case_result(case_id)
        return templates.TemplateResponse(request=request, name='components/eval_case.html', context={'case': case})
    except Exception as e:
        logging.exception('Error getting case detail')
        return templates.TemplateResponse(request=request, name='components/eval_case.html', context={'case': None, 'error': 'An internal error occurred while fetching case details.'})

@router.delete('/htmx/takes/{take_id}')
def htmx_revoke_take(take_id: str, request: Request, session: Session = Depends(get_session)):
    import logging
    try:
        result = delete_take(session, take_id)
        return templates.TemplateResponse(request=request, name='components/revoke_result.html', context={'result': result})
    except Exception as e:
        logging.exception('Error revoking take')
        return templates.TemplateResponse(request=request, name='components/revoke_result.html', context={'error': 'An internal error occurred while revoking.'})

@router.get('/inbox')
def inbox_index(request: Request, session: Session = Depends(get_session)):
    takes = list(session.scalars(select(Take).where(Take.project_id.is_(None), Take.is_deleted.is_(False))))
    projects = list(session.scalars(select(Project).order_by(Project.name)))
    return templates.TemplateResponse(request=request, name='inbox.html', context={'takes': takes, 'projects': projects})

@router.post('/htmx/takes/{take_id}/scope')
def htmx_assign_scope(take_id: str, request: Request, project_id: str = Form(...), session: Session = Depends(get_session)):
    import logging
    from backend.kivi.services.memory_control import MemoryControlError
    from backend.kivi.providers import ProviderUnavailable
    from pydantic import ValidationError
    from backend.kivi.services.ingestion import IngestionError
    bundle = request.app.state.bundle
    try:
        result = assign_take_scope(session, take_id, TakeScopeAssignmentRequest(project_id=project_id), bundle.extractor)
        return templates.TemplateResponse(request=request, name='components/scope_result.html', context={'result': result})
    except (MemoryControlError, IngestionError, ValidationError):
        logging.exception('Invalid action assigning scope')
        return templates.TemplateResponse(request=request, name='components/scope_result.html', context={'error': 'Invalid or conflicting user action.'})
    except ProviderUnavailable:
        logging.exception('Provider unavailable assigning scope')
        return templates.TemplateResponse(request=request, name='components/scope_result.html', context={'error': 'Provider is unavailable.'})
    except Exception:
        logging.exception('Error assigning scope')
        return templates.TemplateResponse(request=request, name='components/scope_result.html', context={'error': 'An internal error occurred.'})

@router.post('/htmx/memories/{memory_id}/correct')
def htmx_correct_memory(memory_id: str, request: Request, project_id: str = Form(...), corrected_value: str = Form(...), note: str = Form(None), session: Session = Depends(get_session)):
    import logging
    from backend.kivi.services.memory_control import MemoryControlError
    from backend.kivi.providers import ProviderUnavailable
    from pydantic import ValidationError
    from backend.kivi.services.ingestion import IngestionError
    bundle = request.app.state.bundle
    try:
        result = correct_memory(session, memory_id, MemoryCorrectionRequest(corrected_value=corrected_value, note=note or ''), bundle.embedder)
        actual_project_id = result.take.project_id if result.take else project_id
        response = get_project_timeline(session, actual_project_id)
        corrected_memory_id = result.memories[0].id if result.memories else None
        return templates.TemplateResponse(request=request, name='components/timeline_view.html', context={'timeline': response, 'project_id': actual_project_id, 'corrected_memory_id': corrected_memory_id})
    except (MemoryControlError, IngestionError, ValidationError):
        logging.exception('Invalid action correcting memory')
        return templates.TemplateResponse(request=request, name='components/correction_error.html', context={'error': 'Invalid or conflicting user action.', 'project_id': project_id})
    except ProviderUnavailable:
        logging.exception('Provider unavailable correcting memory')
        return templates.TemplateResponse(request=request, name='components/correction_error.html', context={'error': 'Provider is unavailable.', 'project_id': project_id})
    except Exception:
        logging.exception('Error correcting memory')
        return templates.TemplateResponse(request=request, name='components/correction_error.html', context={'error': 'An internal error occurred.', 'project_id': project_id})

@router.get('/briefing')
def briefing_index(request: Request, session: Session = Depends(get_session)):
    projects = list(session.scalars(select(Project).order_by(Project.name)))
    return templates.TemplateResponse(request=request, name='briefing.html', context={'projects': projects})

@router.post('/htmx/briefing')
def htmx_briefing(
    request: Request,
    project_id: str = Form(None),
    focus: str = Form(None),
    session: Session = Depends(get_session)
):
    import logging
    from backend.kivi.services.memory_control import MemoryControlError
    from backend.kivi.providers import ProviderUnavailable
    from pydantic import ValidationError
    from backend.kivi.services.ingestion import IngestionError
    from backend.kivi.schemas import BriefingRequest

    bundle = request.app.state.bundle
    try:
        if not project_id or not focus:
            raise ValidationError.from_exception_data('Missing data', line_errors=[])
        req = BriefingRequest(project_id=project_id, focus=focus)
        payload = AskRequest(project_id=req.project_id, question=req.focus)
        response = ask(session, payload, bundle.embedder, bundle.answerer)
        return templates.TemplateResponse(request=request, name='components/ask_result.html', context={'response': response, 'question': focus})
    except (MemoryControlError, IngestionError, ValidationError, ValueError):
        logging.exception('Invalid action briefing')
        return templates.TemplateResponse(request=request, name='components/ask_result.html', context={'error': 'Invalid or conflicting user action.', 'question': focus or ''})
    except ProviderUnavailable:
        logging.exception('Provider unavailable briefing')
        return templates.TemplateResponse(request=request, name='components/ask_result.html', context={'error': 'Provider is unavailable.', 'question': focus or ''})
    except Exception:
        logging.exception('Error during /htmx/briefing')
        return templates.TemplateResponse(request=request, name='components/ask_result.html', context={'error': 'An internal service error occurred.', 'question': focus or ''})
