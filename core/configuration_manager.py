"""Gerenciador central de configuracoes do sistema."""

from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class SystemConfiguration:
    """Configuracao central do TraderIA_WDO."""

    symbol: str = "WDO"
    initial_capital: float = 0.0
    contracts: int = 1
    stop_points: float = 50.0
    target_points: float = 100.0
    max_daily_loss: float = -300.0
    max_daily_gain: float = 500.0
    minimum_score: int = 70
    minimum_confidence: float = 0.0
    simulation_mode: bool = True
    version: str = "0.3.0"
    max_daily_operations: int = 5
    quantitative_score_candles_loaded: int = 5000
    quantitative_score_feature_lookback: int = 50
    quantitative_score_forward_return_candles: int = 10
    quantitative_score_fast_ma_period: int = 9
    quantitative_score_slow_ma_period: int = 21
    quantitative_score_rsi_period: int = 14
    quantitative_score_atr_period: int = 14
    quantitative_score_volatility_period: int = 14
    quantitative_score_min_sample_size: int = 30
    quantitative_score_min_profit_factor: float = 1.3
    quantitative_score_min_win_rate: float = 0.55
    quantitative_score_max_allowed_drawdown: float = 0.05
    quantitative_score_confidence_floor: float = 0.2
    quantitative_score_confidence_ceiling: float = 0.95
    quantitative_score_volatility_bucket_method: str = "ATR"
    quantitative_score_volatility_low_threshold: float = 0.0001
    quantitative_score_volatility_high_threshold: float = 0.0003
    quantitative_score_ma_flat_threshold: float = 0.0001
    quantitative_score_ma_strong_threshold: float = 0.001
    quantitative_score_rsi_oversold_threshold: float = 30.0
    quantitative_score_rsi_overbought_threshold: float = 70.0
    timeframe_optimizer_timeframes: tuple[str, ...] = (
        "M1",
        "M5",
        "M15",
        "M30",
        "H1",
    )
    timeframe_optimizer_min_sample_size: int = 30
    timeframe_optimizer_min_profit_factor: float = 1.3
    timeframe_optimizer_min_win_rate: float = 0.55
    timeframe_optimizer_max_allowed_drawdown: float = 0.05
    timeframe_optimizer_min_confidence: float = 0.2
    mt5_fast_refresh_enabled: bool = True
    research_recalculate_on_every_refresh: bool = False
    timeframe_optimizer_auto_run: bool = False
    mt5_diagnostics_compact_mode: bool = True
    mt5_safe_mode: bool = True
    mt5_safe_mode_candles_loaded: int = 1000
    mt5_safe_mode_fast_ma_period: int = 20
    mt5_safe_mode_mid_ma_period: int = 50
    mt5_safe_mode_slow_ma_period: int = 50
    mt5_safe_mode_adx_period: int = 14
    mt5_safe_mode_adx_trend_min: float = 25.0
    mt5_safe_mode_rsi_period: int = 14
    mt5_safe_mode_rsi_buy_min: float = 55.0
    mt5_safe_mode_rsi_sell_max: float = 45.0
    mt5_safe_mode_rsi_overbought: float = 70.0
    mt5_safe_mode_rsi_oversold: float = 30.0
    mt5_safe_mode_macd_fast: int = 12
    mt5_safe_mode_macd_slow: int = 26
    mt5_safe_mode_macd_signal: int = 9
    mt5_safe_mode_atr_period: int = 14
    mt5_safe_mode_atr_baseline_period: int = 20
    mt5_safe_mode_bollinger_period: int = 20
    mt5_safe_mode_bollinger_std: float = 2.0
    mt5_safe_mode_tick_volume_period: int = 20
    mt5_safe_mode_momentum_period: int = 10
    mt5_safe_mode_volatility_period: int = 20
    mt5_safe_mode_volatility_low_threshold: float = 0.00001
    mt5_safe_mode_ma_flat_threshold: float = 0.00005
    forex_session_filter_enabled: bool = False
    dynamic_exit_simulation_enabled: bool = False
    dynamic_exit_demo_sl_assisted_execution_enabled: bool = False


