"""Testes do Timeframe Optimizer do Research Lab."""

from __future__ import annotations

import inspect
import unittest

from research.timeframe_optimizer import (
    TimeframeCandidate,
    TimeframeOptimizationResult,
    TimeframeOptimizer,
    TimeframeOptimizerConfiguration,
)


class TimeframeOptimizerTest(unittest.TestCase):
    """Valida ranking conservador de timeframes."""

    def setUp(self) -> None:
        self.configuration = TimeframeOptimizerConfiguration(
            min_sample_size=30,
            min_profit_factor=1.3,
            min_win_rate=0.55,
            max_allowed_drawdown=0.02,
            min_confidence=0.60,
        )

    def test_ranking_escolhe_timeframe_robusto_nao_maior_retorno(self) -> None:
        result = TimeframeOptimizer().optimize(
            "EURUSD",
            [
                self._candidate("M1", avg_return=0.006, max_drawdown=0.019),
                self._candidate(
                    "H1",
                    sample_size=120,
                    win_rate=0.67,
                    avg_return=0.002,
                    profit_factor=2.1,
                    max_drawdown=0.006,
                    confidence=0.82,
                ),
            ],
            self.configuration,
        )

        self.assertEqual(result.best_timeframe, "H1")
        self.assertTrue(result.is_research_only)

    def test_timeframe_com_baixa_amostra_e_rejeitado(self) -> None:
        result = self._single_candidate_result(
            self._candidate("M5", sample_size=10)
        )

        self.assertEqual(result.best_timeframe, "NONE")
        self.assertEqual(result.rejected_candidates[0].rejection_reason, "LOW_SAMPLE_SIZE")

    def test_timeframe_com_profit_factor_baixo_e_rejeitado(self) -> None:
        result = self._single_candidate_result(
            self._candidate("M15", profit_factor=1.0)
        )

        self.assertEqual(result.rejected_candidates[0].rejection_reason, "LOW_PROFIT_FACTOR")

    def test_timeframe_com_drawdown_alto_e_rejeitado(self) -> None:
        result = self._single_candidate_result(
            self._candidate("M30", max_drawdown=0.05)
        )

        self.assertEqual(result.rejected_candidates[0].rejection_reason, "HIGH_DRAWDOWN")

    def test_resultado_e_research_only(self) -> None:
        result = self._single_candidate_result(self._candidate("H1"))

        self.assertIsInstance(result, TimeframeOptimizationResult)
        self.assertTrue(result.is_research_only)

    def test_nao_depende_de_mt5_broker_dashboard_ou_ia(self) -> None:
        source = inspect.getsource(TimeframeOptimizer)
        forbidden = {
            "MetaTrader5",
            "mt5",
            "Broker",
            "Streamlit",
            "streamlit",
            "order_send",
            "order_check",
            "OpenAI",
            "LLM",
        }

        self.assertEqual([item for item in forbidden if item in source], [])

    def _single_candidate_result(
        self,
        candidate: TimeframeCandidate,
    ) -> TimeframeOptimizationResult:
        return TimeframeOptimizer().optimize(
            "EURUSD",
            [candidate],
            self.configuration,
        )

    def _candidate(
        self,
        timeframe: str,
        sample_size: int = 80,
        win_rate: float = 0.62,
        avg_return: float = 0.001,
        profit_factor: float = 1.6,
        max_drawdown: float = 0.01,
        confidence: float = 0.70,
    ) -> TimeframeCandidate:
        return TimeframeCandidate(
            symbol="EURUSD",
            timeframe=timeframe,
            sample_size=sample_size,
            win_rate=win_rate,
            avg_return=avg_return,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            calibrated_confidence=confidence,
        )


if __name__ == "__main__":
    unittest.main()
