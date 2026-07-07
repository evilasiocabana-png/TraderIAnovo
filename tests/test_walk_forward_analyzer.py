"""Testes do analyzer de resultados Walk-Forward."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.walk_forward_analyzer import (
    WalkForwardAnalysisResult,
    WalkForwardAnalyzer,
)
from research.validation.walk_forward_engine import WalkForwardResult
from research.validation.walk_forward_profile import WalkForwardProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class WalkForwardAnalyzerTest(unittest.TestCase):
    """Valida analise estrutural sem recalcular metricas das Alphas."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(WalkForwardAnalysisResult))
        self.assertTrue(WalkForwardAnalysisResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(WalkForwardAnalysisResult)],
            [
                "stability_score",
                "degradation_score",
                "consistency_score",
                "validation_score",
            ],
        )

    def test_analyzer_calcula_scores_estaveis(self) -> None:
        result = WalkForwardAnalyzer().analyze(
            self._walk_forward_result(
                training=("COMPLETED", "COMPLETED"),
                validation=("COMPLETED", "COMPLETED"),
                testing=("COMPLETED",),
            )
        )

        self.assertEqual(result.stability_score, 1.0)
        self.assertEqual(result.degradation_score, 0.0)
        self.assertEqual(result.consistency_score, 1.0)
        self.assertEqual(result.validation_score, 1.0)

    def test_analyzer_detecta_degradacao_entre_janelas(self) -> None:
        result = WalkForwardAnalyzer().analyze(
            self._walk_forward_result(
                training=("COMPLETED", "COMPLETED"),
                validation=("COMPLETED", "FAILED"),
                testing=("FAILED",),
            )
        )

        self.assertEqual(result.stability_score, 1.0)
        self.assertEqual(result.degradation_score, 1.0)
        self.assertEqual(result.consistency_score, 0.0)
        self.assertLess(result.validation_score, 0.6)

    def test_analyzer_retorna_zero_para_janelas_vazias(self) -> None:
        result = WalkForwardAnalyzer().analyze(
            self._walk_forward_result(training=(), validation=(), testing=())
        )

        self.assertEqual(result.stability_score, 0.0)
        self.assertEqual(result.degradation_score, 0.0)
        self.assertEqual(result.consistency_score, 1.0)
        self.assertEqual(result.validation_score, 0.4)

    def test_result_e_imutavel(self) -> None:
        result = WalkForwardAnalyzer().analyze(
            self._walk_forward_result(
                training=("COMPLETED",),
                validation=("COMPLETED",),
                testing=("COMPLETED",),
            )
        )

        with self.assertRaises(FrozenInstanceError):
            result.validation_score = 0.0

    def test_analyzer_nao_recalcula_metricas_ou_altera_pipeline(self) -> None:
        source = read_source(Path("research/validation/walk_forward_analyzer.py"))
        forbidden_fragments = (
            "ResearchPipeline",
            "ResearchRunner",
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
            "Alpha001DrawdownEngine",
            "Alpha001WinRateEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001ExpectancyEngine",
            "net_profit",
            "profit_factor",
            "win_rate",
            "max_drawdown",
            "ReplayEngine",
            ".run(",
            ".calculate(",
            ".next_candle(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_analyzer_permanece_desacoplado_de_domain_e_operacao(self) -> None:
        path = Path("research/validation/walk_forward_analyzer.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.research_runner",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "database",
            "openai",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "calculate",
            "validate",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _walk_forward_result(
        self,
        training: tuple[str, ...],
        validation: tuple[str, ...],
        testing: tuple[str, ...],
    ) -> WalkForwardResult:
        training_experiments = tuple(
            self._experiment(f"training-{index}", status)
            for index, status in enumerate(training)
        )
        validation_experiments = tuple(
            self._experiment(f"validation-{index}", status)
            for index, status in enumerate(validation)
        )
        testing_experiments = tuple(
            self._experiment(f"testing-{index}", status)
            for index, status in enumerate(testing)
        )
        return WalkForwardResult(
            campaign_id="campaign-alpha001-wf",
            profile=self._profile(),
            executed_experiments=(
                *training_experiments,
                *validation_experiments,
                *testing_experiments,
            ),
            training_experiments=training_experiments,
            validation_experiments=validation_experiments,
            testing_experiments=testing_experiments,
            rolling_window=1,
            minimum_samples=100,
        )

    def _experiment(
        self,
        experiment_id: str,
        status: str,
    ) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id=experiment_id,
            alpha_id="Alpha001",
            alpha_version="1.0",
            configuration_version="cfg-001",
            replay_period="2026-01",
            dataset="WDO-1m",
            status=status,
            priority=1,
            created_at="2026-06-28T06:00:00-03:00",
            metadata={},
        )

    def _profile(self) -> WalkForwardProfile:
        return WalkForwardProfile(
            profile_id="walk-forward-balanced-001",
            training_window=2,
            validation_window=2,
            testing_window=1,
            rolling_window=1,
            minimum_samples=100,
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
