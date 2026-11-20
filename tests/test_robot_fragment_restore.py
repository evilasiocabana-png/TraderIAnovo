import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / 'dashboard_app.py'

def load_functions(namespace, *names):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    for node in nodes:
        node.decorator_list = []
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), 'exec'), namespace)

def test_partial_forex_refresh_restores_online_before_render():
    calls, state = [], {}
    ns = dict(st=SimpleNamespace(session_state=state, error=Mock()),
              MT5_DEMO_ROBOT_ONLINE_KEY='online',
              MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY='last',
              MT5_DEMO_ROBOT_MESSAGE_KEY='message',
              _load_demo_robot_online_state=lambda:dict(online=True, message='Auto armed'),
              _maybe_run_demo_robot_global_cycle=lambda service,data: calls.append(state.get('online')) or data)
    load_functions(ns, '_restore_demo_robot_online_state_if_needed', 'exibir_mt5_forex_dashboard')
    data = SimpleNamespace(mt5_forex_signals=None)
    assert ns['exibir_mt5_forex_dashboard'](object(), data) is data
    assert calls == [True]
    assert state['message'] == 'Auto armed'

def test_global_fragment_restores_before_snapshot():
    calls = []
    ns = dict(_restore_demo_robot_online_state_if_needed=lambda:calls.append('restore'),
              _maybe_run_demo_robot_global_cycle=lambda *args:calls.append('snapshot'))
    load_functions(ns, '_global_demo_robot_cycle_fragment')
    ns['_global_demo_robot_cycle_fragment'](None, None)
    assert calls == ['restore', 'snapshot']

def test_offline_persisted_state_does_not_arm_session():
    state = {}
    ns = dict(st=SimpleNamespace(session_state=state), MT5_DEMO_ROBOT_ONLINE_KEY='online',
              _load_demo_robot_online_state=lambda:dict(online=False))
    load_functions(ns, '_restore_demo_robot_online_state_if_needed')
    ns['_restore_demo_robot_online_state_if_needed']()
    assert not state
