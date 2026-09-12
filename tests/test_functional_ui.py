import pytest
from backend.kivi.models import Take, Project, Memory, MemoryEvidence
from backend.kivi.enums import LifecycleStatus, EpistemicStatus, MemoryType
from datetime import datetime, timezone
from frontend.router import router as frontend_router
from backend.kivi.db import get_session
from backend.kivi.providers import ProviderUnavailable
from backend.kivi.schemas import CorpusImportResult, CorpusImportError
from sqlalchemy import select
from unittest.mock import patch

@pytest.fixture(autouse=True)
def inject_router(client, session_factory):
    if not any(route.path == '/inbox' for route in client.app.routes):
        client.app.include_router(frontend_router)

    def session_dependency():
        with session_factory() as session:
            yield session

    client.app.dependency_overrides[get_session] = session_dependency

def test_inbox_view(client, session_factory):
    with session_factory() as session:
        t = Take(id='take_unscoped_1', raw_asr='test', formatted_text='test text', source_application='app', event_ts=datetime.now(timezone.utc))
        session.add(t)
        session.commit()

    response = client.get('/inbox')
    assert response.status_code == 200
    assert 'take_unscoped_1' in response.text
    assert 'test text' in response.text

def test_assign_scope_success(client, session_factory):
    with session_factory() as session:
        p = Project(id='proj_scope_test', name='Scope Test')
        t = Take(id='take_unscoped_2', raw_asr='test', formatted_text='Test sentence.', source_application='app', event_ts=datetime.now(timezone.utc), embedding=b'0'*1536, source_metadata={'object_value': 'O', 'memory_type': MemoryType.EPISODE})
        session.add_all([p, t])
        session.commit()

    response = client.post('/htmx/takes/take_unscoped_2/scope', data={'project_id': 'proj_scope_test'})
    assert response.status_code == 200
    assert 'Scoped to' in response.text

    with session_factory() as session:
        take = session.get(Take, 'take_unscoped_2')
        assert take.project_id == 'proj_scope_test'
        assert take.id == 'take_unscoped_2'

        # creates memory check
        evs = list(session.scalars(select(MemoryEvidence).where(MemoryEvidence.take_id == 'take_unscoped_2')))
        assert len(evs) > 0

def test_assign_scope_provider_unavailable(client, monkeypatch):
    def mock_assign(*args, **kwargs):
        raise ProviderUnavailable('secret API key leaked')
    monkeypatch.setattr('frontend.router.assign_take_scope', mock_assign)

    response = client.post('/htmx/takes/take_unscoped_1/scope', data={'project_id': 'proj_scope_test'})
    assert response.status_code == 200
    assert "service unavailable" in response.text
    assert 'secret API key leaked' not in response.text

def test_assign_scope_runtime_error(client, monkeypatch):
    def mock_assign(*args, **kwargs):
        raise RuntimeError('internal database corruption')
    monkeypatch.setattr('frontend.router.assign_take_scope', mock_assign)

    response = client.post('/htmx/takes/take_unscoped_1/scope', data={'project_id': 'proj_scope_test'})
    assert response.status_code == 200
    assert 'internal error' in response.text.lower()
    assert 'internal database corruption' not in response.text

def test_correct_memory_success(client, session_factory):
    with session_factory() as session:
        p = Project(id='proj_corr', name='Corr Test')
        t = Take(id='take_corr_1', project_id='proj_corr', raw_asr='test', formatted_text='Test sentence.', source_application='app', event_ts=datetime.now(timezone.utc))
        m = Memory(id='mem_corr_1', project_id='proj_corr', subject='S', predicate='P', object_value='O', memory_type=MemoryType.EPISODE, epistemic_status=EpistemicStatus.APPROVED, lifecycle_status=LifecycleStatus.ACTIVE, confidence=1.0, created_at=datetime.now(timezone.utc), extraction_method='user', schema_version='1.0')
        session.add_all([p, t, m])
        session.commit()

    response = client.post('/htmx/memories/mem_corr_1/correct', data={'project_id': 'proj_corr', 'corrected_value': 'New O'})
    assert response.status_code == 200
    # Timeline view lowercases lifecycle_status via Jinja |lower filter
    assert "superseded" in response.text
    assert "active" in response.text
    assert 'New O' in response.text

    with session_factory() as session:
        mem = session.get(Memory, 'mem_corr_1')
        assert mem.lifecycle_status == LifecycleStatus.SUPERSEDED

        # New memory check
        new_mems = list(session.scalars(select(Memory).where(Memory.object_value == 'New O')))
        assert len(new_mems) == 1
        new_mem = new_mems[0]
        assert new_mem.lifecycle_status == LifecycleStatus.ACTIVE
        assert new_mem.epistemic_status == EpistemicStatus.APPROVED

        evidence_take_ids = [e.take_id for e in new_mem.evidence_links]
        assert any('take_correction_' in t_id for t_id in evidence_take_ids)

def test_briefing_success_renders_answered(client, session_factory, monkeypatch):
    """Briefing success must render ANSWERED status with citation chips, not NO_EVIDENCE or error."""
    with session_factory() as session:
        p = Project(id='proj_br', name='Proj BR')
        session.add(p)
        session.commit()

    from backend.kivi.schemas import AskResponse
    from backend.kivi.enums import QueryStatus

    def mock_ask(*args, **kwargs):
        return AskResponse(
            query_id='q1',
            status=QueryStatus.ANSWERED,
            answer='Mocked answer text.',
            project_id='proj_br',
            claims=[{
                'claim_text': 'Mocked answer text.',
                'memory_ids': ['mem1'],
                'supporting_take_ids': ['take_br_1']
            }],
            supporting_take_ids=['take_br_1'],
            decision_reason='Test',
            retrieval_latency_ms=10,
            end_to_end_latency_ms=10,
            model_name='test-model'
        )
    monkeypatch.setattr('frontend.router.ask', mock_ask)

    response = client.post('/htmx/briefing', data={'project_id': 'proj_br', 'focus': 'What is going on?'})
    assert response.status_code == 200
    html = response.text
    # Must NOT be error or NO_EVIDENCE
    assert 'no evidence' not in html.lower()
    assert 'service unavailable' not in html.lower()
    assert 'service error' not in html.lower()
    # Must contain the answer
    assert 'Mocked answer text.' in html
    # Must contain citation chip with hx-get
    assert 'take_br_1' in html
    assert 'hx-get="/htmx/takes/take_br_1"' in html

