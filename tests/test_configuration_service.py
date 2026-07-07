"""Testes do servico de aplicacao de configuracoes."""

import unittest

from application.configuration_service import ConfigurationData, ConfigurationService
from core.configuration_manager import ConfigurationManager


class ConfigurationServiceTest(unittest.TestCase):
    """Valida exposicao e atualizacao de configuracoes."""

    def setUp(self) -> None:
        """Restaura configuracao padrao antes de cada teste."""
        ConfigurationManager.reset_configuration()

    def test_expoe_configuracao_atual(self) -> None:
        """Garante leitura da configuracao atual."""
        data = ConfigurationService().get_configuration_data()

        self.assertIsInstance(data, ConfigurationData)
        self.assertEqual(data.symbol, "WDO")
        self.assertEqual(data.initial_capital, 0.0)

    def test_atualiza_configuracoes_basicas(self) -> None:
        """Garante atualizacao via ConfigurationManager."""
        data = ConfigurationService().update_configuration(
            symbol="WIN",
            contracts=2,
        )

        self.assertEqual(data.symbol, "WIN")
        self.assertEqual(data.contracts, 2)

    def test_expoe_parametros_quantitative_score(self) -> None:
        """Garante painel read-only com parametros do Research Lab."""
        data = ConfigurationService().update_configuration(
            quantitative_score_candles_loaded=5000,
            quantitative_score_feature_lookback=50,
            quantitative_score_forward_return_candles=10,
            quantitative_score_fast_ma_period=9,
            quantitative_score_slow_ma_period=21,
            quantitative_score_atr_period=14,
            quantitative_score_min_sample_size=30,
            quantitative_score_min_profit_factor=1.3,
            quantitative_score_min_win_rate=0.55,
            quantitative_score_max_allowed_drawdown=0.05,
            quantitative_score_confidence_floor=0.2,
        )

        self.assertEqual(data.quantitative_score_candles_loaded, 5000)
        self.assertEqual(data.quantitative_score_feature_lookback, 50)
        self.assertEqual(data.quantitative_score_forward_return_candles, 10)
        self.assertEqual(data.quantitative_score_fast_ma_period, 9)
        self.assertEqual(data.quantitative_score_slow_ma_period, 21)
        self.assertEqual(data.quantitative_score_atr_period, 14)
        self.assertEqual(data.quantitative_score_min_sample_size, 30)
        self.assertEqual(data.quantitative_score_min_profit_factor, 1.3)
        self.assertEqual(data.quantitative_score_min_win_rate, 0.55)
        self.assertEqual(data.quantitative_score_max_allowed_drawdown, 0.05)
        self.assertEqual(data.quantitative_score_confidence_floor, 0.2)

    def test_configuration_data_expoe_campos_do_painel_research_configuration(
        self,
    ) -> None:
        """Garante que o painel nao referencia campos ausentes no DTO."""
        data = ConfigurationService().get_configuration_data()
        required_fields = {
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
            "quantitative_score_volatility_bucket_method",
            "quantitative_score_volatility_low_threshold",
            "quantitative_score_volatility_high_threshold",
            "quantitative_score_ma_flat_threshold",
            "quantitative_score_ma_strong_threshold",
            "quantitative_score_rsi_oversold_threshold",
            "quantitative_score_rsi_overbought_threshold",
            "timeframe_optimizer_timeframes",
            "timeframe_optimizer_min_sample_size",
            "timeframe_optimizer_min_profit_factor",
            "timeframe_optimizer_min_win_rate",
            "timeframe_optimizer_max_allowed_drawdown",
            "timeframe_optimizer_min_confidence",
            "mt5_fast_refresh_enabled",
            "research_recalculate_on_every_refresh",
            "timeframe_optimizer_auto_run",
            "mt5_diagnostics_compact_mode",
        }

        missing = [field for field in required_fields if not hasattr(data, field)]

        self.assertEqual(missing, [])

    def test_defaults_do_configuration_data_nao_expoem_nd(self) -> None:
        """Garante valores reais no DTO consumido pelo dashboard."""
        data = ConfigurationService().get_configuration_data()
        values = {
            data.quantitative_score_candles_loaded,
            data.quantitative_score_feature_lookback,
            data.quantitative_score_forward_return_candles,
            data.quantitative_score_fast_ma_period,
            data.quantitative_score_slow_ma_period,
            data.quantitative_score_rsi_period,
            data.quantitative_score_atr_period,
            data.quantitative_score_volatility_bucket_method,
            data.quantitative_score_min_sample_size,
            data.quantitative_score_min_profit_factor,
            data.quantitative_score_min_win_rate,
            data.quantitative_score_max_allowed_drawdown,
            data.quantitative_score_confidence_floor,
            data.quantitative_score_confidence_ceiling,
            data.quantitative_score_volatility_low_threshold,
            data.quantitative_score_volatility_high_threshold,
            data.quantitative_score_ma_flat_threshold,
            data.quantitative_score_ma_strong_threshold,
        }

        self.assertNotIn("N/D", values)

    def test_expoe_parametros_do_timeframe_optimizer(self) -> None:
        """Garante painel read-only com parametros do otimizador."""
        data = ConfigurationService().update_configuration(
            timeframe_optimizer_timeframes=("M1", "M30"),
            timeframe_optimizer_min_sample_size=35,
            timeframe_optimizer_min_profit_factor=1.35,
            timeframe_optimizer_min_win_rate=0.56,
            timeframe_optimizer_max_allowed_drawdown=0.012,
            timeframe_optimizer_min_confidence=0.61,
        )

        self.assertEqual(data.timeframe_optimizer_timeframes, ("M1", "M30"))
        self.assertEqual(data.timeframe_optimizer_min_sample_size, 35)
        self.assertEqual(data.timeframe_optimizer_min_profit_factor, 1.35)
        self.assertEqual(data.timeframe_optimizer_min_win_rate, 0.56)
        self.assertEqual(data.timeframe_optimizer_max_allowed_drawdown, 0.012)
        self.assertEqual(data.timeframe_optimizer_min_confidence, 0.61)

    def test_repassa_validacao_de_configuracao(self) -> None:
        """Garante validacao de valores invalidos."""
        with self.assertRaises(ValueError):
            ConfigurationService().update_configuration(stop_points=-1)

    def test_gerencia_presets(self) -> None:
        """Garante salvar, listar, carregar e excluir presets."""
        service = ConfigurationService()
        service.update_configuration(symbol="WIN")
        service.save_preset("teste")
        service.update_configuration(symbol="WDO")

        self.assertEqual(service.list_presets(), ["teste"])
        self.assertEqual(service.load_preset("teste").symbol, "WIN")

        service.delete_preset("teste")
        self.assertEqual(service.list_presets(), [])


if __name__ == "__main__":
    unittest.main()
