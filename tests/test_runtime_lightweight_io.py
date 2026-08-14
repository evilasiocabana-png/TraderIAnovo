from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import application.dashboard_service as dashboard_service_module
from application.demo_execution_service import DemoExecutionService
from application.dashboard_service import DashboardService
from application.dashboard_service import (
    MT5_OPERATIONAL_MODEL_8,
    MT5_OPERATIONAL_MODEL_ALL,
)
from application.mt5_market_data_service import MT5MarketDataService
from application.operational_indicator_window import (
    OPERATIONAL_INDICATOR_CLOSED_CANDLES,
    OPERATIONAL_INDICATOR_RAW_CANDLES,
)
from core.jsonl_tail import read_last_text_lines
from core.mt5_external_process_gate import (
    get_mt5_external_cache,
    mt5_external_process_slot,
    set_mt5_external_cache,
)


def _m5_time(index: int, *, day: int = 11) -> str:
    start = datetime(2026, 8, day, tzinfo=timezone.utc)
    return (start + timedelta(minutes=5 * index)).isoformat()
from domain.candle import Candle


def test_read_last_text_lines_reads_only_requested_tail(tmp_path: Path) -> None:
    target = tmp_path / "audit.jsonl"
    target.write_text("\n".join(f"line-{index}" for index in range(5000)) + "\n")

    assert read_last_text_lines(target, limit=3) == [
        "line-4997",
        "line-4998",
        "line-4999",
    ]


def test_mt5_external_process_gate_is_non_reentrant() -> None:
    with mt5_external_process_slot(timeout=0.0) as first:
        with mt5_external_process_slot(timeout=0.0) as second:
            assert first is True
            assert second is False


def test_mt5_external_cache_returns_copy() -> None:
    set_mt5_external_cache("positions-test", {"ok": True, "rows": []})

    cached = get_mt5_external_cache("positions-test", ttl_seconds=10.0)

    assert cached == {"ok": True, "rows": []}
    cached["ok"] = False
    assert get_mt5_external_cache("positions-test", ttl_seconds=10.0)["ok"] is True


def test_supplemental_candles_use_only_requested_pair_timeframes() -> None:
    class SparseProvider:
        calls: list[tuple[dict[str, list[str]], dict[str, object], int]] = []

        def get_sparse_research_batch(self, requested, timeframes, count):
            self.calls.append((requested, timeframes, count))
            return {
                timeframe: {
                    symbol: {
                        "exists": True,
                        "selected": True,
                        "candles": [
                            SimpleNamespace(data=f"2026-08-06T00:00:00+00:00")
                        ],
                    }
                    for symbol in symbols
                }
                for timeframe, symbols in requested.items()
            }

    provider = SparseProvider()
    service = MT5MarketDataService(provider=provider)

    errors = service._read_supplemental_forex_batch(
        {"M5": {"SYNTHETIC"}, "H1": {"EURUSD", "USDJPY"}},
        count=3,
    )

    assert errors == {}
    assert provider.calls[0][0] == {
        "M5": ["SYNTHETIC"],
        "H1": ["EURUSD", "USDJPY"],
    }
    assert ("SYNTHETIC", "H1") not in service.latest_forex_candles
    assert ("EURUSD", "M5") not in service.latest_forex_candles


def test_empty_operational_m5_cache_accepts_full_live_batch() -> None:
    candles = [
        Candle(_m5_time(index), 100.0, 101.0, 99.0, 100.5, 10)
        for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES)
    ]

    class FullProvider:
        def get_sparse_research_batch(self, requested, timeframes, count):
            assert count == OPERATIONAL_INDICATOR_RAW_CANDLES
            return {
                "M5": {
                    "XAUUSD": {
                        "exists": True,
                        "selected": True,
                        "candles": candles,
                    }
                }
            }

    service = MT5MarketDataService(provider=FullProvider())

    errors = service.refresh_supplemental_forex_candles(
        {"XAUUSD": {"M5"}},
        full_count=OPERATIONAL_INDICATOR_RAW_CANDLES,
    )

    assert errors == {}
    assert service.latest_forex_candles[("XAUUSD", "M5")] == candles


