"""Testes do relatorio quantitativo consolidado Alpha001."""

import ast
from pathlib import Path
import unittest

from domain.contracts.backtest_result import BacktestResult
from research.alpha001_robustness_analyzer import Alpha001RobustnessResult
from research.alpha001_sensitivity_analyzer import Alpha001SensitivityResult
from research.monte_carlo_analyzer import MonteCarloResult
from research.quantitative_research_report import (
    QuantitativeReportSection,
    QuantitativeResearchReport,
    QuantitativeResearchReportResult,
)
from research.strategy_benchmark import StrategyBenchmarkResult
from research.walk_forward_runner import WalkForwardResult


class QuantitativeResearchReportTest(unittest.TestCase):
    """Valida consolidacao analitica sem executar novos experimentos."""

    def test_generate_retorna_resultado_com_score_status_e_recommendation(self):
        result = QuantitativeResearchReport().generate()

        self.assertIsInstance(result, QuantitativeResearchReportResult)
        self.assertEqual("NEEDS_RESEARCH", result.overall_status)
        self.assertEqual("NEED_MORE_RESEARCH", result.recommendation)
        self.assertGreaterEqual(result.overall_score, 0.0)

    def test_inclui_todas_as_secoes_obrigatorias(self):
        result = self._approved_report().generate()

        titles = [section.title for section in result.sections]

        self.assertEqual(
            [
                "Executive Summary",
                "Statistical Validation",
                "Robustness Analysis",
                "Walk Forward Analysis",
                "Monte Carlo Analysis",
                "Stress Analysis",
                "Risk Analysis",
                "Recommendation",
            ],
            titles,
        )
        self.assertTrue(
            all(
                isinstance(item, QuantitativeReportSection)
                for item in result.sections
            )
        )

    def test_recommendation_approved_for_paper_quando_resultados_robustos(self):
        result = self._approved_report().generate()

        self.assertEqual("APPROVED_FOR_PAPER", result.recommendation)
        self.assertEqual("APPROVED", result.overall_status)
        self.assertGreaterEqual(result.overall_score, 75.0)

    def test_recommendation_need_more_research_sem_dados(self):
        result = QuantitativeResearchReport().generate()

        self.assertEqual("NEED_MORE_RESEARCH", result.recommendation)
        self.assertEqual("NEEDS_RESEARCH", result.overall_status)

    def test_recommendation_rejected_com_monte_carlo_fragil(self):
        report = self._approved_report(
            monte_carlo_result=MonteCarloResult(
                monte_carlo_score=20.0,
                worst_drawdown=400.0,
                average_net_profit=-30.0,
                ruin_probability=0.5,
                status="FRAGILE",
            )
        )

        result = report.generate()

        self.assertEqual("REJECTED", result.recommendation)
        self.assertEqual("REJECTED", result.overall_status)

    def test_consolida_backtest_e_benchmark_nos_details(self):
        result = self._approved_report().generate()

        executive = self._section(result, "Executive Summary")
        statistical = self._section(result, "Statistical Validation")

        self.assertEqual(40, executive.details["total_trades"])
        self.assertEqual("Alpha001IORBStrategy", statistical.details["strategy_name"])

    def test_consolida_walk_forward_robustez_sensibilidade(self):
        result = self._approved_report().generate()

        robustness = self._section(result, "Robustness Analysis")
        walk_forward = self._section(result, "Walk Forward Analysis")

        self.assertEqual("ROBUST", robustness.details["robustness_status"])
        self.assertEqual("LOW", robustness.details["sensitivity_level"])
        self.assertEqual("ROBUST", walk_forward.details["robustness_status"])

    def test_consolida_monte_carlo_stress_e_risco(self):
        report = self._approved_report(
            stress_result={"stress_score": 80.0, "status": "APPROVED"},
        )
        result = report.generate()

        monte_carlo = self._section(result, "Monte Carlo Analysis")
        stress = self._section(result, "Stress Analysis")
        risk = self._section(result, "Risk Analysis")

        self.assertEqual("ROBUST", monte_carlo.details["status"])
        self.assertEqual("APPROVED", stress.status)
        self.assertEqual("ROBUST", risk.details["monte_carlo_status"])

    def test_nao_importa_camadas_operacionais(self):
        path = Path("research/quantitative_research_report.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = self._imported_modules(tree)

        forbidden = {"replay", "application.replay_service", "broker", "alpha"}

        self.assertTrue(forbidden.isdisjoint(imports))

    def test_rejeita_backtest_fraco_com_dado_existente(self):
        result = QuantitativeResearchReport(
            backtest_result=BacktestResult(
                total_profit=-100.0,
                total_trades=5,
                win_rate=0.2,
                drawdown=150.0,
                profit_factor=0.5,
                sharpe=-1.0,
            )
        ).generate()

        self.assertEqual("REJECTED", result.recommendation)

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

    def _section(self, result, title):
        return next(section for section in result.sections if section.title == title)

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
