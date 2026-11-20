from dataclasses import replace
import threading
from unittest.mock import Mock
from types import SimpleNamespace
import pytest
from application import operational_audit as audit
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from core.background_runtime_registry import start_background_runtime_once

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'EVENTS',tmp_path/'events.jsonl')
    monkeypatch.setattr(audit,'fallback_path',lambda p:tmp_path/'fallback'/p.name)

def inputs(tmp_path):
    p=SimpleNamespace(log_path=tmp_path/'orders.jsonl',execution_account=SimpleNamespace(mode='DEMO'))
    o=ExecutionOrder('BUY',.1,100,90,110,symbol='XAUUSD',plan_identity='signal-one')
    return p,o

def test_accepted_plan_cannot_repeat_after_new_wrapper(tmp_path):
    p,o=inputs(tmp_path);send=Mock(return_value=ExecutionResult(True,'ACCEPTED','ok',ticket=7))
    assert audit.audited_submit(send)(p,o).accepted
    assert not audit.audited_submit(send)(p,o).accepted
    assert send.call_count==1
    assert audit.audited_submit(send)(p,replace(o,plan_identity='signal-two')).accepted

def test_unknown_result_blocks_even_a_new_signal(tmp_path):
    p,o=inputs(tmp_path);send=Mock(side_effect=RuntimeError('after broker'))
    with pytest.raises(RuntimeError):audit.audited_submit(send)(p,o)
    second=Mock()
    assert not audit.audited_submit(second)(p,replace(o,plan_identity='signal-two')).accepted
    second.assert_not_called()

def test_crash_after_attempt_blocks_replay(tmp_path):
    p,o=inputs(tmp_path)
    audit.append_record(tmp_path/'execution_attempts.jsonl',dict(stage='ATTEMPT',attempt_id='old',execution_account_mode='DEMO',symbol=o.symbol,operational_model=o.operational_model))
    send=Mock();assert not audit.audited_submit(send)(p,o).accepted;send.assert_not_called()

def test_corrupt_journal_blocks(tmp_path):
    p,o=inputs(tmp_path);(tmp_path/'execution_attempts.jsonl').write_text('broken')
    send=Mock();assert not audit.audited_submit(send)(p,o).accepted;send.assert_not_called()

def test_supervisor_restarts_failed_target_without_second_start():
    import uuid
    called=threading.Event();hold=threading.Event();count=[]
    def target():
        count.append(1)
        if len(count)==1:raise RuntimeError('failed')
        called.set();hold.wait()
    name='recovery-test-'+str(uuid.uuid4())
    assert start_background_runtime_once(name,target,restart=True,retry_seconds=.01)
    assert called.wait(2)
    assert not start_background_runtime_once(name,target,restart=True)
    assert len(count)==2
