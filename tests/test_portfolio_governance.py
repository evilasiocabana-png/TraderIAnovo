"""Testes das regras oficiais de governanca do portfolio."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.portfolio.portfolio_governance import PortfolioGovernance
from tests.architecture_test_utils import calls_from, imports_from, read_source


class PortfolioGovernanceTest(unittest.TestCase):
    """Valida contrato puro de governanca do portfolio."""

    def test_governance_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(PortfolioGovernance))
        self.assertTrue(PortfolioGovernance.__dataclass_params__.frozen)

    def test_governance_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(PortfolioGovernance)],
            [
                "maximum_alphas",
                "maximum_per_family",
                "minimum_diversification",
                "maximum_correlation",
                "minimum_validation_level",
                "minimum_benchmark_score",
            ],
        )

    def test_governance_possui_type_hints_explicitos(self) -> None:
        annotations = PortfolioGovernance.__annotations__

        self.assertEqual(annotations["maximum_alphas"], "int")
        self.assertEqual(annotations["maximum_per_family"], "int")
        self.assertEqual(annotations["minimum_diversification"], "float")
        self.assertEqual(annotations["maximum_correlation"], "float")
        self.assertEqual(annotations["minimum_validation_level"], "str")
        self.assertEqual(annotations["minimum_benchmark_score"], "float")

    def test_governance_representa_regras_institucionais(self) -> None:
        governance = self._governance()

        self.assertEqual(governance.maximum_alphas, 8)
        self.assertEqual(governance.maximum_per_family, 3)
        self.assertEqual(governance.minimum_diversification, 0.4)
        self.assertEqual(governance.maximum_correlation, 0.75)
        self.assertEqual(governance.minimum_validation_level, "ROBUST")
        self.assertEqual(governance.minimum_benchmark_score, 0.7)

    def test_governance_e_imutavel(self) -> None:
        governance = self._governance()

        with self.assertRaises(FrozenInstanceError):
            governance.maximum_alphas = 10

    def test_governance_nao_executa_decisoes_ou_altera_componentes(self) -> None:
        source = read_source(Path("research/portfolio/portfolio_governance.py"))
        forbidden_fragments = (
            "def ",
            "PortfolioOptimization",
            "AlphaBenchmark",
            "BenchmarkEngine",
            "ResearchPipeline",
            "ResearchRunner",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".optimize(",
            ".compare(",
            ".calculate(",
            ".evaluate(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_governance_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/portfolio/portfolio_governance.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "research.research_pipeline",
            "research.research_runner",
            "research.portfolio.portfolio_optimization_engine",
            "research.benchmark.alpha_benchmark_engine",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "database",
            "openai",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "optimize",
            "compare",
            "calculate",
            "evaluate",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _governance(self) -> PortfolioGovernance:
        return PortfolioGovernance(
            maximum_alphas=8,
            maximum_per_family=3,
            minimum_diversification=0.4,
            maximum_correlation=0.75,
            minimum_validation_level="ROBUST",
            minimum_benchmark_score=0.7,
        )


if __name__ == "__main__":
    unittest.main()
