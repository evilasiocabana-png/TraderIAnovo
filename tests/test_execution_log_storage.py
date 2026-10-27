import json
import pytest
from core.execution_log_storage import execution_log_path

def test_unconfigured_runtime_stays_isolated(tmp_path):
    assert execution_log_path(tmp_path) == tmp_path/'.traderia/mt5_demo_execution.jsonl'

def test_configured_local_log_and_other_account(tmp_path, monkeypatch):
    monkeypatch.setenv('TRADERIA_EXECUTION_ACCOUNT_MODE', 'DEMO')
    runtime=tmp_path/'project';(runtime/'.traderia').mkdir(parents=True)
    target=tmp_path/'local.jsonl';target.write_text('{}\n')
    (runtime/'.traderia/execution_storage.json').write_text(json.dumps({'mode':'DEMO','execution_log':str(target)}))
    assert execution_log_path(runtime)==target
    monkeypatch.setenv('TRADERIA_EXECUTION_ACCOUNT_MODE','REAL')
    assert execution_log_path(runtime)==runtime/'.traderia/mt5_demo_execution.jsonl'

def test_missing_configured_log_does_not_fall_back_to_stale(tmp_path, monkeypatch):
    monkeypatch.setenv('TRADERIA_EXECUTION_ACCOUNT_MODE','DEMO')
    (tmp_path/'.traderia').mkdir()
    (tmp_path/'.traderia/execution_storage.json').write_text(json.dumps({'mode':'DEMO','execution_log':str(tmp_path/'missing')}))
    with pytest.raises(ValueError):execution_log_path(tmp_path)
