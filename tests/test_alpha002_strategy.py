"""Testes da strategy oficial da Alpha002."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from pathlib import Path
import unittest

from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from strategies.alpha002.alpha002_config import Alpha002Config
from strategies.alpha002.alpha002_strategy import Alpha002Strategy
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha002StrategyTest(unittest.TestCase):
    """Valida regras do playbook Alpha002 sem acoplamento operacional."""

    def test_strategy_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha002Strategy))
        self.assertTrue(Alpha002Strategy.__dataclass_params__.frozen)

    def test_strategy_e_imutavel(self) -> None:
        strategy = Alpha002Strategy(config=self._config())

        with self.assertRaises(FrozenInstanceError):
            strategy.nome = "outra"

    def test_retorna_buy_para_reversao_abaixo_da_vwap(self) -> None:
        signal = Alpha002Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(
                price=5480.0,
                vwap=5500.0,
                vwap_distance_percent=-0.36,
                momentum=1.0,
            ),
        )

        self.assertIsInstance(signal, StrategySignal)
        self.assertEqual(signal.decision, "BUY")
        self.assertEqual(signal.score, 80)
        self.assertEqual(signal.confidence, 0.8)
        self.assertIn("preco abaixo da VWAP", signal.reasons)

    def test_retorna_sell_para_reversao_acima_da_vwap(self) -> None:
        signal = Alpha002Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(
                price=5520.0,
                vwap=5500.0,
                vwap_distance_percent=0.36,
                momentum=-1.0,
            ),
        )

        self.assertEqual(signal.decision, "SELL")
        self.assertEqual(signal.score, 80)
        self.assertIn("preco acima da VWAP", signal.reasons)

    def test_retorna_wait_quando_gatilho_nao_confirma_reversao(self) -> None:
        signal = Alpha002Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(
                price=5480.0,
                vwap=5500.0,
                vwap_distance_percent=-0.36,
                momentum=-3.0,
            ),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertEqual(signal.score, 0)
        self.assertIn("gatilho de reversao VWAP nao confirmado", signal.reasons)

    def test_retorna_wait_quando_feature_obrigatoria_esta_ausente(self) -> None:
        report = FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "price": 5480.0,
                "vwap_distance_percent": -0.36,
                "volume": 2000.0,
                "volatility": 25.0,
                "momentum": 1.0,
            },
            execution_time_ms=1.0,
        )

        signal = Alpha002Strategy(config=self._config()).generate_signal(
            self._context(),
            report,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("features ausentes: vwap", signal.reasons)

    def test_retorna_wait_quando_contexto_viola_playbook(self) -> None:
        context = replace(
            self._context(),
            regime="STRONG_TREND",
            confidence=0.4,
        )

        signal = Alpha002Strategy(config=self._config()).generate_signal(
            context,
            self._feature_report(),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("regime proibido para reversao VWAP", signal.reasons)
        self.assertIn("confianca abaixo do minimo", signal.reasons)

    def test_retorna_wait_quando_volume_ou_volatilidade_insuficientes(self) -> None:
        signal = Alpha002Strategy(config=self._config()).generate_signal(
            replace(self._context(), liquidity=500.0, volatility=10.0),
            self._feature_report(volume=500.0, volatility=10.0),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("liquidez abaixo do minimo", signal.reasons)
        self.assertIn("volatilidade abaixo do minimo", signal.reasons)
        self.assertIn("volume abaixo do minimo", signal.reasons)
        self.assertIn("feature de volatilidade abaixo do minimo", signal.reasons)

    def test_retorna_wait_fora_da_sessao_configurada(self) -> None:
        signal = Alpha002Strategy(config=self._config()).generate_signal(
            replace(self._context(), timestamp="2026-06-27T18:30:00-03:00"),
            self._feature_report(),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("fora da sessao configurada", signal.reasons)

    def test_strategy_nao_acessa_camadas_proibidas(self) -> None:
        source = read_source(Path("strategies/alpha002/alpha002_strategy.py"))
        forbidden_fragments = (
            "Alpha001",
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
        path = Path("strategies/alpha002/alpha002_strategy.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "alpha",
            "alpha.alpha001_config",
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

    def _config(self) -> Alpha002Config:
        return Alpha002Config(
            opening_range=15,
            stop_points=50.0,
            target_points=100.0,
            minimum_volume=1000.0,
            minimum_volatility=20.0,
            minimum_confidence=0.7,
            session_start="09:00",
            session_end="18:00",
        )

    def _context(self) -> MarketContext:
        return MarketContext(
            timestamp="2026-06-27T10:00:00-03:00",
            regime="RANGE",
            volatility=25.0,
            liquidity=2000.0,
            momentum=1.0,
            session="REGULAR",
            market_dna={"similarity": 75.0},
            confidence=0.8,
            metadata={},
        )

    def _feature_report(
        self,
        *,
        price: float = 5480.0,
        vwap: float = 5500.0,
        vwap_distance_percent: float = -0.36,
        volume: float = 2000.0,
        volatility: float = 25.0,
        momentum: float = 1.0,
    ) -> FeatureReport:
        return FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "price": price,
                "vwap": vwap,
                "vwap_distance_percent": vwap_distance_percent,
                "volume": volume,
                "volatility": volatility,
                "momentum": momentum,
            },
            execution_time_ms=1.0,
        )


if __name__ == "__main__":
    unittest.main()
