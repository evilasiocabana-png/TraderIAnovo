"""Exportador visual read-only para o indicador MT5."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from domain.contracts.lab_result import LabResult
from domain.contracts.visual_signal import VisualSignal


class MT5VisualSignalExporter:
    """Gera JSON visual sem executar ordens ou tocar corretora operacional."""

    SCHEMA_VERSION = "traderiaianovo.mt5.visual_signals.v1"

    def build_payload(self, signals: list[VisualSignal], lab: LabResult) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "traderiaianovo",
            "mode": "VISUAL_ONLY",
            "read_only": True,
            "execution_allowed": False,
            "lab": {
                "setup": lab.setup,
                "timeframe": lab.timeframe,
                "theoretical_entry": lab.theoretical_entry,
                "interest_zone": lab.interest_zone,
                "stop_management": lab.stop_management,
                "parameters": dict(lab.parameters),
            },
            "signals": [asdict(signal) for signal in signals],
        }

    def export(self, output_path: Path, signals: list[VisualSignal], lab: LabResult) -> Path:
        payload = self.build_payload(signals=signals, lab=lab)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return output_path
