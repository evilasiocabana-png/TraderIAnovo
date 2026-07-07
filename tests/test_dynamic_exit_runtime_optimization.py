"""Testes de otimizacao do runtime da saida dinamica."""

import unittest

from application.dynamic_exit_engine import DynamicExitUnifiedEngine
from domain.contracts.dynamic_exit import DynamicExitMarketReading
from domain.contracts.dynamic_exit_engine import DynamicExitEngineInput


class CountingClassifier:
    def __init__(self) -> None:
        self.calls = 0

    def classify(self, reading: DynamicExitMarketReading) -> DynamicExitMarketReading:
        self.calls += 1
        return reading


class FailingClassifier:
    def classify(self, reading: DynamicExitMarketReading) -> DynamicExitMarketReading:
        raise RuntimeError("boom")


class DynamicExitRuntimeOptimizationTest(unittest.TestCase):
    def test_cache_reutiliza_resultado_para_leitura_identica(self) -> None:
        classifier = CountingClassifier()
        engine = DynamicExitUnifiedEngine(
            classifier=classifier,
            max_cache_entries=2,
        )
        payload = DynamicExitEngineInput(
            reading=self._reading(),
            policy="FIXED_STOP",
        )

        first = engine.evaluate(payload)
        second = engine.evaluate(payload)

        self.assertIs(first, second)
        self.assertEqual(classifier.calls, 1)
        self.assertFalse(second.allowed_to_execute_demo)

    def test_cache_lru_descarta_entrada_antiga(self) -> None:
        classifier = CountingClassifier()
        engine = DynamicExitUnifiedEngine(
            classifier=classifier,
            max_cache_entries=1,
        )

        first_payload = DynamicExitEngineInput(
            reading=self._reading(symbol="EURUSD"),
            policy="FIXED_STOP",
        )
        second_payload = DynamicExitEngineInput(
            reading=self._reading(symbol="GBPUSD"),
            policy="FIXED_STOP",
        )
        engine.evaluate(first_payload)
        engine.evaluate(second_payload)
        engine.evaluate(first_payload)

        self.assertEqual(classifier.calls, 3)

    def test_cache_pode_ser_desligado(self) -> None:
        classifier = CountingClassifier()
        engine = DynamicExitUnifiedEngine(
            classifier=classifier,
            max_cache_entries=0,
        )
        payload = DynamicExitEngineInput(
            reading=self._reading(),
            policy="FIXED_STOP",
        )

        engine.evaluate(payload)
        engine.evaluate(payload)

        self.assertEqual(classifier.calls, 2)

    def test_erro_inesperado_falha_fechado_sem_execucao(self) -> None:
        engine = DynamicExitUnifiedEngine(
            classifier=FailingClassifier(),
            max_cache_entries=2,
        )

        result = engine.evaluate(
            DynamicExitEngineInput(
                reading=self._reading(),
                policy="ATR_TRAILING_STOP",
            )
        )

        self.assertEqual(result.market_reading.state, "BAD_EXECUTION_CONTEXT")
        self.assertEqual(result.recommendation.action, "NO_ACTION_BAD_CONTEXT")
        self.assertEqual(result.authorization.status, "REJECTED")
        self.assertFalse(result.allowed_to_execute_demo)
        self.assertFalse(result.authorization.allowed_to_execute_demo)

    def _reading(self, *, symbol: str = "EURUSD") -> DynamicExitMarketReading:
        return DynamicExitMarketReading(
            symbol=symbol,
            side="BUY",
            is_positioned=True,
            current_price=1.1010,
            entry_price=1.1000,
            stop_price=1.0990,
            target_price=1.1060,
            atr=0.0010,
            volatility=0.0012,
            momentum=0.1,
            spread=0.0001,
            time_in_position_minutes=60,
        )


if __name__ == "__main__":
    unittest.main()
