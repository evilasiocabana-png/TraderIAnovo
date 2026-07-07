"""Testes do contrato de assessment de decisao."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from decision.decision_assessment import DecisionAssessment
from domain.contracts.decision_context import DecisionContext
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from research.research_engine import ResearchResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class DecisionAssessmentTest(unittest.TestCase):
    """Valida consolidacao de insumos de decisao."""

    def test_assessment_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(DecisionAssessment))
        self.assertTrue(DecisionAssessment.__dataclass_params__.frozen)

    def test_assessment_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(DecisionAssessment)]

        self.assertEqual(
            field_names,
            [
                "strategy_signal",
                "market_context",
                "risk_decision",
                "research_result",
                "decision_context",
                "strategy_confidence",
                "market_confidence",
                "research_confidence",
                "risk_status",
                "metadata",
            ],
        )

    def test_assessment_possui_type_hints_explicitos(self) -> None:
        annotations = DecisionAssessment.__annotations__

        self.assertEqual(annotations["strategy_signal"], "StrategySignal")
        self.assertEqual(annotations["market_context"], "MarketContext")
        self.assertEqual(annotations["risk_decision"], "RiskDecision")
        self.assertEqual(annotations["research_result"], "ResearchResult")
        self.assertEqual(annotations["decision_context"], "DecisionContext")
        self.assertEqual(annotations["strategy_confidence"], "float")
        self.assertEqual(annotations["market_confidence"], "float")
        self.assertEqual(annotations["research_confidence"], "float")
        self.assertEqual(annotations["risk_status"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_assessment_agrega_componentes_tipados(self) -> None:
        assessment = self._assessment()

        self.assertIsInstance(assessment.strategy_signal, StrategySignal)
        self.assertIsInstance(assessment.market_context, MarketContext)
        self.assertIsInstance(assessment.risk_decision, RiskDecision)
        self.assertIsInstance(assessment.research_result, ResearchResult)
        self.assertIsInstance(assessment.decision_context, DecisionContext)
        self.assertEqual(assessment.strategy_confidence, 0.8)
        self.assertEqual(assessment.market_confidence, 0.7)
        self.assertEqual(assessment.research_confidence, 55.0)
        self.assertEqual(assessment.risk_status, "ALLOWED")
        self.assertEqual(assessment.metadata["source"], "test")

    def test_assessment_preserva_referencias_recebidas(self) -> None:
        signal = self._signal()
        context = self._market_context()
        risk = self._risk()
        research = self._research()
        decision_context = self._decision_context(signal, risk)
        metadata = {"source": "test"}

        assessment = DecisionAssessment(
            strategy_signal=signal,
            market_context=context,
            risk_decision=risk,
            research_result=research,
            decision_context=decision_context,
            strategy_confidence=0.8,
            market_confidence=0.7,
            research_confidence=55.0,
            risk_status="ALLOWED",
            metadata=metadata,
        )

        self.assertIs(assessment.strategy_signal, signal)
        self.assertIs(assessment.market_context, context)
        self.assertIs(assessment.risk_decision, risk)
        self.assertIs(assessment.research_result, research)
        self.assertIs(assessment.decision_context, decision_context)
        self.assertIs(assessment.metadata, metadata)

    def test_assessment_e_imutavel(self) -> None:
        assessment = self._assessment()

        with self.assertRaises(FrozenInstanceError):
            assessment.risk_status = "BLOCKED"

    def test_assessment_nao_toma_decisao_ou_aprova_ordens(self) -> None:
        source = read_source(Path("decision/decision_assessment.py"))
        forbidden_fragments = (
            "DecisionPipeline",
            "ExecutionOrder",
            "OrderManager",
            "Broker",
            "MT5",
            "MetaTrader5",
            ".processar(",
            ".run(",
            ".execute(",
            "order_send",
            "execute_order",
            "send_order",
            "approved =",
            "allowed =",
            "final_decision =",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_assessment_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("decision/decision_assessment.py")
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
        signal = self._signal()
        risk = self._risk()
        return DecisionAssessment(
            strategy_signal=signal,
            market_context=self._market_context(),
            risk_decision=risk,
            research_result=self._research(),
            decision_context=self._decision_context(signal, risk),
            strategy_confidence=0.8,
            market_confidence=0.7,
            research_confidence=55.0,
            risk_status="ALLOWED",
            metadata={"source": "test"},
        )

    def _signal(self) -> StrategySignal:
        return StrategySignal(
            decision="BUY",
            score=80,
            confidence=0.8,
            reasons=["sinal forte"],
        )

    def _risk(self) -> RiskDecision:
        return RiskDecision(
            allowed=True,
            reason="Risco aprovado",
            max_contracts=1,
            risk_multiplier=1.0,
        )

    def _decision_context(
        self,
        signal: StrategySignal,
        risk: RiskDecision,
    ) -> DecisionContext:
        return DecisionContext(
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
        )

    def _market_context(self) -> MarketContext:
        return MarketContext(
            timestamp="2026-06-27T09:00:00-03:00",
            regime="TREND",
            volatility=20.0,
            liquidity=1500.0,
            momentum=8.0,
            session="OPENING",
            market_dna={"similarity": 80},
            confidence=0.7,
            metadata={},
        )

    def _research(self) -> ResearchResult:
        return ResearchResult(
            similar_scenarios=55,
            confidence=55.0,
            historical_score=55.0,
            average_momentum=7.5,
            average_trend_strength=0.65,
            history_strength="Historico forte",
            summary="Pesquisa consolidada.",
        )


if __name__ == "__main__":
    unittest.main()
