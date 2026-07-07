"""Testes do runtime operacional demo."""

import unittest

from application.demo_execution_service import DemoExecutionService
from application.demo_trading_runtime import (
    DemoTradingRuntime,
    DemoTradingRuntimeConfig,
    MovingAverageDemoSignalProvider,
)
from domain.candle import Candle
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.strategy_signal import StrategySignal


class DemoTradingRuntimeTest(unittest.TestCase):
    """Valida o ciclo sinal -> ordem demo sem acoplamento direto ao MT5."""

    def test_runtime_desativado_nao_conecta_nem_envia_ordem(self) -> None:
        market_data = _FakeMarketDataProvider(self._uptrend_candles())
        execution_provider = _AcceptingExecutionProvider()
        runtime = DemoTradingRuntime(
            market_data_provider=market_data,
            execution_service=DemoExecutionService(provider=execution_provider),
            config=DemoTradingRuntimeConfig(enabled=False),
        )

        result = runtime.run_once()

        self.assertEqual(result.status, "DISABLED")
        self.assertEqual(market_data.initialize_calls, 0)
        self.assertEqual(execution_provider.orders, [])

    def test_runtime_gera_entrada_stop_alvo_e_envia_ordem_demo(self) -> None:
        market_data = _FakeMarketDataProvider(self._uptrend_candles())
        execution_provider = _AcceptingExecutionProvider()
        runtime = DemoTradingRuntime(
            market_data_provider=market_data,
            execution_service=DemoExecutionService(provider=execution_provider),
            signal_provider=_StaticSignalProvider("BUY"),
            config=DemoTradingRuntimeConfig(
                symbol="WDO",
                timeframe="M1",
                quantity=2,
                stop_points=10.0,
                target_points=20.0,
                enabled=True,
            ),
        )

        result = runtime.run_once()

        self.assertEqual(result.status, "ACCEPTED")
        self.assertIsNotNone(result.plan)
        self.assertEqual(result.plan.entry_price, 129.0)
        self.assertEqual(result.plan.stop, 119.0)
        self.assertEqual(result.plan.target, 149.0)
        self.assertEqual(len(execution_provider.orders), 1)
        self.assertEqual(execution_provider.orders[0].symbol, "WDO")
        self.assertEqual(execution_provider.orders[0].quantity, 2)

    def test_runtime_nao_envia_ordem_quando_sinal_e_wait(self) -> None:
        market_data = _FakeMarketDataProvider(self._uptrend_candles())
        execution_provider = _AcceptingExecutionProvider()
        runtime = DemoTradingRuntime(
            market_data_provider=market_data,
            execution_service=DemoExecutionService(provider=execution_provider),
            signal_provider=_StaticSignalProvider("WAIT"),
            config=DemoTradingRuntimeConfig(enabled=True),
        )

        result = runtime.run_once()

        self.assertEqual(result.status, "NO_ORDER")
        self.assertEqual(execution_provider.orders, [])

    def test_signal_provider_padrao_detecta_compra_em_alta(self) -> None:
        provider = MovingAverageDemoSignalProvider()
        candles = self._uptrend_candles()
        snapshot = MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-29 10:00:00",
            regime="TREND_UP",
            volatility=1.0,
            liquidity=1.0,
            trend_strength=1.0,
            market_dna_score=100.0,
        )

        signal = provider.generate_signal(candles, snapshot, candles[-1].fechamento)

        self.assertEqual(signal.decision, "BUY")
        self.assertGreaterEqual(signal.score, 60)

    def _uptrend_candles(self) -> list[Candle]:
        return [
            Candle(
                data="2026-06-29 10:00:00",
                abertura=100.0 + index,
                maxima=101.0 + index,
                minima=99.0 + index,
                fechamento=100.0 + index,
                volume=1000 + index,
            )
            for index in range(30)
        ]


class _FakeMarketDataProvider:
    def __init__(self, candles: list[Candle]) -> None:
        self.candles = candles
        self.initialize_calls = 0

    def initialize_market_data(self) -> bool:
        self.initialize_calls += 1
        return True

    def select_symbol(self, symbol: str) -> bool:
        return bool(symbol)

    def get_candles(self, symbol: str, timeframe: object, count: int) -> list[Candle]:
        return self.candles[-count:]


class _AcceptingExecutionProvider:
    def __init__(self) -> None:
        self.orders: list[ExecutionOrder] = []

    def has_open_position(self, symbol: str) -> bool:
        return False

    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        self.orders.append(order)
        return ExecutionResult(True, "ACCEPTED", "ordem demo aceita", ticket=321)


class _StaticSignalProvider:
    def __init__(self, decision: str) -> None:
        self.decision = decision

    def generate_signal(
        self,
        candles: list[Candle],
        market_snapshot: MarketSnapshot,
        current_price: float,
    ) -> StrategySignal:
        if self.decision == "WAIT":
            return StrategySignal("WAIT", 0, 0.0, ["aguardar"])
        return StrategySignal(self.decision, 90, 0.90, ["sinal operacional"])


if __name__ == "__main__":
    unittest.main()
