"""Testes do contrato oficial de regra de validacao."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.validation.validation_rule import ValidationRule
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ValidationRuleTest(unittest.TestCase):
    """Valida regra declarativa sem execucao de validacao."""

    def test_rule_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ValidationRule))
        self.assertTrue(ValidationRule.__dataclass_params__.frozen)

    def test_rule_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ValidationRule)]

        self.assertEqual(
            field_names,
            [
                "rule_id",
                "name",
                "description",
                "severity",
                "threshold",
                "enabled",
                "metadata",
            ],
        )

    def test_rule_possui_type_hints_explicitos(self) -> None:
        annotations = ValidationRule.__annotations__

        self.assertEqual(annotations["rule_id"], "str")
        self.assertEqual(annotations["name"], "str")
        self.assertEqual(annotations["description"], "str")
        self.assertEqual(annotations["severity"], "str")
        self.assertEqual(annotations["threshold"], "float")
        self.assertEqual(annotations["enabled"], "bool")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_rule_representa_regra_de_validacao(self) -> None:
        rule = self._rule()

        self.assertEqual(rule.rule_id, "minimum-profit-factor")
        self.assertEqual(rule.name, "Minimum Profit Factor")
        self.assertEqual(rule.description, "Exige profit factor minimo.")
        self.assertEqual(rule.severity, "HIGH")
        self.assertEqual(rule.threshold, 1.2)
        self.assertTrue(rule.enabled)
        self.assertEqual(rule.metadata["source"], "test")

    def test_rule_preserva_metadata_recebido(self) -> None:
        metadata = {"source": "test"}

        rule = ValidationRule(
            rule_id="minimum-profit-factor",
            name="Minimum Profit Factor",
            description="Exige profit factor minimo.",
            severity="HIGH",
            threshold=1.2,
            enabled=True,
            metadata=metadata,
        )

        self.assertIs(rule.metadata, metadata)

    def test_rule_e_imutavel(self) -> None:
        rule = self._rule()

        with self.assertRaises(FrozenInstanceError):
            rule.enabled = False

    def test_rule_nao_executa_validacoes_ou_calcula_metricas(self) -> None:
        source = read_source(Path("research/validation/validation_rule.py"))
        forbidden_fragments = (
            "def ",
            "calculate",
            "validate",
            "ResearchRunner",
            "ResearchPipeline",
            "ResearchValidator",
            "Alpha001ResearchValidator",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_rule_permanece_desacoplada_de_pipeline_runner_e_domain(self) -> None:
        path = Path("research/validation/validation_rule.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
            "research.alpha001_research_validator",
            "research.experiment_validator",
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
            "validate",
            "calculate",
            "run",
            "execute",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _rule(self) -> ValidationRule:
        return ValidationRule(
            rule_id="minimum-profit-factor",
            name="Minimum Profit Factor",
            description="Exige profit factor minimo.",
            severity="HIGH",
            threshold=1.2,
            enabled=True,
            metadata={"source": "test"},
        )


if __name__ == "__main__":
    unittest.main()
