from datetime import datetime, timezone
from types import SimpleNamespace
from scripts import system_supervisor as runner


def test_repair_runs_on_detection_and_rechecks(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'RUNTIME',tmp_path)
    monkeypatch.setattr(runner,'STATE',tmp_path/'state.json')
    monkeypatch.setattr(runner,'event',lambda *a,**k:None)
    monkeypatch.setattr(runner,'notify',lambda *a:None)
    now=datetime.now(timezone.utc).isoformat()
    obs=dict(passive=True,operating=True,cycle={'updated_at':now},online={'online':True},native={},markets={},journal={'ok':True},server_ok=False)
    calls=[]
    def repair(*a,**k):
        calls.append(1);obs['server_ok']=True
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runner,'observe',lambda:obs)
    monkeypatch.setattr(runner.subprocess,'run',repair)
    state=runner.run_once()
    assert calls==[1]
    row=next(x for x in state['checks'] if x['name']=='Painel')
    assert row['corrected']=='SIM' and row['status']=='OK'
    assert state['status']=='PENDING'  # Other incomplete evidence must not become green.


def test_cooldown_never_converts_unrepaired_failure_to_success(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'RUNTIME',tmp_path)
    monkeypatch.setattr(runner,'STATE',tmp_path/'state.json')
    monkeypatch.setattr(runner,'event',lambda *a,**k:None)
    monkeypatch.setattr(runner,'notify',lambda *a:None)
    now=datetime.now(timezone.utc).isoformat()
    runner.atomic_json(tmp_path/'supervisor_recovery.json',{'attempted_at':now})
    obs=dict(passive=True,operating=True,cycle={'updated_at':now},online={'online':True},native={},markets={},journal={'ok':True},server_ok=False)
    monkeypatch.setattr(runner,'observe',lambda:obs)
    monkeypatch.setattr(runner.subprocess,'run',lambda *a,**k: (_ for _ in ()).throw(AssertionError('Must not restart repeatedly')))
    assert runner.run_once()['status']=='FAIL'
