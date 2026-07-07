"""Testes do validador estatistico de experimentos."""

import unittest

from research.experiment_validator import (
    ExperimentValidation,
    ExperimentValidator,
)
from research.strategy_benchmark import StrategyBenchmarkResult


class ExperimentValidatorTest(unittest.TestCase):
    """Valida regras estatisticas simples do Research Lab."""

    def test_validate_menos_de_30_operacoes_nao_confiavel(self) -> None:
        """Garante classificacao de pouca amostra."""
        validation = ExperimentValidator().validate(
            self._benchmark(total_trades=20)
        )

        self.assertIsInstance(validation, ExperimentValidation)
        self.assertEqual(validation.sample_size, 20)
        self.assertFalse(validation.is_statistically_relevant)
        self.assertEqual(validation.confidence_level, "Nao confiavel")
        self.assertIn("Pouca amostra", validation.warnings)

    def test_validate_entre_30_e_100_confiabilidade_media(self) -> None:
        """Garante classificacao intermediaria."""
        validation = ExperimentValidator().validate(
            self._benchmark(total_trades=60, wins=35)
        )

        self.assertTrue(validation.is_statistically_relevant)
        self.assertEqual(validation.confidence_level, "Confiabilidade media")
        self.assertNotIn("Pouca amostra", validation.warnings)

    def test_validate_acima_de_100_confiabilidade_alta(self) -> None:
        """Garante classificacao alta."""
        validation = ExperimentValidator().validate(
            self._benchmark(total_trades=120, wins=70)
        )

        self.assertTrue(validation.is_statistically_relevant)
        self.assertEqual(validation.confidence_level, "Confiabilidade alta")

    def test_validate_alerta_poucas_vitorias(self) -> None:
        """Garante alerta de poucas vitorias."""
        validation = ExperimentValidator().validate(
            self._benchmark(total_trades=40, wins=5)
        )

        self.assertIn("Poucas vitorias", validation.warnings)

    def test_validate_alerta_profit_factor_baixo(self) -> None:
        """Garante alerta de profit factor baixo."""
        validation = ExperimentValidator().validate(
            self._benchmark(profit_factor=1.0)
        )

        self.assertIn("Profit Factor baixo", validation.warnings)

    def test_validate_alerta_win_rate_baixo(self) -> None:
        """Garante alerta de win rate baixo."""
        validation = ExperimentValidator().validate(
            self._benchmark(win_rate=0.30)
        )

        self.assertIn("Win Rate baixo", validation.warnings)

    def test_validate_summary_explica_resultado(self) -> None:
        """Garante resumo em linguagem simples."""
        validation = ExperimentValidator().validate(
            self._benchmark(total_trades=20)
        )

        self.assertIn("20 operacoes", validation.summary)
        self.assertIn("Nao confiavel", validation.summary)

    def _benchmark(
        self,
        total_trades: int = 50,
        wins: int = 30,
        losses: int = 20,
        profit_factor: float = 1.5,
        win_rate: float = 0.60,
    ) -> StrategyBenchmarkResult:
        return StrategyBenchmarkResult(
            strategy_name="benchmark",
            total_trades=total_trades,
            wins=wins,
            losses=losses,
            net_profit_points=100.0,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown_points=20.0,
            equity_curve=[0.0, 100.0],
        )


if __name__ == "__main__":
    unittest.main()
