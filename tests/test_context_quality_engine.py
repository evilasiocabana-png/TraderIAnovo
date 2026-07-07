"""Testes do avaliador de qualidade de contextos."""

from dataclasses import FrozenInstanceError, is_dataclass, replace
from math import inf, nan
from pathlib import Path
import unittest

from market.context.context_quality_engine import (
    ContextQualityEngine,
    ContextQualityResult,
)
from market.context.market_context import MarketContext
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ContextQualityEngineTest(unittest.TestCase):
    """Valida scores de qualidade sobre MarketContext."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ContextQualityResult))
        self.assertTrue(ContextQualityResult.__dataclass_params__.frozen)

    def test_engine_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ContextQualityEngine))
        self.assertTrue(ContextQualityEngine.__dataclass_params__.frozen)

    def test_avalia_contextos_com_score_perfeito(self) -> None:
        contexts = (
            self._context(confidence=1.0),
            self._context(confidence=1.0),
        )

        result = ContextQualityEngine().evaluate(contexts)

        self.assertEqual(result.total_contexts, 2)
        self.assertEqual(result.confidence_score, 100.0)
        self.assertEqual(result.consistency_score, 100.0)
        self.assertEqual(result.quality_score, 100.0)

    def test_calcula_confidence_score_medio(self) -> None:
        contexts = (
            self._context(confidence=0.8),
            self._context(confidence=0.6),
        )

        result = ContextQualityEngine().evaluate(contexts)

        self.assertEqual(result.confidence_score, 70.0)
        self.assertEqual(result.consistency_score, 100.0)
        self.assertEqual(result.quality_score, 85.0)

    def test_calcula_consistency_score_com_contexto_inconsistente(self) -> None:
        contexts = (
            self._context(confidence=0.8),
            replace(self._context(confidence=0.8), regime=""),
        )

        result = ContextQualityEngine().evaluate(contexts)

        self.assertEqual(result.total_contexts, 2)
        self.assertEqual(result.confidence_score, 80.0)
        self.assertEqual(result.consistency_score, 50.0)
        self.assertEqual(result.quality_score, 65.0)

    def test_retorna_zero_para_colecao_vazia(self) -> None:
        result = ContextQualityEngine().evaluate(())

        self.assertEqual(result.total_contexts, 0)
        self.assertEqual(result.confidence_score, 0.0)
        self.assertEqual(result.consistency_score, 0.0)
        self.assertEqual(result.quality_score, 0.0)

    def test_confidence_score_limita_valores_invalidos(self) -> None:
        contexts = (
            self._context(confidence=-0.5),
            self._context(confidence=1.5),
            self._context(confidence=nan),
        )

        result = ContextQualityEngine().evaluate(contexts)

        self.assertEqual(result.confidence_score, 33.33)

    def test_detecta_numeros_inconsistentes(self) -> None:
        contexts = (
            replace(self._context(), volatility=inf),
            replace(self._context(), liquidity=-1.0),
        )

        result = ContextQualityEngine().evaluate(contexts)

        self.assertEqual(result.consistency_score, 0.0)

    def test_nao_modifica_contextos_recebidos(self) -> None:
        context = replace(self._context(), confidence=1.5)

        ContextQualityEngine().evaluate((context,))

        self.assertEqual(context.confidence, 1.5)

    def test_resultado_e_imutavel(self) -> None:
        result = ContextQualityEngine().evaluate(())

        with self.assertRaises(FrozenInstanceError):
            result.quality_score = 100.0

    def test_engine_nao_recalcula_contexto_ou_acessa_alpha(self) -> None:
        source = read_source(Path("market/context/context_quality_engine.py"))
        forbidden_fragments = (
            "MarketContextBuilder",
            "FeatureEngine",
            "RegimeEngine",
            "MarketDNA",
            "Alpha001",
            "ReplayEngine",
            "ResearchPipeline",
            "DecisionPipeline",
            "Broker",
            "MT5",
            ".build(",
            ".analyze(",
            ".criar_pattern(",
            ".comparar(",
            "generate_signal",
            "next_candle",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/context/context_quality_engine.py")
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
            "build",
            "analyze",
            "criar_pattern",
            "comparar",
            "calculate",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _context(self, confidence: float = 0.8) -> MarketContext:
        return MarketContext(
            timestamp="2026-06-27T09:00:00-03:00",
            regime="TREND",
            volatility=22.5,
            liquidity=1500.0,
            momentum=8.0,
            session="OPENING",
            market_dna={"similarity": 82},
            confidence=confidence,
            metadata={"source": "fixture"},
        )


if __name__ == "__main__":
    unittest.main()
