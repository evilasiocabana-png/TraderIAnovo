"""Gate assistido para mover somente SL demo a partir da saida dinamica."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from domain.contracts.dynamic_exit_demo_sl import DynamicExitDemoSLExecutionResult
from domain.contracts.dynamic_exit_simulation import DynamicExitSimulationDecision


class DynamicExitDemoSLExecutor(Protocol):
    """Porta explicita para modificacao assistida de SL em conta demo."""

    def modify_demo_position_stop_loss(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        requested_stop: float,
        decision_key: str = "N/D",
    ) -> DynamicExitDemoSLExecutionResult:
        """Modifica somente o SL de uma posicao demo existente."""


@dataclass
class DynamicExitDemoSLExecutionService:
    """Revalida gates antes de permitir chamada assistida ao MT5 Demo."""

    min_stop_delta: float = 0.00001
    audit_log: list[DynamicExitDemoSLExecutionResult] = field(default_factory=list)
    _executed_keys: set[tuple[object, ...]] = field(default_factory=set)

    def execute_assisted(
        self,
        *,
        decision: DynamicExitSimulationDecision,
        executor: DynamicExitDemoSLExecutor | None,
        enabled: bool = False,
        user_confirmed: bool = False,
        robot_armed: bool = False,
        demo_account_confirmed: bool = False,
        current_price: float | None = None,
        spread: float | None = None,
    ) -> DynamicExitDemoSLExecutionResult:
        """Executa SL assistido somente quando todos os gates aprovam."""

        requested_stop = decision.approved_stop
        rejection_reasons = self._rejection_reasons(
            decision=decision,
            enabled=enabled,
            user_confirmed=user_confirmed,
            robot_armed=robot_armed,
            demo_account_confirmed=demo_account_confirmed,
            current_price=current_price,
            spread=spread,
        )
        allowed = not rejection_reasons
        base = self._base_result(
            decision=decision,
            requested_stop=requested_stop,
            allowed=allowed,
            rejection_reasons=tuple(rejection_reasons),
        )
        if not allowed:
            self.audit_log.append(base)
            return base
        if executor is None:
            result = self._replace(
                base,
                allowed=True,
                message="Provider MT5 Demo indisponivel para execucao assistida.",
                rejection_reasons=("Provider MT5 Demo indisponivel.",),
            )
            self.audit_log.append(result)
            return result

        key = self._execution_key(decision, requested_stop)
        self._executed_keys.add(key)
        provider_result = executor.modify_demo_position_stop_loss(
            symbol=decision.symbol,
            ticket=int(decision.ticket or 0),
            side=decision.side,
            requested_stop=float(requested_stop),
            decision_key=str(decision.candle_key or "N/D"),
        )
        result = self._replace(
            provider_result,
            allowed=True,
            requested_stop=requested_stop,
            rejection_reasons=tuple(provider_result.rejection_reasons),
        )
        self.audit_log.append(result)
        return result

    def list_audit_log(self) -> list[DynamicExitDemoSLExecutionResult]:
        """Retorna auditoria em memoria da execucao assistida."""
        return list(self.audit_log)

    def _rejection_reasons(
        self,
        *,
        decision: DynamicExitSimulationDecision,
        enabled: bool,
        user_confirmed: bool,
        robot_armed: bool,
        demo_account_confirmed: bool,
        current_price: float | None,
        spread: float | None,
    ) -> list[str]:
        reasons: list[str] = []
        side = str(decision.side or "").upper()
        requested_stop = decision.approved_stop
        current_stop = decision.current_stop
        if not enabled:
            reasons.append("dynamic_exit_demo_sl_assisted_execution_enabled desligado.")
        if not user_confirmed:
            reasons.append("Confirmacao operacional assistida ausente.")
        if not robot_armed:
            reasons.append("Robo demo nao esta armado.")
        if not demo_account_confirmed:
            reasons.append("Conta demo nao confirmada pelo dashboard.")
        if not decision.allowed_to_simulate:
            reasons.append("Decisao simulada da TIA-026 nao esta aprovada.")
        if decision.ticket is None or int(decision.ticket or 0) <= 0:
            reasons.append("Ticket MT5 invalido ou ausente.")
        if side not in {"BUY", "SELL"}:
            reasons.append("Lado da posicao invalido.")
        if requested_stop is None:
            reasons.append("Stop aprovado simulado ausente.")
        if current_stop is None:
            reasons.append("Stop atual ausente.")
        if current_price is None:
            reasons.append("Preco atual ausente.")
        if requested_stop is not None and current_stop is not None:
            if side == "BUY" and requested_stop <= current_stop:
                reasons.append("BUY nao permite SL menor ou igual ao stop atual.")
            if side == "SELL" and requested_stop >= current_stop:
                reasons.append("SELL nao permite SL maior ou igual ao stop atual.")
            if abs(float(requested_stop) - float(current_stop)) < self.min_stop_delta:
                reasons.append("Diferenca de SL irrelevante.")
        if requested_stop is not None and current_price is not None:
            if side == "BUY" and requested_stop >= current_price:
                reasons.append("BUY exige SL abaixo do preco atual.")
            if side == "SELL" and requested_stop <= current_price:
                reasons.append("SELL exige SL acima do preco atual.")
        if self._spread_invalid(spread):
            reasons.append("Spread invalido para execucao assistida.")
        if (
            requested_stop is not None
            and self._execution_key(decision, requested_stop) in self._executed_keys
        ):
            reasons.append("Execucao assistida ja registrada para esta vela/janela.")
        return reasons

    def _spread_invalid(self, spread: float | None) -> bool:
        if spread is None:
            return False
        try:
            return float(spread) < 0.0
        except (TypeError, ValueError):
            return True

    def _execution_key(
        self,
        decision: DynamicExitSimulationDecision,
        requested_stop: float | None,
    ) -> tuple[object, ...]:
        return (
            str(decision.symbol).upper(),
            int(decision.ticket or 0),
            str(decision.side).upper(),
            str(decision.candle_key or "N/D"),
            round(float(requested_stop or 0.0), 8),
        )

    def _base_result(
        self,
        *,
        decision: DynamicExitSimulationDecision,
        requested_stop: float | None,
        allowed: bool,
        rejection_reasons: tuple[str, ...],
    ) -> DynamicExitDemoSLExecutionResult:
        return DynamicExitDemoSLExecutionResult(
            symbol=decision.symbol,
            ticket=decision.ticket,
            side=decision.side,
            requested_stop=requested_stop,
            previous_stop=decision.current_stop,
            allowed=allowed,
            submitted=False,
            success=False,
            retcode="NOT_SUBMITTED",
            message=(
                "Gate assistido aprovado; aguardando provider."
                if allowed
                else "Gate assistido rejeitado."
            ),
            rejection_reasons=rejection_reasons,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _replace(
        self,
        result: DynamicExitDemoSLExecutionResult,
        **updates: object,
    ) -> DynamicExitDemoSLExecutionResult:
        data = result.__dict__.copy()
        data.update(updates)
        if data.get("created_at") in {None, "N/D"}:
            data["created_at"] = datetime.now(timezone.utc).isoformat()
        return DynamicExitDemoSLExecutionResult(**data)
