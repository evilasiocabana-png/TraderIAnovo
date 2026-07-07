"""Testes do contrato oficial de definicao de experimento."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import ExperimentDefinition
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ExperimentDefinitionTest(unittest.TestCase):
    """Valida contrato puro para experimentos de pesquisa."""

    def test_definition_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ExperimentDefinition))
        self.assertTrue(ExperimentDefinition.__dataclass_params__.frozen)

    def test_definition_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ExperimentDefinition)]

        self.assertEqual(
            field_names,
            [
                "experiment_id",
                "alpha_id",
                "alpha_version",
                "configuration_version",
                "replay_period",
                "dataset",
                "status",
                "priority",
                "created_at",
                "metadata",
            ],
        )

    def test_definition_possui_type_hints_explicitos(self) -> None:
        annotations = ExperimentDefinition.__annotations__

        self.assertEqual(annotations["experiment_id"], "str")
        self.assertEqual(annotations["alpha_id"], "str")
        self.assertEqual(annotations["alpha_version"], "str")
        self.assertEqual(annotations["configuration_version"], "str")
        self.assertEqual(annotations["replay_period"], "str")
        self.assertEqual(annotations["dataset"], "str")
        self.assertEqual(annotations["status"], "str")
        self.assertEqual(annotations["priority"], "int")
        self.assertEqual(annotations["created_at"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_definition_representa_experimento(self) -> None:
        definition = self._definition()

        self.assertEqual(definition.experiment_id, "exp-alpha002-001")
        self.assertEqual(definition.alpha_id, "Alpha002")
        self.assertEqual(definition.alpha_version, "0.1.0")
        self.assertEqual(definition.configuration_version, "cfg-001")
        self.assertEqual(definition.replay_period, "2026-01-01/2026-01-31")
        self.assertEqual(definition.dataset, "WDO-1m-2026-01")
        self.assertEqual(definition.status, "PENDING")
        self.assertEqual(definition.priority, 1)
        self.assertEqual(definition.created_at, "2026-06-27T23:40:00-03:00")
        self.assertEqual(definition.metadata["source"], "test")

    def test_definition_preserva_metadata_recebido(self) -> None:
        metadata = {"source": "test"}

        definition = ExperimentDefinition(
            experiment_id="exp-alpha002-001",
            alpha_id="Alpha002",
            alpha_version="0.1.0",
            configuration_version="cfg-001",
            replay_period="2026-01-01/2026-01-31",
            dataset="WDO-1m-2026-01",
            status="PENDING",
            priority=1,
            created_at="2026-06-27T23:40:00-03:00",
            metadata=metadata,
        )

        self.assertIs(definition.metadata, metadata)

    def test_definition_e_imutavel(self) -> None:
        definition = self._definition()

        with self.assertRaises(FrozenInstanceError):
            definition.status = "RUNNING"

    def test_definition_nao_executa_experimentos_ou_acessa_camadas(self) -> None:
        source = read_source(
            Path("research/experiment_management/experiment_definition.py")
        )
        forbidden_fragments = (
            "def ",
            "ReplayEngine",
            "ResearchRunner",
            "ResearchPipeline",
            "Alpha001",
            "Alpha002Strategy",
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
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_definition_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/experiment_management/experiment_definition.py")
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

    def _definition(self) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id="exp-alpha002-001",
            alpha_id="Alpha002",
            alpha_version="0.1.0",
            configuration_version="cfg-001",
            replay_period="2026-01-01/2026-01-31",
            dataset="WDO-1m-2026-01",
            status="PENDING",
            priority=1,
            created_at="2026-06-27T23:40:00-03:00",
            metadata={"source": "test"},
        )


if __name__ == "__main__":
    unittest.main()
