"""Testes do relatorio oficial de campanhas."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.campaigns.campaign_analyzer import CampaignAnalysisResult
from research.campaigns.campaign_report import CampaignReport
from research.campaigns.research_campaign import ResearchCampaign
from tests.architecture_test_utils import calls_from, imports_from, read_source


class CampaignReportTest(unittest.TestCase):
    """Valida consolidacao sem calculo ou geracao de saida."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(CampaignReport))
        self.assertTrue(CampaignReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(CampaignReport)]

        self.assertEqual(
            field_names,
            [
                "campaign",
                "analysis",
                "campaign_id",
                "alpha_id",
                "total_experiments",
                "successful_experiments",
                "failed_experiments",
                "approved_experiments",
                "rejected_experiments",
                "campaign_success_rate",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = CampaignReport.__annotations__

        self.assertEqual(annotations["campaign"], "ResearchCampaign")
        self.assertEqual(annotations["analysis"], "CampaignAnalysisResult")
        self.assertEqual(annotations["campaign_id"], "str")
        self.assertEqual(annotations["alpha_id"], "str")
        self.assertEqual(annotations["total_experiments"], "int")
        self.assertEqual(annotations["successful_experiments"], "int")
        self.assertEqual(annotations["failed_experiments"], "int")
        self.assertEqual(annotations["approved_experiments"], "int")
        self.assertEqual(annotations["rejected_experiments"], "int")
        self.assertEqual(annotations["campaign_success_rate"], "float")
        self.assertEqual(annotations["execution_time"], "float")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.campaign, ResearchCampaign)
        self.assertIsInstance(report.analysis, CampaignAnalysisResult)
        self.assertEqual(report.campaign_id, "campaign-alpha001-001")
        self.assertEqual(report.alpha_id, "Alpha001")
        self.assertEqual(report.total_experiments, 3)
        self.assertEqual(report.successful_experiments, 2)
        self.assertEqual(report.failed_experiments, 1)
        self.assertEqual(report.approved_experiments, 1)
        self.assertEqual(report.rejected_experiments, 1)
        self.assertEqual(report.campaign_success_rate, 2 / 3)
        self.assertEqual(report.execution_time, 12.5)
        self.assertEqual(report.metadata["source"], "unit-test")

    def test_report_preserva_referencias_recebidas(self) -> None:
        campaign = self._campaign()
        analysis = self._analysis()
        metadata = {"source": "unit-test"}

        report = CampaignReport(
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
            execution_time=12.5,
            metadata=metadata,
        )

        self.assertIs(report.campaign, campaign)
        self.assertIs(report.analysis, analysis)
        self.assertIs(report.metadata, metadata)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.total_experiments = 0

    def test_report_nao_calcula_ou_gera_saida(self) -> None:
        source = read_source(Path("research/campaigns/campaign_report.py"))
        forbidden_fragments = (
            "def ",
            "len(",
            "sum(",
            "max(",
            "min(",
            "round(",
            "Dashboard",
            "streamlit",
            "HTML",
            "PDF",
            "open(",
            "write(",
            "persist",
            "ResearchRunner",
            "ResearchPipeline",
            "ExperimentScheduler",
            ".run(",
            ".execute(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/campaigns/campaign_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
            "research.experiment_management.experiment_scheduler",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "database",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "enqueue",
            "dequeue",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> CampaignReport:
        campaign = self._campaign()
        analysis = self._analysis()
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
            execution_time=12.5,
            metadata={"source": "unit-test"},
        )

    def _campaign(self) -> ResearchCampaign:
        return ResearchCampaign(
            campaign_id="campaign-alpha001-001",
            name="Alpha001 baseline research",
            description="Campanha inicial de pesquisa.",
            alpha_id="Alpha001",
            objective="Validar baseline estatistico.",
            status="PENDING",
            created_at="2026-06-28T01:10:00-03:00",
            created_by="CTO",
            metadata={"source": "unit-test"},
        )

    def _analysis(self) -> CampaignAnalysisResult:
        return CampaignAnalysisResult(
            total_experiments=3,
            successful_experiments=2,
            failed_experiments=1,
            approved_experiments=1,
            rejected_experiments=1,
            average_execution_time=4.0,
            campaign_success_rate=2 / 3,
        )


if __name__ == "__main__":
    unittest.main()
