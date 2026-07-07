"""Testes do status paper Alpha001 exposto ao dashboard."""

import ast
from pathlib import Path
import unittest

from application.dashboard_service import DashboardService
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.strategy_signal import StrategySignal


class DashboardAlpha001PaperStatusTest(unittest.TestCase):
    """Valida exposicao paper somente via DashboardService."""

    def test_dashboard_service_expoe_status_paper_only(self):
        status = DashboardService().get_alpha001_paper_status()

        self.assertEqual("PAPER ONLY", status.status)
        self.assertFalse(status.real_trading_authorized)
        self.assertFalse(status.broker_integrated)
        self.assertFalse(status.mt5_integrated)

    def test_dashboard_data_inclui_status_paper_alpha001(self):
        data = DashboardService().get_dashboard_data()

        self.assertEqual("PAPER ONLY", data.alpha001_paper_status.status)
        self.assertEqual([0.0], data.alpha001_paper_status.equity_curve)

    def test_exibe_posicao_paper_atual_apos_buy(self):
        service = DashboardService()

        status = service.process_alpha001_paper_signal(
            self._signal("BUY"),
            self._snapshot(100.0),
        )

        self.assertIsNotNone(status.position)
        self.assertEqual("BUY", status.position.side)
        self.assertEqual("OPEN", status.position.status)

    def test_exibe_historico_operacoes_paper(self):
        service = DashboardService()
        service.process_alpha001_paper_signal(
            self._signal("BUY"),
            self._snapshot(100.0),
        )

        status = service.process_alpha001_paper_signal(
            self._signal("WAIT"),
            self._snapshot(200.0),
        )

        self.assertEqual(1, status.total_trades)
        self.assertEqual(1, len(status.trades_history))
        self.assertEqual("TARGET", status.trades_history[0].close_reason)

    def test_exibe_equity_curve_e_resultado_acumulado(self):
        service = DashboardService()
        service.process_alpha001_paper_signal(
            self._signal("BUY"),
            self._snapshot(100.0),
        )

        status = service.process_alpha001_paper_signal(
            self._signal("WAIT"),
            self._snapshot(200.0),
        )

        self.assertEqual([0.0, 100.0], status.equity_curve)
        self.assertEqual(100.0, status.accumulated_result_points)

    def test_estado_paper_persiste_no_dashboard_service(self):
        service = DashboardService()
        service.process_alpha001_paper_signal(
            self._signal("BUY"),
            self._snapshot(100.0),
        )
        service.process_alpha001_paper_signal(
            self._signal("WAIT"),
            self._snapshot(200.0),
        )

        status = service.get_alpha001_paper_status()

        self.assertEqual(1, status.total_trades)
        self.assertEqual(100.0, status.accumulated_result_points)

    def test_dashboard_nao_importa_paper_trading_diretamente(self):
        imports = self._imports(Path("dashboard_app.py"))

        self.assertNotIn("paper.paper_trading_engine", imports)
        self.assertNotIn("application.paper_trading_service", imports)

    def test_dashboard_nao_acessa_broker_ou_mt5(self):
        imports = self._imports(Path("dashboard_app.py"))

        self.assertNotIn("broker", imports)
        self.assertNotIn("MetaTrader5", imports)

    def _signal(self, decision):
        return StrategySignal(
            decision=decision,
            score=100 if decision != "WAIT" else 0,
            confidence=1.0 if decision != "WAIT" else 0.0,
            reasons=[decision],
        )

    def _snapshot(self, price):
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-26 09:00:00",
            regime="TREND",
            volatility=1.0,
            liquidity=1.0,
            trend_strength=1.0,
            market_dna_score=price,
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
