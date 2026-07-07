"""Testes do relatorio paper Alpha001 exposto ao dashboard."""

import ast
from dataclasses import dataclass
from pathlib import Path
import unittest

from application.dashboard_service import DashboardService
from application.paper_trading_service import PaperTradingService
from domain.contracts.execution_order import ExecutionOrder


@dataclass(frozen=True)
class ClosedPaperTrade:
    """Registro fechado usado para simular historico paper."""

    side: str
    result_points: float
    status: str = "CLOSED"


class DashboardAlpha001PaperReportTest(unittest.TestCase):
    """Valida exposicao do relatorio paper via DashboardService."""

    def test_dashboard_service_expoe_relatorio_paper(self):
        service = self._dashboard_service_with_history([10.0, -5.0, 20.0])

        report = service.get_alpha001_paper_report()

        self.assertEqual(report.status, "PAPER ONLY")
        self.assertEqual(report.total_operations, 3)
        self.assertEqual(report.accumulated_result_points, 25.0)

    def test_dashboard_data_inclui_relatorio_paper(self):
        service = self._dashboard_service_with_history([10.0, -5.0])

        data = service.get_dashboard_data()

        self.assertEqual(data.alpha001_paper_report.total_operations, 2)
        self.assertEqual(data.alpha001_paper_report.paper_win_rate, 0.5)

    def test_relatorio_expoe_maior_drawdown(self):
        service = self._dashboard_service_with_history([30.0, -10.0, -15.0])

        report = service.get_alpha001_paper_report()

        self.assertEqual(report.max_drawdown_points, 25.0)

    def test_relatorio_expoe_sequencia_maxima_de_perdas(self):
        service = self._dashboard_service_with_history(
            [10.0, -5.0, -7.0, 3.0],
        )

        report = service.get_alpha001_paper_report()

        self.assertEqual(report.max_loss_sequence, 2)

    def test_relatorio_expoe_posicao_atual(self):
        paper_service = PaperTradingService()
        paper_service.paper_history.append(self._open_order())
        service = DashboardService(paper_trading_service=paper_service)

        report = service.get_alpha001_paper_report()

        self.assertIsNotNone(report.current_position)
        self.assertEqual(report.current_position.side, "BUY")
        self.assertEqual(report.current_position.status, "OPEN")

    def test_dashboard_nao_importa_paper_trading_diretamente(self):
        imports = self._imports(Path("dashboard_app.py"))

        self.assertNotIn("application.paper_trading_service", imports)
        self.assertNotIn("paper.paper_trading_engine", imports)

    def test_dashboard_nao_acessa_broker_ou_mt5(self):
        imports = self._imports(Path("dashboard_app.py"))

        self.assertNotIn("broker", imports)
        self.assertNotIn("MetaTrader5", imports)

    def test_dashboard_nao_calcula_metricas_paper_diretamente(self):
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertNotIn("paper_win_rate =", source)
        self.assertNotIn("max_loss_sequence =", source)
        self.assertNotIn("max_drawdown_points =", source)

    def _dashboard_service_with_history(self, results: list[float]):
        paper_service = PaperTradingService()
        paper_service.paper_history.extend(
            ClosedPaperTrade("BUY" if result >= 0 else "SELL", result)
            for result in results
        )
        return DashboardService(paper_trading_service=paper_service)

    def _open_order(self):
        return ExecutionOrder(
            side="BUY",
            quantity=1,
            entry_price=1000.0,
            stop=950.0,
            target=1100.0,
        )

    def _imports(self, path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        return imports


if __name__ == "__main__":
    unittest.main()
