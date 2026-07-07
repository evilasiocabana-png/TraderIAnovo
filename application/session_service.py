"""Servico de aplicacao para expor sessao operacional."""

from dataclasses import dataclass

from core.operation_session import OperationSession


@dataclass(frozen=True)
class SessionSnapshot:
    """Dados da sessao operacional prontos para apresentacao."""

    session_date: str
    system_status: str
    operations_today: int
    wins_today: int
    losses_today: int
    gross_profit: float
    gross_loss: float
    net_profit: float
    current_position: object | None
    last_signal: object | None
    last_event: object | None


def empty_session_snapshot() -> SessionSnapshot:
    """Retorna um snapshot amigavel quando nao ha sessao ativa."""
    return SessionSnapshot(
        session_date="N/D",
        system_status="Sessao nao disponivel",
        operations_today=0,
        wins_today=0,
        losses_today=0,
        gross_profit=0.0,
        gross_loss=0.0,
        net_profit=0.0,
        current_position=None,
        last_signal=None,
        last_event=None,
    )


@dataclass(frozen=True)
class SessionService:
    """Fornece dados da OperationSession para camadas de apresentacao."""

    session: OperationSession

    def get_session_snapshot(self) -> SessionSnapshot:
        """Retorna um snapshot imutavel da sessao operacional."""
        return SessionSnapshot(
            session_date=self.session.session_date,
            system_status=self.session.system_status,
            operations_today=self.session.operations_today,
            wins_today=self.session.wins_today,
            losses_today=self.session.losses_today,
            gross_profit=self.session.gross_profit,
            gross_loss=self.session.gross_loss,
            net_profit=self.session.net_profit,
            current_position=self.session.current_position,
            last_signal=self.session.last_signal,
            last_event=self.session.last_event,
        )
