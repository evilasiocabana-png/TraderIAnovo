"""Testes do relatorio oficial do Risk Lab."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from risk.risk_policy_engine import RiskPolicyResult
from risk.risk_profile import RiskProfile
from risk.risk_report import RiskReport
from risk.risk_score_engine import RiskScoreResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class RiskReportTest(unittest.TestCase):
    """Valida consolidacao sem calculo ou saida operacional."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(RiskReport))
        self.assertTrue(RiskReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(RiskReport)]

        self.assertEqual(
            field_names,
            [
                "profile",
                "score_result",
                "policy_result",
                "capital",
                "max_exposure",
                "final_risk_score",
                "policy_decision",
                "exposure_score",
                "drawdown_score",
                "volatility_score",
                "research_score",
                "execution_time",
                "metadata",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = RiskReport.__annotations__

        self.assertEqual(annotations["profile"], "RiskProfile")
        self.assertEqual(annotations["score_result"], "RiskScoreResult")
        self.assertEqual(annotations["policy_result"], "RiskPolicyResult")
        self.assertEqual(annotations["capital"], "float")
        self.assertEqual(annotations["max_exposure"], "float")
        self.assertEqual(annotations["final_risk_score"], "float")
        self.assertEqual(annotations["policy_decision"], "str")
        self.assertEqual(annotations["exposure_score"], "float")
        self.assertEqual(annotations["drawdown_score"], "float")
        self.assertEqual(annotations["volatility_score"], "float")
        self.assertEqual(annotations["research_score"], "float")
        self.assertEqual(annotations["execution_time"], "float")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.profile, RiskProfile)
        self.assertIsInstance(report.score_result, RiskScoreResult)
        self.assertIsInstance(report.policy_result, RiskPolicyResult)
        self.assertEqual(report.capital, 100000.0)
        self.assertEqual(report.max_exposure, 0.3)
        self.assertEqual(report.final_risk_score, 80.0)
        self.assertEqual(report.policy_decision, "ALLOW")
        self.assertEqual(report.exposure_score, 80.0)
        self.assertEqual(report.drawdown_score, 75.0)
        self.assertEqual(report.volatility_score, 85.0)
        self.assertEqual(report.research_score, 80.0)
        self.assertEqual(report.execution_time, 8.5)
        self.assertEqual(report.metadata["source"], "test")

    def test_report_preserva_referencias_recebidas(self) -> None:
        profile = self._profile()
        score_result = self._score_result()
        policy_result = self._policy_result()
        metadata = {"source": "test"}

        report = RiskReport(
            profile=profile,
            score_result=score_result,
            policy_result=policy_result,
            capital=100000.0,
            max_exposure=0.3,
            final_risk_score=80.0,
            policy_decision="ALLOW",
            exposure_score=80.0,
            drawdown_score=75.0,
            volatility_score=85.0,
            research_score=80.0,
            execution_time=8.5,
            metadata=metadata,
        )

        self.assertIs(report.profile, profile)
        self.assertIs(report.score_result, score_result)
        self.assertIs(report.policy_result, policy_result)
        self.assertIs(report.metadata, metadata)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.policy_decision = "BLOCK_PAPER"

    def test_report_nao_calcula_persiste_ou_envia_ordens(self) -> None:
        source = read_source(Path("risk/risk_report.py"))
        forbidden_fragments = (
            "def ",
            "sum(",
            "min(",
            "max(",
            "round(",
            "RiskEngine",
            "RiskDecision",
            "StrategySignal",
            "Dashboard",
            "HTML",
            "PDF",
            "open(",
            "write(",
            "persist",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            "send_order",
            "open_position",
            "close_position",
            ".avaliar(",
            ".processar(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("risk/risk_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "risk.risk_engine",
            "domain",
            "core.decision_pipeline",
            "replay",
            "application.replay_service",
            "alpha",
            "strategies",
            "broker",
            "mt5",
            "MetaTrader5",
            "paper",
            "database",
            "dashboard_app",
            "streamlit",
        }
        forbidden_calls = {
            "open",
            "avaliar",
            "processar",
            "execute",
            "run",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _profile(self) -> RiskProfile:
        return RiskProfile(
            capital=100000.0,
            max_exposure=0.3,
            risk_per_trade=0.01,
            daily_risk_limit=0.03,
            max_daily_loss=3000.0,
            max_daily_gain=5000.0,
            max_drawdown_allowed=0.1,
            contracts=2,
            enabled=True,
            metadata={"source": "profile"},
        )

    def _score_result(self) -> RiskScoreResult:
        return RiskScoreResult(
            exposure_score=80.0,
            drawdown_score=75.0,
            volatility_score=85.0,
            research_score=80.0,
            final_risk_score=80.0,
        )

    def _policy_result(self) -> RiskPolicyResult:
        return RiskPolicyResult(
            decision="ALLOW",
            reason="Politica quantitativa dentro dos limites definidos.",
            final_risk_score=80.0,
        )

    def _report(self) -> RiskReport:
        return RiskReport(
            profile=self._profile(),
            score_result=self._score_result(),
            policy_result=self._policy_result(),
            capital=100000.0,
            max_exposure=0.3,
            final_risk_score=80.0,
            policy_decision="ALLOW",
            exposure_score=80.0,
            drawdown_score=75.0,
            volatility_score=85.0,
            research_score=80.0,
            execution_time=8.5,
            metadata={"source": "test"},
        )


if __name__ == "__main__":
    unittest.main()
