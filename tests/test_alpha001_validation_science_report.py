"""Testes do relatorio de validacao cientifica da Alpha 001."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_monte_carlo_engine import Alpha001MonteCarloResult
from research.alpha001_sensitivity_engine import Alpha001SensitivityResult
from research.alpha001_statistical_significance_engine import (
    Alpha001StatisticalSignificanceResult,
)
from research.alpha001_validation_science_report import (
    Alpha001ValidationScienceResult,
)
from research.alpha001_walk_forward_engine import (
    Alpha001WalkForwardMetrics,
    Alpha001WalkForwardResult,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha001ValidationScienceReportTest(unittest.TestCase):
    """Valida agregacao pura dos resultados cientificos."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha001ValidationScienceResult))
        self.assertTrue(
            Alpha001ValidationScienceResult.__dataclass_params__.frozen
        )

    def test_agrega_resultados_tipados_dos_engines_anteriores(self) -> None:
        report = self._report()

        self.assertIsInstance(report.walk_forward, Alpha001WalkForwardResult)
        self.assertIsInstance(report.monte_carlo, Alpha001MonteCarloResult)
        self.assertIsInstance(report.sensitivity, Alpha001SensitivityResult)
        self.assertIsInstance(
            report.statistical_significance,
            Alpha001StatisticalSignificanceResult,
        )

    def test_preserva_referencias_recebidas_sem_recalcular(self) -> None:
        walk_forward = self._walk_forward()
        monte_carlo = self._monte_carlo()
        sensitivity = self._sensitivity()
        statistical_significance = self._statistical_significance()

        report = Alpha001ValidationScienceResult(
            walk_forward=walk_forward,
            monte_carlo=monte_carlo,
            sensitivity=sensitivity,
            statistical_significance=statistical_significance,
        )

        self.assertIs(report.walk_forward, walk_forward)
        self.assertIs(report.monte_carlo, monte_carlo)
        self.assertIs(report.sensitivity, sensitivity)
        self.assertIs(
            report.statistical_significance,
            statistical_significance,
        )

    def test_resultado_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.monte_carlo = self._monte_carlo()

    def test_nao_expoe_campos_operacionais_ou_recomendacao(self) -> None:
        report = self._report()
        forbidden_fields = (
            "recommendation",
            "real_trading_authorized",
            "broker",
            "dashboard",
            "score",
            "approved_for_trading",
        )

        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                self.assertFalse(hasattr(report, field_name))

    def test_relatorio_nao_importa_engines_ou_camadas_operacionais(self) -> None:
        path = Path("research/alpha001_validation_science_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "broker",
            "mt5",
            "MetaTrader5",
            "Alpha001WalkForwardEngine",
            "Alpha001MonteCarloEngine",
            "Alpha001SensitivityEngine",
            "Alpha001StatisticalSignificanceEngine",
        }
        forbidden_calls = {
            "calculate",
            "run",
            "analyze",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_codigo_fonte_nao_recalcula_metricas(self) -> None:
        source = read_source(
            Path("research/alpha001_validation_science_report.py")
        )
        forbidden_fragments = (
            ".calculate(",
            ".analyze(",
            "sum(",
            "max(",
            "min(",
            " / ",
            " * ",
            " + ",
            " - ",
            "Alpha001WalkForwardEngine",
            "Alpha001MonteCarloEngine",
            "Alpha001SensitivityEngine",
            "Alpha001StatisticalSignificanceEngine",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def _report(self) -> Alpha001ValidationScienceResult:
        return Alpha001ValidationScienceResult(
            walk_forward=self._walk_forward(),
            monte_carlo=self._monte_carlo(),
            sensitivity=self._sensitivity(),
            statistical_significance=self._statistical_significance(),
        )

    def _walk_forward(self) -> Alpha001WalkForwardResult:
        metrics = Alpha001WalkForwardMetrics(
            total_experiments=1,
            total_candles=100,
            total_signals=10,
            total_buy=5,
            total_sell=3,
            total_wait=2,
        )
        return Alpha001WalkForwardResult(
            training_window=1,
            validation_window=1,
            testing_window=1,
            training_metrics=metrics,
            validation_metrics=metrics,
            testing_metrics=metrics,
        )

    def _monte_carlo(self) -> Alpha001MonteCarloResult:
        return Alpha001MonteCarloResult(
            total_simulations=100,
            average_net_profit=10.0,
            median_net_profit=9.0,
            worst_simulation=-5.0,
            best_simulation=20.0,
            average_drawdown=3.0,
        )

    def _sensitivity(self) -> Alpha001SensitivityResult:
        return Alpha001SensitivityResult(
            variation_of_net_profit=5.0,
            variation_of_drawdown=2.0,
            variation_of_profit_factor=0.2,
            variation_of_win_rate=0.05,
        )

    def _statistical_significance(
        self,
    ) -> Alpha001StatisticalSignificanceResult:
        return Alpha001StatisticalSignificanceResult(
            mean_return=1.0,
            standard_deviation=2.0,
            standard_error=0.5,
            t_score=2.0,
            significance_flag=True,
        )


if __name__ == "__main__":
    unittest.main()
