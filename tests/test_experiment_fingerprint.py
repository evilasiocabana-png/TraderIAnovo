"""Testes da assinatura deterministica de experimentos."""

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from pathlib import Path
import unittest

from research.reproducibility.experiment_fingerprint import (
    ExperimentFingerprint,
    ExperimentFingerprintResult,
)
from research.reproducibility.research_snapshot import ResearchSnapshot
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ExperimentFingerprintTest(unittest.TestCase):
    """Valida geracao reprodutivel sem aleatoriedade ou timestamps."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ExperimentFingerprintResult))
        self.assertTrue(ExperimentFingerprintResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ExperimentFingerprintResult)]

        self.assertEqual(
            field_names,
            [
                "snapshot_id",
                "experiment_id",
                "fingerprint",
                "algorithm",
                "payload",
            ],
        )

    def test_result_possui_type_hints_explicitos(self) -> None:
        annotations = ExperimentFingerprintResult.__annotations__

        self.assertEqual(annotations["snapshot_id"], "str")
        self.assertEqual(annotations["experiment_id"], "str")
        self.assertEqual(annotations["fingerprint"], "str")
        self.assertEqual(annotations["algorithm"], "str")
        self.assertEqual(annotations["payload"], "Mapping[str, object]")

    def test_fingerprint_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ExperimentFingerprint))
        self.assertTrue(ExperimentFingerprint.__dataclass_params__.frozen)

    def test_experimentos_identicos_geram_mesmo_fingerprint(self) -> None:
        first = self._snapshot(snapshot_id="snap-001")
        second = self._snapshot(snapshot_id="snap-002")

        first_result = ExperimentFingerprint().generate(first)
        second_result = ExperimentFingerprint().generate(second)

        self.assertEqual(first_result.fingerprint, second_result.fingerprint)
        self.assertNotEqual(first_result.snapshot_id, second_result.snapshot_id)

    def test_fingerprint_ignora_timestamp_de_criacao(self) -> None:
        first = self._snapshot(created_at="2026-06-28T00:30:00-03:00")
        second = self._snapshot(created_at="2026-06-28T00:40:00-03:00")

        first_result = ExperimentFingerprint().generate(first)
        second_result = ExperimentFingerprint().generate(second)

        self.assertEqual(first_result.fingerprint, second_result.fingerprint)
        self.assertNotIn("created_at", first_result.payload)

    def test_fingerprint_muda_quando_dataset_muda(self) -> None:
        first = self._snapshot(dataset="WDO-1m-2026-01")
        second = self._snapshot(dataset="WDO-1m-2026-02")

        first_result = ExperimentFingerprint().generate(first)
        second_result = ExperimentFingerprint().generate(second)

        self.assertNotEqual(first_result.fingerprint, second_result.fingerprint)

    def test_fingerprint_muda_quando_parametros_mudam(self) -> None:
        first = self._snapshot(parameters={"stop": 50, "target": 100})
        second = self._snapshot(parameters={"stop": 60, "target": 100})

        first_result = ExperimentFingerprint().generate(first)
        second_result = ExperimentFingerprint().generate(second)

        self.assertNotEqual(first_result.fingerprint, second_result.fingerprint)

    def test_fingerprint_muda_quando_random_seed_muda(self) -> None:
        first = self._snapshot(random_seed=42)
        second = self._snapshot(random_seed=43)

        first_result = ExperimentFingerprint().generate(first)
        second_result = ExperimentFingerprint().generate(second)

        self.assertNotEqual(first_result.fingerprint, second_result.fingerprint)

    def test_payload_contem_apenas_campos_reprodutiveis(self) -> None:
        snapshot = self._snapshot()

        result = ExperimentFingerprint().generate(snapshot)

        self.assertEqual(
            tuple(result.payload.keys()),
            (
                "alpha_id",
                "alpha_version",
                "configuration_version",
                "feature_version",
                "context_version",
                "risk_version",
                "research_pipeline_version",
                "dataset",
                "replay_period",
                "random_seed",
                "parameters",
            ),
        )

    def test_fingerprint_nao_altera_snapshot(self) -> None:
        snapshot = self._snapshot()

        ExperimentFingerprint().generate(snapshot)

        self.assertEqual(snapshot.created_at, "2026-06-28T00:30:00-03:00")
        self.assertEqual(snapshot.metadata["parameters"], {"stop": 50, "target": 100})

    def test_result_e_imutavel(self) -> None:
        result = ExperimentFingerprint().generate(self._snapshot())

        with self.assertRaises(FrozenInstanceError):
            result.fingerprint = "changed"

    def test_fingerprint_nao_acessa_camadas_operacionais(self) -> None:
        source = read_source(
            Path("research/reproducibility/experiment_fingerprint.py")
        )
        forbidden_fragments = (
            "datetime",
            "time.",
            "uuid",
            "import random",
            "random.",
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
            "open(",
            "write(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_fingerprint_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/reproducibility/experiment_fingerprint.py")
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

    def _snapshot(
        self,
        snapshot_id: str = "snap-alpha001-001",
        created_at: str = "2026-06-28T00:30:00-03:00",
        dataset: str = "WDO-1m-2026-01",
        random_seed: int = 42,
        parameters: dict[str, object] | None = None,
    ) -> ResearchSnapshot:
        base = ResearchSnapshot(
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
            created_at="2026-06-28T00:30:00-03:00",
            metadata={"parameters": {"stop": 50, "target": 100}},
        )
        metadata = {"parameters": parameters or {"stop": 50, "target": 100}}
        return replace(
            base,
            snapshot_id=snapshot_id,
            created_at=created_at,
            dataset=dataset,
            random_seed=random_seed,
            metadata=metadata,
        )


if __name__ == "__main__":
    unittest.main()
