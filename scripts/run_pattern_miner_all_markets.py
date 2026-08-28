"""Run all M5 Pattern Miner histories sequentially and prepare M28 Demo specs."""

from __future__ import annotations

import gc
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.xau_pattern_miner_service import XauPatternMinerService
from domain.market_universe import MT5_RESEARCH_MARKETS


MARKETS = (
    "XAUUSD",
    *(symbol for symbol in MT5_RESEARCH_MARKETS if symbol != "XAUUSD"),
)


def main() -> int:
    failures: list[tuple[str, str]] = []
    started = time.perf_counter()
    for index, symbol in enumerate(MARKETS, start=1):
        market_started = time.perf_counter()
        service = XauPatternMinerService.for_symbol(symbol)
        print(f"[{index:02d}/{len(MARKETS)}] {symbol}: Maximum...", flush=True)
        try:
            state = service.calculate_maximum()
            if state.status.value != "FINISHED":
                raise RuntimeError(f"status final inesperado: {state.status.value}")
            prepared = service.prepare_adaptive_shadow(limit=12)
            print(
                f"[{index:02d}/{len(MARKETS)}] {symbol}: "
                f"{state.total_candles:,} candles, "
                f"{len(state.result.rankings) if state.result else 0} rankings, "
                f"{len(prepared)} contratos M28 Demo, "
                f"{time.perf_counter() - market_started:.1f}s",
                flush=True,
            )
        except Exception as exc:  # batch must continue and report every market
            failures.append((symbol, str(exc)))
            print(f"[{index:02d}/{len(MARKETS)}] {symbol}: FALHA - {exc}", flush=True)
        finally:
            service.release()
            del service
            gc.collect()
    print(f"Tempo total: {time.perf_counter() - started:.1f}s", flush=True)
    if failures:
        print("Falhas:", flush=True)
        for symbol, error in failures:
            print(f"- {symbol}: {error}", flush=True)
        return 1
    print("Todos os 19 ativos concluidos e preparados para M28 Demo.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
