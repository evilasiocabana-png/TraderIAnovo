"""Testes do adaptador entre Decision Lab e DecisionPipeline."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from decision.decision_assessment import DecisionAssessment
from decision.decision_pipeline_adapter import DecisionPipelineAdapter
from decision.decision_quality_engine import DecisionQualityResult
from decision.decision_score_engine import DecisionScoreResult
from domain.contracts.decision_context import DecisionContext
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from research.research_engine import ResearchResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class DecisionPipelineAdapterTest(unittest.TestCase):
    """Valida conversao para o contrato do pipeline central."""

    def test_adapter_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(DecisionPipelineAdapter))
        self.assertTrue(DecisionPipelineAdapter.__dataclass_params__.frozen)

    def test_adapter_e_imutavel(self) -> None:
        adapter = DecisionPipelineAdapter()

        with self.assertRaises(FrozenInstanceError):
            adapter.pipeline = _SpyDecisionPipeline()

    def test_adapter_retorna_decision_context(self) -> None:
        context = DecisionPipelineAdapter().adapt(
            self._assessment(),
            self._score_result(),
            self._quality_result(),
        )

        self.assertIsInstance(context, DecisionContext)
        self.assertEqual(context.final_decision, "BUY")
        self.assertEqual(context.final_confidence, 0.6833)
        self.assertTrue(context.approved)

    def test_adapter_delega_para_pipeline_existente(self) -> None:
        pipeline = _SpyDecisionPipeline()
        adapter = DecisionPipelineAdapter(pipeline=pipeline)

        context = adapter.adapt(
            self._assessment(),
            self._score_result(),
            self._quality_result(),
        )

        self.assertEqual(pipeline.calls, 1)
        self.assertIs(context, pipeline.returned_context)

    def test_adapter_converte_strategy_signal(self) -> None:
        pipeline = _SpyDecisionPipeline()

        DecisionPipelineAdapter(pipeline=pipeline).adapt(
            self._assessment(),
            self._score_result(),
            self._quality_result(),
        )

        signal = pipeline.strategy_signal
        self.assertIsInstance(signal, StrategySignal)
        self.assertEqual(signal.decision, "BUY")
        self.assertEqual(signal.score, 68)
        self.assertEqual(signal.confidence, 0.6833)
        self.assertEqual(signal.reasons, ["sinal forte"])

    def test_adapter_converte_market_snapshot(self) -> None:
        pipeline = _SpyDecisionPipeline()

        DecisionPipelineAdapter(pipeline=pipeline).adapt(
            self._assessment(),
            self._score_result(),
            self._quality_result(),
        )

        snapshot = pipeline.market_snapshot
        self.assertIsInstance(snapshot, MarketSnapshot)
        self.assertEqual(snapshot.symbol, "WDO")
        self.assertEqual(snapshot.datetime, "2026-06-27T09:00:00-03:00")
        self.assertEqual(snapshot.regime, "TREND")
        self.assertEqual(snapshot.volatility, 20.0)
        self.assertEqual(snapshot.liquidity, 1500.0)
        self.assertEqual(snapshot.trend_strength, 0.7)
        self.assertEqual(snapshot.market_dna_score, 80.0)

    def test_adapter_preserva_risk_decision(self) -> None:
        pipeline = _SpyDecisionPipeline()
        assessment = self._assessment()

        DecisionPipelineAdapter(pipeline=pipeline).adapt(
            assessment,
            self._score_result(),
            self._quality_result(),
        )

        self.assertIs(pipeline.risk_decision, assessment.risk_decision)

    def test_adapter_nao_altera_pipeline_contexto_ou_domain(self) -> None:
        source = read_source(Path("decision/decision_pipeline_adapter.py"))
        forbidden_fragments = (
            "class DecisionPipeline:",
            "class DecisionContext:",
            "class StrategySignal:",
            "class RiskDecision:",
            "class MarketSnapshot:",
            "OrderManager",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            "send_order",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_adapter_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("decision/decision_pipeline_adapter.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
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
        signal = StrategySignal(
            decision="BUY",
            score=80,
            confidence=0.8,
            reasons=["sinal forte"],
        )
        risk = RiskDecision(
            allowed=True,
            reason="Risco aprovado",
            max_contracts=1,
            risk_multiplier=1.0,
        )
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
            metadata={
                "source": "test",
                "symbol": "WDO",
                "trend_strength": 0.7,
            },
        )

    def _score_result(self) -> DecisionScoreResult:
        return DecisionScoreResult(
            strategy_score=80.0,
            market_score=70.0,
            research_score=55.0,
            final_score=68.33,
        )

    def _quality_result(self) -> DecisionQualityResult:
        return DecisionQualityResult(
            confidence_score=68.33,
            consistency_score=75.0,
            approval_score=71.67,
        )


class _SpyDecisionPipeline:
    def __init__(self) -> None:
        self.calls = 0
        self.strategy_signal: StrategySignal | None = None
        self.market_snapshot: MarketSnapshot | None = None
        self.risk_decision: RiskDecision | None = None
        self.returned_context: DecisionContext | None = None

    def processar(
        self,
        strategy_signal: StrategySignal,
        market_snapshot: MarketSnapshot,
        risk_decision: RiskDecision,
    ) -> DecisionContext:
        self.calls += 1
        self.strategy_signal = strategy_signal
        self.market_snapshot = market_snapshot
        self.risk_decision = risk_decision
        self.returned_context = DecisionContext(
            strategy_signal=strategy_signal,
            market_snapshot=market_snapshot,
            risk_decision=risk_decision,
            final_decision=strategy_signal.decision,
            final_confidence=strategy_signal.confidence,
            approved=risk_decision.allowed,
        )
        return self.returned_context


if __name__ == "__main__":
    unittest.main()
