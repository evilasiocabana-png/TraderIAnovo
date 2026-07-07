"""Testes do Indice de Certificacao TraderIA."""

import unittest

from research.traderia_certification_index import (
    TraderIACertificationEngine,
    TraderIACertificationInput,
)


class TraderIACertificationEngineTest(unittest.TestCase):
    """Valida ICT, classificacao e filtros eliminatorios."""

    def test_classifica_alpha_a_com_metricas_robustas(self) -> None:
        result = TraderIACertificationEngine().certify(
            TraderIACertificationInput(
                win_rate=0.61,
                profit_factor=2.10,
                expectancy=0.0015,
                max_drawdown=0.08,
                sample_size=640,
                recovery_factor=4.2,
            )
        )

        self.assertEqual(result.grade, "A")
        self.assertEqual(result.status, "CERTIFICADA_A")
        self.assertTrue(result.demo_allowed)
        self.assertTrue(result.minimum_filters_passed)
        self.assertGreaterEqual(result.ict_score, 80.0)
        self.assertIn("profit_factor", result.component_scores)

    def test_reprova_mesmo_com_win_rate_alto_quando_filtro_minimo_falha(self) -> None:
        result = TraderIACertificationEngine().certify(
            TraderIACertificationInput(
                win_rate=0.72,
                profit_factor=1.10,
                expectancy=0.001,
                max_drawdown=0.08,
                sample_size=400,
                recovery_factor=2.0,
            )
        )

        self.assertEqual(result.grade, "E")
        self.assertEqual(result.status, "REJEITADA")
        self.assertFalse(result.demo_allowed)
        self.assertFalse(result.minimum_filters_passed)
        self.assertIn("Profit Factor abaixo de 1.30.", result.rejection_reasons)

    def test_b_libera_demo_com_monitoramento_reforcado(self) -> None:
        result = TraderIACertificationEngine().certify(
            TraderIACertificationInput(
                win_rate=0.58,
                profit_factor=1.70,
                expectancy=0.0009,
                max_drawdown=0.12,
                sample_size=260,
                recovery_factor=3.0,
            )
        )

        self.assertEqual(result.grade, "B")
        self.assertEqual(result.status, "CERTIFICADA_B")
        self.assertTrue(result.demo_allowed)
        self.assertIn("monitoramento reforcado", result.usage)


if __name__ == "__main__":
    unittest.main()
