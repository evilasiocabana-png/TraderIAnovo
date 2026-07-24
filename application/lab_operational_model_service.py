"""Light runtime adapters for the researched Lab models M2 through M5."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from research.alpha_suggested.alpha_suggested_1_plus_discovery import (
    build_signal as build_m2_signal,
    engineer_features,
)
from research.alpha_suggested.alpha_suggested_2_plus_individual import (
    build_signal as build_m3_signal,
    enrich_market,
)
from research.alpha_suggested.model4_contextual_frontier import (
    apply_context_overlay,
    build_contexts,
)


MODEL_2_ID = "MODELO_2_LAB_ALPHA_SUGERIDA_1_PLUS"
MODEL_3_ID = "MODELO_3_LAB_ALPHA_SUGERIDA_2_PLUS"
MODEL_4_ID = "MODELO_4_LAB_CONTEXTUAL_MTF"
MODEL_5_ID = "MODELO_5_LAB_CONSOLIDADO"
MODEL_IDS = {
    "M2": MODEL_2_ID,
    "M3": MODEL_3_ID,
    "M4": MODEL_4_ID,
    "M5": MODEL_5_ID,
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

    def model_label(self, model_id: str) -> str:
        return MODEL_LABELS.get(str(model_id or "").upper(), "N/D")

    def results(self, model_id: str) -> dict[str, dict[str, Any]]:
        label = self.model_label(model_id)
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
                required.setdefault(pair, set()).add(
                    str(row.get("timeframe") or "M1").upper()
                )
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
        if not bool(winner.get("demo_forward_enabled", False)):
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
        if label == "M5" and source_model == "M1":
            return self._wait(
                normalized_model,
                normalized_pair,
                timeframe,
                "DELEGATE_TO_LAB_M1",
                "M5 usa o Trade Plan M1 vigente quando Alpha e TF coincidem.",
                **common,
            )
        if label == "M2":
            return self._evaluate_standard(
                model_id=normalized_model,
                pair=normalized_pair,
                timeframe=timeframe,
                winner=winner,
                candles_by_market=candles_by_market,
                current_price=current_price,
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
            )
        return self._wait(
            normalized_model,
            normalized_pair,
            timeframe,
            "UNSUPPORTED_LAB_RUNTIME_ADAPTER",
            f"Adaptador runtime ausente para {label}/{source_model}.",
            **common,
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
        signal_builder: Callable[[object, dict[str, Any]], object],
        enrich: bool,
    ) -> LabOperationalDecision:
        candles = self._candles(candles_by_market, pair, timeframe)
        common = self._winner_values(winner)
        if len(candles) < 260:
            return self._wait(
                model_id,
                pair,
                timeframe,
                "INSUFFICIENT_LIVE_CANDLES",
                f"Modelo exige 260 candles; recebeu {len(candles)}.",
                **common,
            )
        signal_time = str(candles[-2]["data"])
        current_time = str(candles[-1]["data"])
        cache_key = (model_id, pair, timeframe, signal_time)
        cached = self._decision_cache.get(cache_key)
        if cached is not None:
            return self._decision_with_live_entry(cached, current_price, current_time)
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
        return self._decision_with_live_entry(decision, current_price, current_time)

    def _evaluate_m4(
        self,
        *,
        model_id: str,
        pair: str,
        winner: dict[str, Any],
        candles_by_market: Mapping[tuple[str, str], Iterable[object]],
        current_price: float | None,
    ) -> LabOperationalDecision:
        common = self._winner_values(winner)
        primary_rows: dict[str, list[dict[str, Any]]] = {}
        h1_rows: dict[str, list[dict[str, Any]]] = {}
        h4_rows: dict[str, list[dict[str, Any]]] = {}
        for market_pair in sorted(self.results(MODEL_4_ID)):
            primary = self._candles(candles_by_market, market_pair, "M30")
            h1 = self._candles(candles_by_market, market_pair, "H1")
            h4 = self._candles(candles_by_market, market_pair, "H4")
            if min(len(primary), len(h1), len(h4)) < 260:
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
            return self._decision_with_live_entry(cached, current_price, current_time)
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
        return self._decision_with_live_entry(decision, current_price, current_time)

    def _decision_with_live_entry(
        self,
        frozen: LabOperationalDecision,
        current_price: float | None,
        current_bar_time: str,
    ) -> LabOperationalDecision:
        if not frozen.ready:
            return frozen
        age_seconds = self._bar_age_seconds(current_bar_time)
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
        values = list(source.get((normalized_pair, normalized_timeframe), []) or [])
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
        if isinstance(candle, dict):
            return candle.get(name)
        return getattr(candle, name, None)

    def _candle_dict(self, candle: object) -> dict[str, Any] | None:
        data = (
            dict(candle)
            if isinstance(candle, dict)
            else {
                "data": getattr(candle, "data", None),
                "abertura": getattr(candle, "abertura", None),
                "maxima": getattr(candle, "maxima", None),
                "minima": getattr(candle, "minima", None),
                "fechamento": getattr(candle, "fechamento", None),
                "volume": getattr(candle, "volume", None),
            }
        )
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
        return self._manifest_cache

    def _bar_age_seconds(self, value: str) -> float | None:
        parsed = self._parse_datetime(value)
        if parsed is None:
            return None
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
