"""Motor base de replay candle a candle em memoria."""

from dataclasses import dataclass, field

from core.event_bus import EventBus
from core.events import BACKTEST_FINISHED, NEW_CANDLE
from domain.candle import Candle


@dataclass(frozen=True)
class ReplayState:
    """Estado atual do replay de mercado."""

    current_index: int
    total_candles: int
    current_candle: Candle | None
    is_running: bool
    is_finished: bool


@dataclass
class ReplayEngine:
    """Simula a passagem do mercado candle a candle."""

    candles: list[Candle] = field(default_factory=list)
    current_index: int = -1
    current_candle: Candle | None = None
    is_running: bool = False
    is_finished: bool = False
    event_bus: EventBus | None = None

    def load_candles(self, candles: list[Candle]) -> None:
        """Carrega candles em memoria e reinicia o replay."""
        self.candles = list(candles)
        self.reset()

    def start(self) -> None:
        """Inicia o replay."""
        if not self.is_finished:
            self.is_running = True

    def stop(self) -> None:
        """Para o replay."""
        self.is_running = False

    def reset(self) -> None:
        """Volta o replay para o estado inicial."""
        self.current_index = -1
        self.current_candle = None
        self.is_running = False
        self.is_finished = False

    def next_candle(self) -> Candle | None:
        """Avanca um candle e retorna o candle atual."""
        if self.is_finished:
            return None

        next_index = self.current_index + 1
        if next_index >= len(self.candles):
            self._finish()
            return None

        self.current_index = next_index
        self.current_candle = self.candles[self.current_index]
        self._publish_new_candle()
        self._finish_if_last_candle()
        return self.current_candle

    def get_state(self) -> ReplayState:
        """Retorna o estado atual do replay."""
        return ReplayState(
            current_index=self.current_index,
            total_candles=len(self.candles),
            current_candle=self.current_candle,
            is_running=self.is_running,
            is_finished=self.is_finished,
        )

    def _finish_if_last_candle(self) -> None:
        if self.current_index == len(self.candles) - 1:
            self._finish()

    def _finish(self) -> None:
        if self.is_finished:
            return
        self.is_finished = True
        self.is_running = False
        self._publish_backtest_finished()

    def _publish_new_candle(self) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(
            NEW_CANDLE,
            {
                "candle": self.current_candle,
                "current_index": self.current_index,
                "total_candles": len(self.candles),
            },
        )

    def _publish_backtest_finished(self) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(
            BACKTEST_FINISHED,
            {"total_candles": len(self.candles)},
        )
