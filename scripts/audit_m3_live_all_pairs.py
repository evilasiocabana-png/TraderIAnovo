"""Read-only MT5 audit for the operational Model 3 universe."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.lab_operational_model_service import (
    LabOperationalModelService,
    MODEL_3_ID,
)
from application.mt5_market_data_service import MT5MarketDataService


BLOCKING_DATA_STATUSES = {
    "FEATURE_EVALUATION_ERROR",
    "INSUFFICIENT_LIVE_CANDLES",
    "PAIR_NOT_IN_LAB_MODEL",
}


def main() -> None:
    market = MT5MarketDataService()
    model = LabOperationalModelService()
    failures: list[str] = []
    for pair in sorted(model.results(MODEL_3_ID)):
        snapshot = market.load_dashboard_market_data(pair, "H1", 500)
        last_price = (
            float(snapshot.last_candle.close)
            if snapshot.last_candle is not None
            else None
        )
        decision = model.evaluate(
            model_id=MODEL_3_ID,
            pair=pair,
            candles_by_market={(pair, "H1"): snapshot.candles},
            current_price=last_price,
        )
        certified = bool(
            (model.winner(MODEL_3_ID, pair) or {}).get("research_qualified")
        )
        print(
            f"{pair}: connection={snapshot.connection_status} "
            f"candles={len(snapshot.candles)} status={decision.status} "
            f"direction={decision.direction} certified={certified}"
        )
        if snapshot.connection_status != "CONNECTED":
            failures.append(f"{pair}: MT5 disconnected")
        if decision.status in BLOCKING_DATA_STATUSES:
            failures.append(f"{pair}: {decision.status} - {decision.reason}")
    if failures:
        raise SystemExit("\n".join(failures))


if __name__ == "__main__":
    main()
