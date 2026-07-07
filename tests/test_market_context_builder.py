"""Testes do builder de contexto de mercado."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from market.context.market_context import MarketContext
from market.context.market_context_builder import MarketContextBuilder
from market.feature_engine import FeatureSnapshot
from market.regime_engine import MarketRegime, RegimeAnalysis
from tests.architecture_test_utils import calls_from, imports_from, read_source


class MarketContextBuilderTest(unittest.TestCase):
    """Valida consolidacao de contexto sem recalculo de componentes."""

    def test_builder_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MarketContextBuilder))
        self.assertTrue(MarketContextBuilder.__dataclass_params__.frozen)

    def test_build_retorna_market_context(self) -> None:
        context = self._context()

        self.assertIsInstance(context, MarketContext)
        self.assertEqual(context.timestamp, "2026-06-27T09:00:00-03:00")
        self.assertEqual(context.regime, "TREND")
        self.assertEqual(context.volatility, 15.0)
        self.assertEqual(context.liquidity, 1500.0)
        self.assertEqual(context.momentum, 10.0)
        self.assertEqual(context.session, "OPENING")
        self.assertEqual(context.market_dna["similarity"], 82)
        self.assertEqual(context.confidence, 0.7)
        self.assertEqual(context.metadata["source"], "test")

    def test_build_reutiliza_resultados_recebidos(self) -> None:
        feature_snapshot = self._feature_snapshot()
        regime_analysis = self._regime_analysis()
        market_dna = {"similarity": 82}
        metadata = {"source": "test"}

        context = MarketContextBuilder().build(
            timestamp="2026-06-27T09:00:00-03:00",
            feature_snapshot=feature_snapshot,
            regime_analysis=regime_analysis,
            market_dna=market_dna,
            liquidity=1500.0,
            session="OPENING",
            metadata=metadata,
        )

        self.assertIs(context.market_dna, market_dna)
        self.assertIs(context.metadata, metadata)
        self.assertEqual(context.volatility, feature_snapshot.average_range)
        self.assertEqual(context.momentum, feature_snapshot.momentum)
        self.assertEqual(context.regime, regime_analysis.regime.value)
        self.assertEqual(context.confidence, regime_analysis.confidence)

    def test_build_aceita_regime_alternativo_ja_classificado(self) -> None:
        context = MarketContextBuilder().build(
            timestamp="2026-06-27T09:00:00-03:00",
            feature_snapshot=self._feature_snapshot(),
            regime_analysis=RegimeAnalysis(
                regime=MarketRegime.RANGE,
                confidence=0.65,
                description="Lateral.",
            ),
            market_dna={},
            liquidity=900.0,
            session="MIDDAY",
            metadata={},
        )

        self.assertEqual(context.regime, "RANGE")
        self.assertEqual(context.confidence, 0.65)

    def test_builder_e_imutavel(self) -> None:
        builder = MarketContextBuilder()

        with self.assertRaises(FrozenInstanceError):
            builder.anything = "value"

    def test_builder_nao_recalcula_features_regime_ou_market_dna(self) -> None:
        source = read_source(Path("market/context/market_context_builder.py"))
        forbidden_fragments = (
            ".analyze(",
            ".build(",
            ".criar_pattern(",
            ".comparar(",
            ".salvar(",
            ".carregar(",
            ".taxa_lucro(",
            "FeatureEngine(",
            "RegimeEngine(",
            "MarketDNA(",
            "CandleHistory",
            "MarketState",
            "MarketSnapshot(",
            "sum(",
            "max(",
            "min(",
            "round(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_builder_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/context/market_context_builder.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "alpha",
            "strategies",
            "research.research_pipeline",
            "core.decision_pipeline",
            "DecisionPipeline",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "open",
            "analyze",
            "criar_pattern",
            "comparar",
            "salvar",
            "carregar",
            "calculate",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _context(self) -> MarketContext:
        return MarketContextBuilder().build(
            timestamp="2026-06-27T09:00:00-03:00",
            feature_snapshot=self._feature_snapshot(),
            regime_analysis=self._regime_analysis(),
            market_dna={"similarity": 82},
            liquidity=1500.0,
            session="OPENING",
            metadata={"source": "test"},
        )

    def _feature_snapshot(self) -> FeatureSnapshot:
        return FeatureSnapshot(
            momentum=10.0,
            average_range=15.0,
            highest_high=120.0,
            lowest_low=95.0,
            direction="UP",
            candles_count=3,
            trend_strength=0.66,
            volatility_level="MEDIUM",
        )

    def _regime_analysis(self) -> RegimeAnalysis:
        return RegimeAnalysis(
            regime=MarketRegime.TREND,
            confidence=0.7,
            description="Mercado direcional.",
        )


if __name__ == "__main__":
    unittest.main()
