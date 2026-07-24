"""Consolidate the best observed M3 research candidate for each Forex pair.

This module never promotes a candidate to the operational runtime. It compares
finished, read-only research artifacts and keeps the source evidence intact so
the Lab can present one auditable M3 row per pair.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_INPUTS = (
    Path(".traderia/research/m3_alpha_sugerida_2_plus_individual_h1_20000.json"),
    Path(".traderia/research/m3_alpha_sugerida_2_plus_individual_m30_20000.json"),
    Path(".traderia/research/m3_alpha_sugerida_2_plus_individual_h4_10000.json"),
)
DEFAULT_OUTPUT = Path(
    ".traderia/research/m3_alpha_sugerida_2_plus_best_by_pair.json"
)


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _winner_metrics(result: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    winner = result.get("winner", {})
    if not isinstance(winner, dict):
        winner = {}
    metric_names = ("full_sample", "holdout", "stress_holdout")
    metrics: list[dict[str, Any]] = []
    for name in metric_names:
        value = winner.get(name, {})
        metrics.append(value if isinstance(value, dict) else {})
    return tuple(metrics)


def replay_candidate_reasons(result: dict[str, Any]) -> list[str]:
    """Return unmet gates for the non-operational M3 Replay shortlist."""
    full, holdout, stress_holdout = _winner_metrics(result)
    winner = result.get("winner", {})
    if not isinstance(winner, dict):
        winner = {}
    blocks = winner.get("stability_blocks", [])
    if not isinstance(blocks, list):
        blocks = []
    positive_blocks = sum(
        1
        for block in blocks
        if isinstance(block, dict) and _number(block.get("net_return")) > 0
    )

    reasons: list[str] = []
    if int(_number(full.get("sample_size"))) < 100:
        reasons.append("Amostra total abaixo de 100 trades para Replay.")
    if _number(full.get("profit_factor")) < 1.30:
        reasons.append("PF total abaixo de 1,30.")
    if _number(holdout.get("profit_factor")) < 1.15:
        reasons.append("PF do holdout abaixo de 1,15.")
    if _number(stress_holdout.get("profit_factor")) < 1.00:
        reasons.append("PF do holdout estressado abaixo de 1,00.")
    if _number(full.get("expectancy")) <= 0:
        reasons.append("Expectancia total nao positiva.")
    if _number(holdout.get("expectancy")) <= 0:
        reasons.append("Expectancia do holdout nao positiva.")
    if _number(full.get("max_drawdown"), 1.0) > 0.15:
        reasons.append("Drawdown total acima de 15%.")
    if positive_blocks < 3:
        reasons.append("Menos de tres blocos cronologicos positivos.")
    return reasons


def candidate_status(result: dict[str, Any]) -> tuple[str, int, list[str]]:
    """Classify a result without granting permission to trade."""
    if bool(result.get("qualified", False)):
        return "APROVADA_B_PARA_REPLAY", 3, []
    reasons = replay_candidate_reasons(result)
    if not reasons:
        return "PROMISSORA_PARA_REPLAY", 2, []
    return "REJEITADA_NAO_ATIVA", 1, reasons


def candidate_rank(result: dict[str, Any]) -> tuple[float, ...]:
    """Favor certification first, then the weakest out-of-sample PF."""
    status, tier, _ = candidate_status(result)
    del status
    full, holdout, stress_holdout = _winner_metrics(result)
    conservative_pf = min(
        _number(full.get("profit_factor")),
        _number(holdout.get("profit_factor")),
        _number(stress_holdout.get("profit_factor")),
    )
    return (
        float(tier),
        conservative_pf,
        _number(full.get("ict_score")),
        _number(full.get("sample_size")),
        -_number(full.get("max_drawdown"), 1.0),
    )


def select_best_by_pair(
    artifacts: Iterable[tuple[Path, dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Choose one best-observed candidate per pair across timeframe artifacts."""
    selected: dict[str, dict[str, Any]] = {}
    for source_path, payload in artifacts:
        timeframe = str(payload.get("timeframe") or "N/D").upper()
        results = payload.get("results", {})
        if not isinstance(results, dict):
            continue
        for pair, raw_result in results.items():
            if not isinstance(raw_result, dict):
                continue
            pair_name = str(pair).upper()
            current = selected.get(pair_name)
            if current is not None and candidate_rank(current["result"]) >= candidate_rank(
                raw_result
            ):
                continue
            selected[pair_name] = {
                "source_path": source_path,
                "source_timeframe": timeframe,
                "source_generated_at": payload.get("generated_at"),
                "result": raw_result,
            }
    return selected


