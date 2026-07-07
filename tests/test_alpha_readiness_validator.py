"""Testes do validador de prontidao de Alpha."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from datetime import datetime
from pathlib import Path
import unittest

from research.alpha_factory.alpha_hypothesis import AlphaHypothesis
from research.alpha_factory.alpha_playbook_template import AlphaPlaybookTemplate
from research.alpha_factory.alpha_readiness_validator import (
    AlphaReadinessResult,
    AlphaReadinessValidator,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaReadinessValidatorTest(unittest.TestCase):
    """Valida prontidao declarativa para iniciar pesquisa."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaReadinessResult))
        self.assertTrue(AlphaReadinessResult.__dataclass_params__.frozen)

    def test_aprova_hipotese_e_playbook_completos(self) -> None:
        result = AlphaReadinessValidator().validate(
            self._hypothesis(),
            self._playbook(),
        )

        self.assertTrue(result.approved)
        self.assertEqual(result.validation_messages, ())

    def test_reprova_hipotese_sem_titulo(self) -> None:
        result = AlphaReadinessValidator().validate(
            replace(self._hypothesis(), title=""),
            self._playbook(),
        )

        self.assertFalse(result.approved)
        self.assertIn("Hipotese nao definida.", result.validation_messages)

    def test_reprova_mercado_proibido(self) -> None:
        result = AlphaReadinessValidator().validate(
            replace(self._hypothesis(), market="WIN"),
            self._playbook(),
        )

        self.assertFalse(result.approved)
        self.assertIn("Mercado proibido para a hipotese.", result.validation_messages)

    def test_reprova_mercado_nao_permitido(self) -> None:
        result = AlphaReadinessValidator().validate(
            replace(self._hypothesis(), market="DOL"),
            self._playbook(),
        )

        self.assertFalse(result.approved)
        self.assertIn("Mercado nao permitido para a hipotese.", result.validation_messages)

    def test_reprova_campos_de_timeframe_e_gatilho(self) -> None:
        result = AlphaReadinessValidator().validate(
            replace(self._hypothesis(), timeframe="", trigger=""),
            self._playbook(),
        )

        self.assertIn("Timeframe nao definido.", result.validation_messages)
        self.assertIn("Gatilho nao definido.", result.validation_messages)

    def test_reprova_camadas_e_parametros_pesquisaveis_ausentes(self) -> None:
        result = AlphaReadinessValidator().validate(
            replace(self._hypothesis(), used_layers=(), searchable_parameters=()),
            self._playbook(),
        )

        self.assertFalse(result.approved)
        self.assertIn("Camadas usadas ausentes.", result.validation_messages)
        self.assertIn("Parametros pesquisaveis ausentes.", result.validation_messages)

    def test_reprova_regras_e_criterios_ausentes(self) -> None:
        playbook = replace(
            self._playbook(),
            entry_rules=(),
            exit_rules=(),
            acceptance_criteria=(),
            rejection_criteria=(),
        )
        hypothesis = replace(
            self._hypothesis(),
            approval_criteria=(),
            rejection_criteria=(),
        )
        result = AlphaReadinessValidator().validate(hypothesis, playbook)

        self.assertFalse(result.approved)
        self.assertIn("Regras de entrada ausentes.", result.validation_messages)
        self.assertIn("Regras de saida ausentes.", result.validation_messages)
        self.assertIn("Criterios de aceitacao ausentes.", result.validation_messages)
        self.assertIn("Criterios de rejeicao ausentes.", result.validation_messages)

    def test_reprova_plano_de_validacao_ausente(self) -> None:
        hypothesis = replace(self._hypothesis(), validation_plan="")
        playbook = replace(
            self._playbook(),
            replay_validation="",
            research_validation="",
        )

        result = AlphaReadinessValidator().validate(hypothesis, playbook)

        self.assertFalse(result.approved)
        self.assertIn("Plano de validacao ausente.", result.validation_messages)

    def test_resultado_e_imutavel(self) -> None:
        result = AlphaReadinessValidator().validate(
            self._hypothesis(),
            self._playbook(),
        )

        with self.assertRaises(FrozenInstanceError):
            result.approved = False

    def test_validator_nao_inicia_pesquisa_replay_backtest_ou_dashboard(self) -> None:
        source = read_source(
            Path("research/alpha_factory/alpha_readiness_validator.py")
        )
        forbidden_fragments = (
            "backtest",
            "Alpha001Experiment",
            "ResearchRunner",
            "ResearchPipeline",
            "dashboard",
            "streamlit",
            ".run(",
            ".calculate(",
            ".compare(",
            ".recommend(",
            "generate_signal",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_validator_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_readiness_validator.py")
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

    def _hypothesis(self) -> AlphaHypothesis:
        return AlphaHypothesis(
            hypothesis_id="hyp-001",
            alpha_name="Alpha Candidate",
            version=1,
            title="Rompimento controlado",
            description="Hipotese de pesquisa.",
            market="WDO",
            timeframe="1m",
            context="Abertura do mercado.",
            trigger="Rompimento da maxima inicial.",
            expected_behavior="Movimento direcional.",
            risk_assumptions=("Stops limitados.",),
            validation_plan="Validar em pesquisa.",
            author="Research",
            created_at=datetime(2026, 6, 27, 21, 25, 0),
            status="DRAFT",
            formal_hypothesis=(
                "Rompimentos da abertura com volume acima da media podem continuar."
            ),
            allowed_markets=("WDO",),
            forbidden_markets=("WIN", "CONTA_REAL"),
            used_layers=(
                "MARKET_DATA",
                "INDICADORES",
                "CONTEXTO",
                "ESTRUTURA",
            ),
            searchable_parameters=("ema_curta", "ema_longa", "atr_stop_factor", "rr"),
            rejection_criteria=("Amostra insuficiente.",),
            approval_criteria=("Robustez estatistica.",),
        )

    def _playbook(self) -> AlphaPlaybookTemplate:
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
