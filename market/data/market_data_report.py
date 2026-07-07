"""Relatorio oficial do Data Lab."""

from __future__ import annotations

from dataclasses import dataclass

from market.data.candle_validator import CandleValidationResult
from market.data.market_data_contract import MarketDataContract
from market.data.market_data_quality_engine import MarketDataQualityResult


@dataclass(frozen=True)
class MarketDataReport:
    """Consolida resultados produzidos pelos componentes de dados."""

    candles: tuple[MarketDataContract, ...]
    validation_results: tuple[CandleValidationResult, ...]
    quality_result: MarketDataQualityResult
    total_candles: int
    valid_candles: int
    invalid_candles: int
    duplicated_candles: int
    missing_candles: int
    quality_score: float
    execution_time: float
