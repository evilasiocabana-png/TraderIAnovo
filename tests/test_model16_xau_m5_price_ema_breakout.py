"""Testes do M16 XAUUSD/M5 sem acesso ao MT5 real."""

from __future__ import annotations

from types import SimpleNamespace

from application.dashboard_service import DashboardService
from application.demo_execution_service import DemoExecutionService
from application.model16_xau_m5_price_ema_breakout import (
    MODEL_16_BETA_ID,
    MODEL_16_ID,
    MODEL_16_STOP_MANAGEMENT,
    evaluate_model16_entry,
    model16_previous_candle_stop,
)
from application.position_manager_service import (
    PositionManagerService,
    PositionStateSnapshot,
    PositionTradePlan,
)
from domain.contracts.execution_order import ExecutionOrder
from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
)


def test_m16_buy_stop_quando_preco_acima_da_ema20() -> None:
    decision = evaluate_model16_entry(_entry_candles(uptrend=True, breakout=False))

    assert decision.ready
    assert decision.direction == "BUY"
    assert decision.status == "M16_BUY_STOP_PRONTA"
    assert decision.entry_price == 2010.01
    assert decision.initial_stop == 2005.0
    assert float(decision.current_price or 0.0) > float(decision.ema20 or 0.0)


def test_m16_sell_stop_quando_preco_abaixo_da_ema20() -> None:
    decision = evaluate_model16_entry(_entry_candles(uptrend=False, breakout=False))

    assert decision.ready
    assert decision.direction == "SELL"
    assert decision.status == "M16_SELL_STOP_PRONTA"
    assert decision.entry_price == 1999.99
    assert decision.initial_stop == 2005.0
    assert float(decision.current_price or 0.0) < float(decision.ema20 or 0.0)


def test_m16_nao_persegue_rompimento_ja_ocorrido() -> None:
    decision = evaluate_model16_entry(_entry_candles(uptrend=True, breakout=True))

    assert not decision.ready
    assert decision.status == "M16_BUY_STOP_PERDIDA"


def test_m16_stop_movel_usa_extremo_exato_do_candle_fechado() -> None:
    candles = [
        _candle(2000.0, 2004.0, 1999.0, 2003.0, 1),
        _candle(2003.0, 2010.0, 2005.0, 2008.0, 2),
        _candle(2008.0, 2012.0, 2007.0, 2011.0, 3),
    ]

    buy_stop, _ = model16_previous_candle_stop(candles, "BUY")
    sell_stop, _ = model16_previous_candle_stop(candles, "SELL")

    assert buy_stop == 2005.0
    assert sell_stop == 2010.0


def test_m16_esta_aposentado_com_seu_historico() -> None:
    assert not is_active_operational_model(MODEL_16_ID)
    assert is_retired_operational_model(MODEL_16_ID)
    assert is_retired_operational_model("MODELO_16_ALPHA012_VWAP_MEAN_REVERSION")


def test_m16_nao_exige_tp_fixo() -> None:
    order = ExecutionOrder(
        symbol="XAUUSD",
        side="BUY",
        quantity=0.01,
        entry_price=2010.01,
        stop=2005.0,
        target=0.0,
        operational_model=MODEL_16_ID,
    )

    assert DemoExecutionService()._has_required_stop_and_target(order)


def test_dashboard_m16_consume_snapshot_compartilhado_xauusd_m5() -> None:
    service = DashboardService.__new__(DashboardService)
    object.__setattr__(
        service,
        "mt5_market_data_service",
        SimpleNamespace(
            latest_forex_candles={
                ("XAUUSD", "M5"): _entry_candles(uptrend=True, breakout=False)
            }
        ),
    )

    decision = service.get_model16_entry_decision()

    assert decision.ready
    assert decision.direction == "BUY"


def test_position_manager_m16_move_sl_so_para_nivel_mais_protetivo() -> None:
    candles = [
        _candle(2000.0, 2004.0, 1999.0, 2003.0, 1),
        _candle(2003.0, 2010.0, 2005.0, 2008.0, 2),
        _candle(2008.0, 2012.0, 2007.0, 2011.0, 3),
    ]
    provider = SimpleNamespace(
        get_recent_candles=lambda symbol, timeframe, limit: candles
    )
    manager = PositionManagerService(
        provider=provider,
        assisted_execution_enabled=True,
    )
    plan = PositionTradePlan(
        symbol="XAUUSD",
        side="BUY",
        entry=2000.0,
        stop=1998.0,
        target=None,
        stop_management=MODEL_16_STOP_MANAGEMENT,
        beta_id=MODEL_16_BETA_ID,
        operational_model=MODEL_16_ID,
        timeframe="M5",
    )
    snapshot = PositionStateSnapshot(
        symbol="XAUUSD",
        ticket=16001,
        side="BUY",
        volume=0.01,
        entry_price=2000.0,
        current_price=2012.0,
        current_stop=1998.0,
        current_target=None,
        r_multiple=6.0,
        distance_to_target_r=None,
        time_in_position_minutes=10.0,
        atr=None,
        momentum=None,
        volatility=None,
        spread=None,
        state="TREND_RUNNER",
    )

    decision = manager._decide(plan, snapshot)

    assert decision.action == "PROTECT_POSITION"
    assert decision.requested_stop == 2005.0
    assert decision.beta_id == MODEL_16_BETA_ID


def _entry_candles(*, uptrend: bool, breakout: bool) -> list[dict[str, float]]:
    candles: list[dict[str, float]] = []
    start = 1980.0 if uptrend else 2020.0
    step = 1.0 if uptrend else -1.0
    for index in range(19):
        close = start + (step * index)
        candles.append(_candle(close - step, close + 0.5, close - 0.5, close, index))
    if uptrend:
        candles.append(_candle(2005.0, 2010.0, 2005.0, 2008.0, 19))
        high = 2010.02 if breakout else 2010.0
        candles.append(_candle(2008.0, high, 2007.0, 2009.0, 20))
    else:
        candles.append(_candle(2004.0, 2005.0, 2000.0, 2002.0, 19))
        low = 1999.98 if breakout else 2000.0
        candles.append(_candle(2002.0, 2003.0, low, 2001.0, 20))
    return candles


def _candle(
    open_price: float,
    high: float,
    low: float,
    close: float,
    index: int,
) -> dict[str, float]:
    return {
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "time": float(index),
    }
