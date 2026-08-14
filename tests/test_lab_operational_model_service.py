"""Tests for the canonical Lab M2-M5 runtime adapters."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from application.lab_operational_model_service import (
    LabOperationalDecision,
    LabOperationalModelService,
    MODEL_19_ID,
    MODEL_21_ID,
    MODEL_2_ID,
    MODEL_5_ID,
    MODEL_IDS,
    OFFICIAL_ALPHA_MODEL_SPECS,
    SUPPORTED_FOREX_PAIRS,
)
from application.operational_indicator_window import OPERATIONAL_INDICATOR_RAW_CANDLES


class LabOperationalModelServiceTest(unittest.TestCase):
    def test_mt5_english_candle_fields_are_normalized_for_lab_models(self) -> None:
        service = LabOperationalModelService()
        candles = [
            SimpleNamespace(
                timestamp=f"2026-07-29T{i:02d}:00:00+00:00",
                open=1.40,
                high=1.41,
                low=1.39,
                close=1.405,
                volume=100,
            )
            for i in range(3)
        ]

        normalized = service._candles(
            {("USDCAD", "H1"): candles},
            "USDCAD",
            "H1",
        )

        self.assertEqual(3, len(normalized))
        self.assertEqual("2026-07-29T00:00:00+00:00", normalized[0]["data"])
        self.assertEqual(1.40, normalized[0]["abertura"])
        self.assertEqual(1.41, normalized[0]["maxima"])
        self.assertEqual(1.39, normalized[0]["minima"])
        self.assertEqual(1.405, normalized[0]["fechamento"])

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

        m3_results = service.results(
            "MODELO_3_LAB_ALPHA_SUGERIDA_2_PLUS"
        )
        self.assertTrue(m3_results["USDCAD"]["research_qualified"])
        self.assertEqual(
            "QUALIFIED_FOR_DEMO_REPLAY",
            m3_results["USDCAD"]["research_status"],
        )
        for pair in expected - {"USDCAD"}:
            with self.subTest(m3_expansion_pair=pair):
                self.assertFalse(m3_results[pair]["research_qualified"])
                self.assertEqual(
                    "USER_APPROVED_DEMO_EXPANSION_UNVALIDATED",
                    m3_results[pair]["research_status"],
                )
                self.assertTrue(m3_results[pair]["demo_forward_enabled"])

        m4_results = service.results("MODELO_4_LAB_CONTEXTUAL_MTF")
        self.assertFalse(m4_results["AUDUSD"]["research_qualified"])
        self.assertEqual(
            "BEST_AVAILABLE_DEMO_CANDIDATE_UNCERTIFIED",
            m4_results["AUDUSD"]["research_status"],
        )
        for pair in expected - {"AUDUSD"}:
            with self.subTest(m4_expansion_pair=pair):
                self.assertFalse(m4_results[pair]["research_qualified"])
                self.assertEqual(
                    "USER_APPROVED_DEMO_EXPANSION_UNVALIDATED",
                    m4_results[pair]["research_status"],
                )
                self.assertTrue(m4_results[pair]["demo_forward_enabled"])

        formerly_blocked = service.winner(MODEL_2_ID, "GBPUSD") or {}
        self.assertTrue(formerly_blocked["demo_forward_enabled"])
        self.assertEqual(
            formerly_blocked["parity_status"],
            "DEMO_FORWARD_OPERATIONALLY_APPROVED",
        )
        self.assertFalse(formerly_blocked["evidence_demo_forward_enabled"])
        self.assertEqual(
            formerly_blocked["evidence_parity_status"],
            "REPLAY_VALIDATION_PENDING",
        )

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

    def test_mt5_server_clock_validates_broker_offset_entry_window(self) -> None:
        system_now = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
        server_current_bar = system_now + timedelta(hours=3)
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            self._write_manifest(manifest, enabled=True)
            service = LabOperationalModelService(
                manifest_path=manifest,
                now_provider=lambda: system_now,
                max_entry_delay_seconds=120.0,
            )
            candles = self._candles(server_current_bar)

            with patch(
                "application.lab_operational_model_service.build_m2_signal",
                side_effect=self._buy_signal,
            ):
                system_clock_decision = service.evaluate(
                    model_id=MODEL_2_ID,
                    pair="EURUSD",
                    candles_by_market={("EURUSD", "H1"): candles},
                    current_price=1.2,
                )
                server_clock_decision = service.evaluate(
                    model_id=MODEL_2_ID,
                    pair="EURUSD",
                    candles_by_market={("EURUSD", "H1"): candles},
                    current_price=1.2,
                    server_timestamp=(
                        server_current_bar + timedelta(seconds=10)
                    ).isoformat(),
                )

        self.assertFalse(system_clock_decision.ready)
        self.assertEqual(system_clock_decision.status, "INVALID_CURRENT_BAR_TIME")
        self.assertTrue(server_clock_decision.ready)
        self.assertEqual(server_clock_decision.status, "READY")
        self.assertIn(
            "ENTRY_CLOCK_SOURCE=MT5_SERVER",
            server_clock_decision.diagnostics,
        )

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

            self.assertEqual(normalize.call_count, OPERATIONAL_INDICATOR_RAW_CANDLES)

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

    def test_m23_override_bypasses_only_the_demo_forward_parity_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            self._write_manifest(manifest, enabled=False)
            service = LabOperationalModelService(manifest_path=manifest)

            direct = service.evaluate(
                model_id=MODEL_2_ID,
                pair="EURUSD",
                candles_by_market={},
                current_price=1.2,
            )
            routed_by_m23 = service.evaluate(
                model_id=MODEL_2_ID,
                pair="EURUSD",
                candles_by_market={},
                current_price=1.2,
                demo_forward_override=True,
            )

        self.assertEqual(direct.status, "BLOCKED_BY_EXECUTABLE_PARITY")
        self.assertNotEqual(
            routed_by_m23.status,
            "BLOCKED_BY_EXECUTABLE_PARITY",
        )
        self.assertFalse(routed_by_m23.ready)

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

    def test_m11_to_m21_materialize_one_official_alpha_for_all_pairs(self) -> None:
        service = LabOperationalModelService()

        for label, spec in OFFICIAL_ALPHA_MODEL_SPECS.items():
            with self.subTest(model=label):
                rows = service.results(MODEL_IDS[label])
                self.assertEqual(set(rows), set(SUPPORTED_FOREX_PAIRS))
                for row in rows.values():
                    self.assertEqual(row["alpha_id"], spec["alpha_id"])
                    self.assertEqual(row["timeframe"], spec["timeframe"])
                    self.assertTrue(row["demo_forward_enabled"])
                    self.assertEqual(row["exit_policy"], "RESEARCH_FIXED_SL_TP")
                    self.assertFalse(row["position_manager_enabled"])

    def test_m11_to_m21_evaluate_only_closed_candles_without_heavy_lab(self) -> None:
        now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        service = LabOperationalModelService(now_provider=lambda: now)
        candles = self._candles(now)
        sources = {
            (pair, timeframe): candles
            for pair in SUPPORTED_FOREX_PAIRS
            for timeframe in {"M1", "M15", "M30", "H1", "H4"}
        }
        market_row = SimpleNamespace(spread=0.0001, spread_average=0.0002)

        for label, spec in OFFICIAL_ALPHA_MODEL_SPECS.items():
            with self.subTest(model=label, alpha=spec["alpha_id"]):
                decision = service.evaluate(
                    model_id=MODEL_IDS[label],
                    pair="EURUSD",
                    candles_by_market=sources,
                    current_price=1.2,
                    server_timestamp=(now + timedelta(seconds=10)).isoformat(),
                    market_row=market_row,
                )
                self.assertNotIn(
                    decision.status,
                    {
                        "FEATURE_EVALUATION_ERROR",
                        "INSUFFICIENT_LIVE_CANDLES",
                        "INSUFFICIENT_CONTEXT_CANDLES",
                        "UNSUPPORTED_LAB_RUNTIME_ADAPTER",
                    },
                )
                self.assertEqual(decision.alpha_id, spec["alpha_id"])
                self.assertEqual(decision.signal_candle_time, candles[-2]["data"])

    def test_official_models_share_features_for_the_same_pair_timeframe(self) -> None:
        now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        service = LabOperationalModelService(now_provider=lambda: now)
        candles = self._candles(now)
        source = {("EURUSD", "H1"): candles}

        for label in ("M11", "M17"):
            service.evaluate(
                model_id=MODEL_IDS[label],
                pair="EURUSD",
                candles_by_market=source,
                current_price=1.2,
                server_timestamp=(now + timedelta(seconds=10)).isoformat(),
            )

        self.assertEqual(len(service._official_feature_cache), 1)

    def test_complete_m11_to_m21_cycle_stays_below_three_seconds(self) -> None:
        now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        service = LabOperationalModelService(now_provider=lambda: now)
        candles = self._candles(now)
        sources = {
            (pair, timeframe): candles
            for pair in SUPPORTED_FOREX_PAIRS
            for timeframe in {"M1", "M15", "M30", "H1", "H4"}
        }
        market_row = SimpleNamespace(spread=0.0001, spread_average=0.0002)

        started = time.perf_counter()
        for label in OFFICIAL_ALPHA_MODEL_SPECS:
            for pair in SUPPORTED_FOREX_PAIRS:
                service.evaluate(
                    model_id=MODEL_IDS[label],
                    pair=pair,
                    candles_by_market=sources,
                    current_price=1.2,
                    server_timestamp=(now + timedelta(seconds=10)).isoformat(),
                    market_row=market_row,
                )
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 3.0)
        self.assertEqual(len(service._official_feature_cache), 40)

    def test_m21_inverte_direcao_e_troca_exatamente_sl_tp_do_m19(self) -> None:
        now = datetime(2026, 8, 4, 12, 0, 10, tzinfo=timezone.utc)
        service = LabOperationalModelService(now_provider=lambda: now)
        m19 = service.winner(MODEL_19_ID, "EURUSD") or {}
        m21 = service.winner(MODEL_21_ID, "EURUSD") or {}
        m19_parameters = dict(m19["parameters"])
        m21_parameters = dict(m21["parameters"])
        features = {
            "close": 1.2000,
            "atr": 0.0010,
            "momentum": 0.0010,
            "volatility": 0.0002,
            "ema20": 1.2010,
            "ema50": 1.1990,
            "rsi": 55.0,
            "adx": 18.0,
            "tick_volume": 120.0,
            "tick_volume_average": 100.0,
        }
        market_row = SimpleNamespace(spread=0.0001, spread_average=0.0002)

        m19_direction, _, _ = service._official_alpha_direction(
            alpha_id=str(m19["alpha_id"]),
            features=features,
            parameters=m19_parameters,
            context_features=None,
            market_row=market_row,
        )
        m21_direction, _, diagnostics = service._official_alpha_direction(
            alpha_id=str(m21["alpha_id"]),
            features=features,
            parameters=m21_parameters,
            context_features=None,
            market_row=market_row,
        )

        self.assertEqual(m19_direction, "BUY")
        self.assertEqual(m21_direction, "SELL")
        self.assertIn("MIRROR_SOURCE_MODEL=M19", diagnostics)
        self.assertEqual(m21_parameters["stop_factor"], 4.0)
        self.assertEqual(m21_parameters["risk_reward"], 0.5)

        current_bar = "2026-08-04T12:00:00+00:00"
        common = {
            "pair": "EURUSD",
            "timeframe": "M1",
            "status": "SIGNAL_FROZEN",
            "ready": True,
            "signal_candle_time": "2026-08-04T11:59:00+00:00",
            "current_bar_time": current_bar,
            "atr": 0.0010,
        }
        m19_plan = service._decision_with_live_entry(
            LabOperationalDecision(
                model_id=MODEL_19_ID,
                direction="BUY",
                risk_reward=float(m19_parameters["risk_reward"]),
                alpha_id=str(m19["alpha_id"]),
                family="LIQUIDITY_SPREAD_FILTER",
                source_model="M19",
                parameters=m19_parameters,
                **common,
            ),
            1.2000,
            current_bar,
        )
        m21_plan = service._decision_with_live_entry(
            LabOperationalDecision(
                model_id=MODEL_21_ID,
                direction="SELL",
                risk_reward=float(m21_parameters["risk_reward"]),
                alpha_id=str(m21["alpha_id"]),
                family="LIQUIDITY_SPREAD_FILTER_MIRROR",
                source_model="M21",
                parameters=m21_parameters,
                **common,
            ),
            1.2000,
            current_bar,
        )

        self.assertAlmostEqual(float(m21_plan.stop), float(m19_plan.target))
        self.assertAlmostEqual(float(m21_plan.target), float(m19_plan.stop))

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
