import json,subprocess
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import infrastructure.execution.mt5_demo_execution_provider as module

@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv('TRADERIA_MT5_EXECUTION_READ_CACHE_SECONDS','2')
    monkeypatch.setattr(module,'resolve_mt5_terminal_path',lambda:'demo-terminal')
    monkeypatch.setattr(module.time,'monotonic',lambda:100.0)
    monkeypatch.setattr(module,'get_mt5_external_cache',lambda *a,**k:None)
    monkeypatch.setattr(module,'set_mt5_external_cache',Mock())
    provider=module.MT5DemoExecutionProvider(mt5=SimpleNamespace())
    key=json.dumps(dict(action='m29_sequence',terminal_path='demo-terminal'),sort_keys=True,default=str)
    provider.external_read_cache[key]=(1.0,{'ok':True,'rows':[{'stale':True}]})
    return provider,key

def test_expired_history_not_returned_when_slot_busy(setup,monkeypatch):
    provider,key=setup
    monkeypatch.setattr(module,'mt5_external_process_slot',lambda **kw:nullcontext(False))
    result=provider._external_mt5_read('m29_sequence')
    assert result['ok'] is False and result['rows']==[]
    assert result['reason']=='MT5_READ_BUSY'
    assert result['discarded_cache_age_seconds']==99

@pytest.mark.parametrize('error',[subprocess.TimeoutExpired('read',5),OSError('cannot start')])
def test_failed_read_discards_stale_data(setup,monkeypatch,error):
    provider,key=setup
    monkeypatch.setattr(module,'mt5_external_process_slot',lambda **kw:nullcontext(True))
    process=Mock();process.communicate.side_effect=error
    monkeypatch.setattr(module.subprocess,'Popen',lambda *a,**kw:process)
    terminate=Mock();monkeypatch.setattr(module,'terminate_process_tree',terminate)
    result=provider._external_mt5_read('m29_sequence')
    assert not result['ok'] and result['rows']==[]
    terminate.assert_called_once_with(process)

def test_fresh_cache_still_works(setup,monkeypatch):
    provider,key=setup
    provider.external_read_cache[key]=(99.0,{'ok':True,'rows':[1]})
    process=Mock();monkeypatch.setattr(module.subprocess,'Popen',process)
    assert provider._external_mt5_read('m29_sequence')['rows']==[1]
    process.assert_not_called()

def test_shared_cache_is_not_retimestamped(setup,monkeypatch):
    provider,key=setup
    provider.external_read_cache.clear()
    monkeypatch.setattr(module,'get_mt5_external_cache',lambda *a,**kw:{'ok':True,'rows':[2]})
    assert provider._external_mt5_read('m29_sequence')['rows']==[2]
    assert key not in provider.external_read_cache

def test_fresh_read_recovers_after_busy(setup,monkeypatch):
    provider,key=setup
    monkeypatch.setattr(module,'mt5_external_process_slot',lambda **kw:nullcontext(False))
    assert not provider._external_mt5_read('m29_sequence')['ok']
    monkeypatch.setattr(module,'mt5_external_process_slot',lambda **kw:nullcontext(True))
    process=Mock();process.communicate.return_value=(json.dumps({'ok':True,'rows':[3]}),'')
    monkeypatch.setattr(module.subprocess,'Popen',lambda *a,**kw:process)
    assert provider._external_mt5_read('m29_sequence')['rows']==[3]
    assert provider.external_read_cache[key][0]==100
