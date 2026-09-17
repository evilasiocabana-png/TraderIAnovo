from dataclasses import replace
from types import SimpleNamespace

import pytest

from application.model29_entry_sync import GoldM7EntrySync, is_gold_m7, same_source_plan, pair_has_open_position
from research.mt5_research_trade_plan import MT5ResearchTradePlan


def plan(mirrored=False):
    return MT5ResearchTradePlan(
        symbol="XAUUSD", timeframe="H1", direction="BUY" if mirrored else "SELL",
        entry_price=100, stop=90 if mirrored else 110,
        target=110 if mirrored else 75, risk_reward=1 if mirrored else 2.5,
        stop_multiplier=1, exit_model="TEST", exit_score=0, exit_candidates=0,
        status="PLANO_VALIDO", stop_management_parameters={
            "source_operational_model": "MODELO_7_LAB_XAU_BTC",
            "source_entry_setup": "TREND_MOMENTUM", "source_initial_stop": 110,
            "source_target": 75, "m29_m7_mode": "ESPELHADO" if mirrored else "NORMAL", **({"m29_mirrored": True, "m29_original_direction": "SELL"} if mirrored else {}),
        },
    )


def result(status="EXECUTED", accepted=True, ticket=123):
    return SimpleNamespace(status=status, message="Test", execution_result=SimpleNamespace(
        accepted=accepted, ticket=ticket, status="ACCEPTED" if accepted else "REJECTED", message="Test",
    ))


@pytest.mark.parametrize("mirrored", [False, True])
def test_confirmed_same_signal_is_consumed_once(mirrored):
    sync = GoldM7EntrySync()
    sync.record("MODELO_23_BASKET_ACCUMULATOR_SOURCE_M7", plan(), "candle1", result())
    assert sync.claim(plan(mirrored), "candle1") == 123
    assert sync.claim(plan(mirrored), "candle1") is None
    assert GoldM7EntrySync().claim(plan(mirrored), "candle1") is None


@pytest.mark.parametrize("outcome", [result("REJECTED", False), result("WAITING"), result(ticket=None)])
def test_no_execution_no_permission(outcome):
    sync = GoldM7EntrySync()
    sync.record("MODELO_23_BASKET_ACCUMULATOR_SOURCE_M7", plan(), "candle1", outcome)
    assert sync.claim(plan(True), "candle1") is None


@pytest.mark.parametrize("change", ["candle", "entry", "target", "stop", "source", "symbol", "direction"])
def test_different_plan_cannot_consume_confirmation(change):
    sync = GoldM7EntrySync()
    sync.record("MODELO_23_BASKET_ACCUMULATOR_SOURCE_M7", plan(), "candle1", result())
    candidate = plan(True)
    candle = "candle1"
    if change == "candle":
        candle = "candle2"
    elif change == "entry":
        candidate = replace(candidate, entry_price=101)
    elif change == "target":
        candidate = replace(candidate, target=111)
    elif change == "symbol":
        candidate = replace(candidate, symbol="BTCUSD")
    else:
        parameters = dict(candidate.stop_management_parameters)
        key = {"stop": "source_initial_stop", "source": "source_operational_model", "direction": "m29_original_direction"}[change]
        parameters[key] = {"stop": 111, "source": "MODELO_8", "direction": "BUY"}[change]
        candidate = replace(candidate, stop_management_parameters=parameters)
    assert sync.claim(candidate, candle) is None


def test_scope_excludes_bitcoin_and_other_sources():
    assert is_gold_m7(plan())
    assert not is_gold_m7(replace(plan(), symbol="BTCUSD"))
    assert not is_gold_m7(replace(plan(), stop_management_parameters={"source_operational_model": "MODELO_8"}))


@pytest.mark.parametrize("model", [23, 29])
def test_either_open_leg_blocks_next_pair(model):
    position = SimpleNamespace(symbol="XAUUSD", comment=f"TraderIA M{model} S7 TOKEN")
    assert pair_has_open_position([position])
    assert not pair_has_open_position([SimpleNamespace(symbol="BTCUSD", comment=position.comment)])
    assert not pair_has_open_position([SimpleNamespace(symbol="XAUUSD", comment="TraderIA M29 S8 TOKEN")])
    assert not pair_has_open_position([])
    with pytest.raises(RuntimeError):
        pair_has_open_position(None)


def test_normal_and_mirror_pair_use_identical_source():
    assert same_source_plan(plan(), "one", plan(True), "one")
    assert same_source_plan(plan(), "one", plan(), "one")
    assert not same_source_plan(plan(), "one", plan(True), "two")


