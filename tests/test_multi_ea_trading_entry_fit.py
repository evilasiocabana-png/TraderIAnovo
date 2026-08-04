from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
import json
import unittest

from research.multi_ea_trading_entry_fit import (
    MultiEAM15EntryFitEngine,
    _Opportunity,
    _classification_metrics,
)
from research.multi_ea_trading_lab import MultiEACandle, MultiEATradePosition


class MultiEAM15EntryFitEngineTest(unittest.TestCase):
    def test_oraculo_100_porcento_nao_mascara_falsos_positivos_causais(self) -> None:
        candles = self._rising_candles(120)
        positions = [
            self._position("p1", candles, 70, "BUY"),
            self._position("p2", candles, 90, "BUY"),
        ]

        result = MultiEAM15EntryFitEngine().analyze(positions, candles)
        oracle = result["oracle_replay"]
        causal = result["causal_fit"]

        self.assertEqual(oracle["coverage_percent"], 100.0)
        self.assertEqual(oracle["precision"], 1.0)
        self.assertEqual(oracle["recall"], 1.0)
        self.assertTrue(oracle["uses_target_labels"])
        self.assertFalse(oracle["predictive_setup"])
        self.assertGreater(causal["coverage"]["negative_events"], 0)
        self.assertTrue(causal["negative_opportunities_included"])
        self.assertLess(
            max(row["precision"] for row in causal["ranking_train"]),
            1.0,
        )
        self.assertIn("ORACULO_NAO_PREDITIVO", " ".join(result["warnings"]))

    def test_candle_ainda_aberto_na_entrada_nao_altera_fit(self) -> None:
        candles = self._rising_candles(85)
        position = self._position("p1", candles, 70, "BUY")
        changed = list(candles)
        future = changed[71]
        changed[71] = replace(
            future,
            open=5.0,
            high=9.0,
            low=0.1,
            close=8.0,
        )

        original = MultiEAM15EntryFitEngine().analyze([position], candles)
        altered = MultiEAM15EntryFitEngine().analyze([position], changed)

        self.assertEqual(
            original["causal_fit"]["ranking_train"],
            altered["causal_fit"]["ranking_train"],
        )
        self.assertEqual(
            original["causal_fit"]["selected_candidate_id"],
            altered["causal_fit"]["selected_candidate_id"],
        )
        record = original["causal_fit"]["entry_records"][0]
        self.assertTrue(record["eligible"])
        self.assertEqual(record["split"], "TRAIN")
        self.assertEqual(record["observed_direction"], "BUY")
        self.assertIn(record["signal"], {"BUY", "SELL", "WAIT"})
        self.assertEqual(record["metrics"]["evaluation_unit"], "SOURCE_POSITION")
        self.assertEqual(
            record["metrics"]["signal_emitted"],
            record["signal"] in {"BUY", "SELL"},
        )
        self.assertEqual(
            record["metrics"]["directional_hit"],
            record["direction_match"],
        )
        self.assertEqual(
            record["m15_candle"]["timestamp"],
            candles[70].timestamp.isoformat(),
        )
        self.assertEqual(
            datetime.fromisoformat(record["m15_candle"]["close_time"]).replace(
                tzinfo=None
            ),
            candles[70].timestamp + timedelta(minutes=15),
        )
        self.assertFalse(original["methodology"]["lookahead"])

    def test_validacao_nao_escolhe_candidato_e_split_e_cronologico(self) -> None:
        candles = self._rising_candles(230)
        positions = [
            self._position(
                f"p{index}",
                candles,
                70 + index * 4,
                "BUY",
            )
            for index in range(30)
        ]
        changed_validation = [
            position if index < 21 else replace(position, direction="SELL")
            for index, position in enumerate(positions)
        ]
        engine = MultiEAM15EntryFitEngine()

        baseline = engine.analyze(positions, candles)
        changed = engine.analyze(changed_validation, candles)
        baseline_fit = baseline["causal_fit"]
        changed_fit = changed["causal_fit"]

        self.assertEqual(
            baseline_fit["selected_candidate_id"],
            changed_fit["selected_candidate_id"],
        )
        self.assertEqual(
            baseline_fit["selection_metrics_train"],
            changed_fit["selection_metrics_train"],
        )
        self.assertNotEqual(
            baseline_fit["validation_metrics_frozen"]["recall"],
            changed_fit["validation_metrics_frozen"]["recall"],
        )
        split = baseline_fit["split"]
        self.assertEqual(
            split["method"],
            "CRONOLOGICO_TREINO_VALIDACAO_COM_EMBARGO",
        )
        self.assertLess(
            datetime.fromisoformat(split["train_end"]),
            datetime.fromisoformat(split["validation_start"]),
        )
        self.assertGreaterEqual(split["validation_positive_events"], 5)
        self.assertEqual(len(baseline_fit["entry_records"]), 30)
        self.assertIn(
            "VALIDATION",
            {record["split"] for record in baseline_fit["entry_records"]},
        )

    def test_metricas_directionais_contabilizam_lado_errado_como_fp_e_fn(self) -> None:
        start = datetime(2026, 1, 1)
        rows = [
            (
                _Opportunity("EURUSD", 1, start, ("BUY",), ("p1",)),
                "BUY",
            ),
            (
                _Opportunity(
                    "EURUSD",
                    2,
                    start + timedelta(minutes=15),
                    ("SELL",),
                    ("p2",),
                ),
                "BUY",
            ),
            (
                _Opportunity(
                    "EURUSD",
                    3,
                    start + timedelta(minutes=30),
                    (),
                    (),
                ),
                "SELL",
            ),
            (
                _Opportunity(
                    "EURUSD",
                    4,
                    start + timedelta(minutes=45),
                    (),
                    (),
                ),
                "WAIT",
            ),
        ]

        metrics = _classification_metrics(rows)

        self.assertEqual(metrics["true_positive"], 1)
        self.assertEqual(metrics["false_positive"], 2)
        self.assertEqual(metrics["false_negative"], 1)
        self.assertEqual(metrics["true_negative"], 1)
        self.assertAlmostEqual(metrics["precision"], 1.0 / 3.0, places=7)
        self.assertEqual(metrics["recall"], 0.5)
        self.assertEqual(metrics["f1"], 0.4)

    def test_resultado_nao_depende_de_saida_profit_ou_swap_e_e_json_valido(self) -> None:
        candles = self._rising_candles(100)
        original = self._position("p1", candles, 75, "BUY")
        changed_outcome = replace(
            original,
            close_time=original.close_time + timedelta(days=20),
            close_price=0.25,
            commission=-99.0,
            swap=-50.0,
            profit=-1000.0,
        )
        engine = MultiEAM15EntryFitEngine()

        first = engine.analyze([original], candles)
        second = engine.analyze([changed_outcome], candles)

        self.assertEqual(first, second)
        self.assertFalse(first["causal_fit"]["uses_exit_data"])
        self.assertFalse(first["causal_fit"]["uses_observed_outcomes"])
        json.dumps(first, allow_nan=False)

    def _rising_candles(self, count: int) -> list[MultiEACandle]:
        start = datetime(2025, 1, 1)
        candles = []
        for index in range(count):
            close = 1.0 + index * 0.001
            candles.append(
                MultiEACandle(
                    symbol="EURUSD",
                    source_symbol="EURUSD",
                    timeframe="M15",
                    timestamp=start + timedelta(minutes=15 * index),
                    open=close - 0.0002,
                    high=close + 0.0004,
                    low=close - 0.0004,
                    close=close,
                    volume=100.0,
                )
            )
        return candles

    def _position(
        self,
        position_id: str,
        candles: list[MultiEACandle],
        closed_candle_index: int,
        direction: str,
    ) -> MultiEATradePosition:
        entry_time = (
            candles[closed_candle_index].timestamp
            + timedelta(minutes=20)
        )
        return MultiEATradePosition(
            source_symbol="EURUSD",
            symbol="EURUSD",
            direction=direction,
            volume=0.01,
            open_time=entry_time,
            open_price=candles[closed_candle_index].close,
            close_time=entry_time + timedelta(hours=1),
            close_price=candles[closed_candle_index].close + 0.001,
            commission=-0.01,
            swap=0.0,
            profit=1.0,
            source_row=closed_candle_index,
            position_id=position_id,
        )


if __name__ == "__main__":
    unittest.main()
