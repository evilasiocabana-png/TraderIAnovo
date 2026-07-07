"""Testes da integracao Dashboard Research Alpha001."""

import ast
import unittest
from pathlib import Path

from application.dashboard_service import DashboardData, DashboardService
from application.research_lab_service import (
    Alpha001DashboardBenchmarkData,
    Alpha001DashboardResearchData,
)


class DashboardResearchAlpha001Test(unittest.TestCase):
    """Valida exposicao de metricas de research via DashboardService."""

    def test_research_lab_service_expoe_metricas_alpha001_para_dashboard(self) -> None:
        service = DashboardService()
        service.run_demo_alpha001_experiment()

        data = service.get_dashboard_data()

        self.assertIsInstance(data, DashboardData)
        self.assertIsInstance(
            data.alpha001_dashboard_research,
            Alpha001DashboardResearchData,
        )

    def test_metricas_alpha001_contem_campos_esperados(self) -> None:
        service = DashboardService()
        service.run_demo_alpha001_experiment()

        metrics = service.get_dashboard_data().alpha001_dashboard_research

        self.assertGreaterEqual(metrics.total_trades, 0)
        self.assertGreaterEqual(metrics.total_buy, 0)
        self.assertGreaterEqual(metrics.total_sell, 0)
        self.assertGreaterEqual(metrics.total_wait, 0)
        self.assertIsInstance(metrics.net_profit, float)
        self.assertIsInstance(metrics.gross_profit, float)
        self.assertIsInstance(metrics.gross_loss, float)
        self.assertIsInstance(metrics.max_drawdown, float)
        self.assertIsInstance(metrics.drawdown, float)
        self.assertIsInstance(metrics.win_rate, float)
        self.assertIsInstance(metrics.profit_factor, float)
        self.assertIsInstance(metrics.expectancy, float)
        self.assertIn(
            metrics.recommendation,
            {
                "APPROVED_FOR_MORE_RESEARCH",
                "REJECTED",
                "INSUFFICIENT_SAMPLE",
            },
        )
        self.assertIsInstance(metrics.equity_curve, list)
        self.assertIsInstance(metrics.benchmark, Alpha001DashboardBenchmarkData)

    def test_metricas_alpha001_expoem_benchmark_entre_experimentos(self) -> None:
        service = DashboardService()
        service.run_demo_alpha001_experiment()
        service.run_demo_alpha001_experiment()

        benchmark = service.get_dashboard_data().alpha001_dashboard_research.benchmark

        self.assertEqual(benchmark.total_results, 2)
        self.assertIsNotNone(benchmark.best_overall)
        self.assertIsNotNone(benchmark.best_total_trades)
        self.assertIsNotNone(benchmark.best_net_profit)
        self.assertIsNotNone(benchmark.best_max_drawdown)
        self.assertIsNotNone(benchmark.best_profit_factor)
        self.assertIsNotNone(benchmark.best_win_rate)
        self.assertIsNotNone(benchmark.best_expectancy)
        self.assertEqual(len(benchmark.ranking), 2)

    def test_dashboard_app_renderiza_metricas_sem_importar_research(self) -> None:
        source = Path("dashboard_app.py").read_text(encoding="utf-8")
        imports = self._imports(Path("dashboard_app.py"))

        self.assertIn("exibir_research_lab_data", source)
        self.assertIn("Nenhum experimento executado.", source)
        self.assertNotIn("data.alpha001_dashboard_research", source)
        for label in (
            "Calibracao Forex MT5",
            "Melhor constante/modelo",
            "Heuristica recomendada",
            "Atualizar historico de pesquisa (5000 candles)",
            "Laboratorio de Pesquisa Forex",
        ):
            with self.subTest(label=label):
                self.assertIn(label, source)
        for legacy_label in (
            "Comparar Benchmarks",
            "Validar Benchmarks",
        ):
            with self.subTest(legacy_label=legacy_label):
                self.assertNotIn(legacy_label, source)
        self.assertIn("application.dashboard_service", imports)
        self.assertNotIn("research", imports)
        self.assertNotIn("application.research_lab_service", imports)

    def test_dashboard_nao_instancia_engines_de_research(self) -> None:
        tree = ast.parse(Path("dashboard_app.py").read_text(encoding="utf-8"))
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        }
        forbidden_fragments = (
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
            "Alpha001DrawdownEngine",
            "Alpha001WinRateEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001ExpectancyEngine",
            "DecisionPipeline",
            "ReplayEngine",
        )

        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, calls)

    def _imports(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
        return imports


if __name__ == "__main__":
    unittest.main()