@pytest.mark.parametrize("mirrored", [False, True])
@pytest.mark.parametrize("scenario", ["accepted", "rejected", "open23", "open29", "opencopy", "copyreject"])
@pytest.mark.parametrize("own_m29", [False, True])
def test_dashboard_pairs_real_candidate_pipeline(tmp_path, monkeypatch, mirrored, scenario, own_m29):
    from unittest.mock import Mock
    import application.dashboard_service as module
    from application.dashboard_service import DashboardService

    monkeypatch.chdir(tmp_path)
    service = DashboardService()
    service.set_mt5_operational_models((), basket_models=((module.MT5_OPERATIONAL_MODEL_23, module.MT5_OPERATIONAL_MODEL_29) if own_m29 else (module.MT5_OPERATIONAL_MODEL_23,)))
    from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
    row = DashboardMT5ForexSignalRowViewModel(pair="XAUUSD", status="OK", timeframe="H1", decision="SELL", active_model="M7 TEST", theoretical_entry_candle="candle1", last_candle_time="candle1")
    source = Mock(return_value=(row, plan()))
    overrides = {
        "_mt5_demo_execution_enabled": lambda: True,
        "get_mt5_forex_signals": lambda: None,
        "_candidate_rows_for_demo_robot": lambda *a: [row],
        "_mt5_research_source_for_reports": lambda: None,
        "_active_mt5_research_models_by_market": lambda *a: {},
        "_active_mt5_research_rows_by_market": lambda *a: {},
        "_active_mt5_research_model_for_row": lambda *a: None,
        "_active_mt5_research_row_for_source_row": lambda *a: None,
        "_to_view_model_mt5_forex_signal_row": lambda *a: row,
        "_mt5_research_trade_plan_for_view_row": lambda *a: plan(),
        "_enable_mt5_demo_provider": lambda: None,
        "_mt5_operational_models_to_evaluate": lambda: (module.MT5_OPERATIONAL_MODEL_7,),
        "_mt5_apply_operational_model": source,
        "_mt5_model23_variant_from_source": lambda *a, **k: (row, plan()),
        "_mt5_model29_variant_from_source": lambda *a, **k: (replace(row, decision="BUY" if mirrored else "SELL"), plan(mirrored)),
        "_record_m7_execution_diagnostic": lambda *a, **k: None,
        "_mt5_server_timestamp": lambda *a: None,
        "_mt5_demo_signal_from_view_row": lambda *a, **k: k["operational_model"],
        "_to_mt5_demo_trade_plan": lambda row, p, **k: p,
        "_demo_robot_audit_rows": lambda: (),
        "_demo_robot_rejection_tree": lambda *a, **k: None,
        "_demo_robot_view_model": lambda **k: SimpleNamespace(**k),
        "_append_demo_robot_visual_signal": lambda *a: None,
    }
    for n in (23, 29, 24, 25):
        overrides[f"_evaluate_model{n}_risk_gate"] = lambda *a: None
    for name, value in overrides.items():
        object.__setattr__(service, name, value)
    positions = [] if not scenario.startswith("open") else [SimpleNamespace(symbol="XAUUSD", comment=("TraderIA M23 S29 M7 TEST" if scenario=="opencopy" else f"TraderIA M{scenario[-2:]} S7 TEST"))]
    provider = SimpleNamespace(_external_mt5_read=lambda *a, **k: dict(ok=True, account=dict(login=1,server="TEST"), open_positions=[vars(p) for p in positions]))
    object.__setattr__(service, "demo_robot_execution_service", SimpleNamespace(provider=provider, list_open_positions=lambda: positions))
    sent = []
    def send(signal, candidate):
        sent.append((signal, candidate))
        if scenario == "copyreject" and signal == "MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29":
            return result("REJECTED", False)
        return result("REJECTED", False) if scenario == "rejected" else result()
    object.__setattr__(service, "mt5_demo_robot_service", SimpleNamespace(enabled=True, evaluate_once=send))
    object.__setattr__(service, "forex_time_layer", SimpleNamespace(classify=lambda *a, **k: None))
    monkeypatch.setattr(module, "model23_entry_gate", lambda *a: (True, ""))
    monkeypatch.setattr(module, "model29_entry_gate", lambda *a: (True, ""))
    if scenario == "copyreject":
        base_send = send
        def send_pair(signal, candidate):
            outcome = base_send(signal, candidate)
            if signal.endswith("_SOURCE_M7") and signal.startswith("MODELO_23_"):
                positions.append(SimpleNamespace(ticket=123,identifier=123,symbol="XAUUSD",comment="TraderIA M23 S7 TEST"))
            return outcome
        service.mt5_demo_robot_service.evaluate_once = send_pair
    service.evaluate_armed_demo_robot_once()
    if scenario == "copyreject":
        first_count = len(sent)
        def retry_send(signal, candidate):
            sent.append((signal,candidate))
            assert signal == "MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29"
            return result(ticket=456)
        service.mt5_demo_robot_service.evaluate_once = retry_send
        service.evaluate_armed_demo_robot_once()
        assert len(sent) == first_count + 1
        # Accepted copy may already have closed: still do not reopen while original remains.
        service.evaluate_armed_demo_robot_once()
        assert len(sent) == first_count + 1
        return
    assert source.call_count == 1
    expected = 0 if scenario.startswith("open") else 1 if scenario == "rejected" else 3 if own_m29 else 2
    assert len(sent) == expected
    if expected == 3:
        assert sent[0][0].startswith("MODELO_23_")
        assert sent[1][0].startswith("MODELO_29_")
        assert sent[1][1].stop_management_parameters["m29_sync_m23_ticket"] == 123
        assert sent[1][1].direction == ("BUY" if mirrored else "SELL")
        assert sent[2][0] == "MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29"
        assert sent[2][1].direction == sent[1][1].direction
        assert not is_gold_m7(sent[2][1])


    copies=[(m,p) for m,p in sent if m == "MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29"]
    assert len(copies)==(1 if scenario=="accepted" else 0)
    if copies:
        assert copies[0][1].stop_management_parameters["execution_volume"]==(0.2 if mirrored else 0.1)
        assert copies[0][1].stop_management_parameters["m23_m29_pair_original_ticket"]=="123"
    if not own_m29:
        assert not any(m.startswith("MODELO_29_") for m,p in sent)
