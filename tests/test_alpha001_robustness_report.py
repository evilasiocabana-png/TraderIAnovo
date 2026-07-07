"""Testes do relatorio consolidado de robustez da Alpha 001."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_outlier_engine import Alpha001OutlierResult
from research.alpha001_parameter_stability_engine import (
    Alpha001ParameterStabilityResult,
)
from research.alpha001_regime_breakdown_engine import (
    Alpha001RegimeBreakdownResult,
    Alpha001RegimeMetrics,
)
from research.alpha001_robustness_report import Alpha001RobustnessResult
from research.alpha001_sample_quality_engine import Alpha001SampleQualityResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha001RobustnessReportTest(unittest.TestCase):
    """Valida agregacao pura dos resultados de robustez."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha001RobustnessResult))
        self.assertTrue(Alpha001RobustnessResult.__dataclass_params__.frozen)

    def test_agrega_resultados_tipados_dos_engines_anteriores(self) -> None:
        report = self._report()

        self.assertIsInstance(report.sample_quality, Alpha001SampleQualityResult)
        self.assertIsInstance(report.outlier, Alpha001OutlierResult)
        self.assertIsInstance(
            report.regime_breakdown,
            Alpha001RegimeBreakdownResult,
        )
        self.assertIsInstance(
            report.parameter_stability,
            Alpha001ParameterStabilityResult,
        )

    def test_preserva_referencias_recebidas_sem_recalcular(self) -> None:
        sample_quality = self._sample_quality()
        outlier = self._outlier()
        regime_breakdown = self._regime_breakdown()
        parameter_stability = self._parameter_stability()

        report = Alpha001RobustnessResult(
            sample_quality=sample_quality,
            outlier=outlier,
            regime_breakdown=regime_breakdown,
            parameter_stability=parameter_stability,
        )

        self.assertIs(report.sample_quality, sample_quality)
        self.assertIs(report.outlier, outlier)
        self.assertIs(report.regime_breakdown, regime_breakdown)
        self.assertIs(report.parameter_stability, parameter_stability)

    def test_resultado_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.outlier = self._outlier()

    def test_nao_expoe_campos_calculados_ou_operacionais(self) -> None:
        report = self._report()
        forbidden_fields = (
            "score",
            "status",
            "recommendation",
            "real_trading_authorized",
            "broker",
            "dashboard",
            "generated_at",
        )

        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                self.assertFalse(hasattr(report, field_name))

    def test_relatorio_nao_importa_engines_ou_camadas_operacionais(self) -> None:
        path = Path("research/alpha001_robustness_report.py")
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
            "Alpha001SampleQualityEngine",
            "Alpha001OutlierEngine",
            "Alpha001RegimeBreakdownEngine",
            "Alpha001ParameterStabilityEngine",
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
        source = read_source(Path("research/alpha001_robustness_report.py"))
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
            "Alpha001SampleQualityEngine",
            "Alpha001OutlierEngine",
            "Alpha001RegimeBreakdownEngine",
            "Alpha001ParameterStabilityEngine",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def _report(self) -> Alpha001RobustnessResult:
        return Alpha001RobustnessResult(
            sample_quality=self._sample_quality(),
            outlier=self._outlier(),
            regime_breakdown=self._regime_breakdown(),
            parameter_stability=self._parameter_stability(),
        )

    def _sample_quality(self) -> Alpha001SampleQualityResult:
        return Alpha001SampleQualityResult(
            total_trading_days=1,
            average_trades_per_day=10.0,
            maximum_trades_per_day=10,
            minimum_trades_per_day=10,
            sufficient_sample=True,
        )

    def _outlier(self) -> Alpha001OutlierResult:
        return Alpha001OutlierResult(
            largest_winning_trade=40.0,
            largest_losing_trade=20.0,
            largest_trade_contribution_percent=20.0,
            outlier_detected=False,
        )

    def _regime_breakdown(self) -> Alpha001RegimeBreakdownResult:
        return Alpha001RegimeBreakdownResult(
            regimes={
                "TREND": Alpha001RegimeMetrics(
                    total_trades=10,
                    gross_profit=0.0,
                    gross_loss=0.0,
                    net_profit=0.0,
                    win_rate=0.0,
                ),
            },
        )

    def _parameter_stability(self) -> Alpha001ParameterStabilityResult:
        return Alpha001ParameterStabilityResult(
            variation_of_net_profit=10.0,
            variation_of_drawdown=5.0,
            variation_of_profit_factor=0.2,
            variation_of_win_rate=0.05,
            stable_strategy=True,
        )


if __name__ == "__main__":
    unittest.main()
