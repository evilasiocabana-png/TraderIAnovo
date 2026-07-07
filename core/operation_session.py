"""Estado em memoria da sessao operacional."""

from dataclasses import dataclass
from typing import Any


@dataclass
class OperationSession:
    """Armazena o estado operacional diario do TraderIA_WDO."""

    session_date: str
    market_open_time: str
    market_close_time: str
    operations_today: int = 0
    wins_today: int = 0
    losses_today: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    current_position: Any | None = None
    last_signal: Any | None = None
    last_event: Any | None = None
    system_status: str = "Simulação"

    def register_operation(self) -> None:
        """Registra uma nova operacao na sessao."""
        self.operations_today += 1

    def register_win(self, profit: float) -> None:
        """Registra uma operacao vencedora."""
        self.wins_today += 1
        self.gross_profit += profit
        self._recalculate_net_profit()

    def register_loss(self, loss: float) -> None:
        """Registra uma operacao perdedora."""
        self.losses_today += 1
        self.gross_loss += abs(loss)
        self._recalculate_net_profit()

    def update_position(self, position: Any | None) -> None:
        """Atualiza a posicao atual."""
        self.current_position = position

    def update_last_signal(self, signal: Any | None) -> None:
        """Atualiza o ultimo sinal observado."""
        self.last_signal = signal

    def update_last_event(self, event: Any | None) -> None:
        """Atualiza o ultimo evento observado."""
        self.last_event = event

    def reset_session(self) -> None:
        """Reinicia os dados mutaveis da sessao."""
        self.operations_today = 0
        self.wins_today = 0
        self.losses_today = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        self.net_profit = 0.0
        self.current_position = None
        self.last_signal = None
        self.last_event = None
        self.system_status = "Simulação"

    def _recalculate_net_profit(self) -> None:
        self.net_profit = self.gross_profit - self.gross_loss
