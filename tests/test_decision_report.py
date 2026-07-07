"""Testes do relatorio consolidado do Decision Lab."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from decision.decision_assessment import DecisionAssessment
from decision.decision_quality_engine import DecisionQualityResult
from decision.decision_report import DecisionReport
from decision.decision_score_engine import DecisionScoreResult
from domain.contracts.decision_context import DecisionContext
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from research.research_engine import ResearchResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class DecisionReportTest(unittest.TestCase):
    """Valida consolidacao sem calculo ou acoplamento operacional."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(DecisionReport))
        self.assertTrue(DecisionReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(DecisionReport)]

        self.assertEqual(
            field_names,
            [
                "assessment",
                "score_result",
                "quality_result",
                "strategy_score",
                "market_score",
                "research_score",
                "final_score",
                "confidence_score",
                "consistency_score",
                "approval_score",
                "execution_time",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = DecisionReport.__annotations__

        self.assertEqual(annotations["assessment"], "DecisionAssessment")
        self.assertEqual(annotations["score_result"], "DecisionScoreResult")
        self.assertEqual(annotations["quality_result"], "DecisionQualityResult")
        self.assertEqual(annotations["strategy_score"], "float")
        self.assertEqual(annotations["market_score"], "float")
        self.assertEqual(annotations["research_score"], "float")
        self.assertEqual(annotations["final_score"], "float")
        self.assertEqual(annotations["confidence_score"], "float")
        self.assertEqual(annotations["consistency_score"], "float")
        self.assertEqual(annotations["approval_score"], "float")
        self.assertEqual(annotations["execution_time"], "float")

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.assessment, DecisionAssessment)
        self.assertIsInstance(report.score_result, DecisionScoreResult)
        self.assertIsInstance(report.quality_result, DecisionQualityResult)
        self.assertEqual(report.strategy_score, 80.0)
        self.assertEqual(report.market_score, 70.0)
        self.assertEqual(report.research_score, 55.0)
        self.assertEqual(report.final_score, 68.33)
        self.assertEqual(report.confidence_score, 68.33)
        self.assertEqual(report.consistency_score, 75.0)
        self.assertEqual(report.approval_score, 71.67)
        self.assertEqual(report.execution_time, 12.5)

    def test_report_preserva_referencias_recebidas(self) -> None:
        assessment = self._assessment()
        score_result = self._score_result()
        quality_result = self._quality_result()

        report = DecisionReport(
            assessment=assessment,
            score_result=score_result,
            quality_result=quality_result,
            strategy_score=80.0,
            market_score=70.0,
            research_score=55.0,
            final_score=68.33,
            confidence_score=68.33,
            consistency_score=75.0,
            approval_score=71.67,
            execution_time=12.5,
        )

        self.assertIs(report.assessment, assessment)
        self.assertIs(report.score_result, score_result)
        self.assertIs(report.quality_result, quality_result)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.final_score = 0.0

    def test_report_nao_realiza_calculos_ou_gera_saida(self) -> None:
        source = read_source(Path("decision/decision_report.py"))
        forbidden_fragments = (
            "def ",
            "sum(",
            "max(",
            "min(",
            "round(",
            "Dashboard",
            "HTML",
            "PDF",
            "open(",
            "write(",
            "persist",
            "DecisionPipeline",
            "ReplayEngine",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("decision/decision_report.py")
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

    def _report(self) -> DecisionReport:
        return DecisionReport(
            assessment=self._assessment(),
            score_result=self._score_result(),
            quality_result=self._quality_result(),
            strategy_score=80.0,
            market_score=70.0,
            research_score=55.0,
            final_score=68.33,
            confidence_score=68.33,
            consistency_score=75.0,
            approval_score=71.67,
            execution_time=12.5,
        )

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
            metadata={"source": "test"},
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


if __name__ == "__main__":
    unittest.main()
