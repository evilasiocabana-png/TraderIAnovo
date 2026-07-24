"""Build a read-only local MT5 snapshot for isolated Alpha research."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from infrastructure.market_data.mt5_market_data_provider import MT5MarketDataProvider


DEFAULT_PAIRS = (
    "EURUSD",
    "GBPUSD",
    "USDCHF",
    "USDJPY",
    "EURJPY",
    "AUDUSD",
    "NZDUSD",
    "USDCAD",
)

TIMEFRAME_VALUES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 16385,
    "H4": 16388,
    "D1": 16408,
}


def build_snapshot(
    timeframe: str,
    count: int,
    pairs: tuple[str, ...] = DEFAULT_PAIRS,
) -> dict[str, object]:
    normalized_timeframe = str(timeframe).strip().upper()
    if normalized_timeframe not in TIMEFRAME_VALUES:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    provider = MT5MarketDataProvider()
    if not provider.connect():
        raise RuntimeError(provider.last_error or "MT5 read-only connection failed.")
    candles_by_market: dict[str, list[dict[str, object]]] = {}
    for pair in pairs:
        normalized_pair = str(pair).strip().upper()
        if not provider.select_symbol(normalized_pair):
            raise RuntimeError(f"MT5 symbol unavailable: {normalized_pair}")
        candles = provider.get_candles(
            normalized_pair,
            TIMEFRAME_VALUES[normalized_timeframe],
            int(count),
        )
        if len(candles) < int(count):
            raise RuntimeError(
                f"{normalized_pair}|{normalized_timeframe}: requested {count}, "
                f"received {len(candles)}."
            )
        candles_by_market[f"{normalized_pair}|{normalized_timeframe}"] = [
            asdict(candle) for candle in candles
        ]
        print(
            json.dumps(
                {
                    "market": f"{normalized_pair}|{normalized_timeframe}",
                    "candles": len(candles),
                }
            ),
            flush=True,
        )
    return {
        "source": "MT5_READ_ONLY",
        "server": provider.server_name,
        "timeframe": normalized_timeframe,
        "candles_per_market": int(count),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candles_by_market": candles_by_market,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeframe", required=True, choices=sorted(TIMEFRAME_VALUES))
    parser.add_argument("--count", type=int, default=20_000)
    parser.add_argument("--pairs", nargs="*", default=list(DEFAULT_PAIRS))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_snapshot(
        args.timeframe,
        args.count,
        tuple(args.pairs),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "status": "OK"}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
