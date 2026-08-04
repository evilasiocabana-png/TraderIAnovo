from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
import json
import math
import unittest

import numpy as np

from research.multi_ea_intrabar_search import (
    MultiEAIntrabarSearchConfiguration,
    MultiEAIntrabarSearchEngine,
    _counts_from_arrays,
    _finalize_counts,
)
from research.multi_ea_trading_lab import MultiEACandle, MultiEATradePosition


class MultiEAIntrabarSearchEngineTest(unittest.TestCase):
    def test_grade_tem_mais_de_500_hipoteses_e_dimensoes_exigidas(self) -> None:
        engine = MultiEAIntrabarSearchEngine()
        catalog = engine.candidate_catalog()

        self.assertGreaterEqual(len(catalog), 500)
        self.assertEqual(len(catalog), len({item["candidate_id"] for item in catalog}))
        self.assertEqual({item["delay_bars"] for item in catalog}, {0, 1, 2, 4, 8})
        self.assertEqual({item["cooldown_bars"] for item in catalog}, {1, 2, 4, 8, 16})
        self.assertTrue({"EMA", "SMA"}.issubset({str(item["parameters"].get("kind")) for item in catalog}))
        self.assertTrue(
            {"BOLLINGER", "KELTNER", "ATR_LEVEL", "DONCHIAN"}.issubset(
                {item["family"] for item in catalog}
            )
        )
        self.assertTrue(
            {"NONE", "RSI_REVERSAL", "RSI_MOMENTUM", "STOCH_REVERSAL", "ADX_TREND", "ADX_RANGE"}.issubset(
                {item["filter"] for item in catalog}
            )
        )

    def test_fechamento_do_candle_de_execucao_nao_entra_no_sinal(self) -> None:
        candles = self._candles("EURUSD", 270)
        position = self._position("p1", candles, 235, "BUY")
        changed = list(candles)
        execution = changed[235]
        changed[235] = replace(
            execution,
            open=execution.low,
            close=execution.high,
            volume=999999.0,
        )
        engine = self._engine()

        baseline = engine.analyze([position], candles)
        altered = engine.analyze([position], changed)

        self.assertEqual(baseline, altered)
        self.assertEqual(len(baseline["catalog_sha256"]), 64)
        self.assertFalse(baseline["execution_candle_close_used"])
        self.assertEqual(baseline["execution_candle_fields_used"], ["timestamp", "high", "low"])
        self.assertFalse(baseline["signal_level_lookahead"])
        self.assertFalse(baseline["causal_entry_test"])
        self.assertTrue(baseline["evaluation_uses_full_execution_bar"])
        self.assertTrue(baseline["execution_confirmation_ex_post"])
        self.assertFalse(baseline["intrabar_path_known"])
        self.assertFalse(baseline["exact_entry_reconstruction"])
        self.assertFalse(baseline["source_row_multiplicity_preserved"])

    def test_faixa_seguinte_pode_disparar_buy_e_sell_no_mesmo_bar(self) -> None:
        candles = self._candles("EURUSD", 270)
        execution_index = 235
        previous = candles[execution_index - 20 : execution_index]
        changed = list(candles)
        changed[execution_index] = replace(
            changed[execution_index],
            high=max(item.high for item in previous) + 1.0,
            low=min(item.low for item in previous) - 1.0,
        )
        positions = [
            self._position("buy", changed, execution_index, "BUY"),
            self._position("sell", changed, execution_index, "SELL"),
        ]
        engine = self._engine(maximum_ranked_candidates=2000)

        result = engine.analyze(positions, changed)
        row = self._global_row(
            result,
            "DONCHIAN_20_BREAKOUT__D0_C1_ALL_NONE",
        )

        self.assertEqual(result["coverage"]["hedged_events"], 1)
        self.assertEqual(row["direction_micro"]["true_positive"], 2)
        self.assertEqual(row["event"]["true_positive"], 1)
        self.assertEqual(row["exact_direction_set_matches"], 1)
        self.assertEqual(row["direction_match_rate"], 1.0)

    def test_todas_as_barras_negativas_e_cooldown_entram_no_ranking(self) -> None:
        candles = self._wide_range_candles("EURUSD", 330)
        positions = [
            self._position("p1", candles, 220, "BUY"),
            self._position("p2", candles, 310, "SELL"),
        ]
        result = self._engine(maximum_ranked_candidates=2000).analyze(
            positions,
            candles,
        )

        self.assertEqual(
            result["coverage"]["negative_events"],
            result["coverage"]["opportunity_bars"]
            - result["coverage"]["positive_events"],
        )
        self.assertGreater(result["coverage"]["negative_events"], 80)
        self.assertTrue(
            any(
                row["suppressed_by_constraints_and_cooldown"] > 0
                for row in result["global"]["ranking_train"]
            )
        )
        sample = result["global"]["ranking_train"][0]
        self.assertIn("mcc", sample["buy"])
        self.assertIn("mcc", sample["sell"])
        self.assertIn("mcc", sample["direction_micro"])
        self.assertIn("mcc", sample["event"])

    def test_validacao_nao_reseleciona_setup_ou_portfolio(self) -> None:
        candles = self._candles("EURUSD", 390)
        positions = [
            self._position(
                f"p{index}",
                candles,
                220 + index * 5,
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
        engine = self._engine()

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
            baseline["portfolio"]["selected_candidate_ids"],
            altered["portfolio"]["selected_candidate_ids"],
        )
        self.assertEqual(
            baseline["portfolio"]["metrics_train"],
            altered["portfolio"]["metrics_train"],
        )
        self.assertEqual(
            baseline["symbol_portfolio"]["selected_setup_by_symbol"],
            altered["symbol_portfolio"]["selected_setup_by_symbol"],
        )
        self.assertEqual(
            baseline["symbol_portfolio"]["metrics_train"],
            altered["symbol_portfolio"]["metrics_train"],
        )

    def test_ranking_por_simbolo_e_portfolio_limitado_a_oito(self) -> None:
        eurusd = self._candles("EURUSD", 330)
        gbpusd = self._wide_range_candles("GBPUSD", 330)
        positions = [
            self._position("e1", eurusd, 220, "BUY"),
            self._position("e2", eurusd, 310, "SELL"),
            self._position("g1", gbpusd, 225, "SELL"),
            self._position("g2", gbpusd, 305, "BUY"),
        ]

        result = self._engine(portfolio_maximum_setups=8).analyze(
            positions,
            [*eurusd, *gbpusd],
        )

        self.assertEqual(set(result["by_symbol"]), {"EURUSD", "GBPUSD"})
        self.assertTrue(result["by_symbol"]["EURUSD"]["ranking_train"])
        self.assertTrue(result["by_symbol"]["GBPUSD"]["ranking_train"])
        self.assertLessEqual(len(result["portfolio"]["selected_candidate_ids"]), 8)
        self.assertEqual(result["portfolio"]["selection_method"], "GREEDY_UNION_TRAIN_ONLY")
        self.assertEqual(result["portfolio"]["validation_policy"], "FROZEN")
        self.assertGreater(result["portfolio"]["false_positive_penalty"], 0.0)
        self.assertGreater(result["portfolio"]["complexity_penalty"], 0.0)
        self.assertEqual(
            set(result["symbol_portfolio"]["selected_setup_by_symbol"]),
            {"EURUSD", "GBPUSD"},
        )
        self.assertEqual(result["symbol_portfolio"]["included_symbols"], 2)
        self.assertGreater(
            result["symbol_portfolio"]["metrics_train"]["opportunities"],
            0,
        )

    def test_symbol_portfolio_exclui_ativo_sem_positivo_no_treino(self) -> None:
        eurusd = self._candles("EURUSD", 380)
        gbpusd = self._candles("GBPUSD", 380)
        positions = [
            self._position("e1", eurusd, 220, "BUY"),
            self._position("e2", eurusd, 275, "SELL"),
            self._position("g1", gbpusd, 355, "BUY"),
        ]

        result = self._engine().analyze(
            positions,
            [*eurusd, *gbpusd],
        )
        symbol_portfolio = result["symbol_portfolio"]

        self.assertEqual(
            set(symbol_portfolio["selected_setup_by_symbol"]),
            {"EURUSD"},
        )
        self.assertEqual(symbol_portfolio["included_symbols"], 1)
        self.assertEqual(symbol_portfolio["excluded_symbols_count"], 1)
        self.assertEqual(
            symbol_portfolio["excluded_validation_positive_events"],
            1,
        )
        excluded = {row["symbol"]: row for row in symbol_portfolio["excluded_symbols"]}
        self.assertEqual(excluded["GBPUSD"]["reason"], "SEM_POSITIVOS_NO_TREINO")
        self.assertEqual(excluded["GBPUSD"]["train_positive_events"], 0)
        self.assertEqual(excluded["GBPUSD"]["validation_positive_events"], 1)
        self.assertEqual(symbol_portfolio["selection_segment"], "TRAIN")
        self.assertEqual(symbol_portfolio["validation_policy"], "FROZEN")

    def test_metricas_multilabel_por_direcao_e_evento(self) -> None:
        target_buy = np.asarray([True, False, False, True])
        target_sell = np.asarray([False, True, False, True])
        predicted_buy = np.asarray([True, True, False, True])
        predicted_sell = np.asarray([False, False, True, True])

        metrics = _finalize_counts(
            _counts_from_arrays(
                target_buy,
                target_sell,
                predicted_buy,
                predicted_sell,
                predicted_buy,
                predicted_sell,
            )
        )

        self.assertEqual(metrics["buy"]["true_positive"], 2)
        self.assertEqual(metrics["buy"]["false_positive"], 1)
        self.assertEqual(metrics["sell"]["true_positive"], 1)
        self.assertEqual(metrics["sell"]["false_positive"], 1)
        self.assertEqual(metrics["event"]["true_positive"], 3)
        self.assertEqual(metrics["direction_matches"], 3)
        self.assertEqual(metrics["exact_direction_set_matches"], 2)

    def test_saidas_pnl_nao_afetam_resultado_e_json_e_finito(self) -> None:
        candles = self._candles("EURUSD", 290)
        position = self._position("p1", candles, 240, "BUY")
        changed = replace(
            position,
            close_time=position.close_time + timedelta(days=100),
            close_price=999.0,
            commission=-100.0,
            swap=-200.0,
            profit=-10000.0,
        )
        engine = self._engine()

        baseline = engine.analyze([position], candles)
        altered = engine.analyze([changed], candles)

        self.assertEqual(baseline, altered)
        self.assertFalse(baseline["uses_exit_data"])
        json.dumps(baseline, allow_nan=False)

    def test_configuracao_invalida_falha_fechada(self) -> None:
        with self.assertRaises(ValueError):
            MultiEAIntrabarSearchEngine(
                MultiEAIntrabarSearchConfiguration(common_history_bars=100)
            )

    def _engine(self, **overrides: object) -> MultiEAIntrabarSearchEngine:
        values = {
            "maximum_ranked_candidates": 100,
            "portfolio_candidate_pool": 12,
            "portfolio_maximum_setups": 3,
        }
        values.update(overrides)
        return MultiEAIntrabarSearchEngine(
            MultiEAIntrabarSearchConfiguration(**values)  # type: ignore[arg-type]
        )

    def _global_row(
        self,
        result: dict[str, object],
        candidate_id: str,
    ) -> dict[str, object]:
        return next(
            row
            for row in result["global"]["ranking_train"]  # type: ignore[index,union-attr]
            if row["candidate_id"] == candidate_id
        )

    def _candles(self, symbol: str, count: int) -> list[MultiEACandle]:
        start = datetime(2025, 1, 1)
        result = []
        previous = 1.0
        for index in range(count):
            close = 1.0 + 0.015 * math.sin(index / 7.0) + index * 0.00003
            opening = previous
            result.append(
                MultiEACandle(
                    symbol=symbol,
                    source_symbol=symbol,
                    timeframe="M15",
                    timestamp=start + timedelta(minutes=15 * index),
                    open=opening,
                    high=max(opening, close) + 0.001,
                    low=min(opening, close) - 0.001,
                    close=close,
                    volume=100.0 + index % 20,
                )
            )
            previous = close
        return result

    def _wide_range_candles(
        self,
        symbol: str,
        count: int,
    ) -> list[MultiEACandle]:
        result = self._candles(symbol, count)
        return [
            replace(
                candle,
                high=max(candle.high, candle.close + 0.03),
                low=min(candle.low, candle.close - 0.03),
            )
            for candle in result
        ]

    def _position(
        self,
        position_id: str,
        candles: list[MultiEACandle],
        execution_index: int,
        direction: str,
    ) -> MultiEATradePosition:
        candle = candles[execution_index]
        entry_time = candle.timestamp + timedelta(minutes=5)
        return MultiEATradePosition(
            source_symbol=candle.symbol,
            symbol=candle.symbol,
            direction=direction,
            volume=0.01,
            open_time=entry_time,
            open_price=candle.open,
            close_time=entry_time + timedelta(hours=1),
            close_price=candle.close,
            commission=-0.01,
            swap=0.0,
            profit=1.0,
            source_row=execution_index,
            position_id=position_id,
        )


if __name__ == "__main__":
    unittest.main()
