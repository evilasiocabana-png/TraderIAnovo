"""Servico de aplicacao para configuracoes do sistema."""

from dataclasses import dataclass
from typing import Any

from core.configuration_manager import ConfigurationManager, SystemConfiguration


@dataclass(frozen=True)
class ConfigurationData:
    """Configuracao pronta para consumo do dashboard."""

    symbol: str
    initial_capital: float
    contracts: int
    stop_points: float
    target_points: float
    max_daily_loss: float
    max_daily_gain: float
    minimum_score: int
    minimum_confidence: float
    simulation_mode: bool
    version: str
    quantitative_score_candles_loaded: int
    quantitative_score_feature_lookback: int
    quantitative_score_forward_return_candles: int
    quantitative_score_fast_ma_period: int
    quantitative_score_slow_ma_period: int
    quantitative_score_rsi_period: int
    quantitative_score_atr_period: int
    quantitative_score_volatility_period: int
    quantitative_score_min_sample_size: int
    quantitative_score_min_profit_factor: float
    quantitative_score_min_win_rate: float
    quantitative_score_max_allowed_drawdown: float
    quantitative_score_confidence_floor: float
    quantitative_score_confidence_ceiling: float
    quantitative_score_volatility_bucket_method: str
    quantitative_score_volatility_low_threshold: float
    quantitative_score_volatility_high_threshold: float
    quantitative_score_ma_flat_threshold: float
    quantitative_score_ma_strong_threshold: float
    quantitative_score_rsi_oversold_threshold: float
    quantitative_score_rsi_overbought_threshold: float
    timeframe_optimizer_timeframes: tuple[str, ...]
    timeframe_optimizer_min_sample_size: int
    timeframe_optimizer_min_profit_factor: float
    timeframe_optimizer_min_win_rate: float
    timeframe_optimizer_max_allowed_drawdown: float
    timeframe_optimizer_min_confidence: float
    mt5_fast_refresh_enabled: bool
    research_recalculate_on_every_refresh: bool
    timeframe_optimizer_auto_run: bool
    mt5_diagnostics_compact_mode: bool
    mt5_safe_mode: bool
    mt5_safe_mode_candles_loaded: int
    mt5_safe_mode_fast_ma_period: int
    mt5_safe_mode_mid_ma_period: int
    mt5_safe_mode_slow_ma_period: int
    mt5_safe_mode_adx_period: int
    mt5_safe_mode_adx_trend_min: float
    mt5_safe_mode_rsi_period: int
    mt5_safe_mode_rsi_buy_min: float
    mt5_safe_mode_rsi_sell_max: float
    mt5_safe_mode_rsi_overbought: float
    mt5_safe_mode_rsi_oversold: float
    mt5_safe_mode_macd_fast: int
    mt5_safe_mode_macd_slow: int
    mt5_safe_mode_macd_signal: int
    mt5_safe_mode_atr_period: int
    mt5_safe_mode_atr_baseline_period: int
    mt5_safe_mode_bollinger_period: int
    mt5_safe_mode_bollinger_std: float
    mt5_safe_mode_tick_volume_period: int
    mt5_safe_mode_momentum_period: int
    mt5_safe_mode_volatility_period: int
    mt5_safe_mode_volatility_low_threshold: float
    mt5_safe_mode_ma_flat_threshold: float
    forex_session_filter_enabled: bool


