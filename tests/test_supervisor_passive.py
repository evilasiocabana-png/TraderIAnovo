import inspect
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from application import supervisor_observations as telemetry
from scripts import system_supervisor as runner


def test_observer_and_hourly_never_call_mt5():
    from application import supervisor_daily
    text=inspect.getsource(runner.observe)
    assert "child('--probe')" not in text and 'MetaTrader5' not in text
    hourly=inspect.getsource(supervisor_daily)
    assert 'mt5.initialize' not in hourly and 'get_mt5_trade_audit_report()' not in hourly
    assert 'subprocess.run(' not in hourly


def test_order_path_has_no_supervisor_file_reads():
    from infrastructure.execution.mt5_demo_execution_provider import MT5DemoExecutionProvider
    text=inspect.getsource(MT5DemoExecutionProvider.submit_order)
    assert 'entry_hold_reason' not in text
    assert 'reinforcement_order_error' in text


def test_full_queue_never_waits(monkeypatch):
    import queue
    q=queue.Queue(maxsize=1);q.put(1)
    monkeypatch.setattr(telemetry,'_queue',q)
    monkeypatch.setattr(telemetry,'_thread',SimpleNamespace(is_alive=lambda:True))
    monkeypatch.setattr(telemetry,'_last',{})
    monkeypatch.delenv('PYTEST_CURRENT_TEST',raising=False)
    telemetry.publish('m29_sequence',{'ok':True,'account':{'login':123}})
    assert q.get_nowait()==1


def test_passive_unknown_does_not_claim_healthy():
    from application.system_supervisor import assess
    now=datetime.now(timezone.utc)
    result=assess(dict(passive=True,operating=True,native={},cycle={'updated_at':now.isoformat()},online={'online':True},journal={'ok':True},markets={},server_ok=True),now=now)
    assert result['status']=='PENDING'


def test_read_error_not_hidden_by_recent_cycle():
    from application.system_supervisor import assess
    now=datetime.now(timezone.utc)
    result=assess(dict(passive=True,operating=True,native={},cycle={'updated_at':now.isoformat(),'result_status':'M23_RISK_READ_ERROR'},online={'online':True},journal={'ok':True},markets={},server_ok=True),now=now)
    assert result['status']=='FAIL'