def test_supplemental_warm_cache_rehydrates_200_closed_m5_candles(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cache_path = tmp_path / "warm.json"
    monkeypatch.setenv("TRADERIA_MT5_WARM_CACHE_ENABLED", "1")
    monkeypatch.setenv("TRADERIA_MT5_WARM_CACHE_PATH", str(cache_path))
    candles = [
        Candle(
                _m5_time(index),
            1.0,
            2.0,
            0.5,
            1.5,
            10,
        )
        for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES)
    ]
    writer = MT5MarketDataService(provider=SimpleNamespace())
    writer.latest_forex_candles[("XAUUSD", "M5")] = candles
    writer._persist_supplemental_forex_cache()

    restored = MT5MarketDataService(provider=SimpleNamespace())

    assert cache_path.exists()
    assert restored.latest_forex_candles[("XAUUSD", "M5")] == candles
    assert ("XAUUSD", "M5") in restored.supplemental_forex_seed_only_keys


def test_seeded_operational_m5_rejects_incomplete_live_reconciliation() -> None:
    class PartialProvider:
        calls: list[int] = []

        def get_sparse_research_batch(self, requested, timeframes, count):
            self.calls.append(count)
            return {
                "M5": {
                    "XAUUSD": {
                        "exists": True,
                        "selected": True,
                        "candles": live_candles[-3:],
                    }
                }
            }

    seeded_candles = [
        Candle(
                _m5_time(index, day=5),
            100.0,
            101.0,
            99.0,
            100.5,
            10,
        )
        for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES)
    ]
    live_candles = [
        Candle(
                _m5_time(index),
            200.0,
            201.0,
            199.0,
            200.5,
            10,
        )
        for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES)
    ]
    provider = PartialProvider()
    service = MT5MarketDataService(provider=provider)
    service.seed_supplemental_forex_candles(
        {("XAUUSD", "M5"): seeded_candles}
    )

    errors = service.refresh_supplemental_forex_candles(
        {"XAUUSD": {"M5"}},
        full_count=OPERATIONAL_INDICATOR_RAW_CANDLES,
    )

    assert provider.calls == [OPERATIONAL_INDICATOR_RAW_CANDLES]
    assert errors["XAUUSD|M5"].startswith("RECUPERAR_LOTE_COMPLETO:")
    assert ("XAUUSD", "M5") in service.supplemental_forex_seed_only_keys
    assert service.latest_forex_candles[("XAUUSD", "M5")] == seeded_candles


def test_seeded_operational_m5_requires_full_live_reconciliation() -> None:
    class FullProvider:
        def get_sparse_research_batch(self, requested, timeframes, count):
            assert count == OPERATIONAL_INDICATOR_RAW_CANDLES
            return {
                "M5": {
                    "XAUUSD": {
                        "exists": True,
                        "selected": True,
                        "candles": live_candles,
                    }
                }
            }

    seeded_candles = [
        Candle(
            _m5_time(index),
            100.0,
            101.0,
            99.0,
            100.5,
            10,
        )
        for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES)
    ]
    live_candles = [
        Candle(
            _m5_time(index, day=12),
            200.0 + index,
            201.0 + index,
            199.0 + index,
            200.5 + index,
            10,
        )
        for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES)
    ]
    service = MT5MarketDataService(provider=FullProvider())
    service.seed_supplemental_forex_candles(
        {("XAUUSD", "M5"): seeded_candles}
    )

    errors = service.refresh_supplemental_forex_candles(
        {"XAUUSD": {"M5"}},
        full_count=OPERATIONAL_INDICATOR_RAW_CANDLES,
    )

    assert errors == {}
    assert ("XAUUSD", "M5") not in service.supplemental_forex_seed_only_keys
    assert service.latest_forex_candles[("XAUUSD", "M5")] == live_candles


