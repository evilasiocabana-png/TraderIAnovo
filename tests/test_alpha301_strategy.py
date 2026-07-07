"""Testes da strategy oficial da Alpha301."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from pathlib import Path
import unittest

from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from strategies.alpha301.alpha301_config import Alpha301Config
from strategies.alpha301.alpha301_strategy import Alpha301Strategy
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha301StrategyTest(unittest.TestCase):
    """Valida regras do playbook Alpha301 sem acoplamento operacional."""

    def test_strategy_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha301Strategy))
        self.assertTrue(Alpha301Strategy.__dataclass_params__.frozen)

    def test_strategy_e_imutavel(self) -> None:
        strategy = Alpha301Strategy(config=self._config())

        with self.assertRaises(FrozenInstanceError):
            strategy.nome = "outra"

    def test_retorna_long_para_instrumento_descontado(self) -> None:
        signal = Alpha301Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(spread_zscore=-1.4),
        )

        self.assertIsInstance(signal, StrategySignal)
        self.assertEqual(signal.decision, "LONG")
        self.assertEqual(signal.score, 83)
        self.assertEqual(signal.confidence, 0.83)
        self.assertIn("instrumento principal relativamente descontado", signal.reasons)

    def test_retorna_short_para_instrumento_esticado(self) -> None:
        signal = Alpha301Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(spread_zscore=1.4),
        )

        self.assertEqual(signal.decision, "SHORT")
        self.assertEqual(signal.score, 83)
        self.assertIn("instrumento principal relativamente esticado", signal.reasons)

    def test_retorna_wait_quando_gatilho_nao_confirma_spread(self) -> None:
        signal = Alpha301Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(spread_zscore=0.2),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertEqual(signal.score, 0)
        self.assertIn("gatilho Long & Short nao confirmado", signal.reasons)

    def test_retorna_wait_quando_feature_obrigatoria_esta_ausente(self) -> None:
        report = FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "spread": -2.0,
                "spread_zscore": -1.4,
                "correlation": 0.85,
                "primary_volume": 5000.0,
                "spread_volatility": 20.0,
                "data_quality_score": 0.9,
            },
            execution_time_ms=1.0,
        )

        signal = Alpha301Strategy(config=self._config()).generate_signal(
            self._context(),
            report,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("features ausentes: secondary_volume", signal.reasons)

    def test_retorna_wait_quando_contexto_viola_playbook(self) -> None:
        context = replace(
            self._context(),
            regime="BROKEN_RELATION",
            confidence=0.4,
        )

        signal = Alpha301Strategy(config=self._config()).generate_signal(
            context,
            self._feature_report(),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("regime proibido para Long & Short", signal.reasons)
        self.assertIn("confianca abaixo do minimo", signal.reasons)

    def test_retorna_wait_quando_liquidez_ou_volatilidade_invalidas(self) -> None:
        signal = Alpha301Strategy(config=self._config()).generate_signal(
            replace(self._context(), liquidity=500.0, volatility=40.0),
            self._feature_report(
                primary_volume=500.0,
                secondary_volume=500.0,
                spread_volatility=40.0,
            ),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("liquidez agregada abaixo do minimo", signal.reasons)
        self.assertIn("volatilidade do contexto acima do limite aceito", signal.reasons)
        self.assertIn("volume do instrumento principal abaixo do minimo", signal.reasons)
        self.assertIn("volume do instrumento secundario abaixo do minimo", signal.reasons)
        self.assertIn("volatilidade do spread acima do limite aceito", signal.reasons)

    def test_retorna_wait_quando_correlacao_insuficiente(self) -> None:
        signal = Alpha301Strategy(config=self._config()).generate_signal(
            self._context(),
            self._feature_report(correlation=0.2),
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("correlacao abaixo do minimo", signal.reasons)

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

        signal = Alpha301Strategy(config=self._config()).generate_signal(
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

    def test_strategy_nao_acessa_camadas_proibidas(self) -> None:
        source = read_source(Path("strategies/alpha301/alpha301_strategy.py"))
        forbidden_fragments = (
            "Alpha001",
            "Alpha002",
            "Alpha003",
            "Alpha101",
            "Alpha201",
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
        path = Path("strategies/alpha301/alpha301_strategy.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "alpha",
            "alpha.alpha001_config",
            "strategies.alpha002",
            "strategies.alpha003",
            "strategies.alpha101",
            "strategies.alpha201",
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

    def _config(self) -> Alpha301Config:
        return Alpha301Config(
            timeframe="DAILY",
            holding_period="LONG_SHORT",
            stop_points=150.0,
            target_points=300.0,
            minimum_volume=1000.0,
            minimum_volatility=30.0,
            minimum_confidence=0.7,
            risk_profile="long-short-research",
        )

    def _context(self) -> MarketContext:
        return MarketContext(
            timestamp="2026-06-27T10:00:00-03:00",
            regime="RELATIVE_VALUE",
            volatility=20.0,
            liquidity=6000.0,
            momentum=0.0,
            session="REGULAR",
            market_dna={"similarity": 80.0},
            confidence=0.83,
            metadata={
                "decision_approval_score": 0.83,
                "risk_policy_decision": "ALLOW",
                "research_validation_status": "PASSED",
                "research_confidence": 0.83,
                "reproducibility_score": 0.83,
            },
        )

    def _feature_report(
        self,
        *,
        spread: float = -2.0,
        spread_zscore: float = -1.4,
        correlation: float = 0.85,
        primary_volume: float = 5000.0,
        secondary_volume: float = 5000.0,
        spread_volatility: float = 20.0,
        data_quality_score: float = 0.9,
    ) -> FeatureReport:
        return FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "spread": spread,
                "spread_zscore": spread_zscore,
                "correlation": correlation,
                "primary_volume": primary_volume,
                "secondary_volume": secondary_volume,
                "spread_volatility": spread_volatility,
                "data_quality_score": data_quality_score,
            },
            execution_time_ms=1.0,
        )


if __name__ == "__main__":
    unittest.main()
