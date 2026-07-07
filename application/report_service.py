"""Servico de relatorio consolidado read-only."""

from __future__ import annotations

from domain.contracts.lab_result import LabResult
from domain.contracts.mt5_status import MT5Status
from domain.contracts.report_row import ReportRow
from domain.contracts.trade_audit import TradeAuditReport


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
                dynamic_exit_policy=str(
                    lab.parameters.get("dynamic_exit_policy", lab.stop_management)
                ),
                dynamic_exit_action=str(
                    lab.parameters.get("dynamic_exit_action", "KEEP_ORIGINAL_PLAN")
                ),
                dynamic_exit_reason=str(
                    lab.parameters.get("dynamic_exit_reason", "N/D")
                ),
                dynamic_exit_confidence=self._float_or_zero(
                    lab.parameters.get("dynamic_exit_confidence")
                ),
                dynamic_exit_market_state=str(
                    lab.parameters.get("dynamic_exit_market_state", "NO_POSITION")
                ),
                dynamic_exit_r_multiple=self._float_or_zero(
                    lab.parameters.get("dynamic_exit_r_multiple")
                ),
                dynamic_exit_candidate_stop=self._float_or_none(
                    lab.parameters.get("dynamic_exit_candidate_stop")
                ),
                dynamic_exit_allowed_to_execute_demo=False,
                dynamic_exit_executed_action="NONE",
                dynamic_exit_final_result="OBSERVADO_READ_ONLY",
            ),
        ]

    def build_summary(
        self,
        forex: MT5Status,
        lab: LabResult,
        audit: TradeAuditReport,
    ) -> dict[str, object]:
        return {
            "forex_status": forex.status,
            "forex_timeframe": forex.timeframe,
            "lab_setup": lab.setup,
            "lab_timeframe": lab.timeframe,
            "lab_entry": lab.theoretical_entry,
            "lab_stop_management": lab.stop_management,
            "dynamic_exit_policy": str(
                lab.parameters.get("dynamic_exit_policy", lab.stop_management)
            ),
            "dynamic_exit_action": str(
                lab.parameters.get("dynamic_exit_action", "KEEP_ORIGINAL_PLAN")
            ),
            "dynamic_exit_reason": str(
                lab.parameters.get("dynamic_exit_reason", "N/D")
            ),
            "dynamic_exit_confidence": self._float_or_zero(
                lab.parameters.get("dynamic_exit_confidence")
            ),
            "dynamic_exit_market_state": str(
                lab.parameters.get("dynamic_exit_market_state", "NO_POSITION")
            ),
            "dynamic_exit_r_multiple": self._float_or_zero(
                lab.parameters.get("dynamic_exit_r_multiple")
            ),
            "dynamic_exit_candidate_stop": self._float_or_none(
                lab.parameters.get("dynamic_exit_candidate_stop")
            ),
            "dynamic_exit_allowed_to_execute_demo": False,
            "dynamic_exit_executed_action": "NONE",
            "dynamic_exit_final_result": "OBSERVADO_READ_ONLY",
            "audit_status": audit.status,
            "audit_rows": audit.total_rows,
        }

    def _float_or_none(self, value: object) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _float_or_zero(self, value: object) -> float:
        parsed = self._float_or_none(value)
        return 0.0 if parsed is None else parsed
