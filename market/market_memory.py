"""Memoria estatistica em memoria para snapshots de mercado."""

from dataclasses import dataclass, field
from datetime import datetime

from market.feature_engine import FeatureSnapshot
from market.regime_engine import RegimeAnalysis


@dataclass(frozen=True)
class MarketMemoryRecord:
    """Registro historico para comparacao futura de contexto de mercado."""

    timestamp: datetime
    regime: str
    direction: str
    momentum: float
    volatility: str
    trend_strength: float


@dataclass
class MarketMemory:
    """Armazena registros estatisticos recentes apenas em memoria."""

    records: list[MarketMemoryRecord] = field(default_factory=list)

    def remember(
        self,
        feature_snapshot: FeatureSnapshot,
        regime_analysis: RegimeAnalysis,
    ) -> MarketMemoryRecord:
        """Armazena um novo registro combinando features e regime."""
        record = MarketMemoryRecord(
            timestamp=datetime.now(),
            regime=regime_analysis.regime.value,
            direction=feature_snapshot.direction,
            momentum=feature_snapshot.momentum,
            volatility=feature_snapshot.volatility_level,
            trend_strength=feature_snapshot.trend_strength,
        )
        self.records.append(record)
        return record

    def count(self) -> int:
        """Retorna a quantidade de registros armazenados."""
        return len(self.records)

    def clear(self) -> None:
        """Remove todos os registros da memoria."""
        self.records.clear()

    def last(self) -> MarketMemoryRecord | None:
        """Retorna o ultimo registro armazenado."""
        if not self.records:
            return None
        return self.records[-1]

    def all(self) -> list[MarketMemoryRecord]:
        """Retorna todos os registros armazenados."""
        return list(self.records)

    def find_by_regime(self, regime: str) -> list[MarketMemoryRecord]:
        """Busca registros pelo regime de mercado."""
        return [record for record in self.records if record.regime == regime]

    def find_by_direction(self, direction: str) -> list[MarketMemoryRecord]:
        """Busca registros pela direcao do mercado."""
        return [
            record for record in self.records if record.direction == direction
        ]

    def find_similar(
        self,
        feature_snapshot: FeatureSnapshot,
        regime_analysis: RegimeAnalysis,
        tolerance: float = 0.20,
    ) -> list[MarketMemoryRecord]:
        """Busca cenarios similares aos parametros informados."""
        return [
            record for record in self.records
            if self._is_similar(
                record,
                feature_snapshot,
                regime_analysis,
                tolerance,
            )
        ]

    def _is_similar(
        self,
        record: MarketMemoryRecord,
        feature_snapshot: FeatureSnapshot,
        regime_analysis: RegimeAnalysis,
        tolerance: float,
    ) -> bool:
        return (
            record.regime == regime_analysis.regime.value
            and record.direction == feature_snapshot.direction
            and self._within_tolerance(
                record.momentum,
                feature_snapshot.momentum,
                tolerance,
            )
            and self._within_tolerance(
                record.trend_strength,
                feature_snapshot.trend_strength,
                tolerance,
            )
        )

    def _within_tolerance(
        self,
        stored_value: float,
        target_value: float,
        tolerance: float,
    ) -> bool:
        if target_value == 0:
            return stored_value == 0
        allowed_difference = abs(target_value) * tolerance
        return abs(stored_value - target_value) <= allowed_difference
