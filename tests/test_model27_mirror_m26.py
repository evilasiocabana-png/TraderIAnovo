from types import SimpleNamespace

from application.dashboard_service import (
    DashboardService,
    MT5_OPERATIONAL_MODEL_26,
    MT5_OPERATIONAL_MODEL_27,
    MT5_SELECTABLE_OPERATIONAL_MODEL_IDS,
)
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.model27_mirror_m26 import (
    MODEL_27_ALPHA_ID,
    MODEL_27_BETA_ID,
    MODEL_27_ID,
    MODEL_27_SOURCE,
    MODEL_27_STOP_MANAGEMENT,
    MODEL_27_VOLUME,
    mirror_model26_geometry,
    mirror_model26_order_type,
)
from application.mt5_demo_robot_service import MT5DemoRobotService
from infrastructure.execution.mt5_demo_execution_provider import MT5DemoExecutionProvider
from domain.operational_model_policy import is_active_operational_model
from research.mt5_research_trade_plan import MT5ResearchTradePlan


def _source_plan(
    direction: str = "BUY",
    order_type: str = "BUY_STOP",
    route: str = "CONTINUATION",
) -> MT5ResearchTradePlan:
    entry = 3000.0
    stop = 2990.0 if direction == "BUY" else 3010.0
    return MT5ResearchTradePlan(
        symbol="XAUUSD",
        timeframe="M5",
        direction=direction,
        entry_price=entry,
        stop=stop,
        target=0.0,
        risk_reward=0.0,
        stop_multiplier=0.0,
        exit_model="M26_EXIT",
        exit_score=100.0,
        exit_candidates=1,
        status="PLANO_VALIDO",
        source="MODEL_26_CANDLE_SEQUENCE_RULE",
        alpha_id="ALPHA026",
        beta_id="BETA026",
        stop_management_parameters={
            "active_entry_order_type": order_type,
            "active_signal_kind": route,
            "route_key": f"M26_{route}",
        },
    )


def test_model27_geometry_is_exact_rr1_mirror() -> None:
    sell = mirror_model26_geometry("BUY", 3000.0, 2990.0)
    buy = mirror_model26_geometry("SELL", 3000.0, 3010.0)

    assert (sell.direction, sell.target, sell.stop) == ("SELL", 2990.0, 3010.0)
    assert (buy.direction, buy.target, buy.stop) == ("BUY", 3010.0, 2990.0)
    assert sell.risk_reward == buy.risk_reward == 1.0


def test_model27_mirrors_every_pending_order_type() -> None:
    assert mirror_model26_order_type("MARKET") == "MARKET"
    assert mirror_model26_order_type("BUY_STOP") == "SELL_LIMIT"
    assert mirror_model26_order_type("SELL_STOP") == "BUY_LIMIT"
    assert mirror_model26_order_type("BUY_LIMIT") == "SELL_STOP"
    assert mirror_model26_order_type("SELL_LIMIT") == "BUY_STOP"


def test_dashboard_materializes_model27_from_model26_route() -> None:
    service = object.__new__(DashboardService)
    source_row = DashboardMT5ForexSignalRowViewModel(
        pair="XAUUSD",
        timeframe="M5",
        decision="BUY",
        theoretical_entry_direction="BUY",
    )

    row, plan = service._mt5_model27_mirror_from_source(
        source_row,
        _source_plan(),
    )

    assert row.decision == "SELL"
    assert plan.direction == "SELL"
    assert plan.entry_price == 3000.0
    assert plan.target == 2990.0
    assert plan.stop == 3010.0
    assert plan.risk_reward == 1.0
    assert plan.source == MODEL_27_SOURCE
    assert plan.alpha_id == MODEL_27_ALPHA_ID
    assert plan.beta_id == MODEL_27_BETA_ID
    assert plan.stop_management == MODEL_27_STOP_MANAGEMENT
    assert plan.stop_management_parameters["active_entry_order_type"] == "SELL_LIMIT"
    assert plan.stop_management_parameters["execution_volume"] == 0.03


def test_model27_preserves_routes_and_uses_fixed_volume() -> None:
    service = object.__new__(DashboardService)
    rows_and_plans = tuple(
        service._mt5_model27_mirror_from_source(
            DashboardMT5ForexSignalRowViewModel(pair="XAUUSD", timeframe="M5"),
            _source_plan(route=route),
        )
        for route in ("CONTINUATION", "LATERALIZATION", "EXHAUSTION")
    )
    assert {
        plan.stop_management_parameters["active_signal_kind"]
        for _row, plan in rows_and_plans
    } == {"CONTINUATION", "LATERALIZATION", "EXHAUSTION"}

    robot = object.__new__(MT5DemoRobotService)
    robot.volume = 0.99
    signal = SimpleNamespace(operational_model=MODEL_27_ID)
    assert robot._execution_volume(signal, rows_and_plans[0][1]) == MODEL_27_VOLUME


def test_model27_is_selectable_and_has_independent_route_comments() -> None:
    assert MODEL_27_ID == MT5_OPERATIONAL_MODEL_27
    assert is_active_operational_model(MODEL_27_ID)
    assert MT5_OPERATIONAL_MODEL_27 in MT5_SELECTABLE_OPERATIONAL_MODEL_IDS
    assert MT5_OPERATIONAL_MODEL_26 != MT5_OPERATIONAL_MODEL_27

    provider = object.__new__(MT5DemoExecutionProvider)
    order = SimpleNamespace(
        operational_model=MODEL_27_ID,
        plan_snapshot={
            "stop_management_parameters": {
                "active_signal_kind": "LATERALIZATION",
            }
        },
    )
    assert provider._model_comment(MODEL_27_ID) == "M27"
    assert provider._order_comment(order) == "TraderIA M27 LAT"
