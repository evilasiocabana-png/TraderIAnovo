"""Testes do registro oficial de regras de validacao."""

from dataclasses import is_dataclass
from pathlib import Path
import unittest

from research.validation.validation_rule import ValidationRule
from research.validation.validation_rule_registry import (
    DEFAULT_VALIDATION_RULES,
    ValidationRuleRegistry,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ValidationRuleRegistryTest(unittest.TestCase):
    """Valida registro em memoria de regras declarativas."""

    def test_registry_e_dataclass(self) -> None:
        self.assertTrue(is_dataclass(ValidationRuleRegistry))

    def test_registry_carrega_regras_oficiais(self) -> None:
        registry = ValidationRuleRegistry()

        self.assertEqual(
            tuple(rule.rule_id for rule in registry.list()),
            (
                "minimum_trades",
                "maximum_drawdown",
                "minimum_profit_factor",
                "minimum_win_rate",
                "maximum_outlier_dependency",
            ),
        )

    def test_regras_padrao_sao_validation_rule(self) -> None:
        self.assertTrue(DEFAULT_VALIDATION_RULES)
        self.assertTrue(
            all(isinstance(rule, ValidationRule) for rule in DEFAULT_VALIDATION_RULES)
        )

    def test_get_e_exists_retorna_regra_registrada(self) -> None:
        registry = ValidationRuleRegistry()

        rule = registry.get("minimum_profit_factor")

        self.assertIsInstance(rule, ValidationRule)
        self.assertEqual(rule.name, "Minimum Profit Factor")
        self.assertTrue(registry.exists("minimum_profit_factor"))
        self.assertFalse(registry.exists("unknown"))

    def test_register_substitui_regra_por_id(self) -> None:
        registry = ValidationRuleRegistry()
        replacement = ValidationRule(
            rule_id="minimum_profit_factor",
            name="Minimum Profit Factor Custom",
            description="Regra customizada de teste.",
            severity="LOW",
            threshold=1.5,
            enabled=True,
            metadata={"source": "test"},
        )

        saved = registry.register(replacement)

        self.assertIs(saved, replacement)
        self.assertIs(registry.get("minimum_profit_factor"), replacement)

    def test_unregister_remove_regra_existente(self) -> None:
        registry = ValidationRuleRegistry()

        removed = registry.unregister("minimum_trades")

        self.assertTrue(removed)
        self.assertIsNone(registry.get("minimum_trades"))
        self.assertFalse(registry.exists("minimum_trades"))

    def test_unregister_retorna_false_para_regra_inexistente(self) -> None:
        self.assertFalse(ValidationRuleRegistry().unregister("unknown"))

    def test_list_retorna_tuple_para_proteger_saida(self) -> None:
        rules = ValidationRuleRegistry().list()

        self.assertIsInstance(rules, tuple)
        self.assertEqual(len(rules), len(DEFAULT_VALIDATION_RULES))

    def test_registry_nao_executa_regras_ou_acessa_validators(self) -> None:
        source = read_source(Path("research/validation/validation_rule_registry.py"))
        forbidden_fragments = (
            "ResearchValidator",
            "Alpha001ResearchValidator",
            "ResearchRunner",
            "ResearchPipeline",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".validate(",
            ".calculate(",
            ".run(",
            ".execute(",
            "sum(",
            "max(",
            "min(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_registry_permanece_desacoplado_de_runner_pipeline_domain(self) -> None:
        path = Path("research/validation/validation_rule_registry.py")
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


if __name__ == "__main__":
    unittest.main()
