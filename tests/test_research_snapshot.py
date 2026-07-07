"""Testes do snapshot oficial de execucao de pesquisa."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.reproducibility.research_snapshot import ResearchSnapshot
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchSnapshotTest(unittest.TestCase):
    """Valida contrato puro para reprodutibilidade de pesquisas."""

    def test_snapshot_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ResearchSnapshot))
        self.assertTrue(ResearchSnapshot.__dataclass_params__.frozen)

    def test_snapshot_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ResearchSnapshot)]

        self.assertEqual(
            field_names,
            [
                "snapshot_id",
                "experiment_id",
                "alpha_id",
                "alpha_version",
                "configuration_version",
                "feature_version",
                "context_version",
                "risk_version",
                "research_pipeline_version",
                "replay_period",
                "dataset",
                "random_seed",
                "created_at",
                "metadata",
            ],
        )

    def test_snapshot_possui_type_hints_explicitos(self) -> None:
        annotations = ResearchSnapshot.__annotations__

        self.assertEqual(annotations["snapshot_id"], "str")
        self.assertEqual(annotations["experiment_id"], "str")
        self.assertEqual(annotations["alpha_id"], "str")
        self.assertEqual(annotations["alpha_version"], "str")
        self.assertEqual(annotations["configuration_version"], "str")
        self.assertEqual(annotations["feature_version"], "str")
        self.assertEqual(annotations["context_version"], "str")
        self.assertEqual(annotations["risk_version"], "str")
        self.assertEqual(annotations["research_pipeline_version"], "str")
        self.assertEqual(annotations["replay_period"], "str")
        self.assertEqual(annotations["dataset"], "str")
        self.assertEqual(annotations["random_seed"], "int")
        self.assertEqual(annotations["created_at"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_snapshot_representa_execucao_completa(self) -> None:
        snapshot = self._snapshot()

        self.assertEqual(snapshot.snapshot_id, "snap-alpha001-001")
        self.assertEqual(snapshot.experiment_id, "exp-alpha001-001")
        self.assertEqual(snapshot.alpha_id, "Alpha001")
        self.assertEqual(snapshot.alpha_version, "1.0.0")
        self.assertEqual(snapshot.configuration_version, "cfg-001")
        self.assertEqual(snapshot.feature_version, "feat-001")
        self.assertEqual(snapshot.context_version, "ctx-001")
        self.assertEqual(snapshot.risk_version, "risk-001")
        self.assertEqual(snapshot.research_pipeline_version, "pipe-001")
        self.assertEqual(snapshot.replay_period, "2026-01-01/2026-01-31")
        self.assertEqual(snapshot.dataset, "WDO-1m-2026-01")
        self.assertEqual(snapshot.random_seed, 42)
        self.assertEqual(snapshot.created_at, "2026-06-28T00:20:00-03:00")
        self.assertEqual(snapshot.metadata["source"], "unit-test")

    def test_snapshot_preserva_metadata_recebido(self) -> None:
        metadata = {"source": "unit-test"}

        snapshot = ResearchSnapshot(
            snapshot_id="snap-alpha001-001",
            experiment_id="exp-alpha001-001",
            alpha_id="Alpha001",
            alpha_version="1.0.0",
            configuration_version="cfg-001",
            feature_version="feat-001",
            context_version="ctx-001",
            risk_version="risk-001",
            research_pipeline_version="pipe-001",
            replay_period="2026-01-01/2026-01-31",
            dataset="WDO-1m-2026-01",
            random_seed=42,
            created_at="2026-06-28T00:20:00-03:00",
            metadata=metadata,
        )

        self.assertIs(snapshot.metadata, metadata)

    def test_snapshot_e_imutavel(self) -> None:
        snapshot = self._snapshot()

        with self.assertRaises(FrozenInstanceError):
            snapshot.random_seed = 7

    def test_snapshot_nao_executa_pesquisas_ou_acessa_camadas(self) -> None:
        source = read_source(Path("research/reproducibility/research_snapshot.py"))
        forbidden_fragments = (
            "def ",
            "ResearchRunner",
            "ResearchPipeline",
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
            "sum(",
            "len(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_snapshot_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/reproducibility/research_snapshot.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
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

    def _snapshot(self) -> ResearchSnapshot:
        return ResearchSnapshot(
            snapshot_id="snap-alpha001-001",
            experiment_id="exp-alpha001-001",
            alpha_id="Alpha001",
            alpha_version="1.0.0",
            configuration_version="cfg-001",
            feature_version="feat-001",
            context_version="ctx-001",
            risk_version="risk-001",
            research_pipeline_version="pipe-001",
            replay_period="2026-01-01/2026-01-31",
            dataset="WDO-1m-2026-01",
            random_seed=42,
            created_at="2026-06-28T00:20:00-03:00",
            metadata={"source": "unit-test"},
        )


if __name__ == "__main__":
    unittest.main()
