"""Nested per-pair research for a robust M3 replacement.

Candidates are trained on the oldest 60 percent, selected with the following
20 percent, and evaluated once on the newest 20 percent. Nothing here changes
the operational manifest or sends orders.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from research.alpha_suggested.alpha_suggested_2_plus_individual import (
    MarketArrays,
    _evaluate_signal,
    build_signal,
    enrich_market,
    generate_candidates,
    load_markets_for_timeframe,
)


ALPHA_ID = "ALPHA_NESTED_ROBUSTA_003"
MODEL_DESTINATION = "MODELO_3"
DEFAULT_SNAPSHOTS = {
    "M30": Path(".traderia/research/m3_alpha_sugerida_m30_20000_snapshot.json"),
    "H1": Path(".traderia/research/alpha_sugerida_h1_20000_snapshot.json"),
}
ALLOWED_FAMILIES = {
    "TREND_PULLBACK_CONTINUATION",
    "MOMENTUM_ACCELERATION",
    "BREAKOUT_EXPANSION",
    "SQUEEZE_RELEASE",
    "MEAN_REVERSION_REJECTION",
    "LIQUIDITY_RECLAIM",
    "STRUCTURE_CONTINUATION",
}


def _windows(count: int) -> dict[str, Any]:
    train_end = int(count * 0.60)
    validation_end = int(count * 0.80)
    block = train_end // 3
    return {
        "train": (0, train_end),
        "blocks": (
            (0, block),
            (block, block * 2),
            (block * 2, train_end),
        ),
        "validation": (train_end, validation_end),
        "holdout": (validation_end, count),
        "full": (0, count),
    }


def _finite(value: Any) -> float:
    number = float(value or 0.0)
    return number if np.isfinite(number) else 10.0


def _train_score(metrics: dict[str, Any]) -> float:
    return (
        min(_finite(metrics["profit_factor"]), 3.0) * 35.0
        + min(int(metrics["sample_size"]), 300) / 12.0
        + min(float(metrics["recovery_factor"]), 5.0) * 3.0
    )


def _selection_score(
    train: dict[str, Any],
    validation: dict[str, Any],
    blocks: list[dict[str, Any]],
) -> float:
    block_pfs = [min(_finite(row["profit_factor"]), 3.0) for row in blocks]
    return (
        _train_score(train)
        + min(_finite(validation["profit_factor"]), 3.0) * 45.0
        + min(float(np.median(block_pfs)), 3.0) * 15.0
        + sum(float(row["expectancy"]) > 0 for row in blocks) * 6.0
        + min(int(validation["sample_size"]), 100) / 4.0
    )


def _train_allowed(metrics: dict[str, Any]) -> bool:
    return (
        int(metrics["sample_size"]) >= 55
        and float(metrics["profit_factor"]) >= 1.05
        and float(metrics["expectancy"]) > 0
        and float(metrics["max_drawdown"]) <= 0.20
    )


def _validation_allowed(
    validation: dict[str, Any],
    stress_validation: dict[str, Any],
    blocks: list[dict[str, Any]],
) -> bool:
    populated = [row for row in blocks if int(row["sample_size"]) >= 12]
    return (
        int(validation["sample_size"]) >= 15
        and float(validation["profit_factor"]) >= 1.05
        and float(validation["expectancy"]) > 0
        and float(stress_validation["profit_factor"]) >= 0.95
        and len(populated) == 3
        and sum(float(row["expectancy"]) > 0 for row in populated) >= 2
        and min(float(row["profit_factor"]) for row in populated) >= 0.75
    )


def _search_pair_timeframe(
    pair: str,
    timeframe: str,
    market: MarketArrays,
    candidates: list[dict[str, Any]],
    *,
    shortlist_size: int,
    cost_fraction: float,
    stress_cost_fraction: float,
) -> dict[str, Any] | None:
    windows = _windows(len(market.close))
    provisional: list[dict[str, Any]] = []
    for candidate in candidates:
        if str(candidate.get("family")) not in ALLOWED_FAMILIES:
            continue
        signal = build_signal(market, candidate)
        train = _evaluate_signal(
            market,
            signal,
            candidate,
            windows["train"],
            cost_fraction,
        )
        if _train_allowed(train):
            provisional.append(
                {
                    "parameters": candidate,
                    "train": train,
                    "train_score": _train_score(train),
                }
            )
    provisional.sort(key=lambda row: float(row["train_score"]), reverse=True)

    ranked: list[dict[str, Any]] = []
    for row in provisional[: max(shortlist_size, 1)]:
        candidate = row["parameters"]
        signal = build_signal(market, candidate)
        blocks = [
            _evaluate_signal(market, signal, candidate, bounds, cost_fraction)
            for bounds in windows["blocks"]
        ]
        validation = _evaluate_signal(
            market,
            signal,
            candidate,
            windows["validation"],
            cost_fraction,
        )
        stress_validation = _evaluate_signal(
            market,
            signal,
            candidate,
            windows["validation"],
            stress_cost_fraction,
        )
        if not _validation_allowed(validation, stress_validation, blocks):
            continue
        ranked.append(
            {
                **row,
                "timeframe": timeframe,
                "stability_blocks": blocks,
                "validation": validation,
                "stress_validation": stress_validation,
                "selection_score": _selection_score(
                    row["train"],
                    validation,
                    blocks,
                ),
            }
        )
    ranked.sort(key=lambda row: float(row["selection_score"]), reverse=True)
    if not ranked:
        return None
    winner = ranked[0]
    winner["development_survivors"] = len(provisional)
    winner["validation_survivors"] = len(ranked)
    return winner


def _finalize_pair(
    pair: str,
    market: MarketArrays,
    frozen: dict[str, Any],
    *,
    cost_fraction: float,
    stress_cost_fraction: float,
) -> dict[str, Any]:
    windows = _windows(len(market.close))
    candidate = frozen["parameters"]
    signal = build_signal(market, candidate)
    holdout = _evaluate_signal(
        market,
        signal,
        candidate,
        windows["holdout"],
        cost_fraction,
    )
    stress_holdout = _evaluate_signal(
        market,
        signal,
        candidate,
        windows["holdout"],
        stress_cost_fraction,
    )
    full = _evaluate_signal(
        market,
        signal,
        candidate,
        windows["full"],
        cost_fraction,
    )
    reasons: list[str] = []
    checks = (
        (int(full["sample_size"]) >= 100, "Amostra total abaixo de 100 trades."),
        (int(holdout["sample_size"]) >= 15, "Holdout abaixo de 15 trades."),
        (float(holdout["profit_factor"]) >= 1.10, "PF do holdout abaixo de 1.10."),
        (float(holdout["expectancy"]) > 0, "Expectancy do holdout nao positiva."),
        (float(stress_holdout["profit_factor"]) >= 1.00, "PF estressado abaixo de 1.00."),
        (float(full["profit_factor"]) >= 1.20, "PF total abaixo de 1.20."),
        (float(full["max_drawdown"]) <= 0.15, "Drawdown total acima de 15%."),
    )
    reasons.extend(message for passed, message in checks if not passed)
    qualified = not reasons
    return {
        "pair": pair,
        "model": MODEL_DESTINATION,
        "alpha_id": f"{ALPHA_ID}_{pair}",
        "selected_timeframe": frozen["timeframe"],
        "selection_status": (
            "QUALIFIED_FOR_DEMO_REPLAY" if qualified else "RESEARCH_REJECTED"
        ),
        "operational": False,
        "qualification_reasons": reasons,
        "winner": {
            "selection_score": frozen["selection_score"],
            "parameters": candidate,
            "development": frozen["train"],
            "stability_blocks": frozen["stability_blocks"],
            "validation": frozen["validation"],
            "stress_validation": frozen["stress_validation"],
            "holdout": holdout,
            "stress_holdout": stress_holdout,
            "full_sample": full,
        },
    }


def research_nested_pairs(
    snapshots: dict[str, Path],
    *,
    candidate_count: int = 1_200,
    shortlist_size: int = 80,
    seed: int = 20260729,
    round_trip_cost_bps: float = 1.5,
    stress_round_trip_cost_bps: float = 2.5,
    requested_pairs: list[str] | None = None,
) -> dict[str, Any]:
    cost_fraction = round_trip_cost_bps / 10_000.0
    stress_cost_fraction = stress_round_trip_cost_bps / 10_000.0
    markets_by_timeframe = {
        timeframe: {
            pair: enrich_market(market)
            for pair, market in load_markets_for_timeframe(path, timeframe).items()
        }
        for timeframe, path in snapshots.items()
    }
    available_pairs = set.intersection(
        *(set(rows) for rows in markets_by_timeframe.values())
    )
    requested = {
        str(pair).strip().upper()
        for pair in (requested_pairs or available_pairs)
        if str(pair).strip()
    }
    pairs = sorted(available_pairs.intersection(requested))
    if not pairs:
        raise RuntimeError("No requested pairs were found in both snapshots.")
    results: dict[str, Any] = {}

    for pair in pairs:
        pair_seed = seed + sum((index + 1) * ord(char) for index, char in enumerate(pair))
        candidates = generate_candidates(candidate_count, pair_seed)
        finalists = [
            finalist
            for timeframe, markets in markets_by_timeframe.items()
            if (
                finalist := _search_pair_timeframe(
                    pair,
                    timeframe,
                    markets[pair],
                    candidates,
                    shortlist_size=shortlist_size,
                    cost_fraction=cost_fraction,
                    stress_cost_fraction=stress_cost_fraction,
                )
            )
            is not None
        ]
        finalists.sort(key=lambda row: float(row["selection_score"]), reverse=True)
        if not finalists:
            results[pair] = {
                "pair": pair,
                "model": MODEL_DESTINATION,
                "alpha_id": f"{ALPHA_ID}_{pair}",
                "selection_status": "NO_TRAIN_VALIDATION_SURVIVOR",
                "operational": False,
                "winner": None,
            }
        else:
            frozen = finalists[0]
            results[pair] = _finalize_pair(
                pair,
                markets_by_timeframe[frozen["timeframe"]][pair],
                frozen,
                cost_fraction=cost_fraction,
                stress_cost_fraction=stress_cost_fraction,
            )
        winner = results[pair].get("winner") or {}
        print(
            json.dumps(
                {
                    "pair": pair,
                    "status": results[pair]["selection_status"],
                    "timeframe": results[pair].get("selected_timeframe"),
                    "family": (winner.get("parameters") or {}).get("family"),
                    "holdout_pf": (winner.get("holdout") or {}).get("profit_factor"),
                }
            ),
            flush=True,
        )

    qualified_pairs = [
        pair
        for pair, result in results.items()
        if result["selection_status"] == "QUALIFIED_FOR_DEMO_REPLAY"
    ]
    return {
        "schema_version": "1.0",
        "alpha_id": ALPHA_ID,
        "model_destination": MODEL_DESTINATION,
        "status": "NESTED_RESEARCH_COMPLETE",
        "operational": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "TRAIN_60_VALIDATION_20_FINAL_HOLDOUT_20",
        "candidate_count_per_pair": candidate_count,
        "timeframes_compared": list(snapshots),
        "qualified_pairs": qualified_pairs,
        "results": results,
        "guardrails": {
            "final_holdout_opened_after_pair_candidate_and_timeframe_frozen": True,
            "real_account_authorized": False,
            "operational_manifest_changed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-count", type=int, default=1_200)
    parser.add_argument("--shortlist-size", type=int, default=80)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--pairs", nargs="*")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".traderia/research/m3_nested_robusta_003.json"),
    )
    args = parser.parse_args()
    payload = research_nested_pairs(
        DEFAULT_SNAPSHOTS,
        candidate_count=args.candidate_count,
        shortlist_size=args.shortlist_size,
        seed=args.seed,
        requested_pairs=args.pairs,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "qualified": payload["qualified_pairs"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
