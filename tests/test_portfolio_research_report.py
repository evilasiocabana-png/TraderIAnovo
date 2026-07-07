"""Testes do relatorio consolidado do Portfolio Research."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.portfolio.alpha_correlation_engine import AlphaCorrelationResult
from research.portfolio.alpha_registry import AlphaRegistry
from research.portfolio.alpha_research_profile import AlphaResearchProfile
from research.portfolio.portfolio_research_comparator import (
    PortfolioComparisonResult,
    PortfolioResearchComparison,
)
from research.portfolio.portfolio_research_report import PortfolioResearchReport
from tests.architecture_test_utils import calls_from, imports_from, read_source


class PortfolioResearchReportTest(unittest.TestCase):
    """Valida agregacao pura dos componentes de portfolio."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(PortfolioResearchReport))
        self.assertTrue(PortfolioResearchReport.__dataclass_params__.frozen)

    def test_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.alpha_registry, AlphaRegistry)
        self.assertIsInstance(report.alpha_profiles[0], AlphaResearchProfile)
        self.assertIsInstance(report.comparison_result, PortfolioComparisonResult)
        self.assertIsInstance(report.correlation_result, AlphaCorrelationResult)

    def test_preserva_referencias_recebidas_sem_recalcular(self) -> None:
        registry = AlphaRegistry()
        profiles = (self._profile(),)
        comparison = self._comparison()
        correlation = self._correlation()

        report = PortfolioResearchReport(
            alpha_registry=registry,
            alpha_profiles=profiles,
            comparison_result=comparison,
            correlation_result=correlation,
        )

        self.assertIs(report.alpha_registry, registry)
        self.assertIs(report.alpha_profiles, profiles)
        self.assertIs(report.comparison_result, comparison)
        self.assertIs(report.correlation_result, correlation)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.alpha_profiles = ()

    def test_report_nao_realiza_calculos_ou_execucoes(self) -> None:
        source = read_source(
            Path("research/portfolio/portfolio_research_report.py")
        )
        forbidden_fragments = (
            ".run(",
            ".calculate(",
            ".compare(",
            ".validate(",
            ".recommend(",
            "sum(",
            "max(",
            "min(",
            " / ",
            " * ",
            " + ",
            " - ",
            "AlphaCorrelationEngine",
            "PortfolioResearchComparator",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_nao_gera_dashboard_html_pdf_ou_persistencia(self) -> None:
        source = read_source(
            Path("research/portfolio/portfolio_research_report.py")
        )
        forbidden_fragments = (
            "dashboard",
            "streamlit",
            "html",
            "pdf",
            "open(",
            "write",
            "json",
            "csv",
            "export",
            "database",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/portfolio/portfolio_research_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "alpha.alpha001_config",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "generate_signal",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> PortfolioResearchReport:
        return PortfolioResearchReport(
            alpha_registry=AlphaRegistry(),
            alpha_profiles=(self._profile(),),
            comparison_result=self._comparison(),
            correlation_result=self._correlation(),
        )

    def _profile(self) -> AlphaResearchProfile:
        return AlphaResearchProfile(
            alpha_id="Alpha001",
            alpha_name="Alpha 001 IORB",
            version=1,
            description="Perfil oficial de pesquisa.",
            market="WDO",
            timeframe="1m",
            status="ACTIVE",
            current_stage="RESEARCH",
            validation_level="STATISTICAL",
            configuration_version=1,
        )

    def _comparison(self) -> PortfolioComparisonResult:
        return PortfolioComparisonResult(
            total_results=1,
            comparisons=(
                PortfolioResearchComparison(
                    alpha_id="Alpha001",
                    total_trades=10,
                    net_profit=100.0,
                    max_drawdown=5.0,
                    profit_factor=2.0,
                    expectancy=4.0,
                    win_rate=0.6,
                ),
            ),
        )

    def _correlation(self) -> AlphaCorrelationResult:
        return AlphaCorrelationResult(
            alpha_ids=("Alpha001",),
            correlation_matrix=((1.0,),),
            average_correlation=0.0,
            highest_correlation=0.0,
            lowest_correlation=0.0,
        )


if __name__ == "__main__":
    unittest.main()
