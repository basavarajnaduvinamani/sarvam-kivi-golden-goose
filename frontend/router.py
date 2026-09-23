import sys
import json
import logging
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func
from pydantic import ValidationError

from kivi.schemas import AskRequest, TakeCreate, TakeScopeAssignmentRequest, MemoryCorrectionRequest, BriefingRequest, AskResponse
from kivi.app import default_provider_bundle
from kivi.db import get_session
from kivi.services.retrieval import ask
from kivi.services.timeline import get_project_timeline
from kivi.services.corpus_import import import_takes
from kivi.services.deletion import delete_take
from kivi.services.memory_control import assign_take_scope, correct_memory, MemoryControlError
from kivi.models import Take, Project, Memory, MemoryEvidence
from kivi.enums import MemoryType, EpistemicStatus, LifecycleStatus, QueryStatus
from kivi.providers import ProviderUnavailable
from kivi.services.ingestion import IngestionError
from kivi.presenters import present_memory

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
        logging.exception('Error during /htmx/ask')
        return templates.TemplateResponse(request=request, name='components/ask_result.html', context={'error': 'An internal service error occurred. Check server logs.', 'question': question})

@router.get('/htmx/takes/{take_id}')
def htmx_get_take(take_id: str, request: Request, session: Session = Depends(get_session)):
    take = session.get(Take, take_id)
    return templates.TemplateResponse(request=request, name='components/evidence_drawer.html', context={'take': take, 'missing': take is None})

@router.get('/timeline')
def timeline_index(request: Request, session: Session = Depends(get_session)):
    projects = list(session.scalars(select(Project).order_by(Project.name)))
    return templates.TemplateResponse(request=request, name='timeline.html', context={'projects': projects})

@router.get('/htmx/timeline/{project_id}')
def htmx_timeline(project_id: str, request: Request, session: Session = Depends(get_session)):
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
    from kivi.evaluation import get_latest_run
    try:
        run = get_latest_run()
        return templates.TemplateResponse(request=request, name='components/eval_result.html', context={'run': run})
    except Exception as e:
        logging.exception('Error getting latest evaluation')
        return templates.TemplateResponse(request=request, name='components/eval_result.html', context={'run': None, 'error': 'An internal error occurred while fetching the evaluation.'})

@router.post('/htmx/evaluate/run')
def htmx_evaluate_run(request: Request, mode: str = Form('deterministic')):
    from kivi.evaluation import run_evaluation
    try:
        run = run_evaluation(mode=mode)
        return templates.TemplateResponse(request=request, name='components/eval_result.html', context={'run': run})
    except Exception as e:
        logging.exception('Error running evaluation')
        return templates.TemplateResponse(request=request, name='components/eval_result.html', context={'run': None, 'error': 'An internal error occurred while running the evaluation.'})

@router.get('/htmx/evaluate/cases/{case_id}')
def htmx_evaluate_case(case_id: str, request: Request):
    from kivi.evaluation import get_case_result
    try:
        case = get_case_result(case_id)
        return templates.TemplateResponse(request=request, name='components/eval_case.html', context={'case': case})
    except Exception as e:
        logging.exception('Error getting case detail')
        return templates.TemplateResponse(request=request, name='components/eval_case.html', context={'case': None, 'error': 'An internal error occurred while fetching case details.'})

@router.delete('/htmx/takes/{take_id}')
def htmx_revoke_take(take_id: str, request: Request, session: Session = Depends(get_session)):
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
    bundle = request.app.state.bundle
    try:
        result = assign_take_scope(session, take_id, TakeScopeAssignmentRequest(project_id=project_id), bundle.extractor)
        return templates.TemplateResponse(request=request, name='components/scope_result.html', context={'result': result})
    except (MemoryControlError, IngestionError, ValidationError):
        logging.exception('Invalid action assigning scope')
        return templates.TemplateResponse(request=request, name='components/scope_result.html', context={'error': 'Invalid or conflicting user action.'})
    except ProviderUnavailable:
        logging.exception('Provider unavailable assigning scope')
        return templates.TemplateResponse(request=request, name='components/scope_result.html', context={'error': 'service unavailable'})
    except Exception:
        logging.exception('Error assigning scope')
        return templates.TemplateResponse(request=request, name='components/scope_result.html', context={'error': 'An internal error occurred.'})

@router.post('/htmx/memories/{memory_id}/correct')
def htmx_correct_memory(memory_id: str, request: Request, project_id: str = Form(...), corrected_value: str = Form(...), note: str = Form(None), session: Session = Depends(get_session)):
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
        return templates.TemplateResponse(request=request, name='components/correction_error.html', context={'error': 'service unavailable', 'project_id': project_id})
    except Exception:
        logging.exception('Error correcting memory')
        return templates.TemplateResponse(request=request, name='components/correction_error.html', context={'error': 'An internal error occurred.', 'project_id': project_id})

@router.get('/briefing')
def briefing_index(request: Request, session: Session = Depends(get_session)):
    projects = list(session.scalars(select(Project).order_by(Project.name)))
    return templates.TemplateResponse(request=request, name='briefing.html', context={'projects': projects})

