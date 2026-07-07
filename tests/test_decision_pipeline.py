"""Testes do pipeline central de decisao."""

import ast
import unittest
from pathlib import Path

from core.decision_pipeline import DecisionPipeline
from domain.contracts.decision_context import DecisionContext
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal


class DecisionPipelineTest(unittest.TestCase):
    """Valida o contrato central de decisao."""

    def test_pipeline_copia_decisao_sem_alterar(self) -> None:
        """Garante que a primeira versao apenas centraliza dados."""
        signal = StrategySignal("BUY", 80, 0.8, ["sinal forte"])
        snapshot = self._snapshot()
        risk = RiskDecision(True, "Risco aprovado", 1, 1.0)

        context = DecisionPipeline().processar(signal, snapshot, risk)

        self.assertIsInstance(context, DecisionContext)
        self.assertEqual(context.final_decision, "BUY")
        self.assertEqual(context.final_confidence, 0.8)
        self.assertTrue(context.approved)

    def test_estrategias_nao_importam_risk_engine(self) -> None:
        """Garante que estrategias nao conversam diretamente com risco."""
        for caminho in Path("strategies").glob("*.py"):
            tree = ast.parse(caminho.read_text(encoding="utf-8"))
            imports = self._imports(tree)
            self.assertNotIn("risk.risk_engine", imports, str(caminho))

    def _snapshot(self) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-25 09:23",
            regime="ALTA",
            volatility=51.0,
            liquidity=1500.0,
            trend_strength=0.84,
            market_dna_score=0.0,
        )

    def _imports(self, tree: ast.AST) -> set[str]:
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
        return imports


if __name__ == "__main__":
    unittest.main()
