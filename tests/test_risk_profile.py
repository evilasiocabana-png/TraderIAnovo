"""Testes do contrato de perfil de risco."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from risk.risk_profile import RiskProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class RiskProfileTest(unittest.TestCase):
    """Valida politica parametrizada sem avaliacao operacional."""

    def test_profile_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(RiskProfile))
        self.assertTrue(RiskProfile.__dataclass_params__.frozen)

    def test_profile_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(RiskProfile)]

        self.assertEqual(
            field_names,
            [
                "capital",
                "max_exposure",
                "risk_per_trade",
                "daily_risk_limit",
                "max_daily_loss",
                "max_daily_gain",
                "max_drawdown_allowed",
                "contracts",
                "enabled",
                "metadata",
            ],
        )

    def test_profile_possui_type_hints_explicitos(self) -> None:
        annotations = RiskProfile.__annotations__

        self.assertEqual(annotations["capital"], "float")
        self.assertEqual(annotations["max_exposure"], "float")
        self.assertEqual(annotations["risk_per_trade"], "float")
        self.assertEqual(annotations["daily_risk_limit"], "float")
        self.assertEqual(annotations["max_daily_loss"], "float")
        self.assertEqual(annotations["max_daily_gain"], "float")
        self.assertEqual(annotations["max_drawdown_allowed"], "float")
        self.assertEqual(annotations["contracts"], "int")
        self.assertEqual(annotations["enabled"], "bool")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_profile_representa_politica_parametrizada(self) -> None:
        profile = self._profile()

        self.assertEqual(profile.capital, 100000.0)
        self.assertEqual(profile.max_exposure, 0.3)
        self.assertEqual(profile.risk_per_trade, 0.01)
        self.assertEqual(profile.daily_risk_limit, 0.03)
        self.assertEqual(profile.max_daily_loss, 3000.0)
        self.assertEqual(profile.max_daily_gain, 5000.0)
        self.assertEqual(profile.max_drawdown_allowed, 0.1)
        self.assertEqual(profile.contracts, 2)
        self.assertTrue(profile.enabled)
        self.assertEqual(profile.metadata["source"], "test")

    def test_profile_preserva_metadata_recebido(self) -> None:
        metadata = {"source": "test"}

        profile = RiskProfile(
            capital=100000.0,
            max_exposure=0.3,
            risk_per_trade=0.01,
            daily_risk_limit=0.03,
            max_daily_loss=3000.0,
            max_daily_gain=5000.0,
            max_drawdown_allowed=0.1,
            contracts=2,
            enabled=True,
            metadata=metadata,
        )

        self.assertIs(profile.metadata, metadata)

    def test_profile_e_imutavel(self) -> None:
        profile = self._profile()

        with self.assertRaises(FrozenInstanceError):
            profile.enabled = False

    def test_profile_nao_calcula_risco_ou_aprova_ordens(self) -> None:
        source = read_source(Path("risk/risk_profile.py"))
        forbidden_fragments = (
            "def ",
            "avaliar",
            "registrar_resultado",
            "RiskEngine",
            "StrategySignal",
            "Alpha",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            "send_order",
            "approved =",
            "allowed =",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_profile_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("risk/risk_profile.py")
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
            metadata={"source": "test"},
        )


if __name__ == "__main__":
    unittest.main()
