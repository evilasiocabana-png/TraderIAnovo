"""Pipeline oficial de preparacao dos dados de mercado."""

from dataclasses import dataclass, field

from market.data.candle_validator import CandleValidationResult, CandleValidator
from market.data.market_data_contract import MarketDataContract
from market.data.market_data_quality_engine import (
    MarketDataQualityEngine,
    MarketDataQualityResult,
)


@dataclass(frozen=True)
class NormalizedMarketData:
    """Resultado consolidado da preparacao de dados de mercado."""

    candles: tuple[MarketDataContract, ...]
    validation_results: tuple[CandleValidationResult, ...]
    quality_result: MarketDataQualityResult


@dataclass(frozen=True)
class DataPipeline:
    """Orquestra validacao e qualidade sem modificar candles."""

    candle_validator: CandleValidator = field(default_factory=CandleValidator)
    quality_engine: MarketDataQualityEngine = field(
        default_factory=MarketDataQualityEngine,
    )

    def prepare(
        self,
        candles: tuple[MarketDataContract, ...],
    ) -> NormalizedMarketData:
        """Executa a sequencia oficial de preparacao de dados."""
        validation_results = tuple(
            self.candle_validator.validate(candle)
            for candle in candles
        )
        quality_result = self.quality_engine.evaluate(candles)
        return NormalizedMarketData(
            candles=candles,
            validation_results=validation_results,
            quality_result=quality_result,
        )
