from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import application.dashboard_service as dashboard_service_module
from application.demo_execution_service import DemoExecutionService
from application.dashboard_service import DashboardService
from application.dashboard_service import (
    MT5_OPERATIONAL_MODEL_8,
    MT5_OPERATIONAL_MODEL_ALL,
)
from application.forex_m5_sma_rsi_model_family import MODEL_13_ID
from application.mt5_market_data_service import MT5MarketDataService
from core.jsonl_tail import read_last_text_lines
from core.mt5_external_process_gate import (
    get_mt5_external_cache,
    mt5_external_process_slot,
    set_mt5_external_cache,
)
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
        {"M5": {"XAUUSD"}, "H1": {"EURUSD", "USDJPY"}},
        count=3,
    )

    assert errors == {}
    assert provider.calls[0][0] == {
        "M5": ["XAUUSD"],
        "H1": ["EURUSD", "USDJPY"],
    }
    assert ("XAUUSD", "H1") not in service.latest_forex_candles
    assert ("EURUSD", "M5") not in service.latest_forex_candles


def test_supplemental_warm_cache_rehydrates_52_m5_candles(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cache_path = tmp_path / "warm.json"
    monkeypatch.setenv("TRADERIA_MT5_WARM_CACHE_ENABLED", "1")
    monkeypatch.setenv("TRADERIA_MT5_WARM_CACHE_PATH", str(cache_path))
    candles = [
        Candle(
            f"2026-08-11T{index // 12:02d}:{(index % 12) * 5:02d}:00+00:00",
            1.0,
            2.0,
            0.5,
            1.5,
            10,
        )
        for index in range(52)
    ]
    writer = MT5MarketDataService(provider=SimpleNamespace())
    writer.latest_forex_candles[("XAUUSD", "M5")] = candles
    writer._persist_supplemental_forex_cache()

    restored = MT5MarketDataService(provider=SimpleNamespace())

    assert cache_path.exists()
    assert restored.latest_forex_candles[("XAUUSD", "M5")] == candles
    assert ("XAUUSD", "M5") not in restored.supplemental_forex_seed_only_keys


def test_seeded_operational_m5_recovers_full_batch_only_when_latest_has_gap() -> None:
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
            f"2026-08-05T{index // 12:02d}:{(index % 12) * 5:02d}:00+00:00",
            100.0,
            101.0,
            99.0,
            100.5,
            10,
        )
        for index in range(52)
    ]
    live_candles = [
        Candle(
            f"2026-08-11T{index // 12:02d}:{(index % 12) * 5:02d}:00+00:00",
            200.0,
            201.0,
            199.0,
            200.5,
            10,
        )
        for index in range(52)
    ]
    provider = PartialProvider()
    service = MT5MarketDataService(provider=provider)
    service.seed_supplemental_forex_candles(
        {("XAUUSD", "M5"): seeded_candles}
    )

    errors = service.refresh_supplemental_forex_candles(
        {"XAUUSD": {"M5"}},
        full_count=52,
    )

    assert provider.calls == [1, 52]
    assert errors["XAUUSD|M5"].startswith("RECUPERAR_LOTE_COMPLETO:")
    assert ("XAUUSD", "M5") in service.supplemental_forex_seed_only_keys
    assert service.latest_forex_candles[("XAUUSD", "M5")] == seeded_candles


def test_one_adjacent_live_candle_rolls_cache_and_unlocks_operational_m5() -> None:
    class IncrementalProvider:
        def get_sparse_research_batch(self, requested, timeframes, count):
            assert count == 1
            return {
                "M5": {
                    "XAUUSD": {
                        "exists": True,
                        "selected": True,
                        "candles": [latest_candle],
                    }
                }
            }

    seeded_candles = [
        Candle(
            f"2026-08-11T{index // 12:02d}:{(index % 12) * 5:02d}:00+00:00",
            100.0,
            101.0,
            99.0,
            100.5,
            10,
        )
        for index in range(52)
    ]
    latest_candle = Candle(
        "2026-08-11T04:20:00+00:00",
        200.0,
        201.0,
        199.0,
        200.5,
        10,
    )
    service = MT5MarketDataService(provider=IncrementalProvider())
    service.seed_supplemental_forex_candles(
        {("XAUUSD", "M5"): seeded_candles}
    )

    errors = service.refresh_supplemental_forex_candles(
        {"XAUUSD": {"M5"}},
        full_count=52,
    )

    assert errors == {}
    assert ("XAUUSD", "M5") not in service.supplemental_forex_seed_only_keys
    assert service.latest_forex_candles[("XAUUSD", "M5")] == [
        *seeded_candles[1:],
        latest_candle,
    ]


def test_seeded_52_candles_warm_models_without_authorizing_stale_order() -> None:
    candles = [
        Candle(
            f"2026-08-05T{index // 12:02d}:{(index % 12) * 5:02d}:00+00:00",
            100.0 + index,
            101.0 + index,
            99.0 + index,
            100.5 + index,
            10,
        )
        for index in range(52)
    ]
    market_data = MT5MarketDataService(provider=SimpleNamespace())
    market_data.seed_supplemental_forex_candles(
        {("XAUUSD", "M5"): candles, ("AUDUSD", "M5"): candles}
    )
    service = DashboardService(mt5_market_data_service=market_data)
    service.set_mt5_operational_model(MT5_OPERATIONAL_MODEL_ALL)

    xau = service.get_xau_m5_operational_decision_snapshot()
    forex = service.get_forex_m5_sma_rsi_decision_snapshot()

    assert xau[("__XAU_M5__", "CANDLE_COUNT")] == 52
    assert "AQUECIDO_52_CANDLES" in xau[
        (MT5_OPERATIONAL_MODEL_8, "XAUUSD")
    ].status
    assert xau[(MT5_OPERATIONAL_MODEL_8, "XAUUSD")].ready is False
    assert forex[("__FOREX_M5__", "AUDUSD")] == 52
    assert "AQUECIDO_52_CANDLES" in forex[(MODEL_13_ID, "AUDUSD")].status
    assert forex[(MODEL_13_ID, "AUDUSD")].ready is False


def test_operational_m5_cache_discards_oldest_candle_after_52() -> None:
    candles = [
        Candle(
            f"2026-08-11T{index // 12:02d}:{(index % 12) * 5:02d}:00+00:00",
            100.0 + index,
            101.0 + index,
            99.0 + index,
            100.5 + index,
            10,
        )
        for index in range(52)
    ]
    newest = Candle(
        "2026-08-11T05:00:00+00:00",
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
    assert len(retained) == 52
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
