"""Promote the frozen M3 setup to every monitored pair in Demo mode.

This script does not recalculate or copy USDCAD performance metrics to another
pair. It only materializes the user's operational expansion request while
preserving the original pair-level research qualification.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = ROOT / ".traderia" / "research"
SOURCE_PATH = RESEARCH_ROOT / "m3_nested_robusta_003_usdcad_6000.json"
OUTPUT_PATH = RESEARCH_ROOT / "m3_nested_robusta_003_all_pairs_demo.json"
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
CERTIFIED_PAIR = "USDCAD"
EXPANSION_STATUS = "USER_APPROVED_DEMO_EXPANSION_UNVALIDATED"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object expected: {path}")
    return payload


def build_payload(source: dict[str, Any]) -> dict[str, Any]:
    certified = dict((source.get("results") or {}).get(CERTIFIED_PAIR) or {})
    winner = dict(certified.get("winner") or {})
    parameters = dict(winner.get("parameters") or {})
    if not parameters:
        raise ValueError("Certified M3 parameters were not found.")

    results: dict[str, Any] = {}
    for pair in PAIRS:
        if pair == CERTIFIED_PAIR:
            results[pair] = copy.deepcopy(certified)
            continue
        results[pair] = {
            "pair": pair,
            "model": "MODELO_3",
            "alpha_id": f"ALPHA_NESTED_ROBUSTA_003_DEMO_{pair}",
            "selected_timeframe": "H1",
            "selection_status": EXPANSION_STATUS,
            "operational": False,
            "qualification_reasons": [
                "Configuracao extrapolada do USDCAD por solicitacao do usuario.",
                "Sem certificacao historica individual para este par.",
            ],
            "winner": {
                "parameters": copy.deepcopy(parameters),
                "development": {},
                "stability_blocks": [],
                "validation": {},
                "stress_validation": {},
                "holdout": {},
                "stress_holdout": {},
                "full_sample": {},
            },
        }

    return {
        "schema_version": "1.1",
        "alpha_id": "ALPHA_NESTED_ROBUSTA_003",
        "model_destination": "MODELO_3",
        "status": "DEMO_ALL_PAIRS_EXPANSION",
        "operational": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": str(source.get("method") or "N/D"),
        "candidate_count_per_pair": int(
            source.get("candidate_count_per_pair", 0) or 0
        ),
        "timeframes_compared": list(source.get("timeframes_compared") or []),
        "qualified_pairs": [CERTIFIED_PAIR],
        "demo_expansion_pairs": list(PAIRS),
        "source_artifact": str(SOURCE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "results": results,
        "guardrails": {
            "original_research_metrics_preserved_only_for_certified_pair": True,
            "uncertified_pairs_marked_as_operational_expansion": True,
            "real_account_authorized": False,
            "position_manager_enabled": False,
            "fixed_initial_sl_tp": True,
        },
    }


def main() -> None:
    payload = build_payload(_read_json(SOURCE_PATH))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
