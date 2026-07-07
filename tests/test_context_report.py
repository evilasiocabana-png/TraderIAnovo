"""Testes do relatorio oficial do Context Lab."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from market.context.context_quality_engine import ContextQualityResult
from market.context.context_report import ContextReport
from market.context.market_context import MarketContext
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ContextReportTest(unittest.TestCase):
    """Valida consolidacao pura dos resultados do Context Lab."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ContextReport))
        self.assertTrue(ContextReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ContextReport)]

        self.assertEqual(
            field_names,
            [
                "context",
                "quality_result",
                "regime",
                "volatility",
                "liquidity",
                "momentum",
                "session",
                "market_dna",
                "confidence_score",
                "quality_score",
                "execution_time",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = ContextReport.__annotations__

        self.assertEqual(annotations["context"], "MarketContext")
        self.assertEqual(annotations["quality_result"], "ContextQualityResult")
        self.assertEqual(annotations["regime"], "str")
        self.assertEqual(annotations["volatility"], "float")
        self.assertEqual(annotations["liquidity"], "float")
        self.assertEqual(annotations["momentum"], "float")
        self.assertEqual(annotations["session"], "str")
        self.assertEqual(annotations["market_dna"], "Mapping[str, object]")
        self.assertEqual(annotations["confidence_score"], "float")
        self.assertEqual(annotations["quality_score"], "float")
        self.assertEqual(annotations["execution_time"], "float")

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.context, MarketContext)
        self.assertIsInstance(report.quality_result, ContextQualityResult)
        self.assertEqual(report.regime, "TREND")
        self.assertEqual(report.volatility, 22.5)
        self.assertEqual(report.liquidity, 1500.0)
        self.assertEqual(report.momentum, 8.0)
        self.assertEqual(report.session, "OPENING")
        self.assertEqual(report.market_dna["similarity"], 82)
        self.assertEqual(report.confidence_score, 78.0)
        self.assertEqual(report.quality_score, 89.0)
        self.assertEqual(report.execution_time, 3.5)

    def test_report_preserva_referencias_recebidas(self) -> None:
        context = self._context()
        quality = self._quality()
        market_dna = {"similarity": 82}

        report = ContextReport(
            context=context,
            quality_result=quality,
            regime="TREND",
            volatility=22.5,
            liquidity=1500.0,
            momentum=8.0,
            session="OPENING",
            market_dna=market_dna,
            confidence_score=78.0,
            quality_score=89.0,
            execution_time=3.5,
        )

        self.assertIs(report.context, context)
        self.assertIs(report.quality_result, quality)
        self.assertIs(report.market_dna, market_dna)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.execution_time = 0.0

    def test_report_nao_realiza_calculos_ou_execucoes(self) -> None:
        source = read_source(Path("market/context/context_report.py"))
        forbidden_fragments = (
            ".run(",
            ".execute(",
            ".evaluate(",
            ".build(",
            ".analyze(",
            ".criar_pattern(",
            ".comparar(",
            "sum(",
            "max(",
            "min(",
            "round(",
            "len(",
            "ContextPipeline",
            "ContextQualityEngine",
            "MarketContextBuilder",
            "FeatureEngine",
            "RegimeEngine",
            "MarketDNA",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_nao_gera_interfaces_ou_persistencia(self) -> None:
        source = read_source(Path("market/context/context_report.py"))
        forbidden_fragments = (
            "dashboard",
            "streamlit",
            "html",
            "pdf",
            "open(",
            "write",
            "json",
            "csv",
            "export",
            "database",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/context/context_report.py")
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
            "execute",
            "evaluate",
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

    def _report(self) -> ContextReport:
        return ContextReport(
            context=self._context(),
            quality_result=self._quality(),
            regime="TREND",
            volatility=22.5,
            liquidity=1500.0,
            momentum=8.0,
            session="OPENING",
            market_dna={"similarity": 82},
            confidence_score=78.0,
            quality_score=89.0,
            execution_time=3.5,
        )

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

    def _quality(self) -> ContextQualityResult:
        return ContextQualityResult(
            total_contexts=1,
            confidence_score=78.0,
            consistency_score=100.0,
            quality_score=89.0,
        )


if __name__ == "__main__":
    unittest.main()
