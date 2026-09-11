"""Exercise the complete armed cycle with an inert executor and live-cache fakes."""
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

from application.dashboard_service import DashboardService, MT5_OPERATIONAL_MODEL_28, MT5_OPERATIONAL_MODEL_7
from tests.test_model28_context_integration import setup_live


def setup_armed_cycle(tmp_path, monkeypatch, *, models=(MT5_OPERATIONAL_MODEL_28,),
                      before_execution=None):
    service, row, base, record, selection = setup_live(tmp_path, monkeypatch)
    ready_row = replace(row, status='OK', decision='BUY',
                        theoretical_entry_direction='BUY',
                        theoretical_entry_status='SINAL_TEORICO',
                        theoretical_entry_price=3402.,
                        theoretical_entry_candle=selection.selected_at,
                        research_plan_status='PLANO_VALIDO')
    ready_plan = replace(base, direction='BUY', entry_price=3402.,
                         stop=3397., target=3412., risk_reward=2.,
                         status='PLANO_VALIDO', source='INERT_TEST_SOURCE')
    source_row = SimpleNamespace(pair='XAUUSD', last_candle_time=selection.selected_at)
    executor = Mock(return_value=SimpleNamespace(status='EXECUTED',
                    message='Stub accepted; no provider attached.', execution_result=None))
    converted = []
    built = []

    def set_method(name, value):
        object.__setattr__(service, name, value)

    def apply_model(candidate_row, candidate_plan, *, operational_model, **kwargs):
        if operational_model == MT5_OPERATIONAL_MODEL_28:
            result = DashboardService._mt5_model28_adaptive_plan(service, candidate_row, candidate_plan)
        else:
            result = (ready_row, ready_plan)
        built.append((operational_model, result[1]))
        return result

    def convert(candidate_row, candidate_plan, *, operational_model):
        converted.append(operational_model)
        if before_execution is not None:
            before_execution(service, operational_model)
        return SimpleNamespace(operational_model=operational_model,
                               stop_management_parameters=dict(candidate_plan.stop_management_parameters))

    set_method('mt5_demo_robot_service', SimpleNamespace(enabled=True,
               execution_service=None, evaluate_once=executor))
    set_method('demo_robot_execution_service', SimpleNamespace())
    set_method('mt5_selected_direct_operational_models', tuple(models))
    set_method('_mt5_demo_execution_enabled', lambda: True)
    set_method('get_mt5_forex_signals', lambda: object())
    set_method('_candidate_rows_for_demo_robot', lambda *args, **kwargs: [source_row])
    set_method('_mt5_research_source_for_reports', lambda: object())
    set_method('_active_mt5_research_models_by_market', lambda *args: {})
    set_method('_active_mt5_research_rows_by_market', lambda *args: {})
    set_method('_active_mt5_research_model_for_row', lambda *args: None)
    set_method('_active_mt5_research_row_for_source_row', lambda *args: None)
    set_method('_to_view_model_mt5_forex_signal_row', lambda *args: ready_row)
    set_method('_mt5_research_trade_plan_for_view_row', lambda *args: ready_plan)
    set_method('_enable_mt5_demo_provider', lambda: None)
    set_method('_mt5_model23_routing_enabled', lambda: False)
    set_method('_mt5_model24_routing_enabled', lambda: False)
    set_method('_mt5_model25_routing_enabled', lambda: False)
    set_method('_mt5_direct_routing_enabled', lambda: True)
    set_method('_mt5_operational_models_to_evaluate', lambda: list(models))
    set_method('_evaluate_model23_risk_gate', lambda *args: None)
    set_method('_evaluate_model24_risk_gate', lambda *args: None)
    set_method('_evaluate_model25_risk_gate', lambda *args: None)
    set_method('_mt5_apply_operational_model', apply_model)
    set_method('_mt5_multi_model_selection_active', lambda: len(models) > 1)
    set_method('_ordered_demo_model_candidates_per_pair', lambda candidates: candidates)
    set_method('_mt5_server_timestamp', lambda *args: None)
    set_method('forex_time_layer', SimpleNamespace(classify=lambda *args, **kwargs: SimpleNamespace()))
    set_method('_mt5_demo_signal_from_view_row', lambda *args, **kwargs: SimpleNamespace())
    set_method('_to_mt5_demo_trade_plan', convert)
    set_method('_demo_robot_rejection_tree', lambda *args, **kwargs: ())
    set_method('_demo_robot_view_model', lambda **kwargs: SimpleNamespace(**kwargs))
    set_method('_append_demo_robot_visual_signal', lambda *args: None)
    set_method('_demo_robot_audit_rows', lambda: [])
    set_method('_record_m7_execution_diagnostic', lambda *args: None)
    return service, executor, built, converted


