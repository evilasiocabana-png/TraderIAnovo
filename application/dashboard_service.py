"""Fachada unica consumida pelo dashboard Streamlit."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from application.forex_mt5_service import ForexMT5Service
from application.lab_service import LabService
from application.report_service import ReportService


class DashboardService:
    """Agrega as tres abas iniciais sem expor infraestrutura para a UI."""

    def __init__(
        self,
        forex_mt5_service: ForexMT5Service | None = None,
        lab_service: LabService | None = None,
        report_service: ReportService | None = None,
    ) -> None:
        self.forex_mt5_service = forex_mt5_service or ForexMT5Service()
        self.lab_service = lab_service or LabService()
        self.report_service = report_service or ReportService()

    def get_forex_mt5_view(self) -> dict[str, Any]:
        status = self.forex_mt5_service.get_status()
        signals = self.forex_mt5_service.get_signals()
        return {
            "status": status.status,
            "server": status.server,
            "account": status.account,
            "timeframe": status.timeframe,
            "signals": [asdict(signal) for signal in signals],
        }

    def get_lab_view(self) -> dict[str, Any]:
        return asdict(self.lab_service.get_latest_result())

    def get_report_view(self) -> dict[str, Any]:
        forex = self.forex_mt5_service.get_status()
        lab = self.lab_service.get_latest_result()
        rows = self.report_service.build_rows(forex=forex, lab=lab)
        return {"rows": [asdict(row) for row in rows]}

    def get_dashboard_view_model(self) -> dict[str, Any]:
        return {
            "forex_mt5": self.get_forex_mt5_view(),
            "lab": self.get_lab_view(),
            "report": self.get_report_view(),
        }
