"""Servico inicial do Lab teorico."""

from __future__ import annotations

from domain.contracts.lab_result import LabResult
from research.stop_management_catalog import SUPPORTED_STOP_MANAGEMENT


class LabService:
    """Define parametros teoricos mockados para o Forex MT5."""

    def get_latest_result(self) -> LabResult:
        return LabResult(
            setup="TREND_MOMENTUM",
            timeframe="M1",
            theoretical_entry="WAIT",
            interest_zone="N/D",
            stop_management="ATR_TRAILING_STOP",
            parameters={
                "risk_reward": "2.0",
                "atr_factor": "2.0",
                "source": "baseline_lab_parameters",
                "supported_stop_management": ", ".join(SUPPORTED_STOP_MANAGEMENT),
                "entry_rule": "zona_de_interesse_sem_posicao_aberta",
            },
        )
