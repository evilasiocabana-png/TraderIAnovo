"""Modelo 26: continuidade e lateralizacao por sequencias de candles M5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from collections.abc import Mapping
from typing import Any, Iterable
from uuid import uuid4


# O ID legado preserva selecao, historico e comentarios MT5.
MODEL_26_ID = "MODELO_26_XAU_M5_SMART_MONEY"
MODEL_26_ALPHA_ID = "ALPHA026_CANDLE_CONTINUATION_RANGE"
MODEL_26_ALPHA_VERSION = "M26_ENTRY_V22"
MODEL_26_BETA_ID = "BETA026_CANDLE_CONTINUATION_RANGE_EXIT"
MODEL_26_BETA_VERSION = "M26_EXIT_V22"
MODEL_26_SOURCE = "MODEL_26_CANDLE_SEQUENCE_RULE"
MODEL_26_STOP_MANAGEMENT = "M26_CANDLE_SEQUENCE_EXIT"
MODEL_26_SYMBOL = "XAUUSD"
MODEL_26_TIMEFRAME = "M5"
MODEL_26_CONTINUATION_VOLUME = 0.01
MODEL_26_LATERALIZATION_VOLUME = 0.02
MODEL_26_VOLUME = MODEL_26_CONTINUATION_VOLUME  # compatibilidade
MODEL_26_CLOSED_CANDLES = 200
MODEL_26_RAW_CANDLES = MODEL_26_CLOSED_CANDLES + 1
MODEL_26_STOP_BUFFER = 0.01
MODEL_26_MIN_TREND_CANDLES = 1
MODEL_26_RSI_PERIOD = 14
MODEL_26_RSI_BUY_MIN = 50.0
MODEL_26_RSI_BUY_MAX = 70.0
MODEL_26_RSI_SELL_MIN = 30.0
MODEL_26_RSI_SELL_MAX = 50.0
MODEL_26_MIN_RISK_REWARD = 0.0
MODEL_26_CONTRACT_VERSION = "M26_CANDLE_SEQUENCE_V22_20260826"
MODEL_26_RUNTIME_STATE_PATH = Path(".traderia") / "model26_exhaustion_state.json"
_MODEL_26_STATE_LOCK = threading.RLock()
_MODEL_26_STATE_MEMORY: dict[str, Any] = {}
MODEL_26_CONTRACT_FINGERPRINT = hashlib.sha256(
    "|".join(
        (
            MODEL_26_CONTRACT_VERSION,
            MODEL_26_SYMBOL,
            MODEL_26_TIMEFRAME,
            "CONTINUATION_TREND_PLUS_PAUSE_PLUS_BREAKOUT",
            "CONTINUATION_BUY_STOP_RED_HIGH_RSI_50_70",
            "CONTINUATION_SELL_STOP_GREEN_LOW_RSI_30_50",
            "EXHAUSTION_BUY_RSI_CROSS_UP_30",
            "EXHAUSTION_SELL_RSI_CROSS_DOWN_70",
            "EXHAUSTION_STOP_AT_PREVIOUS_CANDLE_EXTREME",
            "EXHAUSTION_EXIT_AFTER_50_OR_EXTREME_RETURN",
            "EXHAUSTION_TRAIL_CONFIRMED_MICRO_SWINGS",
            "CONTINUATION_EXIT_TWO_OPPOSITE_OR_RSI_EXTREME_RETURN",
            "CONTINUATION_TRAIL_EACH_CONFIRMED_PAUSE",
            "TOP_2_GREEN_2_RED",
            "BOTTOM_2_RED_2_GREEN",
            "LATERALIZATION_TWO_OR_MORE_CORRECTION_CANDLES",
            "CONTINUATION_VOLUME_0.01",
            "LATERALIZATION_VOLUME_0.02",
            "LATERALIZATION_BUY_TWO_PLUS_RED_BUY_STOP_LAST_RED_HIGH",
            "LATERALIZATION_SELL_TWO_PLUS_GREEN_SELL_STOP_LAST_GREEN_LOW",
            "RANGE_BUY_RSI_50_70_SELL_RSI_30_50",
            "RANGE_STOP_OUTSIDE_STRUCTURAL_EXTREME",
            "ROUTES_CAN_COEXIST",
            "ROBOT_DEDUPLICATION_PER_ROUTE",
            "ROUTE_IDENTITY_END_TO_END",
            "PLAN_VALIDATION_BEFORE_PROVIDER",
            "NO_SMA_RSI14_CONTINUATION_ONLY",
        )
    ).encode("utf-8")
).hexdigest()[:16]


@dataclass(frozen=True)
class _Bar:
    time: str
    open: float
    high: float
    low: float
    close: float

    @property
    def bullish(self) -> bool:
        return self.close > self.open

    @property
    def bearish(self) -> bool:
        return self.close < self.open


@dataclass(frozen=True)
class _BoundaryMark:
    kind: str
    price: float
    time: str
    index: int


@dataclass(frozen=True)
class Model26Decision:
    direction: str = "WAIT"
    status: str = "M26_AGUARDA_DADOS"
    reason: str = "M26 aguarda snapshot XAUUSD/M5."
    signal_kind: str = "NONE"
    entry_order_type: str = "NONE"
    current_candle_time: str = "N/D"
    closed_candle_time: str = "N/D"
    entry_price: float | None = None
    initial_stop: float | None = None
    target: float | None = None
    risk_reward: float = 0.0
    last_swing_price: float | None = None
    last_swing_time: str = "N/D"
    pullback_candles: int = 0
    trend_candles_before_pullback: int = 0
    range_low: float | None = None
    range_high: float | None = None
    structure_sequence: str = "N/D"
    rsi14: float | None = None
    exhaustion_armed_at: str = "N/D"
    setup_id: str = ""

    @property
    def ready(self) -> bool:
        return (
            self.direction in {"BUY", "SELL"}
            and self.entry_price is not None
            and self.initial_stop is not None
            and self.entry_order_type
            in {"MARKET", "BUY_STOP", "SELL_STOP", "BUY_LIMIT", "SELL_LIMIT"}
        )

    @property
    def route_key(self) -> str:
        route = str(self.signal_kind or "NONE").upper()
        direction = str(self.direction or "WAIT").upper()
        return f"M26:{route}:{direction}"


@dataclass(frozen=True)
class Model26ExitDecision:
    action: str
    status: str
    reason: str
    closed_candle_time: str = "N/D"
    candidate_stop: float | None = None
    structure_sequence: str = "N/D"


def model26_parameters() -> dict[str, object]:
    return {
        "symbol": MODEL_26_SYMBOL,
        "timeframe": MODEL_26_TIMEFRAME,
        "closed_candles": MODEL_26_CLOSED_CANDLES,
        "candle_color_rule": "GREEN_CLOSE_GT_OPEN_RED_CLOSE_LT_OPEN",
        "indicators_disabled": ("SMA20", "SMA50"),
        "rsi_period": MODEL_26_RSI_PERIOD,
        "continuation_buy_rsi": "50<RSI14<=70",
        "continuation_sell_rsi": "30<=RSI14<50",
        "continuation_buy": "GREEN_THEN_RED_THEN_GREEN_BREAKS_RED_HIGH",
        "continuation_sell": "RED_THEN_GREEN_THEN_RED_BREAKS_GREEN_LOW",
        "continuation_buy_order": "BUY_STOP_AT_RED_PAUSE_HIGH",
        "continuation_sell_order": "SELL_STOP_AT_GREEN_PAUSE_LOW",
        "exhaustion_sell_entry": "RSI14_CROSSES_DOWN_70_MARKET",
        "exhaustion_buy_entry": "RSI14_CROSSES_UP_30_MARKET",
        "exhaustion_sell_exit": "AFTER_CROSS_DOWN_50_RETURN_UP_50_OR_AFTER_CROSS_DOWN_30_RETURN_UP_30",
        "exhaustion_buy_exit": "AFTER_CROSS_UP_50_RETURN_DOWN_50_OR_AFTER_CROSS_UP_70_RETURN_DOWN_70",
        "exhaustion_initial_stop": "EXTREME_OF_LAST_CLOSED_SIGNAL_CANDLE",
        "exhaustion_trailing": "LATEST_CONFIRMED_MICRO_BOTTOM_OR_TOP",
        "continuation_stop": "OTHER_SIDE_OF_PULLBACK_CANDLE_BUFFER_0.01",
        "continuation_full_exit": "TWO_OPPOSITE_CANDLES_OR_RSI70_30_RETURN",
        "continuation_trailing": "LATEST_OPPOSITE_CANDLE_CONFIRMED_BY_TREND_CANDLE",
        "top_mark": "TWO_GREEN_THEN_TWO_RED",
        "bottom_mark": "TWO_RED_THEN_TWO_GREEN",
        "lateralization_buy_pattern": "TWO_OR_MORE_RED",
        "lateralization_sell_pattern": "TWO_OR_MORE_GREEN",
        "lateralization_buy_order": "BUY_STOP_AT_LAST_RED_HIGH",
        "lateralization_sell_order": "SELL_STOP_AT_LAST_GREEN_LOW",
        "lateralization_buy_rsi": "50<RSI14<=70",
        "lateralization_sell_rsi": "30<=RSI14<50",
        "lateralization_stop": "OUTSIDE_CORRECTION_SEQUENCE_EXTREME_BUFFER_0.01",
        "lateralization_target": "PREVIOUS_CONFIRMED_STRUCTURAL_EXTREME",
        "entry_routes_are_mutually_exclusive": False,
        "entry_routes_can_coexist": True,
        "maximum_pending_orders_per_route": 1,
        "continuation_volume": MODEL_26_CONTINUATION_VOLUME,
        "lateralization_volume": MODEL_26_LATERALIZATION_VOLUME,
        "active_entry_order_type": "NONE",
        "active_signal_kind": "NONE",
        "contract_version": MODEL_26_CONTRACT_VERSION,
        "contract_fingerprint": MODEL_26_CONTRACT_FINGERPRINT,
    }


def is_model26(value: object) -> bool:
    return str(value or "").strip().upper().startswith(MODEL_26_ID)


def evaluate_model26_entry(
    candles: Iterable[object],
    *,
    exhaustion_state: dict[str, Any] | None = None,
) -> Model26Decision:
    """Retorna a primeira rota para consumidores legados de decisao unica."""
    return evaluate_model26_entries(
        candles,
        exhaustion_state=exhaustion_state,
    )[0]


def evaluate_model26_entries(
    candles: Iterable[object],
    *,
    exhaustion_state: dict[str, Any] | None = None,
) -> tuple[Model26Decision, ...]:
    """Avalia as duas rotas independentes sobre o mesmo snapshot fechado.

    Continuidade e lateralizacao procuram estruturas distintas. Quando ambas
    estiverem prontas, as duas decisoes sao publicadas no mesmo ciclo.
    """
    raw = list(candles) if candles is not None else []
    raw = raw[-MODEL_26_RAW_CANDLES:]
    current_time = _time(raw[-1]) if raw else "N/D"
    closed_count = max(0, len(raw) - 1)
    if len(raw) < MODEL_26_RAW_CANDLES:
        return (Model26Decision(
            status=f"M26_AQUECENDO_{closed_count}_DE_{MODEL_26_CLOSED_CANDLES}",
            reason=f"M26 recebeu {closed_count} de 200 candles M5 fechados.",
            current_candle_time=current_time,
        ),)
    try:
        bars = [_bar(row) for row in raw[:-1]]
    except (TypeError, ValueError):
        return (Model26Decision(
            status="M26_DADOS_INVALIDOS",
            reason="M26 recebeu candle M5 sem OHLC valido.",
            current_candle_time=current_time,
        ),)
    common = {
        "current_candle_time": current_time,
        "closed_candle_time": bars[-1].time,
        "rsi14": _wilder_rsi([bar.close for bar in bars], MODEL_26_RSI_PERIOD),
    }
    ready = tuple(
        validated
        for decision in (
            _continuation_decision(bars, common),
            _lateralization_decision(bars, common),
            _exhaustion_decision(bars, common, exhaustion_state or {}),
        )
        if decision is not None
        for validated in (_validate_entry_decision(decision),)
        if validated is not None
    )
    if ready:
        return ready
    return (Model26Decision(
        status="M26_AGUARDA_CONTINUIDADE_OU_LATERALIZACAO",
        reason=(
            f"Aguardar continuidade com RSI14={float(common['rsi14']):.2f} "
            "ou lateralizacao por duas velas de correcao e uma de retomada."
        ),
        structure_sequence=_latest_sequence(_boundary_marks(bars)),
        **common,
    ),)


def _validate_entry_decision(
    decision: Model26Decision,
) -> Model26Decision | None:
    """Rejeita internamente rotas incoerentes antes de materializar o plano."""
    if not decision.ready:
        return None
    entry = float(decision.entry_price or 0.0)
    stop = float(decision.initial_stop or 0.0)
    target = float(decision.target or 0.0)
    direction = str(decision.direction or "").upper()
    order_type = str(decision.entry_order_type or "").upper()
    if entry <= 0.0 or stop <= 0.0:
        return None
    if direction == "BUY":
        if stop >= entry or order_type not in {"MARKET", "BUY_STOP", "BUY_LIMIT"}:
            return None
        if decision.signal_kind == "LATERALIZATION" and target <= entry:
            return None
    elif direction == "SELL":
        if stop <= entry or order_type not in {"MARKET", "SELL_STOP", "SELL_LIMIT"}:
            return None
        if decision.signal_kind == "LATERALIZATION" and not (0.0 < target < entry):
            return None
    else:
        return None
    return decision


def evaluate_model26_exit(
    candles: Iterable[object],
    side: str,
    *,
    reentry_position: bool = False,
    reentry_route: str = "",
    entry_candle_time: object = None,
) -> Model26ExitDecision:
    """Gere cada rota M26, incluindo exaustao por progresso e retorno do RSI."""
    del reentry_position
    raw = list(candles) if candles is not None else []
    raw = raw[-MODEL_26_RAW_CANDLES:]
    if len(raw) < MODEL_26_RAW_CANDLES:
        return Model26ExitDecision(
            "HOLD_POSITION",
            "M26_EXIT_CANDLES_INSUFICIENTES",
            "M26 preservou a posicao enquanto aquece 200 candles M5 fechados.",
        )
    try:
        bars = [_bar(row) for row in raw[:-1]]
    except (TypeError, ValueError):
        return Model26ExitDecision(
            "HOLD_POSITION",
            "M26_EXIT_DADOS_INVALIDOS",
            "M26 preservou a posicao por falta de OHLC M5 valido.",
        )
    normalized_side = str(side or "").upper()
    if normalized_side not in {"BUY", "SELL"}:
        return Model26ExitDecision(
            "HOLD_POSITION",
            "M26_EXIT_LADO_INVALIDO",
            "Lado da posicao invalido.",
            closed_candle_time=bars[-1].time,
        )
    normalized_route = str(reentry_route or "").upper()
    if normalized_route == "EXHAUSTION":
        entry_index = _entry_bar_index(bars, entry_candle_time)
        rsi_path = _rsi_path(bars)
        exit_level = _exhaustion_exit_level(
            rsi_path,
            normalized_side,
            entry_index,
        )
        current_rsi = rsi_path[-1][1]
        previous_rsi = rsi_path[-2][1]
        if exit_level is not None:
            return Model26ExitDecision(
                "FULL_EXIT",
                f"M26_EXHAUSTION_{normalized_side}_RSI_RETURN_{exit_level}",
                (
                    f"EXHAUSTION {normalized_side}: RSI14 retornou de "
                    f"{previous_rsi:.2f} para {current_rsi:.2f} e perdeu o "
                    f"nivel {exit_level} ja conquistado; encerrar integralmente."
                ),
                closed_candle_time=bars[-1].time,
            )
        candidate_stop = _latest_exhaustion_trailing_stop(
            bars,
            normalized_side,
            entry_index,
        )
        if candidate_stop is not None:
            return Model26ExitDecision(
                "PROTECT_POSITION",
                f"M26_EXHAUSTION_{normalized_side}_TRAIL_STRUCTURE",
                (
                    f"EXHAUSTION {normalized_side}: novo "
                    f"{'fundo' if normalized_side == 'BUY' else 'topo'} "
                    "confirmado; proteger o SL sem afasta-lo."
                ),
                closed_candle_time=bars[-1].time,
                candidate_stop=candidate_stop,
            )
        return Model26ExitDecision(
            "HOLD_POSITION",
            f"M26_EXHAUSTION_{normalized_side}_AWAIT_PROGRESS",
            (
                f"EXHAUSTION {normalized_side}: RSI14 anterior={previous_rsi:.2f}, "
                f"atual={current_rsi:.2f}; manter ate perder 50 ou o extremo "
                "conquistado, protegendo por estrutura."
            ),
            closed_candle_time=bars[-1].time,
        )
    if normalized_route == "LATERALIZATION":
        return Model26ExitDecision(
            "HOLD_POSITION",
            "M26_RANGE_HOLD_SL_TP",
            "Lateralizacao preserva SL e TP nas bordas confirmadas do range.",
            closed_candle_time=bars[-1].time,
            structure_sequence=_latest_sequence(_boundary_marks(bars)),
        )
    opposite_pair = (
        bars[-2].bearish and bars[-1].bearish
        if normalized_side == "BUY"
        else bars[-2].bullish and bars[-1].bullish
    )
    if opposite_pair:
        label = "DOIS_VERMELHOS_BUY" if normalized_side == "BUY" else "DOIS_VERDES_SELL"
        return Model26ExitDecision(
            "FULL_EXIT",
            f"M26_CONTINUATION_EXIT_{label}",
            "Dois candles M5 consecutivos contra a continuidade confirmaram o Full Exit.",
            closed_candle_time=bars[-1].time,
        )
    entry_index = _entry_bar_index(bars, entry_candle_time)
    rsi_path = _rsi_path(bars)
    rsi_exit_level = _continuation_rsi_exit_level(
        rsi_path,
        normalized_side,
        entry_index,
    )
    if rsi_exit_level is not None:
        return Model26ExitDecision(
            "FULL_EXIT",
            f"M26_CONTINUATION_{normalized_side}_RSI_RETURN_{rsi_exit_level}",
            (
                f"CONTINUATION {normalized_side}: RSI14 atingiu o extremo "
                f"{rsi_exit_level} e retornou; encerrar integralmente."
            ),
            closed_candle_time=bars[-1].time,
        )
    candidate = _latest_continuation_trailing_stop(
        bars,
        normalized_side,
        entry_index,
    )
    if candidate is not None:
        return Model26ExitDecision(
            "PROTECT_POSITION",
            f"M26_CONTINUATION_TRAIL_{normalized_side}",
            (
                "Nova pausa de continuidade confirmada; mover o SL para o "
                f"{'fundo' if normalized_side == 'BUY' else 'topo'} criado."
            ),
            closed_candle_time=bars[-1].time,
            candidate_stop=candidate,
        )
    return Model26ExitDecision(
        "HOLD_POSITION",
        "M26_CONTINUATION_HOLD",
        "Sem novo recuo confirmado e sem dois candles contrarios; manter posicao.",
        closed_candle_time=bars[-1].time,
    )


def evolve_model26_exhaustion_state(
    candles: Iterable[object],
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Atualiza o alerta extremo sem desarma-lo quando o RSI retorna."""
    raw = list(candles) if candles is not None else []
    raw = raw[-MODEL_26_RAW_CANDLES:]
    evolved = dict(state or {})
    if len(raw) < MODEL_26_RAW_CANDLES:
        return evolved
    try:
        bars = [_bar(row) for row in raw[:-1]]
    except (TypeError, ValueError):
        return evolved
    closed_time = bars[-1].time
    last_processed = str(evolved.get("last_processed_closed_candle") or "")
    contract_changed = (
        str(evolved.get("contract_version") or "") != MODEL_26_CONTRACT_VERSION
    )
    if last_processed == closed_time and not contract_changed:
        return evolved

    bar_times = [bar.time for bar in bars]
    rebuild = contract_changed or last_processed not in bar_times
    if rebuild:
        evolved.update(
            buy_armed=False,
            buy_armed_at="N/D",
            buy_entry_price=None,
            buy_initial_stop=None,
            sell_armed=False,
            sell_armed_at="N/D",
            sell_entry_price=None,
            sell_initial_stop=None,
        )
        # Contrato novo nao pode transformar cruzamento historico antigo em ordem.
        first_index = max(MODEL_26_RSI_PERIOD + 1, len(bars) - 1)
    else:
        first_index = bar_times.index(last_processed) + 1

    for index in range(first_index, len(bars)):
        processed_time = bars[index].time
        previous_rsi = _wilder_rsi(
            [bar.close for bar in bars[:index]],
            MODEL_26_RSI_PERIOD,
        )
        rsi14 = _wilder_rsi(
            [bar.close for bar in bars[: index + 1]],
            MODEL_26_RSI_PERIOD,
        )
        if previous_rsi < 30.0 <= rsi14:
            evolved.update(
                buy_armed=True,
                buy_armed_at=processed_time,
                buy_entry_price=bars[index].close,
                buy_initial_stop=bars[index].low,
                sell_armed=False,
                sell_armed_at="N/D",
                sell_entry_price=None,
                sell_initial_stop=None,
            )
        elif previous_rsi > 70.0 >= rsi14:
            evolved.update(
                sell_armed=True,
                sell_armed_at=processed_time,
                sell_entry_price=bars[index].close,
                sell_initial_stop=bars[index].high,
                buy_armed=False,
                buy_armed_at="N/D",
                buy_entry_price=None,
                buy_initial_stop=None,
            )
        evolved.update(
            last_processed_closed_candle=processed_time,
            last_rsi14=rsi14,
        )

    evolved.update(
        contract_version=MODEL_26_CONTRACT_VERSION,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    return evolved


def load_model26_exhaustion_state() -> dict[str, Any]:
    with _MODEL_26_STATE_LOCK:
        try:
            payload = json.loads(
                MODEL_26_RUNTIME_STATE_PATH.read_text(encoding="utf-8")
            )
        except (OSError, TypeError, ValueError):
            return dict(_MODEL_26_STATE_MEMORY)
        normalized = dict(payload) if isinstance(payload, dict) else {}
        _MODEL_26_STATE_MEMORY.clear()
        _MODEL_26_STATE_MEMORY.update(normalized)
        return normalized


def update_model26_exhaustion_state(
    candles: Iterable[object],
) -> dict[str, Any]:
    with _MODEL_26_STATE_LOCK:
        current = load_model26_exhaustion_state()
        evolved = evolve_model26_exhaustion_state(candles, current)
        if evolved != current:
            _write_model26_exhaustion_state(evolved)
        return evolved


def consume_model26_exhaustion_alert(side: object) -> None:
    """Consome o alerta somente depois de o MT5 aceitar a entrada."""
    normalized = str(side or "").upper()
    if normalized not in {"BUY", "SELL"}:
        return
    prefix = "buy" if normalized == "BUY" else "sell"
    with _MODEL_26_STATE_LOCK:
        state = load_model26_exhaustion_state()
        state[f"{prefix}_armed"] = False
        state[f"{prefix}_armed_at"] = "N/D"
        state[f"{prefix}_entry_price"] = None
        state[f"{prefix}_initial_stop"] = None
        state[f"last_{prefix}_consumed_at"] = datetime.now(timezone.utc).isoformat()
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        _write_model26_exhaustion_state(state)


def _write_model26_exhaustion_state(payload: dict[str, Any]) -> None:
    _MODEL_26_STATE_MEMORY.clear()
    _MODEL_26_STATE_MEMORY.update(payload)
    temporary: Path | None = None
    try:
        MODEL_26_RUNTIME_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = MODEL_26_RUNTIME_STATE_PATH.with_suffix(f".{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        for attempt in range(6):
            try:
                os.replace(temporary, MODEL_26_RUNTIME_STATE_PATH)
                return
            except PermissionError:
                if attempt >= 5:
                    return
                time.sleep(0.05 * (attempt + 1))
    except OSError:
        # Mantem a decisao em memoria e preserva o ciclo se o OneDrive
        # bloquear transitoriamente o arquivo de runtime.
        return
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _exhaustion_decision(
    bars: list[_Bar],
    common: dict[str, object],
    state: dict[str, Any],
) -> Model26Decision | None:
    if len(bars) < MODEL_26_RSI_PERIOD + 2:
        return None
    if bool(state.get("sell_armed")):
        direction = "SELL"
        entry = float(state.get("sell_entry_price") or bars[-1].close)
        stop = float(state.get("sell_initial_stop") or bars[-1].high)
        armed_at = str(state.get("sell_armed_at") or "N/D")
    elif bool(state.get("buy_armed")):
        direction = "BUY"
        entry = float(state.get("buy_entry_price") or bars[-1].close)
        stop = float(state.get("buy_initial_stop") or bars[-1].low)
        armed_at = str(state.get("buy_armed_at") or "N/D")
    else:
        return None
    decision_common = dict(common)
    decision_common["closed_candle_time"] = armed_at
    return Model26Decision(
        direction=direction,
        status=f"M26_EXHAUSTION_{direction}_MARKET_PRONTA",
        reason=(
            f"EXHAUSTION {direction}: cruzamento de retorno do RSI14 confirmado "
            f"em {armed_at}; entrada a mercado com SL na vela fechada do sinal."
        ),
        signal_kind="EXHAUSTION",
        entry_order_type="MARKET",
        entry_price=entry,
        initial_stop=stop,
        target=0.0,
        last_swing_price=stop,
        last_swing_time=armed_at,
        exhaustion_armed_at=armed_at,
        setup_id=f"M26|EXHAUSTION|{direction}|{armed_at}",
        **decision_common,
    )


def _rsi_path(bars: list[_Bar]) -> list[tuple[int, float]]:
    return [
        (
            index,
            _wilder_rsi(
                [bar.close for bar in bars[: index + 1]],
                MODEL_26_RSI_PERIOD,
            ),
        )
        for index in range(MODEL_26_RSI_PERIOD, len(bars))
    ]


def _entry_bar_index(bars: list[_Bar], entry_candle_time: object) -> int:
    expected = str(entry_candle_time or "").strip()
    if expected:
        for index, bar in enumerate(bars):
            if bar.time == expected:
                return index
        expected_epoch = _timestamp_epoch(expected)
        if expected_epoch is not None:
            for index, bar in enumerate(bars):
                if _timestamp_epoch(bar.time) == expected_epoch:
                    return index
    # Snapshot legado sem horario pode usar somente a pausa mais recente,
    # sem herdar toda a estrutura anterior a posicao.
    return max(0, len(bars) - 3)


def _timestamp_epoch(value: object) -> int | None:
    raw = str(value or "").strip()
    if not raw or raw.upper() in {"N/D", "NONE"}:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        pass
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def _continuation_rsi_exit_level(
    rsi_path: list[tuple[int, float]],
    side: str,
    entry_index: int,
) -> int | None:
    after_entry = [(index, value) for index, value in rsi_path if index >= entry_index]
    if len(after_entry) < 2:
        return None
    extreme_reached = (
        after_entry[0][1] > 70.0
        if side == "BUY"
        else after_entry[0][1] < 30.0
    )
    for (_, previous), (_, current) in zip(after_entry, after_entry[1:]):
        if side == "BUY":
            if current > 70.0:
                extreme_reached = True
            if extreme_reached and previous >= 70.0 > current:
                return 70
        else:
            if current < 30.0:
                extreme_reached = True
            if extreme_reached and previous <= 30.0 < current:
                return 30
    return None


def _latest_continuation_trailing_stop(
    bars: list[_Bar],
    side: str,
    entry_index: int,
) -> float | None:
    first = max(1, entry_index + 1)
    candidates: list[float] = []
    for index in range(first, len(bars) - 1):
        if side == "BUY" and bars[index].bearish and bars[index + 1].bullish:
            candidates.append(bars[index].low - MODEL_26_STOP_BUFFER)
        elif side == "SELL" and bars[index].bullish and bars[index + 1].bearish:
            candidates.append(bars[index].high + MODEL_26_STOP_BUFFER)
    return candidates[-1] if candidates else None


def _exhaustion_exit_level(
    rsi_path: list[tuple[int, float]],
    side: str,
    entry_index: int,
) -> int | None:
    after_entry = [(index, value) for index, value in rsi_path if index >= entry_index]
    if len(after_entry) < 2:
        return None
    crossed_50 = False
    crossed_extreme = False
    for (_, previous), (_, current) in zip(after_entry, after_entry[1:]):
        if side == "BUY":
            if previous < 50.0 <= current:
                crossed_50 = True
            if previous < 70.0 <= current:
                crossed_extreme = True
            if crossed_extreme and previous >= 70.0 > current:
                return 70
            if crossed_50 and previous >= 50.0 > current:
                return 50
        else:
            if previous > 50.0 >= current:
                crossed_50 = True
            if previous > 30.0 >= current:
                crossed_extreme = True
            if crossed_extreme and previous <= 30.0 < current:
                return 30
            if crossed_50 and previous <= 50.0 < current:
                return 50
    return None


def _latest_exhaustion_trailing_stop(
    bars: list[_Bar],
    side: str,
    entry_index: int,
) -> float | None:
    first = max(1, entry_index + 1)
    candidates: list[float] = []
    for index in range(first, len(bars) - 1):
        if side == "BUY" and (
            bars[index].low <= bars[index - 1].low
            and bars[index].low <= bars[index + 1].low
        ):
            candidates.append(bars[index].low)
        elif side == "SELL" and (
            bars[index].high >= bars[index - 1].high
            and bars[index].high >= bars[index + 1].high
        ):
            candidates.append(bars[index].high)
    return candidates[-1] if candidates else None


def _continuation_decision(
    bars: list[_Bar], common: dict[str, object]
) -> Model26Decision | None:
    if len(bars) < MODEL_26_RSI_PERIOD + 1:
        return None
    rsi14 = float(common.get("rsi14") or 50.0)
    pause = bars[-1]
    breakout_confirmed = False
    if pause.bearish:
        direction = "BUY"
        trend_test = lambda bar: bar.bullish
        entry = pause.high
        stop = pause.low - MODEL_26_STOP_BUFFER
        order_type = "BUY_STOP"
        rsi_allowed = MODEL_26_RSI_BUY_MIN < rsi14 <= MODEL_26_RSI_BUY_MAX
    elif pause.bullish:
        direction = "SELL"
        trend_test = lambda bar: bar.bearish
        entry = pause.low
        stop = pause.high + MODEL_26_STOP_BUFFER
        order_type = "SELL_STOP"
        rsi_allowed = MODEL_26_RSI_SELL_MIN <= rsi14 < MODEL_26_RSI_SELL_MAX
    else:
        direction = ""
        trend_test = lambda bar: False
        entry = stop = 0.0
        order_type = "NONE"
        rsi_allowed = False
    trend_end_index = len(bars) - 2
    if not rsi_allowed and len(bars) >= 3:
        breakout = bars[-1]
        candidate_pause = bars[-2]
        if (
            breakout.bullish
            and candidate_pause.bearish
            and breakout.high >= candidate_pause.high
        ):
            direction = "BUY"
            trend_test = lambda bar: bar.bullish
            entry = candidate_pause.high
            stop = candidate_pause.low - MODEL_26_STOP_BUFFER
            order_type = "BUY_STOP"
            rsi_allowed = MODEL_26_RSI_BUY_MIN < rsi14 <= MODEL_26_RSI_BUY_MAX
        elif (
            breakout.bearish
            and candidate_pause.bullish
            and breakout.low <= candidate_pause.low
        ):
            direction = "SELL"
            trend_test = lambda bar: bar.bearish
            entry = candidate_pause.low
            stop = candidate_pause.high + MODEL_26_STOP_BUFFER
            order_type = "SELL_STOP"
            rsi_allowed = MODEL_26_RSI_SELL_MIN <= rsi14 < MODEL_26_RSI_SELL_MAX
        else:
            return None
        pause = candidate_pause
        breakout_confirmed = True
        trend_end_index = len(bars) - 3
    if not rsi_allowed:
        return None
    index = trend_end_index
    trend_count = 0
    while index >= 0 and trend_test(bars[index]):
        trend_count += 1
        index -= 1
    if trend_count < MODEL_26_MIN_TREND_CANDLES:
        return None
    return Model26Decision(
        direction=direction,
        status=(
            f"M26_CONTINUATION_{order_type}_ROMPIDA_PRONTA"
            if breakout_confirmed
            else f"M26_CONTINUATION_{order_type}_PRONTA"
        ),
        reason=(
            f"{direction}: {trend_count} candles a favor + vela de pausa; "
            f"RSI14={rsi14:.2f}; {order_type} na extremidade da pausa"
            + (
                "; rompimento confirmado no ultimo candle fechado"
                if breakout_confirmed
                else ""
            )
            + " e "
            "SL alem da extremidade oposta."
        ),
        signal_kind="CONTINUATION",
        entry_order_type=order_type,
        entry_price=entry,
        initial_stop=stop,
        target=0.0,
        last_swing_price=pause.low if direction == "BUY" else pause.high,
        last_swing_time=pause.time,
        pullback_candles=1,
        trend_candles_before_pullback=trend_count,
        setup_id=f"M26|CONTINUATION|{direction}|{pause.time}",
        **common,
    )


def _wilder_rsi(values: list[float], period: int) -> float:
    if len(values) <= period:
        return 50.0
    changes = [current - previous for previous, current in zip(values, values[1:])]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    average_gain = sum(gains[:period]) / float(period)
    average_loss = sum(losses[:period]) / float(period)
    for gain, loss in zip(gains[period:], losses[period:]):
        average_gain = ((average_gain * (period - 1)) + gain) / float(period)
        average_loss = ((average_loss * (period - 1)) + loss) / float(period)
    if average_loss == 0.0:
        return 100.0 if average_gain > 0.0 else 50.0
    relative_strength = average_gain / average_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def _lateralization_decision(
    bars: list[_Bar], common: dict[str, object]
) -> Model26Decision | None:
    if len(bars) < 6:
        return None
    latest = bars[-1]
    correction_is_bullish = latest.bullish
    correction_is_bearish = latest.bearish
    if not (correction_is_bullish or correction_is_bearish):
        return None
    correction_count = 0
    for bar in reversed(bars):
        same_color = bar.bullish if correction_is_bullish else bar.bearish
        if not same_color:
            break
        correction_count += 1
    if correction_count < 2:
        return None
    correction = bars[-correction_count:]
    marks = _boundary_marks(bars[:-correction_count])
    if not marks:
        return None
    rsi14 = float(common.get("rsi14") or 50.0)
    if correction_is_bullish:
        if not MODEL_26_RSI_SELL_MIN <= rsi14 < MODEL_26_RSI_SELL_MAX:
            return None
        target_mark = next(
            (mark for mark in reversed(marks) if mark.kind == "BOTTOM"),
            None,
        )
        if target_mark is None:
            return None
        direction, order_type = "SELL", "SELL_STOP"
        entry = latest.low
        stop_mark = max(correction, key=lambda bar: bar.high)
        stop_reference = stop_mark.high
        stop = stop_reference + MODEL_26_STOP_BUFFER
        target = target_mark.price
    else:
        if not MODEL_26_RSI_BUY_MIN < rsi14 <= MODEL_26_RSI_BUY_MAX:
            return None
        target_mark = next(
            (mark for mark in reversed(marks) if mark.kind == "TOP"),
            None,
        )
        if target_mark is None:
            return None
        direction, order_type = "BUY", "BUY_STOP"
        entry = latest.high
        stop_mark = min(correction, key=lambda bar: bar.low)
        stop_reference = stop_mark.low
        stop = stop_reference - MODEL_26_STOP_BUFFER
        target = target_mark.price
    valid = stop < entry < target if direction == "BUY" else target < entry < stop
    if not valid:
        return None
    color = "RED" if direction == "BUY" else "GREEN"
    sequence = f"{color}x{correction_count}"
    risk = abs(entry - stop)
    return Model26Decision(
        direction=direction,
        status=f"M26_LATERALIZATION_{order_type}_PRONTA",
        reason=(
            f"{direction}: lateralizacao {sequence}; RSI14={rsi14:.2f}; "
            f"{order_type} na extremidade da ultima vela fechada, SL alem "
            "do topo/fundo criado pela sequencia e TP no "
            "ultimo extremo estrutural."
        ),
        signal_kind="LATERALIZATION",
        entry_order_type=order_type,
        entry_price=entry,
        initial_stop=stop,
        target=target,
        risk_reward=abs(target - entry) / risk if risk else 0.0,
        last_swing_price=stop_reference,
        last_swing_time=stop_mark.time,
        pullback_candles=correction_count,
        range_low=target if direction == "SELL" else stop,
        range_high=target if direction == "BUY" else stop,
        structure_sequence=sequence,
        setup_id=f"M26|LATERALIZATION|{direction}|{latest.time}",
        **common,
    )


def _boundary_marks(bars: list[_Bar]) -> list[_BoundaryMark]:
    raw: list[_BoundaryMark] = []
    for index in range(3, len(bars)):
        group = bars[index - 3 : index + 1]
        if all(bar.bullish for bar in group[:2]) and all(bar.bearish for bar in group[2:]):
            offset, candle = max(enumerate(group), key=lambda item: item[1].high)
            raw.append(
                _BoundaryMark("TOP", candle.high, candle.time, index - 3 + offset)
            )
        elif all(bar.bearish for bar in group[:2]) and all(bar.bullish for bar in group[2:]):
            offset, candle = min(enumerate(group), key=lambda item: item[1].low)
            raw.append(
                _BoundaryMark("BOTTOM", candle.low, candle.time, index - 3 + offset)
            )
    compressed: list[_BoundaryMark] = []
    for mark in raw:
        if not compressed or compressed[-1].kind != mark.kind:
            compressed.append(mark)
            continue
        previous = compressed[-1]
        more_extreme = mark.price > previous.price if mark.kind == "TOP" else mark.price < previous.price
        if more_extreme:
            compressed[-1] = mark
    return compressed


def _latest_sequence(marks: list[_BoundaryMark]) -> str:
    return "-".join(mark.kind for mark in marks[-3:]) if marks else "N/D"


def _bar(row: object) -> _Bar:
    return _Bar(
        time=_time(row),
        open=float(_value(row, "abertura", "open")),
        high=float(_value(row, "maxima", "high")),
        low=float(_value(row, "minima", "low")),
        close=float(_value(row, "fechamento", "close")),
    )


def _value(row: object, *names: str) -> object:
    for name in names:
        if isinstance(row, Mapping) and name in row:
            return row[name]
        dtype_names = getattr(getattr(row, "dtype", None), "names", ()) or ()
        if name in dtype_names:
            return row[name]  # type: ignore[index]
        if hasattr(row, name):
            return getattr(row, name)
    raise ValueError(f"Campo ausente: {names[0]}")


def _time(row: object) -> str:
    names = ("data", "time", "timestamp")
    if isinstance(row, Mapping):
        for name in names:
            if name in row and row[name] is not None:
                return str(row[name])
    dtype_names = getattr(getattr(row, "dtype", None), "names", ()) or ()
    for name in names:
        if name in dtype_names and row[name] is not None:  # type: ignore[index]
            return str(row[name])  # type: ignore[index]
    for name in names:
        if not hasattr(row, name):
            continue
        value = getattr(row, name)
        if value is not None:
            return str(value)
    return "N/D"
