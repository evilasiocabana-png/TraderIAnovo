"""Servico de relatorio consolidado read-only."""

from __future__ import annotations

from domain.contracts.lab_result import LabResult
from domain.contracts.mt5_status import MT5Status
from domain.contracts.report_row import ReportRow


class ReportService:
    """Consolida status de Forex MT5 e Lab sem ler posicoes reais."""

    def build_rows(self, forex: MT5Status, lab: LabResult) -> list[ReportRow]:
        return [
            ReportRow(
                section="Forex MT5",
                status=forex.status,
                detail=f"{forex.server} / {forex.timeframe}",
            ),
            ReportRow(
                section="Lab",
                status=lab.theoretical_entry,
                detail=f"{lab.setup} / {lab.stop_management}",
            ),
        ]
