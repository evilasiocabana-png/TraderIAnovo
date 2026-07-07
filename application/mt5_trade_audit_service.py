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
        positions: list[dict[str, object]] | None = None,
    ) -> TradeAuditReport:
        positions_by_symbol = {
            str(position.get("symbol", "")).upper(): position
            for position in (positions or [])
        }
        rows = [
            TradeAuditRow(
                symbol=signal.pair,
                status="READ_ONLY",
                source="FOREX_MT5_MOCK",
                lab_decision=lab.theoretical_entry,
                mt5_position_status=(
                    "OPEN"
                    if signal.pair.upper() in positions_by_symbol
                    else "NO_POSITION"
                ),
                message=self._message(signal=signal, lab=lab),
                side=signal.position_side,
                volume=signal.position_volume,
                entry_price=signal.position_price,
                current_price=signal.price or None,
                profit=signal.position_profit,
                dynamic_exit_policy=signal.dynamic_exit_policy,
                dynamic_exit_action=signal.dynamic_exit_action,
                dynamic_exit_reason=signal.dynamic_exit_reason,
                dynamic_exit_allowed_to_execute_demo=(
                    signal.dynamic_exit_allowed_to_execute_demo
                ),
            )
            for signal in signals
        ]
        total_open_positions = sum(1 for row in rows if row.mt5_position_status == "OPEN")
        open_profit = sum(float(row.profit or 0.0) for row in rows)
        return TradeAuditReport(
            status="READ_ONLY",
            source="Lab + Forex MT5",
            total_rows=len(rows),
            rows=rows,
            message="Auditoria read-only: acompanha posicoes abertas sem envio de ordens.",
            total_open_positions=total_open_positions,
            open_profit=open_profit,
        )

    def _message(self, signal: ForexSignal, lab: LabResult) -> str:
        if signal.is_positioned:
            return (
                f"Posicionado {signal.position_side}; "
                f"Lab={lab.setup}; saida={lab.stop_management}; "
                f"saida_dinamica={signal.dynamic_exit_action}"
            )
        return (
            f"Sem posicao aberta; Lab={lab.theoretical_entry}; "
            f"saida={lab.stop_management}; saida_dinamica={signal.dynamic_exit_action}"
        )
