"""Testes do engine de score consolidado da decisao."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from math import inf, nan
from pathlib import Path
import unittest

from decision.decision_assessment import DecisionAssessment
from decision.decision_score_engine import DecisionScoreEngine, DecisionScoreResult
from domain.contracts.decision_context import DecisionContext
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from research.research_engine import ResearchResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class DecisionScoreEngineTest(unittest.TestCase):
    """Valida score consolidado sem decisao operacional."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(DecisionScoreResult))
        self.assertTrue(DecisionScoreResult.__dataclass_params__.frozen)

    def test_engine_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(DecisionScoreEngine))
        self.assertTrue(DecisionScoreEngine.__dataclass_params__.frozen)

    def test_calcula_scores_normalizados_e_final_score(self) -> None:
        result = DecisionScoreEngine().calculate(self._assessment())

        self.assertEqual(result.strategy_score, 80.0)
        self.assertEqual(result.market_score, 70.0)
        self.assertEqual(result.research_score, 55.0)
        self.assertEqual(result.final_score, 68.33)

    def test_preserva_scores_ja_em_percentual(self) -> None:
        assessment = replace(
            self._assessment(),
            strategy_confidence=85.0,
            market_confidence=75.0,
            research_confidence=65.0,
        )

        result = DecisionScoreEngine().calculate(assessment)

        self.assertEqual(result.strategy_score, 85.0)
        self.assertEqual(result.market_score, 75.0)
        self.assertEqual(result.research_score, 65.0)
        self.assertEqual(result.final_score, 75.0)

    def test_limita_valores_invalidos_ou_fora_da_faixa(self) -> None:
        assessment = replace(
            self._assessment(),
            strategy_confidence=-1.0,
            market_confidence=inf,
            research_confidence=150.0,
        )

        result = DecisionScoreEngine().calculate(assessment)

        self.assertEqual(result.strategy_score, 0.0)
        self.assertEqual(result.market_score, 0.0)
        self.assertEqual(result.research_score, 100.0)
        self.assertEqual(result.final_score, 33.33)

    def test_trata_nan_como_zero(self) -> None:
        result = DecisionScoreEngine().calculate(
            replace(self._assessment(), strategy_confidence=nan)
        )

        self.assertEqual(result.strategy_score, 0.0)

    def test_nao_modifica_assessment_recebido(self) -> None:
        assessment = self._assessment()

        DecisionScoreEngine().calculate(assessment)

        self.assertEqual(assessment.strategy_confidence, 0.8)
        self.assertEqual(assessment.market_confidence, 0.7)
        self.assertEqual(assessment.research_confidence, 55.0)

    def test_resultado_e_imutavel(self) -> None:
        result = DecisionScoreEngine().calculate(self._assessment())

        with self.assertRaises(FrozenInstanceError):
            result.final_score = 0.0

    def test_engine_nao_aprova_decisoes_ou_acessa_pipeline_replay(self) -> None:
        source = read_source(Path("decision/decision_score_engine.py"))
        forbidden_fragments = (
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
            "approved =",
            "allowed =",
            "final_decision =",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("decision/decision_score_engine.py")
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

    def _assessment(self) -> DecisionAssessment:
        signal = StrategySignal("BUY", 80, 0.8, ["sinal forte"])
        risk = RiskDecision(True, "Risco aprovado", 1, 1.0)
        return DecisionAssessment(
            strategy_signal=signal,
            market_context=MarketContext(
                timestamp="2026-06-27T09:00:00-03:00",
                regime="TREND",
                volatility=20.0,
                liquidity=1500.0,
                momentum=8.0,
                session="OPENING",
                market_dna={"similarity": 80},
                confidence=0.7,
                metadata={},
            ),
            risk_decision=risk,
            research_result=ResearchResult(
                similar_scenarios=55,
                confidence=55.0,
                historical_score=55.0,
                average_momentum=7.5,
                average_trend_strength=0.65,
                history_strength="Historico forte",
                summary="Pesquisa consolidada.",
            ),
            decision_context=DecisionContext(
                strategy_signal=signal,
                market_snapshot=MarketSnapshot(
                    symbol="WDO",
                    datetime="2026-06-27 09:00",
                    regime="TREND",
                    volatility=20.0,
                    liquidity=1500.0,
                    trend_strength=0.7,
                    market_dna_score=80.0,
                ),
                risk_decision=risk,
                final_decision="BUY",
                final_confidence=0.8,
                approved=True,
            ),
            strategy_confidence=0.8,
            market_confidence=0.7,
            research_confidence=55.0,
            risk_status="ALLOWED",
            metadata={"source": "test"},
        )


if __name__ == "__main__":
    unittest.main()
