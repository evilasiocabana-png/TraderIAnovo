"""Testes da strategy oficial da Alpha003."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from pathlib import Path
import unittest

from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from strategies.alpha003.alpha003_config import Alpha003Config
from strategies.alpha003.alpha003_strategy import Alpha003Strategy
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha003StrategyTest(unittest.TestCase):
    """Valida regras do playbook Alpha003 sem acoplamento operacional."""

    def test_strategy_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha003Strategy))
        self.assertTrue(Alpha003Strategy.__dataclass_params__.frozen)

    def test_strategy_e_imutavel(self) -> None:
        strategy = Alpha003Strategy(config=self._config())

        with self.assertRaises(FrozenInstanceError):
            strategy.nome = "outra"

    def test_retorna_buy_para_rompimento_acima_da_opening_range(self) -> None:
        signal = Alpha003Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(
                price=5520.0,
                opening_range_high=5510.0,
                opening_range_low=5480.0,
                momentum=2.0,
            ),
        )

        self.assertIsInstance(signal, StrategySignal)
        self.assertEqual(signal.decision, "BUY")
        self.assertEqual(signal.score, 80)
        self.assertEqual(signal.confidence, 0.8)
        self.assertIn("rompimento acima da Opening Range", signal.reasons)

    def test_retorna_sell_para_rompimento_abaixo_da_opening_range(self) -> None:
        signal = Alpha003Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(
                price=5470.0,
                opening_range_high=5510.0,
                opening_range_low=5480.0,
                momentum=-2.0,
            ),
        )

        self.assertEqual(signal.decision, "SELL")
        self.assertEqual(signal.score, 80)
        self.assertIn("rompimento abaixo da Opening Range", signal.reasons)

    def test_retorna_wait_quando_gatilho_nao_confirma_rompimento(self) -> None:
        signal = Alpha003Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(
                price=5500.0,
                opening_range_high=5510.0,
                opening_range_low=5480.0,
                momentum=1.0,
            ),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertEqual(signal.score, 0)
        self.assertIn("gatilho de rompimento da Opening Range nao confirmado", signal.reasons)

    def test_retorna_wait_quando_feature_obrigatoria_esta_ausente(self) -> None:
        report = FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "price": 5520.0,
                "opening_range_high": 5510.0,
                "volume": 2000.0,
                "volatility": 25.0,
                "momentum": 2.0,
            },
            execution_time_ms=1.0,
        )

        signal = Alpha003Strategy(config=self._config()).generate_signal(
            self._context(),
            report,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("features ausentes: opening_range_low", signal.reasons)

    def test_retorna_wait_quando_contexto_viola_playbook(self) -> None:
        context = replace(
            self._context(),
            regime="LOW_LIQUIDITY",
            confidence=0.4,
        )

        signal = Alpha003Strategy(config=self._config()).generate_signal(
            context,
            self._feature_report(),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("regime proibido para Opening Range breakout", signal.reasons)
        self.assertIn("confianca abaixo do minimo", signal.reasons)

    def test_retorna_wait_quando_volume_ou_volatilidade_insuficientes(self) -> None:
        signal = Alpha003Strategy(config=self._config()).generate_signal(
            replace(self._context(), liquidity=500.0, volatility=10.0),
            self._feature_report(volume=500.0, volatility=10.0),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("liquidez abaixo do minimo", signal.reasons)
        self.assertIn("volatilidade abaixo do minimo", signal.reasons)
        self.assertIn("volume abaixo do minimo", signal.reasons)
        self.assertIn("feature de volatilidade abaixo do minimo", signal.reasons)

    def test_retorna_wait_quando_data_lab_decision_lab_ou_risk_lab_bloqueiam(self) -> None:
        context = replace(
            self._context(),
            metadata={
                "decision_approval_score": 0.3,
                "risk_policy_decision": "BLOCK_RESEARCH",
            },
        )
        report = self._feature_report(data_quality_score=0.4)

        signal = Alpha003Strategy(config=self._config()).generate_signal(
            context,
            report,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("Data Lab abaixo do minimo", signal.reasons)
        self.assertIn("Decision Lab abaixo do minimo", signal.reasons)
        self.assertIn("Risk Lab bloqueou a pesquisa", signal.reasons)

    def test_retorna_wait_fora_da_sessao_configurada(self) -> None:
        signal = Alpha003Strategy(config=self._config()).generate_signal(
            replace(self._context(), timestamp="2026-06-27T18:30:00-03:00"),
            self._feature_report(),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("fora da sessao configurada", signal.reasons)

    def test_strategy_nao_acessa_camadas_proibidas(self) -> None:
        source = read_source(Path("strategies/alpha003/alpha003_strategy.py"))
        forbidden_fragments = (
            "Alpha001",
            "Alpha002",
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
        path = Path("strategies/alpha003/alpha003_strategy.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "alpha",
            "alpha.alpha001_config",
            "strategies.alpha002",
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

    def _config(self) -> Alpha003Config:
        return Alpha003Config(
            session_start="09:00",
            session_end="18:00",
            stop_points=50.0,
            target_points=100.0,
            minimum_volume=1000.0,
            minimum_volatility=20.0,
            minimum_confidence=0.7,
            risk_profile="research-only",
        )

    def _context(self) -> MarketContext:
        return MarketContext(
            timestamp="2026-06-27T10:00:00-03:00",
            regime="TREND",
            volatility=25.0,
            liquidity=2000.0,
            momentum=1.0,
            session="REGULAR",
            market_dna={"similarity": 75.0},
            confidence=0.8,
            metadata={
                "decision_approval_score": 0.8,
                "risk_policy_decision": "ALLOW",
            },
        )

    def _feature_report(
        self,
        *,
        price: float = 5520.0,
        opening_range_high: float = 5510.0,
        opening_range_low: float = 5480.0,
        volume: float = 2000.0,
        volatility: float = 25.0,
        momentum: float = 2.0,
        data_quality_score: float = 0.9,
    ) -> FeatureReport:
        return FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "price": price,
                "opening_range_high": opening_range_high,
                "opening_range_low": opening_range_low,
                "volume": volume,
                "volatility": volatility,
                "momentum": momentum,
                "data_quality_score": data_quality_score,
            },
            execution_time_ms=1.0,
        )


if __name__ == "__main__":
    unittest.main()
