"""Testes do paper trading controlado da Alpha001."""

import ast
import unittest
from pathlib import Path

from application.paper_trading_service import (
    PaperTradingResult,
    PaperTradingService,
)
from core.configuration_manager import ConfigurationManager
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.strategy_signal import StrategySignal
from risk.risk_engine import RiskEngine
from strategies.alpha001_iorb_strategy import Alpha001IORBStrategy


class Alpha001PaperTradingTest(unittest.TestCase):
    """Valida paper trading sem corretora e sem ordem real."""

    def setUp(self) -> None:
        ConfigurationManager.reset_configuration()

    def test_usa_alpha001_strategy_registrada(self) -> None:
        """Servico deve obter Alpha001 pela StrategyFactory."""
        strategy = PaperTradingService().alpha001_strategy()

        self.assertIsInstance(strategy, Alpha001IORBStrategy)
        self.assertEqual(strategy.nome, "alpha001_iorb")

    def test_buy_aprovado_cria_ordem_paper(self) -> None:
        """Sinal BUY aprovado deve criar apenas ExecutionOrder paper."""
        result = PaperTradingService().process_signal(
            self._signal("BUY", score=90),
            self._snapshot(),
            entry_price=1000.0,
        )

        self.assertIsInstance(result.order, ExecutionOrder)
        self.assertEqual(result.order.side, "BUY")
        self.assertEqual(result.order.entry_price, 1000.0)

    def test_sell_aprovado_cria_ordem_paper(self) -> None:
        """Sinal SELL aprovado deve criar ordem paper de venda."""
        result = PaperTradingService().process_signal(
            self._signal("SELL", score=90),
            self._snapshot(),
            entry_price=1000.0,
        )

        self.assertIsInstance(result.order, ExecutionOrder)
        self.assertEqual(result.order.side, "SELL")

    def test_wait_nao_cria_ordem(self) -> None:
        """WAIT deve passar pelo risco e nao virar ordem."""
        result = PaperTradingService().process_signal(
            self._signal("WAIT", score=90),
            self._snapshot(),
            entry_price=1000.0,
        )

        self.assertIsNone(result.order)
        self.assertFalse(result.decision_context.approved)

    def test_passa_pelo_decision_pipeline(self) -> None:
        """Resultado deve conter DecisionContext oficial."""
        signal = self._signal("BUY", score=90)

        result = PaperTradingService().process_signal(
            signal,
            self._snapshot(),
            entry_price=1000.0,
        )

        self.assertEqual(result.decision_context.strategy_signal, signal)
        self.assertEqual(result.decision_context.final_decision, "BUY")
        self.assertTrue(result.decision_context.approved)

    def test_passa_pelo_risk_engine(self) -> None:
        """Score abaixo do minimo deve ser bloqueado pelo RiskEngine."""
        result = PaperTradingService().process_signal(
            self._signal("BUY", score=10),
            self._snapshot(),
            entry_price=1000.0,
        )

        self.assertFalse(result.risk_decision.allowed)
        self.assertIsNone(result.order)
        self.assertEqual(result.risk_decision.reason, "Sinal sem score minimo")

    def test_limite_de_operacoes_bloqueia_ordem_paper(self) -> None:
        """RiskEngine deve impedir nova ordem quando limite foi atingido."""
        service = PaperTradingService(
            risk_engine=RiskEngine(
                perda_maxima_dia=-300.0,
                limite_operacoes=0,
                score_minimo=70,
            ),
        )

        result = service.process_signal(
            self._signal("BUY", score=90),
            self._snapshot(),
            entry_price=1000.0,
        )

        self.assertFalse(result.risk_decision.allowed)
        self.assertIsNone(result.order)
        self.assertEqual(result.risk_decision.reason, "Limite de operacoes atingido")

    def test_stop_e_target_buy_usam_configuracao(self) -> None:
        """BUY deve calcular stop e target por configuracao central."""
        result = PaperTradingService().process_signal(
            self._signal("BUY", score=90),
            self._snapshot(),
            entry_price=1000.0,
        )

        self.assertEqual(result.order.stop, 950.0)
        self.assertEqual(result.order.target, 1100.0)

    def test_stop_e_target_sell_usam_configuracao(self) -> None:
        """SELL deve calcular stop e target por configuracao central."""
        result = PaperTradingService().process_signal(
            self._signal("SELL", score=90),
            self._snapshot(),
            entry_price=1000.0,
        )

        self.assertEqual(result.order.stop, 1050.0)
        self.assertEqual(result.order.target, 900.0)

    def test_registra_historico_paper(self) -> None:
        """Ordens paper devem ficar em memoria."""
        service = PaperTradingService()

        service.process_signal(self._signal("BUY", score=90), self._snapshot(), 1000.0)

        self.assertEqual(len(service.list_paper_history()), 1)
        self.assertEqual(service.list_paper_history()[0].side, "BUY")

    def test_clear_history_limpa_historico(self) -> None:
        """Historico paper deve poder ser limpo."""
        service = PaperTradingService()
        service.process_signal(self._signal("BUY", score=90), self._snapshot(), 1000.0)

        service.clear_history()

        self.assertEqual(service.list_paper_history(), [])

    def test_resultado_informa_operacao_real_nao_autorizada(self) -> None:
        """Servico deve deixar claro que nao ha ordem real."""
        result = PaperTradingService().process_signal(
            self._signal("BUY", score=90),
            self._snapshot(),
            entry_price=1000.0,
        )

        self.assertIsInstance(result, PaperTradingResult)
        self.assertFalse(result.real_trading_authorized)
        self.assertFalse(result.broker_integrated)
        self.assertFalse(result.mt5_integrated)
        self.assertIn("Nenhuma ordem real", result.message)

    def test_servico_nao_importa_broker_ou_mt5(self) -> None:
        """Paper service nao deve depender de corretora real."""
        imports = self._imports(Path("application/paper_trading_service.py"))

        self.assertNotIn("core.broker", imports)
        self.assertNotIn("MetaTrader5", imports)

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
