"""Strategy oficial da Alpha101."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from statistics import mean

from domain.candle import Candle
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.strategy_signal import StrategySignal
from domain.market_state import MarketState
from strategies.alpha101.alpha101_config import Alpha101Config
from strategies.base import Strategy


MINIMUM_MOMENTUM_5D = 0.0
MINIMUM_VOLUME_RATIO_20 = 1.2
MINIMUM_DONCHIAN_POSITION_20 = 0.80
MAXIMUM_ATR14_PCT = 0.08
MAXIMUM_DISTANCE_MA200 = 0.50


@dataclass(frozen=True)
class Alpha101Features:
    """Features internas da Alpha101."""

    ret_5d: float
    volume_ratio_20: float
    donchian_pos20: float
    atr14_pct: float
    dist_ma_200: float


def _default_config() -> Alpha101Config:
    return Alpha101Config(
        timeframe="1d",
        holding_period="5d",
        stop_points=0.0,
        target_points=0.0,
        minimum_volume=MINIMUM_VOLUME_RATIO_20,
        minimum_volatility=0.0,
        minimum_confidence=0.6,
        risk_profile="research-only",
    )


@dataclass(frozen=True)
class Alpha101Strategy(Strategy):
    """Alpha101 Daily Volume Momentum Breakout para PETR4 diario."""

    config: Alpha101Config = field(default_factory=_default_config)
    nome: str = "alpha101"

    def analisar(self, estado: MarketState) -> StrategySignal:
        """Retorna WAIT quando nao ha historico suficiente para Alpha101."""
        return StrategySignal(
            decision="WAIT",
            score=0,
            confidence=0.0,
            reasons=[
                "Alpha101 requer historico diario para ret_5d, volume_ratio_20, "
                "donchian_pos20, atr14_pct e dist_ma_200"
            ],
        )

    def generate_signal(
        self,
        *args: object,
        candles: list[Candle] | tuple[Candle, ...] | None = None,
        market_snapshot: MarketSnapshot | None = None,
        current_price: float | None = None,
        **_: object,
    ) -> StrategySignal:
        """Gera StrategySignal usando somente candles ja processados."""
        if candles is None:
            return self._wait(
                [
                    "Alpha101 requer candles historicos para avaliar a tese "
                    "volume momentum breakout"
                ]
            )
        candle_list = list(candles)
        if len(candle_list) < 200:
            return self._wait(
                [
                    "historico insuficiente para Alpha101",
                    "necessario minimo de 200 candles para MM200",
                ]
            )

        features = self._features(candle_list)
        rejection_reasons = self._rejection_reasons(features)
        if rejection_reasons:
            return self._wait(rejection_reasons)

        return StrategySignal(
            decision="BUY",
            score=self._score(features),
            confidence=self._confidence(features),
            reasons=[
                "momentum de 5 dias positivo",
                "volume acima da media de 20 dias",
                "fechamento proximo da maxima de 20 dias",
                "volatilidade e esticamento dentro dos limites da Alpha101",
            ],
        )

    def _features(self, candles: list[Candle]) -> Alpha101Features:
        close = float(candles[-1].fechamento)
        previous_5d_close = float(candles[-6].fechamento)
        volumes_20 = [float(candle.volume) for candle in candles[-20:]]
        highs_20 = [float(candle.maxima) for candle in candles[-20:]]
        lows_20 = [float(candle.minima) for candle in candles[-20:]]
        ma200 = mean(float(candle.fechamento) for candle in candles[-200:])
        range_20 = max(highs_20) - min(lows_20)

        return Alpha101Features(
            ret_5d=close / previous_5d_close - 1,
            volume_ratio_20=float(candles[-1].volume) / mean(volumes_20),
            donchian_pos20=self._safe_ratio(close - min(lows_20), range_20),
            atr14_pct=self._atr14_pct(candles),
            dist_ma_200=close / ma200 - 1,
        )

    def _rejection_reasons(self, features: Alpha101Features) -> list[str]:
        reasons: list[str] = []
        if features.ret_5d <= MINIMUM_MOMENTUM_5D:
            reasons.append("momentum de 5 dias nao positivo")
        if features.volume_ratio_20 < MINIMUM_VOLUME_RATIO_20:
            reasons.append("volume relativo de 20 dias abaixo do minimo")
        if features.donchian_pos20 < MINIMUM_DONCHIAN_POSITION_20:
            reasons.append("fechamento distante do topo de 20 dias")
        if features.atr14_pct > MAXIMUM_ATR14_PCT:
            reasons.append("ATR14 percentual acima do limite de risco")
        if features.dist_ma_200 > MAXIMUM_DISTANCE_MA200:
            reasons.append("distancia da MM200 acima do limite de esticamento")
        if not all(
            isfinite(value)
            for value in (
                features.ret_5d,
                features.volume_ratio_20,
                features.donchian_pos20,
                features.atr14_pct,
                features.dist_ma_200,
            )
        ):
            reasons.append("features invalidas ou nao finitas")
        return reasons

    def _atr14_pct(self, candles: list[Candle]) -> float:
        true_ranges: list[float] = []
        for index in range(len(candles) - 14, len(candles)):
            candle = candles[index]
            previous_close = float(candles[index - 1].fechamento)
            high = float(candle.maxima)
            low = float(candle.minima)
            true_ranges.append(
                max(
                    high - low,
                    abs(high - previous_close),
                    abs(low - previous_close),
                )
            )
        return mean(true_ranges) / float(candles[-1].fechamento)

    def _safe_ratio(self, numerator: float, denominator: float) -> float:
        if denominator == 0:
            return 0.0
        return numerator / denominator

    def _confidence(self, features: Alpha101Features) -> float:
        components = [
            min(max(features.ret_5d / 0.05, 0.0), 1.0),
            min(max((features.volume_ratio_20 - 1.0) / 1.0, 0.0), 1.0),
            min(max(features.donchian_pos20, 0.0), 1.0),
            1.0 - min(max(features.atr14_pct / MAXIMUM_ATR14_PCT, 0.0), 1.0),
            1.0 - min(max(features.dist_ma_200 / MAXIMUM_DISTANCE_MA200, 0.0), 1.0),
        ]
        return max(0.0, min(mean(components), 1.0))

    def _score(self, features: Alpha101Features) -> int:
        return int(round(self._confidence(features) * 100))

    def _wait(self, reasons: list[str]) -> StrategySignal:
        return StrategySignal(
            decision="WAIT",
            score=0,
            confidence=0.0,
            reasons=reasons,
        )
