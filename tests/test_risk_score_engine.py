"""Testes do engine quantitativo de score de risco."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from math import inf, nan
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
from risk.risk_profile import RiskProfile
from risk.risk_score_engine import RiskScoreEngine, RiskScoreResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class RiskScoreEngineTest(unittest.TestCase):
    """Valida score quantitativo sem aprovacao operacional."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(RiskScoreResult))
        self.assertTrue(RiskScoreResult.__dataclass_params__.frozen)

    def test_engine_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(RiskScoreEngine))
        self.assertTrue(RiskScoreEngine.__dataclass_params__.frozen)

    def test_calcula_scores_quantitativos(self) -> None:
        result = RiskScoreEngine().calculate(
            self._profile(),
            self._market_context(),
            self._data_quality(),
            self._research_result(),
            self._drawdown_result(),
        )

        self.assertEqual(result.exposure_score, 65.0)
        self.assertEqual(result.drawdown_score, 50.0)
        self.assertEqual(result.volatility_score, 80.0)
        self.assertEqual(result.research_score, 77.5)
        self.assertEqual(result.final_risk_score, 61.31)

    def test_data_quality_reduz_score_final_sem_alterar_scores_base(self) -> None:
        result = RiskScoreEngine().calculate(
            self._profile(),
            self._market_context(),
            MarketDataQualityResult(
                total_candles=100,
                valid_candles=50,
                invalid_candles=50,
                missing_candles=0,
                duplicated_candles=0,
                quality_score=50.0,
            ),
            self._research_result(),
            self._drawdown_result(),
        )

        self.assertEqual(result.exposure_score, 65.0)
        self.assertEqual(result.drawdown_score, 50.0)
        self.assertEqual(result.volatility_score, 80.0)
        self.assertEqual(result.research_score, 77.5)
        self.assertEqual(result.final_risk_score, 34.06)

    def test_normaliza_valores_invalidos_ou_fora_da_faixa(self) -> None:
        profile = replace(
            self._profile(),
            max_exposure=inf,
            max_drawdown_allowed=0.0,
            contracts=25,
        )
        market_context = replace(self._market_context(), volatility=nan)
        data_quality = replace(self._data_quality(), quality_score=150.0)
        drawdown = replace(self._drawdown_result(), max_drawdown_percent=inf)

        result = RiskScoreEngine().calculate(
            profile,
            market_context,
            data_quality,
            self._research_result(),
            drawdown,
        )

        self.assertEqual(result.exposure_score, 0.0)
        self.assertEqual(result.drawdown_score, 0.0)
        self.assertEqual(result.volatility_score, 100.0)
        self.assertEqual(result.research_score, 77.5)
        self.assertEqual(result.final_risk_score, 44.38)

    def test_resultado_e_imutavel(self) -> None:
        result = RiskScoreEngine().calculate(
            self._profile(),
            self._market_context(),
            self._data_quality(),
            self._research_result(),
            self._drawdown_result(),
        )

        with self.assertRaises(FrozenInstanceError):
            result.final_risk_score = 0.0

    def test_engine_nao_aprova_ou_executa_ordens(self) -> None:
        source = read_source(Path("risk/risk_score_engine.py"))
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
        path = Path("risk/risk_score_engine.py")
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


if __name__ == "__main__":
    unittest.main()
