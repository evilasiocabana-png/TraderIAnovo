"""Exportador read-only de sinais visuais TraderIA para o MT5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
from typing import Any

from application.dashboard_view_model import (
    DashboardMT5ForexSignalRowViewModel,
    DashboardMT5ForexSignalViewModel,
)


@dataclass(frozen=True)
class MT5VisualSignalExportResult:
    """Resultado da exportacao visual para indicador MT5."""

    output_path: Path
    total_signals: int
    generated_at: str


class MT5VisualSignalExporter:
    """Converte sinais prontos do DashboardService em JSON visual para MT5."""

    MAX_HISTORY_SIGNALS = 0

    def export(
        self,
        forex: DashboardMT5ForexSignalViewModel,
        output_path: Path,
        extra_history: list[dict[str, Any]] | None = None,
    ) -> MT5VisualSignalExportResult:
        payload = self.build_payload(
            forex,
            previous_history=extra_history or [],
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_payload_atomically(output_path, payload)
        return MT5VisualSignalExportResult(
            output_path=output_path,
            total_signals=len(payload["signals"]),
            generated_at=str(payload["generated_at"]),
        )

    def clear(self, output_path: Path) -> MT5VisualSignalExportResult:
        """Limpa sinais visuais para o indicador MT5 parar de desenhar textos."""
        generated_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "schema_version": "traderia.mt5.visual_signals.v1",
            "generated_at": generated_at,
            "source": "TraderIA",
            "mode": "VISUAL_DISABLED",
            "read_only": True,
            "order_execution": "NOT_ALLOWED_BY_INDICATOR",
            "timeframe": "N/D",
            "signals": [],
            "signal_history": [],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_payload_atomically(output_path, payload)
        return MT5VisualSignalExportResult(
            output_path=output_path,
            total_signals=0,
            generated_at=generated_at,
        )

    def build_payload(
        self,
        forex: DashboardMT5ForexSignalViewModel,
        *,
        previous_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        generated_at = datetime.now(timezone.utc).isoformat()
        open_positions = self._open_positions_by_symbol()
        signals = [self._row_to_signal(row, open_positions) for row in forex.pairs]
        current_symbols = {
            str(signal.get("symbol", "")).upper()
            for signal in signals
            if signal.get("symbol")
        }
        allowed_previous_history = self._filter_history_by_symbols(
            previous_history or [],
            current_symbols,
        )
        signal_history = self._merge_history(allowed_previous_history, signals)
        return {
            "schema_version": "traderia.mt5.visual_signals.v1",
            "generated_at": generated_at,
            "source": "TraderIA",
            "mode": "VISUAL_ONLY",
            "read_only": True,
            "execution_allowed": False,
            "order_execution": "NOT_ALLOWED_BY_INDICATOR",
            "timeframe": forex.timeframe,
            "signals": signals,
            "signal_history": [],
        }

    def _row_to_signal(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
        open_positions: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        operational_timeframe = self._operational_timeframe(row)
        position = (open_positions or {}).get(self._symbol_key(row.pair))
        is_positioned = position is not None
        decision = str(position["side"]) if is_positioned else row.decision
        entry = (
            float(position["entry"])
            if is_positioned and position.get("entry") is not None
            else (
                row.research_plan_entry_price
                if row.research_plan_entry_price is not None
                else row.theoretical_entry_price
            )
        )
        stop = (
            float(position["stop"])
            if is_positioned and position.get("stop") is not None
            else row.research_plan_stop
        )
        target = (
            float(position["target"])
            if is_positioned and position.get("target") is not None
            else row.research_plan_target
        )
        return {
            "symbol": row.pair,
            "timeframe": operational_timeframe,
            "mt5_source_timeframe": row.timeframe,
            "timestamp": (
                position.get("opened_at")
                if is_positioned and position.get("opened_at")
                else (
                    row.theoretical_entry_candle
                    if row.theoretical_entry_candle != "N/D"
                    else row.last_candle_time
                )
            ),
            "is_positioned": is_positioned,
            "position_open_time": position.get("opened_at") if is_positioned else None,
            "last_candle_time": row.last_candle_time,
            "decision": decision,
            "entry": entry,
            "stop": stop,
            "target": target,
            "rr": row.research_plan_risk_reward,
            "risk_pips": row.research_plan_risk_pips,
            "reward_pips": row.research_plan_reward_pips,
            "risk_percent": row.research_plan_risk_percent,
            "reward_percent": row.research_plan_reward_percent,
            "stop_reason": row.research_plan_stop_reason,
            "target_reason": row.research_plan_target_reason,
            "stop_management": row.research_plan_stop_management,
            "stop_management_parameters": row.research_plan_stop_management_parameters,
            "stop_management_reason": row.research_plan_stop_management_reason,
            "dynamic_exit_policy": row.dynamic_exit_policy,
            "dynamic_exit_action": row.dynamic_exit_action,
            "dynamic_exit_reason": row.dynamic_exit_reason,
            "dynamic_exit_confidence": row.dynamic_exit_confidence,
            "dynamic_exit_market_state": (
                self._dynamic_exit_market_state(row, is_positioned=is_positioned)
            ),
            "dynamic_exit_r_multiple": row.dynamic_exit_r_multiple,
            "dynamic_exit_candidate_stop": row.dynamic_exit_candidate_stop,
            "dynamic_exit_allowed_to_execute_demo": False,
            "dynamic_exit_source": row.dynamic_exit_source,
            "operational_plan_text": "",
            "model": row.active_model,
            "score": row.active_model_score,
            "confidence": row.confidence,
            "lab_alpha_id": row.lab_alpha_id,
            "lab_timeframe": row.lab_timeframe,
            "lab_configuration_source": row.lab_configuration_source,
            "lab_configuration": self._lab_configuration(row),
            "market_indicators": self._market_indicators(row),
            "active_indicators": list(row.active_model_indicators),
            "plan_status": row.research_plan_status,
            "reason": row.research_plan_reason or row.reason,
            "reason_codes": self._reason_codes(row),
            "theoretical_entry_status": row.theoretical_entry_status,
            "theoretical_entry_direction": row.theoretical_entry_direction,
            "trigger_candle": row.theoretical_entry_candle,
            "exit_model": row.research_plan_exit_model,
            "robot_status": self._robot_status(row, is_positioned=is_positioned),
            "position_ticket": position.get("ticket") if is_positioned else None,
            "position_volume": position.get("volume") if is_positioned else None,
            "visual_only": True,
        }

    def _operational_plan_text(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
    ) -> str:
        atr_stop_factor = self._text_or_na(
            row.lab_parameters.get("atr_stop_factor")
            or row.research_plan_stop_multiplier
        )
        risk_reward = self._text_or_na(row.research_plan_risk_reward)
        trigger_candle = self._text_or_na(row.theoretical_entry_candle)
        stop_management = self._text_or_na(row.research_plan_stop_management)
        management_parameters = self._management_parameters_text(
            row.research_plan_stop_management_parameters
        )
        return "\n".join(
            (
                self._text_or_na(row.lab_alpha_id),
                "",
                "Entrada",
                "--------",
                "Modelo:",
                self._text_or_na(row.active_model),
                "",
                "Gatilho:",
                trigger_candle,
                "",
                "Stop Inicial:",
                f"{atr_stop_factor} ATR",
                "",
                "Saida:",
                f"RR {risk_reward}",
                "",
                "Gestao:",
                stop_management,
                "",
                "Parametros:",
                management_parameters,
                "",
                "Confidence:",
                self._percent_text(row.confidence),
                "",
                "Score:",
                self._score_text(row.active_model_score),
                "",
                "Reason:",
                self._text_or_na(row.research_plan_reason or row.reason),
            )
        )

    def _text_or_na(self, value: object) -> str:
        text = str(value or "").strip()
        if not text or text == "N/D" or text.lower() == "none":
            return "N/A"
        return text.replace('"', "'")

    def _percent_text(self, value: object) -> str:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return "N/A"
        if parsed <= 1.0:
            parsed *= 100.0
        return f"{parsed:.0f}%"

    def _score_text(self, value: object) -> str:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return "N/A"
        return f"{parsed:.0f}"

    def _management_parameters_text(self, parameters: dict[str, str]) -> str:
        if not parameters:
            return "N/A"
        return " | ".join(
            f"{self._text_or_na(key)}={self._text_or_na(value)}"
            for key, value in parameters.items()
        )

    def _operational_timeframe(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
    ) -> str:
        lab_timeframe = str(row.lab_timeframe or "").strip().upper()
        if row.lab_configuration_source == "RESEARCH_LAB" and lab_timeframe:
            return lab_timeframe
        source_timeframe = str(row.timeframe or "").strip().upper()
        return source_timeframe or "M1"

    def _lab_configuration(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
    ) -> dict[str, Any]:
        return {
            "alpha": row.lab_alpha_id,
            "model": row.active_model,
            "timeframe": row.lab_timeframe,
            "source": row.lab_configuration_source,
            "parameters": dict(row.lab_parameters),
        }

    def _market_indicators(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
    ) -> dict[str, Any]:
        return {
            "trend": row.trend,
            "momentum": row.momentum,
            "volatility": row.volatility,
            "rsi": row.rsi,
            "short_average": row.short_average,
            "long_average": row.long_average,
            "mid_average": row.mid_average,
            "ema_fast": row.ema_fast,
            "ema_mid": row.ema_mid,
            "ema_slow": row.ema_slow,
            "adx": row.adx,
            "macd": row.macd,
            "macd_signal": row.macd_signal,
            "atr": row.atr,
            "atr_average": row.atr_average,
            "bollinger_upper": row.bollinger_upper,
            "bollinger_lower": row.bollinger_lower,
            "tick_volume": row.tick_volume,
            "tick_volume_average": row.tick_volume_average,
            "day_high": row.day_high,
            "day_low": row.day_low,
            "volatility_bucket": row.volatility_bucket,
            "rsi_bucket": row.rsi_bucket,
            "momentum_sign": row.momentum_sign,
            "ma_distance_bucket": row.ma_distance_bucket,
        }

    def _load_previous_history(self, output_path: Path) -> list[dict[str, Any]]:
        if not output_path.exists():
            return []
        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        history = payload.get("signal_history", [])
        if isinstance(history, list):
            return [
                item
                for item in history
                if isinstance(item, dict) and item.get("visual_only") is True
            ]
        return []

    def _merge_history(
        self,
        previous_history: list[dict[str, Any]],
        current_signals: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if self.MAX_HISTORY_SIGNALS <= 0:
            return []
        merged: dict[tuple[Any, ...], dict[str, Any]] = {}
        for signal in [*previous_history, *current_signals]:
            key = (
                signal.get("symbol"),
                signal.get("timeframe"),
                signal.get("timestamp"),
                signal.get("decision"),
                signal.get("entry"),
                signal.get("stop"),
                signal.get("target"),
            )
            merged[key] = signal
        return list(merged.values())[-self.MAX_HISTORY_SIGNALS :]

    def _filter_history_by_symbols(
        self,
        previous_history: list[dict[str, Any]],
        current_symbols: set[str],
    ) -> list[dict[str, Any]]:
        if not current_symbols:
            return []
        return [
            signal
            for signal in previous_history
            if str(signal.get("symbol", "")).upper() in current_symbols
        ]

    def _write_payload_atomically(
        self,
        output_path: Path,
        payload: dict[str, Any],
    ) -> None:
        content = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"
        tmp_path = output_path.with_name(f"{output_path.name}.tmp")
        tmp_path.write_text(content, encoding="utf-8")
        try:
            tmp_path.replace(output_path)
        except PermissionError:
            output_path.write_text(content, encoding="utf-8")
            try:
                tmp_path.unlink()
            except OSError:
                pass

    def _reason_codes(self, row: DashboardMT5ForexSignalRowViewModel) -> list[str]:
        codes: list[str] = []
        codes.extend(str(item) for item in row.active_model_indicators if item)
        codes.extend(str(item) for item in row.research_plan_diagnostics if item)
        codes.extend(str(item) for item in row.confidence_drivers if item)
        codes.extend(str(item) for item in row.confidence_penalties if item)

        reason = row.research_plan_reason or row.reason
        if reason and reason != "N/D":
            codes.append(reason)

        return codes[:12]

    def _robot_status(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
        *,
        is_positioned: bool = False,
    ) -> str:
        if is_positioned:
            return "POSICAO_ABERTA_MT5"
        if row.research_plan_status == "PLANO_VALIDO":
            return "PLANO_VALIDADO"
        if row.theoretical_entry_status == "SINAL_TEORICO":
            return "AGUARDANDO_PLANO"
        if row.decision in {"BUY", "SELL"}:
            return "MONITORANDO_GATILHO"
        return "AGUARDANDO_GATILHO"

    def _dynamic_exit_market_state(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
        *,
        is_positioned: bool,
    ) -> str:
        if not is_positioned:
            return "NO_POSITION"
        market_state = str(row.dynamic_exit_market_state or "").strip().upper()
        if market_state and market_state != "NO_POSITION":
            return market_state
        return "NEW_POSITION"

    def _open_positions_by_symbol(self) -> dict[str, dict[str, Any]]:
        try:
            mt5 = importlib.import_module("MetaTrader5")
        except Exception:
            return {}

        initialize = getattr(mt5, "initialize", None)
        try:
            if callable(initialize) and not bool(initialize()):
                return {}
        except Exception:
            return {}

        positions_get = getattr(mt5, "positions_get", None)
        if not callable(positions_get):
            return {}

        positions: dict[str, dict[str, Any]] = {}
        try:
            open_positions = positions_get() or []
        except Exception:
            return {}

        for position in open_positions:
            data = position._asdict() if hasattr(position, "_asdict") else {}
            symbol = str(data.get("symbol", "")).upper()
            if not symbol:
                continue
            position_type = int(data.get("type", -1))
            side = "BUY" if position_type == 0 else "SELL" if position_type == 1 else ""
            if side == "":
                continue
            positions[self._symbol_key(symbol)] = {
                "symbol": symbol,
                "side": side,
                "entry": self._positive_or_none(data.get("price_open")),
                "stop": self._positive_or_none(data.get("sl")),
                "target": self._positive_or_none(data.get("tp")),
                "volume": self._positive_or_none(data.get("volume")),
                "ticket": data.get("ticket"),
                "opened_at": self._position_time_iso(data.get("time")),
            }
        return positions

    def _symbol_key(self, symbol: str) -> str:
        return str(symbol).replace("/", "").replace(" ", "").upper()

    def _positive_or_none(self, value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number <= 0.0:
            return None
        return number

    def _position_time_iso(self, value: Any) -> str | None:
        try:
            timestamp = int(value)
        except (TypeError, ValueError):
            return None
        if timestamp <= 0:
            return None
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
