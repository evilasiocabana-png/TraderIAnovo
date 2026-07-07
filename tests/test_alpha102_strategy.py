"""Testes da strategy oficial da Alpha102."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from pathlib import Path
import unittest

from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from strategies.alpha102.alpha102_config import Alpha102Config
from strategies.alpha102.alpha102_strategy import Alpha102Strategy
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha102StrategyTest(unittest.TestCase):
    """Valida regras do playbook Alpha102 sem acoplamento operacional."""

    def test_strategy_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha102Strategy))
        self.assertTrue(Alpha102Strategy.__dataclass_params__.frozen)

    def test_strategy_e_imutavel(self) -> None:
        strategy = Alpha102Strategy(config=self._config())

        with self.assertRaises(FrozenInstanceError):
            strategy.nome = "outra"

    def test_retorna_buy_para_pullback_com_retomada_compradora(self) -> None:
        signal = Alpha102Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(trend_direction=1.0, momentum=2.0),
        )

        self.assertIsInstance(signal, StrategySignal)
        self.assertEqual(signal.decision, "BUY")
        self.assertEqual(signal.score, 84)
        self.assertEqual(signal.confidence, 0.84)
        self.assertIn("pullback controlado preservou a estrutura", signal.reasons)

    def test_retorna_sell_para_pullback_com_retomada_vendedora(self) -> None:
        signal = Alpha102Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(trend_direction=-1.0, momentum=-2.0),
        )

        self.assertEqual(signal.decision, "SELL")
        self.assertEqual(signal.score, 84)
        self.assertIn("momentum vendedor alinhado", signal.reasons)

    def test_retorna_wait_quando_rompimento_nao_confirma(self) -> None:
        signal = Alpha102Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(trend_direction=1.0, momentum=0.5),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertEqual(signal.score, 0)
        self.assertIn("retomada pos-pullback nao confirmada", signal.reasons)

    def test_retorna_wait_quando_feature_obrigatoria_esta_ausente(self) -> None:
        report = FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "price": 5530.0,
                "trend_direction": 1.0,
                "trend_strength": 0.8,
                "pullback_depth": 20.0,
                "structure_intact": True,
                "volume": 3500.0,
                "volatility": 35.0,
                "momentum": 2.0,
                "data_quality_score": 0.9,
            },
            execution_time_ms=1.0,
        )

        signal = Alpha102Strategy(config=self._config()).generate_signal(
            self._context(),
            report,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("features ausentes: recovery_confirmation", signal.reasons)

    def test_retorna_wait_quando_contexto_viola_playbook(self) -> None:
        context = replace(
            self._context(),
            regime="LOW_LIQUIDITY",
            confidence=0.4,
        )

        signal = Alpha102Strategy(config=self._config()).generate_signal(
            context,
            self._feature_report(),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("regime proibido para rompimento Swing Trade", signal.reasons)
        self.assertIn("confianca abaixo do minimo", signal.reasons)

    def test_retorna_wait_quando_tendencia_ou_pullback_invalidos(self) -> None:
        signal = Alpha102Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(
                trend_strength=0.2,
                pullback_depth=100.0,
                structure_intact=False,
            ),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("forca de tendencia abaixo do minimo", signal.reasons)
        self.assertIn("pullback acima da profundidade maxima", signal.reasons)
        self.assertIn("estrutura principal do pullback violada", signal.reasons)

    def test_retorna_wait_quando_volume_ou_volatilidade_insuficientes(self) -> None:
        signal = Alpha102Strategy(config=self._config()).generate_signal(
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
            },
        )
        report = self._feature_report(data_quality_score=0.4)

        signal = Alpha102Strategy(config=self._config()).generate_signal(
            context,
            report,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("Data Lab abaixo do minimo", signal.reasons)
        self.assertIn("Decision Lab abaixo do minimo", signal.reasons)
        self.assertIn("Risk Lab bloqueou a pesquisa", signal.reasons)
        self.assertIn("Research Lab rejeitou o cenario", signal.reasons)
        self.assertIn("Research Lab abaixo do minimo", signal.reasons)

    def test_strategy_nao_acessa_camadas_proibidas(self) -> None:
        source = read_source(Path("strategies/alpha102/alpha102_strategy.py"))
        forbidden_fragments = (
            "Alpha001",
            "Alpha002",
            "Alpha003",
            "Alpha101",
            "Alpha201",
            "Alpha301",
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
        path = Path("strategies/alpha102/alpha102_strategy.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "alpha",
            "alpha.alpha001_config",
            "strategies.alpha002",
            "strategies.alpha003",
            "strategies.alpha101",
            "strategies.alpha201",
            "strategies.alpha301",
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

    def _config(self) -> Alpha102Config:
        return Alpha102Config(
            timeframe="120M",
            holding_period="2-7_SESSIONS",
            stop_points=140.0,
            target_points=280.0,
            minimum_volume=1000.0,
            minimum_volatility=20.0,
            minimum_confidence=0.7,
            risk_profile="swing-pullback-research",
            trend_lookback_periods=20,
            minimum_trend_strength=0.6,
            minimum_pullback_depth=8.0,
            maximum_pullback_depth=80.0,
            momentum_confirmation_threshold=1.5,
        )

    def _context(self) -> MarketContext:
        return MarketContext(
            timestamp="2026-06-28T10:00:00-03:00",
            regime="TREND",
            volatility=35.0,
            liquidity=3500.0,
            momentum=2.0,
            session="REGULAR",
            market_dna={"similarity": 80.0},
            confidence=0.84,
            metadata={
                "decision_approval_score": 0.84,
                "risk_policy_decision": "ALLOW",
                "research_validation_status": "PASSED",
                "research_confidence": 0.84,
            },
        )

    def _feature_report(
        self,
        *,
        price: float = 5530.0,
        trend_direction: float = 1.0,
        trend_strength: float = 0.8,
        pullback_depth: float = 20.0,
        structure_intact: bool = True,
        recovery_confirmation: float | None = None,
        volume: float = 3500.0,
        volatility: float = 35.0,
        momentum: float = 2.0,
        data_quality_score: float = 0.9,
    ) -> FeatureReport:
        if recovery_confirmation is None:
            recovery_confirmation = momentum
        return FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "price": price,
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                "pullback_depth": pullback_depth,
                "structure_intact": structure_intact,
                "recovery_confirmation": recovery_confirmation,
                "volume": volume,
                "volatility": volatility,
                "momentum": momentum,
                "data_quality_score": data_quality_score,
            },
            execution_time_ms=1.0,
        )


if __name__ == "__main__":
    unittest.main()
