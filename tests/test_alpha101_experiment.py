"""Testes do experimento controlado da Alpha101."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from domain.candle import Candle
from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from replay.replay_engine import ReplayEngine
from research.alpha101.alpha101_experiment import (
    Alpha101Experiment,
    Alpha101ExperimentResult,
)
from research.research_pipeline import ResearchPipeline
from strategies.alpha101.alpha101_config import Alpha101Config
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha101ExperimentTest(unittest.TestCase):
    """Valida execucao estrutural da Alpha101 sem metricas financeiras."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha101ExperimentResult))
        self.assertTrue(Alpha101ExperimentResult.__dataclass_params__.frozen)

    def test_resultado_e_imutavel(self) -> None:
        result = Alpha101ExperimentResult(
            total_candles=0,
            total_signals=0,
            total_buy=0,
            total_sell=0,
            total_wait=0,
            execution_time_ms=0.0,
        )

        with self.assertRaises(FrozenInstanceError):
            result.total_buy = 1

    def test_experiment_executa_replay_e_consolida_sinais(self) -> None:
        experiment = Alpha101Experiment(
            config=self._config(),
            candles=self._candles(),
            strategy=_SequenceStrategy(("BUY", "SELL", "WAIT")),
        )

        result = experiment.run()

        self.assertIsInstance(result, Alpha101ExperimentResult)
        self.assertEqual(result.total_candles, 3)
        self.assertEqual(result.total_signals, 3)
        self.assertEqual(result.total_buy, 1)
        self.assertEqual(result.total_sell, 1)
        self.assertEqual(result.total_wait, 1)
        self.assertEqual([signal.decision for signal in result.signals], [
            "BUY",
            "SELL",
            "WAIT",
        ])
        self.assertGreaterEqual(result.execution_time_ms, 0.0)

    def test_experiment_reutiliza_replay_engine_injetado(self) -> None:
        replay_engine = ReplayEngine()

        result = Alpha101Experiment(
            config=self._config(),
            candles=self._candles(),
            strategy=_SequenceStrategy(("WAIT", "WAIT", "WAIT")),
            replay_engine=replay_engine,
        ).run()

        self.assertTrue(replay_engine.is_finished)
        self.assertFalse(replay_engine.is_running)
        self.assertEqual(replay_engine.current_index, 2)
        self.assertEqual(result.total_wait, 3)

    def test_experiment_expoe_research_pipeline_sem_executar_metricas(self) -> None:
        pipeline = ResearchPipeline()
        experiment = Alpha101Experiment(
            config=self._config(),
            candles=self._candles(),
            strategy=_SequenceStrategy(("WAIT", "WAIT", "WAIT")),
            research_pipeline=pipeline,
        )

        self.assertIs(experiment._research_pipeline(), pipeline)
        self.assertEqual(experiment.run().total_wait, 3)

    def test_experiment_usa_factories_de_contexto_e_features(self) -> None:
        contexts: list[Candle] = []
        reports: list[Candle] = []

        Alpha101Experiment(
            config=self._config(),
            candles=self._candles(),
            strategy=_InspectingStrategy(),
            market_context_factory=lambda candle: self._context(candle, contexts),
            feature_report_factory=lambda candle: self._feature_report(candle, reports),
        ).run()

        self.assertEqual(len(contexts), 3)
        self.assertEqual(len(reports), 3)

    def test_experiment_sem_candles_retorna_resultado_vazio(self) -> None:
        result = Alpha101Experiment(
            config=self._config(),
            candles=(),
            strategy=_SequenceStrategy(()),
        ).run()

        self.assertEqual(result.total_candles, 0)
        self.assertEqual(result.total_signals, 0)
        self.assertEqual(result.total_buy, 0)
        self.assertEqual(result.total_sell, 0)
        self.assertEqual(result.total_wait, 0)
        self.assertEqual(result.signals, ())

    def test_experiment_default_gera_features_de_swing_pullback(self) -> None:
        experiment = Alpha101Experiment(
            config=self._config(),
            candles=self._candles(),
            strategy=_InspectingStrategy(),
        )

        result = experiment.run()

        self.assertEqual(result.total_signals, 3)

    def test_experiment_nao_calcula_metricas_financeiras(self) -> None:
        source = read_source(Path("research/alpha101/alpha101_experiment.py"))
        forbidden_fragments = (
            "gross_profit",
            "gross_loss",
            "net_profit",
            "drawdown",
            "win_rate",
            "profit_factor",
            "expectancy",
            "Alpha001Experiment",
            "Alpha002Experiment",
            "Alpha003Experiment",
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
            "Alpha001DrawdownEngine",
            "Alpha001WinRateEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001ExpectancyEngine",
            "RiskEngine",
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

    def test_experiment_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/alpha101/alpha101_experiment.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "alpha.alpha001_config",
            "research.alpha001_experiment",
            "research.alpha002.alpha002_experiment",
            "research.alpha003.alpha003_experiment",
            "risk.risk_engine",
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
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("replay.replay_engine", imports)
        self.assertIn("research.research_pipeline", imports)

    def _config(self) -> Alpha101Config:
        return Alpha101Config(
            timeframe="DAILY",
            holding_period="SWING",
            stop_points=120.0,
            target_points=240.0,
            minimum_volume=1000.0,
            minimum_volatility=20.0,
            minimum_confidence=0.7,
            risk_profile="swing-research",
        )

    def _candles(self) -> tuple[Candle, ...]:
        return (
            Candle("2026-06-27T10:00:00-03:00", 5500.0, 5520.0, 5480.0, 5525.0, 2000),
            Candle("2026-06-27T10:01:00-03:00", 5525.0, 5530.0, 5490.0, 5510.0, 2100),
            Candle("2026-06-27T10:02:00-03:00", 5510.0, 5510.0, 5490.0, 5510.0, 1800),
        )

    def _context(
        self,
        candle: Candle,
        received: list[Candle],
    ) -> MarketContext:
        received.append(candle)
        return MarketContext(
            timestamp=candle.data,
            regime="TREND",
            volatility=float(candle.amplitude),
            liquidity=float(candle.volume),
            momentum=float(candle.fechamento - candle.abertura),
            session="REGULAR",
            market_dna={},
            confidence=1.0,
            metadata={
                "decision_approval_score": 1.0,
                "risk_policy_decision": "ALLOW",
                "research_validation_status": "PASSED",
                "research_confidence": 1.0,
            },
        )

    def _feature_report(
        self,
        candle: Candle,
        received: list[Candle],
    ) -> FeatureReport:
        received.append(candle)
        return FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "price": candle.fechamento,
                "trend_direction": "UP",
                "pullback_depth": abs(candle.fechamento - candle.abertura),
                "volume": candle.volume,
                "volatility": candle.amplitude,
                "momentum": candle.fechamento - candle.abertura,
                "data_quality_score": 1.0,
            },
            execution_time_ms=0.0,
        )


