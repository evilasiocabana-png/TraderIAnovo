"""Testes do relatorio consolidado de pesquisa."""

import unittest

from alpha.alpha001_config import Alpha001Config
from research.alpha001_experiment import Alpha001ExperimentResult
from research.research_report import ResearchReport, ResearchReportResult


class ResearchReportTest(unittest.TestCase):
    """Valida geracao deterministica de relatorio de experimento."""

    def test_gera_relatorio_tipado(self) -> None:
        report = ResearchReport(
            parameters=Alpha001Config(),
            experiment_result=self._result(),
        ).generate()

        self.assertIsInstance(report, ResearchReportResult)

    def test_relatorio_contem_parametros_utilizados(self) -> None:
        config = Alpha001Config(minimum_range_size=30.0, minimum_volume=2000.0)

        report = ResearchReport(
            parameters=config,
            experiment_result=self._result(),
        ).generate()

        self.assertEqual(report.parameters["minimum_range_size"], 30.0)
        self.assertEqual(report.parameters["minimum_volume"], 2000.0)

    def test_relatorio_contem_metricas_estruturais(self) -> None:
        report = ResearchReport(
            parameters=Alpha001Config(),
            experiment_result=self._result(),
        ).generate()

        self.assertEqual(report.metrics["total_candles"], 10)
        self.assertEqual(report.metrics["total_signals"], 10)
        self.assertEqual(report.metrics["total_buy"], 6)
        self.assertEqual(report.metrics["total_sell"], 4)
        self.assertEqual(report.metrics["total_wait"], 2)

    def test_relatorio_nao_contem_metricas_financeiras(self) -> None:
        report = ResearchReport(
            parameters=Alpha001Config(),
            experiment_result=self._result(),
        ).generate()

        self.assertNotIn("profit_factor", report.metrics)
        self.assertNotIn("win_rate", report.metrics)
        self.assertNotIn("max_drawdown_points", report.metrics)
        self.assertNotIn("net_profit", report.metrics)

    def test_relatorio_contem_resumo_estatistico(self) -> None:
        report = ResearchReport(
            parameters=Alpha001Config(),
            experiment_result=self._result(),
        ).generate()

        self.assertIn("10 candle(s)", report.statistical_summary)
        self.assertIn("10 signal(s)", report.statistical_summary)
        self.assertIn("6 BUY", report.statistical_summary)

    def test_conclusao_acceptable_para_execucao_com_sinais(self) -> None:
        report = ResearchReport(
            parameters=Alpha001Config(),
            experiment_result=self._result(),
        ).generate()

        self.assertEqual(report.conclusion, "ACCEPTABLE")

    def test_conclusao_inconclusive_sem_candles(self) -> None:
        report = ResearchReport(
            parameters=Alpha001Config(),
            experiment_result=self._result(total_candles=0, total_signals=0),
        ).generate()

        self.assertEqual(report.conclusion, "INCONCLUSIVE")

    def test_nao_utiliza_ia(self) -> None:
        with open("research/research_report.py", encoding="utf-8") as file:
            source = file.read().lower()

        self.assertNotIn("openai", source)
        self.assertNotIn("chatgpt", source)
        self.assertNotIn("llm", source)

    def _result(
        self,
        total_candles: int = 10,
        total_signals: int = 10,
    ) -> Alpha001ExperimentResult:
        return Alpha001ExperimentResult(
            total_candles=total_candles,
            total_signals=total_signals,
            total_buy=6,
            total_sell=4,
            total_wait=2,
            execution_time_ms=1.0,
        )


if __name__ == "__main__":
    unittest.main()