def _build_briefing_view_model(session: Session, project_id: str):
    project = session.scalar(select(Project).where(Project.id == project_id))

    indexed_count = session.scalar(
        select(func.count(Take.id)).where(Take.project_id == project_id, Take.is_deleted.is_(False))
    ) or 0

    memories_query = (
        select(Memory)
        .where(
            Memory.project_id == project_id,
            Memory.lifecycle_status == LifecycleStatus.ACTIVE
        )
        .order_by(Memory.created_at.desc())
    )
    active_memories = list(session.scalars(memories_query))

    open_questions = []
    seen_question_ids = set()
    for mem in active_memories:
        if mem.memory_type == MemoryType.UNRESOLVED_QUESTION and mem.id not in seen_question_ids:
            take_ids = sorted({
                link.take_id
                for link in mem.evidence_links
                if not link.take.is_deleted and link.take.project_id == project_id
            })
            if take_ids:
                seen_question_ids.add(mem.id)
                open_questions.append({
                    "id": mem.id,
                    "text": f"{mem.predicate} — {mem.object_value}",
                    "predicate": mem.predicate,
                    "value": mem.object_value,
                    "status": str(mem.epistemic_status).lower(),
                    "take_ids": take_ids,
                })

    commitments = []
    seen_commitment_ids = set()
    for mem in active_memories:
        if mem.memory_type == MemoryType.COMMITMENT and mem.id not in seen_commitment_ids:
            take_ids = sorted({
                link.take_id
                for link in mem.evidence_links
                if not link.take.is_deleted and link.take.project_id == project_id
            })
            if take_ids:
                seen_commitment_ids.add(mem.id)
                commitments.append({
                    "id": mem.id,
                    "statement": f"{mem.predicate} — {mem.object_value}",
                    "subject": mem.subject,
                    "predicate": mem.predicate,
                    "value": mem.object_value,
                    "status": str(mem.epistemic_status).lower(),
                    "take_ids": take_ids,
                })

    return {
        "project": project,
        "indexed_count": indexed_count,
        "commitments": commitments,
        "open_questions": open_questions,
    }

@router.post('/htmx/briefing')
def htmx_briefing(
    request: Request,
    project_id: str = Form(None),
    focus: str = Form(None),
    session: Session = Depends(get_session)
):
    bundle = request.app.state.bundle
    try:
        if not project_id:
            raise ValidationError.from_exception_data('Missing project_id', line_errors=[])
        clean_focus = focus.strip() if focus and focus.strip() else None
        if clean_focus:
            req = BriefingRequest(project_id=project_id, focus=clean_focus)
            payload = AskRequest(project_id=req.project_id, question=req.focus)
            response = ask(session, payload, bundle.embedder, bundle.answerer)
        else:
            req = BriefingRequest(project_id=project_id)
            payload = AskRequest(project_id=req.project_id, question=req.focus)
            response = ask(session, payload, bundle.embedder, bundle.answerer)
            if response.status == QueryStatus.NO_EVIDENCE:
                mems_query = (
                    select(Memory)
                    .where(
                        Memory.project_id == project_id,
                        Memory.lifecycle_status == LifecycleStatus.ACTIVE
                    )
                    .options(selectinload(Memory.evidence_links).selectinload(MemoryEvidence.take))
                )
                active_mems = list(session.scalars(mems_query))
                valid_mems = [
                    m for m in active_mems
                    if any(not l.take.is_deleted and l.take.project_id == project_id for l in m.evidence_links)
                ]
                if valid_mems:
                    readable = [present_memory(m) for m in valid_mems]
                    grounded = bundle.answerer.answer(req.focus, readable)
                    all_takes = sorted({tid for claim in grounded.claims for tid in claim.supporting_take_ids})
                    response = AskResponse(
                        query_id=response.query_id,
                        status=QueryStatus.ANSWERED,
                        answer=grounded.answer,
                        project_id=project_id,
                        claims=grounded.claims,
                        supporting_take_ids=all_takes,
                        decision_reason="Answer generated from the project's active, verified memories.",
                        retrieval_latency_ms=response.retrieval_latency_ms,
                        end_to_end_latency_ms=response.end_to_end_latency_ms,
                        model_name=grounded.usage.model_name,
                        input_tokens=grounded.usage.input_tokens,
                        output_tokens=grounded.usage.output_tokens,
                        estimated_cost_usd=grounded.usage.estimated_cost_usd,
                    )
        vm = _build_briefing_view_model(session, project_id)
        ctx = {
            'response': response,
            'question': req.focus,
            'project': vm['project'],
            'indexed_count': vm['indexed_count'],
            'commitments': vm['commitments'],
            'open_questions': vm['open_questions'],
        }
        return templates.TemplateResponse(request=request, name='components/briefing_result.html', context=ctx)
    except (MemoryControlError, IngestionError, ValidationError, ValueError):
        logging.exception('Invalid action briefing')
        return templates.TemplateResponse(request=request, name='components/briefing_result.html', context={'error': 'Invalid or conflicting user action.', 'question': focus or ''})
    except ProviderUnavailable:
        logging.exception('Provider unavailable briefing')
        return templates.TemplateResponse(request=request, name='components/briefing_result.html', context={'error': 'service unavailable', 'question': focus or ''})
    except Exception:
        logging.exception('Error during /htmx/briefing')
        return templates.TemplateResponse(request=request, name='components/briefing_result.html', context={'error': 'An internal service error occurred.', 'question': focus or ''})
