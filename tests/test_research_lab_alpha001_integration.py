"""Testes de integracao da Alpha 001 com o Research Lab."""

import unittest

from application.research_lab_service import ResearchLabService
from alpha.alpha001_config import Alpha001Config
from core.events import STRATEGY_SIGNAL_CREATED
from domain.candle import Candle
from domain.contracts.strategy_signal import StrategySignal
from research.alpha001_experiment import Alpha001ExperimentResult
from research.research_lab import ResearchExperiment, ResearchLab
from research.strategy_benchmark import StrategyBenchmarkResult
from strategies.breakout import BreakoutStrategy
from strategies.strategy_factory import StrategyFactory


class ResearchLabAlpha001IntegrationTest(unittest.TestCase):
    """Valida execucao da Alpha 001 em experimentos quantitativos."""

    def test_research_lab_executa_alpha001_iorb_strategy(self) -> None:
        """Benchmark deve executar Alpha 001 registrada."""
        result = ResearchLab().run_strategy_benchmark(
            StrategyFactory().create("alpha001_iorb"),
            self._buy_candles(),
        )

        self.assertIsInstance(result, StrategyBenchmarkResult)
        self.assertEqual(result.strategy_name, "alpha001_iorb")

    def test_experimento_gera_sinal_buy(self) -> None:
        """Experimento com rompimento comprador deve gerar BUY."""
        experiment = self._run_experiment(self._buy_candles())

        signals = self._strategy_signals(experiment)

        self.assertIn("BUY", [signal.decision for signal in signals])

    def test_experimento_gera_sinal_sell(self) -> None:
        """Experimento com rompimento vendedor deve gerar SELL."""
        experiment = self._run_experiment(self._sell_candles())

        signals = self._strategy_signals(experiment)

        self.assertIn("SELL", [signal.decision for signal in signals])

    def test_experimento_gera_sinal_wait(self) -> None:
        """Experimento sem rompimento deve gerar WAIT."""
        experiment = self._run_experiment(self._wait_candles())

        signals = self._strategy_signals(experiment)

        self.assertIn("WAIT", [signal.decision for signal in signals])

    def test_metricas_continuam_sendo_calculadas(self) -> None:
        """Benchmark Alpha 001 deve retornar metricas existentes."""
        result = ResearchLab().run_strategy_benchmark(
            StrategyFactory().create("alpha001_iorb"),
            self._buy_candles(),
        )

        self.assertGreaterEqual(result.total_trades, 0)
        self.assertGreaterEqual(result.wins, 0)
        self.assertGreaterEqual(result.losses, 0)
        self.assertIsInstance(result.net_profit_points, float)
        self.assertIsInstance(result.equity_curve, list)

    def test_estrategias_existentes_continuam_funcionando(self) -> None:
        """Benchmark de estrategia antiga deve seguir funcionando."""
        result = ResearchLab().run_strategy_benchmark(
            BreakoutStrategy(),
            self._buy_candles(),
        )

        self.assertIsInstance(result, StrategyBenchmarkResult)
        self.assertEqual(result.strategy_name, "breakout")

    def test_alpha001_nao_executa_ordens_reais(self) -> None:
        """Research Lab deve manter apenas simulacao paper em memoria."""
        experiment = self._run_experiment(self._buy_candles())

        self.assertIsNotNone(experiment.result)
        self.assertTrue(hasattr(experiment.result, "order_preview"))
        self.assertTrue(hasattr(experiment.result, "paper_position"))

    def test_research_lab_executa_alpha001_experiment(self) -> None:
        """Research Lab deve executar Alpha001Experiment diretamente."""
        lab = ResearchLab()
        experiment = self._alpha001_experiment(self._buy_candles())

        completed = lab.run_alpha001_experiment(
            experiment,
            config=Alpha001Config(),
        )

        self.assertIsInstance(completed.result, Alpha001ExperimentResult)
        self.assertEqual(completed.result.total_buy, 1)
        self.assertEqual(completed.result.total_signals, 3)

    def test_research_lab_armazena_alpha001_experiment(self) -> None:
        """Experimento Alpha001 deve entrar no historico do Research Lab."""
        lab = ResearchLab()
        completed = lab.run_alpha001_experiment(
            self._alpha001_experiment(self._buy_candles())
        )

        self.assertEqual(lab.list_experiments(), [completed])
        self.assertEqual(lab.last_experiment(), completed)

    def test_research_lab_alpha001_experiment_coleta_strategy_signals(self) -> None:
        """Resultado integrado deve preservar StrategySignal gerados."""
        completed = ResearchLab().run_alpha001_experiment(
            self._alpha001_experiment(self._sell_candles())
        )

        signals = completed.result.signals

        self.assertTrue(all(isinstance(signal, StrategySignal) for signal in signals))
        self.assertIn("SELL", [signal.decision for signal in signals])

    def test_service_demo_benchmarks_inclui_alpha001(self) -> None:
        """Service deve incluir Alpha 001 usando StrategyFactory."""
        benchmarks = ResearchLabService().run_demo_benchmarks()

        names = [benchmark.strategy_name for benchmark in benchmarks]
        self.assertIn("alpha001_iorb", names)

    def _run_experiment(self, candles: list[Candle]) -> ResearchExperiment:
        experiment = ResearchExperiment(
            experiment_name="Alpha 001 integration",
            strategy_name="alpha001_iorb",
            stop_points=50.0,
            target_points=100.0,
            candles=candles,
        )
        return ResearchLab().run_experiment(experiment)

    def _alpha001_experiment(self, candles: list[Candle]) -> ResearchExperiment:
        return ResearchExperiment(
            experiment_name="Alpha 001 direct experiment",
            strategy_name="alpha001_iorb",
            stop_points=50.0,
            target_points=100.0,
            candles=candles,
        )

    def _strategy_signals(
        self,
        experiment: ResearchExperiment,
    ) -> list[StrategySignal]:
        events = experiment.result.recent_events
        return [
            event.payload["strategy_signal"]
            for event in events
            if event.event_name == STRATEGY_SIGNAL_CREATED
        ]

    def _buy_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 126.0, 128.0, 121.0, 1500),
        ]

    def _sell_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 110.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 94.0, 99.0, 92.0, 1500),
        ]

    def _wait_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 110.0, 116.0, 104.0, 1500),
        ]

    def _candle(
        self,
        candle_time: str,
        close: float,
        high: float,
        low: float,
        volume: int,
    ) -> Candle:
        return Candle(
            data=f"2026-06-26 {candle_time}",
            abertura=close,
            maxima=high,
            minima=low,
            fechamento=close,
            volume=volume,
        )


if __name__ == "__main__":
    unittest.main()
