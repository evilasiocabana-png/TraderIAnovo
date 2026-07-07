"""Testes do motor de correlacao entre Alphas."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.portfolio.alpha_correlation_engine import (
    AlphaCorrelationEngine,
    AlphaCorrelationResult,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaCorrelationEngineTest(unittest.TestCase):
    """Valida correlacao entre curvas de resultado."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaCorrelationResult))
        self.assertTrue(AlphaCorrelationResult.__dataclass_params__.frozen)

    def test_calcula_matriz_de_correlacao(self) -> None:
        result = AlphaCorrelationEngine().calculate(
            {
                "Alpha001": (1.0, 2.0, 3.0),
                "Alpha002": (2.0, 4.0, 6.0),
                "Alpha003": (3.0, 2.0, 1.0),
            },
        )

        self.assertEqual(result.alpha_ids, ("Alpha001", "Alpha002", "Alpha003"))
        self.assertEqual(result.correlation_matrix[0][0], 1.0)
        self.assertAlmostEqual(result.correlation_matrix[0][1], 1.0)
        self.assertAlmostEqual(result.correlation_matrix[0][2], -1.0)
        self.assertAlmostEqual(result.average_correlation, -1.0 / 3.0)
        self.assertAlmostEqual(result.highest_correlation, 1.0)
        self.assertAlmostEqual(result.lowest_correlation, -1.0)

    def test_sem_curvas_retorna_resultado_vazio(self) -> None:
        result = AlphaCorrelationEngine().calculate({})

        self.assertEqual(result.alpha_ids, ())
        self.assertEqual(result.correlation_matrix, ())
        self.assertEqual(result.average_correlation, 0.0)
        self.assertEqual(result.highest_correlation, 0.0)
        self.assertEqual(result.lowest_correlation, 0.0)

    def test_uma_alpha_retorna_matriz_unitaria_sem_pares(self) -> None:
        result = AlphaCorrelationEngine().calculate(
            {"Alpha001": (1.0, 2.0, 3.0)},
        )

        self.assertEqual(result.correlation_matrix, ((1.0,),))
        self.assertEqual(result.average_correlation, 0.0)
        self.assertEqual(result.highest_correlation, 0.0)
        self.assertEqual(result.lowest_correlation, 0.0)

    def test_curvas_constantes_retorna_correlacao_zero(self) -> None:
        result = AlphaCorrelationEngine().calculate(
            {
                "Alpha001": (1.0, 1.0, 1.0),
                "Alpha002": (2.0, 3.0, 4.0),
            },
        )

        self.assertEqual(result.correlation_matrix[0][1], 0.0)

    def test_curvas_de_tamanhos_diferentes_usam_trecho_comum(self) -> None:
        result = AlphaCorrelationEngine().calculate(
            {
                "Alpha001": (1.0, 2.0, 3.0, 100.0),
                "Alpha002": (2.0, 4.0, 6.0),
            },
        )

        self.assertAlmostEqual(result.correlation_matrix[0][1], 1.0)

    def test_resultado_e_imutavel(self) -> None:
        result = AlphaCorrelationEngine().calculate(
            {"Alpha001": (1.0,), "Alpha002": (1.0,)},
        )

        with self.assertRaises(FrozenInstanceError):
            result.average_correlation = 1.0

    def test_engine_nao_implementa_otimizacao_de_carteira(self) -> None:
        source = read_source(Path("research/portfolio/alpha_correlation_engine.py"))
        forbidden_fragments = (
            "optimize",
            "optimizer",
            "weight",
            "Markowitz",
            "HRP",
            "Risk Parity",
            "risk_parity",
            "portfolio_allocation",
            "allocation",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_nao_gera_graficos_dashboard_ou_persistencia(self) -> None:
        source = read_source(Path("research/portfolio/alpha_correlation_engine.py"))
        forbidden_fragments = (
            "matplotlib",
            "plot",
            "dashboard",
            "streamlit",
            "open(",
            "write",
            "json",
            "csv",
            "export",
            "database",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/portfolio/alpha_correlation_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "alpha.alpha001_config",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "generate_signal",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))


if __name__ == "__main__":
    unittest.main()
