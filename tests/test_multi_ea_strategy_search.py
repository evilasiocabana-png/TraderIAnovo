from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
import json
import math
import unittest

from research.multi_ea_strategy_search import (
    BUY,
    SELL,
    WAIT,
    MultiEAStrategySearchConfiguration,
    MultiEAStrategySearchEngine,
    _Opportunity,
    _directional_metrics,
)
from research.multi_ea_trading_lab import MultiEACandle, MultiEATradePosition


class MultiEAStrategySearchEngineTest(unittest.TestCase):
    def test_catalogo_cobre_familias_minimas_e_combinacoes_and(self) -> None:
        engine = MultiEAStrategySearchEngine()

        catalog = engine.candidate_catalog()
        families = {str(item["family"]) for item in catalog}

        self.assertTrue(
            {
                "RSI_REVERSAL",
                "RSI_MOMENTUM",
                "BOLLINGER_ZSCORE",
                "EMA_CROSS",
                "EMA_TREND",
                "EMA_PULLBACK",
                "SMA_CROSS",
                "SMA_TREND",
                "SMA_PULLBACK",
                "DONCHIAN_BREAKOUT",
                "MACD",
                "STOCHASTIC",
                "CANDLE_BODY",
                "CANDLE_ENGULFING",
                "ATR_VOLATILITY",
                "TIME_SESSION_FILTER",
                "AND_COMBINATION",
            }.issubset(families)
        )
        combinations = [
            item for item in catalog if item["family"] == "AND_COMBINATION"
        ]
        self.assertGreaterEqual(len(combinations), 4)
        self.assertTrue(all(len(item["components"]) >= 2 for item in combinations))
        self.assertEqual(
            [item["candidate_id"] for item in catalog],
            [item["candidate_id"] for item in engine.candidate_catalog()],
        )

    def test_candle_futuro_nao_altera_sinal_nem_ranking_da_entrada(self) -> None:
        candles = self._wave_candles("EURUSD", 140)
        position = self._position("p1", candles, 90, "BUY")
        changed = list(candles)
        changed[91] = replace(
            changed[91],
            open=20.0,
            high=30.0,
            low=10.0,
            close=25.0,
            volume=999999.0,
        )
        engine = MultiEAStrategySearchEngine()

        baseline = engine.analyze([position], candles)
        altered = engine.analyze([position], changed)

        self.assertEqual(baseline["global"], altered["global"])
        self.assertEqual(baseline["coverage"], altered["coverage"])
        self.assertFalse(baseline["lookahead"])
        self.assertFalse(baseline["uses_exit_data"])
        self.assertEqual(baseline["coverage"]["opportunity_bars"], 1)

    def test_saida_e_resultado_financeiro_nao_participam_da_busca(self) -> None:
        candles = self._wave_candles("EURUSD", 150)
        position = self._position("p1", candles, 95, "SELL")
        changed_exit = replace(
            position,
            close_time=position.close_time + timedelta(days=100),
            close_price=999.0,
            commission=-100.0,
            swap=-200.0,
            profit=-10000.0,
        )
        engine = MultiEAStrategySearchEngine()

        baseline = engine.analyze([position], candles)
        altered = engine.analyze([changed_exit], candles)

        self.assertEqual(baseline, altered)
        self.assertIn("ENTRADAS_SOMENTE", " ".join(baseline["warnings"]))

    def test_negativos_dedupe_metricas_e_penalidade_de_complexidade(self) -> None:
        candles = self._rising_candles("EURUSD", 170)
        positions = [
            self._position("p1", candles, 70, "BUY"),
            self._position("p2", candles, 140, "BUY"),
        ]
        engine = MultiEAStrategySearchEngine(
            MultiEAStrategySearchConfiguration(dedupe_bars=4)
        )

        result = engine.analyze(positions, candles)
        rows = {
            row["candidate_id"]: row
            for row in result["global"]["ranking_train"]
        }
        trend = rows["EMA_TREND_20_50"]
        combination = rows["AND_DONCHIAN_ATR"]

        self.assertGreater(result["coverage"]["negative_events"], 0)
        self.assertGreater(trend["raw_signals"], trend["signals"])
        self.assertGreater(trend["suppressed_duplicate_signals"], 0)
        self.assertIn("mcc", trend)
        self.assertIn("direction_match_rate", trend)
        self.assertEqual(trend["complexity_penalty_applied"], 0.0)
        self.assertGreater(combination["complexity_penalty_applied"], 0.0)
        self.assertEqual(result["deduplication"]["window_bars"], 4)

    def test_selecao_usa_treino_e_validacao_permanece_congelada(self) -> None:
        candles = self._wave_candles("EURUSD", 260)
        positions = [
            self._position(
                f"p{index}",
                candles,
                70 + index * 5,
                "BUY" if index % 3 else "SELL",
            )
            for index in range(32)
        ]
        changed_validation = [
            position
            if index < 22
            else replace(
                position,
                direction="SELL" if position.direction == "BUY" else "BUY",
            )
            for index, position in enumerate(positions)
        ]
        engine = MultiEAStrategySearchEngine()

        baseline = engine.analyze(positions, candles)
        altered = engine.analyze(changed_validation, candles)

        self.assertEqual(
            baseline["split"]["method"],
            "CRONOLOGICO_TREINO_VALIDACAO_COM_EMBARGO",
        )
        self.assertGreater(baseline["split"]["embargo_opportunities"], 0)
        self.assertGreaterEqual(baseline["split"]["validation_positive_events"], 5)
        self.assertEqual(
            baseline["global"]["selected_candidate_id"],
            altered["global"]["selected_candidate_id"],
        )
        self.assertEqual(
            baseline["global"]["selection_metrics_train"],
            altered["global"]["selection_metrics_train"],
        )
        self.assertEqual(
            baseline["global"]["validation_metrics_frozen"]["candidate_id"],
            baseline["global"]["selected_candidate_id"],
        )

    def test_ranking_por_simbolo_e_cluster_customizado(self) -> None:
        eurusd = self._wave_candles("EURUSD", 150)
        gbpusd = self._rising_candles("GBPUSD", 150)
        positions = [
            self._position("e1", eurusd, 75, "BUY"),
            self._position("e2", eurusd, 120, "SELL"),
            self._position("g1", gbpusd, 80, "BUY"),
            self._position("g2", gbpusd, 125, "BUY"),
        ]

        result = MultiEAStrategySearchEngine().analyze(
            positions,
            [*eurusd, *gbpusd],
            symbol_clusters={"EURUSD": "cluster_fx", "GBPUSD": "cluster_fx"},
        )

        self.assertEqual(set(result["by_symbol"]), {"EURUSD", "GBPUSD"})
        self.assertEqual(result["cluster_assignments"]["EURUSD"], "CLUSTER_FX")
        self.assertEqual(result["cluster_assignments"]["GBPUSD"], "CLUSTER_FX")
        self.assertEqual(set(result["by_cluster"]), {"CLUSTER_FX"})
        self.assertTrue(result["by_symbol"]["EURUSD"]["ranking_train"])
        self.assertTrue(result["by_cluster"]["CLUSTER_FX"]["ranking_train"])

    def test_metricas_directionais_contam_lado_errado_como_fp_e_fn(self) -> None:
        start = datetime(2026, 1, 1)
        opportunities = [
            _Opportunity("EURUSD", 1, start, (BUY,)),
            _Opportunity("EURUSD", 2, start + timedelta(minutes=15), (SELL,)),
            _Opportunity("EURUSD", 3, start + timedelta(minutes=30), ()),
            _Opportunity("EURUSD", 4, start + timedelta(minutes=45), ()),
        ]
        raw = bytearray((BUY, BUY, SELL, WAIT))
        signals = bytearray((BUY, BUY, SELL, WAIT))

        metrics = _directional_metrics(
            list(range(4)), opportunities, raw, signals
        )

        self.assertEqual(metrics["true_positive"], 1)
        self.assertEqual(metrics["false_positive"], 2)
        self.assertEqual(metrics["false_negative"], 1)
        self.assertEqual(metrics["true_negative"], 1)
        self.assertAlmostEqual(metrics["precision"], 1.0 / 3.0, places=7)
        self.assertEqual(metrics["recall"], 0.5)
        self.assertEqual(metrics["f1"], 0.4)
        self.assertAlmostEqual(metrics["mcc"], -1.0 / 6.0, places=7)
        self.assertEqual(metrics["direction_match_rate"], 0.5)

    def test_resultado_e_deterministico_e_json_sem_nan(self) -> None:
        candles = self._wave_candles("EURUSD", 180)
        positions = [
            self._position("p1", candles, 80, "BUY"),
            self._position("p2", candles, 130, "SELL"),
        ]
        engine = MultiEAStrategySearchEngine()

        first = engine.analyze(positions, candles)
        second = engine.analyze(positions, candles)

        self.assertEqual(first, second)
        json.dumps(first, allow_nan=False)

    def test_configuracao_invalida_falha_fechada(self) -> None:
        with self.assertRaises(ValueError):
            MultiEAStrategySearchEngine(
                MultiEAStrategySearchConfiguration(dedupe_bars=-1)
            )

    def _rising_candles(
        self,
        symbol: str,
        count: int,
    ) -> list[MultiEACandle]:
        start = datetime(2025, 1, 1)
        candles = []
        for index in range(count):
            close = 1.0 + index * 0.001
            candles.append(
                MultiEACandle(
                    symbol=symbol,
                    source_symbol=symbol,
                    timeframe="M15",
                    timestamp=start + timedelta(minutes=15 * index),
                    open=close - 0.0006,
                    high=close + 0.0003,
                    low=close - 0.0008,
                    close=close,
                    volume=100.0 + index,
                )
            )
        return candles

    def _wave_candles(
        self,
        symbol: str,
        count: int,
    ) -> list[MultiEACandle]:
        start = datetime(2025, 1, 1)
        candles = []
        previous = 1.0
        for index in range(count):
            close = 1.0 + 0.012 * math.sin(index / 5.0) + index * 0.00004
            opening = previous
            candles.append(
                MultiEACandle(
                    symbol=symbol,
                    source_symbol=symbol,
                    timeframe="M15",
                    timestamp=start + timedelta(minutes=15 * index),
                    open=opening,
                    high=max(opening, close) + 0.001,
                    low=min(opening, close) - 0.001,
                    close=close,
                    volume=100.0 + (index % 17) * 4.0,
                )
            )
            previous = close
        return candles

    def _position(
        self,
        position_id: str,
        candles: list[MultiEACandle],
        closed_candle_index: int,
        direction: str,
    ) -> MultiEATradePosition:
        candle = candles[closed_candle_index]
        entry_time = candle.timestamp + timedelta(minutes=20)
        return MultiEATradePosition(
            source_symbol=candle.symbol,
            symbol=candle.symbol,
            direction=direction,
            volume=0.01,
            open_time=entry_time,
            open_price=candle.close,
            close_time=entry_time + timedelta(hours=1),
            close_price=candle.close + 0.001,
            commission=-0.01,
            swap=0.0,
            profit=1.0,
            source_row=closed_candle_index,
            position_id=position_id,
        )


if __name__ == "__main__":
    unittest.main()
