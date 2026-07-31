"""Read-only MT5 audit for the operational Model 4 universe."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.lab_operational_model_service import (
    LabOperationalModelService,
    MODEL_4_ID,
)
from application.mt5_market_data_service import MT5MarketDataService


PAIRS = (
    "AUDUSD",
    "EURJPY",
    "EURUSD",
    "GBPUSD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "USDJPY",
)
TIMEFRAMES = ("M30", "H1", "H4")
BLOCKING_DATA_STATUSES = {
    "M4_CONTEXT_CACHE_INCOMPLETE",
    "M4_CONTEXT_EVALUATION_ERROR",
    "PAIR_NOT_IN_LAB_MODEL",
}


def main() -> None:
    market = MT5MarketDataService()
    model = LabOperationalModelService()
    candles_by_market: dict[tuple[str, str], list[object]] = {}
    prices: dict[str, float | None] = {}
    failures: list[str] = []

    for pair in PAIRS:
        for timeframe in TIMEFRAMES:
            snapshot = market.load_dashboard_market_data(pair, timeframe, 500)
            candles_by_market[(pair, timeframe)] = list(snapshot.candles)
            if timeframe == "M30":
                prices[pair] = (
                    float(snapshot.last_candle.close)
                    if snapshot.last_candle is not None
                    else None
                )
            if snapshot.connection_status != "CONNECTED":
                failures.append(f"{pair}/{timeframe}: MT5 disconnected")

    for pair in PAIRS:
        decision = model.evaluate(
            model_id=MODEL_4_ID,
            pair=pair,
            candles_by_market=candles_by_market,
            current_price=prices.get(pair),
        )
        winner = model.winner(MODEL_4_ID, pair) or {}
        print(
            f"{pair}: status={decision.status} direction={decision.direction} "
            f"family={decision.family} research={winner.get('research_status')}"
        )
        if decision.status in BLOCKING_DATA_STATUSES:
            failures.append(f"{pair}: {decision.status} - {decision.reason}")

    if failures:
        raise SystemExit("\n".join(failures))


if __name__ == "__main__":
    main()
