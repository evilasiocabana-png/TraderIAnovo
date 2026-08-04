from __future__ import annotations

import unittest
from unittest.mock import patch

import dashboard_app


class _Context:
    def __init__(self, owner: "_FakeStreamlit") -> None:
        self.owner = owner

    def __enter__(self) -> "_Context":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def button(self, *args: object, **kwargs: object) -> bool:
        self.owner.buttons.append(str(args[0] if args else ""))
        return False

    def metric(self, label: object, value: object, *args: object, **kwargs: object) -> None:
        self.owner.metrics.append((str(label), value))


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {}
        self.subheaders: list[str] = []
        self.messages: list[str] = []
        self.buttons: list[str] = []
        self.metrics: list[tuple[str, object]] = []

    def container(self, **kwargs: object) -> _Context:
        return _Context(self)

    def columns(self, count: object) -> list[_Context]:
        quantity = count if isinstance(count, int) else len(list(count))
        return [_Context(self) for _ in range(quantity)]

    def expander(self, *args: object, **kwargs: object) -> _Context:
        return _Context(self)

    def spinner(self, *args: object, **kwargs: object) -> _Context:
        return _Context(self)

    def subheader(self, value: object) -> None:
        self.subheaders.append(str(value))

    def caption(self, value: object) -> None:
        self.messages.append(str(value))

    def warning(self, value: object) -> None:
        self.messages.append(str(value))

    def success(self, value: object) -> None:
        self.messages.append(str(value))

    def info(self, value: object) -> None:
        self.messages.append(str(value))

    def error(self, value: object) -> None:
        self.messages.append(str(value))

    def write(self, value: object) -> None:
        self.messages.append(str(value))

    def markdown(self, value: object, **kwargs: object) -> None:
        self.messages.append(str(value))

    def json(self, value: object) -> None:
        self.messages.append(str(value))


class _FakeService:
    def __init__(self) -> None:
        self.get_calls = 0
        self.run_calls = 0
        self.download_calls = 0

    def get_multi_ea_trading_lab_report(self) -> dict[str, object]:
        self.get_calls += 1
        return {
            "status": "OK",
            "classification": "AMOSTRA_EXPLORATORIA",
            "research_only": True,
            "sample": {"positions": 322, "markets": 18},
            "coverage": {
                "markets_with_history": 8,
                "full_series": 40,
                "by_market": [],
            },
            "behavior": {},
            "split": {},
            "reported_profile": {"estatistica": {"operacoes": 346}},
            "ranking_global": [],
            "ranking_by_market": {},
            "warnings": ["RESEARCH_ONLY"],
            "methodology": {"lookahead": False},
            "gold_download": {
                "received_by_timeframe": {
                    "M1": 5000,
                    "M5": 5000,
                    "M15": 5000,
                    "M30": 5000,
                    "H1": 5000,
                }
            },
        }

    def run_multi_ea_trading_lab(self) -> dict[str, object]:
        self.run_calls += 1
        return {}

    def download_multi_ea_trading_gold(self) -> dict[str, object]:
        self.download_calls += 1
        return {}


class MultiEADashboardPanelTest(unittest.TestCase):
    def test_render_passivo_le_somente_relatorio_compacto(self) -> None:
        fake_st = _FakeStreamlit()
        service = _FakeService()

        with patch.object(dashboard_app, "st", fake_st):
            dashboard_app.exibir_multi_ea_trading_lab(service)  # type: ignore[arg-type]

        self.assertEqual(service.get_calls, 1)
        self.assertEqual(service.run_calls, 0)
        self.assertEqual(service.download_calls, 0)
        self.assertIn("Multi EA Trading", fake_st.subheaders)
        self.assertIn(("Posicoes no CSV", 322), fake_st.metrics)
        self.assertIn(("Ativos com candles", 8), fake_st.metrics)
        self.assertIn("RESEARCH_ONLY", " ".join(fake_st.messages))
        self.assertIn("M1 5,000 candles", " ".join(fake_st.messages))


if __name__ == "__main__":
    unittest.main()
