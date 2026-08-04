from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from application.multi_ea_trading_lab_use_case import MultiEATradingLabUseCase


class _FakeAdapter:
    def __init__(self) -> None:
        self.positions_path = Path("positions.csv")
        self.history_database_path = Path("history.sqlite")
        self.fit_result_path = Path("fit_v1.json")
        self.fit: dict[str, object] = {}
        self.stored_batch: object | None = None
        self.imported_source: object | None = None
        self.download_counts = {
            "M1": 5000,
            "M5": 5000,
            "M15": 5000,
            "M30": 5000,
            "H1": 5000,
        }
        self.persisted_download_counts = dict(self.download_counts)
        self.positions = [SimpleNamespace(symbol="XAUUSD")]

    def read_fit_result(self) -> dict[str, object]:
        return dict(self.fit)

    def write_fit_result(self, payload: dict[str, object]) -> Path:
        self.fit = dict(payload)
        return self.fit_result_path

    def import_positions_csv(self, source_path: object, *, strict: bool) -> object:
        self.imported_source = source_path
        if not self.positions:
            self.positions = [SimpleNamespace(symbol="XAUUSD")]
        return SimpleNamespace(
            source_sha256="abc",
            total_rows=2,
            trade_rows=1,
            balance_rows=1,
            ignored_rows=0,
            persisted_path="positions.csv",
        )

    def load_positions(self, *, strict: bool) -> list[object]:
        return list(self.positions)

    def load_candles(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int,
    ) -> list[object]:
        if timeframe != "H1":
            return []
        return [
            SimpleNamespace(
                timestamp=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00")
            )
        ]

    def load_research_candles(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int,
    ) -> list[object]:
        return [object()] * min(
            int(self.persisted_download_counts.get(timeframe, 0)),
            limit,
        )

    def get_history_metadata(self) -> dict[str, object]:
        return {"positions_import": {"trade_rows": 1}}

    def store_provider_candles(
        self,
        batch: object,
        *,
        requested_count: int,
        source: str,
    ) -> dict[str, object]:
        self.stored_batch = batch
        return {
            "received_by_timeframe": dict(self.download_counts),
            "total_candles": sum(self.download_counts.values()),
            "database_path": "history.sqlite",
            "status": "OK",
        }


class _FakeEngine:
    def analyze(self, positions: object, candles: object, **kwargs: object) -> dict[str, object]:
        return {
            "status": "OK",
            "classification": "AMOSTRA_EXPLORATORIA",
            "research_only": True,
            "operational_eligible": False,
            "sample": {"positions": len(list(positions))},
            "coverage": {"candles": len(list(candles))},
            "behavior": {},
            "split": {},
            "ranking_global": [],
            "ranking_by_market": {},
            "reported_profile": {},
            "warnings": ["RESEARCH_ONLY"],
            "methodology": {},
        }


class _FakeProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, object]] = []
        self.last_error = ""

    def get_research_batch(
        self,
        symbols: object,
        timeframes: object,
        count: object,
    ) -> dict[str, object]:
        self.calls.append((symbols, timeframes, count))
        return {"H1": {"XAUUSD": {"candles": [object()]}}}


class MultiEATradingLabUseCaseTest(unittest.TestCase):
    def test_run_e_somente_local_e_persiste_resultado_compacto(self) -> None:
        adapter = _FakeAdapter()
        use_case = MultiEATradingLabUseCase(
            adapter=adapter,  # type: ignore[arg-type]
            engine=_FakeEngine(),  # type: ignore[arg-type]
        )

        result = use_case.run()

        self.assertEqual(result["name"], "Multi EA Trading")
        self.assertTrue(result["research_only"])
        self.assertFalse(result["operational_eligible"])
        self.assertEqual(result["candle_limit_per_series"], 5000)
        self.assertEqual(adapter.fit["status"], "OK")

    def test_download_ouro_usa_somente_batch_read_only_e_base_separada(self) -> None:
        adapter = _FakeAdapter()
        provider = _FakeProvider()
        use_case = MultiEATradingLabUseCase(
            adapter=adapter,  # type: ignore[arg-type]
            engine=_FakeEngine(),  # type: ignore[arg-type]
        )

        result = use_case.download_gold(provider)

        self.assertEqual(len(provider.calls), 1)
        symbols, timeframes, count = provider.calls[0]
        self.assertEqual(symbols, ["XAUUSD"])
        self.assertEqual(set(timeframes), {"M1", "M5", "M15", "M30", "H1"})
        self.assertEqual(count, 5000)
        self.assertIsNotNone(adapter.stored_batch)
        self.assertFalse(result["gold_download"]["operational_database_modified"])
        self.assertTrue(result["gold_download"]["read_only"])
        self.assertEqual(
            result["gold_download"]["persisted_by_timeframe"],
            adapter.persisted_download_counts,
        )

    def test_download_ouro_falha_fechado_se_um_timeframe_estiver_parcial(self) -> None:
        adapter = _FakeAdapter()
        adapter.persisted_download_counts["M1"] = 4999
        use_case = MultiEATradingLabUseCase(
            adapter=adapter,  # type: ignore[arg-type]
            engine=_FakeEngine(),  # type: ignore[arg-type]
        )

        with self.assertRaisesRegex(RuntimeError, "M1"):
            use_case.download_gold(_FakeProvider())

        self.assertEqual(adapter.fit, {})

    def test_sem_csv_retorna_falha_fechada_sem_escrever_fit(self) -> None:
        adapter = _FakeAdapter()
        adapter.positions = []
        use_case = MultiEATradingLabUseCase(
            adapter=adapter,  # type: ignore[arg-type]
            engine=_FakeEngine(),  # type: ignore[arg-type]
        )

        result = use_case.run()

        self.assertEqual(result["status"], "SEM_FONTE")
        self.assertTrue(result["research_only"])
        self.assertFalse(result["operational_eligible"])
        self.assertEqual(adapter.fit, {})

    def test_bootstrap_configuravel_importa_csv_sem_dependencia_da_ui(self) -> None:
        adapter = _FakeAdapter()
        adapter.positions = []
        use_case = MultiEATradingLabUseCase(
            adapter=adapter,  # type: ignore[arg-type]
            engine=_FakeEngine(),  # type: ignore[arg-type]
        )

        with patch.dict(
            "os.environ",
            {"TRADERIA_MULTI_EA_POSITIONS_CSV": "amostra/multi-ea.csv"},
        ):
            result = use_case.run()

        self.assertEqual(adapter.imported_source, "amostra/multi-ea.csv")
        self.assertEqual(result["status"], "OK")


if __name__ == "__main__":
    unittest.main()
