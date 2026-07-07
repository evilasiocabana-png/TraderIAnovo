"""Testes do contrato oficial de calendario de negociacao."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from market.instruments.trading_calendar import TradingCalendar
from tests.architecture_test_utils import calls_from, imports_from, read_source


class TradingCalendarTest(unittest.TestCase):
    """Valida contrato imutavel de calendario de negociacao."""

    def test_calendar_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(TradingCalendar))
        self.assertTrue(TradingCalendar.__dataclass_params__.frozen)

    def test_calendar_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(TradingCalendar)],
            [
                "calendar_id",
                "business_days",
                "holidays",
                "sessions",
                "market_open",
                "market_close",
                "special_hours",
                "metadata",
            ],
        )

    def test_calendar_possui_type_hints_explicitos(self) -> None:
        annotations = TradingCalendar.__annotations__

        self.assertEqual(annotations["calendar_id"], "str")
        self.assertEqual(annotations["business_days"], "tuple[str, ...]")
        self.assertEqual(annotations["holidays"], "tuple[str, ...]")
        self.assertEqual(annotations["sessions"], "tuple[str, ...]")
        self.assertEqual(annotations["market_open"], "str")
        self.assertEqual(annotations["market_close"], "str")
        self.assertEqual(annotations["special_hours"], "Mapping[str, str]")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_calendar_representa_estrutura_de_negociacao(self) -> None:
        calendar = self._calendar()

        self.assertEqual(calendar.calendar_id, "B3")
        self.assertEqual(calendar.business_days, ("MON", "TUE", "WED", "THU", "FRI"))
        self.assertEqual(calendar.holidays, ("2026-01-01",))
        self.assertEqual(calendar.sessions, ("REGULAR", "AFTER_MARKET"))
        self.assertEqual(calendar.market_open, "09:00")
        self.assertEqual(calendar.market_close, "18:00")
        self.assertEqual(calendar.special_hours["2026-12-24"], "09:00-13:00")
        self.assertEqual(calendar.metadata["source"], "contract-only")

    def test_calendar_e_imutavel(self) -> None:
        calendar = self._calendar()

        with self.assertRaises(FrozenInstanceError):
            calendar.market_open = "10:00"

    def test_calendar_nao_implementa_logica_de_calendario_real(self) -> None:
        public_methods = [
            name for name in dir(TradingCalendar)
            if not name.startswith("_") and callable(getattr(TradingCalendar, name))
        ]

        self.assertEqual(public_methods, [])

    def test_calendar_permanece_desacoplado_de_camadas_proibidas(self) -> None:
        path = Path("market/instruments/trading_calendar.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "market.data",
            "market.features",
            "replay",
            "research",
            "strategies",
            "alpha",
            "core.decision_pipeline",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "open",
            "validate",
            "calculate",
            "run",
            "is_business_day",
            "is_holiday",
            "next_session",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_calendar_nao_contem_acoplamento_no_codigo_fonte(self) -> None:
        source = read_source(Path("market/instruments/trading_calendar.py"))
        forbidden_fragments = (
            "DataPipeline",
            "FeaturePipeline",
            "ReplayEngine",
            "ResearchPipeline",
            "Alpha001",
            "FeatureEngine",
            "DecisionPipeline",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            "datetime.now",
            "weekday(",
            "is_holiday",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def _calendar(self) -> TradingCalendar:
        return TradingCalendar(
            calendar_id="B3",
            business_days=("MON", "TUE", "WED", "THU", "FRI"),
            holidays=("2026-01-01",),
            sessions=("REGULAR", "AFTER_MARKET"),
            market_open="09:00",
            market_close="18:00",
            special_hours={"2026-12-24": "09:00-13:00"},
            metadata={"source": "contract-only"},
        )


if __name__ == "__main__":
    unittest.main()
