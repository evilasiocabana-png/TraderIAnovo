"""Testes do contrato oficial de cenarios de estresse."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.validation.stress.stress_scenario import (
    StressScenario,
    StressScenarioType,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class StressScenarioTest(unittest.TestCase):
    """Valida contrato puro para cenarios de estresse."""

    def test_scenario_type_define_estados_oficiais(self) -> None:
        self.assertEqual(
            [scenario.value for scenario in StressScenarioType],
            [
                "HIGH_VOLATILITY",
                "LOW_VOLATILITY",
                "GAP_UP",
                "GAP_DOWN",
                "LOW_LIQUIDITY",
                "TRENDING_MARKET",
                "RANGING_MARKET",
                "BLACK_SWAN",
            ],
        )

    def test_scenario_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(StressScenario))
        self.assertTrue(StressScenario.__dataclass_params__.frozen)

    def test_scenario_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(StressScenario)],
            [
                "scenario_id",
                "scenario_type",
                "description",
                "severity",
                "enabled",
                "metadata",
            ],
        )

    def test_scenario_possui_type_hints_explicitos(self) -> None:
        annotations = StressScenario.__annotations__

        self.assertEqual(annotations["scenario_id"], "str")
        self.assertEqual(annotations["scenario_type"], "StressScenarioType")
        self.assertEqual(annotations["description"], "str")
        self.assertEqual(annotations["severity"], "float")
        self.assertEqual(annotations["enabled"], "bool")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_scenario_representa_cenario_de_estresse(self) -> None:
        scenario = self._scenario()

        self.assertEqual(scenario.scenario_id, "stress-high-volatility-001")
        self.assertEqual(
            scenario.scenario_type,
            StressScenarioType.HIGH_VOLATILITY,
        )
        self.assertEqual(scenario.description, "Alta volatilidade intraday.")
        self.assertEqual(scenario.severity, 0.8)
        self.assertTrue(scenario.enabled)
        self.assertEqual(scenario.metadata["scope"], "validation")

    def test_scenario_preserva_metadata_recebido(self) -> None:
        metadata = {"scope": "validation"}

        scenario = StressScenario(
            scenario_id="stress-black-swan-001",
            scenario_type=StressScenarioType.BLACK_SWAN,
            description="Evento extremo.",
            severity=1.0,
            enabled=True,
            metadata=metadata,
        )

        self.assertIs(scenario.metadata, metadata)

    def test_scenario_e_imutavel(self) -> None:
        scenario = self._scenario()

        with self.assertRaises(FrozenInstanceError):
            scenario.enabled = False

    def test_scenario_nao_executa_pesquisa_ou_modifica_dados(self) -> None:
        source = read_source(Path("research/validation/stress/stress_scenario.py"))
        forbidden_fragments = (
            "def ",
            "ResearchPipeline",
            "ResearchRunner",
            "ValidationRunner",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            "modify",
            "transform",
            ".run(",
            ".calculate(",
            ".validate(",
            ".execute(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_scenario_permanece_desacoplado_de_domain_e_operacao(self) -> None:
        path = Path("research/validation/stress/stress_scenario.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.research_runner",
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
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _scenario(self) -> StressScenario:
        return StressScenario(
            scenario_id="stress-high-volatility-001",
            scenario_type=StressScenarioType.HIGH_VOLATILITY,
            description="Alta volatilidade intraday.",
            severity=0.8,
            enabled=True,
            metadata={"scope": "validation"},
        )


if __name__ == "__main__":
    unittest.main()
