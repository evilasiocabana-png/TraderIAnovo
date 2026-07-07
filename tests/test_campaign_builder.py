"""Testes do construtor de campanhas de pesquisa."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.campaigns.campaign_builder import CampaignBuilder
from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import ExperimentDefinition
from tests.architecture_test_utils import calls_from, imports_from, read_source


class CampaignBuilderTest(unittest.TestCase):
    """Valida montagem de experimentos sem execucao operacional."""

    def test_builder_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(CampaignBuilder))
        self.assertTrue(CampaignBuilder.__dataclass_params__.frozen)

    def test_builder_gera_definicoes_de_experimento(self) -> None:
        campaign = self._campaign()
        template = self._template()

        experiments = CampaignBuilder().build(campaign, template)

        self.assertEqual(len(experiments), 8)
        self.assertTrue(all(isinstance(item, ExperimentDefinition) for item in experiments))
        self.assertEqual(experiments[0].experiment_id, "campaign-alpha001-001-001")
        self.assertEqual(experiments[-1].experiment_id, "campaign-alpha001-001-008")

    def test_builder_expande_datasets_replay_configuracoes_e_parametros(self) -> None:
        experiments = CampaignBuilder().build(self._campaign(), self._template())

        datasets = {experiment.dataset for experiment in experiments}
        replay_periods = {experiment.replay_period for experiment in experiments}
        configuration_versions = {
            experiment.configuration_version for experiment in experiments
        }
        parameters = {
            experiment.metadata["parameters"]["stop"] for experiment in experiments
        }

        self.assertEqual(datasets, {"WDO-1m-2026-01", "WDO-1m-2026-02"})
        self.assertEqual(
            replay_periods,
            {"2026-01-01/2026-01-31", "2026-02-01/2026-02-28"},
        )
        self.assertEqual(configuration_versions, {"cfg-001"})
        self.assertEqual(parameters, {50, 60})

    def test_builder_vincula_campanha_aos_experimentos(self) -> None:
        experiments = CampaignBuilder().build(self._campaign(), self._template())
        first = experiments[0]

        self.assertEqual(first.alpha_id, "Alpha001")
        self.assertEqual(first.status, "PENDING")
        self.assertEqual(first.created_at, "2026-06-28T00:50:00-03:00")
        self.assertEqual(first.metadata["campaign_id"], "campaign-alpha001-001")
        self.assertEqual(first.metadata["campaign_name"], "Alpha001 baseline research")

    def test_builder_preserva_template_quando_campanha_nao_declara_valores(self) -> None:
        campaign = ResearchCampaign(
            campaign_id="campaign-alpha001-002",
            name="Fallback campaign",
            description="Campanha sem expansoes declaradas.",
            alpha_id="Alpha001",
            objective="Validar fallback.",
            status="PENDING",
            created_at="2026-06-28T00:55:00-03:00",
            created_by="CTO",
            metadata={},
        )
        template = self._template()

        experiments = CampaignBuilder().build(campaign, template)

        self.assertEqual(len(experiments), 1)
        self.assertEqual(experiments[0].dataset, template.dataset)
        self.assertEqual(experiments[0].replay_period, template.replay_period)
        self.assertEqual(
            experiments[0].configuration_version,
            template.configuration_version,
        )

    def test_builder_nao_altera_template(self) -> None:
        template = self._template()

        CampaignBuilder().build(self._campaign(), template)

        self.assertEqual(template.experiment_id, "template-alpha001")
        self.assertEqual(template.dataset, "WDO-template")
        self.assertEqual(template.status, "DRAFT")

    def test_builder_e_imutavel(self) -> None:
        builder = CampaignBuilder()

        with self.assertRaises(FrozenInstanceError):
            builder.extra = "blocked"

    def test_builder_nao_executa_experimentos_ou_acessa_camadas(self) -> None:
        source = read_source(Path("research/campaigns/campaign_builder.py"))
        forbidden_fragments = (
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

    def test_builder_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/campaigns/campaign_builder.py")
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
            created_at="2026-06-28T00:50:00-03:00",
            created_by="CTO",
            metadata={
                "datasets": ("WDO-1m-2026-01", "WDO-1m-2026-02"),
                "replay_periods": (
                    "2026-01-01/2026-01-31",
                    "2026-02-01/2026-02-28",
                ),
                "configuration_versions": ("cfg-001",),
                "parameters": (
                    {"stop": 50, "target": 100},
                    {"stop": 60, "target": 120},
                ),
            },
        )

    def _template(self) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id="template-alpha001",
            alpha_id="Alpha001",
            alpha_version="1.0.0",
            configuration_version="cfg-template",
            replay_period="template-period",
            dataset="WDO-template",
            status="DRAFT",
            priority=1,
            created_at="2026-06-28T00:45:00-03:00",
            metadata={"source": "template"},
        )


if __name__ == "__main__":
    unittest.main()
