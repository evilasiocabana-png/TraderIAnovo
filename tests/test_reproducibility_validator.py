"""Testes do validador de reprodutibilidade."""

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from pathlib import Path
import unittest

from research.reproducibility.experiment_fingerprint import (
    ExperimentFingerprint,
    ExperimentFingerprintResult,
)
from research.reproducibility.reproducibility_validator import (
    ReproducibilityValidationResult,
    ReproducibilityValidator,
)
from research.reproducibility.research_snapshot import ResearchSnapshot
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ReproducibilityValidatorTest(unittest.TestCase):
    """Valida compatibilidade sem executar pesquisa ou replay."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ReproducibilityValidationResult))
        self.assertTrue(ReproducibilityValidationResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        field_names = [
            field.name for field in fields(ReproducibilityValidationResult)
        ]

        self.assertEqual(
            field_names,
            [
                "versions_compatible",
                "configuration_compatible",
                "fingerprint_valid",
                "dataset_compatible",
                "replay_compatible",
                "is_reproducible",
                "validation_messages",
            ],
        )

    def test_result_possui_type_hints_explicitos(self) -> None:
        annotations = ReproducibilityValidationResult.__annotations__

        self.assertEqual(annotations["versions_compatible"], "bool")
        self.assertEqual(annotations["configuration_compatible"], "bool")
        self.assertEqual(annotations["fingerprint_valid"], "bool")
        self.assertEqual(annotations["dataset_compatible"], "bool")
        self.assertEqual(annotations["replay_compatible"], "bool")
        self.assertEqual(annotations["is_reproducible"], "bool")
        self.assertEqual(annotations["validation_messages"], "tuple[str, ...]")

    def test_validator_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ReproducibilityValidator))
        self.assertTrue(ReproducibilityValidator.__dataclass_params__.frozen)

    def test_validator_aprova_snapshot_e_fingerprint_compativeis(self) -> None:
        snapshot = self._snapshot()
        fingerprint = ExperimentFingerprint().generate(snapshot)

        result = ReproducibilityValidator().validate(snapshot, fingerprint)

        self.assertTrue(result.versions_compatible)
        self.assertTrue(result.configuration_compatible)
        self.assertTrue(result.fingerprint_valid)
        self.assertTrue(result.dataset_compatible)
        self.assertTrue(result.replay_compatible)
        self.assertTrue(result.is_reproducible)
        self.assertEqual(result.validation_messages, ())

    def test_validator_detecta_versoes_incompativeis(self) -> None:
        snapshot = self._snapshot()
        fingerprint = self._fingerprint_with_payload(
            snapshot,
            {"alpha_version": "2.0.0"},
        )

        result = ReproducibilityValidator().validate(snapshot, fingerprint)

        self.assertFalse(result.versions_compatible)
        self.assertFalse(result.fingerprint_valid)
        self.assertFalse(result.is_reproducible)
        self.assertIn("Versions are not compatible.", result.validation_messages)

    def test_validator_detecta_configuracao_incompativel(self) -> None:
        snapshot = self._snapshot()
        fingerprint = self._fingerprint_with_payload(
            snapshot,
            {"configuration_version": "cfg-002"},
        )

        result = ReproducibilityValidator().validate(snapshot, fingerprint)

        self.assertFalse(result.configuration_compatible)
        self.assertFalse(result.fingerprint_valid)
        self.assertIn("Configuration is not compatible.", result.validation_messages)

    def test_validator_detecta_fingerprint_invalido(self) -> None:
        snapshot = self._snapshot()
        fingerprint = ExperimentFingerprint().generate(snapshot)
        invalid = replace(fingerprint, fingerprint="invalid")

        result = ReproducibilityValidator().validate(snapshot, invalid)

        self.assertTrue(result.versions_compatible)
        self.assertTrue(result.configuration_compatible)
        self.assertFalse(result.fingerprint_valid)
        self.assertTrue(result.dataset_compatible)
        self.assertTrue(result.replay_compatible)
        self.assertFalse(result.is_reproducible)
        self.assertIn("Fingerprint is not valid.", result.validation_messages)

    def test_validator_detecta_dataset_incompativel(self) -> None:
        snapshot = self._snapshot()
        fingerprint = self._fingerprint_with_payload(
            snapshot,
            {"dataset": "WDO-1m-2026-02"},
        )

        result = ReproducibilityValidator().validate(snapshot, fingerprint)

        self.assertFalse(result.dataset_compatible)
        self.assertFalse(result.fingerprint_valid)
        self.assertIn("Dataset is not compatible.", result.validation_messages)

    def test_validator_detecta_replay_incompativel(self) -> None:
        snapshot = self._snapshot()
        fingerprint = self._fingerprint_with_payload(
            snapshot,
            {"replay_period": "2026-02-01/2026-02-28"},
        )

        result = ReproducibilityValidator().validate(snapshot, fingerprint)

        self.assertFalse(result.replay_compatible)
        self.assertFalse(result.fingerprint_valid)
        self.assertIn("Replay period is not compatible.", result.validation_messages)

    def test_result_e_imutavel(self) -> None:
        snapshot = self._snapshot()
        fingerprint = ExperimentFingerprint().generate(snapshot)
        result = ReproducibilityValidator().validate(snapshot, fingerprint)

        with self.assertRaises(FrozenInstanceError):
            result.is_reproducible = False

    def test_validator_nao_executa_replay_ou_pesquisa(self) -> None:
        source = read_source(
            Path("research/reproducibility/reproducibility_validator.py")
        )
        forbidden_fragments = (
            "ReplayEngine",
            "ExperimentRunner",
            "ResearchRunner",
            "ResearchPipeline",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            "open(",
            "write(",
            ".run(",
            ".execute(",
            ".next_candle(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_validator_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/reproducibility/reproducibility_validator.py")
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

    def _fingerprint_with_payload(
        self,
        snapshot: ResearchSnapshot,
        overrides: dict[str, object],
    ) -> ExperimentFingerprintResult:
        fingerprint = ExperimentFingerprint().generate(snapshot)
        payload = dict(fingerprint.payload)
        payload.update(overrides)
        return replace(fingerprint, payload=payload)

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
            created_at="2026-06-28T00:30:00-03:00",
            metadata={"parameters": {"stop": 50, "target": 100}},
        )


if __name__ == "__main__":
    unittest.main()
