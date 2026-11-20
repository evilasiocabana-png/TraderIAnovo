from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import pytest
from application.system_supervisor import assess, display_state, entry_hold_reason, atomic_json

NOW=datetime(2026,11,20,12,tzinfo=timezone.utc)


def healthy():
    return dict(operating=True,native=dict(identity_ok=True,connected=True,positions=0,pending=0),
        cycle=dict(updated_at=NOW.isoformat()),online=dict(online=True),server_ok=True,
        journal=dict(ok=True,attempts=5,results=5,orphans=0),
        markets={'EURUSD':dict(native=1000,cache=1000,tick=1010,valid=True)},
        daily=dict(ok=True,finished_at=NOW.isoformat(),summary='Conferido'))


def test_green_requires_all_checks():
    result=assess(healthy(),now=NOW)
    assert result['status']=='OK' and not result['block_entries']


@pytest.mark.parametrize('component',['native','cycle','journal'])
def test_server_responding_cannot_mask_critical_failure(component):
    obs=healthy();obs[component]={}
    state=assess(obs,now=NOW)
    assert state['status']=='FAIL' and state['block_entries']


def test_unknown_daily_never_green():
    obs=healthy();obs['daily']={}
    assert assess(obs,now=NOW)['status']=='PENDING'


def test_repair_only_green_after_observation_passes():
    obs=healthy();obs['native']['connected']=False
    assert assess(obs,now=NOW)['status']=='FAIL'
    obs['native']['connected']=True
    assert assess(obs,now=NOW)['status']=='OK'


def test_no_new_orders_is_not_failure():
    obs=healthy();obs['journal']=dict(ok=True,attempts=5,results=5,orphans=0)
    assert assess(obs,now=NOW)['status']=='OK'


def test_friday_requires_native_flat_not_offline_label():
    obs=healthy();obs.update(operating=False,online=dict(online=False),cycle={})
    obs['native']['positions']=1
    assert assess(obs,now=NOW)['status']=='FAIL'
    obs['native']['positions']=0
    assert assess(obs,now=NOW)['status']=='OK'
    obs['native']['pending']=None
    assert assess(obs,now=NOW)['status']=='FAIL'


def test_native_and_cache_agree_but_tick_not_advancing_is_pending():
    obs=healthy();prior=assess(obs,now=NOW)
    assert assess(obs,prior,now=NOW)['status']=='PENDING'


def test_stale_symbol_block_is_scoped():
    obs=healthy();obs['markets']['EURUSD']['native']=2000
    state=assess(obs,now=NOW)
    assert state['blocked_symbols']==['EURUSD'] and not state['block_entries']


@pytest.mark.parametrize('seconds',[181,-1])
def test_old_or_future_heartbeat_never_green(seconds):
    state=assess(healthy(),now=NOW)
    state['updated_at']=(NOW-timedelta(seconds=seconds)).isoformat()
    assert display_state(state,NOW)['status']=='FAIL'


def test_freshness_gate_opt_in_and_fail_closed(tmp_path):
    assert entry_hold_reason('EURUSD',root=tmp_path,now=NOW)==''
    runtime=tmp_path/'.traderia/runtime'
    atomic_json(runtime/'supervisor_config.json',dict(enabled=True))
    assert entry_hold_reason('EURUSD',root=tmp_path,now=NOW)
    state=assess(healthy(),now=NOW);atomic_json(runtime/'supervisor_state.json',state)
    assert entry_hold_reason('EURUSD',root=tmp_path,now=NOW)==''
    state['blocked_symbols']=['EURUSD'];atomic_json(runtime/'supervisor_state.json',state)
    assert entry_hold_reason('EURUSD',root=tmp_path,now=NOW)
    assert entry_hold_reason('GBPUSD',root=tmp_path,now=NOW)==''
    (runtime/'supervisor_state.json').write_text('{broken')
    assert entry_hold_reason('EURUSD',root=tmp_path,now=NOW)


def test_guard_cannot_log_healthy_after_failed_recovery():
    text=Path('scripts/traderianovo_ram_guard.ps1').read_text()
    assert '$cycleVerified = ($LASTEXITCODE -eq 0)' in text
    assert 'if ($cycleVerified -and' in text


def test_weekly_close_rejects_open_window(monkeypatch):
    from scripts import system_supervisor as runner
    from types import SimpleNamespace
    monkeypatch.setattr(runner,'configure',lambda:None)
    monkeypatch.setattr(runner,'weekly_robot_schedule_decision',lambda:SimpleNamespace(operating=True))
    monkeypatch.setattr(runner,'probe',lambda:pytest.fail('No native call required'))
    assert runner.weekly_close()['status']=='SKIPPED'


def test_ui_uses_disabled_indicator_and_explanations():
    import inspect
    from application.system_supervisor import render
    text=inspect.getsource(render)
    assert 'disabled=True' in text and "row['corrected']" in text


def test_serialized_close_does_not_start_second_worker(tmp_path,monkeypatch):
    from filelock import FileLock
    import application.system_supervisor as mod
    monkeypatch.setattr(mod,'RUNTIME',tmp_path)
    calls=[]
    @mod.serialized_weekly_close
    def close():calls.append(1)
    with FileLock(str(tmp_path/'weekly_close.lock')):
        assert close()['status']=='BUSY'
    assert calls==[]
