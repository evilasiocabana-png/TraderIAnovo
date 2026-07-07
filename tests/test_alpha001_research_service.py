"""Testes do servico de pesquisa consolidada da Alpha 001."""

import unittest

from application.alpha001_research_service import Alpha001ResearchService
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_winrate_engine import Alpha001WinRateResult


class Alpha001ResearchServiceTest(unittest.TestCase):
    """Valida orquestracao dos engines Alpha001 pela camada Application."""

    def test_run_retorna_resultado_agregado_tipado(self) -> None:
        result = Alpha001ResearchService().run(self._experiment_result())

        self.assertIsInstance(result, Alpha001ResearchResult)
        self.assertIsInstance(result.metrics, Alpha001MetricsResult)
        self.assertIsInstance(result.profit, Alpha001ProfitResult)
        self.assertIsInstance(result.drawdown, Alpha001DrawdownResult)
        self.assertIsInstance(result.win_rate, Alpha001WinRateResult)
        self.assertIsInstance(result.profit_factor, Alpha001ProfitFactorResult)
        self.assertIsInstance(result.expectancy, Alpha001ExpectancyResult)

    def test_run_executa_engines_na_ordem_oficial(self) -> None:
        calls: list[str] = []
        profit_result = Alpha001ProfitResult(10.0, 5.0, 5.0)
        service = Alpha001ResearchService(
            metrics_engine=_SpyEngine("metrics", calls, Alpha001MetricsResult(1, 1, 0, 0)),
            profit_engine=_SpyEngine("profit", calls, profit_result),
            drawdown_engine=_SpyEngine(
                "drawdown",
                calls,
                Alpha001DrawdownResult((0.0, 5.0), 0.0, 0.0),
            ),
            win_rate_engine=_SpyEngine(
                "win_rate",
                calls,
                Alpha001WinRateResult(1, 0, 0, 1.0),
            ),
            profit_factor_engine=_SpyEngine(
                "profit_factor",
                calls,
                Alpha001ProfitFactorResult(2.0),
                expected_input=profit_result,
            ),
            expectancy_engine=_SpyEngine(
                "expectancy",
                calls,
                Alpha001ExpectancyResult(10.0, 5.0, 2.0, 5.0),
            ),
        )

        result = service.run(self._experiment_result())

        self.assertEqual(
            calls,
            ["metrics", "profit", "drawdown", "win_rate", "profit_factor", "expectancy"],
        )
        self.assertEqual(result.profit, profit_result)

    def test_nao_calcula_metricas_diretamente(self) -> None:
        with open(
            "application/alpha001_research_service.py",
            encoding="utf-8",
        ) as file:
            source = file.read()

        forbidden_fragments = (
            "Alpha001MetricsResult(",
            "Alpha001ProfitResult(",
            "Alpha001DrawdownResult(",
            "Alpha001WinRateResult(",
            "Alpha001ProfitFactorResult(",
            "Alpha001ExpectancyResult(",
            " / ",
            " * ",
            " + ",
            " - ",
        )
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

    def test_nao_acessa_camadas_proibidas(self) -> None:
        with open(
            "application/alpha001_research_service.py",
            encoding="utf-8",
        ) as file:
            source = file.read()

        forbidden_fragments = (
            "ReplayEngine",
            "DecisionPipeline",
            "EventBus",
            "Dashboard",
            "domain",
            "Broker",
            "MT5",
            "database",
        )
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

    def _experiment_result(self) -> Alpha001ExperimentResult:
        return Alpha001ExperimentResult(
            total_candles=1,
            total_signals=1,
            total_buy=1,
            total_sell=0,
            total_wait=0,
            execution_time_ms=1.0,
            signals=(),
        )


class _SpyEngine:
    """Engine controlado para validar ordem e entrada."""

    def __init__(
        self,
        name: str,
        calls: list[str],
        result: object,
        expected_input: object | None = None,
    ) -> None:
        self.name = name
        self.calls = calls
        self.result = result
        self.expected_input = expected_input

    def calculate(self, value: object) -> object:
        if self.expected_input is not None:
            assert value is self.expected_input
        self.calls.append(self.name)
        return self.result


if __name__ == "__main__":
    unittest.main()
