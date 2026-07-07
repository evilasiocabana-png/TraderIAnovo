"""Testes do relatorio oficial de features."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from market.features.feature_definition import FeatureDefinition
from market.features.feature_report import FeatureReport
from market.features.feature_validator import FeatureValidationResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class FeatureReportTest(unittest.TestCase):
    """Valida consolidacao pura dos resultados de features."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(FeatureReport))
        self.assertTrue(FeatureReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(FeatureReport)]

        self.assertEqual(
            field_names,
            [
                "feature_definitions",
                "validation_results",
                "calculated_values",
                "execution_time_ms",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = FeatureReport.__annotations__

        self.assertEqual(annotations["feature_definitions"], "tuple[FeatureDefinition, ...]")
        self.assertEqual(
            annotations["validation_results"],
            "tuple[FeatureValidationResult, ...]",
        )
        self.assertEqual(annotations["calculated_values"], "Mapping[str, object]")
        self.assertEqual(annotations["execution_time_ms"], "float")

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.feature_definitions[0], FeatureDefinition)
        self.assertIsInstance(report.validation_results[0], FeatureValidationResult)
        self.assertEqual(report.calculated_values["Momentum"], 12.5)
        self.assertEqual(report.execution_time_ms, 7.25)

    def test_report_preserva_referencias_recebidas(self) -> None:
        definitions = (self._definition(),)
        validations = (FeatureValidationResult(True, ()),)
        values = {"Momentum": 12.5}

        report = FeatureReport(
            feature_definitions=definitions,
            validation_results=validations,
            calculated_values=values,
            execution_time_ms=7.25,
        )

        self.assertIs(report.feature_definitions, definitions)
        self.assertIs(report.validation_results, validations)
        self.assertIs(report.calculated_values, values)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.execution_time_ms = 1.0

    def test_report_nao_realiza_calculos_ou_execucoes(self) -> None:
        source = read_source(Path("market/features/feature_report.py"))
        forbidden_fragments = (
            ".run(",
            ".execute(",
            ".calculate(",
            ".build(",
            ".validate(",
            "sum(",
            "max(",
            "min(",
            "FeatureEngine",
            "Alpha001",
            "ReplayEngine",
            "DecisionPipeline",
            "ResearchPipeline",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_nao_gera_interfaces_ou_persistencia(self) -> None:
        source = read_source(Path("market/features/feature_report.py"))
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
        path = Path("market/features/feature_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "market.feature_engine",
            "FeatureEngine",
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
            "validate",
            "calculate",
            "build",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> FeatureReport:
        return FeatureReport(
            feature_definitions=(self._definition(),),
            validation_results=(FeatureValidationResult(True, ()),),
            calculated_values={"Momentum": 12.5},
            execution_time_ms=7.25,
        )

    def _definition(self) -> FeatureDefinition:
        return FeatureDefinition(
            feature_id="Momentum",
            name="Momentum",
            description="Definicao declarativa de momentum.",
            category="price_action",
            timeframe="1m",
            data_type="float",
            source="market_data",
            version=1,
            author="TraderIA",
            created_at="2026-06-27T22:30:00-03:00",
            enabled=True,
        )


if __name__ == "__main__":
    unittest.main()
