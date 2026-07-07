"""Testes do motor de saude institucional de Alpha."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_winrate_engine import Alpha001WinRateResult
from research.alpha_factory.alpha_health_engine import (
    AlphaHealthEngine,
    AlphaHealthResult,
)
from research.campaigns.campaign_analyzer import CampaignAnalysisResult
from research.campaigns.campaign_report import CampaignReport
from research.campaigns.research_campaign import ResearchCampaign
from research.validation.experiment_validation_report import (
    ExperimentValidationReport,
)
from research.validation.experiment_validation_runner import (
    ValidationExecutionResult,
)
from research.validation.validation_rule import ValidationRule
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaHealthEngineTest(unittest.TestCase):
    """Valida avaliacao de saude sem recalcular pesquisas."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaHealthResult))
        self.assertTrue(AlphaHealthResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(AlphaHealthResult)],
            [
                "robustness_score",
                "reproducibility_score",
                "validation_score",
                "campaign_score",
                "health_score",
            ],
        )

    def test_result_e_imutavel(self) -> None:
        result = AlphaHealthResult(1.0, 1.0, 1.0, 1.0, 1.0)

        with self.assertRaises(FrozenInstanceError):
            result.health_score = 0.0

    def test_engine_calcula_scores_a_partir_de_resultados_existentes(self) -> None:
        result = AlphaHealthEngine().evaluate(
            research_result=self._research_result(
                profit_factor=1.5,
                win_rate=0.6,
                drawdown_percent=10.0,
            ),
            campaign_report=self._campaign_report(
                campaign_success_rate=0.8,
                reproducibility_score=0.7,
            ),
            validation_report=self._validation_report(
                total_rules=4,
                passed_rules=3,
            ),
        )

        self.assertAlmostEqual(result.robustness_score, 0.75)
        self.assertAlmostEqual(result.reproducibility_score, 0.7)
        self.assertAlmostEqual(result.validation_score, 0.75)
        self.assertAlmostEqual(result.campaign_score, 0.8)
        self.assertAlmostEqual(result.health_score, 0.75)

    def test_engine_limita_scores_entre_zero_e_um(self) -> None:
        result = AlphaHealthEngine().evaluate(
            research_result=self._research_result(
                profit_factor=4.0,
                win_rate=2.0,
                drawdown_percent=-20.0,
            ),
            campaign_report=self._campaign_report(
                campaign_success_rate=2.0,
                reproducibility_score=1.5,
            ),
            validation_report=self._validation_report(
                total_rules=2,
                passed_rules=3,
            ),
        )

        self.assertEqual(result.robustness_score, 1.0)
        self.assertEqual(result.reproducibility_score, 1.0)
        self.assertEqual(result.validation_score, 1.0)
        self.assertEqual(result.campaign_score, 1.0)
        self.assertEqual(result.health_score, 1.0)

    def test_reproducibility_score_tem_fallback_seguro(self) -> None:
        result = AlphaHealthEngine().evaluate(
            research_result=self._research_result(
                profit_factor=0.0,
                win_rate=0.0,
                drawdown_percent=100.0,
            ),
            campaign_report=self._campaign_report(
                campaign_success_rate=0.0,
                reproducibility_score="not-a-number",
            ),
            validation_report=self._validation_report(
                total_rules=0,
                passed_rules=0,
            ),
        )

        self.assertEqual(result.reproducibility_score, 0.0)
        self.assertEqual(result.validation_score, 0.0)
        self.assertEqual(result.health_score, 0.0)

    def test_engine_nao_recalcula_metricas_ou_executa_pesquisa(self) -> None:
        source = read_source(Path("research/alpha_factory/alpha_health_engine.py"))
        forbidden_fragments = (
            "ResearchPipeline",
            "ResearchRunner",
            "ReplayEngine",
            "Dashboard",
            "StrategySignal",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".run(",
            ".calculate(",
            ".validate(",
            "gross_profit_points =",
            "net_profit_points =",
            "max_drawdown_points =",
            "profit_factor =",
            "win_rate =",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_health_engine.py")
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
            "research.research_pipeline",
            "research.research_runner",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "validate",
            "recommend",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _research_result(
        self,
        profit_factor: float,
        win_rate: float,
        drawdown_percent: float,
    ) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(10, 4, 3, 3),
            profit=Alpha001ProfitResult(10.0, 5.0, 5.0),
            drawdown=Alpha001DrawdownResult(
                equity_curve=(0.0, 5.0),
                max_drawdown_points=1.0,
                max_drawdown_percent=drawdown_percent,
            ),
            win_rate=Alpha001WinRateResult(6, 3, 1, win_rate),
            profit_factor=Alpha001ProfitFactorResult(profit_factor),
            expectancy=Alpha001ExpectancyResult(10.0, 5.0, 2.0, 5.0),
        )

    def _campaign_report(
        self,
        campaign_success_rate: float,
        reproducibility_score: object,
    ) -> CampaignReport:
        campaign = ResearchCampaign(
            campaign_id="campaign-alpha001-001",
            name="Alpha health campaign",
            description="Campanha de saude.",
            alpha_id="Alpha001",
            objective="Avaliar saude institucional.",
            status="COMPLETED",
            created_at="2026-06-28T02:30:00-03:00",
            created_by="Research",
            metadata={},
        )
        analysis = CampaignAnalysisResult(
            total_experiments=5,
            successful_experiments=4,
            failed_experiments=1,
            approved_experiments=3,
            rejected_experiments=1,
            average_execution_time=2.0,
            campaign_success_rate=campaign_success_rate,
        )
        return CampaignReport(
            campaign=campaign,
            analysis=analysis,
            campaign_id=campaign.campaign_id,
            alpha_id=campaign.alpha_id,
            total_experiments=analysis.total_experiments,
            successful_experiments=analysis.successful_experiments,
            failed_experiments=analysis.failed_experiments,
            approved_experiments=analysis.approved_experiments,
            rejected_experiments=analysis.rejected_experiments,
            campaign_success_rate=campaign_success_rate,
            execution_time=10.0,
            metadata={"reproducibility_score": reproducibility_score},
        )

    def _validation_report(
        self,
        total_rules: int,
        passed_rules: int,
    ) -> ExperimentValidationReport:
        passed = tuple(self._rule(f"passed-{index}") for index in range(passed_rules))
        failed = tuple(
            self._rule(f"failed-{index}")
            for index in range(max(0, total_rules - passed_rules))
        )
        rules = (*passed, *failed)
        return ExperimentValidationReport(
            validation_result=ValidationExecutionResult(passed, failed, ()),
            rules=rules,
            total_rules=total_rules,
            passed_rules=passed,
            failed_rules=failed,
            skipped_rules=(),
            validation_messages=(),
            execution_time=1.0,
        )

    def _rule(self, rule_id: str) -> ValidationRule:
        return ValidationRule(
            rule_id=rule_id,
            name=rule_id,
            description="Regra de teste.",
            severity="LOW",
            threshold=1.0,
            enabled=True,
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
