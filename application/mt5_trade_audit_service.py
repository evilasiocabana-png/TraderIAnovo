"""Auditoria read-only para a aba Relatorio."""

from __future__ import annotations

from domain.contracts.forex_signal import ForexSignal
from domain.contracts.lab_result import LabResult
from domain.contracts.trade_audit import TradeAuditReport, TradeAuditRow


class MT5TradeAuditService:
    """Consolida Lab e Forex MT5 sem consultar nem executar operacao real."""

    def build_report(
        self,
        *,
        signals: list[ForexSignal],
        lab: LabResult,
    ) -> TradeAuditReport:
        rows = [
            TradeAuditRow(
                symbol=signal.pair,
                status="READ_ONLY",
                source="FOREX_MT5_MOCK",
                lab_decision=lab.theoretical_entry,
                mt5_position_status="NOT_READ_IN_BASELINE",
                message=f"{signal.decision} / {lab.setup} / {lab.stop_management}",
            )
            for signal in signals
        ]
        return TradeAuditReport(
            status="READ_ONLY",
            source="Lab + Forex MT5",
            total_rows=len(rows),
            rows=rows,
            message="Auditoria baseline sem leitura real de posicoes e sem envio de ordens.",
        )
