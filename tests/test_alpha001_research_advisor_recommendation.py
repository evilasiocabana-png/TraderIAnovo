"""Testes da recomendacao estatistica da Alpha 001."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_research_advisor import (
    Alpha001ResearchAdvisor,
    Alpha001ResearchRecommendation,
)
from research.alpha001_research_validator import Alpha001ResearchValidationResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha001ResearchAdvisorRecommendationTest(unittest.TestCase):
    """Valida interpretacao de Alpha001ResearchValidationResult."""

    def test_recommendation_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha001ResearchRecommendation))
        self.assertTrue(Alpha001ResearchRecommendation.__dataclass_params__.frozen)

    def test_aprovado_vira_approved_for_more_research(self) -> None:
        recommendation = Alpha001ResearchAdvisor().recommend(
            self._validation_result(status="APPROVED", approved=True),
        )

        self.assertEqual(
            recommendation.recommendation,
            "APPROVED_FOR_MORE_RESEARCH",
        )
        self.assertFalse(recommendation.real_trading_authorized)

    def test_amostra_insuficiente_vira_insufficient_sample(self) -> None:
        for status in ("INSUFFICIENT_SAMPLE", "INSUFFICIENT_TRADES"):
            with self.subTest(status=status):
                recommendation = Alpha001ResearchAdvisor().recommend(
                    self._validation_result(status=status),
                )

                self.assertEqual(
                    recommendation.recommendation,
                    "INSUFFICIENT_SAMPLE",
                )

    def test_reprovado_vira_rejected(self) -> None:
        for status in ("LOW_PROFIT_FACTOR", "HIGH_DRAWDOWN", "LOW_WIN_RATE"):
            with self.subTest(status=status):
                recommendation = Alpha001ResearchAdvisor().recommend(
                    self._validation_result(status=status),
                )

                self.assertEqual(recommendation.recommendation, "REJECTED")

    def test_preserva_status_e_reasons_da_validacao(self) -> None:
        reasons = ("Profit factor abaixo do minimo configurado.",)

        recommendation = Alpha001ResearchAdvisor().recommend(
            self._validation_result(status="LOW_PROFIT_FACTOR", reasons=reasons),
        )

        self.assertEqual(recommendation.status, "LOW_PROFIT_FACTOR")
        self.assertEqual(recommendation.reasons, reasons)

    def test_recommendation_e_imutavel(self) -> None:
        recommendation = Alpha001ResearchAdvisor().recommend(
            self._validation_result(status="APPROVED", approved=True),
        )

        with self.assertRaises(FrozenInstanceError):
            recommendation.recommendation = "BUY"

    def test_nao_recomenda_compra_venda_ou_operacao_real(self) -> None:
        allowed = {
            "APPROVED_FOR_MORE_RESEARCH",
            "REJECTED",
            "INSUFFICIENT_SAMPLE",
        }
        results = [
            Alpha001ResearchAdvisor().recommend(
                self._validation_result(status="APPROVED", approved=True),
            ),
            Alpha001ResearchAdvisor().recommend(
                self._validation_result(status="INSUFFICIENT_TRADES"),
            ),
            Alpha001ResearchAdvisor().recommend(
                self._validation_result(status="LOW_WIN_RATE"),
            ),
        ]

        self.assertEqual(
            {result.recommendation for result in results},
            allowed,
        )
        for result in results:
            self.assertFalse(result.real_trading_authorized)
            self.assertNotIn(result.recommendation, {"BUY", "SELL", "TRADE"})

    def test_advisor_nao_acessa_camadas_proibidas(self) -> None:
        path = Path("research/alpha001_research_advisor.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "broker",
            "core.broker",
            "replay",
            "application.replay_service",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "order_send",
            "send_order",
            "place_order",
            "execute_order",
            "next_candle",
            "start",
            "stop",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_novo_fluxo_produz_somente_recomendacoes_permitidas(self) -> None:
        source = read_source(Path("research/alpha001_research_advisor.py"))
        method_source = source[
            source.index("    def recommend") :
            source.index("    def analyze")
        ]
        allowed = (
            "APPROVED_FOR_MORE_RESEARCH",
            "REJECTED",
            "INSUFFICIENT_SAMPLE",
        )
        forbidden = (
            "BUY",
            "SELL",
            "COMPRA",
            "VENDA",
            "OPERACAO_REAL",
            "REAL_TRADING",
        )

        for recommendation in allowed:
            self.assertIn(recommendation, source)
        for fragment in forbidden:
            self.assertNotIn(fragment, method_source)

    def _validation_result(
        self,
        status: str,
        approved: bool = False,
        reasons: tuple[str, ...] = ("Validacao estatistica.",),
    ) -> Alpha001ResearchValidationResult:
        return Alpha001ResearchValidationResult(
            approved=approved,
            status=status,
            reasons=reasons,
            minimum_trades=30,
            minimum_profit_factor=1.2,
            maximum_drawdown=100.0,
            minimum_win_rate=0.4,
            real_trading_authorized=False,
        )


if __name__ == "__main__":
    unittest.main()
