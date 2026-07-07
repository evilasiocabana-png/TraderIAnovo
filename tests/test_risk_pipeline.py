"""Testes do pipeline oficial do Risk Lab."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from market.context.market_context import MarketContext
from market.data.market_data_quality_engine import MarketDataQualityResult
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_win_rate_engine import Alpha001WinRateResult
from risk.risk_pipeline import RiskPipeline
from risk.risk_policy_engine import RiskPolicyResult
from risk.risk_profile import RiskProfile
from risk.risk_score_engine import RiskScoreResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class RiskPipelineTest(unittest.TestCase):
    """Valida orquestracao sem calculo direto ou execucao operacional."""

    def test_pipeline_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(RiskPipeline))
        self.assertTrue(RiskPipeline.__dataclass_params__.frozen)

    def test_pipeline_e_imutavel(self) -> None:
        pipeline = RiskPipeline()

        with self.assertRaises(FrozenInstanceError):
            pipeline.score_engine = _SpyScoreEngine()

    def test_pipeline_retorna_risk_policy_result(self) -> None:
        result = RiskPipeline().run(
            self._profile(),
            self._market_context(),
            self._data_quality(),
            self._research_result(),
            self._drawdown_result(),
        )

        self.assertIsInstance(result, RiskPolicyResult)
        self.assertEqual(result.decision, "REDUCE")
        self.assertEqual(result.final_risk_score, 61.31)

    def test_pipeline_delega_para_score_e_policy_engines(self) -> None:
        score_engine = _SpyScoreEngine()
        policy_engine = _SpyPolicyEngine()
        pipeline = RiskPipeline(
            score_engine=score_engine,
            policy_engine=policy_engine,
        )

        result = pipeline.run(
            self._profile(),
            self._market_context(),
            self._data_quality(),
            self._research_result(),
            self._drawdown_result(),
        )

        self.assertEqual(score_engine.calls, 1)
        self.assertEqual(policy_engine.calls, 1)
        self.assertIs(result, policy_engine.returned_result)

    def test_pipeline_encadeia_score_antes_da_politica(self) -> None:
        events: list[str] = []
        score_engine = _SpyScoreEngine(events=events)
        policy_engine = _SpyPolicyEngine(events=events)

        RiskPipeline(
            score_engine=score_engine,
            policy_engine=policy_engine,
        ).run(
            self._profile(),
            self._market_context(),
            self._data_quality(),
            self._research_result(),
            self._drawdown_result(),
        )

        self.assertEqual(events, ["score", "policy"])

    def test_pipeline_repassa_insumos_para_score_engine(self) -> None:
        score_engine = _SpyScoreEngine()
        profile = self._profile()
        market_context = self._market_context()
        data_quality = self._data_quality()
        research_result = self._research_result()
        drawdown_result = self._drawdown_result()

        RiskPipeline(
            score_engine=score_engine,
            policy_engine=_SpyPolicyEngine(),
        ).run(
            profile,
            market_context,
            data_quality,
            research_result,
            drawdown_result,
        )

        self.assertIs(score_engine.profile, profile)
        self.assertIs(score_engine.market_context, market_context)
        self.assertIs(score_engine.data_quality, data_quality)
        self.assertIs(score_engine.research_result, research_result)
        self.assertIs(score_engine.drawdown_result, drawdown_result)

    def test_pipeline_repassa_score_para_policy_engine(self) -> None:
        score_engine = _SpyScoreEngine()
        policy_engine = _SpyPolicyEngine()
        profile = self._profile()

        RiskPipeline(
            score_engine=score_engine,
            policy_engine=policy_engine,
        ).run(
            profile,
            self._market_context(),
            self._data_quality(),
            self._research_result(),
            self._drawdown_result(),
        )

        self.assertIs(policy_engine.profile, profile)
        self.assertIs(policy_engine.score_result, score_engine.returned_score)

    def test_pipeline_nao_calcula_score_ou_aplica_politica_diretamente(self) -> None:
        source = read_source(Path("risk/risk_pipeline.py"))
        forbidden_fragments = (
            "RiskEngine",
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
            "BLOCK_PAPER",
            "BLOCK_RESEARCH",
            "ALLOW",
            "REDUCE",
            "final_risk_score =",
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

    def test_pipeline_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("risk/risk_pipeline.py")
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
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
            "sum",
            "min",
            "max",
            "round",
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

    def _data_quality(self) -> MarketDataQualityResult:
        return MarketDataQualityResult(
            total_candles=100,
            valid_candles=90,
            invalid_candles=10,
            missing_candles=0,
            duplicated_candles=0,
            quality_score=90.0,
        )

    def _drawdown_result(self) -> Alpha001DrawdownResult:
        return Alpha001DrawdownResult(
            equity_curve=(0.0, 10.0, 5.0),
            max_drawdown_points=5.0,
            max_drawdown_percent=5.0,
        )

    def _research_result(self) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(
                total_trades=10,
                total_buy=6,
                total_sell=4,
                total_wait=2,
            ),
            profit=Alpha001ProfitResult(
                gross_profit_points=120.0,
                gross_loss_points=40.0,
                net_profit_points=60.0,
            ),
            drawdown=self._drawdown_result(),
            win_rate=Alpha001WinRateResult(
                winning_trades=6,
                losing_trades=4,
                breakeven_trades=0,
                win_rate=60.0,
            ),
            profit_factor=Alpha001ProfitFactorResult(profit_factor=2.2),
            expectancy=Alpha001ExpectancyResult(
                average_win=20.0,
                average_loss=10.0,
                payoff_ratio=2.0,
                expectancy=90.0,
            ),
        )


class _SpyScoreEngine:
    def __init__(self, events: list[str] | None = None) -> None:
        self.events = events
        self.calls = 0
        self.profile: RiskProfile | None = None
        self.market_context: MarketContext | None = None
        self.data_quality: MarketDataQualityResult | None = None
        self.research_result: Alpha001ResearchResult | None = None
        self.drawdown_result: Alpha001DrawdownResult | None = None
        self.returned_score = RiskScoreResult(
            exposure_score=80.0,
            drawdown_score=80.0,
            volatility_score=80.0,
            research_score=80.0,
            final_risk_score=80.0,
        )

    def calculate(
        self,
        profile: RiskProfile,
        market_context: MarketContext,
        data_quality: MarketDataQualityResult,
        research_result: Alpha001ResearchResult,
        drawdown_result: Alpha001DrawdownResult,
    ) -> RiskScoreResult:
        if self.events is not None:
            self.events.append("score")
        self.calls += 1
        self.profile = profile
        self.market_context = market_context
        self.data_quality = data_quality
        self.research_result = research_result
        self.drawdown_result = drawdown_result
        return self.returned_score


class _SpyPolicyEngine:
    def __init__(self, events: list[str] | None = None) -> None:
        self.events = events
        self.calls = 0
        self.profile: RiskProfile | None = None
        self.score_result: RiskScoreResult | None = None
        self.returned_result = RiskPolicyResult(
            decision="ALLOW",
            reason="test",
            final_risk_score=80.0,
        )

    def evaluate(
        self,
        profile: RiskProfile,
        score_result: RiskScoreResult,
    ) -> RiskPolicyResult:
        if self.events is not None:
            self.events.append("policy")
        self.calls += 1
        self.profile = profile
        self.score_result = score_result
        return self.returned_result


if __name__ == "__main__":
    unittest.main()
