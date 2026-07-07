"""Testes da integracao oficial Alpha001 no ResearchLabService."""

import unittest
from pathlib import Path

from alpha.alpha001_config import Alpha001Config
from application.alpha001_research_service import Alpha001ResearchService
from application.research_lab_service import ResearchLabService
from domain.candle import Candle
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_research_report import Alpha001ResearchResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchLabServiceAlpha001Test(unittest.TestCase):
    """Valida a entrada publica de pesquisa Alpha001."""

    def test_run_alpha001_research_retorna_resultado_consolidado(self) -> None:
        service = ResearchLabService()

        result = service.run_alpha001_research(self._candles())

        self.assertIsInstance(result, Alpha001ResearchResult)
        self.assertEqual(
            result.metrics.total_trades + result.metrics.total_wait,
            3,
        )
        self.assertGreaterEqual(result.metrics.total_trades, 0)

    def test_run_alpha001_research_executa_experimento_e_chama_service(
        self,
    ) -> None:
        spy = _SpyAlpha001ResearchService()
        service = ResearchLabService(alpha001_research_service=spy)

        result = service.run_alpha001_research(
            self._candles(),
            config=Alpha001Config(
                initial_stop_points=12.0,
                initial_target_points=34.0,
            ),
            experiment_name="Alpha001 Contrato",
        )

        self.assertIs(result, spy.result)
        self.assertIsInstance(spy.received, Alpha001ExperimentResult)
        self.assertEqual(spy.received.total_candles, 3)
        last = service.last_experiment()
        self.assertIsNotNone(last)
        self.assertEqual(last.experiment_name, "Alpha001 Contrato")
        self.assertEqual(last.stop_points, 12.0)
        self.assertEqual(last.target_points, 34.0)

    def test_run_alpha001_research_nao_calcula_metricas_diretamente(self) -> None:
        source = read_source(Path("application/research_lab_service.py"))
        method_source = source[
            source.index("    def run_alpha001_research") :
            source.index("    def run_historical_experiment")
        ]

        self.assertIn("run_alpha001_experiment", method_source)
        self.assertIn("alpha001_research_service.run", method_source)
        forbidden_fragments = (
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
            "Alpha001DrawdownEngine",
            "Alpha001WinRateEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001ExpectancyEngine",
            "gross_profit_points",
            "net_profit_points",
            "profit_factor",
            "win_rate",
            "max_drawdown",
            "expectancy",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in method_source
        ]

        self.assertEqual(leaked, [])

    def test_research_lab_service_permanece_sem_acoplamentos_proibidos(
        self,
    ) -> None:
        path = Path("application/research_lab_service.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "dashboard_app",
            "streamlit",
            "broker",
            "core.broker",
            "mt5",
            "MetaTrader5",
            "domain.contracts.strategy_signal",
        }
        forbidden_calls = {
            "order_send",
            "send_order",
            "place_order",
            "execute_order",
            "executar_ordem",
            "enviar_ordem",
            "connect_mt5",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _candles(self) -> list[Candle]:
        return [
            Candle("2026-06-26 09:00", 1000.0, 1005.0, 995.0, 1000.0, 1000),
            Candle("2026-06-26 09:01", 1000.0, 1100.0, 999.0, 1100.0, 1000),
            Candle("2026-06-26 09:02", 1100.0, 1110.0, 1040.0, 1050.0, 1200),
        ]


class _SpyAlpha001ResearchService:
    """Spy que preserva a execucao real do agregador."""

    def __init__(self) -> None:
        self.delegate = Alpha001ResearchService()
        self.received: Alpha001ExperimentResult | None = None
        self.result: Alpha001ResearchResult | None = None

    def run(
        self,
        experiment_result: Alpha001ExperimentResult,
    ) -> Alpha001ResearchResult:
        self.received = experiment_result
        self.result = self.delegate.run(experiment_result)
        return self.result


if __name__ == "__main__":
    unittest.main()
