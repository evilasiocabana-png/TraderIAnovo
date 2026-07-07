"""Testes do contrato oficial de contexto de mercado."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from market.context.market_context import MarketContext
from tests.architecture_test_utils import calls_from, imports_from, read_source


class MarketContextTest(unittest.TestCase):
    """Valida o DTO de contexto consolidado do mercado."""

    def test_context_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MarketContext))
        self.assertTrue(MarketContext.__dataclass_params__.frozen)

    def test_context_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(MarketContext)]

        self.assertEqual(
            field_names,
            [
                "timestamp",
                "regime",
                "volatility",
                "liquidity",
                "momentum",
                "session",
                "market_dna",
                "confidence",
                "metadata",
            ],
        )

    def test_context_possui_type_hints_explicitos(self) -> None:
        annotations = MarketContext.__annotations__

        self.assertEqual(annotations["timestamp"], "str")
        self.assertEqual(annotations["regime"], "str")
        self.assertEqual(annotations["volatility"], "float")
        self.assertEqual(annotations["liquidity"], "float")
        self.assertEqual(annotations["momentum"], "float")
        self.assertEqual(annotations["session"], "str")
        self.assertEqual(annotations["market_dna"], "Mapping[str, object]")
        self.assertEqual(annotations["confidence"], "float")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_context_representa_contexto_consolidado(self) -> None:
        context = self._context()

        self.assertEqual(context.timestamp, "2026-06-27T09:00:00-03:00")
        self.assertEqual(context.regime, "TREND")
        self.assertEqual(context.volatility, 22.5)
        self.assertEqual(context.liquidity, 1500.0)
        self.assertEqual(context.momentum, 8.0)
        self.assertEqual(context.session, "OPENING")
        self.assertEqual(context.market_dna["similarity"], 82)
        self.assertEqual(context.confidence, 0.78)
        self.assertEqual(context.metadata["source"], "fixture")

    def test_context_e_imutavel(self) -> None:
        context = self._context()

        with self.assertRaises(FrozenInstanceError):
            context.regime = "RANGE"

    def test_context_nao_implementa_metodos_operacionais(self) -> None:
        public_methods = [
            name for name in dir(MarketContext)
            if not name.startswith("_") and callable(getattr(MarketContext, name))
        ]

        self.assertEqual(public_methods, [])

    def test_context_nao_calcula_classifica_ou_acessa_candles(self) -> None:
        source = read_source(Path("market/context/market_context.py"))
        forbidden_fragments = (
            "FeatureEngine",
            "RegimeEngine",
            "MarketDNA",
            "MarketDataContract",
            "Candle",
            "Alpha001",
            "ReplayEngine",
            "ResearchPipeline",
            "DecisionPipeline",
            "Broker",
            "MT5",
            ".analyze(",
            ".criar_pattern(",
            ".comparar(",
            ".calculate(",
            ".build(",
            "next_candle",
            "sum(",
            "max(",
            "min(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_context_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/context/market_context.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "market.feature_engine",
            "market.regime_engine",
            "market.market_dna",
            "market.data.market_data_contract",
            "FeatureEngine",
            "RegimeEngine",
            "MarketDNA",
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
            "calculate",
            "build",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _context(self) -> MarketContext:
        return MarketContext(
            timestamp="2026-06-27T09:00:00-03:00",
            regime="TREND",
            volatility=22.5,
            liquidity=1500.0,
            momentum=8.0,
            session="OPENING",
            market_dna={"similarity": 82},
            confidence=0.78,
            metadata={"source": "fixture"},
        )


if __name__ == "__main__":
    unittest.main()
