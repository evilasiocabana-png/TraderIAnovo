"""Testes do template oficial de playbook de Alpha."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha_factory.alpha_playbook_template import AlphaPlaybookTemplate
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaPlaybookTemplateTest(unittest.TestCase):
    """Valida contrato imutavel do playbook de Alpha."""

    def test_template_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaPlaybookTemplate))
        self.assertTrue(AlphaPlaybookTemplate.__dataclass_params__.frozen)

    def test_template_contem_campos_obrigatorios(self) -> None:
        template = self._template()

        self.assertEqual(template.hypothesis, "Hipotese quantitativa.")
        self.assertEqual(template.objective, "Documentar Alpha candidata.")
        self.assertEqual(template.allowed_markets, ("WDO",))
        self.assertEqual(template.forbidden_markets, ("WIN",))
        self.assertEqual(template.context, "Contexto operacional simulado.")
        self.assertEqual(template.trigger, "Gatilho de entrada.")
        self.assertEqual(template.filters, ("Filtro de volume.",))
        self.assertEqual(template.entry_rules, ("Entrada apos confirmacao.",))
        self.assertEqual(template.exit_rules, ("Saida por regra definida.",))
        self.assertEqual(template.risk_management, ("Stop obrigatorio.",))
        self.assertEqual(template.replay_validation, "Validar em replay.")
        self.assertEqual(template.research_validation, "Validar em pesquisa.")
        self.assertEqual(template.rejection_criteria, ("Amostra insuficiente.",))
        self.assertEqual(template.acceptance_criteria, ("Robustez estatistica.",))

    def test_template_e_imutavel(self) -> None:
        template = self._template()

        with self.assertRaises(FrozenInstanceError):
            template.objective = "Alterado"

    def test_template_nao_executa_logica_ou_calculos(self) -> None:
        source = read_source(
            Path("research/alpha_factory/alpha_playbook_template.py")
        )
        forbidden_fragments = (
            ".run(",
            ".calculate(",
            ".compare(",
            ".validate(",
            ".recommend(",
            "sum(",
            "max(",
            "min(",
            " / ",
            " * ",
            " + ",
            " - ",
            "openai",
            "machine_learning",
            "sklearn",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_template_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_playbook_template.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "alpha.alpha001_config",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "research.alpha001_experiment",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "generate_signal",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _template(self) -> AlphaPlaybookTemplate:
        return AlphaPlaybookTemplate(
            hypothesis="Hipotese quantitativa.",
            objective="Documentar Alpha candidata.",
            allowed_markets=("WDO",),
            forbidden_markets=("WIN",),
            context="Contexto operacional simulado.",
            trigger="Gatilho de entrada.",
            filters=("Filtro de volume.",),
            entry_rules=("Entrada apos confirmacao.",),
            exit_rules=("Saida por regra definida.",),
            risk_management=("Stop obrigatorio.",),
            replay_validation="Validar em replay.",
            research_validation="Validar em pesquisa.",
            rejection_criteria=("Amostra insuficiente.",),
            acceptance_criteria=("Robustez estatistica.",),
        )


if __name__ == "__main__":
    unittest.main()
