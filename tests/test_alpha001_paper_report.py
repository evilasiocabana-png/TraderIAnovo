"""Testes do relatorio operacional paper Alpha001."""

import ast
from dataclasses import dataclass
from pathlib import Path
import unittest

from application.paper_trading_service import (
    PaperTradingReport,
    PaperTradingService,
)
from core.configuration_manager import ConfigurationManager
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.strategy_signal import StrategySignal


@dataclass(frozen=True)
class ClosedPaperTrade:
    """Registro fechado usado para testar consolidacao paper."""

    side: str
    result_points: float
    status: str = "CLOSED"


class Alpha001PaperReportTest(unittest.TestCase):
    """Valida relatorio sem replay, broker ou estrategia nova."""

    def setUp(self) -> None:
        ConfigurationManager.reset_configuration()

    def test_relatorio_vazio(self) -> None:
        report = PaperTradingService().generate_report()

        self.assertIsInstance(report, PaperTradingReport)
        self.assertEqual(report.total_operations, 0)
        self.assertEqual(report.paper_win_rate, 0.0)
        self.assertEqual(report.accumulated_result_points, 0.0)
        self.assertEqual(report.max_drawdown_points, 0.0)
        self.assertEqual(report.max_loss_sequence, 0)
        self.assertIsNone(report.current_position)

    def test_consolida_total_de_operacoes(self) -> None:
        service = self._service_with_results([10.0, -5.0, 20.0])

        report = service.generate_report()

        self.assertEqual(report.total_operations, 3)

    def test_calcula_win_rate_paper(self) -> None:
        service = self._service_with_results([10.0, -5.0, 20.0, -3.0])

        report = service.generate_report()

        self.assertEqual(report.paper_win_rate, 0.5)

    def test_calcula_lucro_prejuizo_acumulado(self) -> None:
        service = self._service_with_results([10.0, -5.0, 20.0])

        report = service.generate_report()

        self.assertEqual(report.accumulated_result_points, 25.0)

    def test_calcula_maior_drawdown(self) -> None:
        service = self._service_with_results([30.0, -10.0, -15.0, 20.0])

        report = service.generate_report()

        self.assertEqual(report.max_drawdown_points, 25.0)

    def test_calcula_sequencia_maxima_de_perdas(self) -> None:
        service = self._service_with_results([10.0, -5.0, -7.0, 3.0, -1.0])

        report = service.generate_report()

        self.assertEqual(report.max_loss_sequence, 2)

    def test_expoe_posicao_atual_de_ordem_aberta(self) -> None:
        service = PaperTradingService()
        order = self._order("BUY")
        service.paper_history.append(order)

        report = service.generate_report()

        self.assertIs(report.current_position, order)

    def test_ordem_criada_pelo_servico_aparece_como_posicao_atual(self) -> None:
        service = PaperTradingService()
        service.process_signal(self._signal("BUY", 90), self._snapshot(), 1000.0)

        report = service.generate_report()

        self.assertEqual(report.total_operations, 1)
        self.assertIsInstance(report.current_position, ExecutionOrder)

    def test_status_permanece_paper_only(self) -> None:
        report = PaperTradingService().generate_report()

        self.assertEqual(report.status, "PAPER ONLY")

    def test_nao_importa_broker_mt5_replay_ou_research_lab(self) -> None:
        imports = self._imports(Path("application/paper_trading_service.py"))

        self.assertNotIn("core.broker", imports)
        self.assertNotIn("MetaTrader5", imports)
        self.assertNotIn("application.replay_service", imports)
        self.assertNotIn("research.research_lab", imports)

    def _service_with_results(self, results: list[float]) -> PaperTradingService:
        service = PaperTradingService()
        service.paper_history.extend(
            ClosedPaperTrade("BUY" if result >= 0 else "SELL", result)
            for result in results
        )
        return service

    def _order(self, side: str) -> ExecutionOrder:
        return ExecutionOrder(
            side=side,
            quantity=1,
            entry_price=1000.0,
            stop=950.0,
            target=1100.0,
        )

    def _signal(self, decision: str, score: int) -> StrategySignal:
        return StrategySignal(
            decision=decision,
            score=score,
            confidence=0.9,
            reasons=["teste paper"],
        )

    def _snapshot(self) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-26 09:30",
            regime="TREND",
            volatility=30.0,
            liquidity=1500.0,
            trend_strength=0.8,
            market_dna_score=80.0,
        )

    def _imports(self, caminho: Path) -> set[str]:
        tree = ast.parse(caminho.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
        return imports


if __name__ == "__main__":
    unittest.main()
