"""Testes do advisor de pesquisa da Alpha 001."""

import unittest

from research.alpha001_experiment_validator import Alpha001ValidationResult
from research.alpha001_research_advisor import (
    Alpha001ResearchAdvice,
    Alpha001ResearchAdvisor,
)


class Alpha001ResearchAdvisorTest(unittest.TestCase):
    """Valida interpretacao de resultados da Alpha 001."""

    def test_retorna_ready_for_extended_research(self) -> None:
        """Status APPROVED deve liberar pesquisa estendida."""
        advice = Alpha001ResearchAdvisor().analyze(self._result("APPROVED"))

        self.assertEqual(advice.recommendation, "READY_FOR_EXTENDED_RESEARCH")
        self.assertEqual(advice.priority, "LOW")

    def test_retorna_collect_more_samples(self) -> None:
        """Pouca amostra deve pedir mais dados."""
        advice = Alpha001ResearchAdvisor().analyze(
            self._result("INSUFFICIENT_SAMPLE"),
        )

        self.assertEqual(advice.recommendation, "COLLECT_MORE_SAMPLES")
        self.assertEqual(advice.priority, "MEDIUM")

    def test_retorna_review_entry_filters(self) -> None:
        """Profit factor baixo deve revisar filtros de entrada."""
        advice = Alpha001ResearchAdvisor().analyze(
            self._result("LOW_PROFIT_FACTOR"),
        )

        self.assertEqual(advice.recommendation, "REVIEW_ENTRY_FILTERS")
        self.assertEqual(advice.priority, "MEDIUM")

    def test_retorna_review_risk_parameters(self) -> None:
        """Drawdown alto deve revisar parametros de risco."""
        advice = Alpha001ResearchAdvisor().analyze(
            self._result("HIGH_DRAWDOWN"),
        )

        self.assertEqual(advice.recommendation, "REVIEW_RISK_PARAMETERS")
        self.assertEqual(advice.priority, "HIGH")

    def test_agrega_recomendacoes(self) -> None:
        """Multiplos problemas devem agregar recomendacoes."""
        advice = Alpha001ResearchAdvisor().analyze(
            self._result(
                "INSUFFICIENT_SAMPLE",
                [
                    "Poucas operacoes para validar a Alpha 001.",
                    "Profit factor abaixo do minimo configurado.",
                    "Drawdown acima do limite configurado.",
                ],
            ),
        )

        self.assertIn("COLLECT_MORE_SAMPLES", advice.recommendation)
        self.assertIn("REVIEW_ENTRY_FILTERS", advice.recommendation)
        self.assertIn("REVIEW_RISK_PARAMETERS", advice.recommendation)

    def test_valida_prioridade_da_mais_critica(self) -> None:
        """Prioridade deve refletir a recomendacao mais critica."""
        advice = Alpha001ResearchAdvisor().analyze(
            self._result(
                "LOW_PROFIT_FACTOR",
                [
                    "Profit factor abaixo do minimo configurado.",
                    "Drawdown acima do limite configurado.",
                ],
            ),
        )

        self.assertEqual(advice.priority, "HIGH")

    def test_valida_reasons_preservados(self) -> None:
        """Reasons do validator devem ser preservados."""
        reasons = ["Drawdown acima do limite configurado."]

        advice = Alpha001ResearchAdvisor().analyze(
            self._result("HIGH_DRAWDOWN", reasons),
        )

        self.assertEqual(advice.reasons, reasons)

    def test_valida_retorno_alpha001_research_advice(self) -> None:
        """Advisor deve retornar Alpha001ResearchAdvice."""
        advice = Alpha001ResearchAdvisor().analyze(self._result("APPROVED"))

        self.assertIsInstance(advice, Alpha001ResearchAdvice)

    def _result(
        self,
        status: str,
        reasons: list[str] | None = None,
    ) -> Alpha001ValidationResult:
        return Alpha001ValidationResult(
            approved=status == "APPROVED",
            status=status,
            reasons=reasons or ["Experimento aprovado."],
            metrics={
                "total_trades": 40,
                "win_rate": 0.6,
                "profit_factor": 1.5,
                "max_drawdown_points": 50.0,
                "net_profit_points": 100.0,
            },
        )


if __name__ == "__main__":
    unittest.main()
