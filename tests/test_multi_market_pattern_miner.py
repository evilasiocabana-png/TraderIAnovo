from __future__ import annotations

import json
from pathlib import Path

from application.xau_pattern_miner_service import (
    XauPatternMinerService,
    pattern_miner_dataset_path,
)
from domain.market_universe import MT5_RESEARCH_MARKETS
from application.model28_pattern_miner_shadow import Model28ShadowRuntime


def test_all_19_markets_have_independent_dataset_paths() -> None:
    paths = {symbol: pattern_miner_dataset_path(symbol) for symbol in MT5_RESEARCH_MARKETS}
    assert len(paths) == 19
    assert len(set(paths.values())) == 19
    assert paths["XAUUSD"].name == "historicoXAU_XAUUSD_M5.csv"
    assert paths["EURUSD"].name == "historicoEURUSD.csv"


def test_market_service_keeps_shared_m28_registry_and_isolated_summary() -> None:
    xau = XauPatternMinerService.for_symbol("XAUUSD")
    eur = XauPatternMinerService.for_symbol("EURUSD")
    assert xau.operational_store_path == eur.operational_store_path
    assert xau.summary_path != eur.summary_path
    assert eur.symbol == "EURUSD"
    assert eur.timeframe == "M5"


def test_summary_is_rejected_when_dataset_changes(tmp_path: Path) -> None:
    dataset = tmp_path / "historicoTEST.csv"
    dataset.write_text("header\n", encoding="utf-8")
    service = XauPatternMinerService.for_symbol("EURUSD")
    service.dataset_path = dataset
    service.dataset_name = "historicoTEST"
    service.summary_path.write_text(
        json.dumps(
            {
                "symbol": "EURUSD",
                "dataset_size": dataset.stat().st_size,
                "dataset_mtime_ns": dataset.stat().st_mtime_ns,
            }
        ),
        encoding="utf-8",
    )
    assert service.load_summary() is not None
    dataset.write_text("header\nchanged\n", encoding="utf-8")
    assert service.load_summary() is None


def test_runtime_rejects_legacy_promotions_without_cost_aware_evidence(
    tmp_path: Path,
) -> None:
    runtime = Model28ShadowRuntime(
        registry_path=tmp_path / "patterns.json",
        journal_path=tmp_path / "shadow.json",
        auto_activate_replay_contracts=False,
    )
    assert runtime.active_markets() == ()
    assert runtime.has_active_specs() is False