@dataclass(frozen=True)
class ConfigurationService:
    """Expoe e atualiza configuracoes via camada de aplicacao."""

    def get_configuration_data(self) -> ConfigurationData:
        """Retorna a configuracao atual em formato de apresentacao."""
        return self._to_data(ConfigurationManager.get_configuration())

    def update_configuration(self, **kwargs: Any) -> ConfigurationData:
        """Atualiza configuracoes basicas usando o ConfigurationManager."""
        configuration = ConfigurationManager.update_configuration(**kwargs)
        return self._to_data(configuration)

    def save_preset(self, name: str) -> None:
        """Salva a configuracao atual como preset."""
        ConfigurationManager.save_preset(name)

    def load_preset(self, name: str) -> ConfigurationData:
        """Carrega um preset salvo."""
        return self._to_data(ConfigurationManager.load_preset(name))

    def list_presets(self) -> list[str]:
        """Lista presets salvos."""
        return ConfigurationManager.list_presets()

    def delete_preset(self, name: str) -> None:
        """Exclui preset salvo."""
        ConfigurationManager.delete_preset(name)

    def _to_data(self, configuration: SystemConfiguration) -> ConfigurationData:
        return ConfigurationData(
            symbol=configuration.symbol,
            initial_capital=configuration.initial_capital,
            contracts=configuration.contracts,
            stop_points=configuration.stop_points,
            target_points=configuration.target_points,
            max_daily_loss=configuration.max_daily_loss,
            max_daily_gain=configuration.max_daily_gain,
            minimum_score=configuration.minimum_score,
            minimum_confidence=configuration.minimum_confidence,
            simulation_mode=configuration.simulation_mode,
            version=configuration.version,
            quantitative_score_candles_loaded=(
                configuration.quantitative_score_candles_loaded
            ),
            quantitative_score_feature_lookback=(
                configuration.quantitative_score_feature_lookback
            ),
            quantitative_score_forward_return_candles=(
                configuration.quantitative_score_forward_return_candles
            ),
            quantitative_score_fast_ma_period=(
                configuration.quantitative_score_fast_ma_period
            ),
            quantitative_score_slow_ma_period=(
                configuration.quantitative_score_slow_ma_period
            ),
            quantitative_score_rsi_period=(
                configuration.quantitative_score_rsi_period
            ),
            quantitative_score_atr_period=(
                configuration.quantitative_score_atr_period
            ),
            quantitative_score_volatility_period=(
                configuration.quantitative_score_volatility_period
            ),
            quantitative_score_min_sample_size=(
                configuration.quantitative_score_min_sample_size
            ),
            quantitative_score_min_profit_factor=(
                configuration.quantitative_score_min_profit_factor
            ),
            quantitative_score_min_win_rate=(
                configuration.quantitative_score_min_win_rate
            ),
            quantitative_score_max_allowed_drawdown=(
                configuration.quantitative_score_max_allowed_drawdown
            ),
            quantitative_score_confidence_floor=(
                configuration.quantitative_score_confidence_floor
            ),
            quantitative_score_confidence_ceiling=(
                configuration.quantitative_score_confidence_ceiling
            ),
            quantitative_score_volatility_bucket_method=(
                configuration.quantitative_score_volatility_bucket_method
            ),
            quantitative_score_volatility_low_threshold=(
                configuration.quantitative_score_volatility_low_threshold
            ),
            quantitative_score_volatility_high_threshold=(
                configuration.quantitative_score_volatility_high_threshold
            ),
            quantitative_score_ma_flat_threshold=(
                configuration.quantitative_score_ma_flat_threshold
            ),
            quantitative_score_ma_strong_threshold=(
                configuration.quantitative_score_ma_strong_threshold
            ),
            quantitative_score_rsi_oversold_threshold=(
                configuration.quantitative_score_rsi_oversold_threshold
            ),
            quantitative_score_rsi_overbought_threshold=(
                configuration.quantitative_score_rsi_overbought_threshold
            ),
            timeframe_optimizer_timeframes=(
                configuration.timeframe_optimizer_timeframes
            ),
            timeframe_optimizer_min_sample_size=(
                configuration.timeframe_optimizer_min_sample_size
            ),
            timeframe_optimizer_min_profit_factor=(
                configuration.timeframe_optimizer_min_profit_factor
            ),
            timeframe_optimizer_min_win_rate=(
                configuration.timeframe_optimizer_min_win_rate
            ),
            timeframe_optimizer_max_allowed_drawdown=(
                configuration.timeframe_optimizer_max_allowed_drawdown
            ),
            timeframe_optimizer_min_confidence=(
                configuration.timeframe_optimizer_min_confidence
            ),
            mt5_fast_refresh_enabled=configuration.mt5_fast_refresh_enabled,
            research_recalculate_on_every_refresh=(
                configuration.research_recalculate_on_every_refresh
            ),
            timeframe_optimizer_auto_run=configuration.timeframe_optimizer_auto_run,
            mt5_diagnostics_compact_mode=configuration.mt5_diagnostics_compact_mode,
            mt5_safe_mode=configuration.mt5_safe_mode,
            mt5_safe_mode_candles_loaded=configuration.mt5_safe_mode_candles_loaded,
            mt5_safe_mode_fast_ma_period=configuration.mt5_safe_mode_fast_ma_period,
            mt5_safe_mode_mid_ma_period=configuration.mt5_safe_mode_mid_ma_period,
            mt5_safe_mode_slow_ma_period=configuration.mt5_safe_mode_slow_ma_period,
            mt5_safe_mode_adx_period=configuration.mt5_safe_mode_adx_period,
            mt5_safe_mode_adx_trend_min=configuration.mt5_safe_mode_adx_trend_min,
            mt5_safe_mode_rsi_period=configuration.mt5_safe_mode_rsi_period,
            mt5_safe_mode_rsi_buy_min=configuration.mt5_safe_mode_rsi_buy_min,
            mt5_safe_mode_rsi_sell_max=configuration.mt5_safe_mode_rsi_sell_max,
            mt5_safe_mode_rsi_overbought=configuration.mt5_safe_mode_rsi_overbought,
            mt5_safe_mode_rsi_oversold=configuration.mt5_safe_mode_rsi_oversold,
            mt5_safe_mode_macd_fast=configuration.mt5_safe_mode_macd_fast,
            mt5_safe_mode_macd_slow=configuration.mt5_safe_mode_macd_slow,
            mt5_safe_mode_macd_signal=configuration.mt5_safe_mode_macd_signal,
            mt5_safe_mode_atr_period=configuration.mt5_safe_mode_atr_period,
            mt5_safe_mode_atr_baseline_period=(
                configuration.mt5_safe_mode_atr_baseline_period
            ),
            mt5_safe_mode_bollinger_period=configuration.mt5_safe_mode_bollinger_period,
            mt5_safe_mode_bollinger_std=configuration.mt5_safe_mode_bollinger_std,
            mt5_safe_mode_tick_volume_period=(
                configuration.mt5_safe_mode_tick_volume_period
            ),
            mt5_safe_mode_momentum_period=(
                configuration.mt5_safe_mode_momentum_period
            ),
            mt5_safe_mode_volatility_period=(
                configuration.mt5_safe_mode_volatility_period
            ),
            mt5_safe_mode_volatility_low_threshold=(
                configuration.mt5_safe_mode_volatility_low_threshold
            ),
            mt5_safe_mode_ma_flat_threshold=(
                configuration.mt5_safe_mode_ma_flat_threshold
            ),
            forex_session_filter_enabled=configuration.forex_session_filter_enabled,
        )