class _SequenceStrategy:
    def __init__(self, decisions: tuple[str, ...]) -> None:
        self.decisions = decisions
        self.index = 0

    def generate_signal(
        self,
        market_context: MarketContext,
        feature_report: FeatureReport,
    ) -> StrategySignal:
        decision = self.decisions[self.index]
        self.index += 1
        return StrategySignal(
            decision=decision,
            score=100 if decision != "WAIT" else 0,
            confidence=1.0 if decision != "WAIT" else 0.0,
            reasons=["test"],
        )


class _InspectingStrategy:
    def generate_signal(
        self,
        market_context: MarketContext,
        feature_report: FeatureReport,
    ) -> StrategySignal:
        self.assert_context(market_context)
        self.assert_report(feature_report)
        return StrategySignal("WAIT", 0, 0.0, ["test"])

    def assert_context(self, market_context: MarketContext) -> None:
        if not isinstance(market_context, MarketContext):
            raise AssertionError("market_context invalido")
        required = {
            "decision_approval_score",
            "risk_policy_decision",
            "research_validation_status",
            "research_confidence",
        }
        if not required.issubset(market_context.metadata):
            raise AssertionError("metadata de labs incompleta")

    def assert_report(self, feature_report: FeatureReport) -> None:
        if not isinstance(feature_report, FeatureReport):
            raise AssertionError("feature_report invalido")
        required = {
            "price",
            "trend_direction",
            "pullback_depth",
            "volume",
            "volatility",
            "momentum",
            "data_quality_score",
        }
        if not required.issubset(feature_report.calculated_values):
            raise AssertionError("feature_report incompleto")


if __name__ == "__main__":
    unittest.main()
