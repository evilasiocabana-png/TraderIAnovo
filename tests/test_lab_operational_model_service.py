"""Tests for the canonical Lab M2-M5 runtime adapters."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np

from application.lab_operational_model_service import (
    LabOperationalModelService,
    MODEL_2_ID,
    MODEL_5_ID,
)


class LabOperationalModelServiceTest(unittest.TestCase):
    def test_production_manifest_exposes_all_demo_forward_pairs_by_policy(self) -> None:
        service = LabOperationalModelService()

        enabled = {
            model: {
                pair
                for pair, row in service.results(model).items()
                if row["demo_forward_enabled"]
            }
            for model in (
                MODEL_2_ID,
                "MODELO_3_LAB_ALPHA_SUGERIDA_2_PLUS",
                "MODELO_4_LAB_CONTEXTUAL_MTF",
                MODEL_5_ID,
            )
        }

        expected = {
            "AUDUSD",
            "EURJPY",
            "EURUSD",
            "GBPUSD",
            "NZDUSD",
            "USDCAD",
            "USDCHF",
            "USDJPY",
        }
        for model_id, pairs in enabled.items():
            with self.subTest(model_id=model_id):
                self.assertEqual(pairs, expected)

        formerly_blocked = service.winner(MODEL_2_ID, "GBPUSD") or {}
        self.assertTrue(formerly_blocked["demo_forward_enabled"])
        self.assertEqual(
            formerly_blocked["parity_status"],
            "DEMO_FORWARD_OPERATIONALLY_APPROVED",
        )
        self.assertFalse(formerly_blocked["evidence_demo_forward_enabled"])
        self.assertEqual(formerly_blocked["evidence_parity_status"], "BLOCKED_PARITY")

    def test_closed_candle_signal_builds_fixed_sl_tp_at_live_price(self) -> None:
        now = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            self._write_manifest(manifest, enabled=True)
            service = LabOperationalModelService(
                manifest_path=manifest,
                now_provider=lambda: now,
            )
            candles = self._candles(now)

            def signal_for_last_candle(market: object, parameters: object) -> np.ndarray:
                del parameters
                signal = np.zeros(len(market.frame), dtype=np.int8)
                signal[-1] = 1
                return signal

            with patch(
                "application.lab_operational_model_service.build_m2_signal",
                side_effect=signal_for_last_candle,
            ) as build:
                decision = service.evaluate(
                    model_id=MODEL_2_ID,
                    pair="EURUSD",
                    candles_by_market={("EURUSD", "H1"): candles},
                    current_price=1.2000,
                )
                second = service.evaluate(
                    model_id=MODEL_2_ID,
                    pair="EURUSD",
                    candles_by_market={("EURUSD", "H1"): candles},
                    current_price=1.2010,
                )

            self.assertTrue(decision.ready)
            self.assertEqual(decision.direction, "BUY")
            self.assertLess(decision.stop or 0.0, 1.2000)
            self.assertGreater(decision.target or 0.0, 1.2000)
            risk = 1.2000 - float(decision.stop)
            reward = float(decision.target) - 1.2000
            self.assertAlmostEqual(reward / risk, 2.0)
            self.assertEqual(second.entry_price, 1.2010)
            self.assertEqual(build.call_count, 1)
            self.assertTrue(any(item.startswith("EMA20=") for item in decision.diagnostics))
            self.assertTrue(any(item.startswith("EMA50=") for item in decision.diagnostics))
            self.assertTrue(
                any(item.startswith("MOMENTUM_3=") for item in decision.diagnostics)
            )

    def test_stale_next_candle_window_blocks_order(self) -> None:
        current_bar = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            self._write_manifest(manifest, enabled=True)
            service = LabOperationalModelService(
                manifest_path=manifest,
                now_provider=lambda: current_bar + timedelta(minutes=10),
                max_entry_delay_seconds=120.0,
            )
            with patch(
                "application.lab_operational_model_service.build_m2_signal",
                side_effect=self._buy_signal,
            ):
                decision = service.evaluate(
                    model_id=MODEL_2_ID,
                    pair="EURUSD",
                    candles_by_market={
                        ("EURUSD", "H1"): self._candles(current_bar)
                    },
                    current_price=1.2,
                )

        self.assertFalse(decision.ready)
        self.assertEqual(decision.status, "STALE_SIGNAL_WINDOW")

    def test_reuses_normalized_candles_within_the_same_closed_bar(self) -> None:
        now = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            self._write_manifest(manifest, enabled=True)
            service = LabOperationalModelService(
                manifest_path=manifest,
                now_provider=lambda: now,
            )
            candles = self._candles(now)
            source = {("EURUSD", "H1"): candles}

            with (
                patch(
                    "application.lab_operational_model_service.build_m2_signal",
                    side_effect=self._buy_signal,
                ),
                patch.object(
                    service,
                    "_candle_dict",
                    wraps=service._candle_dict,
                ) as normalize,
            ):
                service.evaluate(
                    model_id=MODEL_2_ID,
                    pair="EURUSD",
                    candles_by_market=source,
                    current_price=1.2,
                )
                service.evaluate(
                    model_id=MODEL_2_ID,
                    pair="EURUSD",
                    candles_by_market=source,
                    current_price=1.201,
                )

            self.assertEqual(normalize.call_count, len(candles))

    def test_manifest_block_is_a_hard_runtime_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            self._write_manifest(manifest, enabled=False)
            service = LabOperationalModelService(manifest_path=manifest)

            decision = service.evaluate(
                model_id=MODEL_2_ID,
                pair="EURUSD",
                candles_by_market={},
                current_price=1.2,
            )

        self.assertFalse(decision.ready)
        self.assertEqual(decision.status, "BLOCKED_BY_EXECUTABLE_PARITY")

    def test_m5_m1_source_delegates_to_the_official_lab_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            payload = self._manifest_payload(enabled=True)
            payload["models"]["M5"] = {
                "results": {
                    "EURUSD": {
                        **payload["models"]["M2"]["results"]["EURUSD"],
                        "source_model": "M1",
                    }
                }
            }
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            service = LabOperationalModelService(manifest_path=manifest)

            decision = service.evaluate(
                model_id=MODEL_5_ID,
                pair="EURUSD",
                candles_by_market={},
                current_price=1.2,
            )

        self.assertFalse(decision.ready)
        self.assertEqual(decision.status, "DELEGATE_TO_LAB_M1")

    def _buy_signal(self, market: object, parameters: object) -> np.ndarray:
        del parameters
        signal = np.zeros(len(market.frame), dtype=np.int8)
        signal[-1] = 1
        return signal

    def _write_manifest(self, path: Path, *, enabled: bool) -> None:
        path.write_text(
            json.dumps(self._manifest_payload(enabled=enabled)),
            encoding="utf-8",
        )

    def _manifest_payload(self, *, enabled: bool) -> dict[str, object]:
        return {
            "models": {
                "M2": {
                    "results": {
                        "EURUSD": {
                            "pair": "EURUSD",
                            "alpha_id": "ALPHA_TEST",
                            "timeframe": "H1",
                            "demo_forward_enabled": enabled,
                            "parity_status": (
                                "DEMO_PARITY_APPROVED" if enabled else "BLOCKED_PARITY"
                            ),
                            "parity_reason": "fixture",
                            "parameters": {
                                "family": "TREND_IMPULSE",
                                "fast": 20,
                                "slow": 50,
                                "adx_min": 0,
                                "adx_rising": False,
                                "volume_min": 0,
                                "stop_factor": 2.0,
                                "risk_reward": 2.0,
                                "session": "ALL",
                                "weekdays": "ALL",
                                "atr_regime": "ALL",
                                "efficiency_min": 0.0,
                                "slope_aligned": False,
                                "body_atr": 0.0,
                                "close_extreme": 0.5,
                            },
                            "holdout_next_open": {"win_rate": 0.55},
                        }
                    }
                }
            }
        }

    def _candles(self, current_bar: datetime) -> list[dict[str, object]]:
        start = current_bar - timedelta(hours=299)
        candles: list[dict[str, object]] = []
        for index in range(300):
            timestamp = start + timedelta(hours=index)
            base = 1.1 + index * 0.00005
            candles.append(
                {
                    "data": timestamp.isoformat(),
                    "abertura": base,
                    "maxima": base + 0.0008,
                    "minima": base - 0.0008,
                    "fechamento": base + (0.0002 if index % 2 == 0 else -0.0001),
                    "volume": 100 + index % 7,
                }
            )
        return candles


if __name__ == "__main__":
    unittest.main()
