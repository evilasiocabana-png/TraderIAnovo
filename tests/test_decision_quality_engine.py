"""Testes do avaliador de qualidade da decisao."""

from dataclasses import FrozenInstanceError, is_dataclass
from math import inf, nan
from pathlib import Path
import unittest

from decision.decision_quality_engine import (
    DecisionQualityEngine,
    DecisionQualityResult,
)
from decision.decision_score_engine import DecisionScoreResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class DecisionQualityEngineTest(unittest.TestCase):
    """Valida qualidade estatistica sem decidir direcao."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(DecisionQualityResult))
        self.assertTrue(DecisionQualityResult.__dataclass_params__.frozen)

    def test_engine_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(DecisionQualityEngine))
        self.assertTrue(DecisionQualityEngine.__dataclass_params__.frozen)

    def test_calcula_quality_scores(self) -> None:
        result = DecisionQualityEngine().evaluate(
            DecisionScoreResult(
                strategy_score=80.0,
                market_score=70.0,
                research_score=55.0,
                final_score=68.33,
            )
        )

        self.assertEqual(result.confidence_score, 68.33)
        self.assertEqual(result.consistency_score, 75.0)
        self.assertEqual(result.approval_score, 71.66)

    def test_consistency_score_perfeito_para_scores_iguais(self) -> None:
        result = DecisionQualityEngine().evaluate(
            DecisionScoreResult(
                strategy_score=75.0,
                market_score=75.0,
                research_score=75.0,
                final_score=75.0,
            )
        )

        self.assertEqual(result.consistency_score, 100.0)
        self.assertEqual(result.approval_score, 87.5)

    def test_normaliza_scores_invalidos_ou_fora_da_faixa(self) -> None:
        result = DecisionQualityEngine().evaluate(
            DecisionScoreResult(
                strategy_score=-10.0,
                market_score=150.0,
                research_score=nan,
                final_score=inf,
            )
        )

        self.assertEqual(result.confidence_score, 0.0)
        self.assertEqual(result.consistency_score, 0.0)
        self.assertEqual(result.approval_score, 0.0)

    def test_nao_modifica_score_result_recebido(self) -> None:
        score_result = DecisionScoreResult(
            strategy_score=-10.0,
            market_score=150.0,
            research_score=nan,
            final_score=inf,
        )

        DecisionQualityEngine().evaluate(score_result)

        self.assertEqual(score_result.strategy_score, -10.0)
        self.assertEqual(score_result.market_score, 150.0)
        self.assertNotEqual(score_result.research_score, score_result.research_score)
        self.assertEqual(score_result.final_score, inf)

    def test_resultado_e_imutavel(self) -> None:
        result = DecisionQualityEngine().evaluate(
            DecisionScoreResult(80.0, 70.0, 55.0, 68.33)
        )

        with self.assertRaises(FrozenInstanceError):
            result.approval_score = 0.0

    def test_engine_nao_decide_buy_sell_ou_acessa_pipeline(self) -> None:
        source = read_source(Path("decision/decision_quality_engine.py"))
        forbidden_fragments = (
            "BUY",
            "SELL",
            "WAIT",
            "DecisionPipeline",
            "ReplayEngine",
            "ExecutionOrder",
            "Broker",
            "MT5",
            "MetaTrader5",
            ".processar(",
            ".execute(",
            ".run(",
            "order_send",
            "execute_order",
            "final_decision",
            "approved =",
            "allowed =",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("decision/decision_quality_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
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


if __name__ == "__main__":
    unittest.main()
