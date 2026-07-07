"""Testes do motor de descontinuacao de Alpha."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.alpha_factory.alpha_deprecation_engine import (
    AlphaDeprecationEngine,
    AlphaDeprecationResult,
)
from research.alpha_factory.alpha_health_engine import AlphaHealthResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaDeprecationEngineTest(unittest.TestCase):
    """Valida decisao institucional sem alterar lifecycle ou registry."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaDeprecationResult))
        self.assertTrue(AlphaDeprecationResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(AlphaDeprecationResult)],
            [
                "decision",
                "reasons",
                "keep_threshold",
                "watch_threshold",
                "deprecate_threshold",
                "lifecycle_changed",
                "alpha_deleted",
            ],
        )

    def test_result_e_imutavel(self) -> None:
        result = AlphaDeprecationResult(
            decision="KEEP",
            reasons=("ok",),
            keep_threshold=0.7,
            watch_threshold=0.4,
            deprecate_threshold=0.3,
        )

        with self.assertRaises(FrozenInstanceError):
            result.decision = "DEPRECATE"

    def test_keep_quando_saude_e_componentes_estao_bons(self) -> None:
        result = AlphaDeprecationEngine().evaluate(
            AlphaHealthResult(
                robustness_score=0.8,
                reproducibility_score=0.9,
                validation_score=0.85,
                campaign_score=0.75,
                health_score=0.82,
            )
        )

        self.assertEqual(result.decision, "KEEP")
        self.assertFalse(result.lifecycle_changed)
        self.assertFalse(result.alpha_deleted)

    def test_watch_quando_saude_geral_esta_intermediaria(self) -> None:
        result = AlphaDeprecationEngine().evaluate(
            AlphaHealthResult(
                robustness_score=0.65,
                reproducibility_score=0.75,
                validation_score=0.72,
                campaign_score=0.7,
                health_score=0.68,
            )
        )

        self.assertEqual(result.decision, "WATCH")
        self.assertIn("Robustez abaixo do ideal.", result.reasons)

    def test_deprecate_por_baixa_robustez(self) -> None:
        result = AlphaDeprecationEngine().evaluate(
            AlphaHealthResult(
                robustness_score=0.2,
                reproducibility_score=0.8,
                validation_score=0.8,
                campaign_score=0.8,
                health_score=0.65,
            )
        )

        self.assertEqual(result.decision, "DEPRECATE")
        self.assertIn("Baixa robustez estatistica.", result.reasons)

    def test_deprecate_por_baixa_reprodutibilidade(self) -> None:
        result = AlphaDeprecationEngine().evaluate(
            AlphaHealthResult(
                robustness_score=0.8,
                reproducibility_score=0.2,
                validation_score=0.8,
                campaign_score=0.8,
                health_score=0.65,
            )
        )

        self.assertEqual(result.decision, "DEPRECATE")
        self.assertIn("Baixa reprodutibilidade.", result.reasons)

    def test_deprecate_por_campanhas_reprovadas_ou_degradacao(self) -> None:
        result = AlphaDeprecationEngine().evaluate(
            AlphaHealthResult(
                robustness_score=0.8,
                reproducibility_score=0.8,
                validation_score=0.2,
                campaign_score=0.1,
                health_score=0.5,
            )
        )

        self.assertEqual(result.decision, "DEPRECATE")
        self.assertIn("Excesso de campanhas reprovadas.", result.reasons)
        self.assertIn("Degradacao estatistica.", result.reasons)

    def test_deprecate_por_saude_geral_baixa(self) -> None:
        result = AlphaDeprecationEngine().evaluate(
            AlphaHealthResult(
                robustness_score=0.35,
                reproducibility_score=0.35,
                validation_score=0.35,
                campaign_score=0.35,
                health_score=0.35,
            )
        )

        self.assertEqual(result.decision, "DEPRECATE")
        self.assertEqual(
            result.reasons,
            ("Saude geral abaixo do limite de descontinuacao.",),
        )

    def test_engine_nao_exclui_alpha_nao_altera_lifecycle_ou_registry(self) -> None:
        source = read_source(
            Path("research/alpha_factory/alpha_deprecation_engine.py")
        )
        forbidden_fragments = (
            "AlphaLifecycleManager",
            "AlphaLifecycle",
            "AlphaRegistry",
            "AlphaCandidateRegistry",
            ".transition(",
            ".unregister(",
            ".delete(",
            "del ",
            "ResearchPipeline",
            "ResearchRunner",
            "Dashboard",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_deprecation_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "research.alpha_factory.alpha_lifecycle",
            "research.alpha_factory.alpha_lifecycle_manager",
            "research.portfolio.alpha_registry",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "validate",
            "recommend",
            "transition",
            "unregister",
            "delete",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))


if __name__ == "__main__":
    unittest.main()
