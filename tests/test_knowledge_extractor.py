"""Testes do extrator deterministico de conhecimento."""

from datetime import datetime
from pathlib import Path
import unittest

from research.alpha001_experiment import Alpha001ExperimentResult
from research.campaigns.campaign_analyzer import CampaignAnalysisResult
from research.campaigns.campaign_report import CampaignReport
from research.campaigns.research_campaign import ResearchCampaign
from research.knowledge.knowledge_artifact import KnowledgeArtifact
from research.knowledge.knowledge_extractor import KnowledgeExtractor
from research.research_report import ResearchReport
from research.validation.experiment_validation_report import (
    ExperimentValidationReport,
)
from research.validation.experiment_validation_runner import (
    ValidationExecutionResult,
)
from research.validation.validation_rule import ValidationRule
from tests.architecture_test_utils import calls_from, imports_from, read_source


class KnowledgeExtractorTest(unittest.TestCase):
    """Valida extracao deterministica sem IA ou execucao de pesquisa."""

    def test_extrai_seis_artefatos_tipados(self) -> None:
        artifacts = KnowledgeExtractor().extract(
            research_report=self._research_report(),
            campaign_report=self._campaign_report(),
            validation_report=self._validation_report(),
            created_at=datetime(2026, 6, 28, 13, 0, 0),
        )

        self.assertEqual(len(artifacts), 6)
        self.assertTrue(all(isinstance(item, KnowledgeArtifact) for item in artifacts))
        self.assertEqual(
            tuple(item.metadata["category"] for item in artifacts),
            (
                "stable_parameters",
                "unstable_parameters",
                "favorable_contexts",
                "unfavorable_contexts",
                "predominant_regimes",
                "limitations",
            ),
        )

    def test_extrai_evidencias_de_metadata_da_campanha(self) -> None:
        artifacts = KnowledgeExtractor().extract(
            research_report=self._research_report(),
            campaign_report=self._campaign_report(),
            validation_report=self._validation_report(),
            created_at=datetime(2026, 6, 28, 13, 0, 0),
        )
        by_category = {item.metadata["category"]: item for item in artifacts}

        self.assertEqual(
            by_category["stable_parameters"].evidence,
            ("stop=50", "target=100"),
        )
        self.assertEqual(
            by_category["unstable_parameters"].evidence,
            ("minimum_volume",),
        )
        self.assertEqual(
            by_category["favorable_contexts"].evidence,
            ("abertura com volume",),
        )
        self.assertEqual(
            by_category["unfavorable_contexts"].evidence,
            ("baixa liquidez",),
        )
        self.assertEqual(
            by_category["predominant_regimes"].evidence,
            ("TREND", "VOLATILE"),
        )
        self.assertEqual(
            by_category["limitations"].evidence,
            ("amostra curta",),
        )

    def test_artifacts_preservam_identificadores_e_confianca(self) -> None:
        created_at = datetime(2026, 6, 28, 13, 0, 0)

        artifacts = KnowledgeExtractor().extract(
            research_report=self._research_report(),
            campaign_report=self._campaign_report(),
            validation_report=self._validation_report(),
            created_at=created_at,
        )

        first = artifacts[0]
        self.assertEqual(first.artifact_id, "campaign-alpha003-001:stable_parameters")
        self.assertEqual(first.alpha_id, "Alpha003")
        self.assertEqual(first.research_id, "research-alpha003-001")
        self.assertEqual(first.campaign_id, "campaign-alpha003-001")
        self.assertEqual(first.conclusion, "ACCEPTABLE")
        self.assertEqual(first.confidence, 0.82)
        self.assertEqual(first.created_at, created_at)

    def test_extrai_fallbacks_quando_metadata_nao_informa_categorias(self) -> None:
        artifacts = KnowledgeExtractor().extract(
            research_report=self._research_report(),
            campaign_report=self._campaign_report(metadata={}),
            validation_report=self._validation_report(),
            created_at=datetime(2026, 6, 28, 13, 0, 0),
        )
        by_category = {item.metadata["category"]: item for item in artifacts}

        self.assertIn("opening_range=15", by_category["stable_parameters"].evidence)
        self.assertEqual(
            by_category["unstable_parameters"].evidence,
            ("minimum_profit_factor",),
        )
        self.assertEqual(
            by_category["limitations"].evidence,
            ("Regra falhou: minimum_profit_factor", "Profit factor baixo."),
        )

    def test_confidence_e_limitada_entre_zero_e_um(self) -> None:
        high = KnowledgeExtractor().extract(
            research_report=self._research_report(),
            campaign_report=self._campaign_report(
                metadata={"knowledge_confidence": 2.0},
            ),
            validation_report=self._validation_report(),
            created_at=datetime(2026, 6, 28, 13, 0, 0),
        )
        invalid = KnowledgeExtractor().extract(
            research_report=self._research_report(),
            campaign_report=self._campaign_report(
                metadata={"knowledge_confidence": "unknown"},
            ),
            validation_report=self._validation_report(),
            created_at=datetime(2026, 6, 28, 13, 0, 0),
        )

        self.assertEqual(high[0].confidence, 1.0)
        self.assertEqual(invalid[0].confidence, 0.0)

    def test_extractor_nao_usa_ia_ml_ou_execucao_operacional(self) -> None:
        source = read_source(Path("research/knowledge/knowledge_extractor.py"))
        forbidden_fragments = (
            "openai",
            "llm",
            "chatgpt",
            "machine_learning",
            "sklearn",
            "ResearchPipeline",
            "ResearchRunner",
            "AlphaFactory",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".run(",
            ".calculate(",
            ".validate(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_extractor_permanece_desacoplado_das_camadas_proibidas(self) -> None:
        path = Path("research/knowledge/knowledge_extractor.py")
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
            "research.alpha_factory",
            "broker",
            "mt5",
            "MetaTrader5",
            "openai",
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

    def _research_report(self) -> ResearchReport:
        return ResearchReport(
            parameters={
                "opening_range": 15,
                "stop": 50,
                "target": 100,
            },
            experiment_result=Alpha001ExperimentResult(
                total_candles=100,
                total_signals=20,
                total_buy=10,
                total_sell=5,
                total_wait=5,
                execution_time_ms=12.5,
                signals=(),
            ),
        )

    def _campaign_report(
        self,
        metadata: dict[str, object] | None = None,
    ) -> CampaignReport:
        values = {
            "research_id": "research-alpha003-001",
            "knowledge_confidence": 0.82,
            "stable_parameters": ("stop=50", "target=100"),
            "unstable_parameters": ("minimum_volume",),
            "favorable_contexts": ("abertura com volume",),
            "unfavorable_contexts": ("baixa liquidez",),
            "predominant_regimes": ("TREND", "VOLATILE"),
            "limitations": ("amostra curta",),
        }
        if metadata is not None:
            values = metadata
        campaign = ResearchCampaign(
            campaign_id="campaign-alpha003-001",
            name="Alpha003 research campaign",
            description="Campanha de pesquisa.",
            alpha_id="Alpha003",
            objective="Extrair conhecimento.",
            status="COMPLETED",
            created_at="2026-06-28T13:00:00-03:00",
            created_by="Research",
            metadata={},
        )
        analysis = CampaignAnalysisResult(
            total_experiments=4,
            successful_experiments=3,
            failed_experiments=1,
            approved_experiments=2,
            rejected_experiments=1,
            average_execution_time=2.0,
            campaign_success_rate=0.75,
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
            campaign_success_rate=analysis.campaign_success_rate,
            execution_time=8.0,
            metadata=values,
        )

    def _validation_report(self) -> ExperimentValidationReport:
        failed = self._rule("minimum_profit_factor")
        passed = self._rule("minimum_trades")
        return ExperimentValidationReport(
            validation_result=ValidationExecutionResult((passed,), (failed,), ()),
            rules=(passed, failed),
            total_rules=2,
            passed_rules=(passed,),
            failed_rules=(failed,),
            skipped_rules=(),
            validation_messages=("Profit factor baixo.",),
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
