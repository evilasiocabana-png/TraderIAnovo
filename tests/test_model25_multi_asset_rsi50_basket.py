from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from application.model25_multi_asset_rsi50_basket import (
    MODEL_25_ID,
    MODEL_25_SYMBOLS,
    Model25BasketManager,
    evaluate_model25_pending_reentry,
    is_model25,
    mark_model25_market_entry_accepted,
    model25_market_entry_role,
    model25_order_comment,
    model25_symbol_pip_size,
)
from application.dashboard_service import (
    MT5_ACTIVE_SOURCE_MODEL_IDS,
    MT5_CUSTOM_OPERATIONAL_MODELS,
    MT5_OPERATIONAL_MODEL_25,
)
from domain.operational_model_policy import (
    is_active_operational_model,
    operational_model_number,
)


def _reentry_rows() -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for index in range(200):
        close = 1.10 + index * 0.0001
        rows.append(
            {
                "time": float(1_700_000_000 + index * 300),
                "open": close + (0.0002 if index == 199 else 0.0),
                "high": close + 0.0003,
                "low": close - 0.0003,
                "close": close,
            }
        )
    rows[-3]["close"] = rows[-2]["high"] + 0.001
    rows[-3]["high"] = rows[-3]["close"] + 0.0001
    rows.append(dict(rows[-1], time=rows[-1]["time"] + 300))
    return rows


def test_model25_has_exactly_the_canonical_19_assets() -> None:
    assert len(MODEL_25_SYMBOLS) == 19
    assert len(set(MODEL_25_SYMBOLS)) == 19
    assert {"XAUUSD", "BTCUSD", "EURUSD", "NZDJPY"}.issubset(MODEL_25_SYMBOLS)


def test_model25_is_active_and_has_own_comment() -> None:
    assert operational_model_number(MODEL_25_ID) == 25
    assert is_active_operational_model(MODEL_25_ID)
    assert is_model25(MODEL_25_ID)
    assert model25_order_comment() == "TraderIA M25"


def test_model25_is_registered_in_runtime_without_lab_heavy_cycle() -> None:
    assert MT5_OPERATIONAL_MODEL_25 == MODEL_25_ID
    assert MODEL_25_ID in MT5_ACTIVE_SOURCE_MODEL_IDS
    assert MODEL_25_ID in MT5_CUSTOM_OPERATIONAL_MODELS


def test_model25_uses_symbol_specific_pip_size() -> None:
    assert model25_symbol_pip_size("EURUSD") == 0.0001
    assert model25_symbol_pip_size("USDJPY") == 0.01
    assert model25_symbol_pip_size("XAUUSD") == 0.01


def test_model25_reentry_uses_forex_pip_without_changing_m24_logic() -> None:
    rows = _reentry_rows()
    with patch("application.model24_xau_basket._model24_distance_atr", return_value=0.5), patch(
        "application.model24_xau_basket._wilder_rsi", side_effect=(60.0, 59.0)
    ):
        decision = evaluate_model25_pending_reentry(rows, symbol="EURUSD")
    assert decision.ready
    assert decision.status.startswith("M25_")
    assert decision.initial_stop == rows[-2]["low"] - 0.0001


def test_model25_role_state_is_independent_per_symbol(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    with patch(
        "application.model25_multi_asset_rsi50_basket.MODEL_25_RUNTIME_STATE_PATH",
        state_path,
    ):
        assert model25_market_entry_role("EURUSD", "BUY") == "INITIAL"
        mark_model25_market_entry_accepted("EURUSD", "BUY", "2026-08-18T10:00:00Z")
        assert model25_market_entry_role("EURUSD", "BUY") == "REENTRY"
        assert model25_market_entry_role("GBPUSD", "BUY") == "INITIAL"
        assert model25_market_entry_role("EURUSD", "SELL") == "INITIAL"


def test_model25_basket_closes_only_m25_at_one_thousand(tmp_path: Path) -> None:
    positions = [
        SimpleNamespace(symbol="EURUSD", ticket=1, type=0, volume=0.2, profit=600.0, swap=0.0, commission=0.0, fee=0.0, comment="TraderIA M25 INITIAL"),
        SimpleNamespace(symbol="XAUUSD", ticket=2, type=1, volume=0.1, profit=410.0, swap=0.0, commission=0.0, fee=0.0, comment="TraderIA M25 REENTRY"),
        SimpleNamespace(symbol="GBPUSD", ticket=3, type=0, volume=0.1, profit=900.0, swap=0.0, commission=0.0, fee=0.0, comment="TraderIA M24 INITIAL"),
    ]

    class Provider:
        closed: list[int] = []

        def list_open_positions(self):
            return positions

        def close_position(self, **kwargs):
            self.closed.append(int(kwargs["ticket"]))
            return SimpleNamespace(accepted=True, message="ok")

    provider = Provider()
    snapshot = Model25BasketManager(
        execution_service=provider,
        state_path=tmp_path / "basket.json",
        audit_path=tmp_path / "audit.jsonl",
    ).evaluate_once()
    assert snapshot.status == "EXIT_SUBMITTED"
    assert snapshot.net_result_usd == 1010.0
    assert provider.closed == [1, 2]
