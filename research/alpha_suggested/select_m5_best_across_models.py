"""Consolidate the best research evidence per pair across M1 through M4.

The result belongs to ``MODELO_5_PESQUISA_CONSOLIDADO``. It is deliberately
separate from the operational ``MODELO_5_PRICE_ACTION`` and cannot authorize
orders. The selector favors certification and out-of-sample robustness before
raw profit factor.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MODEL_DESTINATION = "MODELO_5_PESQUISA_CONSOLIDADO"
DEFAULT_M1_INPUT = Path(".traderia/mt5_research_snapshot.json")
DEFAULT_M2_INPUT = Path(
    ".traderia/research/alpha_sugerida_1_plus_session_regime_h1_20000.json"
)
DEFAULT_M3_INPUT = Path(
    ".traderia/research/m3_alpha_sugerida_2_plus_best_by_pair.json"
)
DEFAULT_M4_INPUT = Path(
    ".traderia/research/modelo_4_pesquisa_contextual_mtf.json"
)
DEFAULT_OUTPUT = Path(
    ".traderia/research/modelo_5_pesquisa_best_m1_m4.json"
)


def _number(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sample_size(metrics: dict[str, Any]) -> int:
    return int(_number(metrics.get("sample_size")))


def _metric_pf(metrics: dict[str, Any]) -> float:
    return _number(metrics.get("profit_factor"))


def _positive_expectancy(metrics: dict[str, Any]) -> bool:
    return _number(metrics.get("expectancy")) > 0.0


def _candidate(
    *,
    pair: str,
    source_model: str,
    alpha_id: object,
    timeframe: object,
    source_status: object,
    tier: int,
    parameters: object,
    full_sample: object,
    validation: object = None,
    holdout: object = None,
    stress_holdout: object = None,
    context_overlay: object = None,
    source_artifact: str,
    evidence_note: str,
) -> dict[str, Any]:
    full = _mapping(full_sample)
    validation_metrics = _mapping(validation)
    holdout_metrics = _mapping(holdout)
    stress_metrics = _mapping(stress_holdout)
    return {
        "pair": pair.upper(),
        "source_model": source_model,
        "alpha_id": str(alpha_id or "N/D"),
        "timeframe": str(timeframe or "N/D").upper(),
        "source_status": str(source_status or "N/D"),
        "selection_tier": int(tier),
        "parameters": _mapping(parameters),
        "context_overlay": _mapping(context_overlay),
        "full_sample": full,
        "validation": validation_metrics,
        "holdout": holdout_metrics,
        "stress_holdout": stress_metrics,
        "source_artifact": source_artifact,
        "evidence_note": evidence_note,
    }


def normalize_m1(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Adapt the operational Lab snapshot to the research comparison schema."""
    status_tiers = {
        "CERTIFICADA_B": 4,
        "PESQUISA_REPLAY": 3,
        "HIPOTESE_PROMISSORA": 2,
    }
    candidates: list[dict[str, Any]] = []
    scenarios = payload.get("best_scenarios_by_market", [])
    if not isinstance(scenarios, list):
        return candidates
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        pair = str(scenario.get("pair") or "").upper()
        if not pair:
            continue
        status = str(scenario.get("ict_status") or "REJEITADA").upper()
        full = {
            "sample_size": int(
                _number(scenario.get("lab_confidence_sample_size"))
            ),
            "win_rate": _number(scenario.get("lab_confidence")),
            "profit_factor": _number(
                scenario.get("lab_confidence_profit_factor")
            ),
            "expectancy": _number(
                scenario.get("lab_confidence_expectancy")
            ),
            "max_drawdown": _number(
                scenario.get("lab_confidence_max_drawdown")
            ),
            "ict_score": _number(scenario.get("ict_score")),
            "ict_grade": str(scenario.get("ict_grade") or "N/D"),
        }
        candidates.append(
            _candidate(
                pair=pair,
                source_model="M1",
                alpha_id=scenario.get("alpha_id"),
                timeframe=scenario.get("timeframe"),
                source_status=status,
                tier=status_tiers.get(status, 0),
                parameters=scenario.get("parameters"),
                full_sample=full,
                source_artifact=DEFAULT_M1_INPUT.as_posix(),
                evidence_note=(
                    "Lab original; nao possui holdout comparavel aos modelos "
                    "de pesquisa M2-M4."
                ),
            )
        )
    return candidates


def _m2_tier(candidate: dict[str, Any]) -> int:
    if bool(candidate.get("qualified", False)):
        return 4
    full = _mapping(candidate.get("full", candidate.get("full_sample")))
    validation = _mapping(candidate.get("validation"))
    holdout = _mapping(candidate.get("holdout"))
    robust = (
        _sample_size(full) >= 100
        and _metric_pf(full) >= 1.30
        and _sample_size(validation) >= 15
        and _metric_pf(validation) >= 1.10
        and _sample_size(holdout) >= 20
        and _metric_pf(holdout) >= 1.15
        and _positive_expectancy(full)
        and _positive_expectancy(holdout)
    )
    if robust:
        return 3
    partial = (
        _sample_size(full) >= 100
        and _sample_size(holdout) >= 20
        and _metric_pf(full) > 1.0
        and _metric_pf(holdout) > 1.0
        and _positive_expectancy(holdout)
    )
    return 2 if partial else 0


