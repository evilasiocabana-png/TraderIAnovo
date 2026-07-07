"""Motor inicial do Lab, sem execucao operacional."""

from __future__ import annotations

from domain.contracts.lab_result import LabResult


class LabEngine:
    def evaluate(self) -> LabResult:
        return LabResult(
            setup="TREND_MOMENTUM",
            timeframe="M1",
            theoretical_entry="WAIT",
            interest_zone="N/D",
            stop_management="ATR_TRAILING_STOP",
            parameters={"source": "lab_engine_placeholder"},
        )
