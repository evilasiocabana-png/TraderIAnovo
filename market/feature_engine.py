"""Motor oficial de features de mercado do TraderIA_WDO."""

from dataclasses import dataclass, field

from market.candle_history import CandleHistory
from market.temporal_analyzer import TemporalMarketAnalyzer


@dataclass(frozen=True)
class FeatureSnapshot:
    """Conjunto de features derivadas dos candles recentes."""

    momentum: float
    average_range: float
    highest_high: float | None
    lowest_low: float | None
    direction: str
    candles_count: int
    trend_strength: float
    volatility_level: str


@dataclass
class FeatureEngine:
    """Calcula e armazena features derivadas do mercado."""

    temporal_analyzer: TemporalMarketAnalyzer = field(
        default_factory=TemporalMarketAnalyzer,
    )
    current_snapshot: FeatureSnapshot | None = None

    def build(self, candle_history: CandleHistory) -> FeatureSnapshot:
        """Cria um snapshot de features a partir do historico de candles."""
        analysis = self.temporal_analyzer.analyze(candle_history)
        trend_strength = self._trend_strength(
            analysis.momentum,
            analysis.average_range,
        )

        self.current_snapshot = FeatureSnapshot(
            momentum=analysis.momentum,
            average_range=analysis.average_range,
            highest_high=analysis.highest_high,
            lowest_low=analysis.lowest_low,
            direction=analysis.direction,
            candles_count=analysis.candles_count,
            trend_strength=trend_strength,
            volatility_level=self._volatility_level(analysis.average_range),
        )
        return self.current_snapshot

    def get_feature(self, nome: str) -> object | None:
        """Retorna uma feature do ultimo snapshot calculado."""
        if self.current_snapshot is None:
            return None
        return getattr(self.current_snapshot, nome, None)

    def _trend_strength(self, momentum: float, average_range: float) -> float:
        if average_range == 0:
            return 0.0
        return abs(momentum) / average_range

    def _volatility_level(self, average_range: float) -> str:
        if average_range < 10:
            return "LOW"
        if average_range < 30:
            return "MEDIUM"
        return "HIGH"