def normalize_m2(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    results = payload.get("results", {})
    if not isinstance(results, dict):
        return candidates
    for pair, raw_candidates in results.items():
        if not isinstance(raw_candidates, list) or not raw_candidates:
            continue
        raw = raw_candidates[0]
        if not isinstance(raw, dict):
            continue
        tier = _m2_tier(raw)
        candidates.append(
            _candidate(
                pair=str(pair),
                source_model="M2",
                alpha_id=payload.get("alpha_id") or "ALPHA_SUGERIDA_001_PLUS",
                timeframe=payload.get("timeframe") or "H1",
                source_status=(
                    "QUALIFIED"
                    if bool(raw.get("qualified", False))
                    else ("PROMISSORA" if tier >= 2 else "REJEITADA")
                ),
                tier=tier,
                parameters=raw.get("parameters"),
                full_sample=raw.get("full", raw.get("full_sample")),
                validation=raw.get("validation"),
                holdout=raw.get("holdout"),
                stress_holdout=raw.get("stress_holdout"),
                source_artifact=DEFAULT_M2_INPUT.as_posix(),
                evidence_note="Pesquisa H1 com validacao e holdout cronologicos.",
            )
        )
    return candidates


def normalize_m3(payload: dict[str, Any]) -> list[dict[str, Any]]:
    status_tiers = {
        "APROVADA_B_PARA_REPLAY": 4,
        "PROMISSORA_PARA_REPLAY": 3,
    }
    candidates: list[dict[str, Any]] = []
    results = payload.get("results", {})
    if not isinstance(results, dict):
        return candidates
    for pair, result in results.items():
        if not isinstance(result, dict):
            continue
        winner = _mapping(result.get("winner"))
        status = str(
            result.get("selection_status") or "REJEITADA_NAO_ATIVA"
        ).upper()
        candidates.append(
            _candidate(
                pair=str(pair),
                source_model="M3",
                alpha_id=result.get("alpha_id"),
                timeframe=result.get("selected_timeframe"),
                source_status=status,
                tier=status_tiers.get(status, 0),
                parameters=winner.get("parameters"),
                full_sample=winner.get("full_sample"),
                validation=winner.get("validation"),
                holdout=winner.get("holdout"),
                stress_holdout=winner.get("stress_holdout"),
                source_artifact=DEFAULT_M3_INPUT.as_posix(),
                evidence_note=(
                    "Melhor timeframe por par com custos, holdout e estresse."
                ),
            )
        )
    return candidates


def _m4_tier(result: dict[str, Any], winner: dict[str, Any]) -> int:
    if bool(result.get("qualified", False)):
        return 4
    full = _mapping(winner.get("full_sample"))
    validation = _mapping(winner.get("validation"))
    holdout = _mapping(winner.get("holdout"))
    stress = _mapping(winner.get("stress_holdout"))
    promising = (
        _sample_size(full) >= 70
        and _sample_size(validation) >= 10
        and _sample_size(holdout) >= 10
        and _metric_pf(full) >= 1.30
        and _metric_pf(validation) >= 1.15
        and _metric_pf(holdout) >= 1.15
        and _metric_pf(stress) >= 1.05
        and _positive_expectancy(holdout)
    )
    return 2 if promising else 0


def normalize_m4(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    results = payload.get("results", {})
    if not isinstance(results, dict):
        return candidates
    for pair, result in results.items():
        if not isinstance(result, dict):
            continue
        winner = _mapping(result.get("winner"))
        tier = _m4_tier(result, winner)
        candidates.append(
            _candidate(
                pair=str(pair),
                source_model="M4-P",
                alpha_id=result.get("alpha_id"),
                timeframe="M30",
                source_status=(
                    "QUALIFIED"
                    if bool(result.get("qualified", False))
                    else (
                        "PROMISSORA_AMOSTRA_INSUFICIENTE"
                        if tier == 2
                        else "REJEITADA_NAO_ATIVA"
                    )
                ),
                tier=tier,
                parameters=winner.get("base_parameters"),
                context_overlay=winner.get("context_overlay"),
                full_sample=winner.get("full_sample"),
                validation=winner.get("validation"),
                holdout=winner.get("holdout"),
                stress_holdout=winner.get("stress_holdout"),
                source_artifact=DEFAULT_M4_INPUT.as_posix(),
                evidence_note=(
                    "Contexto M30/H1/H4; hipoteses com amostra curta nao sao "
                    "promovidas."
                ),
            )
        )
    return candidates


def candidate_rank(candidate: dict[str, Any]) -> tuple[float, ...]:
    """Rank certification and robustness before in-sample performance."""
    full = _mapping(candidate.get("full_sample"))
    validation = _mapping(candidate.get("validation"))
    holdout = _mapping(candidate.get("holdout"))
    stress = _mapping(candidate.get("stress_holdout"))
    holdout_n = _sample_size(holdout)
    has_stress = 1.0 if _sample_size(stress) > 0 else 0.0
    holdout_coverage = min(holdout_n / 20.0, 1.0)
    pf_values = [_metric_pf(full)]
    for metrics in (validation, holdout, stress):
        if _sample_size(metrics) > 0:
            pf_values.append(_metric_pf(metrics))
    conservative_pf = min(pf_values) if pf_values else 0.0
    return (
        float(candidate.get("selection_tier", 0) or 0),
        has_stress,
        holdout_coverage,
        conservative_pf,
        _number(full.get("ict_score")),
        float(_sample_size(full)),
        -_number(full.get("max_drawdown"), 1.0),
    )


def select_best_by_pair(
    candidates: Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        pair = str(candidate.get("pair") or "").upper()
        if not pair:
            continue
        current = selected.get(pair)
        if current is None or candidate_rank(candidate) > candidate_rank(current):
            selected[pair] = candidate
    return selected


def _selection_status(tier: int) -> str:
    if tier >= 4:
        return "APROVADA_B_PARA_REPLAY"
    if tier == 3:
        return "PROMISSORA_PARA_REPLAY"
    if tier == 2:
        return "HIPOTESE_PENDENTE_DE_VALIDACAO"
    return "SEM_CANDIDATA_ROBUSTA"


def _selection_reason(winner: dict[str, Any]) -> str:
    full = _mapping(winner.get("full_sample"))
    holdout = _mapping(winner.get("holdout"))
    stress = _mapping(winner.get("stress_holdout"))
    pieces = [
        f"nivel {int(winner.get('selection_tier', 0) or 0)}",
        f"PF total {_metric_pf(full):.3f}",
    ]
    if _sample_size(holdout) > 0:
        pieces.append(
            f"holdout {_sample_size(holdout)} / PF {_metric_pf(holdout):.3f}"
        )
    else:
        pieces.append("sem holdout comparavel")
    if _sample_size(stress) > 0:
        pieces.append(f"PF estresse {_metric_pf(stress):.3f}")
    return "; ".join(pieces)


def build_consolidated_payload(
    m1_payload: dict[str, Any],
    m2_payload: dict[str, Any],
    m3_payload: dict[str, Any],
    m4_payload: dict[str, Any],
) -> dict[str, Any]:
    candidates = [
        *normalize_m1(m1_payload),
        *normalize_m2(m2_payload),
        *normalize_m3(m3_payload),
        *normalize_m4(m4_payload),
    ]
    winners = select_best_by_pair(candidates)
    by_pair: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_pair.setdefault(candidate["pair"], []).append(candidate)

    results: dict[str, dict[str, Any]] = {}
    for pair, winner in sorted(winners.items()):
        tier = int(winner.get("selection_tier", 0) or 0)
        results[pair] = {
            "pair": pair,
            "model": "M5-P",
            "model_destination": MODEL_DESTINATION,
            "operational": False,
            "selection_status": _selection_status(tier),
            "selection_reason": _selection_reason(winner),
            "winner": winner,
            "compared_candidates": sorted(
                by_pair.get(pair, []),
                key=candidate_rank,
                reverse=True,
            ),
        }

    return {
        "schema_version": "1.0",
        "status": "M5_BEST_RESEARCH_EVIDENCE_BY_PAIR",
        "model_destination": MODEL_DESTINATION,
        "operational": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_models": ["M1", "M2", "M3", "M4-P"],
        "selection_rule": (
            "certificacao; presenca de estresse; cobertura holdout; pior PF "
            "observado; ICT; amostra; menor drawdown"
        ),
        "promotion_guardrail": (
            "M5-P e uma tabela de pesquisa. Nao substitui MODELO_5_PRICE_ACTION, "
            "nao alimenta Trade Plan e nao autoriza ordens."
        ),
        "source_artifacts": [
            DEFAULT_M1_INPUT.as_posix(),
            DEFAULT_M2_INPUT.as_posix(),
            DEFAULT_M3_INPUT.as_posix(),
            DEFAULT_M4_INPUT.as_posix(),
        ],
        "results": results,
    }


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid research artifact: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m1", type=Path, default=DEFAULT_M1_INPUT)
    parser.add_argument("--m2", type=Path, default=DEFAULT_M2_INPUT)
    parser.add_argument("--m3", type=Path, default=DEFAULT_M3_INPUT)
    parser.add_argument("--m4", type=Path, default=DEFAULT_M4_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = build_consolidated_payload(
        _load(args.m1),
        _load(args.m2),
        _load(args.m3),
        _load(args.m4),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    for pair, result in payload["results"].items():
        winner = result["winner"]
        print(
            json.dumps(
                {
                    "pair": pair,
                    "source_model": winner["source_model"],
                    "alpha_id": winner["alpha_id"],
                    "timeframe": winner["timeframe"],
                    "status": result["selection_status"],
                    "reason": result["selection_reason"],
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
