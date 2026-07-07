"""Testes do contrato oficial de campanha de pesquisa."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.campaigns.research_campaign import ResearchCampaign
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchCampaignTest(unittest.TestCase):
    """Valida contrato puro para campanhas de pesquisa."""

    def test_campaign_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ResearchCampaign))
        self.assertTrue(ResearchCampaign.__dataclass_params__.frozen)

    def test_campaign_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ResearchCampaign)]

        self.assertEqual(
            field_names,
            [
                "campaign_id",
                "name",
                "description",
                "alpha_id",
                "objective",
                "status",
                "created_at",
                "created_by",
                "metadata",
            ],
        )

    def test_campaign_possui_type_hints_explicitos(self) -> None:
        annotations = ResearchCampaign.__annotations__

        self.assertEqual(annotations["campaign_id"], "str")
        self.assertEqual(annotations["name"], "str")
        self.assertEqual(annotations["description"], "str")
        self.assertEqual(annotations["alpha_id"], "str")
        self.assertEqual(annotations["objective"], "str")
        self.assertEqual(annotations["status"], "str")
        self.assertEqual(annotations["created_at"], "str")
        self.assertEqual(annotations["created_by"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_campaign_representa_campanha_de_pesquisa(self) -> None:
        campaign = self._campaign()

        self.assertEqual(campaign.campaign_id, "campaign-alpha001-001")
        self.assertEqual(campaign.name, "Alpha001 baseline research")
        self.assertEqual(campaign.description, "Campanha inicial de pesquisa.")
        self.assertEqual(campaign.alpha_id, "Alpha001")
        self.assertEqual(campaign.objective, "Validar baseline estatistico.")
        self.assertEqual(campaign.status, "PENDING")
        self.assertEqual(campaign.created_at, "2026-06-28T00:45:00-03:00")
        self.assertEqual(campaign.created_by, "CTO")
        self.assertEqual(campaign.metadata["source"], "unit-test")

    def test_campaign_preserva_metadata_recebido(self) -> None:
        metadata = {"source": "unit-test"}

        campaign = ResearchCampaign(
            campaign_id="campaign-alpha001-001",
            name="Alpha001 baseline research",
            description="Campanha inicial de pesquisa.",
            alpha_id="Alpha001",
            objective="Validar baseline estatistico.",
            status="PENDING",
            created_at="2026-06-28T00:45:00-03:00",
            created_by="CTO",
            metadata=metadata,
        )

        self.assertIs(campaign.metadata, metadata)

    def test_campaign_e_imutavel(self) -> None:
        campaign = self._campaign()

        with self.assertRaises(FrozenInstanceError):
            campaign.status = "RUNNING"

    def test_campaign_nao_executa_experimentos_ou_acessa_camadas(self) -> None:
        source = read_source(Path("research/campaigns/research_campaign.py"))
        forbidden_fragments = (
            "def ",
            "ResearchRunner",
            "ResearchPipeline",
            "ExperimentScheduler",
            "ExperimentQueue",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".dequeue(",
            ".enqueue(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_campaign_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/campaigns/research_campaign.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
            "research.experiment_management.experiment_scheduler",
            "research.experiment_management.experiment_queue",
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

    def _campaign(self) -> ResearchCampaign:
        return ResearchCampaign(
            campaign_id="campaign-alpha001-001",
            name="Alpha001 baseline research",
            description="Campanha inicial de pesquisa.",
            alpha_id="Alpha001",
            objective="Validar baseline estatistico.",
            status="PENDING",
            created_at="2026-06-28T00:45:00-03:00",
            created_by="CTO",
            metadata={"source": "unit-test"},
        )


if __name__ == "__main__":
    unittest.main()
