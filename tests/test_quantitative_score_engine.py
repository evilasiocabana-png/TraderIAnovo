"""Testes do score quantitativo calibrado do Research Lab."""

from __future__ import annotations

import inspect
import importlib
import unittest

from research.quantitative_score_engine import (
    QuantitativeScoreConfiguration,
    QuantitativeScoreContext,
    QuantitativeScoreEngine,
    QuantitativeScoreObservation,
)


class QuantitativeScoreEngineTest(unittest.TestCase):
    def test_score_com_amostra_suficiente_calibra_confidence(self) -> None:
        engine = QuantitativeScoreEngine(self._configuration())
        context = self._context("BUY")
        observations = self._observations("BUY", wins=27, losses=3)

        result = engine.calculate(context, observations)

        self.assertEqual(result.decision, "BUY")
        self.assertGreater(result.calibrated_confidence, 0.50)
        self.assertEqual(result.sample_size, 30)
        self.assertAlmostEqual(result.win_rate, 0.90)
        self.assertGreater(result.avg_return, 0.0)
        self.assertGreater(result.profit_factor, 1.2)
        self.assertIn("Confianca calibrada", result.reason)
        self.assertEqual(result.matched_context_count, 30)
        self.assertEqual(result.volatility_bucket, "NORMAL")
        self.assertEqual(result.rsi_bucket, "HEALTHY")
        self.assertEqual(result.momentum_sign, "POSITIVE")
        self.assertEqual(result.ma_distance_bucket, "STRONG")
        self.assertIn("momentum_ma_aligned", result.confidence_drivers)
        self.assertIn("sample_size_sufficient", result.confidence_drivers)
        self.assertIn("drawdown_penalty", result.confidence_penalties)

    def test_score_com_pouca_amostra_vira_wait(self) -> None:
        engine = QuantitativeScoreEngine(self._configuration())
        context = self._context("BUY")
        observations = self._observations("BUY", wins=4, losses=1)

        result = engine.calculate(context, observations)

        self.assertEqual(result.decision, "WAIT")
        self.assertEqual(result.sample_size, 5)
        self.assertLessEqual(result.calibrated_confidence, 0.95)
        self.assertIn("Amostra insuficiente", result.reason)
        self.assertEqual(result.matched_context_count, 5)
        self.assertEqual(result.rejected_reason, "LOW_SAMPLE_SIZE")
        self.assertIn("low_sample_size", result.confidence_penalties)
        self.assertIn("momentum_ma_aligned", result.confidence_drivers)

    def test_baixa_volatilidade_penaliza_contexto(self) -> None:
        engine = QuantitativeScoreEngine(self._configuration())
        context = self._context("BUY", volatility=0.00001)

        result = engine.calculate(context, self._observations("BUY", 30, 0))

        self.assertEqual(result.decision, "WAIT")
        self.assertEqual(result.calibrated_confidence, 0.0)
        self.assertEqual(result.sample_size, 0)
        self.assertIn("Volatilidade baixa", result.reason)
        self.assertEqual(result.rejected_reason, "LOW_VOLATILITY")
        self.assertEqual(result.volatility_bucket, "LOW")
        self.assertIn("low_volatility", result.confidence_penalties)

    def test_estatistica_fraca_vira_wait(self) -> None:
        engine = QuantitativeScoreEngine(self._configuration())
        context = self._context("BUY")
        observations = self._observations("BUY", wins=10, losses=20)

        result = engine.calculate(context, observations)

        self.assertEqual(result.decision, "WAIT")
        self.assertEqual(result.sample_size, 30)
        self.assertLess(result.profit_factor, 1.2)
        self.assertIn("Profit factor insuficiente", result.reason)
        self.assertEqual(result.rejected_reason, "LOW_PROFIT_FACTOR")
        self.assertIn("low_profit_factor", result.confidence_penalties)

    def test_sample_minimo_configuravel_altera_resultado(self) -> None:
        context = self._context("BUY")
        observations = self._observations("BUY", wins=18, losses=2)

        approved = QuantitativeScoreEngine(
            self._configuration(min_sample_size=10)
        ).calculate(context, observations)
        rejected = QuantitativeScoreEngine(
            self._configuration(min_sample_size=30)
        ).calculate(context, observations)

        self.assertEqual(approved.decision, "BUY")
        self.assertEqual(rejected.decision, "WAIT")
        self.assertEqual(rejected.rejected_reason, "LOW_SAMPLE_SIZE")

    def test_profit_factor_minimo_configuravel_altera_resultado(self) -> None:
        context = self._context("BUY")
        observations = self._observations("BUY", wins=18, losses=12)

        approved = QuantitativeScoreEngine(
            self._configuration(min_profit_factor=2.0)
        ).calculate(context, observations)
        rejected = QuantitativeScoreEngine(
            self._configuration(min_profit_factor=4.0)
        ).calculate(context, observations)

        self.assertEqual(approved.decision, "BUY")
        self.assertEqual(rejected.decision, "WAIT")
        self.assertEqual(rejected.rejected_reason, "LOW_PROFIT_FACTOR")

    def test_win_rate_minimo_configuravel_altera_resultado(self) -> None:
        context = self._context("BUY")
        observations = self._observations("BUY", wins=18, losses=12)

        approved = QuantitativeScoreEngine(
            self._configuration(min_win_rate=0.55)
        ).calculate(context, observations)
        rejected = QuantitativeScoreEngine(
            self._configuration(min_win_rate=0.70)
        ).calculate(context, observations)

        self.assertEqual(approved.decision, "BUY")
        self.assertEqual(rejected.decision, "WAIT")
        self.assertEqual(rejected.rejected_reason, "WEAK_STATISTICS")

    def test_research_engine_nao_depende_de_mt5_broker_ou_dashboard(self) -> None:
        module = importlib.import_module("research.quantitative_score_engine")
        source = inspect.getsource(module)
        forbidden = {
            "MetaTrader5",
            "MT5",
            "Broker",
            "dashboard",
            "Dashboard",
            "order" + "_send",
            "order" + "_check",
        }

        self.assertEqual([item for item in forbidden if item in source], [])

    def test_engine_exige_configuracao_explicita(self) -> None:
        signature = inspect.signature(QuantitativeScoreEngine)

        self.assertEqual(list(signature.parameters), ["configuration"])
        self.assertEqual(
            signature.parameters["configuration"].default,
            inspect.Parameter.empty,
        )

    def _context(
        self,
        decision: str,
        volatility: float = 0.0002,
    ) -> QuantitativeScoreContext:
        return QuantitativeScoreContext(
            trend="ALTA",
            momentum=0.001,
            volatility=volatility,
            rsi=55.0,
            moving_average_distance=0.001,
            candidate_decision=decision,
        )

    def _configuration(
        self,
        min_sample_size: int = 20,
        min_profit_factor: float = 1.2,
        min_win_rate: float = 0.5,
    ) -> QuantitativeScoreConfiguration:
        return QuantitativeScoreConfiguration(
            candles_loaded=500,
            feature_lookback=10,
            forward_return_candles=1,
            fast_ma_period=20,
            slow_ma_period=50,
            rsi_period=14,
            volatility_period=20,
            min_sample_size=min_sample_size,
            min_profit_factor=min_profit_factor,
            min_win_rate=min_win_rate,
            confidence_floor=0.0,
            confidence_ceiling=0.95,
            volatility_bucket_method="FIXED",
            volatility_low_threshold=0.0001,
            volatility_high_threshold=0.0003,
            ma_flat_threshold=0.0001,
            ma_strong_threshold=0.001,
            rsi_oversold_threshold=30.0,
            rsi_overbought_threshold=70.0,
        )

    def _observations(
        self,
        decision: str,
        wins: int,
        losses: int,
    ) -> list[QuantitativeScoreObservation]:
        returns = ([0.002] * wins) + ([-0.001] * losses)
        return [
            QuantitativeScoreObservation(
                trend="ALTA",
                momentum=0.001,
                volatility=0.0002,
                rsi=55.0,
                moving_average_distance=0.001,
                candidate_decision=decision,
                forward_return=value,
            )
            for value in returns
        ]


if __name__ == "__main__":
    unittest.main()
