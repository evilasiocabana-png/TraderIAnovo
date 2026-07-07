"""Testes do modelo oficial de hipotese quantitativa."""

from dataclasses import FrozenInstanceError, is_dataclass
from datetime import datetime
from pathlib import Path
import unittest

from research.alpha_factory.alpha_hypothesis import AlphaHypothesis
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaHypothesisTest(unittest.TestCase):
    """Valida contrato imutavel de hipotese quantitativa."""

    def test_hypothesis_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaHypothesis))
        self.assertTrue(AlphaHypothesis.__dataclass_params__.frozen)

    def test_hypothesis_contem_campos_obrigatorios(self) -> None:
        created_at = datetime(2026, 6, 27, 21, 15, 0)
        hypothesis = self._hypothesis(created_at=created_at)

        self.assertEqual(hypothesis.hypothesis_id, "hyp-001")
        self.assertEqual(hypothesis.alpha_name, "Alpha Candidate")
        self.assertEqual(hypothesis.version, 1)
        self.assertEqual(hypothesis.title, "Rompimento controlado")
        self.assertEqual(hypothesis.description, "Hipotese de pesquisa.")
        self.assertEqual(hypothesis.market, "WDO")
        self.assertEqual(hypothesis.timeframe, "1m")
        self.assertEqual(hypothesis.context, "Abertura do mercado.")
        self.assertEqual(hypothesis.trigger, "Rompimento da maxima inicial.")
        self.assertEqual(hypothesis.expected_behavior, "Movimento direcional.")
        self.assertEqual(
            hypothesis.risk_assumptions,
            ("Stops limitados.", "Sem operacao real."),
        )
        self.assertEqual(hypothesis.validation_plan, "Validar em pesquisa.")
        self.assertEqual(hypothesis.author, "Research")
        self.assertEqual(hypothesis.created_at, created_at)
        self.assertEqual(hypothesis.status, "DRAFT")
        self.assertEqual(
            hypothesis.formal_hypothesis,
            "Rompimentos da abertura com volume acima da media podem continuar.",
        )
        self.assertEqual(hypothesis.allowed_markets, ("WDO", "EURUSD"))
        self.assertEqual(hypothesis.forbidden_markets, ("CONTA_REAL",))
        self.assertEqual(
            hypothesis.used_layers,
            (
                "MARKET_DATA",
                "INDICADORES",
                "CONTEXTO",
                "ESTRUTURA",
                "MICROESTRUTURA",
            ),
        )
        self.assertEqual(
            hypothesis.searchable_parameters,
            ("ema_curta", "ema_longa", "atr_stop_factor", "rr"),
        )
        self.assertEqual(
            hypothesis.rejection_criteria,
            ("Amostra insuficiente.", "Drawdown excessivo."),
        )
        self.assertEqual(
            hypothesis.approval_criteria,
            ("Profit factor minimo.", "Reprodutibilidade em replay."),
        )

    def test_hypothesis_estado_vazio_explicitamente_seguro_para_novos_campos(self) -> None:
        hypothesis = AlphaHypothesis(
            hypothesis_id="hyp-empty",
            alpha_name="Alpha Empty",
            version=1,
            title="Hipotese minima",
            description="Contrato minimo.",
            market="EURUSD",
            timeframe="M15",
            context="Contexto.",
            trigger="Gatilho.",
            expected_behavior="Comportamento esperado.",
            risk_assumptions=(),
            validation_plan="Validar.",
            author="Research",
            created_at=datetime(2026, 6, 27, 21, 15, 0),
            status="DRAFT",
        )

        self.assertEqual(hypothesis.formal_hypothesis, "")
        self.assertEqual(hypothesis.allowed_markets, ())
        self.assertEqual(hypothesis.forbidden_markets, ())
        self.assertEqual(hypothesis.used_layers, ())
        self.assertEqual(hypothesis.searchable_parameters, ())
        self.assertEqual(hypothesis.rejection_criteria, ())
        self.assertEqual(hypothesis.approval_criteria, ())

    def test_hypothesis_e_imutavel(self) -> None:
        hypothesis = self._hypothesis()

        with self.assertRaises(FrozenInstanceError):
            hypothesis.status = "APPROVED"

    def test_nao_implementa_execucao_ou_calculo(self) -> None:
        source = read_source(Path("research/alpha_factory/alpha_hypothesis.py"))
        forbidden_fragments = (
            "replay",
            "backtest",
            "experiment",
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

    def test_modelo_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_hypothesis.py")
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

    def _hypothesis(
        self,
        created_at: datetime = datetime(2026, 6, 27, 21, 15, 0),
    ) -> AlphaHypothesis:
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
            risk_assumptions=("Stops limitados.", "Sem operacao real."),
            validation_plan="Validar em pesquisa.",
            author="Research",
            created_at=created_at,
            status="DRAFT",
            formal_hypothesis=(
                "Rompimentos da abertura com volume acima da media podem continuar."
            ),
            allowed_markets=("WDO", "EURUSD"),
            forbidden_markets=("CONTA_REAL",),
            used_layers=(
                "MARKET_DATA",
                "INDICADORES",
                "CONTEXTO",
                "ESTRUTURA",
                "MICROESTRUTURA",
            ),
            searchable_parameters=("ema_curta", "ema_longa", "atr_stop_factor", "rr"),
            rejection_criteria=("Amostra insuficiente.", "Drawdown excessivo."),
            approval_criteria=("Profit factor minimo.", "Reprodutibilidade em replay."),
        )


if __name__ == "__main__":
    unittest.main()
