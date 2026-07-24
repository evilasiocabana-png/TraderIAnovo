"""Build the tracked Demo-forward manifest for Lab models M2 through M5.

The runtime may consume only this compact manifest. Heavy historical snapshots
remain local under ``.traderia``. M2 and M3 are replayed with an executable
contract: signal on a closed candle and entry at the following candle open.
M4 already uses that contract in its original research artifact. M5 delegates
to the selected source model instead of implementing a second signal formula.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np

from research.alpha_suggested.alpha_suggested_1_plus_discovery import (
    build_signal as build_m2_signal,
    engineer_features,
)
from research.alpha_suggested.alpha_suggested_2_plus_individual import (
    build_signal as build_m3_signal,
    enrich_market,
    summarize_outcomes,
)


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = ROOT / ".traderia" / "research"
M2_SOURCE = RESEARCH_ROOT / "alpha_sugerida_1_plus_session_regime_h1_20000.json"
M2_SNAPSHOT = RESEARCH_ROOT / "alpha_sugerida_h1_20000_snapshot.json"
M3_SOURCE = RESEARCH_ROOT / "m3_alpha_sugerida_2_plus_best_by_pair.json"
M3_SNAPSHOTS = {
    "H1": RESEARCH_ROOT / "alpha_sugerida_h1_20000_snapshot.json",
    "M30": RESEARCH_ROOT / "m3_alpha_sugerida_m30_20000_snapshot.json",
    "H4": RESEARCH_ROOT / "m3_alpha_sugerida_h4_10000_snapshot.json",
}
M4_SOURCE = RESEARCH_ROOT / "modelo_4_pesquisa_contextual_mtf.json"
M5_SOURCE = RESEARCH_ROOT / "modelo_5_pesquisa_best_m1_m4.json"
MANIFEST_PATH = (
    ROOT / "research" / "alpha_suggested" / "lab_operational_models_manifest.json"
)
POLICY_PATH = (
    ROOT / "research" / "alpha_suggested" / "lab_demo_forward_policy.json"
)
DETAIL_PATH = RESEARCH_ROOT / "lab_operational_models_parity.json"

MODEL_IDS = {
    "M2": "MODELO_2_LAB_ALPHA_SUGERIDA_1_PLUS",
    "M3": "MODELO_3_LAB_ALPHA_SUGERIDA_2_PLUS",
    "M4": "MODELO_4_LAB_CONTEXTUAL_MTF",
    "M5": "MODELO_5_LAB_CONSOLIDADO",
}
FIXED_EXIT_POLICY = "RESEARCH_FIXED_SL_TP"
MINIMUM_DISTANCE_PERCENT = 0.0005
BASE_COST_BPS = 1.5
STRESS_COST_BPS = 2.5


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object expected: {path}")
    return payload


def _snapshot_candles(path: Path, pair: str, timeframe: str) -> list[dict[str, Any]]:
    payload = _read_json(path)
    rows = payload.get("candles_by_market", {}).get(
        f"{pair.upper()}|{timeframe.upper()}",
        [],
    )
    return list(rows) if isinstance(rows, list) else []


def _replay_next_open(
    market: object,
    signal: np.ndarray,
    bounds: tuple[int, int],
    *,
    stop_factor: float,
    risk_reward: float,
    round_trip_cost_bps: float,
) -> list[dict[str, float]]:
    frame = market.frame
    opens = frame["open"].to_numpy(dtype=float)
    start, requested_end = bounds
    index = max(int(start), 250)
    end = min(int(requested_end), len(market.close))
    outcomes: list[dict[str, float]] = []
    cost_fraction = float(round_trip_cost_bps) / 10_000.0
    while index < end - 1:
        direction = int(signal[index])
        atr = float(market.atr[index])
        entry_index = index + 1
        entry = float(opens[entry_index])
        if (
            direction == 0
            or not math.isfinite(atr)
            or atr <= 0.0
            or not math.isfinite(entry)
            or entry <= 0.0
        ):
            index += 1
            continue
        distance = max(
            atr * float(stop_factor),
            abs(entry) * MINIMUM_DISTANCE_PERCENT,
        )
        stop = entry - direction * distance
        target = entry + direction * distance * float(risk_reward)
        future_high = market.high[entry_index:end]
        future_low = market.low[entry_index:end]
        if direction > 0:
            stop_hits = np.flatnonzero(future_low <= stop)
            target_hits = np.flatnonzero(future_high >= target)
        else:
            stop_hits = np.flatnonzero(future_high >= stop)
            target_hits = np.flatnonzero(future_low <= target)
        first_stop = int(stop_hits[0]) if stop_hits.size else None
        first_target = int(target_hits[0]) if target_hits.size else None
        if first_stop is None and first_target is None:
            break
        stop_first = first_stop is not None and (
            first_target is None or first_stop <= first_target
        )
        exit_offset = first_stop if stop_first else first_target
        if exit_offset is None:
            break
        risk_fraction = distance / abs(entry)
        gross_return = (
            -risk_fraction if stop_first else risk_fraction * float(risk_reward)
        )
        outcomes.append(
            {
                "gross_return": gross_return,
                "net_return": gross_return - cost_fraction,
                "duration_candles": float(exit_offset + 1),
            }
        )
        index = entry_index + exit_offset + 1
    return outcomes


def _metrics(values: Iterable[dict[str, float]]) -> dict[str, Any]:
    source = summarize_outcomes(values)
    return {
        "sample_size": int(source.get("sample_size", 0) or 0),
        "win_rate": float(source.get("win_rate", 0.0) or 0.0),
        "profit_factor": float(source.get("profit_factor", 0.0) or 0.0),
        "expectancy": float(source.get("expectancy", 0.0) or 0.0),
        "net_return": float(source.get("net_return", 0.0) or 0.0),
        "max_drawdown": float(source.get("max_drawdown", 0.0) or 0.0),
    }


def _next_open_audit(
    *,
    pair: str,
    timeframe: str,
    parameters: dict[str, Any],
    candles: list[dict[str, Any]],
    signal_builder: Callable[[object, dict[str, Any]], np.ndarray],
    enrich: bool,
) -> dict[str, Any]:
    if len(candles) < 500:
        return {
            "demo_forward_enabled": False,
            "parity_status": "BLOCKED_MISSING_HISTORY",
            "parity_reason": f"Historico insuficiente: {len(candles)} candles.",
        }
    market = engineer_features(pair, candles)
    if enrich:
        market = enrich_market(market)
    signal = signal_builder(market, parameters)
    holdout_start = int(len(candles) * 0.80)
    common = {
        "stop_factor": float(parameters["stop_factor"]),
        "risk_reward": float(parameters["risk_reward"]),
    }
    full = _metrics(
        _replay_next_open(
            market,
            signal,
            (0, len(candles)),
            round_trip_cost_bps=BASE_COST_BPS,
            **common,
        )
    )
    holdout = _metrics(
        _replay_next_open(
            market,
            signal,
            (holdout_start, len(candles)),
            round_trip_cost_bps=BASE_COST_BPS,
            **common,
        )
    )
    stress = _metrics(
        _replay_next_open(
            market,
            signal,
            (holdout_start, len(candles)),
            round_trip_cost_bps=STRESS_COST_BPS,
            **common,
        )
    )
    enabled = (
        full["sample_size"] >= 100
        and holdout["sample_size"] >= 15
        and holdout["profit_factor"] >= 1.20
        and stress["profit_factor"] >= 1.10
        and stress["expectancy"] > 0.0
    )
    failures: list[str] = []
    if full["sample_size"] < 100:
        failures.append("amostra total menor que 100")
    if holdout["sample_size"] < 15:
        failures.append("holdout menor que 15")
    if holdout["profit_factor"] < 1.20:
        failures.append("PF holdout abaixo de 1.20")
    if stress["profit_factor"] < 1.10:
        failures.append("PF estressado abaixo de 1.10")
    if stress["expectancy"] <= 0.0:
        failures.append("expectancy estressada nao positiva")
    return {
        "demo_forward_enabled": enabled,
        "parity_status": "DEMO_PARITY_APPROVED" if enabled else "BLOCKED_PARITY",
        "parity_reason": (
            "Contrato executavel preservou vantagem no holdout e no estresse."
            if enabled
            else "; ".join(failures)
        ),
        "full_next_open": full,
        "holdout_next_open": holdout,
        "stress_holdout_next_open": stress,
    }


def _build_m2() -> dict[str, Any]:
    source = _read_json(M2_SOURCE)
    results: dict[str, Any] = {}
    for pair, candidates in dict(source.get("results") or {}).items():
        candidate = next(
            (item for item in list(candidates or []) if isinstance(item, dict)),
            None,
        )
        if candidate is None:
            continue
        parameters = dict(candidate.get("parameters") or {})
        parity = _next_open_audit(
            pair=pair,
            timeframe="H1",
            parameters=parameters,
            candles=_snapshot_candles(M2_SNAPSHOT, pair, "H1"),
            signal_builder=build_m2_signal,
            enrich=False,
        )
        results[pair] = {
            "pair": pair,
            "alpha_id": "ALPHA_SUGERIDA_001_PLUS",
            "timeframe": "H1",
            "parameters": parameters,
            "research_qualified": bool(candidate.get("qualified", False)),
            "research_status": str(source.get("status") or "RESEARCH_ONLY"),
            "entry_contract": "CLOSED_CANDLE_SIGNAL_NEXT_LIVE_PRICE",
            "exit_contract": FIXED_EXIT_POLICY,
            **parity,
        }
    return _model_payload("M2", results, M2_SOURCE)


def _build_m3() -> dict[str, Any]:
    source = _read_json(M3_SOURCE)
    results: dict[str, Any] = {}
    for pair, result in dict(source.get("results") or {}).items():
        winner = dict(result.get("winner") or {})
        parameters = dict(winner.get("parameters") or {})
        timeframe = str(result.get("selected_timeframe") or "N/D").upper()
        snapshot_path = M3_SNAPSHOTS.get(timeframe)
        parity = (
            _next_open_audit(
                pair=pair,
                timeframe=timeframe,
                parameters=parameters,
                candles=(
                    _snapshot_candles(snapshot_path, pair, timeframe)
                    if snapshot_path is not None
                    else []
                ),
                signal_builder=build_m3_signal,
                enrich=True,
            )
        )
        results[pair] = {
            "pair": pair,
            "alpha_id": str(result.get("alpha_id") or "ALPHA_SUGERIDA_002_PLUS"),
            "timeframe": timeframe,
            "parameters": parameters,
            "research_qualified": (
                str(result.get("selection_status") or "").upper()
                == "APROVADA_B_PARA_REPLAY"
            ),
            "research_status": str(result.get("selection_status") or "N/D"),
            "entry_contract": "CLOSED_CANDLE_SIGNAL_NEXT_LIVE_PRICE",
            "exit_contract": FIXED_EXIT_POLICY,
            **parity,
        }
    return _model_payload("M3", results, M3_SOURCE)


def _build_m4() -> dict[str, Any]:
    source = _read_json(M4_SOURCE)
    results: dict[str, Any] = {}
    for pair, result in dict(source.get("results") or {}).items():
        winner = dict(result.get("winner") or {})
        parameters = dict(winner.get("base_parameters") or {})
        overlay = dict(winner.get("context_overlay") or {})
        full = dict(winner.get("full_sample") or {})
        holdout = dict(winner.get("holdout") or {})
        stress = dict(winner.get("stress_holdout") or {})
        enabled = (
            int(full.get("sample_size", 0) or 0) >= 70
            and int(holdout.get("sample_size", 0) or 0) >= 10
            and float(full.get("profit_factor", 0.0) or 0.0) >= 1.30
            and float(holdout.get("profit_factor", 0.0) or 0.0) >= 1.15
            and float(stress.get("profit_factor", 0.0) or 0.0) >= 1.05
        )
        results[pair] = {
            "pair": pair,
            "alpha_id": str(
                result.get("alpha_id") or "ALPHA_SUGERIDA_003_CONTEXTUAL_MTF"
            ),
            "timeframe": "M30",
            "context_timeframes": ["H1", "H4"],
            "parameters": parameters,
            "context_overlay": overlay,
            "research_qualified": bool(result.get("qualified", False)),
            "research_status": str(result.get("status") or "RESEARCH_ONLY"),
            "entry_contract": "CLOSED_M30_SIGNAL_NEXT_LIVE_PRICE_WITH_H1_H4_CONTEXT",
            "exit_contract": FIXED_EXIT_POLICY,
            "demo_forward_enabled": enabled,
            "parity_status": (
                "DEMO_FORWARD_CONTEXT_APPROVED"
                if enabled
                else "BLOCKED_CONTEXT_EVIDENCE"
            ),
            "parity_reason": (
                "Contexto causal H1/H4 e custo estressado passaram o gate Demo."
                if enabled
                else "Evidencia contextual fora da amostra abaixo do gate Demo."
            ),
            "full_next_open": _compact_existing(full),
            "holdout_next_open": _compact_existing(holdout),
            "stress_holdout_next_open": _compact_existing(stress),
        }
    return _model_payload("M4", results, M4_SOURCE)


def _build_m5(models: dict[str, Any]) -> dict[str, Any]:
    source = _read_json(M5_SOURCE)
    results: dict[str, Any] = {}
    for pair, result in dict(source.get("results") or {}).items():
        winner = dict(result.get("winner") or {})
        source_model = str(winner.get("source_model") or "").upper().replace("-P", "")
        source_row = dict(models.get(source_model, {}).get("results", {}).get(pair) or {})
        if source_model == "M1":
            enabled = True
            parity_status = "DELEGATE_TO_LAB_M1"
            parity_reason = "Usa o Trade Plan vigente do M1 quando Alpha e TF coincidem."
            evidence_enabled = True
            evidence_status = parity_status
            evidence_reason = parity_reason
        else:
            enabled = bool(source_row.get("demo_forward_enabled", False))
            parity_status = str(source_row.get("parity_status") or "SOURCE_BLOCKED")
            parity_reason = str(source_row.get("parity_reason") or "Fonte bloqueada.")
            evidence_enabled = bool(
                source_row.get("evidence_demo_forward_enabled", enabled)
            )
            evidence_status = str(
                source_row.get("evidence_parity_status") or parity_status
            )
            evidence_reason = str(
                source_row.get("evidence_parity_reason") or parity_reason
            )
        results[pair] = {
            "pair": pair,
            "source_model": source_model,
            "alpha_id": str(winner.get("alpha_id") or "N/D"),
            "timeframe": str(winner.get("timeframe") or "N/D").upper(),
            "parameters": dict(winner.get("parameters") or {}),
            "context_overlay": dict(winner.get("context_overlay") or {}),
            "research_status": str(winner.get("source_status") or "N/D"),
            "entry_contract": str(
                source_row.get("entry_contract")
                or ("DELEGATE_TO_LAB_M1" if source_model == "M1" else "N/D")
            ),
            "exit_contract": FIXED_EXIT_POLICY,
            "demo_forward_enabled": enabled,
            "parity_status": parity_status,
            "parity_reason": parity_reason,
            "evidence_demo_forward_enabled": evidence_enabled,
            "evidence_parity_status": evidence_status,
            "evidence_parity_reason": evidence_reason,
        }
    return _model_payload("M5", results, M5_SOURCE)


def _compact_existing(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_size": int(metrics.get("sample_size", 0) or 0),
        "win_rate": float(metrics.get("win_rate", 0.0) or 0.0),
        "profit_factor": float(metrics.get("profit_factor", 0.0) or 0.0),
        "expectancy": float(metrics.get("expectancy", 0.0) or 0.0),
        "net_return": float(metrics.get("net_return", 0.0) or 0.0),
        "max_drawdown": float(metrics.get("max_drawdown", 0.0) or 0.0),
    }


def _model_payload(label: str, results: dict[str, Any], source: Path) -> dict[str, Any]:
    enabled = sorted(
        pair for pair, row in results.items() if bool(row.get("demo_forward_enabled"))
    )
    return {
        "model_label": label,
        "model_id": MODEL_IDS[label],
        "source_artifact": source.relative_to(ROOT).as_posix(),
        "demo_forward_pairs": enabled,
        "blocked_pairs": sorted(set(results) - set(enabled)),
        "results": results,
    }


def _apply_demo_forward_policy(
    label: str,
    model: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    model_policy = dict(policy.get("models", {}).get(label) or {})
    approve_all = bool(model_policy.get("approve_all_pairs", False))
    approved_pairs = {
        str(pair).upper()
        for pair in list(model_policy.get("approved_pairs") or [])
    }
    if not approve_all and not approved_pairs:
        return model

    results = dict(model.get("results") or {})
    for pair, source_row in results.items():
        row = dict(source_row)
        row.setdefault(
            "evidence_demo_forward_enabled",
            bool(row.get("demo_forward_enabled", False)),
        )
        row.setdefault(
            "evidence_parity_status",
            str(row.get("parity_status") or "N/D"),
        )
        row.setdefault(
            "evidence_parity_reason",
            str(row.get("parity_reason") or "N/D"),
        )
        if approve_all or str(pair).upper() in approved_pairs:
            row["demo_forward_enabled"] = True
            row["parity_status"] = "DEMO_FORWARD_OPERATIONALLY_APPROVED"
            row["parity_reason"] = (
                "Liberado para operacao Demo por politica operacional explicita; "
                "a evidencia historica original permanece registrada."
            )
            row["operational_approval"] = "USER_APPROVED"
            row["operational_approval_scope"] = "DEMO_ONLY"
        results[pair] = row

    enabled = sorted(
        pair for pair, row in results.items() if bool(row.get("demo_forward_enabled"))
    )
    model["results"] = results
    model["demo_forward_pairs"] = enabled
    model["blocked_pairs"] = sorted(set(results) - set(enabled))
    model["operational_policy"] = {
        "approve_all_pairs": approve_all,
        "approved_pairs": sorted(approved_pairs),
        "scope": "DEMO_ONLY",
    }
    return model


def build_manifest() -> dict[str, Any]:
    policy = _read_json(POLICY_PATH) if POLICY_PATH.exists() else {}
    if policy:
        if str(policy.get("scope") or "").upper() != "DEMO_ONLY":
            raise ValueError("A politica operacional deve possuir escopo DEMO_ONLY.")
        if bool(policy.get("real_account_authorized", False)):
            raise ValueError("A politica operacional nao pode autorizar conta real.")
    models = {
        "M2": _build_m2(),
        "M3": _build_m3(),
        "M4": _build_m4(),
    }
    for label in ("M2", "M3", "M4"):
        models[label] = _apply_demo_forward_policy(label, models[label], policy)
    models["M5"] = _build_m5(models)
    models["M5"] = _apply_demo_forward_policy("M5", models["M5"], policy)
    return {
        "schema_version": "2.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contract": "LAB_MODELS_REPLACE_LEGACY_MT5_MODELS",
        "fixed_exit_policy": FIXED_EXIT_POLICY,
        "demo_only": True,
        "real_account_authorized": False,
        "m6_enabled": False,
        "operational_policy_source": (
            POLICY_PATH.relative_to(ROOT).as_posix() if POLICY_PATH.exists() else None
        ),
        "models": models,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--detail", type=Path, default=DETAIL_PATH)
    args = parser.parse_args(list(argv) if argv is not None else None)
    payload = build_manifest()
    _write_json(args.manifest, payload)
    _write_json(args.detail, payload)
    summary = ", ".join(
        f"{label}={len(model['demo_forward_pairs'])}/8"
        for label, model in payload["models"].items()
    )
    print(f"Lab operational parity: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