def test_operational_m5_refreshes_previous_closed_and_current_candle() -> None:
    candles = [
        Candle(_m5_time(index), 100.0, 101.0, 99.0, 100.5, 10)
        for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES)
    ]
    corrected_previous = Candle(
        candles[-1].data,
        100.0,
        105.0,
        98.0,
        104.5,
        20,
    )
    current = Candle(
        _m5_time(OPERATIONAL_INDICATOR_RAW_CANDLES),
        104.5,
        106.0,
        103.0,
        105.0,
        5,
    )

    class TailProvider:
        def get_sparse_research_batch(self, requested, timeframes, count):
            assert count == 2
            return {
                "M5": {
                    "XAUUSD": {
                        "exists": True,
                        "selected": True,
                        "candles": [corrected_previous, current],
                    }
                }
            }

    service = MT5MarketDataService(provider=TailProvider())
    service.latest_forex_candles[("XAUUSD", "M5")] = candles

    errors = service.refresh_supplemental_forex_candles(
        {"XAUUSD": {"M5"}},
        full_count=OPERATIONAL_INDICATOR_RAW_CANDLES,
    )

    retained = service.latest_forex_candles[("XAUUSD", "M5")]
    assert errors == {}
    assert len(retained) == OPERATIONAL_INDICATOR_RAW_CANDLES
    assert retained[-2] == corrected_previous
    assert retained[-1] == current


def test_operational_m5_gap_forces_full_batch_reconciliation() -> None:
    stale = [
        Candle(_m5_time(index, day=5), 100.0, 101.0, 99.0, 100.5, 10)
        for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES)
    ]
    live = [
        Candle(_m5_time(index, day=12), 200.0, 201.0, 199.0, 200.5, 10)
        for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES)
    ]

    class GapProvider:
        calls: list[int] = []

        def get_sparse_research_batch(self, requested, timeframes, count):
            self.calls.append(count)
            candles = live if count == OPERATIONAL_INDICATOR_RAW_CANDLES else live[-2:]
            return {
                "M5": {
                    "XAUUSD": {
                        "exists": True,
                        "selected": True,
                        "candles": candles,
                    }
                }
            }

    provider = GapProvider()
    service = MT5MarketDataService(provider=provider)
    service.latest_forex_candles[("XAUUSD", "M5")] = stale

    errors = service.refresh_supplemental_forex_candles(
        {"XAUUSD": {"M5"}},
        full_count=OPERATIONAL_INDICATOR_RAW_CANDLES,
    )

    assert provider.calls == [2, OPERATIONAL_INDICATOR_RAW_CANDLES]
    assert errors == {}
    assert service.latest_forex_candles[("XAUUSD", "M5")] == live


def test_seeded_200_closed_candles_warm_models_without_authorizing_stale_order() -> None:
    candles = [
        Candle(
                _m5_time(index, day=5),
            100.0 + index,
            101.0 + index,
            99.0 + index,
            100.5 + index,
            10,
        )
        for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES)
    ]
    market_data = MT5MarketDataService(provider=SimpleNamespace())
    market_data.seed_supplemental_forex_candles(
        {("XAUUSD", "M5"): candles, ("AUDUSD", "M5"): candles}
    )
    service = DashboardService(mt5_market_data_service=market_data)
    service.set_mt5_operational_model(MT5_OPERATIONAL_MODEL_ALL)

    xau = service.get_xau_m5_operational_decision_snapshot()
    forex = service.get_forex_m5_sma_rsi_decision_snapshot()

    assert xau[("__XAU_M5__", "CANDLE_COUNT")] == OPERATIONAL_INDICATOR_RAW_CANDLES
    assert "AQUECIDO_200_FECHADOS" in xau[
        (MT5_OPERATIONAL_MODEL_8, "XAUUSD")
    ].status
    assert xau[(MT5_OPERATIONAL_MODEL_8, "XAUUSD")].ready is False
    assert forex[("__FOREX_M5__", "AUDUSD")] == OPERATIONAL_INDICATOR_RAW_CANDLES
    forex_decisions = [
        decision
        for (model_id, pair), decision in forex.items()
        if model_id != "__FOREX_M5__" and pair == "AUDUSD"
    ]
    assert forex_decisions
    assert all("AQUECIDO_200_FECHADOS" in item.status for item in forex_decisions)
    assert all(item.ready is False for item in forex_decisions)


