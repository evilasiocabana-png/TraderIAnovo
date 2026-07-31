"""Promote the best available M4 candidate to all monitored Demo pairs.

The source AUDUSD metrics remain attached only to AUDUSD. Other pairs receive
the frozen executable contract and an explicit unvalidated-expansion status.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = ROOT / ".traderia" / "research"
SOURCE_PATH = RESEARCH_ROOT / "modelo_4_pesquisa_contextual_mtf.json"
OUTPUT_PATH = RESEARCH_ROOT / "modelo_4_liquidity_reclaim_all_pairs_demo.json"
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
EVIDENCE_PAIR = "AUDUSD"
EVIDENCE_STATUS = "BEST_AVAILABLE_DEMO_CANDIDATE_UNCERTIFIED"
EXPANSION_STATUS = "USER_APPROVED_DEMO_EXPANSION_UNVALIDATED"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object expected: {path}")
    return payload


def build_payload(source: dict[str, Any]) -> dict[str, Any]:
    evidence = copy.deepcopy(
        dict((source.get("results") or {}).get(EVIDENCE_PAIR) or {})
    )
    winner = dict(evidence.get("winner") or {})
    parameters = dict(winner.get("base_parameters") or {})
    overlay = dict(winner.get("context_overlay") or {})
    if not parameters or not overlay:
        raise ValueError("AUDUSD M4 candidate contract was not found.")

    evidence["qualified"] = False
    evidence["status"] = EVIDENCE_STATUS
    evidence["qualification_reasons"] = [
        "Melhor evidencia fora da amostra disponivel para o M4.",
        "Holdout de 14 trades ainda insuficiente para certificacao.",
        "Autorizado somente como experimento operacional em conta Demo.",
    ]

    results: dict[str, Any] = {}
    for pair in PAIRS:
        if pair == EVIDENCE_PAIR:
            results[pair] = copy.deepcopy(evidence)
            continue
        results[pair] = {
            "pair": pair,
            "alpha_id": f"ALPHA_M4_LIQUIDITY_RECLAIM_DEMO_{pair}",
            "qualified": False,
            "status": EXPANSION_STATUS,
            "candidate_count": 0,
            "discovery_survivors": 0,
            "validation_finalists": 0,
            "holdout_opened": False,
            "qualification_reasons": [
                "Contrato extrapolado do AUDUSD por solicitacao do usuario.",
                "Sem pesquisa ou certificacao historica individual para este par.",
            ],
            "winner": {
                "base_parameters": copy.deepcopy(parameters),
                "context_overlay": copy.deepcopy(overlay),
                "entry_contract": "SIGNAL_CLOSED_CANDLE_TO_NEXT_CANDLE_OPEN",
                "discovery": {},
                "stability_blocks": [],
                "validation": {},
                "holdout": {},
                "stress_holdout": {},
                "full_sample": {},
            },
        }

    return {
        "schema_version": "1.1",
        "alpha_id": "ALPHA_M4_LIQUIDITY_RECLAIM",
        "status": "DEMO_ALL_PAIRS_EXPANSION",
        "model_destination": "MODELO_4",
        "operational": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_timeframe": "M30",
        "context_timeframes": ["H1", "H4"],
        "entry_contract": "SIGNAL_CLOSED_CANDLE_TO_NEXT_CANDLE_OPEN",
        "evidence_pair": EVIDENCE_PAIR,
        "demo_expansion_pairs": list(PAIRS),
        "source_artifact": str(SOURCE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "results": results,
        "guardrails": {
            "source_metrics_preserved_only_for_evidence_pair": True,
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
