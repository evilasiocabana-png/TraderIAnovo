from types import SimpleNamespace

import application.model26_xau_m5_smart_money as model26_module
from application.dashboard_service import DashboardService, MT5_OPERATIONAL_MODEL_26
from application.demo_execution_service import DemoExecutionService
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.model26_xau_m5_smart_money import (
    MODEL_26_CONTRACT_FINGERPRINT,
    MODEL_26_CONTINUATION_VOLUME,
    MODEL_26_ID,
    MODEL_26_LATERALIZATION_VOLUME,
    MODEL_26_STOP_MANAGEMENT,
    MODEL_26_SYMBOL,
    MODEL_26_TIMEFRAME,
    Model26Decision,
    evaluate_model26_entry,
    evaluate_model26_entries,
    evaluate_model26_exit,
    evolve_model26_exhaustion_state,
    model26_parameters,
)
from application.mt5_demo_robot_service import (
    MT5DemoRobotService,
    MT5DemoRobotSignal,
    MT5DemoTradePlan,
)
from domain.candle import Candle
from domain.contracts.execution_order import ExecutionOrder
from domain.operational_model_policy import is_active_operational_model, operational_model_number
from infrastructure.execution.mt5_demo_execution_provider import MT5DemoExecutionProvider
from research.mt5_research_trade_plan import MT5ResearchTradePlan


def _doji(index: int, price: float = 100.0) -> Candle:
    return Candle(str(index), price, price + 0.2, price - 0.2, price, 1)


def _green(index: int, open_price: float, close_price: float) -> Candle:
    return Candle(str(index), open_price, max(open_price, close_price) + 0.2, min(open_price, close_price) - 0.2, close_price, 1)


def _red(index: int, open_price: float, close_price: float) -> Candle:
    return _green(index, open_price, close_price)


def _continuation_buy_fixture() -> list[Candle]:
    rows = [_doji(index) for index in range(201)]
    rows[197] = _green(197, 100.0, 100.4)
    rows[198] = _green(198, 100.4, 100.8)
    rows[199] = _red(199, 100.8, 100.2)
    rows[200] = _doji(200, 100.2)
    return rows


def _mirror(rows: list[Candle]) -> list[Candle]:
    return [
        Candle(
            row.data,
            300.0 - row.abertura,
            300.0 - row.minima,
            300.0 - row.maxima,
            300.0 - row.fechamento,
            row.volume,
        )
        for row in rows
    ]


def _top_bottom_top_fixture() -> list[Candle]:
    rows = [_doji(index) for index in range(201)]
    pattern = [
        _green(184, 104, 106), _green(185, 106, 109),
        _red(186, 109, 108), _red(187, 108, 106),
        _red(188, 106, 103), _red(189, 103, 101),
        _green(190, 101, 102), _green(191, 102, 104),
        _green(192, 104, 106), _green(193, 106, 110),
        _red(194, 110, 108), _red(195, 108, 106),
    ]
    rows[184:196] = pattern
    return rows


def _lateralization_sell_fixture() -> list[Candle]:
    rows = [_doji(index) for index in range(201)]
    rows[188] = _red(188, 102.0, 100.0)
    rows[189] = _red(189, 100.0, 98.0)
    rows[190] = _green(190, 98.0, 99.0)
    rows[191] = _green(191, 99.0, 100.0)
    rows[197] = _doji(197, 101.0)
    rows[198] = _green(198, 101.0, 102.0)
    rows[199] = Candle("199", 102.0, 103.1, 101.8, 103.0, 1)
    rows[200] = _doji(200, 103.0)
    return rows


def _fallback_plan() -> MT5ResearchTradePlan:
    return MT5ResearchTradePlan(
        symbol="XAUUSD", timeframe="M5", direction="WAIT", entry_price=None,
        stop=None, target=None, risk_reward=0.0, stop_multiplier=0.0,
        exit_model="NONE", exit_score=0.0, exit_candidates=0, status="SEM_PLANO",
    )


def test_model26_contract_is_xauusd_m5() -> None:
    assert MODEL_26_ID == MT5_OPERATIONAL_MODEL_26
    assert MODEL_26_SYMBOL == "XAUUSD"
    assert MODEL_26_TIMEFRAME == "M5"
    assert MODEL_26_CONTINUATION_VOLUME == 0.01
    assert MODEL_26_LATERALIZATION_VOLUME == 0.02
    assert len(MODEL_26_CONTRACT_FINGERPRINT) == 16
    assert operational_model_number(MODEL_26_ID) == 26
    assert is_active_operational_model(MODEL_26_ID)


