"""Testes do pipeline oficial do Context Lab."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from market.context.context_pipeline import ContextPipeline
from market.context.context_quality_engine import ContextQualityResult
from market.context.market_context import MarketContext
from market.feature_engine import FeatureSnapshot
from market.regime_engine import MarketRegime, RegimeAnalysis
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ContextPipelineTest(unittest.TestCase):
    """Valida orquestracao do Context Lab sem duplicar logica."""

    def test_pipeline_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ContextPipeline))
        self.assertTrue(ContextPipeline.__dataclass_params__.frozen)

    def test_execute_retorna_market_context(self) -> None:
        context = ContextPipeline().execute(
            timestamp="2026-06-27T09:00:00-03:00",
            feature_snapshot=self._feature_snapshot(),
            regime_analysis=self._regime_analysis(),
            market_dna={"similarity": 82},
            liquidity=1500.0,
            session="OPENING",
            metadata={"source": "test"},
        )

        self.assertIsInstance(context, MarketContext)
        self.assertEqual(context.regime, "TREND")
        self.assertEqual(context.momentum, 10.0)
        self.assertEqual(context.volatility, 15.0)
        self.assertEqual(context.confidence, 0.7)

    def test_execute_orquestra_builder_antes_quality_engine(self) -> None:
        calls: list[str] = []
        pipeline = ContextPipeline(
            context_builder=_SpyContextBuilder(calls),
            quality_engine=_SpyQualityEngine(calls),
        )

        context = pipeline.execute(
            timestamp="2026-06-27T09:00:00-03:00",
            feature_snapshot=self._feature_snapshot(),
            regime_analysis=self._regime_analysis(),
            market_dna={"similarity": 82},
            liquidity=1500.0,
            session="OPENING",
            metadata={"source": "test"},
        )

        self.assertEqual(calls, ["build", "evaluate"])
        self.assertEqual(context.regime, "TREND")

    def test_execute_inclui_contextos_anteriores_na_avaliacao(self) -> None:
        calls: list[str] = []
        quality_engine = _CapturingQualityEngine(calls)
        pipeline = ContextPipeline(
            context_builder=_SpyContextBuilder(calls),
            quality_engine=quality_engine,
        )
        previous = (self._market_context("RANGE"),)

        pipeline.execute(
            timestamp="2026-06-27T09:00:00-03:00",
            feature_snapshot=self._feature_snapshot(),
            regime_analysis=self._regime_analysis(),
            market_dna={},
            liquidity=1500.0,
            session="OPENING",
            metadata={},
            previous_contexts=previous,
        )

        self.assertEqual(len(quality_engine.contexts), 2)
        self.assertIs(quality_engine.contexts[0], previous[0])
        self.assertEqual(quality_engine.contexts[1].regime, "TREND")

    def test_pipeline_e_imutavel(self) -> None:
        pipeline = ContextPipeline()

        with self.assertRaises(FrozenInstanceError):
            pipeline.quality_engine = _SpyQualityEngine([])

    def test_pipeline_nao_chama_engines_de_mercado_diretamente(self) -> None:
        source = read_source(Path("market/context/context_pipeline.py"))
        forbidden_fragments = (
            "FeatureEngine",
            "RegimeEngine",
            "MarketDNA",
            ".analyze(",
            ".criar_pattern(",
            ".comparar(",
            ".salvar(",
            ".carregar(",
            ".taxa_lucro(",
            "CandleHistory",
            "MarketState",
            "MarketSnapshot",
            "generate_signal",
            "next_candle",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_pipeline_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/context/context_pipeline.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "market.feature_engine",
            "market.regime_engine",
            "market.market_dna",
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

    def _market_context(self, regime: str) -> MarketContext:
        return MarketContext(
            timestamp="2026-06-27T08:59:00-03:00",
            regime=regime,
            volatility=10.0,
            liquidity=900.0,
            momentum=1.0,
            session="PRE_OPEN",
            market_dna={},
            confidence=0.6,
            metadata={},
        )


class _SpyContextBuilder:
    """Builder de teste que registra chamada."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def build(
        self,
        timestamp: str,
        feature_snapshot: FeatureSnapshot,
        regime_analysis: RegimeAnalysis,
        market_dna: dict[str, object],
        liquidity: float,
        session: str,
        metadata: dict[str, object],
    ) -> MarketContext:
        self.calls.append("build")
        return MarketContext(
            timestamp=timestamp,
            regime=regime_analysis.regime.value,
            volatility=feature_snapshot.average_range,
            liquidity=liquidity,
            momentum=feature_snapshot.momentum,
            session=session,
            market_dna=market_dna,
            confidence=regime_analysis.confidence,
            metadata=metadata,
        )


class _SpyQualityEngine:
    """Quality engine de teste que registra chamada."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def evaluate(
        self,
        contexts: tuple[MarketContext, ...],
    ) -> ContextQualityResult:
        self.calls.append("evaluate")
        return ContextQualityResult(
            total_contexts=len(contexts),
            confidence_score=100.0,
            consistency_score=100.0,
            quality_score=100.0,
        )


class _CapturingQualityEngine(_SpyQualityEngine):
    """Quality engine de teste que captura contextos avaliados."""

    contexts: tuple[MarketContext, ...]

    def evaluate(
        self,
        contexts: tuple[MarketContext, ...],
    ) -> ContextQualityResult:
        self.contexts = contexts
        return super().evaluate(contexts)


if __name__ == "__main__":
    unittest.main()
