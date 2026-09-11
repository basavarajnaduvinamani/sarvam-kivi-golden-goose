import pytest
from backend.kivi.models import Take, Project, Memory, MemoryEvidence
from backend.kivi.enums import LifecycleStatus, EpistemicStatus, MemoryType
from datetime import datetime, timezone
from frontend.router import router as frontend_router
from backend.kivi.db import get_session
from backend.kivi.providers import ProviderUnavailable
from sqlalchemy import select

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
    assert 'Scope assigned successfully' in response.text

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
    assert 'Provider is unavailable' in response.text
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
    assert 'Timeline for Corr Test' in response.text
    assert 'New O' in response.text
    assert 'SUPERSEDED' in response.text

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

def test_briefing_success(client, session_factory, monkeypatch):
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
    assert 'NO EVIDENCE' not in response.text.upper()
    assert 'SERVICE ERROR' not in response.text.upper()
    assert 'Mocked answer text.' in response.text
    assert 'take_br_1' in response.text
def test_briefing_provider_error(client, monkeypatch):
    def mock_ask(*args, **kwargs):
        raise ProviderUnavailable('secret token leaked')
    monkeypatch.setattr('frontend.router.ask', mock_ask)

    response = client.post('/htmx/briefing', data={'project_id': 'proj_br', 'focus': 'test'})
    assert response.status_code == 200
    assert 'Provider is unavailable' in response.text
    assert 'secret token leaked' not in response.text
