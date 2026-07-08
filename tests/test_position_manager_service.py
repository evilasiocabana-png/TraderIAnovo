"""Testes do Position Manager MT5 Demo."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from application.position_manager_service import (
    PositionManagerService,
    PositionTradePlan,
)


class PositionManagerServiceTest(unittest.TestCase):
    """Cobre gestao de SL sem abrir novas entradas."""

    def test_buy_move_stop_para_cima_por_atr_trailing(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="ATR_TRAILING_STOP",
                atr=0.0010,
                parameters={"atr_trailing_factor": "2.0"},
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop, 1.1020)
        self.assertEqual(provider.modify_calls, 1)
        self.assertEqual(provider.submit_order_calls, 0)

    def test_sell_move_stop_para_baixo_por_atr_trailing(self) -> None:
        provider = _FakePositionProvider(
            position=_position("USDCHF", "SELL", 0.8060, 0.8070, 0.8030),
            price=0.8040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "USDCHF",
                "SELL",
                entry=0.8060,
                stop=0.8070,
                target=0.8030,
                stop_management="ATR_TRAILING_STOP",
                atr=0.0005,
                parameters={"atr_trailing_factor": "2.0"},
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop, 0.8050)
        self.assertEqual(provider.modify_calls, 1)
        self.assertEqual(provider.submit_order_calls, 0)

    def test_nao_afasta_stop_contra_o_trader(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.1030, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="ATR_TRAILING_STOP",
                atr=0.0020,
                parameters={"atr_trailing_factor": "2.0"},
            )
        )

        self.assertEqual(result.status, "STOP_MAINTAINED")
        self.assertEqual(provider.modify_calls, 0)

    def test_sem_plano_nao_move(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        results = manager.manage_signals(
            [
                {
                    "symbol": "EURUSD",
                    "decision": "BUY",
                    "stop_management": "ATR_TRAILING_STOP",
                }
            ]
        )

        self.assertEqual(results[0].status, "PLAN_ABSENT")
        self.assertEqual(provider.modify_calls, 0)

    def test_sem_posicao_nao_move(self) -> None:
        provider = _FakePositionProvider(position=None, price=1.1040)
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(self._plan("EURUSD", "BUY"))

        self.assertEqual(result.status, "POSITION_ABSENT")
        self.assertEqual(provider.modify_calls, 0)

    def test_sem_atr_nao_move_atr_trailing(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan("EURUSD", "BUY", stop_management="ATR_TRAILING_STOP", atr=None)
        )

        self.assertEqual(result.status, "ATR_ABSENT")
        self.assertEqual(provider.modify_calls, 0)

    def test_break_even_move_para_entrada(self) -> None:
        provider = _FakePositionProvider(
            position=_position("GBPUSD", "BUY", 1.33637, 1.33508, 1.34043),
            price=1.33908,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "GBPUSD",
                "BUY",
                entry=1.33637,
                stop=1.33508,
                target=1.34043,
                stop_management="BREAK_EVEN",
                parameters={
                    "break_even_trigger_rr": "1.0",
                    "break_even_offset_pips": "0.0",
                },
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop, 1.33637)

    def test_atr_trailing_calcula_sem_recalcular_lab(self) -> None:
        provider = _FakePositionProvider(
            position=_position("AUDUSD", "BUY", 0.6900, 0.6880, 0.6960),
            price=0.6940,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "AUDUSD",
                "BUY",
                entry=0.6900,
                stop=0.6880,
                target=0.6960,
                stop_management="ATR_TRAILING_STOP",
                atr=0.0007,
                parameters={"atr_trailing_factor": "2.0"},
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop, 0.6926)
        self.assertEqual(provider.lab_recalculate_calls, 0)

    def test_default_execucao_assistida_false_calcula_mas_nao_envia(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="ATR_TRAILING_STOP",
                atr=0.0010,
                parameters={"atr_trailing_factor": "2.0"},
            )
        )

        self.assertEqual(result.status, "EXECUTION_DISABLED")
        self.assertAlmostEqual(result.new_stop or 0.0, 1.1020)
        self.assertEqual(provider.modify_calls, 0)

    def test_politica_unsupported_fica_bloqueada(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan("EURUSD", "BUY", stop_management="FULL_EXIT")
        )

        self.assertEqual(result.status, "POLICY_BLOCKED_UNSUPPORTED_ACTION")
        self.assertEqual(provider.modify_calls, 0)

    def test_market_aware_stop_protection_move_stop_seguro(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="MARKET_AWARE_STOP_PROTECTION",
                atr=0.0010,
                support=1.1025,
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop or 0.0, 1.1024)

    def test_structure_based_stop_protection_bloqueia_sem_estrutura(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan("EURUSD", "BUY", stop_management="STRUCTURE_BASED_STOP_PROTECTION")
        )

        self.assertEqual(result.status, "STRUCTURE_ABSENT")
        self.assertEqual(provider.modify_calls, 0)

    def test_volatility_stop_protection_move_stop_seguro(self) -> None:
        provider = _FakePositionProvider(
            position=_position("USDCHF", "SELL", 0.8060, 0.8070, 0.8030),
            price=0.8040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "USDCHF",
                "SELL",
                entry=0.8060,
                stop=0.8070,
                target=0.8030,
                stop_management="VOLATILITY_STOP_PROTECTION",
                atr=0.0005,
                volatility=0.0010,
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop or 0.0, 0.80475)

    def test_momentum_weakness_stop_tightening_move_para_entrada(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1030,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="MOMENTUM_WEAKNESS_STOP_TIGHTENING",
                momentum=-0.0002,
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop or 0.0, 1.1000)

    def _manager(
        self,
        provider: "_FakePositionProvider",
        enabled: bool = False,
    ) -> PositionManagerService:
        return PositionManagerService(
            provider=provider,
            assisted_execution_enabled=enabled,
            log_path=Path(tempfile.gettempdir()) / "traderia-position-manager-test.jsonl",
        )

    def _plan(
        self,
        symbol: str,
        side: str,
        *,
        entry: float = 1.1000,
        stop: float = 1.0980,
        target: float = 1.1060,
        stop_management: str = "ATR_TRAILING_STOP",
        atr: float | None = 0.0010,
        parameters: dict[str, str] | None = None,
        momentum: float | None = None,
        volatility: float | None = None,
        support: float | None = None,
        resistance: float | None = None,
        swing_high: float | None = None,
        swing_low: float | None = None,
    ) -> PositionTradePlan:
        return PositionTradePlan(
            symbol=symbol,
            side=side,
            entry=entry,
            stop=stop,
            target=target,
            stop_management=stop_management,
            stop_management_parameters=parameters or {},
            atr=atr,
            momentum=momentum,
            volatility=volatility,
            support=support,
            resistance=resistance,
            swing_high=swing_high,
            swing_low=swing_low,
        )


def _position(
    symbol: str,
    side: str,
    entry: float,
    stop: float,
    target: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        ticket=123,
        symbol=symbol,
        side=side,
        type=0 if side == "BUY" else 1,
        price_open=entry,
        sl=stop,
        tp=target,
    )


class _FakePositionProvider:
    def __init__(self, position: object | None, price: float | None) -> None:
        self.position = position
        self.price = price
        self.modified_stop: float | None = None
        self.modify_calls = 0
        self.submit_order_calls = 0
        self.lab_recalculate_calls = 0

    def get_open_position(self, symbol: str) -> object | None:
        if self.position is None:
            return None
        if str(getattr(self.position, "symbol", "")).upper() != symbol.upper():
            return None
        return self.position

    def get_current_price(self, symbol: str) -> float | None:
        return self.price

    def get_recent_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[object]:
        return []

    def get_atr(
        self,
        symbol: str,
        timeframe: str,
        period: int,
    ) -> float | None:
        return None

    def modify_position_sl(
        self,
        symbol: str,
        ticket: int,
        new_stop: float,
    ) -> SimpleNamespace:
        self.modify_calls += 1
        self.modified_stop = new_stop
        return SimpleNamespace(success=True, message="SL atualizado.")


if __name__ == "__main__":
    unittest.main()

