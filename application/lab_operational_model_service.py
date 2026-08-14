"""Light runtime adapters for the researched operational Lab models."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import numpy as np

from application.operational_indicator_window import (
    OPERATIONAL_INDICATOR_CLOSED_CANDLES,
    OPERATIONAL_INDICATOR_RAW_CANDLES,
)

from research.alpha_suggested.alpha_suggested_1_plus_discovery import (
    build_signal as build_m2_signal,
    engineer_features,
)
from research.alpha_suggested.alpha_suggested_2_plus_individual import (
    build_signal as build_m3_signal,
    enrich_market,
)
from research.alpha_suggested.model2_trend_pullback import (
    MODEL_2_CONTEXT_TIMEFRAME,
    MODEL_2_FAMILY,
    evaluate_trend_pullback,
    model2_operational_results,
    trend_pullback_operational_results,
)
from research.alpha_suggested.model4_contextual_frontier import (
    apply_context_overlay,
    build_contexts,
)


MODEL_2_ID = "MODELO_2_LAB_ALPHA_SUGERIDA_1_PLUS"
MODEL_3_ID = "MODELO_3_LAB_ALPHA_SUGERIDA_2_PLUS"
MODEL_4_ID = "MODELO_4_LAB_CONTEXTUAL_MTF"
MODEL_5_ID = "MODELO_5_LAB_CONSOLIDADO"
MODEL_8_ID = "MODELO_8_TREND_PULLBACK_H1_M5"
MODEL_9_ID = "MODELO_9_TREND_PULLBACK_M15_M1"
MODEL_10_ID = "MODELO_10_TREND_PULLBACK_D1_M15"
MODEL_11_ID = "MODELO_11_ALPHA001_TREND_MOMENTUM"
MODEL_12_ID = "MODELO_12_ALPHA005_DONCHIAN_BREAKOUT"
MODEL_13_ID = "MODELO_13_ALPHA006_ADX_TREND_STRENGTH"
MODEL_14_ID = "MODELO_14_ALPHA007_MACD_MOMENTUM_SHIFT"
MODEL_15_ID = "MODELO_15_ALPHA011_PIVOT_REJECTION"
MODEL_16_ID = "MODELO_16_ALPHA012_VWAP_MEAN_REVERSION"
MODEL_17_ID = "MODELO_17_ALPHA013_SUPPORT_RESISTANCE"
MODEL_18_ID = "MODELO_18_ALPHA014_MULTI_TIMEFRAME"
MODEL_19_ID = "MODELO_19_ALPHA015_LIQUIDITY_SPREAD"
MODEL_20_ID = "MODELO_20_ALPHA016_REVERSAL"
MODEL_21_ID = "MODELO_21_ESPELHO_M19"
MODEL_22_ID = "MODELO_22_ESPELHO_M9"
MODEL_IDS = {
    "M2": MODEL_2_ID,
    "M3": MODEL_3_ID,
    "M4": MODEL_4_ID,
    "M5": MODEL_5_ID,
    "M8": MODEL_8_ID,
    "M9": MODEL_9_ID,
    "M10": MODEL_10_ID,
    "M11": MODEL_11_ID,
    "M12": MODEL_12_ID,
    "M13": MODEL_13_ID,
    "M14": MODEL_14_ID,
    "M15": MODEL_15_ID,
    "M16": MODEL_16_ID,
    "M17": MODEL_17_ID,
    "M18": MODEL_18_ID,
    "M19": MODEL_19_ID,
    "M20": MODEL_20_ID,
    "M21": MODEL_21_ID,
    "M22": MODEL_22_ID,
}
MODEL_LABELS = {value: key for key, value in MODEL_IDS.items()}
FIXED_EXIT_POLICY = "RESEARCH_FIXED_SL_TP"
DEFAULT_MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "alpha_suggested"
    / "lab_operational_models_manifest.json"
)
MINIMUM_DISTANCE_PERCENT = 0.0005
TREND_PULLBACK_MODEL_SPECS = {
    "M8": {
        "alpha_id": "ALPHA_M8_TREND_PULLBACK_H1_M5",
        "family": "TREND_PULLBACK_M5_H1",
        "entry_timeframe": "M5",
        "context_timeframe": "H1",
    },
    "M9": {
        "alpha_id": "ALPHA_M9_TREND_PULLBACK_M15_M1",
        "family": "TREND_PULLBACK_M1_M15",
        "entry_timeframe": "M1",
        "context_timeframe": "M15",
    },
    "M10": {
        "alpha_id": "ALPHA_M10_TREND_PULLBACK_D1_M15",
        "family": "TREND_PULLBACK_M15_D1",
        "entry_timeframe": "M15",
        "context_timeframe": "D1",
    },
    "M22": {
        "alpha_id": "ALPHA_M9_TREND_PULLBACK_M15_M1_MIRROR",
        "family": "TREND_PULLBACK_M1_M15_MIRROR",
        "entry_timeframe": "M1",
        "context_timeframe": "M15",
        "mirror_source_model": "M9",
        "mirror_swap_sl_tp": True,
    },
}

SUPPORTED_FOREX_PAIRS = (
    "AUDUSD",
    "EURJPY",
    "EURUSD",
    "GBPUSD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "USDJPY",
)

# Frozen from the 2026-07-21 Lab snapshot after discarding samples below 50.
# These are Demo hypotheses, not a promise of profitability. ALPHA015 is a gate,
# so M19 uses EMA/momentum only as the directional carrier.
OFFICIAL_ALPHA_MODEL_SPECS: dict[str, dict[str, Any]] = {
    "M11": {
        "alpha_id": "ALPHA001",
        "family": "TREND_MOMENTUM",
        "timeframe": "H1",
        "parameters": {
            "ema_curta": 9,
            "ema_longa": 21,
            "rsi_sobrevenda": 30.0,
            "rsi_sobrecompra": 70.0,
            "stop_factor": 1.5,
            "risk_reward": 1.5,
            "momentum_threshold": 0.0,
            "volatility_threshold": 0.0003,
        },
        "evidence": {"pair": "EURUSD", "sample_size": 145, "ict_score": 61.72},
    },
    "M12": {
        "alpha_id": "ALPHA005",
        "family": "DONCHIAN_BREAKOUT",
        "timeframe": "M30",
        "parameters": {
            "donchian_period": 20,
            "stop_factor": 1.5,
            "risk_reward": 1.5,
            "momentum_threshold": 0.0,
            "breakout_buffer": 0.0001,
        },
        "evidence": {"pair": "AUDUSD", "sample_size": 102, "ict_score": 52.71},
    },
    "M13": {
        "alpha_id": "ALPHA006",
        "family": "ADX_TREND_STRENGTH",
        "timeframe": "M15",
        "parameters": {
            "ema_curta": 20,
            "ema_longa": 100,
            "adx_min": 30.0,
            "stop_factor": 2.5,
            "risk_reward": 2.0,
            "momentum_threshold": 0.0,
        },
        "evidence": {"pair": "USDCAD", "sample_size": 57, "ict_score": 61.31},
    },
    "M14": {
        "alpha_id": "ALPHA007",
        "family": "MACD_MOMENTUM_SHIFT",
        "timeframe": "M30",
        "parameters": {
            "ema_curta": 9,
            "ema_longa": 21,
            "stop_factor": 1.5,
            "risk_reward": 1.5,
        },
        "evidence": {"pair": "NZDUSD", "sample_size": 213, "ict_score": 47.08},
    },
    "M15": {
        "alpha_id": "ALPHA011",
        "family": "PIVOT_REJECTION",
        "timeframe": "M30",
        "parameters": {
            "rsi_sobrevenda": 40.0,
            "rsi_sobrecompra": 60.0,
            "stop_factor": 1.5,
            "risk_reward": 2.0,
        },
        "evidence": {"pair": "EURUSD", "sample_size": 241, "ict_score": 49.11},
    },
    "M16": {
        "alpha_id": "ALPHA012",
        "family": "VWAP_MEAN_REVERSION",
        "timeframe": "M30",
        "parameters": {
            "rsi_sobrevenda": 30.0,
            "rsi_sobrecompra": 70.0,
            "z_threshold": 1.0,
            "stop_factor": 2.0,
            "risk_reward": 2.0,
        },
        "evidence": {"pair": "EURJPY", "sample_size": 82, "ict_score": 61.10},
    },
    "M17": {
        "alpha_id": "ALPHA013",
        "family": "SUPPORT_RESISTANCE_REACTION",
        "timeframe": "H1",
        "parameters": {
            "rsi_sobrevenda": 40.0,
            "rsi_sobrecompra": 60.0,
            "stop_factor": 2.5,
            "risk_reward": 2.0,
        },
        "evidence": {"pair": "NZDUSD", "sample_size": 107, "ict_score": 62.25},
    },
    "M18": {
        "alpha_id": "ALPHA014",
        "family": "MULTI_TIMEFRAME_ALIGNMENT",
        "timeframe": "M30",
        "parameters": {
            "ema_curta": 50,
            "ema_longa": 200,
            "context_timeframe": "H4",
            "stop_factor": 2.0,
            "risk_reward": 2.0,
            "momentum_threshold": 0.0,
        },
        "evidence": {"pair": "USDCAD", "sample_size": 71, "ict_score": 66.41},
    },
    "M19": {
        "alpha_id": "ALPHA015",
        "family": "LIQUIDITY_SPREAD_FILTER",
        "timeframe": "M1",
        "parameters": {
            "ema_curta": 20,
            "ema_longa": 50,
            "volume_factor": 1.0,
            "stop_factor": 2.0,
            "risk_reward": 2.0,
            "momentum_threshold": 0.0,
        },
        "evidence": {"pair": "N/D", "sample_size": 0, "ict_score": 15.0},
    },
    "M20": {
        "alpha_id": "ALPHA016",
        "family": "BETA002_REVERSAL_SIGNAL",
        "timeframe": "M30",
        "parameters": {
            "ema_curta": 9,
            "ema_longa": 21,
            "reversal_strength": 0.0006,
            "volatility_threshold": 0.0001,
            "stop_factor": 2.5,
            "risk_reward": 2.0,
        },
        "evidence": {"pair": "USDCAD", "sample_size": 63, "ict_score": 57.97},
    },
    "M21": {
        "alpha_id": "ALPHA015_M19_MIRROR",
        "family": "LIQUIDITY_SPREAD_FILTER_MIRROR",
        "timeframe": "M1",
        "parameters": {
            "mirror_source_model": "M19",
            "mirror_source_alpha": "ALPHA015",
            "mirror_swap_sl_tp": True,
        },
        "evidence": {"pair": "N/D", "sample_size": 0, "ict_score": 15.0},
    },
}
OFFICIAL_ALPHA_MODEL_IDS = tuple(MODEL_IDS[label] for label in OFFICIAL_ALPHA_MODEL_SPECS)


def official_alpha_operational_results(model_label: str) -> dict[str, dict[str, Any]]:
    """Materialize one immutable Demo contract per pair for M11-M21."""
    label = str(model_label or "").upper()
    spec = OFFICIAL_ALPHA_MODEL_SPECS.get(label)
    if spec is None:
        return {}
    model_parameters = dict(spec["parameters"])
    if label == "M21":
        source_parameters = dict(OFFICIAL_ALPHA_MODEL_SPECS["M19"]["parameters"])
        source_stop_factor = float(source_parameters["stop_factor"])
        source_risk_reward = float(source_parameters["risk_reward"])
        model_parameters = {
            **source_parameters,
            **model_parameters,
            "stop_factor": source_stop_factor * source_risk_reward,
            "risk_reward": 1.0 / source_risk_reward,
            "mirror_source_stop_factor": source_stop_factor,
            "mirror_source_risk_reward": source_risk_reward,
        }
    parameters = {
        **model_parameters,
        "alpha": spec["alpha_id"],
        "family": spec["family"],
        "beta_id": "BETA_FIXED_SL_TP",
        "exit_policy": FIXED_EXIT_POLICY,
    }
    evidence = dict(spec.get("evidence") or {})
    return {
        pair: {
            "pair": pair,
            "alpha_id": spec["alpha_id"],
            "timeframe": spec["timeframe"],
            "source_model": label,
            "demo_forward_enabled": True,
            "exit_policy": FIXED_EXIT_POLICY,
            "position_manager_enabled": False,
            "research_qualified": bool(evidence.get("sample_size", 0) >= 50),
            "research_status": (
                "FROZEN_FROM_ROBUST_LAB_SAMPLE"
                if evidence.get("sample_size", 0) >= 50
                else "USER_APPROVED_DEMO_HYPOTHESIS_UNCERTIFIED"
            ),
            "parity_status": "DEMO_FORWARD_OPERATIONALLY_APPROVED",
            "parity_reason": (
                "Contrato congelado para Demo; conta real continua bloqueada."
            ),
            "parameters": dict(parameters),
            "evidence": dict(evidence),
        }
        for pair in SUPPORTED_FOREX_PAIRS
    }


@dataclass(frozen=True)
class LabOperationalDecision:
    """One auditable decision produced from the exact researched indicators."""

    model_id: str
    pair: str
    timeframe: str
    status: str
    ready: bool
    direction: str = "WAIT"
    signal_candle_time: str = "N/D"
    current_bar_time: str = "N/D"
    entry_price: float | None = None
    stop: float | None = None
    target: float | None = None
    risk_reward: float = 0.0
    atr: float | None = None
    alpha_id: str = "N/D"
    family: str = "N/D"
    source_model: str = "N/D"
    reason: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    context_overlay: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()
    parity_status: str = "N/D"


@dataclass
class LabOperationalModelService:
    """Evaluate only plans frozen in the tracked Lab operational manifest."""

    manifest_path: Path = DEFAULT_MANIFEST_PATH
    max_entry_delay_seconds: float = 120.0
    now_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    _manifest_cache: dict[str, Any] = field(default_factory=dict, repr=False)
    _manifest_mtime_ns: int = field(default=-1, repr=False)
    _decision_cache: dict[tuple[str, str, str, str], LabOperationalDecision] = field(
        default_factory=dict,
        repr=False,
    )
    _m4_market_cache: dict[tuple[tuple[str, str], ...], dict[str, Any]] = field(
        default_factory=dict,
        repr=False,
    )
    _candle_rows_cache: dict[tuple[object, ...], list[dict[str, Any]]] = field(
        default_factory=dict,
        repr=False,
    )
    _official_feature_cache: dict[tuple[str, str, str], dict[str, Any]] = field(
        default_factory=dict,
        repr=False,
    )
    _trend_pullback_reading_cache: dict[tuple[object, ...], Any] = field(
        default_factory=dict,
        repr=False,
    )

    def model_label(self, model_id: str) -> str:
        return MODEL_LABELS.get(str(model_id or "").upper(), "N/D")

    def results(self, model_id: str) -> dict[str, dict[str, Any]]:
        label = self.model_label(model_id)
        if (
            label == "M2"
            and self.manifest_path.resolve() == DEFAULT_MANIFEST_PATH.resolve()
        ):
            return model2_operational_results()
        if (
            label in TREND_PULLBACK_MODEL_SPECS
            and self.manifest_path.resolve() == DEFAULT_MANIFEST_PATH.resolve()
        ):
            return trend_pullback_operational_results(
                model_label=label,
                **TREND_PULLBACK_MODEL_SPECS[label],
            )
        if (
            label in OFFICIAL_ALPHA_MODEL_SPECS
            and self.manifest_path.resolve() == DEFAULT_MANIFEST_PATH.resolve()
        ):
            return official_alpha_operational_results(label)
        model = dict(self._load_manifest().get("models", {}).get(label) or {})
        rows = model.get("results") or {}
        return {
            str(pair).upper(): dict(row)
            for pair, row in dict(rows).items()
            if isinstance(row, dict)
        }

    def winner(self, model_id: str, pair: str) -> dict[str, Any] | None:
        return self.results(model_id).get(str(pair or "").upper())

    def timeframes_by_pair(self, model_id: str) -> dict[str, str]:
        return {
            pair: str(row.get("timeframe") or "M1").upper()
            for pair, row in self.results(model_id).items()
        }

    def required_timeframes(self, model_ids: Iterable[str]) -> dict[str, set[str]]:
        required: dict[str, set[str]] = {}
        normalized_models = {str(model_id or "").upper() for model_id in model_ids}
        needs_m4_context = MODEL_4_ID in normalized_models or (
            MODEL_5_ID in normalized_models
            and any(
                str(row.get("source_model") or "").upper().replace("-P", "")
                == "M4"
                for row in self.results(MODEL_5_ID).values()
            )
        )
        for model_id in normalized_models:
            for pair, row in self.results(model_id).items():
                market_timeframes = required.setdefault(pair, set())
                market_timeframes.add(str(row.get("timeframe") or "M1").upper())
                context_timeframe = str(
                    (row.get("parameters") or {}).get("context_timeframe") or ""
                ).upper()
                if context_timeframe:
                    market_timeframes.add(context_timeframe)
        if needs_m4_context:
            for pair in self.results(MODEL_4_ID):
                required.setdefault(pair, set()).update({"M30", "H1", "H4"})
        return required

    def evaluate(
        self,
        *,
        model_id: str,
        pair: str,
        candles_by_market: Mapping[tuple[str, str], Iterable[object]],
        current_price: float | None,
        server_timestamp: str | None = None,
        market_row: object | None = None,
        demo_forward_override: bool = False,
    ) -> LabOperationalDecision:
        normalized_model = str(model_id or "").upper()
        normalized_pair = str(pair or "").upper()
        winner = self.winner(normalized_model, normalized_pair)
        if winner is None:
            return self._wait(
                normalized_model,
                normalized_pair,
                "N/D",
                "PAIR_NOT_IN_LAB_MODEL",
                "Par ausente do plano pesquisado para este modelo.",
            )
        timeframe = str(winner.get("timeframe") or "N/D").upper()
        common = self._winner_values(winner)
        if not bool(winner.get("demo_forward_enabled", False)) and not demo_forward_override:
            return self._wait(
                normalized_model,
                normalized_pair,
                timeframe,
                "BLOCKED_BY_EXECUTABLE_PARITY",
                str(winner.get("parity_reason") or "Par bloqueado pela paridade."),
                **common,
            )
        label = self.model_label(normalized_model)
        source_model = str(winner.get("source_model") or label).upper().replace("-P", "")
        if label in OFFICIAL_ALPHA_MODEL_SPECS:
            return self._evaluate_official_alpha_model(
                model_id=normalized_model,
                pair=normalized_pair,
                winner=winner,
                candles_by_market=candles_by_market,
                current_price=current_price,
                server_timestamp=server_timestamp,
                market_row=market_row,
            )
        if label == "M5" and source_model == "M1":
            return self._wait(
                normalized_model,
                normalized_pair,
                timeframe,
                "DELEGATE_TO_LAB_M1",
                "M5 usa o Trade Plan M1 vigente quando Alpha e TF coincidem.",
                **common,
            )
        if label in {"M2", "M8", "M9", "M10", "M22"}:
            if (
                str((winner.get("parameters") or {}).get("family") or "").upper()
                .startswith("TREND_PULLBACK_")
            ):
                return self._evaluate_trend_pullback(
                    model_id=normalized_model,
                    pair=normalized_pair,
                    winner=winner,
                    candles_by_market=candles_by_market,
                    current_price=current_price,
                    server_timestamp=server_timestamp,
                )
            return self._evaluate_standard(
                model_id=normalized_model,
                pair=normalized_pair,
                timeframe=timeframe,
                winner=winner,
                candles_by_market=candles_by_market,
                current_price=current_price,
                server_timestamp=server_timestamp,
                signal_builder=build_m2_signal,
                enrich=False,
            )
        if label == "M3" or (label == "M5" and source_model == "M3"):
            return self._evaluate_standard(
                model_id=normalized_model,
                pair=normalized_pair,
                timeframe=timeframe,
                winner=winner,
                candles_by_market=candles_by_market,
                current_price=current_price,
                server_timestamp=server_timestamp,
                signal_builder=build_m3_signal,
                enrich=True,
            )
        if label == "M4" or (label == "M5" and source_model == "M4"):
            return self._evaluate_m4(
                model_id=normalized_model,
                pair=normalized_pair,
                winner=winner,
                candles_by_market=candles_by_market,
                current_price=current_price,
                server_timestamp=server_timestamp,
            )
        return self._wait(
            normalized_model,
            normalized_pair,
            timeframe,
            "UNSUPPORTED_LAB_RUNTIME_ADAPTER",
            f"Adaptador runtime ausente para {label}/{source_model}.",
            **common,
        )

    def _evaluate_official_alpha_model(
        self,
        *,
        model_id: str,
        pair: str,
        winner: dict[str, Any],
        candles_by_market: Mapping[tuple[str, str], Iterable[object]],
        current_price: float | None,
        server_timestamp: str | None,
        market_row: object | None,
    ) -> LabOperationalDecision:
        """Evaluate M11-M21 once per closed candle using shared features."""
        timeframe = str(winner.get("timeframe") or "M1").upper()
        candles = self._candles(candles_by_market, pair, timeframe)
        common = self._winner_values(winner)
        if len(candles) < OPERATIONAL_INDICATOR_RAW_CANDLES:
            return self._wait(
                model_id,
                pair,
                timeframe,
                "INSUFFICIENT_LIVE_CANDLES",
                (
                    "Alpha oficial exige janela deslizante de 200 candles "
                    f"fechados; recebeu {max(len(candles) - 1, 0)}."
                ),
                **common,
            )
        signal_time = str(candles[-2]["data"])
        current_time = str(candles[-1]["data"])
        cache_key = (model_id, pair, timeframe, signal_time)
        cached = self._decision_cache.get(cache_key)
        if cached is not None:
            return self._decision_with_live_entry(
                cached,
                current_price,
                current_time,
                server_timestamp=server_timestamp,
            )
        parameters = dict(winner.get("parameters") or {})
        try:
            features = self._official_features(pair, timeframe, candles[:-1])
            context_features: dict[str, Any] | None = None
            context_timeframe = str(parameters.get("context_timeframe") or "").upper()
            if context_timeframe:
                context_candles = self._candles(
                    candles_by_market,
                    pair,
                    context_timeframe,
                )
                if len(context_candles) < OPERATIONAL_INDICATOR_RAW_CANDLES:
                    return self._wait(
                        model_id,
                        pair,
                        timeframe,
                        "INSUFFICIENT_CONTEXT_CANDLES",
                        (
                            f"{common['alpha_id']} exige 200 candles fechados em "
                            f"{context_timeframe}; recebeu "
                            f"{max(len(context_candles) - 1, 0)}."
                        ),
                        signal_candle_time=signal_time,
                        current_bar_time=current_time,
                        **common,
                    )
                context_features = self._official_features(
                    pair,
                    context_timeframe,
                    context_candles[:-1],
                )
            direction, reason, diagnostics = self._official_alpha_direction(
                alpha_id=str(winner.get("alpha_id") or ""),
                features=features,
                parameters=parameters,
                context_features=context_features,
                market_row=market_row,
            )
            atr = self._positive_float(features.get("atr"))
        except (KeyError, TypeError, ValueError, IndexError, ZeroDivisionError) as exc:
            return self._wait(
                model_id,
                pair,
                timeframe,
                "FEATURE_EVALUATION_ERROR",
                f"Falha ao calcular {common['alpha_id']}: {exc}",
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                **common,
            )
        if direction == "WAIT":
            decision = self._wait(
                model_id,
                pair,
                timeframe,
                "NO_CLOSED_CANDLE_SIGNAL",
                reason,
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                atr=atr,
                diagnostics=diagnostics,
                **common,
            )
        else:
            decision = LabOperationalDecision(
                model_id=model_id,
                pair=pair,
                timeframe=timeframe,
                status="SIGNAL_FROZEN",
                ready=True,
                direction=direction,
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                atr=atr,
                risk_reward=float(parameters.get("risk_reward", 0.0) or 0.0),
                reason=reason,
                diagnostics=diagnostics,
                **common,
            )
        self._decision_cache[cache_key] = decision
        self._trim_caches()
        return self._decision_with_live_entry(
            decision,
            current_price,
            current_time,
            server_timestamp=server_timestamp,
        )

    def _evaluate_trend_pullback(
        self,
        *,
        model_id: str,
        pair: str,
        winner: dict[str, Any],
        candles_by_market: Mapping[tuple[str, str], Iterable[object]],
        current_price: float | None,
        server_timestamp: str | None,
    ) -> LabOperationalDecision:
        timeframe = str(winner.get("timeframe") or "M15").upper()
        parameters = dict(winner.get("parameters") or {})
        context_timeframe = str(
            parameters.get("context_timeframe") or MODEL_2_CONTEXT_TIMEFRAME
        ).upper()
        model_label = self.model_label(model_id)
        candles = self._candles(candles_by_market, pair, timeframe)
        context = self._candles(candles_by_market, pair, context_timeframe)
        common = self._winner_values(winner)
        if len(candles) < 60 or len(context) < 60:
            return self._wait(
                model_id,
                pair,
                timeframe,
                "INSUFFICIENT_LIVE_CANDLES",
                (
                    f"{model_label} exige pelo menos 60 candles em {timeframe} "
                    f"e {context_timeframe}; recebeu {timeframe}={len(candles)}, "
                    f"{context_timeframe}={len(context)}."
                ),
                **common,
            )

        signal_time = str(candles[-2]["data"])
        current_time = str(candles[-1]["data"])
        cache_key = (model_id, pair, timeframe, signal_time)
        cached = self._decision_cache.get(cache_key)
        if cached is not None:
            return self._decision_with_live_entry(
                cached,
                current_price,
                current_time,
                server_timestamp=server_timestamp,
            )
        reading_signature = tuple(
            (name, str(parameters.get(name)))
            for name in (
                "fast",
                "slow",
                "context_fast",
                "context_slow",
                "adx_period",
                "adx_min",
                "atr_period",
                "pullback_rule",
                "confirmation_rule",
            )
        )
        reading_cache_key = (
            pair,
            timeframe,
            context_timeframe,
            signal_time,
            str(context[-2]["data"]),
            reading_signature,
        )
        try:
            reading = self._trend_pullback_reading_cache.get(reading_cache_key)
            if reading is None:
                reading = evaluate_trend_pullback(
                    candles[:-1],
                    context[:-1],
                    parameters,
                    model_label=model_label,
                )
                self._trend_pullback_reading_cache[reading_cache_key] = reading
                self._trim_caches()
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            return self._wait(
                model_id,
                pair,
                timeframe,
                "FEATURE_EVALUATION_ERROR",
                f"Falha ao calcular {model_label} Trend Pullback: {exc}",
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                **common,
            )

        mirror_source_model = str(
            parameters.get("mirror_source_model") or ""
        ).upper()
        mirror_enabled = bool(parameters.get("mirror_swap_sl_tp", False))
        direction_value = -reading.direction if mirror_enabled else reading.direction
        diagnostics = reading.diagnostics
        if mirror_enabled:
            diagnostics += (
                f"MIRROR_SOURCE_MODEL={mirror_source_model or 'N/D'}",
                "MIRROR_DIRECTION=INVERTED",
                "MIRROR_LEVELS=SL_M22_TP_M9__TP_M22_SL_M9",
            )

        if direction_value == 0:
            decision = self._wait(
                model_id,
                pair,
                timeframe,
                "NO_CLOSED_CANDLE_SIGNAL",
                (
                    f"{model_label} aguarda {context_timeframe} direcional, "
                    "EMA9/21 alinhadas, ADX14 > 20, pullback na faixa das "
                    f"medias e candle {timeframe} de confirmacao."
                ),
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                atr=reading.atr,
                diagnostics=diagnostics,
                **common,
            )
        else:
            decision = LabOperationalDecision(
                model_id=model_id,
                pair=pair,
                timeframe=timeframe,
                status="SIGNAL_FROZEN",
                ready=True,
                direction="BUY" if direction_value > 0 else "SELL",
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                atr=reading.atr,
                risk_reward=float(parameters.get("risk_reward", 2.0) or 2.0),
                diagnostics=diagnostics,
                **common,
            )
        self._decision_cache[cache_key] = decision
        self._trim_caches()
        return self._decision_with_live_entry(
            decision,
            current_price,
            current_time,
            server_timestamp=server_timestamp,
        )

    def _evaluate_standard(
        self,
        *,
        model_id: str,
        pair: str,
        timeframe: str,
        winner: dict[str, Any],
        candles_by_market: Mapping[tuple[str, str], Iterable[object]],
        current_price: float | None,
        server_timestamp: str | None,
        signal_builder: Callable[[object, dict[str, Any]], object],
        enrich: bool,
    ) -> LabOperationalDecision:
        candles = self._candles(candles_by_market, pair, timeframe)
        common = self._winner_values(winner)
        if len(candles) < OPERATIONAL_INDICATOR_RAW_CANDLES:
            return self._wait(
                model_id,
                pair,
                timeframe,
                "INSUFFICIENT_LIVE_CANDLES",
                (
                    "Modelo exige janela deslizante de 200 candles fechados; "
                    f"recebeu {max(len(candles) - 1, 0)}."
                ),
                **common,
            )
        signal_time = str(candles[-2]["data"])
        current_time = str(candles[-1]["data"])
        cache_key = (model_id, pair, timeframe, signal_time)
        cached = self._decision_cache.get(cache_key)
        if cached is not None:
            return self._decision_with_live_entry(
                cached,
                current_price,
                current_time,
                server_timestamp=server_timestamp,
            )
        parameters = dict(winner.get("parameters") or {})
        try:
            market = engineer_features(pair, candles[:-1])
            if enrich:
                market = enrich_market(market)
            signal = signal_builder(market, parameters)
            direction_value = int(signal[-1]) if len(signal) else 0
            atr = float(market.atr[-1]) if len(market.atr) else float("nan")
            diagnostics = self._feature_diagnostics(market.frame, parameters)
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            return self._wait(
                model_id,
                pair,
                timeframe,
                "FEATURE_EVALUATION_ERROR",
                f"Falha ao reproduzir indicadores do Lab: {exc}",
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                **common,
            )
        if direction_value == 0:
            decision = self._wait(
                model_id,
                pair,
                timeframe,
                "NO_CLOSED_CANDLE_SIGNAL",
                "Ultimo candle fechado ainda nao encaixou todos os indicadores.",
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                diagnostics=diagnostics,
                **common,
            )
        else:
            decision = LabOperationalDecision(
                model_id=model_id,
                pair=pair,
                timeframe=timeframe,
                status="SIGNAL_FROZEN",
                ready=True,
                direction="BUY" if direction_value > 0 else "SELL",
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                atr=atr,
                risk_reward=float(parameters.get("risk_reward", 0.0) or 0.0),
                diagnostics=diagnostics,
                **common,
            )
        self._decision_cache[cache_key] = decision
        self._trim_caches()
        return self._decision_with_live_entry(
            decision,
            current_price,
            current_time,
            server_timestamp=server_timestamp,
        )

    def _evaluate_m4(
        self,
        *,
        model_id: str,
        pair: str,
        winner: dict[str, Any],
        candles_by_market: Mapping[tuple[str, str], Iterable[object]],
        current_price: float | None,
        server_timestamp: str | None,
    ) -> LabOperationalDecision:
        common = self._winner_values(winner)
        primary_rows: dict[str, list[dict[str, Any]]] = {}
        h1_rows: dict[str, list[dict[str, Any]]] = {}
        h4_rows: dict[str, list[dict[str, Any]]] = {}
        for market_pair in sorted(self.results(MODEL_4_ID)):
            primary = self._candles(candles_by_market, market_pair, "M30")
            h1 = self._candles(candles_by_market, market_pair, "H1")
            h4 = self._candles(candles_by_market, market_pair, "H4")
            if min(len(primary), len(h1), len(h4)) < OPERATIONAL_INDICATOR_RAW_CANDLES:
                return self._wait(
                    model_id,
                    pair,
                    "M30",
                    "M4_CONTEXT_CACHE_INCOMPLETE",
                    (
                        f"Contexto M4 incompleto em {market_pair}: "
                        f"M30={len(primary)}, H1={len(h1)}, H4={len(h4)}."
                    ),
                    **common,
                )
            primary_rows[market_pair] = primary[:-1]
            h1_rows[market_pair] = h1[:-1]
            h4_rows[market_pair] = h4[:-1]
        signal_time = str(primary_rows[pair][-1]["data"])
        current_time = str(self._candles(candles_by_market, pair, "M30")[-1]["data"])
        cache_key = (model_id, pair, "M30", signal_time)
        cached = self._decision_cache.get(cache_key)
        if cached is not None:
            return self._decision_with_live_entry(
                cached,
                current_price,
                current_time,
                server_timestamp=server_timestamp,
            )
        market_key = tuple(
            (market_pair, str(rows[-1]["data"]))
            for market_pair, rows in sorted(primary_rows.items())
        )
        prepared = self._m4_market_cache.get(market_key)
        try:
            if prepared is None:
                primary_markets = {
                    market_pair: enrich_market(engineer_features(market_pair, rows))
                    for market_pair, rows in primary_rows.items()
                }
                h1_markets = {
                    market_pair: enrich_market(engineer_features(market_pair, rows))
                    for market_pair, rows in h1_rows.items()
                }
                h4_markets = {
                    market_pair: enrich_market(engineer_features(market_pair, rows))
                    for market_pair, rows in h4_rows.items()
                }
                prepared = {
                    "primary": primary_markets,
                    "contexts": build_contexts(primary_markets, h1_markets, h4_markets),
                }
                self._m4_market_cache[market_key] = prepared
            market = prepared["primary"][pair]
            parameters = dict(winner.get("parameters") or {})
            base = build_m3_signal(market, parameters)
            signal = apply_context_overlay(
                base,
                prepared["contexts"][pair],
                market.frame["atr_ratio"].to_numpy(dtype=float),
                dict(winner.get("context_overlay") or {}),
            )
            direction_value = int(signal[-1]) if len(signal) else 0
            atr = float(market.atr[-1]) if len(market.atr) else float("nan")
            diagnostics = self._feature_diagnostics(
                market.frame,
                parameters,
            ) + self._context_diagnostics(prepared["contexts"][pair])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            return self._wait(
                model_id,
                pair,
                "M30",
                "M4_CONTEXT_EVALUATION_ERROR",
                f"Falha ao reproduzir contexto M4: {exc}",
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                **common,
            )
        if direction_value == 0:
            decision = self._wait(
                model_id,
                pair,
                "M30",
                "NO_CLOSED_CANDLE_SIGNAL",
                "Candle M30 ou contexto H1/H4 ainda nao confirmou o M4.",
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                diagnostics=diagnostics,
                **common,
            )
        else:
            decision = LabOperationalDecision(
                model_id=model_id,
                pair=pair,
                timeframe="M30",
                status="SIGNAL_FROZEN",
                ready=True,
                direction="BUY" if direction_value > 0 else "SELL",
                signal_candle_time=signal_time,
                current_bar_time=current_time,
                atr=atr,
                risk_reward=float(
                    (winner.get("parameters") or {}).get("risk_reward", 0.0) or 0.0
                ),
                diagnostics=diagnostics,
                **common,
            )
        self._decision_cache[cache_key] = decision
        self._trim_caches()
        return self._decision_with_live_entry(
            decision,
            current_price,
            current_time,
            server_timestamp=server_timestamp,
        )

    def _decision_with_live_entry(
        self,
        frozen: LabOperationalDecision,
        current_price: float | None,
        current_bar_time: str,
        *,
        server_timestamp: str | None = None,
    ) -> LabOperationalDecision:
        if not frozen.ready:
            return frozen
        age_seconds = self._bar_age_seconds(
            current_bar_time,
            reference_timestamp=server_timestamp,
        )
        if age_seconds is None or age_seconds < -60.0:
            return self._replace_wait(
                frozen,
                "INVALID_CURRENT_BAR_TIME",
                "Horario do candle atual nao pode ser validado.",
                current_bar_time,
            )
        if age_seconds > float(self.max_entry_delay_seconds):
            return self._replace_wait(
                frozen,
                "STALE_SIGNAL_WINDOW",
                f"Janela de entrada expirou ({age_seconds:.0f}s).",
                current_bar_time,
            )
        entry = self._positive_float(current_price)
        atr = self._positive_float(frozen.atr)
        stop_factor = self._positive_float(frozen.parameters.get("stop_factor"))
        if entry is None or atr is None or stop_factor is None or frozen.risk_reward <= 0:
            return self._replace_wait(
                frozen,
                "ENTRY_OR_RISK_INPUT_UNAVAILABLE",
                "Preco, ATR, stop factor ou RR ausente.",
                current_bar_time,
            )
        distance = max(atr * stop_factor, abs(entry) * MINIMUM_DISTANCE_PERCENT)
        multiplier = 1.0 if frozen.direction == "BUY" else -1.0
        stop = entry - multiplier * distance
        target = entry + multiplier * distance * frozen.risk_reward
        return LabOperationalDecision(
            **{
                **frozen.__dict__,
                "status": "READY",
                "current_bar_time": current_bar_time,
                "entry_price": entry,
                "stop": stop,
                "target": target,
                "reason": (
                    f"{frozen.family} confirmou {frozen.direction}; entrada no "
                    "preco vivo seguinte com SL/TP fixos do Lab."
                ),
                "diagnostics": frozen.diagnostics
                + (
                    f"CURRENT_BAR_AGE_SECONDS={age_seconds:.1f}",
                    (
                        "ENTRY_CLOCK_SOURCE=MT5_SERVER"
                        if self._parse_datetime(server_timestamp) is not None
                        else "ENTRY_CLOCK_SOURCE=SYSTEM_UTC_FALLBACK"
                    ),
                    f"STOP_FACTOR={stop_factor:.4f}",
                    f"RISK_REWARD={frozen.risk_reward:.4f}",
                    f"FIXED_EXIT_POLICY={FIXED_EXIT_POLICY}",
                ),
            }
        )

    def _replace_wait(
        self,
        frozen: LabOperationalDecision,
        status: str,
        reason: str,
        current_bar_time: str,
    ) -> LabOperationalDecision:
        values = dict(frozen.__dict__)
        values.update(
            {
                "status": status,
                "ready": False,
                "current_bar_time": current_bar_time,
                "entry_price": None,
                "stop": None,
                "target": None,
                "reason": reason,
            }
        )
        return LabOperationalDecision(**values)

    def _official_features(
        self,
        pair: str,
        timeframe: str,
        closed_candles: list[dict[str, Any]],
    ) -> dict[str, Any]:
        signal_time = str(closed_candles[-1]["data"])
        cache_key = (pair.upper(), timeframe.upper(), signal_time)
        cached = self._official_feature_cache.get(cache_key)
        if cached is not None:
            return cached
        def values(name: str) -> np.ndarray:
            return np.asarray(
                [float(candle[name]) for candle in closed_candles],
                dtype=float,
            )

        def ewm_series(
            source: np.ndarray,
            *,
            alpha: float,
            min_periods: int,
        ) -> np.ndarray:
            output = np.full(source.shape, np.nan, dtype=float)
            state = math.nan
            observations = 0
            for index, raw_value in enumerate(source):
                value = float(raw_value)
                if not math.isfinite(value):
                    continue
                state = (
                    value
                    if not math.isfinite(state)
                    else alpha * value + (1.0 - alpha) * state
                )
                observations += 1
                if observations >= min_periods:
                    output[index] = state
            return output

        def ema(source: np.ndarray, period: int) -> np.ndarray:
            return ewm_series(
                source,
                alpha=2.0 / (float(period) + 1.0),
                min_periods=period,
            )

        def finite(value: float, default: float = 0.0) -> float:
            number = float(value)
            return number if math.isfinite(number) else default

        opens = values("abertura")
        highs = values("maxima")
        lows = values("minima")
        closes = values("fechamento")
        volumes = np.clip(values("volume"), 0.0, None)

        previous_close = np.roll(closes, 1)
        previous_close[0] = math.nan
        true_range = np.nanmax(
            np.vstack(
                (
                    np.abs(highs - lows),
                    np.abs(highs - previous_close),
                    np.abs(lows - previous_close),
                )
            ),
            axis=0,
        )
        atr14 = ewm_series(true_range, alpha=1.0 / 14.0, min_periods=14)

        delta = np.diff(closes, prepend=math.nan)
        gain = np.where(np.isfinite(delta), np.clip(delta, 0.0, None), math.nan)
        loss = np.where(np.isfinite(delta), np.clip(-delta, 0.0, None), math.nan)
        average_gain = ewm_series(gain, alpha=1.0 / 14.0, min_periods=14)
        average_loss = ewm_series(loss, alpha=1.0 / 14.0, min_periods=14)
        relative_strength = np.divide(
            average_gain,
            average_loss,
            out=np.full(average_gain.shape, np.nan),
            where=average_loss != 0.0,
        )
        rsi14 = 100.0 - (100.0 / (1.0 + relative_strength))

        upward = np.diff(highs, prepend=math.nan)
        downward = -np.diff(lows, prepend=math.nan)
        plus_dm = np.where((upward > downward) & (upward > 0.0), upward, 0.0)
        minus_dm = np.where((downward > upward) & (downward > 0.0), downward, 0.0)
        smoothed_range = ewm_series(true_range, alpha=1.0 / 14.0, min_periods=14)
        plus_smoothed = ewm_series(plus_dm, alpha=1.0 / 14.0, min_periods=14)
        minus_smoothed = ewm_series(minus_dm, alpha=1.0 / 14.0, min_periods=14)
        plus_di = np.divide(
            100.0 * plus_smoothed,
            smoothed_range,
            out=np.full(smoothed_range.shape, np.nan),
            where=smoothed_range != 0.0,
        )
        minus_di = np.divide(
            100.0 * minus_smoothed,
            smoothed_range,
            out=np.full(smoothed_range.shape, np.nan),
            where=smoothed_range != 0.0,
        )
        directional_sum = plus_di + minus_di
        dx = np.divide(
            100.0 * np.abs(plus_di - minus_di),
            directional_sum,
            out=np.full(directional_sum.shape, np.nan),
            where=directional_sum != 0.0,
        )
        adx14 = ewm_series(dx, alpha=1.0 / 14.0, min_periods=14)

        ema_values = {
            period: ema(closes, period)
            for period in (9, 20, 21, 40, 50, 100, 200)
        }
        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        macd = ema12 - ema26
        macd_signal = ewm_series(
            macd,
            alpha=2.0 / 10.0,
            min_periods=9,
        )

        returns = closes[1:] / closes[:-1] - 1.0
        volatility20 = float(np.std(returns[-20:], ddof=1))
        typical = (highs + lows + closes) / 3.0
        recent_volume = volumes[-20:]
        volume_sum = float(np.sum(recent_volume))
        vwap20 = (
            float(np.sum(typical[-20:] * recent_volume) / volume_sum)
            if volume_sum > 0.0
            else 0.0
        )
        recent_close = closes[-20:]
        deviation20 = float(np.std(recent_close, ddof=1))
        zscore20 = (
            float((closes[-1] - np.mean(recent_close)) / deviation20)
            if deviation20 > 0.0
            else 0.0
        )
        candle_range = max(float(highs[-1] - lows[-1]), 0.0)
        lower_wick = (
            float(min(opens[-1], closes[-1]) - lows[-1]) / candle_range
            if candle_range > 0.0
            else 0.0
        )
        upper_wick = (
            float(highs[-1] - max(opens[-1], closes[-1])) / candle_range
            if candle_range > 0.0
            else 0.0
        )

        features = {
            "time": signal_time,
            "open": finite(opens[-1]),
            "high": finite(highs[-1]),
            "low": finite(lows[-1]),
            "close": finite(closes[-1]),
            "atr": finite(atr14[-1]),
            "adx": finite(adx14[-1]),
            "rsi": finite(rsi14[-1], 50.0),
            "momentum": finite(closes[-1] / closes[-11] - 1.0),
            "volatility": abs(finite(volatility20)),
            "macd": finite(macd[-1]),
            "macd_signal": finite(macd_signal[-1]),
            "previous_macd_histogram": finite(
                macd[-2] - macd_signal[-2]
            ),
            "pivot": finite((highs[-2] + lows[-2] + closes[-2]) / 3.0),
            "vwap": finite(vwap20),
            "z_score": finite(zscore20),
            "support": finite(np.min(lows[-21:-1])),
            "resistance": finite(np.max(highs[-21:-1])),
            "donchian_high20": finite(np.max(highs[-21:-1])),
            "donchian_low20": finite(np.min(lows[-21:-1])),
            "donchian_high40": finite(np.max(highs[-41:-1])),
            "donchian_low40": finite(np.min(lows[-41:-1])),
            "tick_volume": finite(volumes[-1]),
            "tick_volume_average": finite(np.mean(volumes[-21:-1])),
            "lower_wick": lower_wick,
            "upper_wick": upper_wick,
        }
        for period in (9, 20, 21, 40, 50, 100, 200):
            features[f"ema{period}"] = finite(ema_values[period][-1])
        self._official_feature_cache[cache_key] = features
        self._trim_caches()
        return features

    def _official_alpha_direction(
        self,
        *,
        alpha_id: str,
        features: Mapping[str, Any],
        parameters: Mapping[str, Any],
        context_features: Mapping[str, Any] | None,
        market_row: object | None,
    ) -> tuple[str, str, tuple[str, ...]]:
        alpha = str(alpha_id or "").upper()
        close = float(features["close"])
        atr = float(features["atr"])
        momentum = float(features["momentum"])
        volatility = float(features["volatility"])
        fast_period = int(parameters.get("ema_curta", 20) or 20)
        slow_period = int(parameters.get("ema_longa", 50) or 50)
        fast = float(features.get(f"ema{fast_period}", 0.0) or 0.0)
        slow = float(features.get(f"ema{slow_period}", 0.0) or 0.0)
        direction = "WAIT"
        reason = "Ultimo candle fechado ainda nao confirmou todos os parametros."

        if alpha == "ALPHA001":
            threshold = float(parameters.get("momentum_threshold", 0.0) or 0.0)
            vol_min = float(parameters.get("volatility_threshold", 0.0) or 0.0)
            if fast > slow and momentum > threshold and volatility >= vol_min:
                direction = "BUY"
            elif fast < slow and momentum < -threshold and volatility >= vol_min:
                direction = "SELL"
            reason = "EMA, momentum e volatilidade confirmados no candle fechado."
        elif alpha == "ALPHA005":
            period = int(parameters.get("donchian_period", 20) or 20)
            high = float(features.get(f"donchian_high{period}", 0.0) or 0.0)
            low = float(features.get(f"donchian_low{period}", 0.0) or 0.0)
            buffer = float(parameters.get("breakout_buffer", 0.0) or 0.0)
            threshold = float(parameters.get("momentum_threshold", 0.0) or 0.0)
            if high > 0.0 and close >= high * (1.0 - buffer) and momentum > threshold:
                direction = "BUY"
            elif low > 0.0 and close <= low * (1.0 + buffer) and momentum < -threshold:
                direction = "SELL"
            reason = "Canal Donchian anterior e momentum avaliados no candle fechado."
        elif alpha == "ALPHA006":
            adx_min = float(parameters.get("adx_min", 25.0) or 25.0)
            if float(features["adx"]) >= adx_min and fast > slow and momentum > 0.0:
                direction = "BUY"
            elif float(features["adx"]) >= adx_min and fast < slow and momentum < 0.0:
                direction = "SELL"
            reason = "ADX, EMA e momentum avaliados no candle fechado."
        elif alpha == "ALPHA007":
            histogram = float(features["macd"]) - float(features["macd_signal"])
            previous_histogram = float(features["previous_macd_histogram"])
            if previous_histogram <= 0.0 < histogram and fast >= slow:
                direction = "BUY"
            elif previous_histogram >= 0.0 > histogram and fast <= slow:
                direction = "SELL"
            reason = "Virada do histograma MACD com EMA alinhada no candle fechado."
        elif alpha == "ALPHA011":
            pivot = float(features["pivot"])
            rsi = float(features["rsi"])
            near = pivot > 0.0 and abs(close - pivot) <= atr
            if near and close > pivot and float(features["lower_wick"]) >= 0.35 and rsi <= float(parameters.get("rsi_sobrecompra", 60.0)):
                direction = "BUY"
            elif near and close < pivot and float(features["upper_wick"]) >= 0.35 and rsi >= float(parameters.get("rsi_sobrevenda", 40.0)):
                direction = "SELL"
            reason = "Pivot, rejeicao do candle e RSI avaliados no candle fechado."
        elif alpha == "ALPHA012":
            vwap = float(features["vwap"])
            z_score = float(features["z_score"])
            rsi = float(features["rsi"])
            threshold = float(parameters.get("z_threshold", 1.0) or 1.0)
            if vwap > 0.0 and close < vwap and z_score <= -threshold and rsi <= float(parameters.get("rsi_sobrevenda", 30.0)):
                direction = "BUY"
            elif vwap > 0.0 and close > vwap and z_score >= threshold and rsi >= float(parameters.get("rsi_sobrecompra", 70.0)):
                direction = "SELL"
            reason = "VWAP, Z-Score e RSI avaliados no candle fechado."
        elif alpha == "ALPHA013":
            support = float(features["support"])
            resistance = float(features["resistance"])
            rsi = float(features["rsi"])
            if support > 0.0 and abs(close - support) <= atr and close > float(features["open"]) and rsi <= float(parameters.get("rsi_sobrecompra", 60.0)):
                direction = "BUY"
            elif resistance > 0.0 and abs(close - resistance) <= atr and close < float(features["open"]) and rsi >= float(parameters.get("rsi_sobrevenda", 40.0)):
                direction = "SELL"
            reason = "Suporte/resistencia, candle de reacao e RSI avaliados."
        elif alpha == "ALPHA014":
            context = dict(context_features or {})
            context_fast = float(context.get(f"ema{fast_period}", 0.0) or 0.0)
            context_slow = float(context.get(f"ema{slow_period}", 0.0) or 0.0)
            context_momentum = float(context.get("momentum", 0.0) or 0.0)
            if fast > slow and momentum > 0.0 and context_fast > context_slow and context_momentum > 0.0:
                direction = "BUY"
            elif fast < slow and momentum < 0.0 and context_fast < context_slow and context_momentum < 0.0:
                direction = "SELL"
            reason = "EMA e momentum alinhados no timeframe de entrada e no contexto."
        elif alpha in {"ALPHA015", "ALPHA015_M19_MIRROR"}:
            spread = self._market_row_float(market_row, "spread")
            spread_average = self._market_row_float(market_row, "spread_average")
            volume = float(features["tick_volume"])
            volume_average = float(features["tick_volume_average"])
            volume_factor = float(parameters.get("volume_factor", 1.0) or 1.0)
            liquid = (
                spread is not None
                and spread_average is not None
                and spread <= spread_average
                and volume_average > 0.0
                and volume >= volume_average * volume_factor
            )
            if liquid and fast > slow and momentum > 0.0:
                direction = "BUY"
            elif liquid and fast < slow and momentum < 0.0:
                direction = "SELL"
            if alpha == "ALPHA015_M19_MIRROR":
                direction = (
                    "SELL" if direction == "BUY" else "BUY" if direction == "SELL" else "WAIT"
                )
                reason = (
                    "M21 espelhou a direcao M19 apos o mesmo gate ALPHA015 de "
                    "liquidez/spread, EMA e momentum."
                )
            else:
                reason = "ALPHA015 liberou liquidez/spread; EMA e momentum carregam a direcao."
        elif alpha == "ALPHA016":
            reversal = float(parameters.get("reversal_strength", 0.0006) or 0.0006)
            vol_min = float(parameters.get("volatility_threshold", 0.0001) or 0.0001)
            if fast < slow and momentum > reversal and volatility >= vol_min:
                direction = "BUY"
            elif fast > slow and momentum < -reversal and volatility >= vol_min:
                direction = "SELL"
            reason = "Fluxo anterior e reversao de momentum/volatilidade avaliados."

        diagnostics = (
            f"ALPHA={alpha}",
            f"CLOSE={close:.8f}",
            f"EMA{fast_period}={fast:.8f}",
            f"EMA{slow_period}={slow:.8f}",
            f"MOMENTUM10={momentum:.8f}",
            f"VOLATILITY20={volatility:.8f}",
            f"RSI14={float(features['rsi']):.4f}",
            f"ADX14={float(features['adx']):.4f}",
            f"ATR14={atr:.8f}",
            f"DECISION={direction}",
        )
        if alpha == "ALPHA005":
            period = int(parameters.get("donchian_period", 20) or 20)
            diagnostics += (
                f"DONCHIAN_HIGH={float(features.get(f'donchian_high{period}', 0.0)):.8f}",
                f"DONCHIAN_LOW={float(features.get(f'donchian_low{period}', 0.0)):.8f}",
            )
        elif alpha == "ALPHA007":
            diagnostics += (
                f"MACD={float(features['macd']):.8f}",
                f"MACD_SIGNAL={float(features['macd_signal']):.8f}",
            )
        elif alpha == "ALPHA011":
            diagnostics += (
                f"PIVOT={float(features['pivot']):.8f}",
                f"LOWER_WICK={float(features['lower_wick']):.4f}",
                f"UPPER_WICK={float(features['upper_wick']):.4f}",
            )
        elif alpha == "ALPHA012":
            diagnostics += (
                f"VWAP={float(features['vwap']):.8f}",
                f"Z_SCORE={float(features['z_score']):.4f}",
            )
        elif alpha == "ALPHA013":
            diagnostics += (
                f"SUPPORT={float(features['support']):.8f}",
                f"RESISTANCE={float(features['resistance']):.8f}",
            )
        elif alpha == "ALPHA014" and context_features is not None:
            diagnostics += (
                f"CONTEXT_EMA{fast_period}={float(context_features.get(f'ema{fast_period}', 0.0)):.8f}",
                f"CONTEXT_EMA{slow_period}={float(context_features.get(f'ema{slow_period}', 0.0)):.8f}",
                f"CONTEXT_MOMENTUM10={float(context_features.get('momentum', 0.0)):.8f}",
            )
        elif alpha in {"ALPHA015", "ALPHA015_M19_MIRROR"}:
            diagnostics += (
                f"SPREAD={float(spread or 0.0):.8f}",
                f"SPREAD_AVERAGE={float(spread_average or 0.0):.8f}",
                f"TICK_VOLUME={float(features['tick_volume']):.2f}",
                f"TICK_VOLUME_AVERAGE={float(features['tick_volume_average']):.2f}",
            )
            if alpha == "ALPHA015_M19_MIRROR":
                diagnostics += (
                    "MIRROR_SOURCE_MODEL=M19",
                    "MIRROR_DIRECTION=INVERTED",
                    "MIRROR_LEVELS=SL_M21_TP_M19__TP_M21_SL_M19",
                )
        if direction == "WAIT":
            reason = f"AGUARDA: {reason}"
        return direction, reason, diagnostics

    def _market_row_float(self, market_row: object | None, name: str) -> float | None:
        try:
            value = float(getattr(market_row, name))
        except (AttributeError, TypeError, ValueError):
            return None
        return value if math.isfinite(value) and value >= 0.0 else None

    def _winner_values(self, winner: dict[str, Any]) -> dict[str, Any]:
        parameters = dict(winner.get("parameters") or {})
        return {
            "alpha_id": str(winner.get("alpha_id") or "N/D"),
            "family": str(parameters.get("family") or "N/D"),
            "source_model": str(winner.get("source_model") or "N/D"),
            "parameters": parameters,
            "context_overlay": dict(winner.get("context_overlay") or {}),
            "parity_status": str(winner.get("parity_status") or "N/D"),
        }

    def _wait(
        self,
        model_id: str,
        pair: str,
        timeframe: str,
        status: str,
        reason: str,
        **values: Any,
    ) -> LabOperationalDecision:
        return LabOperationalDecision(
            model_id=model_id,
            pair=pair,
            timeframe=timeframe or "N/D",
            status=status,
            ready=False,
            reason=reason,
            **values,
        )

    def _candles(
        self,
        source: Mapping[tuple[str, str], Iterable[object]],
        pair: str,
        timeframe: str,
    ) -> list[dict[str, Any]]:
        normalized_pair = pair.upper()
        normalized_timeframe = timeframe.upper()
        raw_values = list(
            source.get((normalized_pair, normalized_timeframe), []) or []
        )
        deduplicated = {
            str(self._raw_candle_value(candle, "data")): candle
            for candle in raw_values
            if str(self._raw_candle_value(candle, "data"))
        }
        values = [deduplicated[key] for key in sorted(deduplicated)][
            -OPERATIONAL_INDICATOR_RAW_CANDLES:
        ]
        if not values:
            return []
        signal = values[-2] if len(values) >= 2 else values[-1]
        current = values[-1]
        signal_fingerprint = tuple(
            self._raw_candle_value(signal, name)
            for name in (
                "data",
                "abertura",
                "maxima",
                "minima",
                "fechamento",
                "volume",
            )
        )
        cache_key = (
            normalized_pair,
            normalized_timeframe,
            len(values),
            signal_fingerprint,
            self._raw_candle_value(current, "data"),
        )
        cached = self._candle_rows_cache.get(cache_key)
        if cached is not None:
            return cached
        rows = [self._candle_dict(candle) for candle in values]
        normalized = [row for row in rows if row is not None]
        self._candle_rows_cache[cache_key] = normalized
        self._trim_caches()
        return normalized

    def _raw_candle_value(self, candle: object, name: str) -> object:
        aliases = {
            "data": ("data", "timestamp"),
            "abertura": ("abertura", "open"),
            "maxima": ("maxima", "high"),
            "minima": ("minima", "low"),
            "fechamento": ("fechamento", "close"),
            "volume": ("volume",),
        }
        candidates = aliases.get(name, (name,))
        if isinstance(candle, dict):
            for candidate in candidates:
                if candle.get(candidate) is not None:
                    return candle[candidate]
            return None
        for candidate in candidates:
            value = getattr(candle, candidate, None)
            if value is not None:
                return value
        return None

    def _candle_dict(self, candle: object) -> dict[str, Any] | None:
        data = {
            name: self._raw_candle_value(candle, name)
            for name in (
                "data",
                "abertura",
                "maxima",
                "minima",
                "fechamento",
                "volume",
            )
        }
        required = ("data", "abertura", "maxima", "minima", "fechamento")
        if any(data.get(name) is None for name in required):
            return None
        return {
            "data": str(data["data"]),
            "abertura": float(data["abertura"]),
            "maxima": float(data["maxima"]),
            "minima": float(data["minima"]),
            "fechamento": float(data["fechamento"]),
            "volume": int(data.get("volume", 0) or 0),
        }

    def _feature_diagnostics(
        self,
        frame: object,
        parameters: Mapping[str, Any] | None = None,
    ) -> tuple[str, ...]:
        if len(frame.index) == 0:
            return ()
        row = frame.iloc[-1]
        configured = dict(parameters or {})
        names = [
            "open",
            "high",
            "low",
            "close",
            "adx",
            "adx_delta",
            "atr14",
            "atr_ratio",
            "rsi",
            "rsi7",
            "rsi14",
            "rsi21",
            "volume_ratio",
            "momentum_3",
            "momentum_5",
            "macd_hist_atr",
            "macd_hist_delta",
            "bb_width_ratio",
            "body_atr",
            "range_atr",
            "close_position",
            "upper_wick",
            "lower_wick",
            "hour_utc",
            "weekday",
        ]
        for period_key in ("fast", "slow"):
            period = configured.get(period_key)
            if period is not None:
                names.extend((f"ema{period}", f"ema{period}_slope_atr"))
        for key, prefix in (
            ("efficiency_period", "efficiency_"),
            ("rsi_period", "rsi"),
            ("roc_period", "roc_"),
        ):
            period = configured.get(key)
            if period is not None:
                names.append(f"{prefix}{period}")
        momentum_name = configured.get("momentum")
        if momentum_name:
            names.append(str(momentum_name))
        lookback = configured.get("lookback")
        if lookback is not None:
            names.extend((f"prior_high_{lookback}", f"prior_low_{lookback}"))
        names.extend(("zscore20", "bb_width_atr"))
        values: list[str] = []
        for name in dict.fromkeys(names):
            if name not in frame:
                continue
            try:
                number = float(row.get(name))
            except (TypeError, ValueError):
                continue
            if math.isfinite(number):
                values.append(f"{name.upper()}={number:.6f}")
        if len(frame.index) > 1:
            previous_row = frame.iloc[-2]
            for name in ("atr_ratio", "bb_width_ratio"):
                if name not in frame:
                    continue
                try:
                    number = float(previous_row.get(name))
                except (TypeError, ValueError):
                    continue
                if math.isfinite(number):
                    values.append(f"{name.upper()}_PREVIOUS={number:.6f}")
        return tuple(values)

    def _context_diagnostics(self, context: object) -> tuple[str, ...]:
        values: list[str] = []
        for name in (
            "h1_trend",
            "h1_adx",
            "h4_trend",
            "h4_adx",
            "strength_fast",
            "strength_slow",
            "volatility_low",
            "volatility_high",
        ):
            series = getattr(context, name, None)
            if series is None or len(series) == 0:
                continue
            try:
                number = float(series[-1])
            except (TypeError, ValueError):
                continue
            if math.isfinite(number):
                values.append(f"{name.upper()}={number:.6f}")
        return tuple(values)

    def _load_manifest(self) -> dict[str, Any]:
        try:
            mtime_ns = self.manifest_path.stat().st_mtime_ns
        except OSError:
            return {}
        if self._manifest_cache and mtime_ns == self._manifest_mtime_ns:
            return self._manifest_cache
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        self._manifest_cache = payload if isinstance(payload, dict) else {}
        self._manifest_mtime_ns = mtime_ns
        self._decision_cache.clear()
        self._m4_market_cache.clear()
        self._candle_rows_cache.clear()
        self._official_feature_cache.clear()
        self._trend_pullback_reading_cache.clear()
        return self._manifest_cache

    def _bar_age_seconds(
        self,
        value: str,
        *,
        reference_timestamp: str | None = None,
    ) -> float | None:
        parsed = self._parse_datetime(value)
        if parsed is None:
            return None
        now = self._parse_datetime(reference_timestamp)
        if now is None:
            now = self.now_provider()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return (now.astimezone(timezone.utc) - parsed).total_seconds()

    def _parse_datetime(self, value: object) -> datetime | None:
        text = str(value or "").strip()
        if not text or text.upper() in {"N/D", "NONE"}:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _positive_float(self, value: object) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) and number > 0.0 else None

    def _trim_caches(self) -> None:
        while len(self._decision_cache) > 256:
            self._decision_cache.pop(next(iter(self._decision_cache)))
        while len(self._m4_market_cache) > 2:
            self._m4_market_cache.pop(next(iter(self._m4_market_cache)))
        while len(self._candle_rows_cache) > 128:
            self._candle_rows_cache.pop(next(iter(self._candle_rows_cache)))
        while len(self._official_feature_cache) > 128:
            self._official_feature_cache.pop(next(iter(self._official_feature_cache)))
        while len(self._trend_pullback_reading_cache) > 128:
            self._trend_pullback_reading_cache.pop(
                next(iter(self._trend_pullback_reading_cache))
            )