def test_briefing_error_focuses_briefing_input(client, monkeypatch):
    """Error retry button must target briefing's focus input, not #chat-history."""
    def mock_ask(*args, **kwargs):
        raise ProviderUnavailable('secret token leaked')
    monkeypatch.setattr('frontend.router.ask', mock_ask)

    response = client.post('/htmx/briefing', data={'project_id': 'proj_br', 'focus': 'test'})
    assert response.status_code == 200
    html = response.text
    assert "service unavailable" in html
    assert 'secret token leaked' not in html
    # The retry button must find focus input (briefing) or question input (ask)
    assert "input[name=question]" in html or "input[name=focus]" in html

def test_ask_error_focuses_question_input(client, monkeypatch):
    """Ask error retry button must return focus to the question input."""
    def mock_ask(*args, **kwargs):
        raise Exception('internal error')
    monkeypatch.setattr('frontend.router.ask', mock_ask)

    response = client.post('/htmx/ask', data={'question': 'test question'})
    assert response.status_code == 200
    html = response.text
    assert 'service unavailable' in html
    # Must contain focus logic for the question input
    assert "input[name=question]" in html

def test_scope_result_exact_confirmation(client, session_factory):
    """Scope result must show exact project_id and take_id."""
    with session_factory() as session:
        p = Project(id='proj_scope_test', name='Proj')
        t = Take(id='take_scope_2', project_id=None, raw_asr='test', formatted_text='Test.', source_application='app', event_ts=datetime.now(timezone.utc))
        session.add_all([p, t])
        session.commit()
    response = client.post('/htmx/takes/take_scope_2/scope', data={'project_id': 'proj_scope_test'})
    assert response.status_code == 200
    html = response.text
    assert "Scoped to proj_scope_test." in html
    assert "Take take_scope_2 is now being processed" in html

def test_ask_answered_renders_citation(client, session_factory):
    """A genuine ANSWERED Ask must render the answer text and citation chip with hx-get."""
    with session_factory() as session:
        p = Project(id='proj_ask', name='Ask Project')
        session.add(p)
        session.commit()

    from backend.kivi.schemas import AskResponse
    from backend.kivi.enums import QueryStatus

    with patch('frontend.router.ask') as mock_ask:
        mock_ask.return_value = AskResponse(
            query_id='q_test',
            status=QueryStatus.ANSWERED,
            answer="Harbor review is Thursday at 4 PM.",
            project_id='proj_ask',
            claims=[{
                'claim_text': "Harbor review is Thursday at 4 PM.",
                'memory_ids': ['mem_test'],
                'supporting_take_ids': ['take_ask_1']
            }],
            supporting_take_ids=['take_ask_1'],
            decision_reason='Test',
            retrieval_latency_ms=5,
            end_to_end_latency_ms=10,
        )
        response = client.post('/htmx/ask', data={'question': 'When is the review?', 'project_id': 'proj_ask'})

    assert response.status_code == 200
    html = response.text
    # Exact answer text
    assert "Harbor review is Thursday at 4 PM." in html
    # Citation chip with proper hx-get for evidence drawer
    assert 'hx-get="/htmx/takes/take_ask_1"' in html
    assert 'take_ask_1' in html
    # Must NOT show error or no-evidence badges
    assert 'no evidence' not in html.lower()
    assert 'service unavailable' not in html.lower()

def test_import_error_never_shows_detail(client):
    """CorpusImportError.detail must never be displayed regardless of error_type."""
    with patch('frontend.router.import_takes') as mock_import:
        mock_import.return_value = CorpusImportResult(
            total=3, ingested=0, memories_created=0, unscoped=0, failed=3,
            errors=[
                CorpusImportError(take_id='t1', error_type='IngestionError', detail='unknown project_id: secret-proj'),
                CorpusImportError(take_id='t2', error_type='ProviderUnavailable', detail='API key: sk-SECRET123'),
                CorpusImportError(take_id='t3', error_type='RuntimeError', detail='internal stack trace here'),
            ]
        )
        files = {"corpus_file": ("test.jsonl", b'[]', "application/json")}
        response = client.post('/htmx/import', files=files)

    assert response.status_code == 200
    html = response.text
    # Safe mapped categories must appear
    assert 'could not process record' in html
    assert 'service unavailable' in html
    assert 'processing error' in html
    # Raw detail must NEVER appear
    assert 'unknown project_id' not in html
    assert 'secret-proj' not in html
    assert 'sk-SECRET123' not in html
    assert 'API key' not in html
    assert 'internal stack trace' not in html
    assert 'stack trace' not in html

def test_import_eval_page_has_two_panels_no_sidebar(client):
    """Import/Eval page must override sidebar to empty, showing only two primary panels."""
    response = client.get('/import-eval')
    assert response.status_code == 200
    html = response.text
    assert 'import corpus' in html
    assert 'evaluation' in html
    # The evidence drawer should be below, not in sidebar
    assert 'eval-case-container' in html
    assert 'evidence-drawer-container' in html