def test_operational_m5_cache_discards_oldest_candle_after_200_closed() -> None:
    candles = [
        Candle(
            _m5_time(index),
            100.0 + index,
            101.0 + index,
            99.0 + index,
            100.5 + index,
            10,
        )
        for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES)
    ]
    newest = Candle(
        _m5_time(OPERATIONAL_INDICATOR_RAW_CANDLES),
        200.0,
        201.0,
        199.0,
        200.5,
        10,
    )
    service = MT5MarketDataService(provider=SimpleNamespace())
    service.latest_forex_candles[("XAUUSD", "M5")] = candles

    service._merge_forex_candle_cache(
        "XAUUSD",
        "M5",
        [newest],
        limit=500,
    )

    retained = service.latest_forex_candles[("XAUUSD", "M5")]
    assert len(retained) == OPERATIONAL_INDICATOR_RAW_CANDLES
    assert retained[0] == candles[1]
    assert retained[-1] == newest


def test_model15_ui_reuses_real_background_state_without_candles(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state_path = tmp_path / "model15_runtime_state.json"
    state_path.write_text(
        json.dumps(
            {
                "direction": "SELL",
                "status": "M15_SELL_STOP_PRONTA",
                "reason": "Leitura real do ciclo de fundo.",
                "current_candle_time": "2026-08-06T09:35:00+00:00",
                "previous_candle_time": "2026-08-06T09:30:00+00:00",
                "entry_price": 4254.18,
                "initial_stop": 4258.17,
                "ema20": 4260.86,
                "ema50": 4264.62,
                "previous_high": 4258.16,
                "previous_low": 4254.19,
                "current_high": 4255.87,
                "current_low": 4252.77,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        dashboard_service_module,
        "_MODEL15_RUNTIME_STATE_PATH",
        state_path,
    )

    decision = DashboardService().get_model15_entry_decision(
        read_only_fallback=True
    )

    assert decision.status == "M15_SELL_STOP_PRONTA"
    assert decision.entry_price == 4254.18


def test_lightweight_open_positions_keep_mt5_rows_visible_by_ticket(
    monkeypatch,
) -> None:
    position = SimpleNamespace(
        ticket=123456,
        symbol="XAUUSD",
        type=1,
        volume=0.1,
        price_open=4250.0,
        price_current=4245.0,
        sl=4255.0,
        tp=0.0,
        profit=50.0,
        swap=-1.25,
        time=1786000000,
        comment="TraderIA M15",
    )

    class Provider:
        def list_open_positions(self):
            return [position]

    service = DashboardService(
        demo_robot_execution_service=DemoExecutionService(provider=Provider())
    )
    monkeypatch.setattr(
        DashboardService,
        "_enable_mt5_demo_provider",
        lambda _self: None,
    )

    report = service._lightweight_open_positions_report()

    assert report is not None
    assert len(report.rows) == 1
    row = report.rows[0]
    assert row.operation_status == "ABERTA"
    assert row.mt5_ticket == 123456
    assert row.mt5_price == 4245.0
    assert row.mt5_stop == 4255.0
    assert row.mt5_swap == -1.25
    assert row.operational_model == dashboard_service_module.MT5_OPERATIONAL_MODEL_15


def test_lightweight_merge_preserves_last_valid_open_rows_when_probe_is_busy(
    monkeypatch,
) -> None:
    service = DashboardService()
    previous = dashboard_service_module.DashboardMT5TradeAuditViewModel(
        rows=[
            dashboard_service_module.DashboardMT5TradeAuditRowViewModel(
                symbol="EURUSD",
                operation_status="ABERTA",
                mt5_ticket=99,
            )
        ]
    )
    monkeypatch.setattr(
        DashboardService,
        "_lightweight_open_positions_report",
        lambda _self, _base=None: None,
    )

    assert service._merge_lightweight_open_positions(previous) is previous
