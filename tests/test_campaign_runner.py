"""Testes do executor oficial de campanhas de pesquisa."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.campaigns.campaign_builder import CampaignBuilder
from research.campaigns.campaign_runner import CampaignRunner
from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import ExperimentDefinition
from research.experiment_management.experiment_queue import ExperimentQueue
from tests.architecture_test_utils import calls_from, imports_from, read_source


class CampaignRunnerTest(unittest.TestCase):
    """Valida orquestracao de campanha sem execucao direta."""

    def test_runner_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(CampaignRunner))
        self.assertTrue(CampaignRunner.__dataclass_params__.frozen)

    def test_runner_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(CampaignRunner)]

        self.assertEqual(field_names, ["queue", "scheduler", "builder", "template"])

    def test_runner_possui_type_hints_explicitos(self) -> None:
        annotations = CampaignRunner.__annotations__

        self.assertEqual(annotations["queue"], "ExperimentQueue")
        self.assertEqual(annotations["scheduler"], "ExperimentScheduler")
        self.assertEqual(annotations["builder"], "CampaignBuilder")
        self.assertEqual(annotations["template"], "ExperimentDefinition")

    def test_runner_enfileira_experimentos_e_delega_ao_scheduler(self) -> None:
        calls: list[str] = []
        queue = _QueueSpy(calls)
        builder = _BuilderSpy(calls, self._definitions())
        scheduler = _SchedulerSpy(calls, self._definitions())
        runner = CampaignRunner(queue, scheduler, builder, self._template())

        result = runner.run(self._campaign())

        self.assertEqual(
            calls,
            [
                "builder",
                "enqueue:exp-001",
                "enqueue:exp-002",
                "scheduler.run_all",
            ],
        )
        self.assertEqual([item.experiment_id for item in result], ["exp-001", "exp-002"])
        self.assertEqual(queue.size(), 2)

    def test_runner_retorna_resultado_do_scheduler(self) -> None:
        scheduled = self._definitions()
        runner = CampaignRunner(
            _QueueSpy([]),
            _SchedulerSpy([], scheduled),
            _BuilderSpy([], scheduled),
            self._template(),
        )

        result = runner.run(self._campaign())

        self.assertIs(result, scheduled)

    def test_runner_aceita_builder_real(self) -> None:
        calls: list[str] = []
        queue = _QueueSpy(calls)
        scheduler = _SchedulerSpy(calls, ())
        runner = CampaignRunner(queue, scheduler, CampaignBuilder(), self._template())

        runner.run(self._campaign())

        self.assertEqual(queue.size(), 2)
        self.assertEqual(queue.items[0].metadata["campaign_id"], "campaign-alpha001-001")
        self.assertIn("scheduler.run_all", calls)

    def test_runner_e_imutavel(self) -> None:
        runner = CampaignRunner(
            _QueueSpy([]),
            _SchedulerSpy([], ()),
            _BuilderSpy([], ()),
            self._template(),
        )

        with self.assertRaises(FrozenInstanceError):
            runner.template = self._definition("changed")

    def test_runner_nao_executa_pesquisas_diretamente_ou_usa_paralelismo(self) -> None:
        source = read_source(Path("research/campaigns/campaign_runner.py"))
        forbidden_fragments = (
            "threading",
            "multiprocessing",
            "asyncio",
            "Thread(",
            "Process(",
            "Pool(",
            "create_task",
            "gather(",
            "ResearchRunner",
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
            ".next_candle(",
            ".generate_signal(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_runner_permanece_desacoplado_de_domain_pipeline_e_operacao(self) -> None:
        path = Path("research/campaigns/campaign_runner.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
            "threading",
            "multiprocessing",
            "asyncio",
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
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("research.experiment_management.experiment_scheduler", imports)

    def _campaign(self) -> ResearchCampaign:
        return ResearchCampaign(
            campaign_id="campaign-alpha001-001",
            name="Alpha001 baseline research",
            description="Campanha inicial de pesquisa.",
            alpha_id="Alpha001",
            objective="Validar baseline estatistico.",
            status="PENDING",
            created_at="2026-06-28T01:00:00-03:00",
            created_by="CTO",
            metadata={
                "datasets": ("WDO-1m-2026-01", "WDO-1m-2026-02"),
            },
        )

    def _template(self) -> ExperimentDefinition:
        return self._definition("template-alpha001")

    def _definitions(self) -> tuple[ExperimentDefinition, ...]:
        return (self._definition("exp-001"), self._definition("exp-002"))

    def _definition(self, experiment_id: str) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id=experiment_id,
            alpha_id="Alpha001",
            alpha_version="1.0.0",
            configuration_version="cfg-001",
            replay_period="2026-01-01/2026-01-31",
            dataset="WDO-1m-2026-01",
            status="PENDING",
            priority=1,
            created_at="2026-06-28T01:00:00-03:00",
            metadata={"source": "test"},
        )


class _QueueSpy(ExperimentQueue):
    def __init__(self, calls: list[str]) -> None:
        super().__init__()
        self.calls = calls
        self.items: list[ExperimentDefinition] = []

    def enqueue(self, experiment: ExperimentDefinition) -> ExperimentDefinition:
        self.calls.append(f"enqueue:{experiment.experiment_id}")
        self.items.append(experiment)
        return super().enqueue(experiment)


class _BuilderSpy:
    def __init__(
        self,
        calls: list[str],
        experiments: tuple[ExperimentDefinition, ...],
    ) -> None:
        self.calls = calls
        self.experiments = experiments

    def build(
        self,
        campaign: ResearchCampaign,
        template: ExperimentDefinition,
    ) -> tuple[ExperimentDefinition, ...]:
        self.calls.append("builder")
        return self.experiments


class _SchedulerSpy:
    def __init__(
        self,
        calls: list[str],
        result: tuple[ExperimentDefinition, ...],
    ) -> None:
        self.calls = calls
        self.result = result

    def run_all(self) -> tuple[ExperimentDefinition, ...]:
        self.calls.append("scheduler.run_all")
        return self.result


if __name__ == "__main__":
    unittest.main()
