"""Testes do M15 XAUUSD/M5 sem acesso ao MT5 real ou Demo."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from application.demo_execution_service import DemoExecutionService
from application.dashboard_service import DashboardService
from application.model15_xau_m5_breakout import (
    MODEL_15_BETA_ID,
    MODEL_15_ID,
    MODEL_15_STOP_MANAGEMENT,
    evaluate_model15_entry,
    model15_previous_candle_stop,
)
from application.position_manager_service import (
    PositionManagerService,
    PositionTradePlan,
)
from domain.contracts.execution_order import ExecutionOrder
from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
)


class Model15EntryTest(unittest.TestCase):
    def test_buy_stop_um_pip_acima_da_maxima_anterior(self) -> None:
        candles = _entry_candles(uptrend=True, breakout=False)

        decision = evaluate_model15_entry(candles)

        self.assertTrue(decision.ready)
        self.assertEqual(decision.direction, "BUY")
        self.assertEqual(decision.status, "M15_BUY_STOP_PRONTA")
        self.assertAlmostEqual(decision.entry_price or 0.0, 2010.01)
        self.assertAlmostEqual(decision.initial_stop or 0.0, 2005.0)

    def test_sell_stop_um_pip_abaixo_da_minima_anterior(self) -> None:
        candles = _entry_candles(uptrend=False, breakout=False)

        decision = evaluate_model15_entry(candles)

        self.assertTrue(decision.ready)
        self.assertEqual(decision.direction, "SELL")
        self.assertEqual(decision.status, "M15_SELL_STOP_PRONTA")
        self.assertAlmostEqual(decision.entry_price or 0.0, 1999.99)
        self.assertAlmostEqual(decision.initial_stop or 0.0, 2005.0)

    def test_rompimento_ja_ocorrido_nao_persegue_preco(self) -> None:
        decision = evaluate_model15_entry(
            _entry_candles(uptrend=True, breakout=True)
        )

        self.assertFalse(decision.ready)
        self.assertEqual(decision.status, "M15_BUY_STOP_PERDIDA")

    def test_stop_movel_usa_extremo_exato_do_candle_anterior(self) -> None:
        candles = [
            _candle(2000.0, 2004.0, 1999.0, 2003.0, 1),
            _candle(2003.0, 2010.0, 2005.0, 2008.0, 2),
            _candle(2008.0, 2012.0, 2007.0, 2011.0, 3),
        ]

        buy_stop, _ = model15_previous_candle_stop(candles, "BUY")
        sell_stop, _ = model15_previous_candle_stop(candles, "SELL")

        self.assertAlmostEqual(buy_stop or 0.0, 2005.0)
        self.assertAlmostEqual(sell_stop or 0.0, 2010.0)

    def test_m15_esta_aposentado_com_seu_historico(self) -> None:
        self.assertFalse(is_active_operational_model(MODEL_15_ID))
        self.assertTrue(is_retired_operational_model(MODEL_15_ID))
        self.assertTrue(
            is_retired_operational_model("MODELO_15_ALPHA008_MACD_CONFIRMATION")
        )


class Model15ExecutionContractTest(unittest.TestCase):
    def test_dashboard_consume_snapshot_xauusd_m5_compartilhado(self) -> None:
        service = DashboardService.__new__(DashboardService)
        object.__setattr__(
            service,
            "mt5_market_data_service",
            SimpleNamespace(
                latest_forex_candles={
                    ("XAUUSD", "M5"): _entry_candles(
                        uptrend=True,
                        breakout=False,
                    )
                }
            ),
        )

        decision = service.get_model15_entry_decision()

        self.assertTrue(decision.ready)
        self.assertEqual(decision.direction, "BUY")

    def test_dashboard_nao_aceita_m15_para_novas_entradas(self) -> None:
        service = DashboardService.__new__(DashboardService)
        object.__setattr__(service, "mt5_operational_model", "MODELO_1_ALPHA_ATUAL")

        service.set_mt5_operational_model(MODEL_15_ID)

        self.assertEqual(service.get_mt5_operational_model(), "MODELO_1_ALPHA_ATUAL")

    def test_ordem_m15_nao_exige_tp_fixo(self) -> None:
        order = ExecutionOrder(
            symbol="XAUUSD",
            side="BUY",
            quantity=0.01,
            entry_price=2010.01,
            stop=2005.0,
            target=0.0,
            operational_model=MODEL_15_ID,
        )

        self.assertTrue(DemoExecutionService()._has_required_stop_and_target(order))

    def test_position_manager_move_buy_e_nunca_afasta_stop(self) -> None:
        candles = [
            _candle(2000.0, 2004.0, 1999.0, 2003.0, 1),
            _candle(2003.0, 2010.0, 2005.0, 2008.0, 2),
            _candle(2008.0, 2012.0, 2007.0, 2011.0, 3),
        ]
        provider = _Provider("BUY", stop=1998.0, price=2012.0, candles=candles)
        manager = _manager(provider)

        moved = manager.manage_plan(_plan("BUY", stop=1998.0))
        provider.position.sl = 2006.0
        held = manager.manage_plan(_plan("BUY", stop=1998.0))

        self.assertEqual(moved.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.first_modified_stop or 0.0, 2005.0)
        self.assertEqual(held.action, "HOLD_POSITION")
        self.assertEqual(provider.modify_calls, 1)
        self.assertEqual(provider.close_calls, 0)

    def test_position_manager_move_sell_para_baixo(self) -> None:
        candles = [
            _candle(2020.0, 2022.0, 2018.0, 2019.0, 1),
            _candle(2019.0, 2010.0, 2005.0, 2007.0, 2),
            _candle(2007.0, 2008.0, 2000.0, 2002.0, 3),
        ]
        provider = _Provider("SELL", stop=2020.0, price=2002.0, candles=candles)

        result = _manager(provider).manage_plan(_plan("SELL", stop=2020.0))

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop or 0.0, 2010.0)
        self.assertEqual(provider.close_calls, 0)


def _entry_candles(*, uptrend: bool, breakout: bool) -> list[dict[str, float]]:
    candles: list[dict[str, float]] = []
    start = 1950.0 if uptrend else 2050.0
    step = 1.0 if uptrend else -1.0
    for index in range(49):
        close = start + (step * index)
        candles.append(_candle(close - step, close + 0.5, close - 0.5, close, index))
    if uptrend:
        candles.append(_candle(2005.0, 2010.0, 2005.0, 2008.0, 49))
        high = 2010.02 if breakout else 2010.0
        candles.append(_candle(2008.0, high, 2007.0, 2009.0, 50))
    else:
        candles.append(_candle(2004.0, 2005.0, 2000.0, 2002.0, 49))
        low = 1999.98 if breakout else 2000.0
        candles.append(_candle(2002.0, 2003.0, low, 2001.0, 50))
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


def _plan(side: str, *, stop: float) -> PositionTradePlan:
    return PositionTradePlan(
        symbol="XAUUSD",
        side=side,
        entry=2010.01 if side == "BUY" else 1999.99,
        stop=stop,
        target=None,
        stop_management=MODEL_15_STOP_MANAGEMENT,
        alpha_id="ALPHAXAU15_EMA_BREAKOUT",
        beta_id=MODEL_15_BETA_ID,
        beta_version="M15_EXIT_V1",
        beta_mode="TRAILING_ONLY",
        timeframe="M5",
        operational_model=MODEL_15_ID,
    )


def _manager(provider: "_Provider") -> PositionManagerService:
    base = Path(tempfile.gettempdir())
    return PositionManagerService(
        provider=provider,
        assisted_execution_enabled=True,
        early_exit_enabled=True,
        log_path=base / "traderia-m15-position-manager-test.jsonl",
        state_path=base / "traderia-m15-position-manager-state-test.json",
        current_state_path=base / "traderia-m15-position-manager-current-test.json",
    )


class _Provider:
    def __init__(
        self,
        side: str,
        *,
        stop: float,
        price: float,
        candles: list[dict[str, float]],
    ) -> None:
        self.position = SimpleNamespace(
            ticket=15001,
            symbol="XAUUSD",
            side=side,
            type=0 if side == "BUY" else 1,
            price_open=2010.01 if side == "BUY" else 1999.99,
            sl=stop,
            tp=0.0,
            volume=0.01,
        )
        self.price = price
        self.candles = candles
        self.modified_stop: float | None = None
        self.first_modified_stop: float | None = None
        self.modify_calls = 0
        self.close_calls = 0

    def get_open_position(self, symbol: str) -> object | None:
        return self.position if symbol == "XAUUSD" else None

    def get_open_position_by_ticket(self, symbol: str, ticket: int) -> object | None:
        return self.position if symbol == "XAUUSD" and ticket == 15001 else None

    def get_current_price(self, symbol: str) -> float:
        return self.price

    def get_recent_candles(self, symbol: str, timeframe: str, limit: int) -> list[object]:
        self.assert_request(symbol, timeframe)
        return self.candles[-limit:]

    def assert_request(self, symbol: str, timeframe: str) -> None:
        if symbol != "XAUUSD" or timeframe != "M5":
            raise AssertionError((symbol, timeframe))

    def get_atr(self, symbol: str, timeframe: str, period: int) -> None:
        return None

    def modify_position_sl(self, symbol: str, ticket: int, new_stop: float) -> object:
        self.modify_calls += 1
        self.modified_stop = new_stop
        if self.first_modified_stop is None:
            self.first_modified_stop = new_stop
        self.position.sl = new_stop
        return SimpleNamespace(success=True, message="SL atualizado")

    def close_position(self, **kwargs: object) -> object:
        self.close_calls += 1
        return SimpleNamespace(accepted=True, status="ACCEPTED", message="fechada")


class _MarketDataService:
    def __init__(self) -> None:
        self.primary_timeframes: dict[str, str] = {}
        self.supplemental: dict[str, set[str]] = {}
        self.latest_forex_candles: dict[tuple[str, str], list[object]] = {}

    def load_forex_signal_dashboard_for_timeframes(
        self,
        timeframes_by_pair: dict[str, str],
        *,
        fallback_timeframe: str,
    ) -> object:
        self.primary_timeframes = dict(timeframes_by_pair)
        return SimpleNamespace(pairs=[])

    def refresh_supplemental_forex_candles(
        self,
        required: dict[str, set[str]],
        *,
        full_count: int,
    ) -> None:
        self.supplemental = {key: set(value) for key, value in required.items()}


class _LabOperationalModels:
    def __init__(self) -> None:
        self.required_calls = 0

    def required_timeframes(self, model_ids: tuple[str, ...]) -> dict[str, set[str]]:
        self.required_calls += 1
        raise AssertionError(f"M15 nao pertence ao manifesto do Lab: {model_ids}")


if __name__ == "__main__":
    unittest.main()
