"""Testes do executor de regras de validacao do Research Lab."""

from dataclasses import FrozenInstanceError, is_dataclass
from datetime import datetime
from pathlib import Path
import unittest

from research.alpha001_benchmark_comparator import Alpha001BenchmarkResult
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_advisor import Alpha001ResearchRecommendation
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_research_validator import Alpha001ResearchValidationResult
from research.alpha001_winrate_engine import Alpha001WinRateResult
from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage
from research.validation.experiment_validation_runner import (
    ExperimentValidationRunner,
    ValidationExecutionResult,
)
from research.validation.validation_rule import ValidationRule
from research.validation.validation_rule_registry import ValidationRuleRegistry
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ExperimentValidationRunnerTest(unittest.TestCase):
    """Valida execucao de regras sem recalcular metricas."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ValidationExecutionResult))
        self.assertTrue(ValidationExecutionResult.__dataclass_params__.frozen)

    def test_runner_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ExperimentValidationRunner))
        self.assertTrue(ExperimentValidationRunner.__dataclass_params__.frozen)

    def test_resultado_e_imutavel(self) -> None:
        result = ValidationExecutionResult((), (), ())

        with self.assertRaises(FrozenInstanceError):
            result.passed_rules = ()

    def test_executa_regras_registradas_e_classifica_passed_e_skipped(self) -> None:
        result = ExperimentValidationRunner().run(
            self._execution_result(),
            ValidationRuleRegistry(),
        )

        self.assertEqual(
            tuple(rule.rule_id for rule in result.passed_rules),
            (
                "minimum_trades",
                "maximum_drawdown",
                "minimum_profit_factor",
                "minimum_win_rate",
            ),
        )
        self.assertEqual(result.failed_rules, ())
        self.assertEqual(
            tuple(rule.rule_id for rule in result.skipped_rules),
            ("maximum_outlier_dependency",),
        )

    def test_classifica_regras_falhas(self) -> None:
        result = ExperimentValidationRunner().run(
            self._execution_result(
                total_trades=10,
                max_drawdown=150.0,
                profit_factor=0.8,
                win_rate=0.2,
            ),
            ValidationRuleRegistry(),
        )

        self.assertEqual(result.passed_rules, ())
        self.assertEqual(
            tuple(rule.rule_id for rule in result.failed_rules),
            (
                "minimum_trades",
                "maximum_drawdown",
                "minimum_profit_factor",
                "minimum_win_rate",
            ),
        )
        self.assertEqual(
            tuple(rule.rule_id for rule in result.skipped_rules),
            ("maximum_outlier_dependency",),
        )

    def test_regra_desabilitada_e_skipped(self) -> None:
        registry = ValidationRuleRegistry()
        registry.register(
            ValidationRule(
                rule_id="minimum_trades",
                name="Minimum Trades Disabled",
                description="Regra desabilitada em teste.",
                severity="LOW",
                threshold=30.0,
                enabled=False,
                metadata={},
            )
        )

        result = ExperimentValidationRunner().run(
            self._execution_result(),
            registry,
        )

        self.assertNotIn(
            "minimum_trades",
            tuple(rule.rule_id for rule in result.passed_rules),
        )
        self.assertIn(
            "minimum_trades",
            tuple(rule.rule_id for rule in result.skipped_rules),
        )

    def test_regra_desconhecida_e_skipped(self) -> None:
        registry = ValidationRuleRegistry()
        registry.register(
            ValidationRule(
                rule_id="unknown_rule",
                name="Unknown",
                description="Regra sem executor.",
                severity="LOW",
                threshold=1.0,
                enabled=True,
                metadata={},
            )
        )

        result = ExperimentValidationRunner().run(
            self._execution_result(),
            registry,
        )

        self.assertIn(
            "unknown_rule",
            tuple(rule.rule_id for rule in result.skipped_rules),
        )

    def test_runner_reutiliza_research_validator_existente(self) -> None:
        source = read_source(Path("research/validation/experiment_validation_runner.py"))

        self.assertIn("Alpha001ResearchValidator", source)
        self.assertIn("validator.validate(execution_result.research_report)", source)

    def test_runner_nao_altera_runner_pipeline_ou_acessa_operacao(self) -> None:
        source = read_source(Path("research/validation/experiment_validation_runner.py"))
        forbidden_fragments = (
            "ResearchRunner",
            "ResearchPipeline",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".next_candle(",
            ".generate_signal(",
            "sum(",
            "max(",
            "min(",
            "round(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_runner_permanece_desacoplado_de_domain_e_camadas_operacionais(self) -> None:
        path = Path("research/validation/experiment_validation_runner.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
            "alpha",
            "strategies",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "paper",
            "database",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _execution_result(
        self,
        *,
        total_trades: int = 35,
        max_drawdown: float = 50.0,
        profit_factor: float = 1.5,
        win_rate: float = 0.5,
    ) -> ResearchExecutionResult:
        research = self._research_result(
            total_trades=total_trades,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            win_rate=win_rate,
        )
        return ResearchExecutionResult(
            experiment=Alpha001ExperimentResult(0, 0, 0, 0, 0, 0.0, ()),
            metrics=research.metrics,
            profit=research.profit,
            drawdown=research.drawdown,
            win_rate=research.win_rate,
            profit_factor=research.profit_factor,
            expectancy=research.expectancy,
            benchmark=Alpha001BenchmarkResult(0, None, None, None, None, None, None, None, ()),
            research_report=research,
            validation=Alpha001ResearchValidationResult(
                approved=True,
                status="APPROVED",
                reasons=("ok",),
                minimum_trades=1,
                minimum_profit_factor=1.0,
                maximum_drawdown=10.0,
                minimum_win_rate=0.1,
                real_trading_authorized=False,
            ),
            recommendation=Alpha001ResearchRecommendation(
                recommendation="APPROVED_FOR_MORE_RESEARCH",
                status="APPROVED",
                reasons=("ok",),
                real_trading_authorized=False,
            ),
            stage_results=(),
            started_at=datetime(2026, 6, 27, 10, 0, 0),
            finished_at=datetime(2026, 6, 27, 10, 0, 12),
            duration=12.0,
            status=ResearchStage.COMPLETED,
            errors=(),
        )

    def _research_result(
        self,
        *,
        total_trades: int,
        max_drawdown: float,
        profit_factor: float,
        win_rate: float,
    ) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(total_trades, 10, 10, 0),
            profit=Alpha001ProfitResult(0.0, 0.0, 0.0),
            drawdown=Alpha001DrawdownResult((0.0,), max_drawdown, 0.0),
            win_rate=Alpha001WinRateResult(0, 0, 0, win_rate),
            profit_factor=Alpha001ProfitFactorResult(profit_factor),
            expectancy=Alpha001ExpectancyResult(0.0, 0.0, 0.0, 0.0),
        )


if __name__ == "__main__":
    unittest.main()
