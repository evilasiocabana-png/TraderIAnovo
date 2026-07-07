"""Testes da Camada 3 - Estrutura de Mercado."""

from dataclasses import fields, is_dataclass
import inspect
import unittest

from domain.candle import Candle
from market.structure import MarketStructureAnalyzer, MarketStructureSnapshot


class MarketStructureLayerTest(unittest.TestCase):
    """Protege features estruturais sem acoplar execucao ou Alpha."""

    def test_snapshot_e_dataclass_imutavel_com_campos_estruturais(self) -> None:
        self.assertTrue(is_dataclass(MarketStructureSnapshot))
        self.assertTrue(MarketStructureSnapshot.__dataclass_params__.frozen)
        field_names = {field.name for field in fields(MarketStructureSnapshot)}

        expected = {
            "donchian_high",
            "donchian_low",
            "donchian_mid",
            "donchian_position",
            "pivot",
            "pivot_r1",
            "pivot_r2",
            "pivot_s1",
            "pivot_s2",
            "vwap",
            "distance_to_vwap",
            "z_score",
            "bollinger_upper",
            "bollinger_middle",
            "bollinger_lower",
            "bollinger_width",
            "bollinger_position",
            "tick_volume",
            "tick_volume_average",
            "relative_tick_volume",
            "current_spread",
            "average_spread",
            "spread_to_average_ratio",
            "estimated_slippage",
            "price_velocity",
            "session",
            "session_liquidity",
            "spread_blocked",
            "spread_status",
            "support",
            "resistance",
            "swing_high",
            "swing_low",
            "relevant_high",
            "relevant_low",
            "current_range_high",
            "current_range_low",
            "current_range_size",
            "current_range_position",
            "range_breakout",
            "distance_to_support",
            "distance_to_resistance",
            "nearest_structure_level",
            "distance_to_nearest_structure",
            "structure_status",
            "regime",
            "trend_strength",
            "volatility_compression",
            "volatility_expansion",
            "fast_ema_period",
            "medium_ema_period",
            "slow_ema_period",
            "fast_ema",
            "medium_ema",
            "slow_ema",
            "distance_to_fast_ema",
            "distance_to_medium_ema",
            "distance_to_slow_ema",
            "current_timeframe_direction",
            "dominant_multi_timeframe_direction",
            "timeframe_directions",
            "confidence",
        }

        self.assertTrue(expected.issubset(field_names))

    def test_analyzer_calcula_donchian_pivot_vwap_zscore_bollinger_e_volume(self) -> None:
        candles = self._candles()
        snapshot = MarketStructureAnalyzer(
            donchian_period=5,
            bollinger_period=5,
            z_score_period=5,
            tick_volume_period=5,
        ).analyze(candles, symbol="EURUSD", timeframe="M15")

        latest_window = candles[-5:]
        expected_donchian_high = max(candle.maxima for candle in latest_window)
        expected_donchian_low = min(candle.minima for candle in latest_window)
        pivot_candle = candles[-2]
        expected_pivot = (
            pivot_candle.maxima + pivot_candle.minima + pivot_candle.fechamento
        ) / 3.0
        expected_tick_average = sum(candle.volume for candle in latest_window) / 5

        self.assertEqual(snapshot.symbol, "EURUSD")
        self.assertEqual(snapshot.timeframe, "M15")
        self.assertEqual(snapshot.donchian_high, expected_donchian_high)
        self.assertEqual(snapshot.donchian_low, expected_donchian_low)
        self.assertEqual(snapshot.pivot, expected_pivot)
        self.assertGreater(snapshot.vwap, 0.0)
        self.assertNotEqual(snapshot.z_score, 0.0)
        self.assertGreater(snapshot.bollinger_width, 0.0)
        self.assertEqual(snapshot.tick_volume, candles[-1].volume)
        self.assertEqual(snapshot.tick_volume_average, expected_tick_average)
        self.assertGreater(snapshot.relative_tick_volume, 0.0)
        self.assertIn(
            snapshot.structure_status,
            {
                "BREAKOUT_UP",
                "BREAKOUT_DOWN",
                "UPPER_RANGE",
                "LOWER_RANGE",
                "MID_RANGE",
                "NEUTRAL",
            },
        )
        self.assertGreaterEqual(snapshot.confidence, 0.0)
        self.assertLessEqual(snapshot.confidence, 1.0)

    def test_analyzer_calcula_microestrutura_e_bloqueio_por_spread_alto(self) -> None:
        snapshot = MarketStructureAnalyzer(
            tick_volume_period=5,
            price_velocity_period=3,
            max_spread_to_average_ratio=1.8,
        ).analyze(
            self._candles(),
            symbol="EURUSD",
            timeframe="M15",
            current_bid=1.1130,
            current_ask=1.1140,
            spread_history=[0.0002, 0.0002, 0.0003, 0.0003],
            session="LONDON",
        )

        self.assertAlmostEqual(snapshot.current_spread, 0.0010)
        self.assertAlmostEqual(snapshot.average_spread, 0.00025)
        self.assertGreater(snapshot.spread_to_average_ratio, 1.8)
        self.assertGreater(snapshot.estimated_slippage, 0.0)
        self.assertGreater(snapshot.price_velocity, 0.0)
        self.assertEqual(snapshot.session, "LONDON")
        self.assertIn(snapshot.session_liquidity, {"LOW", "NORMAL", "HIGH"})
        self.assertTrue(snapshot.spread_blocked)
        self.assertEqual(snapshot.spread_status, "BLOCKED_HIGH_SPREAD")

    def test_analyzer_calcula_suporte_resistencia_swings_range_e_distancias(self) -> None:
        candles = self._range_candles()
        snapshot = MarketStructureAnalyzer(
            range_period=7,
            swing_lookback=1,
        ).analyze(candles, symbol="EURUSD", timeframe="M15")

        window = candles[-7:]
        expected_resistance = max(candle.maxima for candle in window)
        expected_support = min(candle.minima for candle in window)

        self.assertEqual(snapshot.resistance, expected_resistance)
        self.assertEqual(snapshot.support, expected_support)
        self.assertEqual(snapshot.current_range_high, expected_resistance)
        self.assertEqual(snapshot.current_range_low, expected_support)
        self.assertEqual(
            snapshot.current_range_size,
            expected_resistance - expected_support,
        )
        self.assertGreater(snapshot.swing_high, 0.0)
        self.assertGreater(snapshot.swing_low, 0.0)
        self.assertGreaterEqual(snapshot.relevant_high, snapshot.resistance)
        self.assertLessEqual(snapshot.relevant_low, snapshot.support)
        self.assertIn(
            snapshot.range_breakout,
            {"BREAKOUT_UP", "BREAKOUT_DOWN", "INSIDE_RANGE"},
        )
        self.assertGreaterEqual(snapshot.current_range_position, 0.0)
        self.assertLessEqual(snapshot.current_range_position, 1.0)
        self.assertGreaterEqual(snapshot.distance_to_support, 0.0)
        self.assertGreaterEqual(snapshot.distance_to_resistance, 0.0)
        self.assertGreater(snapshot.nearest_structure_level, 0.0)

    def test_analyzer_calcula_regime_forca_volatilidade_medias_e_direcao(self) -> None:
        candles = self._trend_candles()
        snapshot = MarketStructureAnalyzer(
            donchian_period=20,
            bollinger_period=20,
            z_score_period=20,
            tick_volume_period=20,
            fast_ema_period=5,
            medium_ema_period=10,
            slow_ema_period=20,
            short_volatility_period=5,
            long_volatility_period=20,
        ).analyze(
            candles,
            symbol="EURUSD",
            timeframe="M15",
            multi_timeframe_candles={
                "H1": self._trend_candles(),
                "H4": self._trend_candles(),
            },
        )

        self.assertIn(snapshot.regime, {"TREND", "RANGE", "VOLATILE"})
        self.assertGreaterEqual(snapshot.trend_strength, 0.0)
        self.assertLessEqual(snapshot.trend_strength, 1.0)
        self.assertGreaterEqual(snapshot.volatility_compression, 0.0)
        self.assertLessEqual(snapshot.volatility_compression, 1.0)
        self.assertGreaterEqual(snapshot.volatility_expansion, 0.0)
        self.assertLessEqual(snapshot.volatility_expansion, 1.0)
        self.assertGreater(snapshot.fast_ema, snapshot.medium_ema)
        self.assertGreater(snapshot.medium_ema, snapshot.slow_ema)
        self.assertGreater(snapshot.distance_to_fast_ema, 0.0)
        self.assertGreater(snapshot.distance_to_medium_ema, 0.0)
        self.assertGreater(snapshot.distance_to_slow_ema, 0.0)
        self.assertEqual(snapshot.current_timeframe_direction, "UP")
        self.assertEqual(snapshot.dominant_multi_timeframe_direction, "UP")
        self.assertEqual(
            snapshot.timeframe_directions,
            ("H1:UP", "H4:UP", "M15:UP"),
        )

    def test_analyzer_estado_vazio_sem_excecao(self) -> None:
        snapshot = MarketStructureAnalyzer().analyze([], symbol="EURUSD", timeframe="H1")

        self.assertEqual(snapshot.structure_status, "NO_DATA")
        self.assertEqual(snapshot.current_price, 0.0)
        self.assertEqual(snapshot.candles_count, 0)
        self.assertEqual(snapshot.regime, "RANGE")
        self.assertEqual(snapshot.current_spread, 0.0)
        self.assertEqual(snapshot.average_spread, 0.0)
        self.assertEqual(snapshot.session_liquidity, "UNKNOWN")
        self.assertFalse(snapshot.spread_blocked)
        self.assertEqual(snapshot.spread_status, "NO_DATA")
        self.assertEqual(snapshot.range_breakout, "NO_DATA")
        self.assertEqual(snapshot.support, 0.0)
        self.assertEqual(snapshot.resistance, 0.0)
        self.assertEqual(snapshot.current_timeframe_direction, "SIDEWAYS")
        self.assertEqual(snapshot.dominant_multi_timeframe_direction, "SIDEWAYS")
        self.assertEqual(snapshot.timeframe_directions, ())
        self.assertEqual(snapshot.confidence, 0.0)

    def test_market_structure_nao_executa_ordem_nem_importa_infraestrutura(self) -> None:
        source = inspect.getsource(MarketStructureAnalyzer)
        forbidden = (
            "order_send",
            "ExecutionOrder",
            "DashboardService",
            "MetaTrader5",
            "streamlit",
            "pandas",
            "Path(",
            "open(",
        )

        for fragment in forbidden:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

    def _candles(self) -> list[Candle]:
        return [
            Candle("2026-07-02 10:00", 1.1000, 1.1050, 1.0980, 1.1020, 100),
            Candle("2026-07-02 10:15", 1.1020, 1.1080, 1.1010, 1.1060, 120),
            Candle("2026-07-02 10:30", 1.1060, 1.1100, 1.1040, 1.1090, 130),
            Candle("2026-07-02 10:45", 1.1090, 1.1110, 1.1050, 1.1060, 90),
            Candle("2026-07-02 11:00", 1.1060, 1.1120, 1.1050, 1.1110, 160),
            Candle("2026-07-02 11:15", 1.1110, 1.1150, 1.1100, 1.1140, 180),
        ]

    def _trend_candles(self) -> list[Candle]:
        candles = []
        price = 1.1000
        for index in range(40):
            open_price = price
            close_price = open_price + 0.0010
            candles.append(
                Candle(
                    f"2026-07-02 10:{index:02d}",
                    open_price,
                    close_price + 0.0005,
                    open_price - 0.0002,
                    close_price,
                    100 + index,
                )
            )
            price = close_price
        return candles

    def _range_candles(self) -> list[Candle]:
        return [
            Candle("2026-07-02 10:00", 1.1000, 1.1040, 1.0980, 1.1020, 100),
            Candle("2026-07-02 10:15", 1.1020, 1.1060, 1.1010, 1.1050, 120),
            Candle("2026-07-02 10:30", 1.1050, 1.1080, 1.1030, 1.1040, 130),
            Candle("2026-07-02 10:45", 1.1040, 1.1050, 1.0990, 1.1000, 90),
            Candle("2026-07-02 11:00", 1.1000, 1.1030, 1.0970, 1.1010, 160),
            Candle("2026-07-02 11:15", 1.1010, 1.1090, 1.1000, 1.1070, 180),
            Candle("2026-07-02 11:30", 1.1070, 1.1080, 1.1020, 1.1030, 150),
            Candle("2026-07-02 11:45", 1.1030, 1.1060, 1.1010, 1.1040, 140),
        ]


if __name__ == "__main__":
    unittest.main()
