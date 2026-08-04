from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import math
import unittest

from research.multi_ea_rule_miner import (
    BUY,
    SELL,
    MultiEAM15RuleMiner,
    MultiEAM15RuleMinerConfiguration,
    _closed_feature_set,
    _multi_label_metrics_bits,
    _multi_label_metrics,
    _segment_bitset,
)
from research.multi_ea_trading_lab import MultiEACandle, MultiEATradePosition


class MultiEAM15RuleMinerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.configuration = MultiEAM15RuleMinerConfiguration(
            train_fraction=0.70,
            minimum_positive_events_for_split=8,
            minimum_validation_positive_events=2,
            common_history_bars=20,
            embargo_bars=2,
            minimum_train_signals=1,
            minimum_train_true_positives=1,
            maximum_seed_predicates_per_direction=8,
            maximum_and_rules_per_direction=8,
            maximum_ranked_rules=30,
            maximum_portfolio_candidates=12,
            maximum_portfolio_rules=4,
            rule_complexity_penalty=0.0,
            portfolio_rule_penalty=0.0,
        )

    def test_features_sao_fechadas_e_nao_leem_candle_futuro(self) -> None:
        candles = self._candles("EURUSD", 140)
        changed = list(candles)
        changed[100] = replace(
            changed[100],
            open=10.0,
            high=30.0,
            low=5.0,
            close=20.0,
            volume=999999.0,
        )

        baseline = _closed_feature_set(candles)
        altered = _closed_feature_set(changed)

        for name in baseline:
            self.assertEqual(baseline[name][99], altered[name][99], name)

    def test_quantis_and_e_portfolio_or_sao_expostos(self) -> None:
        candles = self._candles("EURUSD", 360)
        positions = self._positions(candles)

        result = MultiEAM15RuleMiner(self.configuration).analyze(
            positions,
            candles,
        )

        self.assertEqual(result["status"], "OK")
        self.assertTrue(result["predicate_catalog"])
        self.assertTrue(
            all(
                item["threshold_source"] == "TRAIN_QUANTILE_ONLY"
                for item in result["predicate_catalog"]
            )
        )
        self.assertGreater(result["rule_search"]["and_rules_evaluated"], 0)
        self.assertGreater(result["rule_search"]["and_rules_retained"], 0)
        self.assertTrue(
            any(
                row["logic"] == "AND"
                for row in result["rule_search"]["ranking_train"]
            )
        )
        self.assertEqual(result["selected_portfolio"]["method"], "GREEDY_OR")
        self.assertGreater(result["selected_portfolio"]["rule_count"], 0)
        self.assertEqual(
            result["selected_portfolio"]["validation_policy"],
            "FROZEN",
        )

    def test_validacao_nao_altera_quantis_nem_selecao_do_treino(self) -> None:
        candles = self._candles("EURUSD", 360)
        positions = self._positions(candles)
        engine = MultiEAM15RuleMiner(self.configuration)
        baseline = engine.analyze(positions, candles)
        validation_start = datetime.fromisoformat(
            baseline["split"]["validation_start"]
        )
        changed = []
        for index, candle in enumerate(candles):
            close_time = self._utc(candle.timestamp) + timedelta(minutes=15)
            if close_time >= validation_start:
                scale = 1.0 + (index % 7) * 0.5
                changed.append(
                    replace(
                        candle,
                        open=candle.open * scale,
                        high=candle.high * scale * 1.2,
                        low=candle.low * scale * 0.8,
                        close=candle.close * scale,
                        volume=candle.volume * 1000.0,
                    )
                )
            else:
                changed.append(candle)

        altered = engine.analyze(positions, changed)

        self.assertEqual(
            baseline["predicate_catalog"], altered["predicate_catalog"]
        )
        self.assertEqual(
            baseline["rule_search"]["ranking_train"],
            altered["rule_search"]["ranking_train"],
        )
        self.assertEqual(
            baseline["selected_portfolio"]["rule_ids"],
            altered["selected_portfolio"]["rule_ids"],
        )
        self.assertEqual(
            baseline["selected_portfolio"]["train_metrics"],
            altered["selected_portfolio"]["train_metrics"],
        )

    def test_saida_e_resultado_financeiro_nao_participam(self) -> None:
        candles = self._candles("EURUSD", 300)
        positions = self._positions(candles)
        changed = [
            replace(
                position,
                close_time=position.close_time + timedelta(days=100),
                close_price=9999.0,
                commission=-999.0,
                swap=-777.0,
                profit=-100000.0,
            )
            for position in positions
        ]
        engine = MultiEAM15RuleMiner(self.configuration)

        baseline = engine.analyze(positions, candles)
        altered = engine.analyze(changed, candles)

        self.assertEqual(baseline, altered)
        self.assertFalse(baseline["uses_exit_data"])
        self.assertFalse(baseline["uses_observed_outcomes"])

    def test_multilabel_preserva_buy_e_sell_na_mesma_janela(self) -> None:
        labels = bytearray((BUY | SELL, BUY, SELL, 0))
        buy_mask = bytearray((1, 1, 0, 0))
        sell_mask = bytearray((1, 0, 1, 1))

        metrics = _multi_label_metrics(
            buy_mask,
            sell_mask,
            labels,
            [0, 1, 2, 3],
        )

        self.assertEqual(metrics["true_positive"], 4)
        self.assertEqual(metrics["false_positive"], 1)
        self.assertEqual(metrics["false_negative"], 0)
        self.assertEqual(metrics["true_negative"], 3)
        self.assertEqual(metrics["observed_labels"], 4)
        self.assertEqual(metrics["predicted_labels"], 5)
        self.assertEqual(metrics["matched_events"], 3)
        self.assertEqual(metrics["exact_multi_label_events"], 3)
        self.assertEqual(metrics["event_recall"], 1.0)
        self.assertEqual(metrics["event_precision"], 0.75)

        buy_bits = int.from_bytes(buy_mask, "little")
        sell_bits = int.from_bytes(sell_mask, "little")
        label_buy = int.from_bytes(
            bytearray(1 if value & BUY else 0 for value in labels),
            "little",
        )
        label_sell = int.from_bytes(
            bytearray(1 if value & SELL else 0 for value in labels),
            "little",
        )
        bit_metrics = _multi_label_metrics_bits(
            buy_bits,
            sell_bits,
            label_buy,
            label_sell,
            _segment_bitset(4, [0, 1, 2, 3]),
            4,
        )
        self.assertEqual(metrics, bit_metrics)

    def test_eventos_opostos_sao_colapsados_sem_perder_rotulos(self) -> None:
        candles = self._candles("EURUSD", 180)
        first = self._position("buy", candles, 90, "BUY", 1)
        second = replace(first, position_id="sell", direction="SELL", source_row=2)
        configuration = replace(
            self.configuration,
            minimum_positive_events_for_split=2,
        )

        result = MultiEAM15RuleMiner(configuration).analyze(
            [first, second],
            candles,
        )

        self.assertEqual(result["coverage"]["eligible_positions"], 2)
        self.assertEqual(result["coverage"]["positive_events"], 1)
        self.assertEqual(result["coverage"]["collapsed_positions"], 1)
        self.assertEqual(result["coverage"]["multi_label_events"], 1)

    def test_resultado_e_deterministico_e_json_sem_nan(self) -> None:
        candles = self._candles("EURUSD", 260)
        positions = self._positions(candles)
        engine = MultiEAM15RuleMiner(self.configuration)

        first = engine.analyze(positions, candles)
        second = engine.analyze(positions, candles)

        self.assertEqual(first, second)
        json.dumps(first, allow_nan=False)

    def test_configuracao_invalida_falha_fechada(self) -> None:
        with self.assertRaises(ValueError):
            MultiEAM15RuleMiner(
                MultiEAM15RuleMinerConfiguration(quantiles=(0.5,))
            )
        with self.assertRaises(ValueError):
            MultiEAM15RuleMiner(
                MultiEAM15RuleMinerConfiguration(common_history_bars=19)
            )

    def _candles(self, symbol: str, count: int) -> list[MultiEACandle]:
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        candles = []
        for index in range(count):
            wave = 0.0025 * math.sin(index / 6.0)
            trend = 0.000015 * index
            close = 1.1 + trend + wave
            previous = (
                1.1 + 0.000015 * (index - 1) + 0.0025 * math.sin((index - 1) / 6.0)
                if index
                else close
            )
            open_price = previous
            candles.append(
                MultiEACandle(
                    symbol=symbol,
                    source_symbol=symbol,
                    timeframe="M15",
                    timestamp=start + timedelta(minutes=15 * index),
                    open=open_price,
                    high=max(open_price, close) + 0.00035,
                    low=min(open_price, close) - 0.00035,
                    close=close,
                    volume=100.0 + 20.0 * math.sin(index / 5.0) + index % 9,
                )
            )
        return candles

    def _positions(
        self,
        candles: list[MultiEACandle],
    ) -> list[MultiEATradePosition]:
        positions = []
        indexes = range(35, len(candles) - 20, 6)
        for sequence, candle_index in enumerate(indexes, 1):
            direction = "BUY" if sequence % 3 else "SELL"
            positions.append(
                self._position(
                    f"p{sequence}",
                    candles,
                    candle_index,
                    direction,
                    sequence,
                )
            )
            if sequence % 11 == 0:
                positions.append(
                    self._position(
                        f"p{sequence}-opposite",
                        candles,
                        candle_index,
                        "SELL" if direction == "BUY" else "BUY",
                        1000 + sequence,
                    )
                )
        return positions

    @staticmethod
    def _position(
        position_id: str,
        candles: list[MultiEACandle],
        candle_index: int,
        direction: str,
        source_row: int,
    ) -> MultiEATradePosition:
        candle = candles[candle_index]
        open_time = candle.timestamp + timedelta(minutes=20)
        return MultiEATradePosition(
            source_symbol=candle.symbol,
            symbol=candle.symbol,
            direction=direction,
            volume=0.01,
            open_time=open_time,
            open_price=candle.close,
            close_time=open_time + timedelta(hours=1),
            close_price=candle.close,
            commission=-0.01,
            swap=0.0,
            profit=1.0,
            source_row=source_row,
            position_id=position_id,
        )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


if __name__ == "__main__":
    unittest.main()
