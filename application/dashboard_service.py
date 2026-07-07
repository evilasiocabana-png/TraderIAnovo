"""Fachada unica consumida pelo dashboard Streamlit."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from application.forex_mt5_service import ForexMT5Service
from application.lab_service import LabService
from application.mt5_trade_audit_service import MT5TradeAuditService
from application.mt5_visual_signal_exporter import MT5VisualSignalExporter
from application.report_service import ReportService
from domain.contracts.visual_signal import VisualSignal


class DashboardService:
    """Agrega as tres abas iniciais sem expor infraestrutura para a UI."""

    def __init__(
        self,
        forex_mt5_service: ForexMT5Service | None = None,
        lab_service: LabService | None = None,
        report_service: ReportService | None = None,
        trade_audit_service: MT5TradeAuditService | None = None,
        visual_signal_exporter: MT5VisualSignalExporter | None = None,
    ) -> None:
        self.forex_mt5_service = forex_mt5_service or ForexMT5Service()
        self.lab_service = lab_service or LabService()
        self.report_service = report_service or ReportService()
        self.trade_audit_service = trade_audit_service or MT5TradeAuditService()
        self.visual_signal_exporter = visual_signal_exporter or MT5VisualSignalExporter()

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
        signals = self.forex_mt5_service.get_signals()
        lab = self.lab_service.get_latest_result()
        audit = self.trade_audit_service.build_report(signals=signals, lab=lab)
        rows = self.report_service.build_rows(forex=forex, lab=lab)
        return {
            "rows": [asdict(row) for row in rows],
            "audit": {
                "status": audit.status,
                "source": audit.source,
                "total_rows": audit.total_rows,
                "message": audit.message,
                "rows": [asdict(row) for row in audit.rows],
            },
            "summary": self.report_service.build_summary(forex=forex, lab=lab, audit=audit),
        }

    def get_mt5_visual_signal_payload(self) -> dict[str, object]:
        lab = self.lab_service.get_latest_result()
        signals = [
            VisualSignal(
                symbol=signal.pair,
                timeframe=signal.timeframe,
                decision=signal.decision,
                entry=signal.price,
                stop=None,
                target=None,
                setup=lab.setup,
                reason=signal.reason,
                stop_management=lab.stop_management,
            )
            for signal in self.forex_mt5_service.get_signals()
        ]
        return self.visual_signal_exporter.build_payload(signals=signals, lab=lab)

    def get_dashboard_view_model(self) -> dict[str, Any]:
        return {
            "forex_mt5": self.get_forex_mt5_view(),
            "lab": self.get_lab_view(),
            "report": self.get_report_view(),
        }
