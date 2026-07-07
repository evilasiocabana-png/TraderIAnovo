"""Testes do comite de aprovacao da Alpha001."""

import ast
from pathlib import Path
import unittest

from domain.contracts.backtest_result import BacktestResult
from research.alpha001_robustness_analyzer import Alpha001RobustnessResult
from research.alpha001_sensitivity_analyzer import Alpha001SensitivityResult
from research.alpha_approval_committee import (
    AlphaApprovalCommittee,
    AlphaApprovalDecision,
)
from research.monte_carlo_analyzer import MonteCarloResult
from research.quantitative_research_report import QuantitativeResearchReport
from research.strategy_benchmark import StrategyBenchmarkResult
from research.walk_forward_runner import WalkForwardResult


class AlphaApprovalCommitteeTest(unittest.TestCase):
    """Garante decisao apenas por consolidacao de relatorio."""

    def test_aprova_paper_quando_relatorio_e_robusto(self):
        decision = AlphaApprovalCommittee().evaluate(self._approved_report())

        self.assertIsInstance(decision, AlphaApprovalDecision)
        self.assertTrue(decision.approved)
        self.assertEqual("PAPER", decision.stage)
        self.assertGreaterEqual(decision.confidence, 75.0)

    def test_aprova_research_quando_stress_test_esta_inconclusivo(self):
        decision = AlphaApprovalCommittee().evaluate(
            self._approved_report(stress_result=None)
        )

        self.assertTrue(decision.approved)
        self.assertEqual("RESEARCH", decision.stage)
        self.assertIn("Stress Analysis: INCONCLUSIVE.", decision.reasons)

    def test_rejeita_quando_monte_carlo_e_fragil(self):
        report = self._approved_report(
            monte_carlo_result=MonteCarloResult(
                monte_carlo_score=20.0,
                worst_drawdown=400.0,
                average_net_profit=-50.0,
                ruin_probability=0.5,
                status="FRAGILE",
            )
        )

        decision = AlphaApprovalCommittee().evaluate(report)

        self.assertFalse(decision.approved)
        self.assertEqual("REJECTED", decision.stage)
        self.assertIn("Monte Carlo fragil.", decision.reasons)

    def test_rejeita_quando_walk_forward_esta_overfitted(self):
        report = self._approved_report(
            walk_forward_result=WalkForwardResult(
                train_result={"metrics": {"net_profit_points": 500.0}},
                test_result={"metrics": {"net_profit_points": -50.0}},
                overfitting_score=90.0,
                robustness_status="OVERFITTED",
            )
        )

        decision = AlphaApprovalCommittee().evaluate(report)

        self.assertFalse(decision.approved)
        self.assertEqual("REJECTED", decision.stage)
        self.assertIn("Walk Forward rejeitado.", decision.reasons)

    def test_rejeita_quando_robustez_e_fragil(self):
        report = self._approved_report(
            robustness_result=Alpha001RobustnessResult(
                robustness_score=30.0,
                status="FRAGILE",
                reasons=["Drawdown relativo elevado."],
            )
        )

        decision = AlphaApprovalCommittee().evaluate(report)

        self.assertFalse(decision.approved)
        self.assertEqual("REJECTED", decision.stage)
        self.assertIn("Robustez fragil.", decision.reasons)

    def test_rejeita_quando_stress_test_e_rejected(self):
        decision = AlphaApprovalCommittee().evaluate(
            self._approved_report(
                stress_result={"stress_score": 20.0, "status": "REJECTED"}
            )
        )

        self.assertFalse(decision.approved)
        self.assertEqual("REJECTED", decision.stage)
        self.assertIn("Stress Test rejeitado.", decision.reasons)

    def test_ready_for_real_nunca_e_retornado(self):
        decision = AlphaApprovalCommittee().evaluate(self._approved_report())

        self.assertNotEqual("READY_FOR_REAL", decision.stage)

    def test_aceita_resultado_gerado_do_relatorio(self):
        report_result = self._approved_report().generate()

        decision = AlphaApprovalCommittee().evaluate(report_result)

        self.assertEqual("PAPER", decision.stage)

    def test_rejeita_score_geral_insuficiente(self):
        decision = AlphaApprovalCommittee().evaluate(
            QuantitativeResearchReport(
                backtest_result=BacktestResult(
                    total_profit=-100.0,
                    total_trades=2,
                    win_rate=0.1,
                    drawdown=150.0,
                    profit_factor=0.4,
                    sharpe=-1.0,
                )
            )
        )

        self.assertFalse(decision.approved)
        self.assertEqual("REJECTED", decision.stage)
        self.assertIn("Score geral insuficiente.", decision.reasons)

    def test_nao_importa_camadas_operacionais(self):
        path = Path("research/alpha_approval_committee.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = self._imported_modules(tree)

        forbidden = {"replay", "broker", "application.replay_service", "alpha"}

        self.assertTrue(forbidden.isdisjoint(imports))

    def _approved_report(self, **overrides):
        values = {
            "backtest_result": BacktestResult(500.0, 40, 0.62, 50.0, 1.8, 1.2),
            "benchmark_result": self._benchmark_result(),
            "walk_forward_result": self._walk_forward_result(),
            "robustness_result": Alpha001RobustnessResult(100.0, "ROBUST", []),
            "sensitivity_result": Alpha001SensitivityResult(
                "minimum_volume",
                1000,
                100,
                10.0,
                "LOW",
                [],
            ),
            "stress_result": {"stress_score": 90.0, "status": "APPROVED"},
            "monte_carlo_result": MonteCarloResult(
                monte_carlo_score=95.0,
                worst_drawdown=45.0,
                average_net_profit=500.0,
                ruin_probability=0.0,
                status="ROBUST",
            ),
        }
        values.update(overrides)
        return QuantitativeResearchReport(**values)

    def _benchmark_result(self):
        return StrategyBenchmarkResult(
            strategy_name="Alpha001IORBStrategy",
            total_trades=40,
            wins=25,
            losses=15,
            net_profit_points=500.0,
            win_rate=0.62,
            profit_factor=1.8,
            max_drawdown_points=50.0,
            equity_curve=[0.0, 150.0, 500.0],
        )

    def _walk_forward_result(self):
        return WalkForwardResult(
            train_result={"metrics": {"net_profit_points": 500.0}},
            test_result={"metrics": {"net_profit_points": 430.0}},
            overfitting_score=14.0,
            robustness_status="ROBUST",
        )

    def _imported_modules(self, tree):
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        return imports


if __name__ == "__main__":
    unittest.main()