def test_model26_accepts_mt5_structured_candle_records() -> None:
    class StructuredCandle:
        dtype = SimpleNamespace(names=("time", "open", "high", "low", "close"))

        def __init__(self, candle: Candle) -> None:
            # np.void exposes ``data`` as a buffer even when the time field is
            # named ``time``. The adapter must prefer structured field names.
            self.data = memoryview(b"structured-record")
            self.values = {
                "time": candle.data,
                "open": candle.abertura,
                "high": candle.maxima,
                "low": candle.minima,
                "close": candle.fechamento,
            }

        def __getitem__(self, name: str) -> object:
            return self.values[name]

    rows = [StructuredCandle(candle) for candle in _continuation_buy_fixture()]
    rows[198] = StructuredCandle(_red(198, 103.0, 102.0))
    rows[199] = StructuredCandle(_red(199, 102.0, 101.0))

    decision = evaluate_model26_exit(rows, "BUY", reentry_route="CONTINUATION")

    assert decision.action == "FULL_EXIT"
    assert decision.closed_candle_time == "199"


def test_model26_buy_continuation_uses_red_candle_extremes() -> None:
    rows = _continuation_buy_fixture()
    decision = evaluate_model26_entry(rows)
    assert decision.ready
    assert decision.direction == "BUY"
    assert decision.signal_kind == "CONTINUATION"
    assert decision.entry_order_type == "BUY_STOP"
    assert decision.entry_price == rows[199].maxima
    assert decision.initial_stop == rows[199].minima - 0.01
    assert 50.0 < decision.rsi14 <= 70.0


def test_model26_sell_continuation_is_exact_mirror() -> None:
    rows = _mirror(_continuation_buy_fixture())
    decision = evaluate_model26_entry(rows)
    assert decision.ready
    assert decision.direction == "SELL"
    assert decision.signal_kind == "CONTINUATION"
    assert decision.entry_order_type == "SELL_STOP"
    assert decision.entry_price == rows[199].minima
    assert decision.initial_stop > decision.entry_price
    assert 30.0 <= decision.rsi14 < 50.0


def test_model26_sell_continuation_survives_one_cycle_after_breakout(
    monkeypatch,
) -> None:
    monkeypatch.setattr(model26_module, "_wilder_rsi", lambda *_args: 40.0)
    rows = _mirror(_continuation_buy_fixture())
    pause = rows[199]
    rows[200] = Candle(
        "200",
        pause.fechamento,
        pause.fechamento + 0.1,
        pause.minima - 0.2,
        pause.minima - 0.1,
        1,
    )
    rows.append(_doji(201, rows[200].fechamento))

    decision = evaluate_model26_entry(rows)

    assert decision.ready
    assert decision.direction == "SELL"
    assert decision.signal_kind == "CONTINUATION"
    assert decision.entry_order_type == "SELL_STOP"
    assert decision.entry_price == pause.minima
    assert decision.initial_stop == pause.maxima + 0.01
    assert decision.status == "M26_CONTINUATION_SELL_STOP_ROMPIDA_PRONTA"


def test_model26_buy_continuation_survives_one_cycle_after_breakout(
    monkeypatch,
) -> None:
    monkeypatch.setattr(model26_module, "_wilder_rsi", lambda *_args: 60.0)
    rows = _continuation_buy_fixture()
    pause = rows[199]
    rows[200] = Candle(
        "200",
        pause.fechamento,
        pause.maxima + 0.2,
        pause.fechamento - 0.1,
        pause.maxima + 0.1,
        1,
    )
    rows.append(_doji(201, rows[200].fechamento))

    decision = evaluate_model26_entry(rows)

    assert decision.ready
    assert decision.direction == "BUY"
    assert decision.signal_kind == "CONTINUATION"
    assert decision.entry_order_type == "BUY_STOP"
    assert decision.entry_price == pause.maxima
    assert decision.initial_stop == pause.minima - 0.01
    assert decision.status == "M26_CONTINUATION_BUY_STOP_ROMPIDA_PRONTA"


def test_model26_blocks_buy_continuation_above_rsi70() -> None:
    rows = [_doji(index) for index in range(201)]
    price = 100.0
    for index in range(186, 199):
        rows[index] = _green(index, price, price + 0.2)
        price += 0.2
    rows[199] = _red(199, price, price - 0.05)
    rows[200] = _doji(200, price - 0.05)

    decisions = evaluate_model26_entries(rows)

    assert all(decision.signal_kind != "CONTINUATION" for decision in decisions)


def test_model26_blocks_sell_continuation_below_rsi30() -> None:
    rows = _mirror([_doji(index) for index in range(201)])
    price = 200.0
    for index in range(186, 199):
        rows[index] = _red(index, price, price - 0.2)
        price -= 0.2
    rows[199] = _green(199, price, price + 0.05)
    rows[200] = _doji(200, price + 0.05)

    decisions = evaluate_model26_entries(rows)

    assert all(decision.signal_kind != "CONTINUATION" for decision in decisions)


