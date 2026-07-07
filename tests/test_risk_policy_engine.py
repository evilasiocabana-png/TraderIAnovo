"""Testes do engine de politica quantitativa de risco."""

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from math import inf, nan
from pathlib import Path
import unittest

from risk.risk_policy_engine import RiskPolicyEngine, RiskPolicyResult
from risk.risk_profile import RiskProfile
from risk.risk_score_engine import RiskScoreResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class RiskPolicyEngineTest(unittest.TestCase):
    """Valida politicas quantitativas sem operacao real."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(RiskPolicyResult))
        self.assertTrue(RiskPolicyResult.__dataclass_params__.frozen)

    def test_engine_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(RiskPolicyEngine))
        self.assertTrue(RiskPolicyEngine.__dataclass_params__.frozen)

    def test_resultado_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(RiskPolicyResult)]

        self.assertEqual(
            field_names,
            [
                "decision",
                "reason",
                "final_risk_score",
            ],
        )

    def test_resultado_possui_type_hints_explicitos(self) -> None:
        annotations = RiskPolicyResult.__annotations__

        self.assertEqual(annotations["decision"], "RiskPolicyDecision")
        self.assertEqual(annotations["reason"], "str")
        self.assertEqual(annotations["final_risk_score"], "float")

    def test_retorna_allow_para_score_alto(self) -> None:
        result = RiskPolicyEngine().evaluate(
            self._profile(),
            self._score_result(final_risk_score=82.0),
        )

        self.assertEqual(result.decision, "ALLOW")
        self.assertEqual(result.final_risk_score, 82.0)

    def test_retorna_reduce_para_score_intermediario(self) -> None:
        result = RiskPolicyEngine().evaluate(
            self._profile(),
            self._score_result(final_risk_score=62.0),
        )

        self.assertEqual(result.decision, "REDUCE")
        self.assertEqual(result.final_risk_score, 62.0)

    def test_retorna_block_paper_para_score_baixo(self) -> None:
        result = RiskPolicyEngine().evaluate(
            self._profile(),
            self._score_result(final_risk_score=45.0),
        )

        self.assertEqual(result.decision, "BLOCK_PAPER")
        self.assertEqual(result.final_risk_score, 45.0)

    def test_retorna_block_paper_para_componente_critico(self) -> None:
        result = RiskPolicyEngine().evaluate(
            self._profile(),
            self._score_result(drawdown_score=35.0, final_risk_score=70.0),
        )

        self.assertEqual(result.decision, "BLOCK_PAPER")

    def test_retorna_block_research_para_pesquisa_insuficiente(self) -> None:
        result = RiskPolicyEngine().evaluate(
            self._profile(),
            self._score_result(research_score=20.0, final_risk_score=65.0),
        )

        self.assertEqual(result.decision, "BLOCK_RESEARCH")

    def test_retorna_block_paper_quando_profile_desabilitado(self) -> None:
        result = RiskPolicyEngine().evaluate(
            replace(self._profile(), enabled=False),
            self._score_result(final_risk_score=90.0),
        )

        self.assertEqual(result.decision, "BLOCK_PAPER")
        self.assertEqual(result.final_risk_score, 90.0)

    def test_normaliza_score_final_invalido_ou_fora_da_faixa(self) -> None:
        engine = RiskPolicyEngine()

        self.assertEqual(
            engine.evaluate(
                self._profile(),
                self._score_result(final_risk_score=inf),
            ).final_risk_score,
            0.0,
        )
        self.assertEqual(
            engine.evaluate(
                self._profile(),
                self._score_result(final_risk_score=nan),
            ).final_risk_score,
            0.0,
        )
        self.assertEqual(
            engine.evaluate(
                self._profile(),
                self._score_result(final_risk_score=120.0),
            ).final_risk_score,
            100.0,
        )

    def test_resultado_e_imutavel(self) -> None:
        result = RiskPolicyEngine().evaluate(
            self._profile(),
            self._score_result(final_risk_score=82.0),
        )

        with self.assertRaises(FrozenInstanceError):
            result.decision = "BLOCK_PAPER"

    def test_decisoes_permanecem_no_conjunto_permitido(self) -> None:
        decisions = {
            RiskPolicyEngine().evaluate(
                self._profile(),
                self._score_result(final_risk_score=82.0),
            ).decision,
            RiskPolicyEngine().evaluate(
                self._profile(),
                self._score_result(final_risk_score=62.0),
            ).decision,
            RiskPolicyEngine().evaluate(
                self._profile(),
                self._score_result(final_risk_score=45.0),
            ).decision,
            RiskPolicyEngine().evaluate(
                self._profile(),
                self._score_result(research_score=20.0, final_risk_score=65.0),
            ).decision,
        }

        self.assertEqual(
            decisions,
            {"ALLOW", "REDUCE", "BLOCK_PAPER", "BLOCK_RESEARCH"},
        )

    def test_engine_nao_envia_ordens_ou_altera_risk_engine(self) -> None:
        source = read_source(Path("risk/risk_policy_engine.py"))
        forbidden_fragments = (
            "class RiskEngine",
            "RiskDecision",
            "StrategySignal",
            "DecisionPipeline",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            "send_order",
            "open_position",
            "close_position",
            "approved =",
            " allowed =",
            ".avaliar(",
            ".processar(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("risk/risk_policy_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "risk.risk_engine",
            "domain",
            "core.decision_pipeline",
            "replay",
            "application.replay_service",
            "alpha",
            "strategies",
            "broker",
            "mt5",
            "MetaTrader5",
            "paper",
            "database",
            "dashboard_app",
            "streamlit",
        }
        forbidden_calls = {
            "open",
            "avaliar",
            "processar",
            "execute",
            "run",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _profile(self) -> RiskProfile:
        return RiskProfile(
            capital=100000.0,
            max_exposure=0.3,
            risk_per_trade=0.01,
            daily_risk_limit=0.03,
            max_daily_loss=3000.0,
            max_daily_gain=5000.0,
            max_drawdown_allowed=0.1,
            contracts=2,
            enabled=True,
            metadata={"source": "test"},
        )

    def _score_result(
        self,
        exposure_score: float = 80.0,
        drawdown_score: float = 80.0,
        volatility_score: float = 80.0,
        research_score: float = 80.0,
        final_risk_score: float = 80.0,
    ) -> RiskScoreResult:
        return RiskScoreResult(
            exposure_score=exposure_score,
            drawdown_score=drawdown_score,
            volatility_score=volatility_score,
            research_score=research_score,
            final_risk_score=final_risk_score,
        )


if __name__ == "__main__":
    unittest.main()
