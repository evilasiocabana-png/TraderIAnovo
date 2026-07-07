"""Testes do gate institucional de reprodutibilidade."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.reproducibility.experiment_fingerprint import ExperimentFingerprint
from research.reproducibility.reproducibility_gate import (
    ReproducibilityGate,
    ReproducibilityGateResult,
)
from research.reproducibility.reproducibility_report import ReproducibilityReport
from research.reproducibility.reproducibility_validator import (
    ReproducibilityValidationResult,
    ReproducibilityValidator,
)
from research.reproducibility.research_snapshot import ResearchSnapshot
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ReproducibilityGateTest(unittest.TestCase):
    """Valida a decisao institucional sem execucao operacional."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ReproducibilityGateResult))
        self.assertTrue(ReproducibilityGateResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ReproducibilityGateResult)]

        self.assertEqual(field_names, ["status", "message", "report"])

    def test_gate_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ReproducibilityGate))
        self.assertTrue(ReproducibilityGate.__dataclass_params__.frozen)

    def test_result_possui_type_hints_explicitos(self) -> None:
        annotations = ReproducibilityGateResult.__annotations__

        self.assertEqual(annotations["status"], "str")
        self.assertEqual(annotations["message"], "str")
        self.assertEqual(annotations["report"], "ReproducibilityReport")

    def test_gate_retorna_reproducible_quando_validacao_aprova(self) -> None:
        report = self._report()

        result = ReproducibilityGate().evaluate(report)

        self.assertEqual(result.status, "REPRODUCIBLE")
        self.assertIs(result.report, report)

    def test_gate_retorna_partially_reproducible_com_score_parcial(self) -> None:
        report = self._report(
            validation_result=self._validation_result(
                is_reproducible=False,
                versions_compatible=False,
                configuration_compatible=False,
                dataset_compatible=False,
                replay_compatible=False,
            ),
            compatible_versions=False,
            configuration_status="INCOMPATIBLE",
            dataset_status="INCOMPATIBLE",
            replay_status="INCOMPATIBLE",
            reproducibility_score=0.25,
        )

        result = ReproducibilityGate().evaluate(report)

        self.assertEqual(result.status, "PARTIALLY_REPRODUCIBLE")
        self.assertIs(result.report, report)

    def test_gate_retorna_partially_reproducible_com_compatibilidade_parcial(self) -> None:
        report = self._report(
            validation_result=self._validation_result(
                is_reproducible=False,
                versions_compatible=True,
                configuration_compatible=False,
                dataset_compatible=False,
                replay_compatible=False,
            ),
            compatible_versions=True,
            configuration_status="INCOMPATIBLE",
            dataset_status="INCOMPATIBLE",
            replay_status="INCOMPATIBLE",
            reproducibility_score=0.0,
        )

        result = ReproducibilityGate().evaluate(report)

        self.assertEqual(result.status, "PARTIALLY_REPRODUCIBLE")

    def test_gate_retorna_not_reproducible_sem_compatibilidade(self) -> None:
        report = self._report(
            validation_result=self._validation_result(
                is_reproducible=False,
                versions_compatible=False,
                configuration_compatible=False,
                dataset_compatible=False,
                replay_compatible=False,
            ),
            compatible_versions=False,
            configuration_status="INCOMPATIBLE",
            dataset_status="INCOMPATIBLE",
            replay_status="INCOMPATIBLE",
            reproducibility_score=0.0,
        )

        result = ReproducibilityGate().evaluate(report)

        self.assertEqual(result.status, "NOT_REPRODUCIBLE")
        self.assertIs(result.report, report)

    def test_result_e_imutavel(self) -> None:
        result = ReproducibilityGate().evaluate(self._report())

        with self.assertRaises(FrozenInstanceError):
            result.status = "NOT_REPRODUCIBLE"

    def test_gate_nao_executa_replay_ou_gera_saida(self) -> None:
        source = read_source(Path("research/reproducibility/reproducibility_gate.py"))
        forbidden_fragments = (
            "ReplayEngine",
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
            "persist",
            ".run(",
            ".execute(",
            ".next_candle(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_gate_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/reproducibility/reproducibility_gate.py")
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

    def _report(
        self,
        validation_result: ReproducibilityValidationResult | None = None,
        compatible_versions: bool = True,
        configuration_status: str = "COMPATIBLE",
        dataset_status: str = "COMPATIBLE",
        replay_status: str = "COMPATIBLE",
        reproducibility_score: float = 1.0,
    ) -> ReproducibilityReport:
        snapshot = self._snapshot()
        fingerprint = ExperimentFingerprint().generate(snapshot)
        validation = (
            validation_result
            or ReproducibilityValidator().validate(snapshot, fingerprint)
        )
        return ReproducibilityReport(
            snapshot=snapshot,
            fingerprint_result=fingerprint,
            validation_result=validation,
            experiment_id=snapshot.experiment_id,
            fingerprint=fingerprint.fingerprint,
            compatible_versions=compatible_versions,
            configuration_status=configuration_status,
            dataset_status=dataset_status,
            replay_status=replay_status,
            reproducibility_score=reproducibility_score,
            execution_time=2.5,
        )

    def _validation_result(
        self,
        is_reproducible: bool,
        versions_compatible: bool,
        configuration_compatible: bool,
        dataset_compatible: bool,
        replay_compatible: bool,
    ) -> ReproducibilityValidationResult:
        return ReproducibilityValidationResult(
            versions_compatible=versions_compatible,
            configuration_compatible=configuration_compatible,
            fingerprint_valid=is_reproducible,
            dataset_compatible=dataset_compatible,
            replay_compatible=replay_compatible,
            is_reproducible=is_reproducible,
            validation_messages=(),
        )

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
