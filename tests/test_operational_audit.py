import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from application import operational_audit as audit
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult


@pytest.fixture(autouse=True)
def isolate_events(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "EVENTS", tmp_path / "operational.jsonl")

def test_preserves_history_and_ignores_partial_line(tmp_path):
    p=tmp_path/'events.jsonl'
    audit.event('Check','START',path=p)
    with p.open('a') as f:f.write('broken\n')
    audit.event('Check','DONE',path=p)
    assert [r['status'] for r in audit.recent_events(p)]==['DONE','START']


def test_primary_failure_retains_record_in_fallback(tmp_path,monkeypatch):
    primary=tmp_path/'blocked';primary.mkdir()
    fallback=tmp_path/'fallback.jsonl'
    monkeypatch.setattr(audit,'fallback_path',lambda p:fallback)
    assert audit.append_record(primary,{'value':1})==fallback
    assert json.loads(fallback.read_text())['value']==1


def provider(tmp_path):
    return SimpleNamespace(log_path=tmp_path/'orders.jsonl',execution_account=SimpleNamespace(mode='DEMO'))


def order():return ExecutionOrder('BUY',.1,100,90,120,plan_snapshot={'channel':'Alta'})


def test_attempt_precedes_send_and_result_is_persisted(tmp_path):
    p=provider(tmp_path)
    def send(p,o):
        rows=[json.loads(x) for x in (tmp_path/'execution_attempts.jsonl').read_text().splitlines()]
        assert rows[0]['stage']=='ATTEMPT'
        assert rows[0]['plan_snapshot']=={'channel':'Alta'}
        return ExecutionResult(True,'ACCEPTED','ok',ticket=7)
    assert audit.audited_submit(send)(p,order()).accepted
    rows=[json.loads(x) for x in (tmp_path/'execution_attempts.jsonl').read_text().splitlines()]
    assert rows[1]['result']['ticket']==7
    assert rows[0]['attempt_id']==rows[1]['attempt_id']


def test_total_write_failure_never_sends(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'append_record',Mock(side_effect=OSError('disk')))
    send=Mock()
    result=audit.audited_submit(send)(provider(tmp_path),order())
    assert not result.accepted
    send.assert_not_called()


def test_result_write_failure_never_changes_accepted_result(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'append_record',Mock(side_effect=[tmp_path/'ok',OSError('disk'),tmp_path/'alert']))
    expected=ExecutionResult(True,'ACCEPTED','ok',ticket=8)
    assert audit.audited_submit(lambda p,o:expected)(provider(tmp_path),order()) is expected


def test_exception_is_uncertain_not_rejected(tmp_path):
    def send(p,o):raise RuntimeError('unknown transport')
    with pytest.raises(RuntimeError):audit.audited_submit(send)(provider(tmp_path),order())
    rows=[json.loads(x) for x in (tmp_path/'execution_attempts.jsonl').read_text().splitlines()]
    assert rows[-1]['stage']=='UNCERTAIN'


def test_success_summary_does_not_claim_fill(tmp_path):
    audit.audited_submit(lambda p,o:ExecutionResult(True,'ACCEPTED','ok',ticket=99))(provider(tmp_path),order())
    row=audit.recent_events()[0]
    assert row['details']['ticket']==99
    assert row['status']=='CONFIRMADO'
    assert 'Aceite nao confirma preenchimento' in row['message']
