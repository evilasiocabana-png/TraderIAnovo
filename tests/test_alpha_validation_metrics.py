"""Testes das metricas consolidadas de validacao de Alpha."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha_factory.alpha_validation_metrics import (
    AlphaValidationMetricInput,
    AlphaValidationMetricsEngine,
    AlphaValidationMetricsReport,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaValidationMetricsTest(unittest.TestCase):
    """Protege relatorio quantitativo sem iniciar pesquisa."""

    def test_contratos_sao_dataclasses_imutaveis(self) -> None:
        self.assertTrue(is_dataclass(AlphaValidationMetricInput))
        self.assertTrue(AlphaValidationMetricInput.__dataclass_params__.frozen)
        self.assertTrue(is_dataclass(AlphaValidationMetricsReport))
        self.assertTrue(AlphaValidationMetricsReport.__dataclass_params__.frozen)

    def test_consolida_metricas_quantitativas_centrais(self) -> None:
        report = AlphaValidationMetricsEngine().summarize(
            "Alpha001",
            self._metrics(),
        )

        self.assertEqual(report.total_trades, 100)
        self.assertAlmostEqual(report.win_rate, 0.59)
        self.assertAlmostEqual(report.profit_factor, 1.7)
        self.assertAlmostEqual(report.expectancy, 4.4)
        self.assertAlmostEqual(report.max_drawdown, 20.0)
        self.assertAlmostEqual(report.mae, 7.2)
        self.assertAlmostEqual(report.mfe, 13.8)
        self.assertAlmostEqual(report.recovery_factor, 7.5)
        self.assertEqual(report.walk_forward_status, "APPROVED")
        self.assertEqual(report.out_of_sample_status, "APPROVED")
        self.assertEqual(report.validation_status, "APPROVED")
        self.assertEqual(report.warnings, ())

    def test_calcula_consistencia_por_par_e_timeframe(self) -> None:
        report = AlphaValidationMetricsEngine().summarize(
            "Alpha001",
            self._metrics(),
        )

        self.assertEqual(report.consistency_by_market, {"EURUSD": 1.0, "GBPUSD": 1.0})
        self.assertEqual(report.consistency_by_timeframe, {"H1": 1.0, "M15": 1.0})

    def test_sinaliza_falhas_de_walk_forward_e_out_of_sample(self) -> None:
        report = AlphaValidationMetricsEngine(
            minimum_trades=30,
            minimum_profit_factor=1.2,
            minimum_walk_forward_score=0.6,
            minimum_out_of_sample_score=0.6,
        ).summarize(
            "Alpha002",
            (
                AlphaValidationMetricInput(
                    alpha_id="Alpha002",
                    market="EURUSD",
                    timeframe="M15",
                    total_trades=12,
                    win_rate=0.45,
                    profit_factor=0.9,
                    expectancy=-1.0,
                    max_drawdown=30.0,
                    mae=11.0,
                    mfe=5.0,
                    net_profit=-12.0,
                    walk_forward_score=0.3,
                    out_of_sample_score=0.2,
                ),
            ),
        )

        self.assertEqual(report.validation_status, "REVIEW_REQUIRED")
        self.assertEqual(report.walk_forward_status, "FAILED")
        self.assertEqual(report.out_of_sample_status, "FAILED")
        self.assertIn("Amostra insuficiente.", report.warnings)
        self.assertIn("Profit factor abaixo do minimo.", report.warnings)
        self.assertIn("Walk-forward nao aprovado.", report.warnings)
        self.assertIn("Out-of-sample nao aprovado.", report.warnings)

    def test_estado_sem_metricas_e_seguro(self) -> None:
        report = AlphaValidationMetricsEngine().summarize("Alpha999", self._metrics())

        self.assertEqual(report.total_trades, 0)
        self.assertEqual(report.recovery_factor, 0.0)
        self.assertEqual(report.validation_status, "INSUFFICIENT_DATA")
        self.assertEqual(report.warnings, ("Sem metricas para a Alpha.",))

    def test_relatorio_e_imutavel(self) -> None:
        report = AlphaValidationMetricsEngine().summarize(
            "Alpha001",
            self._metrics(),
        )

        with self.assertRaises(FrozenInstanceError):
            report.total_trades = 0

    def test_engine_nao_executa_pesquisa_replay_dashboard_ou_ordens(self) -> None:
        source = read_source(Path("research/alpha_factory/alpha_validation_metrics.py"))
        forbidden_fragments = (
            "ResearchLab",
            "Replay",
            "dashboard",
            "streamlit",
            "MetaTrader5",
            "order_send",
            ".run(",
            "generate_signal",
            "open(",
            "Path(",
            "pandas",
        )

        leaked = [
            fragment
            for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]
        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_validation_metrics.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
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

    def _metrics(self) -> tuple[AlphaValidationMetricInput, ...]:
        return (
            AlphaValidationMetricInput(
                alpha_id="Alpha001",
                market="EURUSD",
                timeframe="M15",
                total_trades=60,
                win_rate=0.60,
                profit_factor=1.8,
                expectancy=5.0,
                max_drawdown=20.0,
                mae=8.0,
                mfe=14.0,
                net_profit=100.0,
                walk_forward_score=0.7,
                out_of_sample_score=0.8,
            ),
            AlphaValidationMetricInput(
                alpha_id="Alpha001",
                market="GBPUSD",
                timeframe="H1",
                total_trades=40,
                win_rate=0.575,
                profit_factor=1.55,
                expectancy=3.5,
                max_drawdown=15.0,
                mae=6.0,
                mfe=13.5,
                net_profit=50.0,
                walk_forward_score=0.65,
                out_of_sample_score=0.7,
            ),
        )


if __name__ == "__main__":
    unittest.main()