def test_model26_exhaustion_sell_arms_on_rsi_cross_down_70(monkeypatch) -> None:
    rising = [_doji(index) for index in range(201)]
    price = 100.0
    for index in range(185, 200):
        rising[index] = _green(index, price, price + 0.2)
        price += 0.2
    rising[200] = _doji(200, price)
    readings = iter((75.0, 68.0))
    monkeypatch.setattr(
        model26_module,
        "_wilder_rsi",
        lambda _values, _period: next(readings),
    )
    state = evolve_model26_exhaustion_state(rising)
    assert state["sell_armed"] is True
    assert state["last_rsi14"] == 68.0
    assert state["sell_entry_price"] == rising[199].fechamento
    assert state["sell_initial_stop"] == rising[199].maxima

    monkeypatch.setattr(model26_module, "_wilder_rsi", lambda *_args: 68.0)
    decisions = evaluate_model26_entries(
        rising,
        exhaustion_state=state,
    )
    exhaustion = next(
        decision for decision in decisions
        if decision.signal_kind == "EXHAUSTION"
    )
    assert exhaustion.direction == "SELL"
    assert exhaustion.entry_order_type == "MARKET"
    assert exhaustion.initial_stop == rising[199].maxima
    assert exhaustion.last_swing_time == rising[199].data


def test_model26_exhaustion_buy_arms_on_rsi_cross_up_30(monkeypatch) -> None:
    falling = [_doji(index) for index in range(201)]
    price = 100.0
    for index in range(185, 200):
        falling[index] = _red(index, price, price - 0.2)
        price -= 0.2
    falling[200] = _doji(200, price)
    readings = iter((25.0, 32.0))
    monkeypatch.setattr(
        model26_module,
        "_wilder_rsi",
        lambda _values, _period: next(readings),
    )

    state = evolve_model26_exhaustion_state(falling)

    assert state["buy_armed"] is True
    assert state["sell_armed"] is False
    assert state["last_rsi14"] == 32.0
    assert state["buy_entry_price"] == falling[199].fechamento
    assert state["buy_initial_stop"] == falling[199].minima


def test_model26_latest_cross_replaces_stale_opposite_alert(monkeypatch) -> None:
    rising = [_doji(index) for index in range(201)]
    price = 100.0
    for index in range(185, 200):
        rising[index] = _green(index, price, price + 0.2)
        price += 0.2
    rising[200] = _doji(200, price)

    readings = iter((75.0, 68.0))
    monkeypatch.setattr(
        model26_module,
        "_wilder_rsi",
        lambda _values, _period: next(readings),
    )
    state = evolve_model26_exhaustion_state(
        rising,
        {
            "buy_armed": True,
            "buy_armed_at": "stale-buy-alert",
            "last_processed_closed_candle": "199",
            "contract_version": "M26_OLD_CONTRACT",
        },
    )

    assert state["sell_armed"] is True
    assert state["sell_armed_at"] != "N/D"
    assert state["buy_armed"] is False
    assert state["buy_armed_at"] == "N/D"


def test_model26_accepts_truth_ambiguous_mt5_candle_collection() -> None:
    class TruthAmbiguousRows(list):
        def __bool__(self) -> bool:
            raise ValueError("ambiguous truth value")

    rows = TruthAmbiguousRows(_continuation_buy_fixture())

    state = evolve_model26_exhaustion_state(rows)
    decisions = evaluate_model26_entries(rows, exhaustion_state=state)

    assert state["last_processed_closed_candle"] == "199"
    assert decisions


def test_model26_exhaustion_buy_is_exact_mirror() -> None:
    rows = _mirror(_continuation_buy_fixture())
    rows[198] = _green(198, 198.0, 199.0)
    rows[199] = _green(199, 199.0, 200.0)
    decisions = evaluate_model26_entries(
        rows,
        exhaustion_state={
            "buy_armed": True,
            "buy_armed_at": rows[199].data,
            "buy_entry_price": rows[199].fechamento,
            "buy_initial_stop": rows[199].minima,
        },
    )
    exhaustion = next(
        decision for decision in decisions
        if decision.signal_kind == "EXHAUSTION"
    )
    assert exhaustion.direction == "BUY"
    assert exhaustion.entry_order_type == "MARKET"
    assert exhaustion.initial_stop == rows[199].minima
    assert exhaustion.last_swing_time == rows[199].data


def test_model26_exhaustion_sell_exits_after_cross_down_and_return_over_50(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        model26_module,
        "_rsi_path",
        lambda _bars: [(197, 55.0), (198, 45.0), (199, 52.0)],
    )
    decision = evaluate_model26_exit(
        _continuation_buy_fixture(),
        "SELL",
        reentry_route="EXHAUSTION",
        entry_candle_time="197",
    )
    assert decision.action == "FULL_EXIT"
    assert decision.status == "M26_EXHAUSTION_SELL_RSI_RETURN_50"


