"""Testes do gerenciador central de configuracoes."""

import unittest

from core.configuration_manager import ConfigurationManager, SystemConfiguration


class ConfigurationManagerTest(unittest.TestCase):
    """Valida leitura, atualizacao e validacao de configuracoes."""

    def setUp(self) -> None:
        """Restaura configuracao padrao antes de cada teste."""
        ConfigurationManager.reset_configuration()

    def test_leitura_da_configuracao(self) -> None:
        """Garante acesso a configuracao atual."""
        configuration = ConfigurationManager.get_configuration()

        self.assertIsInstance(configuration, SystemConfiguration)
        self.assertEqual(configuration.symbol, "WDO")
        self.assertEqual(configuration.initial_capital, 0.0)

    def test_atualizacao_de_campos(self) -> None:
        """Garante atualizacao controlada de campos."""
        configuration = ConfigurationManager.update_configuration(
            symbol="WIN",
            contracts=2,
        )

        self.assertEqual(configuration.symbol, "WIN")
        self.assertEqual(configuration.contracts, 2)

    def test_parametros_do_quantitative_score_sao_configuraveis(self) -> None:
        """Garante reproducibilidade dos parametros do score quantitativo."""
        configuration = ConfigurationManager.update_configuration(
            quantitative_score_candles_loaded=5000,
            quantitative_score_feature_lookback=50,
            quantitative_score_forward_return_candles=10,
            quantitative_score_fast_ma_period=9,
            quantitative_score_slow_ma_period=21,
            quantitative_score_rsi_period=14,
            quantitative_score_atr_period=14,
            quantitative_score_volatility_period=14,
            quantitative_score_min_sample_size=30,
            quantitative_score_min_profit_factor=1.3,
            quantitative_score_min_win_rate=0.55,
            quantitative_score_max_allowed_drawdown=0.05,
            quantitative_score_confidence_floor=0.2,
            quantitative_score_confidence_ceiling=0.95,
            quantitative_score_volatility_bucket_method="ATR",
            quantitative_score_volatility_low_threshold=0.0002,
            quantitative_score_volatility_high_threshold=0.0008,
            quantitative_score_ma_flat_threshold=0.00005,
            quantitative_score_ma_strong_threshold=0.0015,
            quantitative_score_rsi_oversold_threshold=30.0,
            quantitative_score_rsi_overbought_threshold=70.0,
        )

        self.assertEqual(configuration.quantitative_score_candles_loaded, 5000)
        self.assertEqual(configuration.quantitative_score_feature_lookback, 50)
        self.assertEqual(configuration.quantitative_score_forward_return_candles, 10)
        self.assertEqual(configuration.quantitative_score_fast_ma_period, 9)
        self.assertEqual(configuration.quantitative_score_slow_ma_period, 21)
        self.assertEqual(configuration.quantitative_score_rsi_period, 14)
        self.assertEqual(configuration.quantitative_score_atr_period, 14)
        self.assertEqual(configuration.quantitative_score_min_sample_size, 30)
        self.assertEqual(configuration.quantitative_score_min_profit_factor, 1.3)
        self.assertEqual(configuration.quantitative_score_min_win_rate, 0.55)
        self.assertEqual(configuration.quantitative_score_max_allowed_drawdown, 0.05)
        self.assertEqual(configuration.quantitative_score_confidence_floor, 0.2)
        self.assertEqual(configuration.quantitative_score_confidence_ceiling, 0.95)
        self.assertEqual(configuration.quantitative_score_volatility_bucket_method, "ATR")

    def test_defaults_do_quantitative_score_sao_reais_para_dashboard(self) -> None:
        """Garante que o painel nao nasce com valores legados ou N/D."""
        configuration = ConfigurationManager.get_configuration()

        self.assertEqual(configuration.quantitative_score_candles_loaded, 5000)
        self.assertEqual(configuration.quantitative_score_feature_lookback, 50)
        self.assertEqual(configuration.quantitative_score_forward_return_candles, 10)
        self.assertEqual(configuration.quantitative_score_fast_ma_period, 9)
        self.assertEqual(configuration.quantitative_score_slow_ma_period, 21)
        self.assertEqual(configuration.quantitative_score_rsi_period, 14)
        self.assertEqual(configuration.quantitative_score_atr_period, 14)
        self.assertEqual(configuration.quantitative_score_volatility_bucket_method, "ATR")
        self.assertEqual(configuration.quantitative_score_min_sample_size, 30)
        self.assertEqual(configuration.quantitative_score_min_profit_factor, 1.3)
        self.assertEqual(configuration.quantitative_score_min_win_rate, 0.55)
        self.assertEqual(configuration.quantitative_score_max_allowed_drawdown, 0.05)
        self.assertEqual(configuration.quantitative_score_confidence_floor, 0.2)
        self.assertEqual(configuration.quantitative_score_confidence_ceiling, 0.95)

    def test_parametros_do_timeframe_optimizer_sao_configuraveis(self) -> None:
        """Garante reproducibilidade do ranking de timeframes."""
        configuration = ConfigurationManager.update_configuration(
            timeframe_optimizer_timeframes=("M5", "M15", "H1"),
            timeframe_optimizer_min_sample_size=40,
            timeframe_optimizer_min_profit_factor=1.4,
            timeframe_optimizer_min_win_rate=0.57,
            timeframe_optimizer_max_allowed_drawdown=0.015,
            timeframe_optimizer_min_confidence=0.62,
        )

        self.assertEqual(configuration.timeframe_optimizer_timeframes, ("M5", "M15", "H1"))
        self.assertEqual(configuration.timeframe_optimizer_min_sample_size, 40)
        self.assertEqual(configuration.timeframe_optimizer_min_profit_factor, 1.4)
        self.assertEqual(configuration.timeframe_optimizer_min_win_rate, 0.57)
        self.assertEqual(configuration.timeframe_optimizer_max_allowed_drawdown, 0.015)
        self.assertEqual(configuration.timeframe_optimizer_min_confidence, 0.62)

    def test_valor_invalido_gera_erro(self) -> None:
        """Garante bloqueio de valores negativos proibidos."""
        with self.assertRaises(ValueError):
            ConfigurationManager.update_configuration(initial_capital=-1)

    def test_campo_invalido_gera_erro(self) -> None:
        """Garante bloqueio de campos inexistentes."""
        with self.assertRaises(ValueError):
            ConfigurationManager.update_configuration(campo_invalido=1)

    def test_salva_lista_carrega_e_exclui_preset(self) -> None:
        """Garante ciclo completo de preset em memoria."""
        ConfigurationManager.update_configuration(symbol="WIN")
        ConfigurationManager.save_preset("agressivo")
        ConfigurationManager.update_configuration(symbol="WDO")

        self.assertEqual(ConfigurationManager.list_presets(), ["agressivo"])
        loaded = ConfigurationManager.load_preset("agressivo")

        self.assertEqual(loaded.symbol, "WIN")
        ConfigurationManager.delete_preset("agressivo")
        self.assertEqual(ConfigurationManager.list_presets(), [])

    def test_nome_vazio_de_preset_gera_erro(self) -> None:
        """Garante bloqueio de nome vazio."""
        with self.assertRaises(ValueError):
            ConfigurationManager.save_preset("")


if __name__ == "__main__":
    unittest.main()
