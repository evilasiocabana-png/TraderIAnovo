"""Protecao dos DTOs publicos do dominio."""

import dataclasses
import importlib
from pathlib import Path
import unittest

from domain.contracts import (
    BacktestResult,
    DecisionContext,
    ExecutionOrder,
    ExecutionResult,
    MarketSnapshot,
    RiskDecision,
    StrategySignal,
)
from tests.architecture_test_utils import imports_from, read_source


class DomainContractsTest(unittest.TestCase):
    """Congela contratos centrais usados entre camadas."""

    CONTRACTS = {
        "StrategySignal": StrategySignal,
        "MarketSnapshot": MarketSnapshot,
        "RiskDecision": RiskDecision,
        "DecisionContext": DecisionContext,
        "ExecutionOrder": ExecutionOrder,
        "ExecutionResult": ExecutionResult,
        "BacktestResult": BacktestResult,
    }
    REQUIRED_FIELDS = {
        "StrategySignal": {"decision", "score", "confidence", "reasons"},
        "MarketSnapshot": {
            "symbol",
            "datetime",
            "regime",
            "volatility",
            "liquidity",
            "trend_strength",
            "market_dna_score",
        },
        "RiskDecision": {
            "allowed",
            "reason",
            "max_contracts",
            "risk_multiplier",
        },
        "ExecutionOrder": {"side", "quantity", "entry_price", "stop", "target"},
        "ExecutionResult": {
            "accepted",
            "status",
            "message",
            "ticket",
            "executed_price",
            "error_code",
        },
        "BacktestResult": {
            "total_profit",
            "total_trades",
            "win_rate",
            "drawdown",
            "profit_factor",
            "sharpe",
        },
        "DecisionContext": {
            "strategy_signal",
            "market_snapshot",
            "risk_decision",
            "final_decision",
            "final_confidence",
            "approved",
        },
    }

    def test_imports_dos_contratos_nao_quebram(self) -> None:
        modules = [
            "domain.contracts.strategy_signal",
            "domain.contracts.market_snapshot",
            "domain.contracts.risk_decision",
            "domain.contracts.decision_context",
            "domain.contracts.execution_order",
            "domain.contracts.execution_result",
            "domain.contracts.backtest_result",
            "domain.contracts",
        ]

        for module in modules:
            with self.subTest(module=module):
                self.assertIsNotNone(importlib.import_module(module))

    def test_contratos_sao_dataclasses(self) -> None:
        for name, contract in self.CONTRACTS.items():
            with self.subTest(contract=name):
                self.assertTrue(dataclasses.is_dataclass(contract))

    def test_campos_obrigatorios_estao_presentes(self) -> None:
        for name, contract in self.CONTRACTS.items():
            with self.subTest(contract=name):
                field_names = {field.name for field in dataclasses.fields(contract)}
                self.assertTrue(
                    self.REQUIRED_FIELDS[name].issubset(field_names),
                    f"{name} perdeu campos: "
                    f"{sorted(self.REQUIRED_FIELDS[name] - field_names)}",
                )

    def test_campos_criticos_possuem_type_hints(self) -> None:
        for name, contract in self.CONTRACTS.items():
            annotations = getattr(contract, "__annotations__", {})
            for field_name in self.REQUIRED_FIELDS[name]:
                with self.subTest(contract=name, field=field_name):
                    self.assertIn(field_name, annotations)

    def test_contratos_do_dominio_nao_importam_infraestrutura(self) -> None:
        forbidden_imports = {
            "application",
            "dashboard_app",
            "streamlit",
            "database",
            "pandas",
            "duckdb",
            "pathlib",
            "broker",
            "mt5",
            "MetaTrader5",
            "adapters",
            "providers",
            "market_data",
        }
        forbidden_text = ("open(", "Path(", "read_csv", "read_parquet")

        for path in Path("domain/contracts").glob("*.py"):
            if path.name == "__pycache__":
                continue
            with self.subTest(path=str(path)):
                imports = self._imports(path)
                self.assertEqual(
                    self._matches(imports, forbidden_imports),
                    set(),
                    f"{path} importou infraestrutura proibida",
                )
                source = read_source(path)
                leaked = [term for term in forbidden_text if term in source]
                self.assertEqual(leaked, [], f"{path} acessou infraestrutura")

    def test_strategy_signal_aceita_buy_sell_wait(self) -> None:
        for decision in ("BUY", "SELL", "WAIT"):
            with self.subTest(decision=decision):
                signal = StrategySignal(
                    decision=decision,
                    score=80,
                    confidence=0.8,
                    reasons=["contrato valido"],
                )
                self.assertEqual(signal.decision, decision)
                self.assertEqual(signal.reasons, ["contrato valido"])

    def test_risk_decision_representa_permitido_e_bloqueado(self) -> None:
        allowed = RiskDecision(True, "Risco aprovado", 2, 1.0)
        blocked = RiskDecision(False, "Risco bloqueado", 0, 0.0)

        self.assertTrue(allowed.allowed)
        self.assertFalse(blocked.allowed)
        self.assertEqual(allowed.max_contracts, 2)
        self.assertEqual(blocked.risk_multiplier, 0.0)

    def test_decision_context_combina_sinal_snapshot_e_risco(self) -> None:
        signal = self._strategy_signal("BUY")
        snapshot = self._market_snapshot()
        risk = RiskDecision(True, "Risco aprovado", 1, 1.0)

        context = DecisionContext(
            strategy_signal=signal,
            market_snapshot=snapshot,
            risk_decision=risk,
            final_decision="BUY",
            final_confidence=0.8,
            approved=True,
        )

        self.assertEqual(context.strategy_signal, signal)
        self.assertEqual(context.market_snapshot, snapshot)
        self.assertEqual(context.risk_decision, risk)
        self.assertTrue(context.approved)

    def test_execution_order_aceita_dados_minimos_validos(self) -> None:
        order = ExecutionOrder(
            side="BUY",
            quantity=0.1,
            entry_price=5522.0,
            stop=5472.0,
            target=5622.0,
        )

        self.assertEqual(order.side, "BUY")
        self.assertEqual(order.quantity, 0.1)
        self.assertEqual(order.entry_price, 5522.0)
        self.assertEqual(order.symbol, "UNKNOWN")

    def test_execution_result_representa_aceite_e_rejeicao(self) -> None:
        accepted = ExecutionResult(True, "ACCEPTED", "Aceita", ticket=123)
        rejected = ExecutionResult(False, "REJECTED", "Bloqueada", error_code=1)

        self.assertTrue(accepted.accepted)
        self.assertEqual(accepted.ticket, 123)
        self.assertFalse(rejected.accepted)
        self.assertEqual(rejected.error_code, 1)

    def test_backtest_result_aceita_metricas_numericas_basicas(self) -> None:
        result = BacktestResult(
            total_profit=250.0,
            total_trades=10,
            win_rate=0.6,
            drawdown=25.0,
            profit_factor=1.5,
            sharpe=1.1,
        )

        self.assertEqual(result.total_trades, 10)
        self.assertEqual(result.win_rate, 0.6)
        self.assertEqual(result.profit_factor, 1.5)

    def _strategy_signal(self, decision: str) -> StrategySignal:
        return StrategySignal(
            decision=decision,
            score=80,
            confidence=0.8,
            reasons=["contrato valido"],
        )

    def _market_snapshot(self) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-26 09:00",
            regime="TREND",
            volatility=1.2,
            liquidity=0.9,
            trend_strength=0.7,
            market_dna_score=75.0,
        )

    def _imports(self, path: Path) -> set[str]:
        return imports_from(path)

    def _matches(self, imports: set[str], forbidden: set[str]) -> set[str]:
        matches: set[str] = set()
        for imported in imports:
            root = imported.split(".", maxsplit=1)[0]
            if imported in forbidden or root in forbidden:
                matches.add(imported)
        return matches


if __name__ == "__main__":
    unittest.main()
