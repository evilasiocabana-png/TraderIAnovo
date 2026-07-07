"""Testes do ranking consolidado de pesquisa por Alpha."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha_factory.alpha_research_ranking import (
    AlphaResearchRankingEngine,
    AlphaResearchRankingReport,
    AlphaResearchScenario,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaResearchRankingTest(unittest.TestCase):
    """Protege rankings e reprovas sem executar pesquisa real."""

    def test_contratos_sao_dataclasses_imutaveis(self) -> None:
        self.assertTrue(is_dataclass(AlphaResearchScenario))
        self.assertTrue(AlphaResearchScenario.__dataclass_params__.frozen)
        self.assertTrue(is_dataclass(AlphaResearchRankingReport))
        self.assertTrue(AlphaResearchRankingReport.__dataclass_params__.frozen)

    def test_gera_ranking_por_alpha_par_timeframe_e_comparacao(self) -> None:
        report = AlphaResearchRankingEngine().build(self._scenarios())

        self.assertEqual(report.ranking_by_alpha["Alpha001"][0].scenario_id, "s1")
        self.assertEqual(report.ranking_by_market["EURUSD"][0].scenario_id, "s1")
        self.assertEqual(report.ranking_by_timeframe["M15"][0].scenario_id, "s1")
        self.assertEqual(report.alpha_comparison[0].alpha_id, "Alpha001")
        self.assertEqual(report.alpha_comparison[1].alpha_id, "Alpha002")

    def test_relatorio_de_reprovacao_preserva_motivo(self) -> None:
        report = AlphaResearchRankingEngine().build(self._scenarios())

        self.assertEqual(len(report.rejection_reports), 1)
        rejection = report.rejection_reports[0]
        self.assertEqual(rejection.scenario_id, "s3")
        self.assertEqual(rejection.reason, "Profit factor baixo.")
        self.assertEqual(rejection.alpha_id, "Alpha003")

    def test_controle_de_overfitting_classifica_e_bloqueia_alto_risco(self) -> None:
        report = AlphaResearchRankingEngine(
            overfitting_block_threshold=70.0,
            overfitting_warning_threshold=40.0,
        ).build(self._scenarios())

        by_scenario = {
            control.scenario_id: control
            for control in report.overfitting_controls
        }
        self.assertEqual(by_scenario["s1"].risk_level, "LOW")
        self.assertEqual(by_scenario["s2"].risk_level, "WARNING")
        self.assertEqual(by_scenario["s3"].risk_level, "HIGH")
        self.assertFalse(by_scenario["s1"].blocked)
        self.assertTrue(by_scenario["s3"].blocked)

    def test_ranking_e_imutavel(self) -> None:
        report = AlphaResearchRankingEngine().build(self._scenarios())

        with self.assertRaises(FrozenInstanceError):
            report.alpha_comparison[0].status = "REJECTED"

    def test_engine_nao_executa_pesquisa_replay_dashboard_ou_ordens(self) -> None:
        source = read_source(Path("research/alpha_factory/alpha_research_ranking.py"))
        forbidden_fragments = (
            "ResearchLab",
            "Replay",
            "dashboard",
            "streamlit",
            "MetaTrader5",
            "order_send",
            ".run(",
            ".calculate(",
            "generate_signal",
            "open(",
            "Path(",
            "pandas",
        )

        leaked = [
            fragment
            for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]
        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_research_ranking.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
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

    def _scenarios(self) -> tuple[AlphaResearchScenario, ...]:
        return (
            AlphaResearchScenario(
                scenario_id="s1",
                alpha_id="Alpha001",
                market="EURUSD",
                timeframe="M15",
                technical_score=89.0,
                historical_confirmation=64.0,
                total_trades=120,
                profit_factor=1.8,
                max_drawdown=4.0,
                overfitting_score=12.0,
                status="APPROVED",
            ),
            AlphaResearchScenario(
                scenario_id="s2",
                alpha_id="Alpha002",
                market="EURUSD",
                timeframe="H1",
                technical_score=80.0,
                historical_confirmation=60.0,
                total_trades=80,
                profit_factor=1.5,
                max_drawdown=5.0,
                overfitting_score=45.0,
                status="APPROVED",
            ),
            AlphaResearchScenario(
                scenario_id="s3",
                alpha_id="Alpha003",
                market="GBPUSD",
                timeframe="M15",
                technical_score=77.0,
                historical_confirmation=39.0,
                total_trades=20,
                profit_factor=0.8,
                max_drawdown=9.0,
                overfitting_score=82.0,
                status="REJECTED",
                rejection_reason="Profit factor baixo.",
            ),
        )


if __name__ == "__main__":
    unittest.main()