def test_model26_exhaustion_buy_exits_after_cross_up_and_return_below_70(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        model26_module,
        "_rsi_path",
        lambda _bars: [(197, 65.0), (198, 74.0), (199, 68.0)],
    )
    decision = evaluate_model26_exit(
        _continuation_buy_fixture(),
        "BUY",
        reentry_route="EXHAUSTION",
        entry_candle_time="197",
    )
    assert decision.action == "FULL_EXIT"
    assert decision.status == "M26_EXHAUSTION_BUY_RSI_RETURN_70"


def test_model26_exhaustion_buy_trails_each_confirmed_bottom(monkeypatch) -> None:
    rows = _continuation_buy_fixture()
    rows[196] = Candle("196", 101.0, 101.4, 100.5, 101.1, 1)
    rows[197] = Candle("197", 101.1, 101.3, 99.4, 100.2, 1)
    rows[198] = Candle("198", 100.2, 102.0, 100.0, 101.8, 1)
    rows[199] = Candle("199", 101.8, 102.4, 101.2, 102.1, 1)
    rows[200] = _doji(200, 102.1)
    monkeypatch.setattr(
        model26_module,
        "_rsi_path",
        lambda _bars: [(195, 32.0), (196, 40.0), (197, 44.0), (198, 48.0), (199, 49.0)],
    )

    decision = evaluate_model26_exit(
        rows,
        "BUY",
        reentry_route="EXHAUSTION",
        entry_candle_time="195",
    )

    assert decision.action == "PROTECT_POSITION"
    assert decision.status == "M26_EXHAUSTION_BUY_TRAIL_STRUCTURE"
    assert decision.candidate_stop == rows[197].minima


def test_model26_exhaustion_sell_trails_each_confirmed_top(monkeypatch) -> None:
    rows = _continuation_buy_fixture()
    rows[196] = Candle("196", 99.0, 99.5, 98.6, 98.9, 1)
    rows[197] = Candle("197", 98.9, 100.8, 98.7, 100.1, 1)
    rows[198] = Candle("198", 100.1, 100.2, 98.2, 98.5, 1)
    rows[199] = Candle("199", 98.5, 99.0, 97.8, 98.0, 1)
    rows[200] = _doji(200, 98.0)
    monkeypatch.setattr(
        model26_module,
        "_rsi_path",
        lambda _bars: [(195, 68.0), (196, 61.0), (197, 57.0), (198, 53.0), (199, 51.0)],
    )

    decision = evaluate_model26_exit(
        rows,
        "SELL",
        reentry_route="EXHAUSTION",
        entry_candle_time="195",
    )

    assert decision.action == "PROTECT_POSITION"
    assert decision.status == "M26_EXHAUSTION_SELL_TRAIL_STRUCTURE"
    assert decision.candidate_stop == rows[197].maxima


def test_model26_two_green_arms_sell_stop_to_previous_bottom(
    monkeypatch,
) -> None:
    rows = _lateralization_sell_fixture()
    monkeypatch.setattr(model26_module, "_wilder_rsi", lambda *_args: 40.0)
    decision = next(
        item for item in evaluate_model26_entries(rows)
        if item.signal_kind == "LATERALIZATION"
    )
    assert decision.ready
    assert decision.signal_kind == "LATERALIZATION"
    assert decision.structure_sequence == "GREENx2"
    assert decision.direction == "SELL"
    assert decision.entry_order_type == "SELL_STOP"
    assert decision.entry_price == rows[199].minima
    assert decision.initial_stop == max(row.maxima for row in rows[198:200]) + 0.01
    assert decision.last_swing_price == max(
        row.maxima for row in rows[198:200]
    )
    assert decision.target == min(row.minima for row in rows[188:192])
    assert decision.target < decision.entry_price < decision.initial_stop


def test_model26_two_red_arms_buy_stop_to_previous_top(
    monkeypatch,
) -> None:
    rows = _mirror(_lateralization_sell_fixture())
    monkeypatch.setattr(model26_module, "_wilder_rsi", lambda *_args: 60.0)
    decision = next(
        item for item in evaluate_model26_entries(rows)
        if item.signal_kind == "LATERALIZATION"
    )
    assert decision.ready
    assert decision.signal_kind == "LATERALIZATION"
    assert decision.structure_sequence == "REDx2"
    assert decision.direction == "BUY"
    assert decision.entry_order_type == "BUY_STOP"
    assert decision.entry_price == rows[199].maxima
    assert decision.initial_stop == min(row.minima for row in rows[198:200]) - 0.01
    assert decision.last_swing_price == min(
        row.minima for row in rows[198:200]
    )
    assert decision.target == max(row.maxima for row in rows[188:192])
    assert decision.initial_stop < decision.entry_price < decision.target


def test_model26_lateralization_blocks_buy_outside_rsi_band() -> None:
    bars = [model26_module._bar(row) for row in _mirror(_lateralization_sell_fixture())[:-1]]

    decision = model26_module._lateralization_decision(
        bars,
        {"rsi14": 70.01},
    )

    assert decision is None