class ConfigurationManager:
    """Mantem uma unica instancia de configuracao em memoria."""

    _configuration = SystemConfiguration()
    _presets: dict[str, SystemConfiguration] = {}

    @classmethod
    def get_configuration(cls) -> SystemConfiguration:
        """Retorna a configuracao atual."""
        return cls._configuration

    @classmethod
    def update_configuration(cls, **kwargs: Any) -> SystemConfiguration:
        """Atualiza campos da configuracao apos validacao."""
        cls._validate_fields(kwargs)
        cls._validate_values(kwargs)
        cls._configuration = replace(cls._configuration, **kwargs)
        return cls._configuration

    @classmethod
    def reset_configuration(cls) -> None:
        """Restaura a configuracao padrao em memoria."""
        cls._configuration = SystemConfiguration()
        cls._presets = {}

    @classmethod
    def save_preset(cls, name: str) -> None:
        """Salva a configuracao atual como preset em memoria."""
        preset_name = cls._validate_preset_name(name)
        cls._presets[preset_name] = cls._configuration

    @classmethod
    def load_preset(cls, name: str) -> SystemConfiguration:
        """Carrega um preset salvo em memoria."""
        preset_name = cls._validate_preset_name(name)
        if preset_name not in cls._presets:
            raise ValueError(f"Preset nao encontrado: {preset_name}")

        cls._configuration = cls._presets[preset_name]
        return cls._configuration

    @classmethod
    def list_presets(cls) -> list[str]:
        """Lista nomes de presets salvos."""
        return sorted(cls._presets)

    @classmethod
    def delete_preset(cls, name: str) -> None:
        """Exclui um preset salvo em memoria."""
        preset_name = cls._validate_preset_name(name)
        if preset_name not in cls._presets:
            raise ValueError(f"Preset nao encontrado: {preset_name}")

        del cls._presets[preset_name]

    @classmethod
    def _validate_fields(cls, values: dict[str, Any]) -> None:
        valid_fields = SystemConfiguration.__dataclass_fields__
        invalid = [field for field in values if field not in valid_fields]
        if invalid:
            raise ValueError(f"Campos invalidos: {', '.join(invalid)}")

    @classmethod
    def _validate_values(cls, values: dict[str, Any]) -> None:
        non_negative = {
            "initial_capital",
            "contracts",
            "stop_points",
            "target_points",
            "max_daily_gain",
            "minimum_score",
            "minimum_confidence",
            "max_daily_operations",
            "quantitative_score_candles_loaded",
            "quantitative_score_feature_lookback",
            "quantitative_score_forward_return_candles",
            "quantitative_score_fast_ma_period",
            "quantitative_score_slow_ma_period",
            "quantitative_score_rsi_period",
            "quantitative_score_atr_period",
            "quantitative_score_volatility_period",
            "quantitative_score_min_sample_size",
            "quantitative_score_min_profit_factor",
            "quantitative_score_min_win_rate",
            "quantitative_score_max_allowed_drawdown",
            "quantitative_score_confidence_floor",
            "quantitative_score_confidence_ceiling",
            "quantitative_score_volatility_low_threshold",
            "quantitative_score_volatility_high_threshold",
            "quantitative_score_ma_flat_threshold",
            "quantitative_score_ma_strong_threshold",
            "quantitative_score_rsi_oversold_threshold",
            "quantitative_score_rsi_overbought_threshold",
            "timeframe_optimizer_min_sample_size",
            "timeframe_optimizer_min_profit_factor",
            "timeframe_optimizer_min_win_rate",
            "timeframe_optimizer_max_allowed_drawdown",
            "timeframe_optimizer_min_confidence",
            "mt5_safe_mode_candles_loaded",
            "mt5_safe_mode_fast_ma_period",
            "mt5_safe_mode_mid_ma_period",
            "mt5_safe_mode_slow_ma_period",
            "mt5_safe_mode_adx_period",
            "mt5_safe_mode_adx_trend_min",
            "mt5_safe_mode_rsi_period",
            "mt5_safe_mode_rsi_buy_min",
            "mt5_safe_mode_rsi_sell_max",
            "mt5_safe_mode_rsi_overbought",
            "mt5_safe_mode_rsi_oversold",
            "mt5_safe_mode_macd_fast",
            "mt5_safe_mode_macd_slow",
            "mt5_safe_mode_macd_signal",
            "mt5_safe_mode_atr_period",
            "mt5_safe_mode_atr_baseline_period",
            "mt5_safe_mode_bollinger_period",
            "mt5_safe_mode_bollinger_std",
            "mt5_safe_mode_tick_volume_period",
            "mt5_safe_mode_momentum_period",
            "mt5_safe_mode_volatility_period",
            "mt5_safe_mode_volatility_low_threshold",
            "mt5_safe_mode_ma_flat_threshold",
        }
        for field in non_negative.intersection(values):
            if values[field] is None:
                continue
            if values[field] < 0:
                raise ValueError(f"{field} nao pode ser negativo")

    @classmethod
    def _validate_preset_name(cls, name: str) -> str:
        preset_name = name.strip()
        if not preset_name:
            raise ValueError("Nome do preset nao pode ser vazio")
        return preset_name
