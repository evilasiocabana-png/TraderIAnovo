"""Mine cost-aware M28 candidates without changing the active registry."""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.xau_pattern_miner_service import XauPatternMinerService
from domain.market_universe import MT5_RESEARCH_MARKETS
from replay.pattern_miner.operational import PatternPromotionValidator


MARKETS = (
    "XAUUSD",
    *(symbol for symbol in MT5_RESEARCH_MARKETS if symbol != "XAUUSD"),
)
OUTPUT_ROOT = ROOT / ".traderia" / "research" / "model28_optimizer"
CANDIDATE_REGISTRY = OUTPUT_ROOT / "candidate_patterns_v3.json"
CANDIDATE_JOURNAL = OUTPUT_ROOT / "candidate_shadow_v3.json"
SUMMARY_PATH = OUTPUT_ROOT / "optimizer_summary_v3.json"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    CANDIDATE_REGISTRY.unlink(missing_ok=True)
    CANDIDATE_JOURNAL.unlink(missing_ok=True)
    started = time.perf_counter()
    results: list[dict[str, object]] = []

    for index, symbol in enumerate(MARKETS, start=1):
        market_started = time.perf_counter()
        service = XauPatternMinerService.for_symbol(symbol)
        service.operational_store_path = CANDIDATE_REGISTRY
        service.shadow_journal_path = CANDIDATE_JOURNAL
        print(f"[{index:02d}/{len(MARKETS)}] {symbol}: Maximum v3...", flush=True)
        try:
            state = service.calculate_maximum()
            if state.status.value != "FINISHED" or state.result is None:
                raise RuntimeError(f"status final inesperado: {state.status.value}")
            validator = PatternPromotionValidator(
                minimum_occurrences=service.engine.config.operational_min_occurrences,
                minimum_split_expectancy_r=(
                    service.engine.config.operational_min_split_expectancy_r
                ),
            )
            eligible = [
                ranking
                for ranking in state.result.rankings
                if not validator.validate(ranking)
            ]
            prepared = service.prepare_adaptive_shadow(limit=12) if eligible else ()
            elapsed = time.perf_counter() - market_started
            results.append(
                {
                    "symbol": symbol,
                    "status": "OK",
                    "candles": state.total_candles,
                    "rankings": len(state.result.rankings),
                    "eligible": len(eligible),
                    "prepared": len(prepared),
                    "best_score": (
                        state.result.rankings[0].score
                        if state.result.rankings
                        else None
                    ),
                    "elapsed_seconds": round(elapsed, 3),
                }
            )
            print(
                f"[{index:02d}/{len(MARKETS)}] {symbol}: "
                f"{state.total_candles:,} candles, {len(eligible)} elegiveis, "
                f"{len(prepared)} preparados, {elapsed:.1f}s",
                flush=True,
            )
        except Exception as exc:
            results.append(
                {
                    "symbol": symbol,
                    "status": "ERROR",
                    "error": str(exc),
                    "elapsed_seconds": round(
                        time.perf_counter() - market_started,
                        3,
                    ),
                }
            )
            print(f"[{index:02d}/{len(MARKETS)}] {symbol}: FALHA - {exc}", flush=True)
        finally:
            service.release()
            del service
            gc.collect()

    payload = {
        "schema_version": "model28-cost-aware-optimizer-v3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_registry_changed": False,
        "candidate_registry": str(CANDIDATE_REGISTRY),
        "assumptions": {
            "entry": "NEXT_BAR_OPEN",
            "execution_friction_r": 0.5,
            "minimum_occurrences": 100,
            "minimum_split_expectancy_r": 0.05,
            "splits": "60_DISCOVERY_20_VALIDATION_20_OOS",
        },
        "markets": results,
        "eligible_total": sum(int(item.get("eligible", 0)) for item in results),
        "prepared_total": sum(int(item.get("prepared", 0)) for item in results),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    _write_json(SUMMARY_PATH, payload)
    print(
        f"Concluido: {payload['eligible_total']} elegiveis e "
        f"{payload['prepared_total']} candidatos isolados em "
        f"{payload['elapsed_seconds']}s.",
        flush=True,
    )
    return 1 if any(item["status"] == "ERROR" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