def test_model26_lateralization_blocks_sell_outside_rsi_band() -> None:
    bars = [model26_module._bar(row) for row in _lateralization_sell_fixture()[:-1]]

    decision = model26_module._lateralization_decision(
        bars,
        {"rsi14": 29.99},
    )

    assert decision is None


def test_model26_rsi_band_blocks_conflicting_lateralization_route(monkeypatch) -> None:
    rows = _lateralization_sell_fixture()
    monkeypatch.setattr(model26_module, "_wilder_rsi", lambda *_args: 55.0)

    decisions = evaluate_model26_entries(rows)

    assert all(decision.signal_kind != "LATERALIZATION" for decision in decisions)
    assert model26_parameters()["entry_routes_are_mutually_exclusive"] is False
    assert model26_parameters()["entry_routes_can_coexist"] is True


def test_model26_continuation_moves_stop_after_confirmed_pullback() -> None:
    rows = _continuation_buy_fixture()
    rows[198] = _red(198, 101.0, 100.4)
    rows[199] = _green(199, 100.4, 101.2)
    decision = evaluate_model26_exit(rows, "BUY", reentry_route="CONTINUATION")
    assert decision.action == "PROTECT_POSITION"
    assert decision.candidate_stop == rows[198].minima - 0.01


def test_model26_continuation_uses_latest_pause_since_entry(monkeypatch) -> None:
    rows = _continuation_buy_fixture()
    rows[195] = _red(195, 101.0, 100.4)
    rows[196] = _green(196, 100.4, 101.2)
    rows[197] = _green(197, 101.2, 102.0)
    rows[198] = _red(198, 102.0, 101.4)
    rows[199] = _green(199, 101.4, 102.3)
    rows[200] = _doji(200, 102.3)
    monkeypatch.setattr(
        model26_module,
        "_rsi_path",
        lambda _bars: [
            (194, 52.0),
            (195, 54.0),
            (196, 56.0),
            (197, 58.0),
            (198, 60.0),
            (199, 62.0),
        ],
    )

    decision = evaluate_model26_exit(
        rows,
        "BUY",
        reentry_route="CONTINUATION",
        entry_candle_time="194",
    )

    assert decision.action == "PROTECT_POSITION"
    assert decision.candidate_stop == rows[198].minima - 0.01


def test_model26_buy_continuation_full_exit_after_rsi70_return(monkeypatch) -> None:
    monkeypatch.setattr(
        model26_module,
        "_rsi_path",
        lambda _bars: [(197, 62.0), (198, 74.0), (199, 68.0)],
    )

    decision = evaluate_model26_exit(
        _continuation_buy_fixture(),
        "BUY",
        reentry_route="CONTINUATION",
        entry_candle_time="197",
    )

    assert decision.action == "FULL_EXIT"
    assert decision.status == "M26_CONTINUATION_BUY_RSI_RETURN_70"


def test_model26_sell_continuation_full_exit_after_rsi30_return(monkeypatch) -> None:
    monkeypatch.setattr(
        model26_module,
        "_rsi_path",
        lambda _bars: [(197, 38.0), (198, 26.0), (199, 32.0)],
    )

    decision = evaluate_model26_exit(
        _mirror(_continuation_buy_fixture()),
        "SELL",
        reentry_route="CONTINUATION",
        entry_candle_time="197",
    )

    assert decision.action == "FULL_EXIT"
    assert decision.status == "M26_CONTINUATION_SELL_RSI_RETURN_30"


def test_model26_continuation_full_exit_after_two_opposite_candles() -> None:
    rows = _continuation_buy_fixture()
    rows[198] = _red(198, 103.0, 102.0)
    rows[199] = _red(199, 102.0, 101.0)
    decision = evaluate_model26_exit(rows, "BUY", reentry_route="CONTINUATION")
    assert decision.action == "FULL_EXIT"
    assert decision.status == "M26_CONTINUATION_EXIT_DOIS_VERMELHOS_BUY"


def test_model26_range_preserves_fixed_sl_tp() -> None:
    decision = evaluate_model26_exit(
        _lateralization_sell_fixture(), "BUY", reentry_route="LATERALIZATION"
    )
    assert decision.action == "HOLD_POSITION"
    assert decision.status == "M26_RANGE_HOLD_SL_TP"


def test_model26_materializes_lateralization_plan() -> None:
    service = object.__new__(DashboardService)
    decision = Model26Decision(
        direction="BUY", status="M26_LATERALIZATION_BUY_STOP_PRONTA",
        reason="teste", signal_kind="LATERALIZATION", entry_order_type="BUY_STOP",
        current_candle_time="200", closed_candle_time="199", entry_price=101.0,
        initial_stop=99.99, target=110.0, risk_reward=8.91,
        range_low=99.99, range_high=110.0, structure_sequence="REDx2",
        setup_id="M26|LATERALIZATION|BUY|199",
    )
    object.__setattr__(service, "_get_model26_entry_decision", lambda: decision)
    _, plan = service._mt5_model26_smart_money_plan(
        DashboardMT5ForexSignalRowViewModel(pair="XAUUSD", timeframe="M5"),
        _fallback_plan(),
    )
    assert plan.status == "PLANO_VALIDO"
    assert plan.stop_management == MODEL_26_STOP_MANAGEMENT
    assert plan.target == 110.0
    assert plan.stop_management_parameters["active_entry_order_type"] == "BUY_STOP"
    assert plan.stop_management_parameters["execution_volume"] == 0.02


