"""Testes do relatorio Alpha001 exposto pela camada de aplicacao."""

import unittest

from application.research_lab_service import (
    Alpha001ResearchReportData,
    ResearchLabService,
)


class Alpha001ResearchReportTest(unittest.TestCase):
    """Valida relatorio Alpha001 existente sem acessar dashboard diretamente."""

    def test_retorna_dto_tipado_sem_benchmark(self) -> None:
        report = ResearchLabService().alpha001_research_report()

        self.assertIsInstance(report, Alpha001ResearchReportData)

    def test_retorna_validacao_pendente_sem_benchmark(self) -> None:
        report = ResearchLabService().alpha001_research_report()

        self.assertEqual(report.strategy_name, "alpha001_iorb")
        self.assertEqual(report.validation_status, "VALIDATION_PENDING")
        self.assertEqual(report.total_trades, 0)

    def test_nao_autoriza_operacao_real(self) -> None:
        report = ResearchLabService().alpha001_research_report()

        self.assertFalse(report.real_trading_authorized)

    def test_consolida_ultimo_benchmark_alpha001(self) -> None:
        service = ResearchLabService()
        service.run_demo_benchmarks()

        report = service.alpha001_research_report()

        self.assertIsInstance(report, Alpha001ResearchReportData)
        self.assertEqual(report.strategy_name, "alpha001_iorb")
        self.assertGreaterEqual(report.total_trades, 0)
        self.assertIsInstance(report.net_profit_points, float)

    def test_relatorio_nao_expoe_execucao_real(self) -> None:
        service = ResearchLabService()
        service.run_demo_benchmarks()

        report = service.alpha001_research_report()

        self.assertFalse(report.real_trading_authorized)
        self.assertNotIn("corretora", report.summary.lower())
        self.assertNotIn("mt5", report.summary.lower())


if __name__ == "__main__":
    unittest.main()