def age_m28_receipt_after_plan_is_built(service, operational_model):
    if operational_model == MT5_OPERATIONAL_MODEL_28:
        service.mt5_market_data_service.m23_context_observed_at[('XAUUSD', 'M5')] -= 61


def test_full_armed_cycle_sends_fresh_m28_to_stub_executor(tmp_path, monkeypatch):
    service, executor, built, converted = setup_armed_cycle(tmp_path, monkeypatch)
    result = service.evaluate_armed_demo_robot_once('TODOS', 'M5')
    assert result.status == 'EXECUTED'
    executor.assert_called_once()
    assert executor.call_args.args[1].operational_model == MT5_OPERATIONAL_MODEL_28
    assert built[0][1].status == 'PLANO_VALIDO'
    assert built[0][1].stop_management_parameters['m28_context_ready'] is True
    assert converted == [MT5_OPERATIONAL_MODEL_28]


def test_full_armed_cycle_rechecks_receipt_after_plan_assembly(tmp_path, monkeypatch):
    service, executor, built, converted = setup_armed_cycle(
        tmp_path, monkeypatch, before_execution=age_m28_receipt_after_plan_is_built)
    result = service.evaluate_armed_demo_robot_once('TODOS', 'M5')
    assert built[0][1].status == 'PLANO_VALIDO'
    assert built[0][1].stop_management_parameters['m28_context_ready'] is True
    assert converted == [MT5_OPERATIONAL_MODEL_28]
    executor.assert_not_called()
    assert result.status == 'ARMED_WAITING'
    assert result.result_status == 'M28_CONTEXT_WAITING'


def test_stale_m28_does_not_block_direct_m7_in_same_armed_cycle(tmp_path, monkeypatch):
    service, executor, built, converted = setup_armed_cycle(
        tmp_path, monkeypatch, models=(MT5_OPERATIONAL_MODEL_28, MT5_OPERATIONAL_MODEL_7),
        before_execution=age_m28_receipt_after_plan_is_built)
    result = service.evaluate_armed_demo_robot_once('TODOS', 'M5')
    assert built[0][1].status == 'PLANO_VALIDO'
    assert converted == [MT5_OPERATIONAL_MODEL_28, MT5_OPERATIONAL_MODEL_7]
    executor.assert_called_once()
    assert executor.call_args.args[1].operational_model == MT5_OPERATIONAL_MODEL_7
    assert result.status == 'EXECUTED'


def test_direct_m7_has_no_dependency_on_m28_cache(tmp_path, monkeypatch):
    service, executor, built, converted = setup_armed_cycle(
        tmp_path, monkeypatch, models=(MT5_OPERATIONAL_MODEL_7,))
    service.mt5_market_data_service.latest_forex_candles.clear()
    service.mt5_market_data_service.m23_context_observed_at.clear()
    guard = Mock(side_effect=AssertionError('M28 entry gate must not run for direct M7'))
    object.__setattr__(service, '_model28_entry_context_check', guard)
    result = service.evaluate_armed_demo_robot_once('TODOS', 'M5')
    assert result.status == 'EXECUTED'
    guard.assert_not_called()
    executor.assert_called_once()
    assert executor.call_args.args[1].operational_model == MT5_OPERATIONAL_MODEL_7
