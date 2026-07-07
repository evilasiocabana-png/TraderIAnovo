"""Testes do relatorio oficial de benchmark entre Alphas."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.benchmark.alpha_benchmark_engine import (
    AlphaBenchmarkComparison,
    AlphaBenchmarkResult,
)
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.benchmark.alpha_benchmark_report import AlphaBenchmarkReport
from research.benchmark.alpha_dominance_engine import (
    AlphaDominanceResult,
)
from research.benchmark.alpha_similarity_engine import AlphaSimilarityResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaBenchmarkReportTest(unittest.TestCase):
    """Valida agregador puro de benchmark entre Alphas."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaBenchmarkReport))
        self.assertTrue(AlphaBenchmarkReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(AlphaBenchmarkReport)],
            [
                "benchmark_result",
                "dominance",
                "similarity",
                "alpha_a",
                "alpha_b",
                "benchmark_summary",
                "dominance_result",
                "similarity_score",
                "diversification_score",
                "recommendation",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = AlphaBenchmarkReport.__annotations__

        self.assertEqual(annotations["benchmark_result"], "AlphaBenchmarkResult")
        self.assertEqual(annotations["dominance"], "AlphaDominanceResult")
        self.assertEqual(annotations["similarity"], "AlphaSimilarityResult")
        self.assertEqual(annotations["alpha_a"], "str")
        self.assertEqual(annotations["alpha_b"], "str")
        self.assertEqual(annotations["benchmark_summary"], "str")
        self.assertEqual(annotations["dominance_result"], "str")
        self.assertEqual(annotations["similarity_score"], "float")
        self.assertEqual(annotations["diversification_score"], "float")
        self.assertEqual(annotations["recommendation"], "str")
        self.assertEqual(annotations["execution_time"], "float")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_report_agrega_resultados_anteriores(self) -> None:
        benchmark = self._benchmark_result()
        dominance = self._dominance()
        similarity = self._similarity()

        report = AlphaBenchmarkReport(
            benchmark_result=benchmark,
            dominance=dominance,
            similarity=similarity,
            alpha_a="Alpha001",
            alpha_b="Alpha301",
            benchmark_summary="Alpha301 diversifica Alpha001.",
            dominance_result=dominance.decision,
            similarity_score=similarity.similarity_score,
            diversification_score=similarity.diversification_score,
            recommendation="KEEP_BOTH_FOR_RESEARCH",
            execution_time=1.5,
            metadata={"source": "unit-test"},
        )

        self.assertIs(report.benchmark_result, benchmark)
        self.assertIs(report.dominance, dominance)
        self.assertIs(report.similarity, similarity)
        self.assertEqual(report.alpha_a, "Alpha001")
        self.assertEqual(report.alpha_b, "Alpha301")
        self.assertEqual(report.dominance_result, "ALPHA_B_DOMINATES")
        self.assertEqual(report.similarity_score, 0.4)
        self.assertEqual(report.diversification_score, 0.6)
        self.assertEqual(report.recommendation, "KEEP_BOTH_FOR_RESEARCH")
        self.assertEqual(report.execution_time, 1.5)
        self.assertEqual(report.metadata["source"], "unit-test")

    def test_report_e_imutavel(self) -> None:
        report = AlphaBenchmarkReport(
            benchmark_result=self._benchmark_result(),
            dominance=self._dominance(),
            similarity=self._similarity(),
            alpha_a="Alpha001",
            alpha_b="Alpha301",
            benchmark_summary="Resumo.",
            dominance_result="TIE",
            similarity_score=0.5,
            diversification_score=0.5,
            recommendation="KEEP_BOTH_FOR_RESEARCH",
            execution_time=1.0,
            metadata={},
        )

        with self.assertRaises(FrozenInstanceError):
            report.recommendation = "CHANGE"

    def test_report_nao_realiza_calculos_ou_exportacao(self) -> None:
        source = read_source(Path("research/benchmark/alpha_benchmark_report.py"))
        forbidden_fragments = (
            "def ",
            "sum(",
            "max(",
            "min(",
            "round(",
            "Dashboard",
            "streamlit",
            "HTML",
            "PDF",
            "open(",
            "write",
            "json",
            "csv",
            "export",
            "database",
            ".calculate(",
            ".run(",
            ".compare(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/benchmark/alpha_benchmark_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.portfolio",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "database",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "calculate",
            "compare",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _benchmark_result(self) -> AlphaBenchmarkResult:
        comparison = AlphaBenchmarkComparison(
            alpha_id="Alpha301",
            experiment_id="exp-301",
            net_profit=80.0,
            max_drawdown=7.0,
            profit_factor=1.8,
            win_rate=0.6,
            expectancy=3.0,
            robustness=0.9,
            reproducibility=0.8,
        )
        return AlphaBenchmarkResult(
            profile=self._profile(),
            total_results=1,
            comparisons=(comparison,),
            best_net_profit=comparison,
            best_max_drawdown=comparison,
            best_profit_factor=comparison,
            best_win_rate=comparison,
            best_expectancy=comparison,
            best_robustness=comparison,
            best_reproducibility=comparison,
        )

    def _profile(self) -> AlphaBenchmarkProfile:
        return AlphaBenchmarkProfile(
            benchmark_id="benchmark-alpha001-alpha301",
            alpha_a="Alpha001",
            alpha_b="Alpha301",
            experiment_ids=("exp-001", "exp-301"),
            campaign_ids=("campaign-001", "campaign-301"),
            comparison_period="2026-01",
            metrics=("net_profit", "max_drawdown"),
            created_at="2026-06-28T05:25:00-03:00",
            metadata={},
        )

    def _dominance(self) -> AlphaDominanceResult:
        return AlphaDominanceResult(
            benchmark_id="benchmark-alpha001-alpha301",
            alpha_a="Alpha001",
            alpha_b="Alpha301",
            decision="ALPHA_B_DOMINATES",
            alpha_a_score=1,
            alpha_b_score=2,
            compared_metrics=("net_profit", "max_drawdown"),
        )

    def _similarity(self) -> AlphaSimilarityResult:
        return AlphaSimilarityResult(
            similarity_score=0.4,
            overlap_score=0.2,
            diversification_score=0.6,
        )


if __name__ == "__main__":
    unittest.main()
