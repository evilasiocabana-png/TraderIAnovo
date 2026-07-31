"""Research one robust global setup before promoting a replacement for M3.

The search uses development data only for candidate and timeframe selection.
The newest 20 percent is opened once, after the global winner is frozen.
This module never changes the operational manifest or sends MT5 orders.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from research.alpha_suggested.alpha_suggested_2_plus_individual import (
    MarketArrays,
    build_signal,
    chronological_research_windows,
    enrich_market,
    generate_candidates,
    load_markets_for_timeframe,
    replay_segment,
    summarize_outcomes,
)


ALPHA_ID = "ALPHA_GLOBAL_ROBUSTA_003"
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
    "STRUCTURE_CONTINUATION",
}


def _finite(value: Any) -> float:
    number = float(value or 0.0)
    return number if np.isfinite(number) else 10.0


def _market_outcomes(
    market: MarketArrays,
    candidate: dict[str, Any],
    bounds: tuple[int, int],
    cost_fraction: float,
) -> list[dict[str, float]]:
    return replay_segment(
        market,
        build_signal(market, candidate),
        bounds,
        stop_factor=float(candidate["stop_factor"]),
        risk_reward=float(candidate["risk_reward"]),
        round_trip_cost_fraction=cost_fraction,
    )


def _evaluate_portfolio(
    markets: dict[str, MarketArrays],
    candidate: dict[str, Any],
    bounds: tuple[int, int],
    cost_fraction: float,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    combined: list[dict[str, float]] = []
    by_pair: dict[str, dict[str, Any]] = {}
    for pair, market in sorted(markets.items()):
        outcomes = _market_outcomes(market, candidate, bounds, cost_fraction)
        combined.extend(outcomes)
        by_pair[pair] = summarize_outcomes(outcomes)
    return summarize_outcomes(combined), by_pair


def _candidate_score(
    development: dict[str, Any],
    by_pair: dict[str, dict[str, Any]],
) -> float:
    positive_pairs = sum(
        int(metrics["sample_size"]) >= 12 and float(metrics["expectancy"]) > 0
        for metrics in by_pair.values()
    )
    return (
        min(_finite(development["profit_factor"]), 3.0) * 30.0
        + positive_pairs * 9.0
        + min(int(development["sample_size"]), 1_200) / 35.0
        + min(float(development["recovery_factor"]), 5.0) * 2.0
    )


def _candidate_allowed(
    development: dict[str, Any],
    by_pair: dict[str, dict[str, Any]],
) -> bool:
    populated = [
        metrics
        for metrics in by_pair.values()
        if int(metrics["sample_size"]) >= 12
    ]
    positive_pairs = sum(float(metrics["expectancy"]) > 0 for metrics in populated)
    return (
        int(development["sample_size"]) >= 350
        and float(development["profit_factor"]) >= 1.05
        and float(development["expectancy"]) > 0
        and len(populated) >= 6
        and positive_pairs >= 5
    )


def _rank_timeframe(
    timeframe: str,
    markets: dict[str, MarketArrays],
    candidates: Iterable[dict[str, Any]],
    *,
    cost_fraction: float,
    shortlist_size: int,
) -> list[dict[str, Any]]:
    candle_count = min(len(market.close) for market in markets.values())
    windows = chronological_research_windows(candle_count)
    provisional: list[dict[str, Any]] = []
    for candidate in candidates:
        if str(candidate.get("family")) not in ALLOWED_FAMILIES:
            continue
        development, by_pair = _evaluate_portfolio(
            markets,
            candidate,
            windows.development,
            cost_fraction,
        )
        if not _candidate_allowed(development, by_pair):
            continue
        provisional.append(
            {
                "timeframe": timeframe,
                "parameters": candidate,
                "development": development,
                "development_by_pair": by_pair,
                "preliminary_score": _candidate_score(development, by_pair),
            }
        )
    provisional.sort(
        key=lambda row: float(row["preliminary_score"]),
        reverse=True,
    )

    ranked: list[dict[str, Any]] = []
    for row in provisional[: max(shortlist_size, 1)]:
        blocks = [
            _evaluate_portfolio(
                markets,
                row["parameters"],
                bounds,
                cost_fraction,
            )[0]
            for bounds in windows.stability_blocks
        ]
        populated = [block for block in blocks if int(block["sample_size"]) >= 50]
        positive_blocks = sum(float(block["expectancy"]) > 0 for block in populated)
        if len(populated) < 4 or positive_blocks < 3:
            continue
        if min(float(block["profit_factor"]) for block in populated) < 0.85:
            continue
        median_pf = float(
            np.median([min(_finite(block["profit_factor"]), 3.0) for block in populated])
        )
        minimum_pf = min(float(block["profit_factor"]) for block in populated)
        ranked.append(
            {
                **row,
                "stability_blocks": blocks,
                "positive_stability_blocks": positive_blocks,
                "selection_score": (
                    float(row["preliminary_score"])
                    + median_pf * 20.0
                    + minimum_pf * 10.0
                    + positive_blocks * 5.0
                ),
            }
        )
    ranked.sort(key=lambda row: float(row["selection_score"]), reverse=True)
    return ranked


def research_global_setup(
    snapshots: dict[str, Path],
    *,
    candidate_count: int = 1_500,
    shortlist_size: int = 80,
    seed: int = 20260729,
    round_trip_cost_bps: float = 1.5,
    stress_round_trip_cost_bps: float = 2.5,
) -> dict[str, Any]:
    cost_fraction = float(round_trip_cost_bps) / 10_000.0
    stress_cost_fraction = float(stress_round_trip_cost_bps) / 10_000.0
    candidates = generate_candidates(candidate_count, seed)
    ranked_by_timeframe: dict[str, list[dict[str, Any]]] = {}
    markets_by_timeframe: dict[str, dict[str, MarketArrays]] = {}

    for timeframe, snapshot_path in snapshots.items():
        markets = {
            pair: enrich_market(market)
            for pair, market in load_markets_for_timeframe(
                snapshot_path,
                timeframe,
            ).items()
        }
        markets_by_timeframe[timeframe] = markets
        ranked_by_timeframe[timeframe] = _rank_timeframe(
            timeframe,
            markets,
            candidates,
            cost_fraction=cost_fraction,
            shortlist_size=shortlist_size,
        )
        print(
            json.dumps(
                {
                    "timeframe": timeframe,
                    "development_survivors": len(ranked_by_timeframe[timeframe]),
                    "best_development_score": (
                        ranked_by_timeframe[timeframe][0]["selection_score"]
                        if ranked_by_timeframe[timeframe]
                        else None
                    ),
                }
            ),
            flush=True,
        )

    finalists = [
        rows[0]
        for rows in ranked_by_timeframe.values()
        if rows
    ]
    finalists.sort(key=lambda row: float(row["selection_score"]), reverse=True)
    if not finalists:
        return {
            "schema_version": "1.0",
            "alpha_id": ALPHA_ID,
            "model_destination": MODEL_DESTINATION,
            "status": "NO_ROBUST_GLOBAL_CANDIDATE",
            "operational": False,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "candidate_count": len(candidates),
        }

    frozen = finalists[0]
    timeframe = str(frozen["timeframe"])
    markets = markets_by_timeframe[timeframe]
    candle_count = min(len(market.close) for market in markets.values())
    windows = chronological_research_windows(candle_count)
    candidate = frozen["parameters"]
    holdout, holdout_by_pair = _evaluate_portfolio(
        markets,
        candidate,
        windows.holdout,
        cost_fraction,
    )
    stress_holdout, stress_by_pair = _evaluate_portfolio(
        markets,
        candidate,
        windows.holdout,
        stress_cost_fraction,
    )
    full, full_by_pair = _evaluate_portfolio(
        markets,
        candidate,
        (0, candle_count),
        cost_fraction,
    )
    positive_holdout_pairs = sum(
        int(metrics["sample_size"]) >= 8 and float(metrics["expectancy"]) > 0
        for metrics in holdout_by_pair.values()
    )
    reasons: list[str] = []
    checks = (
        (int(frozen["development"]["sample_size"]) >= 400, "Desenvolvimento abaixo de 400 trades."),
        (float(frozen["development"]["profit_factor"]) >= 1.15, "PF de desenvolvimento abaixo de 1.15."),
        (int(holdout["sample_size"]) >= 80, "Holdout abaixo de 80 trades."),
        (float(holdout["profit_factor"]) >= 1.10, "PF de holdout abaixo de 1.10."),
        (float(holdout["expectancy"]) > 0, "Expectancy de holdout nao positiva."),
        (float(stress_holdout["profit_factor"]) >= 1.00, "PF estressado abaixo de 1.00."),
        (positive_holdout_pairs >= 5, "Menos de cinco pares positivos no holdout."),
    )
    reasons.extend(message for passed, message in checks if not passed)
    qualified = not reasons
    approved_pairs = [
        pair
        for pair, metrics in holdout_by_pair.items()
        if int(metrics["sample_size"]) >= 8
        and float(metrics["profit_factor"]) >= 1.05
        and float(metrics["expectancy"]) > 0
        and float(stress_by_pair[pair]["profit_factor"]) >= 0.95
    ]
    return {
        "schema_version": "1.0",
        "alpha_id": ALPHA_ID,
        "model_destination": MODEL_DESTINATION,
        "status": "QUALIFIED_FOR_DEMO_REPLAY" if qualified else "RESEARCH_REJECTED",
        "operational": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "ONE_GLOBAL_SETUP_SELECTED_BEFORE_FINAL_HOLDOUT",
        "candidate_count": len(candidates),
        "timeframes_compared": list(snapshots),
        "selected_timeframe": timeframe,
        "parameters": candidate,
        "development": frozen["development"],
        "development_by_pair": frozen["development_by_pair"],
        "stability_blocks": frozen["stability_blocks"],
        "holdout": holdout,
        "holdout_by_pair": holdout_by_pair,
        "stress_holdout": stress_holdout,
        "stress_holdout_by_pair": stress_by_pair,
        "full_sample": full,
        "full_sample_by_pair": full_by_pair,
        "positive_holdout_pairs": positive_holdout_pairs,
        "qualified": qualified,
        "qualification_reasons": reasons,
        "demo_replay_approved_pairs": approved_pairs if qualified else [],
        "guardrails": {
            "holdout_opened_after_global_candidate_and_timeframe_frozen": True,
            "real_account_authorized": False,
            "operational_manifest_changed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m30-snapshot", type=Path, default=DEFAULT_SNAPSHOTS["M30"])
    parser.add_argument("--h1-snapshot", type=Path, default=DEFAULT_SNAPSHOTS["H1"])
    parser.add_argument("--candidate-count", type=int, default=1_500)
    parser.add_argument("--shortlist-size", type=int, default=80)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".traderia/research/m3_global_robusta_003.json"),
    )
    args = parser.parse_args()
    payload = research_global_setup(
        {"M30": args.m30_snapshot, "H1": args.h1_snapshot},
        candidate_count=args.candidate_count,
        shortlist_size=args.shortlist_size,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "status": payload["status"]}))
    return 0 if bool(payload.get("qualified")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
