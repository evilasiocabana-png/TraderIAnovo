"""Testes do runner de pesquisa da Alpha 001."""

import unittest

from domain.candle import Candle
from research.alpha001_experiment_validator import (
    Alpha001ExperimentValidator,
    Alpha001ValidationResult,
)
from research.alpha001_research_advisor import Alpha001ResearchAdvice
from research.alpha001_research_runner import (
    Alpha001ResearchResult,
    Alpha001ResearchRunner,
)
from research.research_lab import ResearchExperiment


class Alpha001ResearchRunnerTest(unittest.TestCase):
    """Valida orquestracao completa de pesquisa da Alpha 001."""

    def test_executa_multiplos_experimentos(self) -> None:
        """Runner deve executar todos os experimentos recebidos."""
        result = self._runner().run(
            [self._experiment("buy"), self._experiment("sell")],
        )

        self.assertEqual(result.total_experiments, 2)
        self.assertEqual(result.experiments_executed, 2)

    def test_consolida_resultados(self) -> None:
        """Runner deve consolidar validacoes por experimento."""
        result = self._runner().run([self._experiment("buy")])

        self.assertEqual(result.strategy_name, "alpha001_iorb")
        self.assertEqual(len(result.validation_results), 1)
        self.assertEqual(
            result.validation_results[0]["experiment_name"],
            "buy",
        )

    def test_consolida_recomendacoes(self) -> None:
        """Runner deve incluir recomendacoes do advisor."""
        result = self._runner().run([self._experiment("buy")])

        advice = result.validation_results[0]["advice"]

        self.assertIsInstance(advice, Alpha001ResearchAdvice)
        self.assertIn(advice.recommendation, result.summary)

    def test_valida_alpha001_research_result(self) -> None:
        """Runner deve retornar Alpha001ResearchResult."""
        result = self._runner().run([self._experiment("buy")])

        self.assertIsInstance(result, Alpha001ResearchResult)

    def test_garante_execucao_sem_excecoes(self) -> None:
        """Runner deve aceitar colecao vazia sem quebrar."""
        result = self._runner().run([])

        self.assertEqual(result.total_experiments, 0)
        self.assertEqual(result.experiments_executed, 0)
        self.assertEqual(result.validation_results, [])

    def test_validation_results_contem_alpha001_validation_result(self) -> None:
        """Cada entrada deve conter resultado do validator."""
        result = self._runner().run([self._experiment("buy")])

        validation = result.validation_results[0]["validation"]

        self.assertIsInstance(validation, Alpha001ValidationResult)

    def test_executa_lote_de_opening_ranges(self) -> None:
        """Runner deve aceitar diferentes configuracoes de Opening Range."""
        result = self._runner().run(
            [
                self._opening_range_experiment(5),
                self._opening_range_experiment(10),
                self._opening_range_experiment(15),
                self._opening_range_experiment(20),
            ]
        )

        self.assertEqual(result.total_experiments, 4)
        self.assertEqual(result.experiments_executed, 4)

    def test_consolida_aprovados_e_rejeitados(self) -> None:
        """Runner deve sumarizar aprovacoes e rejeicoes."""
        result = self._runner().run(
            [self._experiment("buy"), self._empty_experiment()]
        )

        self.assertEqual(result.approved, 1)
        self.assertEqual(result.rejected, 1)

    def test_retorna_melhor_configuracao(self) -> None:
        """Melhor configuracao deve vir do maior lucro liquido."""
        result = self._runner().run(
            [self._experiment("buy"), self._empty_experiment()]
        )

        self.assertIsNotNone(result.best_configuration)
        self.assertEqual(result.best_configuration["experiment_name"], "buy")
        self.assertIn("net_profit_points", result.best_configuration)

    def test_retorna_resumo_estatistico(self) -> None:
        """Runner deve consolidar estatisticas do lote."""
        result = self._runner().run(
            [self._experiment("buy"), self._empty_experiment()]
        )

        self.assertIn("average_net_profit_points", result.statistical_summary)
        self.assertIn("average_win_rate", result.statistical_summary)
        self.assertIn("average_profit_factor", result.statistical_summary)
        self.assertIn("best_net_profit_points", result.statistical_summary)

    def test_summary_inclui_aprovados_rejeitados_e_melhor(self) -> None:
        """Resumo textual deve explicar o lote executado."""
        result = self._runner().run(
            [self._experiment("buy"), self._empty_experiment()]
        )

        self.assertIn("Aprovados: 1", result.summary)
        self.assertIn("Rejeitados: 1", result.summary)
        self.assertIn("Melhor configuracao: buy", result.summary)

    def _runner(self) -> Alpha001ResearchRunner:
        return Alpha001ResearchRunner(
            validator=Alpha001ExperimentValidator(
                minimum_total_trades=1,
                minimum_win_rate=0.0,
                minimum_profit_factor=0.0,
                maximum_drawdown_points=500.0,
                minimum_net_profit_points=-500.0,
            )
        )

    def _experiment(self, name: str) -> ResearchExperiment:
        return ResearchExperiment(
            experiment_name=name,
            strategy_name="alpha001_iorb",
            stop_points=50.0,
            target_points=100.0,
            candles=self._candles(name),
        )

    def _opening_range_experiment(self, minutes: int) -> ResearchExperiment:
        return ResearchExperiment(
            experiment_name=f"opening_range_{minutes}_min",
            strategy_name="alpha001_iorb",
            stop_points=50.0,
            target_points=100.0,
            candles=self._opening_range_candles(minutes),
        )

    def _empty_experiment(self) -> ResearchExperiment:
        return ResearchExperiment(
            experiment_name="empty",
            strategy_name="alpha001_iorb",
            stop_points=50.0,
            target_points=100.0,
            candles=[],
        )

    def _candles(self, scenario: str) -> list[Candle]:
        if scenario == "sell":
            return self._sell_candles()
        return self._buy_candles()

    def _buy_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 126.0, 128.0, 121.0, 1500),
            self._candle("09:17", 226.0, 230.0, 126.0, 1500),
        ]

    def _sell_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 110.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 94.0, 99.0, 92.0, 1500),
            self._candle("09:17", -6.0, 94.0, -10.0, 1500),
        ]

    def _opening_range_candles(self, minutes: int) -> list[Candle]:
        breakout_minute = minutes + 1
        return [
            self._candle("09:00", 100.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle(
                f"09:{breakout_minute:02d}",
                126.0,
                128.0,
                121.0,
                1500,
            ),
            self._candle(
                f"09:{breakout_minute + 1:02d}",
                226.0,
                230.0,
                126.0,
                1500,
            ),
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
