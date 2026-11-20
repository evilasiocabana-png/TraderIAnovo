import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from contextlib import nullcontext

def test_busy_cycle_restores_saved_history_without_marking_refresh_complete():
    tree=ast.parse(Path('dashboard_app.py').read_text(encoding='utf-8'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_maybe_refresh_mt5_trade_audit_report')
    module=ast.Module(body=[function],type_ignores=[])
    guard=Mock();service=Mock();saved=object();service._load_mt5_trade_audit_report_snapshot.return_value=saved
    state={}
    ns=dict(DashboardService=object,get_runtime_guard_service=lambda:guard,st=SimpleNamespace(session_state=state,spinner=lambda _:nullcontext()),time=SimpleNamespace(monotonic=lambda:1),_load_mt5_trade_audit_report_locked=lambda _:None,MT5_REPORT_AUDIT_CACHE_KEY='report')
    exec(compile(module,'report_refresh','exec'),ns)
    assert ns['_maybe_refresh_mt5_trade_audit_report'](service,None,force=True) is saved
    assert state['report'] is saved
    guard.mark_cycle_completed.assert_not_called()