def test_service_materializes_both_model26_routes_in_same_cycle() -> None:
    service = object.__new__(DashboardService)
    continuation = evaluate_model26_entry(_continuation_buy_fixture())
    lateralization = model26_module._lateralization_decision(
        [model26_module._bar(row) for row in _lateralization_sell_fixture()[:-1]],
        {"rsi14": 40.0, "current_candle_time": "200", "closed_candle_time": "199"},
    )
    assert lateralization is not None
    object.__setattr__(
        service,
        "_get_model26_entry_decisions",
        lambda: (continuation, lateralization),
    )

    plans = service._mt5_model26_smart_money_plans(
        DashboardMT5ForexSignalRowViewModel(pair="XAUUSD", timeframe="M5"),
        _fallback_plan(),
    )

    assert len(plans) == 2
    routes = {
        plan.stop_management_parameters["active_signal_kind"]
        for _row, plan in plans
    }
    assert routes == {"CONTINUATION", "LATERALIZATION"}


def test_service_does_not_materialize_model26_routes_for_another_pair() -> None:
    service = object.__new__(DashboardService)
    continuation = evaluate_model26_entry(_continuation_buy_fixture())
    lateralization = model26_module._lateralization_decision(
        [model26_module._bar(row) for row in _lateralization_sell_fixture()[:-1]],
        {"rsi14": 40.0, "current_candle_time": "200", "closed_candle_time": "199"},
    )
    assert lateralization is not None
    object.__setattr__(
        service,
        "_get_model26_entry_decisions",
        lambda: (continuation, lateralization),
    )

    plans = service._mt5_model26_smart_money_plans(
        DashboardMT5ForexSignalRowViewModel(pair="EURUSD", timeframe="H1"),
        _fallback_plan(),
    )

    assert plans == ()


def test_robot_selects_volume_by_model26_route() -> None:
    robot = object.__new__(MT5DemoRobotService)
    robot.volume = 0.99
    signal = SimpleNamespace(operational_model=MODEL_26_ID)
    continuation = SimpleNamespace(
        operational_model=MODEL_26_ID,
        stop_management_parameters={"active_signal_kind": "CONTINUATION"},
    )
    lateralization = SimpleNamespace(
        operational_model=MODEL_26_ID,
        stop_management_parameters={"active_signal_kind": "LATERALIZATION"},
    )
    assert robot._execution_volume(signal, continuation) == 0.01
    assert robot._execution_volume(signal, lateralization) == 0.02


def test_robot_does_not_reapply_legacy_regime_to_model26() -> None:
    robot = object.__new__(MT5DemoRobotService)
    signal = SimpleNamespace(operational_model=MODEL_26_ID)

    assert robot._regime_validation_signal(signal) is None


def test_robot_deduplicates_model26_per_route_instead_of_whole_model() -> None:
    robot = object.__new__(MT5DemoRobotService)
    common = {
        "symbol": "XAUUSD",
        "timeframe": "M5",
        "operational_model": MODEL_26_ID,
    }
    continuation = SimpleNamespace(**common, entry_route="CONTINUATION")
    lateralization = SimpleNamespace(**common, entry_route="LATERALIZATION")
    exhaustion = SimpleNamespace(**common, entry_route="EXHAUSTION")

    assert robot._execution_key(continuation) != robot._execution_key(lateralization)
    assert robot._execution_key(continuation) != robot._execution_key(exhaustion)
    assert robot._execution_key(lateralization) != robot._execution_key(exhaustion)
    assert robot._execution_key(continuation)[-1] == "CONTINUATION"


