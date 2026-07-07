"""Testes da strategy oficial da Alpha201."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from pathlib import Path
import unittest

from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from strategies.alpha201.alpha201_config import Alpha201Config
from strategies.alpha201.alpha201_strategy import Alpha201Strategy
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha201StrategyTest(unittest.TestCase):
    """Valida regras do playbook Alpha201 sem acoplamento operacional."""

    def test_strategy_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha201Strategy))
        self.assertTrue(Alpha201Strategy.__dataclass_params__.frozen)

    def test_strategy_e_imutavel(self) -> None:
        strategy = Alpha201Strategy(config=self._config())

        with self.assertRaises(FrozenInstanceError):
            strategy.nome = "outra"

    def test_retorna_buy_para_tendencia_estrutural_de_alta(self) -> None:
        signal = Alpha201Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(
                structural_trend="UP",
                directional_persistence=0.75,
                momentum=3.0,
            ),
        )

        self.assertIsInstance(signal, StrategySignal)
        self.assertEqual(signal.decision, "BUY")
        self.assertEqual(signal.score, 84)
        self.assertEqual(signal.confidence, 0.84)
        self.assertIn("tendencia estrutural de alta qualificada", signal.reasons)

    def test_retorna_sell_para_tendencia_estrutural_de_baixa(self) -> None:
        signal = Alpha201Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(
                structural_trend="DOWN",
                directional_persistence=-0.75,
                momentum=-3.0,
            ),
        )

        self.assertEqual(signal.decision, "SELL")
        self.assertEqual(signal.score, 84)
        self.assertIn("tendencia estrutural de baixa qualificada", signal.reasons)

    def test_retorna_wait_quando_gatilho_nao_confirma_tendencia(self) -> None:
        signal = Alpha201Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(
                structural_trend="UP",
                directional_persistence=0.75,
                momentum=-3.0,
            ),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertEqual(signal.score, 0)
        self.assertIn(
            "gatilho de tendencia Position Trade nao confirmado",
            signal.reasons,
        )

    def test_retorna_wait_quando_feature_obrigatoria_esta_ausente(self) -> None:
        report = FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "price": 5520.0,
                "structural_trend": "UP",
                "volume": 6000.0,
                "volatility": 50.0,
                "momentum": 3.0,
                "data_quality_score": 0.9,
            },
            execution_time_ms=1.0,
        )

        signal = Alpha201Strategy(config=self._config()).generate_signal(
            self._context(),
            report,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("features ausentes: directional_persistence", signal.reasons)

    def test_retorna_wait_quando_contexto_viola_playbook(self) -> None:
        context = replace(
            self._context(),
            regime="RANGE",
            confidence=0.4,
        )

        signal = Alpha201Strategy(config=self._config()).generate_signal(
            context,
            self._feature_report(),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("regime proibido para Position Trade", signal.reasons)
        self.assertIn("confianca abaixo do minimo", signal.reasons)

    def test_retorna_wait_quando_volume_ou_volatilidade_insuficientes(self) -> None:
        signal = Alpha201Strategy(config=self._config()).generate_signal(
            replace(self._context(), liquidity=500.0, volatility=10.0),
            self._feature_report(volume=500.0, volatility=10.0),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("liquidez abaixo do minimo", signal.reasons)
        self.assertIn("volatilidade abaixo do minimo", signal.reasons)
        self.assertIn("volume abaixo do minimo", signal.reasons)
        self.assertIn("feature de volatilidade abaixo do minimo", signal.reasons)

    def test_retorna_wait_quando_labs_bloqueiam_cenario(self) -> None:
        context = replace(
            self._context(),
            metadata={
                "decision_approval_score": 0.3,
                "risk_policy_decision": "BLOCK_RESEARCH",
                "research_validation_status": "REJECTED",
                "research_confidence": 0.4,
                "reproducibility_score": 0.2,
            },
        )
        report = self._feature_report(data_quality_score=0.4)

        signal = Alpha201Strategy(config=self._config()).generate_signal(
            context,
            report,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("Data Lab abaixo do minimo", signal.reasons)
        self.assertIn("Decision Lab abaixo do minimo", signal.reasons)
        self.assertIn("Risk Lab bloqueou a pesquisa", signal.reasons)
        self.assertIn("Research Lab rejeitou o cenario", signal.reasons)
        self.assertIn("Research Lab abaixo do minimo", signal.reasons)
        self.assertIn("reprodutibilidade abaixo do minimo", signal.reasons)

    def test_retorna_wait_quando_tendencia_nao_esta_qualificada(self) -> None:
        signal = Alpha201Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(structural_trend="SIDEWAYS"),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("tendencia estrutural nao qualificada", signal.reasons)

    def test_strategy_nao_acessa_camadas_proibidas(self) -> None:
        source = read_source(Path("strategies/alpha201/alpha201_strategy.py"))
        forbidden_fragments = (
            "Alpha001",
            "Alpha002",
            "Alpha003",
            "Alpha101",
            "RiskEngine",
            "DecisionPipeline",
            "ResearchPipeline",
            "Dashboard",
            "streamlit",
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
            ".next_candle(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_strategy_permanece_desacoplada_de_operacao(self) -> None:
        path = Path("strategies/alpha201/alpha201_strategy.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "alpha",
            "alpha.alpha001_config",
            "strategies.alpha002",
            "strategies.alpha003",
            "strategies.alpha101",
            "replay",
            "application.replay_service",
            "risk.risk_engine",
            "core.decision_pipeline",
            "research.research_pipeline",
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
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _config(self) -> Alpha201Config:
        return Alpha201Config(
            timeframe="WEEKLY",
            holding_period="POSITION",
            stop_points=300.0,
            target_points=600.0,
            minimum_volume=1000.0,
            minimum_volatility=20.0,
            minimum_confidence=0.7,
            risk_profile="position-research",
        )

    def _context(self) -> MarketContext:
        return MarketContext(
            timestamp="2026-06-27T10:00:00-03:00",
            regime="TREND",
            volatility=50.0,
            liquidity=6000.0,
            momentum=3.0,
            session="REGULAR",
            market_dna={"similarity": 80.0},
            confidence=0.84,
            metadata={
                "decision_approval_score": 0.84,
                "risk_policy_decision": "ALLOW",
                "research_validation_status": "PASSED",
                "research_confidence": 0.84,
                "reproducibility_score": 0.84,
            },
        )

    def _feature_report(
        self,
        *,
        price: float = 5520.0,
        structural_trend: str = "UP",
        directional_persistence: float = 0.75,
        volume: float = 6000.0,
        volatility: float = 50.0,
        momentum: float = 3.0,
        data_quality_score: float = 0.9,
    ) -> FeatureReport:
        return FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "price": price,
                "structural_trend": structural_trend,
                "directional_persistence": directional_persistence,
                "volume": volume,
                "volatility": volatility,
                "momentum": momentum,
                "data_quality_score": data_quality_score,
            },
            execution_time_ms=1.0,
        )


if __name__ == "__main__":
    unittest.main()
