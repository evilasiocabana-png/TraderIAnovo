"""Testes do contrato oficial da suite de validacao cientifica."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.validation.suite.validation_suite import (
    ValidationSuite,
    ValidationSuiteStep,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ValidationSuiteTest(unittest.TestCase):
    """Valida suite declarativa sem execucao de validacoes."""

    def test_suite_step_define_validacoes_suportadas(self) -> None:
        self.assertEqual(
            [step.value for step in ValidationSuiteStep],
            [
                "WALK_FORWARD",
                "MONTE_CARLO",
                "STRESS_TESTING",
            ],
        )

    def test_suite_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ValidationSuite))
        self.assertTrue(ValidationSuite.__dataclass_params__.frozen)

    def test_suite_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(ValidationSuite)],
            [
                "suite_id",
                "name",
                "enabled_steps",
                "required_steps",
                "created_at",
                "metadata",
            ],
        )

    def test_suite_possui_type_hints_explicitos(self) -> None:
        annotations = ValidationSuite.__annotations__

        self.assertEqual(annotations["suite_id"], "str")
        self.assertEqual(annotations["name"], "str")
        self.assertEqual(
            annotations["enabled_steps"],
            "tuple[ValidationSuiteStep, ...]",
        )
        self.assertEqual(
            annotations["required_steps"],
            "tuple[ValidationSuiteStep, ...]",
        )
        self.assertEqual(annotations["created_at"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_suite_representa_validacoes_padronizadas(self) -> None:
        suite = self._suite()

        self.assertEqual(suite.suite_id, "validation-suite-alpha001-001")
        self.assertEqual(suite.name, "Alpha001 Scientific Validation")
        self.assertEqual(
            suite.enabled_steps,
            (
                ValidationSuiteStep.WALK_FORWARD,
                ValidationSuiteStep.MONTE_CARLO,
                ValidationSuiteStep.STRESS_TESTING,
            ),
        )
        self.assertEqual(
            suite.required_steps,
            (
                ValidationSuiteStep.WALK_FORWARD,
                ValidationSuiteStep.MONTE_CARLO,
            ),
        )
        self.assertEqual(suite.created_at, "2026-06-28T08:10:00-03:00")
        self.assertEqual(suite.metadata["scope"], "validation")

    def test_suite_preserva_colecoes_e_metadata_recebidos(self) -> None:
        enabled = (ValidationSuiteStep.WALK_FORWARD,)
        required = (ValidationSuiteStep.WALK_FORWARD,)
        metadata = {"scope": "validation"}

        suite = ValidationSuite(
            suite_id="validation-suite-alpha001-001",
            name="Alpha001 Scientific Validation",
            enabled_steps=enabled,
            required_steps=required,
            created_at="2026-06-28T08:10:00-03:00",
            metadata=metadata,
        )

        self.assertIs(suite.enabled_steps, enabled)
        self.assertIs(suite.required_steps, required)
        self.assertIs(suite.metadata, metadata)

    def test_suite_permite_estado_vazio_quando_explicito(self) -> None:
        suite = ValidationSuite(
            suite_id="validation-suite-empty-001",
            name="Empty Validation Suite",
            enabled_steps=(),
            required_steps=(),
            created_at="2026-06-28T08:10:00-03:00",
            metadata={},
        )

        self.assertEqual(suite.enabled_steps, ())
        self.assertEqual(suite.required_steps, ())

    def test_suite_e_imutavel(self) -> None:
        suite = self._suite()

        with self.assertRaises(FrozenInstanceError):
            suite.name = "Updated"

    def test_suite_nao_executa_validacoes_ou_altera_componentes(self) -> None:
        source = read_source(
            Path("research/validation/suite/validation_suite.py")
        )
        forbidden_fragments = (
            "def ",
            "ValidationRunner",
            "ExperimentValidationRunner",
            "ResearchPipeline",
            "ResearchRunner",
            "WalkForwardEngine",
            "MonteCarloEngine",
            "StressEngine",
            "Dashboard",
            "streamlit",
            "ReplayEngine",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".calculate(",
            ".validate(",
            ".analyze(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_suite_permanece_desacoplada_de_domain_e_operacao(self) -> None:
        path = Path("research/validation/suite/validation_suite.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.research_runner",
            "research.validation.validation_gate",
            "research.validation.walk_forward_engine",
            "research.validation.monte_carlo.monte_carlo_engine",
            "research.validation.stress.stress_engine",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "database",
            "openai",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "calculate",
            "validate",
            "analyze",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _suite(self) -> ValidationSuite:
        return ValidationSuite(
            suite_id="validation-suite-alpha001-001",
            name="Alpha001 Scientific Validation",
            enabled_steps=(
                ValidationSuiteStep.WALK_FORWARD,
                ValidationSuiteStep.MONTE_CARLO,
                ValidationSuiteStep.STRESS_TESTING,
            ),
            required_steps=(
                ValidationSuiteStep.WALK_FORWARD,
                ValidationSuiteStep.MONTE_CARLO,
            ),
            created_at="2026-06-28T08:10:00-03:00",
            metadata={"scope": "validation"},
        )


if __name__ == "__main__":
    unittest.main()