def test_model26_trade_plan_identity_and_snapshot_include_route() -> None:
    robot = object.__new__(MT5DemoRobotService)
    common = {
        "symbol": "XAUUSD",
        "timeframe": "M5",
        "candle_time": "2026-08-27T05:00:00+00:00",
        "decision": "BUY",
        "confidence": 1.0,
        "active_model": "M26_CANDLE_CONTINUATION_OR_RANGE",
        "reason": "rota pronta",
        "operational_model": MODEL_26_ID,
    }
    continuation = MT5DemoRobotSignal(
        **common,
        entry_route="CONTINUATION",
        setup_id="M26|CONTINUATION|BUY|500",
    )
    lateralization = MT5DemoRobotSignal(
        **common,
        entry_route="LATERALIZATION",
        setup_id="M26|LATERALIZATION|BUY|500",
    )
    plan = MT5DemoTradePlan(
        symbol="XAUUSD",
        timeframe="M5",
        entry_price=100.0,
        stop=99.0,
        target=0.0,
        risk_reward=0.0,
        source="MODEL_26_CANDLE_SEQUENCE_RULE",
        operational_model=MODEL_26_ID,
        stop_management_parameters={"active_signal_kind": "CONTINUATION"},
    )

    continuation_identity = robot._trade_plan_identity(continuation, plan)
    lateralization_identity = robot._trade_plan_identity(lateralization, plan)
    snapshot = robot._trade_plan_snapshot(continuation, plan, "BUY")

    assert continuation_identity != lateralization_identity
    assert "CONTINUATION" in continuation_identity
    assert snapshot["entry_route"] == "CONTINUATION"
    assert snapshot["setup_id"] == "M26|CONTINUATION|BUY|500"


def test_model26_route_key_is_stable_per_route_and_direction() -> None:
    buy = Model26Decision(signal_kind="CONTINUATION", direction="BUY")
    sell = Model26Decision(signal_kind="CONTINUATION", direction="SELL")
    range_buy = Model26Decision(signal_kind="LATERALIZATION", direction="BUY")

    assert buy.route_key == "M26:CONTINUATION:BUY"
    assert sell.route_key == "M26:CONTINUATION:SELL"
    assert range_buy.route_key == "M26:LATERALIZATION:BUY"


def test_dashboard_transports_model26_route_identity_to_robot_signal() -> None:
    service = object.__new__(DashboardService)
    object.__setattr__(
        service,
        "configuration_service",
        SimpleNamespace(
            get_configuration_data=lambda: SimpleNamespace(
                forex_session_filter_enabled=False,
            )
        ),
    )
    row = DashboardMT5ForexSignalRowViewModel(
        pair="XAUUSD",
        timeframe="M5",
        decision="BUY",
        active_model="M26_CANDLE_CONTINUATION_OR_RANGE",
        reason="continuidade pronta",
        lab_parameters={
            "active_signal_kind": "CONTINUATION",
            "setup_id": "M26|CONTINUATION|BUY|123",
        },
    )
    context = SimpleNamespace(
        temporal_blocked=False,
        temporal_status="OK",
    )

    signal = service._mt5_demo_signal_from_view_row(
        row,
        candle_time="123",
        time_context=context,
        operational_model=MODEL_26_ID,
    )

    assert signal.entry_route == "CONTINUATION"
    assert signal.setup_id == "M26|CONTINUATION|BUY|123"


def test_model26_rejects_inverted_stop_before_plan_materialization() -> None:
    invalid_buy = Model26Decision(
        direction="BUY",
        signal_kind="CONTINUATION",
        entry_order_type="BUY_STOP",
        entry_price=100.0,
        initial_stop=101.0,
    )
    invalid_sell = Model26Decision(
        direction="SELL",
        signal_kind="EXHAUSTION",
        entry_order_type="MARKET",
        entry_price=100.0,
        initial_stop=99.0,
    )

    assert model26_module._validate_entry_decision(invalid_buy) is None
    assert model26_module._validate_entry_decision(invalid_sell) is None


def test_provider_builds_real_buy_stop_request_for_model26() -> None:
    provider = object.__new__(MT5DemoExecutionProvider)
    provider.deviation = 20
    provider.magic = 1
    provider.mt5 = SimpleNamespace(
        ORDER_TYPE_BUY=0, ORDER_TYPE_SELL=1,
        ORDER_TYPE_BUY_LIMIT=2, ORDER_TYPE_SELL_LIMIT=3,
        ORDER_TYPE_BUY_STOP=4, ORDER_TYPE_SELL_STOP=5,
        TRADE_ACTION_DEAL=10, TRADE_ACTION_PENDING=11,
        ORDER_TIME_GTC=20, ORDER_TIME_SPECIFIED=21,
        ORDER_FILLING_RETURN=30, ORDER_FILLING_IOC=31,
    )
    order = ExecutionOrder(
        symbol="XAUUSD", side="BUY", quantity=0.02, entry_price=100.0,
        stop=99.99, target=110.0, operational_model=MODEL_26_ID,
        plan_snapshot={
            "timeframe": "M5",
            "stop_management_parameters": {
                "active_entry_order_type": "BUY_STOP",
                "active_signal_kind": "LATERALIZATION",
            },
        },
    )
    request = provider._request(order, SimpleNamespace(ask=95.0, bid=94.9, time=1))
    assert request["action"] == 11
    assert request["type"] == 4
    assert request["price"] == 100.0
    assert request["volume"] == 0.02
    assert request["tp"] == 110.0


