"""Configuracao parametrizavel da Alpha 001 IORB."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta


TIME_FORMAT = "%H:%M"
DEFAULT_OPENING_RANGE_START_TIME = "09:00"
DEFAULT_OPENING_RANGE_DURATION_MINUTES = 15
DEFAULT_INITIAL_STOP_POINTS = 50.0
DEFAULT_INITIAL_TARGET_POINTS = 100.0
DEFAULT_MINIMUM_SCORE = 0
DEFAULT_MINIMUM_CONFIDENCE = 0.0
DEFAULT_MINIMUM_RANGE_SIZE = 20.0
DEFAULT_MINIMUM_VOLUME = 1000.0
DEFAULT_ALLOWED_REGIMES: tuple[str, ...] = ()


@dataclass(frozen=True)
class Alpha001Config:
    """Parametros da Alpha 001 recebidos por injecao de dependencia."""

    opening_range_start_time: str = DEFAULT_OPENING_RANGE_START_TIME
    opening_range_duration_minutes: int = DEFAULT_OPENING_RANGE_DURATION_MINUTES
    initial_stop_points: float = DEFAULT_INITIAL_STOP_POINTS
    initial_target_points: float = DEFAULT_INITIAL_TARGET_POINTS
    minimum_score: int = DEFAULT_MINIMUM_SCORE
    minimum_confidence: float = DEFAULT_MINIMUM_CONFIDENCE
    minimum_range_size: float = DEFAULT_MINIMUM_RANGE_SIZE
    minimum_volume: float = DEFAULT_MINIMUM_VOLUME
    allowed_regimes: tuple[str, ...] = DEFAULT_ALLOWED_REGIMES

    @property
    def opening_range_end_time(self) -> str:
        """Retorna fim da Opening Range derivado do inicio e duracao."""
        start = datetime.strptime(self.opening_range_start_time, TIME_FORMAT)
        end = start + timedelta(minutes=self.opening_range_duration_minutes)
        return end.strftime(TIME_FORMAT)

    def with_overrides(
        self,
        *,
        minimum_range_size: float | None = None,
        minimum_volume: float | None = None,
    ) -> "Alpha001Config":
        """Retorna uma copia com overrides legados opcionais."""
        updates: dict[str, float] = {}
        if minimum_range_size is not None:
            updates["minimum_range_size"] = minimum_range_size
        if minimum_volume is not None:
            updates["minimum_volume"] = minimum_volume
        if not updates:
            return self
        return replace(self, **updates)

    def normalized_allowed_regimes(self) -> tuple[str, ...]:
        """Normaliza regimes configurados para comparacao segura."""
        return tuple(regime.strip().upper() for regime in self.allowed_regimes)