def build_consolidated_payload(
    artifacts: Iterable[tuple[Path, dict[str, Any]]],
) -> dict[str, Any]:
    artifact_list = list(artifacts)
    selected = select_best_by_pair(artifact_list)
    results: dict[str, dict[str, Any]] = {}
    for pair, item in sorted(selected.items()):
        result = item["result"]
        status, tier, replay_reasons = candidate_status(result)
        winner = result.get("winner", {})
        if not isinstance(winner, dict):
            winner = {}
        results[pair] = {
            "pair": pair,
            "model": "MODELO_3",
            "alpha_id": result.get("alpha_id")
            or f"ALPHA_SUGERIDA_002_PLUS_{pair}",
            "selected_timeframe": item["source_timeframe"],
            "selection_status": status,
            "selection_tier": tier,
            "operational": False,
            "source_artifact": item["source_path"].as_posix(),
            "source_generated_at": item["source_generated_at"],
            "research_qualification_reasons": result.get(
                "qualification_reasons", []
            ),
            "replay_shortlist_reasons": replay_reasons,
            "winner": winner,
        }

    timeframes = sorted(
        {
            str(payload.get("timeframe") or "N/D").upper()
            for _, payload in artifact_list
        }
    )
    return {
        "schema_version": "1.0",
        "alpha_id": "ALPHA_SUGERIDA_002_PLUS_INDIVIDUAL",
        "status": "M3_BEST_OBSERVED_BY_PAIR",
        "model_destination": "MODELO_3",
        "operational": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timeframes_evaluated": timeframes,
        "selection_rule": (
            "certificacao; pior PF entre total/holdout/holdout estressado; "
            "ICT; amostra; menor drawdown"
        ),
        "cost_contract": {
            "round_trip_bps": 1.5,
            "stress_round_trip_bps": 2.5,
            "note": "Custo padronizado de pesquisa, nao spread historico dinamico.",
        },
        "promotion_guardrail": (
            "O consolidado pertence ao M3 de pesquisa, mas nao autoriza ordens. "
            "A escolha entre timeframes exige Replay/forward Demo antes de promocao."
        ),
        "source_artifacts": [path.as_posix() for path, _ in artifact_list],
        "results": results,
    }


def load_artifacts(paths: Iterable[Path]) -> list[tuple[Path, dict[str, Any]]]:
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid research artifact: {path}")
        loaded.append((path, payload))
    return loaded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs",
        nargs="+",
        type=Path,
        default=list(DEFAULT_INPUTS),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = build_consolidated_payload(load_artifacts(args.inputs))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    for pair, result in payload["results"].items():
        winner = result.get("winner", {})
        full = winner.get("full_sample", {}) if isinstance(winner, dict) else {}
        holdout = winner.get("holdout", {}) if isinstance(winner, dict) else {}
        print(
            json.dumps(
                {
                    "pair": pair,
                    "timeframe": result["selected_timeframe"],
                    "status": result["selection_status"],
                    "family": winner.get("parameters", {}).get("family"),
                    "full_pf": full.get("profit_factor"),
                    "holdout_pf": holdout.get("profit_factor"),
                    "ict": full.get("ict_score"),
                },
                ensure_ascii=True,
            )
        )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "model_destination": payload["model_destination"],
                "operational": payload["operational"],
                "output": str(args.output),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