def test_provider_executes_model26_continuation_directly_at_market() -> None:
    provider = object.__new__(MT5DemoExecutionProvider)
    provider.deviation = 20
    provider.magic = 1
    provider.mt5 = SimpleNamespace(
        ORDER_TYPE_BUY=0, ORDER_TYPE_SELL=1,
        ORDER_TYPE_BUY_LIMIT=2, ORDER_TYPE_SELL_LIMIT=3,
        ORDER_TYPE_BUY_STOP=4, ORDER_TYPE_SELL_STOP=5,
        TRADE_ACTION_DEAL=10, TRADE_ACTION_PENDING=11,
        ORDER_TIME_GTC=20, ORDER_TIME_SPECIFIED=21,
        ORDER_FILLING_RETURN=30, ORDER_FILLING_IOC=31,
    )
    order = ExecutionOrder(
        symbol="XAUUSD", side="BUY", quantity=0.01, entry_price=100.0,
        stop=99.0, target=0.0, operational_model=MODEL_26_ID,
        plan_snapshot={
            "timeframe": "M5",
            "stop_management_parameters": {
                "active_entry_order_type": "MARKET",
                "active_signal_kind": "CONTINUATION",
            },
        },
    )

    request = provider._request(
        order,
        SimpleNamespace(ask=100.5, bid=100.4, time=1),
    )

    assert request["action"] == 10
    assert request["type"] == 0
    assert request["price"] == 100.5
    assert request["volume"] == 0.01


def test_provider_identifies_model26_routes_with_distinct_comments() -> None:
    provider = object.__new__(MT5DemoExecutionProvider)
    continuation = ExecutionOrder(
        symbol="XAUUSD", side="BUY", quantity=0.01, entry_price=100.0,
        stop=99.0, target=0.0, operational_model=MODEL_26_ID,
        plan_snapshot={
            "timeframe": "M5",
            "stop_management_parameters": {
                "active_entry_order_type": "MARKET",
                "active_signal_kind": "CONTINUATION",
            },
        },
    )
    lateralization = ExecutionOrder(
        symbol="XAUUSD", side="BUY", quantity=0.02, entry_price=95.0,
        stop=94.0, target=105.0, operational_model=MODEL_26_ID,
        plan_snapshot={
            "timeframe": "M5",
            "stop_management_parameters": {
                "active_entry_order_type": "BUY_STOP",
                "active_signal_kind": "LATERALIZATION",
            },
        },
    )
    exhaustion = ExecutionOrder(
        symbol="XAUUSD", side="SELL", quantity=0.01, entry_price=94.0,
        stop=96.0, target=0.0, operational_model=MODEL_26_ID,
        plan_snapshot={
            "timeframe": "M5",
            "stop_management_parameters": {
                "active_entry_order_type": "MARKET",
                "active_signal_kind": "EXHAUSTION",
            },
        },
    )

    assert provider._order_comment(continuation) == "TraderIA M26 CONT"
    assert provider._order_comment(lateralization) == "TraderIA M26 LAT"
    assert provider._order_comment(exhaustion) == "TraderIA M26 EXH"

    provider.mt5 = SimpleNamespace(
        positions_get=lambda **_kwargs: [
            SimpleNamespace(comment="TraderIA M26 CONT")
        ]
    )
    assert provider._open_position_model_limit_preflight(lateralization) is None
    rejection = provider._open_position_model_limit_preflight(continuation)
    assert rejection is not None
    assert rejection.accepted is False
    assert "CONT" in rejection.message

    provider.mt5 = SimpleNamespace(
        positions_get=lambda **_kwargs: [
            SimpleNamespace(comment="TraderIA M26 EXH")
        ]
    )
    assert provider._open_position_model_limit_preflight(continuation) is None
    exhaustion_rejection = provider._open_position_model_limit_preflight(exhaustion)
    assert exhaustion_rejection is not None
    assert "EXH" in exhaustion_rejection.message

    provider._read_execution_log_records = lambda: [
        {
            "ticket": 123,
            "plan_snapshot": {
                "stop_management_parameters": {
                    "active_signal_kind": "LATERALIZATION"
                }
            },
        }
    ]
    assert provider._legacy_model26_ticket_route(
        SimpleNamespace(ticket=123)
    ) == "LAT"


def test_demo_service_does_not_turn_external_probe_failure_into_m26_duplicate() -> None:
    class FailingProbeProvider:
        def has_open_position_for_model(self, *_args: object) -> bool:
            raise AssertionError("M26 must reach the provider atomic preflight")

    service = object.__new__(DemoExecutionService)
    service.provider = FailingProbeProvider()
    service.pending_audit_metadata = {}
    order = ExecutionOrder(
        symbol="XAUUSD", side="SELL", quantity=0.01, entry_price=94.0,
        stop=96.0, target=0.0, operational_model=MODEL_26_ID,
        plan_snapshot={
            "timeframe": "M5",
            "stop_management_parameters": {
                "active_entry_order_type": "MARKET",
                "active_signal_kind": "EXHAUSTION",
            },
        },
    )

    assert service._has_open_position_for_same_model(order) is False
