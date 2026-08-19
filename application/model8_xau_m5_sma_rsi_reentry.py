"""Modelo 8: XAUUSD/M5 por direcao SMA20/50 e entrada/reentrada no RSI50."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
from typing import Any, Iterable

from application.mt5_native_m5_indicators import MT5NativeM5IndicatorSnapshot
from application.operational_indicator_window import (
    OPERATIONAL_INDICATOR_CLOSED_CANDLES,
    OPERATIONAL_INDICATOR_RAW_CANDLES,
)


MODEL_8_ID = "MODELO_8_XAU_M5_SMA_RSI_REENTRY"
MODEL_8_SHORT_NAME = "M8"
MODEL_8_SYMBOL = "XAUUSD"
MODEL_8_TIMEFRAME = "M5"
MODEL_8_COMMENT = "TraderIA M8"
MODEL_8_ALPHA_ID = "ALPHAXAU8_SMA20_50_RSI14"
MODEL_8_ALPHA_VERSION = "M8_ENTRY_V3"
MODEL_8_BETA_ID = "BETAXAU8_RSI70_30_SMA_FULL_EXIT"
MODEL_8_BETA_VERSION = "M8_EXIT_V3"
MODEL_8_STOP_MANAGEMENT = "M8_SMA_RSI_FULL_EXIT"
MODEL_8_ENTRY_ORDER_TYPE = "MARKET_ON_CONFIRMED_CLOSED_M5_SMA20_50_CROSS_WITH_RSI50"
MODEL_8_REENTRY_ORDER_TYPE = "PENDING_STOP_PREVIOUS_CLOSED_M5_EXTREME"
MODEL_8_SMA_FAST = 20
MODEL_8_SMA_SLOW = 50
MODEL_8_RSI_PERIOD = 14
MODEL_8_RSI_BUY_FILTER = 50.0
MODEL_8_RSI_SELL_FILTER = 50.0
MODEL_8_RSI_BUY_EXIT = 70.0
MODEL_8_RSI_SELL_EXIT = 30.0
MODEL_8_LOOKBACK_CANDLES = OPERATIONAL_INDICATOR_RAW_CANDLES
MODEL_8_SWING_LEFT = 2
MODEL_8_SWING_RIGHT = 2
MODEL_8_STOP_BUFFER = 0.01
MODEL_8_REENTRY_PULLBACK_CANDLES = 2
MODEL_8_RUNTIME_STATE_PATH = Path(".traderia") / "model8_runtime_state.json"
_MODEL_8_STATE_LOCK = threading.RLock()


@dataclass(frozen=True)
class Model8EntryDecision:
    """Decisao pura para a entrada a mercado do M8 no candle M5 fechado."""

    direction: str
    status: str
    reason: str
    signal_kind: str = "NONE"
    entry_order_type: str = "NONE"
    current_candle_time: str = "N/D"
    closed_candle_time: str = "N/D"
    entry_price: float | None = None
    initial_stop: float | None = None
    sma20: float | None = None
    sma50: float | None = None
    rsi14: float | None = None
    previous_sma20: float | None = None
    previous_sma50: float | None = None
    last_swing_price: float | None = None
    last_swing_time: str = "N/D"
    structural_target_price: float | None = None
    structural_target_time: str = "N/D"
    indicator_source: str = "LOCAL_CANDLES"
    indicator_generated_at: str = "N/D"

    @property
    def ready(self) -> bool:
        return (
            self.direction in {"BUY", "SELL"}
            and self.entry_price is not None
            and self.initial_stop is not None
        )


@dataclass(frozen=True)
class Model8ExitDecision:
    """Decisao pos-entrada por candle M5 fechado."""

    action: str
    status: str
    reason: str
    extreme_armed: bool
    closed_candle_time: str = "N/D"
    sma20: float | None = None
    sma50: float | None = None
    rsi14: float | None = None
    previous_rsi14: float | None = None
    indicator_source: str = "LOCAL_CANDLES"
    indicator_generated_at: str = "N/D"


def evaluate_model8_native_entry(
    snapshot: MT5NativeM5IndicatorSnapshot,
    *,
    awaiting_reentry_side: str | None = None,
    stop_buffer: float = MODEL_8_STOP_BUFFER,
) -> Model8EntryDecision:
    """Entrada M8 sem warmup Python, usando apenas o snapshot fechado do MT5."""
    common = {
        "current_candle_time": snapshot.current_candle_time,
        "closed_candle_time": snapshot.closed_candle_time,
        "sma20": snapshot.sma20,
        "sma50": snapshot.sma50,
        "rsi14": snapshot.rsi14,
        "previous_sma20": snapshot.previous_sma20,
        "previous_sma50": snapshot.previous_sma50,
        "indicator_source": snapshot.indicator_source,
        "indicator_generated_at": snapshot.generated_at,
    }
    reentry_side = str(awaiting_reentry_side or "").upper()
    if snapshot.rsi14 > MODEL_8_RSI_BUY_FILTER and snapshot.sma20 > snapshot.sma50:
        direction = "BUY"
    elif snapshot.rsi14 < MODEL_8_RSI_SELL_FILTER and snapshot.sma20 < snapshot.sma50:
        direction = "SELL"
    else:
        return Model8EntryDecision(
            direction="WAIT",
            status="M8_AGUARDA_NIVEL_RSI50_E_DIRECAO_SMA",
            reason=(
                "MT5 nativo: aguardar RSI14>50 com SMA20>SMA50 para BUY ou "
                "RSI14<50 com SMA20<SMA50 para SELL."
            ),
            **common,
        )

    crossed_now = (
        snapshot.previous_sma20 <= snapshot.previous_sma50
        and snapshot.sma20 > snapshot.sma50
        if direction == "BUY"
        else snapshot.previous_sma20 >= snapshot.previous_sma50
        and snapshot.sma20 < snapshot.sma50
    )
    is_reentry = reentry_side == direction
    if not crossed_now and not is_reentry:
        return Model8EntryDecision(
            direction="WAIT",
            status="M8_TENDENCIA_EXISTENTE_AGUARDA_REENTRADA_ESTRUTURAL_M5",
            reason=(
                "MT5 nativo: SMA20/50 ja estavam cruzadas antes do ultimo candle "
                "fechado. Nao liberar primeira entrada; aguardar recuo e rompimento "
                "estrutural M5 para reentrada."
            ),
            signal_kind="REENTRY",
            **common,
        )
    signal_kind = "REENTRY" if is_reentry else "SMA20_50_CROSS"
    swing_price = (
        snapshot.last_swing_low if direction == "BUY" else snapshot.last_swing_high
    )
    swing_time = (
        snapshot.last_swing_low_time
        if direction == "BUY"
        else snapshot.last_swing_high_time
    )
    if is_reentry:
        entry = snapshot.high if direction == "BUY" else snapshot.low
        entry_order_type = "BUY_STOP" if direction == "BUY" else "SELL_STOP"
        structural_target_price = (
            snapshot.last_swing_high if direction == "BUY" else snapshot.last_swing_low
        )
        structural_target_time = (
            snapshot.last_swing_high_time
            if direction == "BUY"
            else snapshot.last_swing_low_time
        )
    else:
        entry = snapshot.close
        entry_order_type = "MARKET"
        structural_target_price = None
        structural_target_time = "N/D"
    buffer = abs(float(stop_buffer))
    stop = swing_price - buffer if direction == "BUY" else swing_price + buffer
    valid = stop < entry if direction == "BUY" else stop > entry
    if not valid:
        return Model8EntryDecision(
            direction="WAIT",
            status="M8_STOP_INVALIDO",
            reason="Pivo 2+2 nativo do MT5 nao produz SL valido para a entrada.",
            signal_kind=signal_kind,
            entry_order_type=entry_order_type,
            entry_price=entry,
            initial_stop=stop,
            last_swing_price=swing_price,
            last_swing_time=swing_time,
            structural_target_price=structural_target_price,
            structural_target_time=structural_target_time,
            **common,
        )
    target_valid = (
        not is_reentry
        or (
            structural_target_price is not None
            and (
                structural_target_price > entry
                if direction == "BUY"
                else structural_target_price < entry
            )
        )
    )
    if not target_valid:
        return Model8EntryDecision(
            direction="WAIT",
            status="M8_REENTRY_AGUARDA_ALVO_ESTRUTURAL_VALIDO",
            reason=(
                "MT5 nativo: reentrada aguarda topo/fundo M5 confirmado antes da "
                "correcao e no lado favoravel da entrada."
            ),
            signal_kind="REENTRY",
            entry_order_type=entry_order_type,
            entry_price=entry,
            initial_stop=stop,
            last_swing_price=swing_price,
            last_swing_time=swing_time,
            structural_target_price=structural_target_price,
            structural_target_time=structural_target_time,
            **common,
        )
    return Model8EntryDecision(
        direction=direction,
        status=(
            f"M8_REENTRY_{entry_order_type}_PRONTA"
            if is_reentry
            else f"M8_{direction}_MERCADO_PRONTA"
        ),
        reason=(
            f"MT5 nativo: {direction} confirmado no candle M5 fechado; "
            f"{'reentrada Stop no extremo do candle anterior' if is_reentry else 'entrada a mercado'} "
            "e SL no ultimo pivo 2+2."
        ),
        signal_kind=signal_kind,
        entry_order_type=entry_order_type,
        entry_price=entry,
        initial_stop=stop,
        last_swing_price=swing_price,
        last_swing_time=swing_time,
        structural_target_price=structural_target_price,
        structural_target_time=structural_target_time,
        **common,
    )


def evaluate_model8_entry(
    candles: Iterable[object],
    *,
    awaiting_reentry_side: str | None = None,
    stop_buffer: float = MODEL_8_STOP_BUFFER,
) -> Model8EntryDecision:
    """Entra no cruzamento SMA20/50; tendencia ja iniciada segue como reentrada."""
    rows = list(candles or ())[-MODEL_8_LOOKBACK_CANDLES :]
    minimum = MODEL_8_LOOKBACK_CANDLES
    if len(rows) < minimum:
        return Model8EntryDecision(
            direction="WAIT",
            status=f"M8_AQUECENDO_{len(rows)}_DE_{minimum}_CANDLES",
            reason=(
                f"M8 aquecendo dados: recebeu {len(rows)} de {minimum} candles "
                "M5 necessarios: 200 fechados e o atual em formacao."
            ),
        )

    closed_rows = rows[:-1]
    closes = [_candle_value(row, "close") for row in closed_rows]
    if any(value is None for value in closes):
        return Model8EntryDecision(
            direction="WAIT",
            status="M8_DADOS_INVALIDOS",
            reason="M8 recebeu candle M5 fechado sem preco valido.",
        )
    values = [float(value) for value in closes if value is not None]
    sma20 = _sma(values, MODEL_8_SMA_FAST)
    sma50 = _sma(values, MODEL_8_SMA_SLOW)
    previous_sma20 = _sma(values[:-1], MODEL_8_SMA_FAST)
    previous_sma50 = _sma(values[:-1], MODEL_8_SMA_SLOW)
    rsi14 = _wilder_rsi(values, MODEL_8_RSI_PERIOD)
    current_time = _candle_time(rows[-1])
    closed_time = _candle_time(closed_rows[-1])
    common = {
        "current_candle_time": current_time,
        "closed_candle_time": closed_time,
        "sma20": sma20,
        "sma50": sma50,
        "rsi14": rsi14,
        "previous_sma20": previous_sma20,
        "previous_sma50": previous_sma50,
    }

    reentry_side = str(awaiting_reentry_side or "").upper()
    direction = "WAIT"
    if rsi14 > MODEL_8_RSI_BUY_FILTER and sma20 > sma50:
        direction = "BUY"
    elif rsi14 < MODEL_8_RSI_SELL_FILTER and sma20 < sma50:
        direction = "SELL"
    else:
        return Model8EntryDecision(
            direction="WAIT",
            status="M8_AGUARDA_NIVEL_RSI50_E_DIRECAO_SMA",
            reason=(
                "Aguardar RSI14 acima de 50 com SMA20>SMA50 para BUY ou "
                "RSI14 abaixo de 50 com SMA20<SMA50 para SELL."
            ),
            **common,
        )

    crossed_now = (
        previous_sma20 <= previous_sma50 and sma20 > sma50
        if direction == "BUY"
        else previous_sma20 >= previous_sma50 and sma20 < sma50
    )
    is_reentry = reentry_side == direction or not crossed_now
    signal_kind = "REENTRY" if is_reentry else "SMA20_50_CROSS"

    swing_price, swing_time = _last_confirmed_swing(closed_rows, direction)
    if swing_price is None:
        return Model8EntryDecision(
            direction="WAIT",
            status="M8_SWING_NAO_CONFIRMADO",
            reason="M8 aguarda ultimo fundo/topo M5 confirmado para definir o SL.",
            signal_kind=signal_kind,
            **common,
        )

    buffer = abs(float(stop_buffer))
    structural_target_price: float | None = None
    structural_target_time = "N/D"
    if is_reentry:
        pullback_ok, pullback_reason = _reentry_pullback_structure(
            closed_rows,
            direction,
        )
        if not pullback_ok:
            return Model8EntryDecision(
                direction="WAIT",
                status="M8_REENTRY_AGUARDA_RECUO_ESTRUTURAL_M5",
                reason=pullback_reason,
                signal_kind="REENTRY",
                last_swing_price=swing_price,
                last_swing_time=swing_time,
                **common,
            )
        reference_field = "high" if direction == "BUY" else "low"
        reference_price = _candle_value(closed_rows[-1], reference_field)
        if reference_price is None:
            return Model8EntryDecision(
                direction="WAIT",
                status="M8_REENTRY_GATILHO_INVALIDO",
                reason="M8 nao encontrou topo/fundo do ultimo candle M5 fechado.",
                signal_kind=signal_kind,
                **common,
            )
        entry = float(reference_price)
        entry_order_type = "BUY_STOP" if direction == "BUY" else "SELL_STOP"
        structural_target_price, structural_target_time = _pullback_origin_target(
            closed_rows,
            direction,
        )
        target_valid = (
            structural_target_price is not None
            and (
                structural_target_price > entry
                if direction == "BUY"
                else structural_target_price < entry
            )
        )
        if not target_valid:
            return Model8EntryDecision(
                direction="WAIT",
                status="M8_REENTRY_AGUARDA_ALVO_ESTRUTURAL_VALIDO",
                reason=(
                    "M8 aguarda topo/fundo M5 confirmado antes da correcao e no "
                    "lado favoravel da reentrada."
                ),
                signal_kind="REENTRY",
                entry_order_type=entry_order_type,
                entry_price=entry,
                last_swing_price=swing_price,
                last_swing_time=swing_time,
                structural_target_price=structural_target_price,
                structural_target_time=structural_target_time,
                **common,
            )
    else:
        entry = values[-1]
        entry_order_type = "MARKET"
    stop = swing_price - buffer if direction == "BUY" else swing_price + buffer
    valid = stop < entry if direction == "BUY" else stop > entry
    if not valid:
        return Model8EntryDecision(
            direction="WAIT",
            status="M8_STOP_INVALIDO",
            reason="Ultimo fundo/topo confirmado nao produz SL valido alem da SMA20.",
            signal_kind=signal_kind,
            entry_order_type=entry_order_type,
            entry_price=entry,
            initial_stop=stop,
            last_swing_price=swing_price,
            last_swing_time=swing_time,
            structural_target_price=structural_target_price,
            structural_target_time=structural_target_time,
            **common,
        )

    label = "reentrada" if signal_kind == "REENTRY" else "entrada"
    return Model8EntryDecision(
        direction=direction,
        status=(
            f"M8_REENTRY_{entry_order_type}_PRONTA"
            if is_reentry
            else f"M8_{direction}_MERCADO_PRONTA"
        ),
        reason=(
            (
                f"M8 reentrada {entry_order_type}: RSI50 e SMA confirmados; "
                "recuo estrutural M5 oposto confirmado por dois candles; "
                f"ordem Stop exatamente na "
                f"{'maxima' if direction == 'BUY' else 'minima'} "
                "do ultimo candle M5 fechado."
            )
            if is_reentry
            else (
                f"M8 {label}: {direction} no cruzamento confirmado SMA20/50 do ultimo "
                f"candle M5 fechado, com RSI14 alinhado; SL {buffer:g} alem do ultimo "
                f"{'fundo' if direction == 'BUY' else 'topo'} confirmado."
            )
        ),
        signal_kind=signal_kind,
        entry_order_type=entry_order_type,
        entry_price=entry,
        initial_stop=stop,
        last_swing_price=swing_price,
        last_swing_time=swing_time,
        structural_target_price=structural_target_price,
        structural_target_time=structural_target_time,
        **common,
    )


def evaluate_model8_exit(
    candles: Iterable[object],
    side: str,
    *,
    extreme_armed: bool = False,
    reentry_position: bool = False,
    sma_inversion_exit_enabled: bool = True,
    rsi50_inversion_exit_enabled: bool = False,
    extreme_return_exit_enabled: bool = False,
) -> Model8ExitDecision:
    """Avalia Full Exit por SMA20/50 e RSI, conforme o contrato da posicao."""
    rows = list(candles or ())[-MODEL_8_LOOKBACK_CANDLES :]
    minimum = MODEL_8_LOOKBACK_CANDLES
    if len(rows) < minimum:
        return Model8ExitDecision(
            action="HOLD_POSITION",
            status="M8_EXIT_CANDLES_INSUFICIENTES",
            reason=f"M8 exige ao menos {minimum} candles M5 para avaliar a saida.",
            extreme_armed=bool(extreme_armed),
        )
    closed_rows = rows[:-1]
    closes = [_candle_value(row, "close") for row in closed_rows]
    if any(value is None for value in closes):
        return Model8ExitDecision(
            action="HOLD_POSITION",
            status="M8_EXIT_DADOS_INVALIDOS",
            reason="M8 preservou a posicao porque faltou fechamento M5 valido.",
            extreme_armed=bool(extreme_armed),
        )
    values = [float(value) for value in closes if value is not None]
    sma20 = _sma(values, MODEL_8_SMA_FAST)
    sma50 = _sma(values, MODEL_8_SMA_SLOW)
    rsi14 = _wilder_rsi(values, MODEL_8_RSI_PERIOD)
    previous_rsi14 = _wilder_rsi(values[:-1], MODEL_8_RSI_PERIOD)
    closed_time = _candle_time(closed_rows[-1])
    normalized_side = str(side or "").upper()
    common = {
        "closed_candle_time": closed_time,
        "sma20": sma20,
        "sma50": sma50,
        "rsi14": rsi14,
        "previous_rsi14": previous_rsi14,
    }

    if (
        sma_inversion_exit_enabled
        and normalized_side == "BUY"
        and sma20 <= sma50
    ):
        return Model8ExitDecision(
            action="FULL_EXIT",
            status="M8_EXIT_INVERSAO_SMA_BUY",
            reason="SMA20 deixou de ficar acima da SMA50; encerrar integralmente BUY.",
            extreme_armed=bool(extreme_armed),
            **common,
        )
    if (
        sma_inversion_exit_enabled
        and normalized_side == "SELL"
        and sma20 >= sma50
    ):
        return Model8ExitDecision(
            action="FULL_EXIT",
            status="M8_EXIT_INVERSAO_SMA_SELL",
            reason="SMA20 deixou de ficar abaixo da SMA50; encerrar integralmente SELL.",
            extreme_armed=bool(extreme_armed),
            **common,
        )
    if normalized_side not in {"BUY", "SELL"}:
        return Model8ExitDecision(
            action="HOLD_POSITION",
            status="M8_EXIT_LADO_INVALIDO",
            reason="M8 recebeu lado de posicao invalido; nenhuma acao executada.",
            extreme_armed=bool(extreme_armed),
            **common,
        )

    if extreme_return_exit_enabled:
        returned_from_buy_extreme = normalized_side == "BUY" and rsi14 < 70.0
        returned_from_sell_extreme = normalized_side == "SELL" and rsi14 > 30.0
        if returned_from_buy_extreme or returned_from_sell_extreme:
            level = "70_PARA_BAIXO_BUY" if returned_from_buy_extreme else "30_PARA_CIMA_SELL"
            return Model8ExitDecision(
                action="FULL_EXIT",
                status=f"M24_CONTINUATION_EXIT_RSI_{level}",
                reason=(
                    "CONTINUATION perdeu o RSI extremo exigido; encerrar "
                    "integralmente mesmo apos reinicio ou candle nao observado."
                ),
                extreme_armed=False,
                **common,
            )

    if rsi50_inversion_exit_enabled:
        buy_crossed_down = (
            normalized_side == "BUY"
            and previous_rsi14 >= MODEL_8_RSI_BUY_FILTER
            and rsi14 < MODEL_8_RSI_BUY_FILTER
        )
        sell_crossed_up = (
            normalized_side == "SELL"
            and previous_rsi14 <= MODEL_8_RSI_SELL_FILTER
            and rsi14 > MODEL_8_RSI_SELL_FILTER
        )
        if buy_crossed_down or sell_crossed_up:
            direction = "PARA_BAIXO_BUY" if buy_crossed_down else "PARA_CIMA_SELL"
            return Model8ExitDecision(
                action="FULL_EXIT",
                status=f"M24_EXIT_RSI50_CRUZOU_{direction}",
                reason=(
                    "Candle M5 confirmou o cruzamento inverso do RSI14 em 50; "
                    "encerrar integralmente a posicao antes de permitir a "
                    "entrada inicial oposta."
                ),
                extreme_armed=False,
                **common,
            )

    if (
        reentry_position
        and normalized_side == "BUY"
        and rsi14 <= MODEL_8_RSI_BUY_FILTER
    ):
        return Model8ExitDecision(
            action="FULL_EXIT",
            status="M8_REENTRY_EXIT_RSI50_CRUZOU_PARA_BAIXO_BUY",
            reason=(
                "Posicao de reentrada BUY: candle M5 fechou com RSI14 em 50 ou "
                "abaixo; setup perdeu validade e deve encerrar integralmente."
            ),
            extreme_armed=False,
            **common,
        )
    if (
        reentry_position
        and normalized_side == "SELL"
        and rsi14 >= MODEL_8_RSI_SELL_FILTER
    ):
        return Model8ExitDecision(
            action="FULL_EXIT",
            status="M8_REENTRY_EXIT_RSI50_CRUZOU_PARA_CIMA_SELL",
            reason=(
                "Posicao de reentrada SELL: candle M5 fechou com RSI14 em 50 ou "
                "acima; setup perdeu validade e deve encerrar integralmente."
            ),
            extreme_armed=False,
            **common,
        )

    if normalized_side == "BUY":
        crossed_down_from_70 = (
            previous_rsi14 >= MODEL_8_RSI_BUY_EXIT
            and rsi14 < MODEL_8_RSI_BUY_EXIT
        )
        if crossed_down_from_70:
            return Model8ExitDecision(
                action="FULL_EXIT",
                status="M8_EXIT_RSI70_CRUZOU_PARA_BAIXO_BUY",
                reason=(
                    "Candle M5 fechou confirmando RSI14 de 70 ou mais para "
                    "abaixo de 70; encerrar integralmente BUY."
                ),
                extreme_armed=False,
                **common,
            )
        return Model8ExitDecision(
            action="HOLD_POSITION",
            status="M8_HOLD_BUY",
            reason=(
                "Nao houve cruzamento confirmado do RSI14 de 70 para baixo"
                + (
                    " nem inversao de 50 contra o BUY"
                    if rsi50_inversion_exit_enabled
                    else ""
                )
                + "; a regra SMA20/SMA50 aplicavel nao determinou saida."
            ),
            extreme_armed=rsi14 >= MODEL_8_RSI_BUY_EXIT,
            **common,
        )

    crossed_up_from_30 = (
        previous_rsi14 <= MODEL_8_RSI_SELL_EXIT
        and rsi14 > MODEL_8_RSI_SELL_EXIT
    )
    if crossed_up_from_30:
        return Model8ExitDecision(
            action="FULL_EXIT",
            status="M8_EXIT_RSI30_CRUZOU_PARA_CIMA_SELL",
            reason=(
                "Candle M5 fechou confirmando RSI14 de 30 ou menos para "
                "acima de 30; encerrar integralmente SELL."
            ),
            extreme_armed=False,
            **common,
        )
    return Model8ExitDecision(
        action="HOLD_POSITION",
        status="M8_HOLD_SELL",
        reason=(
            "Nao houve cruzamento confirmado do RSI14 de 30 para cima"
            + (
                " nem inversao de 50 contra o SELL"
                if rsi50_inversion_exit_enabled
                else ""
            )
            + "; a regra SMA20/SMA50 aplicavel nao determinou saida."
        ),
        extreme_armed=rsi14 <= MODEL_8_RSI_SELL_EXIT,
        **common,
    )


def evaluate_model8_native_exit(
    snapshot: MT5NativeM5IndicatorSnapshot,
    side: str,
    *,
    reentry_position: bool = False,
    sma_inversion_exit_enabled: bool = True,
) -> Model8ExitDecision:
    """Saida M8-M17 pelo mesmo buffer nativo fechado usado na entrada."""
    normalized_side = str(side or "").upper()
    common = {
        "closed_candle_time": snapshot.closed_candle_time,
        "sma20": snapshot.sma20,
        "sma50": snapshot.sma50,
        "rsi14": snapshot.rsi14,
        "previous_rsi14": snapshot.previous_rsi14,
        "indicator_source": snapshot.indicator_source,
        "indicator_generated_at": snapshot.generated_at,
    }
    if (
        sma_inversion_exit_enabled
        and normalized_side == "BUY"
        and snapshot.sma20 <= snapshot.sma50
    ):
        return Model8ExitDecision(
            "FULL_EXIT", "M8_EXIT_INVERSAO_SMA_BUY",
            "MT5 nativo: SMA20 deixou de ficar acima da SMA50; fechar BUY.",
            False, **common,
        )
    if (
        sma_inversion_exit_enabled
        and normalized_side == "SELL"
        and snapshot.sma20 >= snapshot.sma50
    ):
        return Model8ExitDecision(
            "FULL_EXIT", "M8_EXIT_INVERSAO_SMA_SELL",
            "MT5 nativo: SMA20 deixou de ficar abaixo da SMA50; fechar SELL.",
            False, **common,
        )
    if normalized_side not in {"BUY", "SELL"}:
        return Model8ExitDecision(
            "HOLD_POSITION", "M8_EXIT_LADO_INVALIDO",
            "Lado da posicao invalido; nenhuma acao executada.",
            False, **common,
        )
    if reentry_position and normalized_side == "BUY" and snapshot.rsi14 <= 50.0:
        return Model8ExitDecision(
            "FULL_EXIT", "M8_REENTRY_EXIT_RSI50_CRUZOU_PARA_BAIXO_BUY",
            "MT5 nativo: reentrada BUY perdeu a condicao RSI14 acima de 50.",
            False, **common,
        )
    if reentry_position and normalized_side == "SELL" and snapshot.rsi14 >= 50.0:
        return Model8ExitDecision(
            "FULL_EXIT", "M8_REENTRY_EXIT_RSI50_CRUZOU_PARA_CIMA_SELL",
            "MT5 nativo: reentrada SELL perdeu a condicao RSI14 abaixo de 50.",
            False, **common,
        )
    if normalized_side == "BUY" and (
        snapshot.previous_rsi14 >= 70.0 and snapshot.rsi14 < 70.0
    ):
        return Model8ExitDecision(
            "FULL_EXIT", "M8_EXIT_RSI70_CRUZOU_PARA_BAIXO_BUY",
            "MT5 nativo: candle M5 confirmou RSI14 cruzando 70 para baixo.",
            False, **common,
        )
    if normalized_side == "SELL" and (
        snapshot.previous_rsi14 <= 30.0 and snapshot.rsi14 > 30.0
    ):
        return Model8ExitDecision(
            "FULL_EXIT", "M8_EXIT_RSI30_CRUZOU_PARA_CIMA_SELL",
            "MT5 nativo: candle M5 confirmou RSI14 cruzando 30 para cima.",
            False, **common,
        )
    return Model8ExitDecision(
        "HOLD_POSITION",
        f"M8_HOLD_{normalized_side}",
        "MT5 nativo: tendencia e RSI nao confirmaram Full Exit.",
        snapshot.rsi14 >= 70.0 if normalized_side == "BUY" else snapshot.rsi14 <= 30.0,
        **common,
    )


def model8_parameters() -> dict[str, object]:
    """Parametros congelados para plano, provider, UI e auditoria."""
    return {
        "symbol": MODEL_8_SYMBOL,
        "timeframe": MODEL_8_TIMEFRAME,
        "sma_fast": MODEL_8_SMA_FAST,
        "sma_slow": MODEL_8_SMA_SLOW,
        "rsi_period": MODEL_8_RSI_PERIOD,
        "lookback_candles": OPERATIONAL_INDICATOR_CLOSED_CANDLES,
        "raw_candles_requested": MODEL_8_LOOKBACK_CANDLES,
        "buy_rsi_filter": MODEL_8_RSI_BUY_FILTER,
        "sell_rsi_filter": MODEL_8_RSI_SELL_FILTER,
        "buy_exit_zone": MODEL_8_RSI_BUY_EXIT,
        "sell_exit_zone": MODEL_8_RSI_SELL_EXIT,
        "entry_order_type": MODEL_8_ENTRY_ORDER_TYPE,
        "initial_entry_requires_fresh_sma_cross": True,
        "initial_buy_cross": "PREVIOUS_SMA20<=PREVIOUS_SMA50_AND_CLOSED_SMA20>SMA50",
        "initial_sell_cross": "PREVIOUS_SMA20>=PREVIOUS_SMA50_AND_CLOSED_SMA20<SMA50",
        "reentry_order_type": MODEL_8_REENTRY_ORDER_TYPE,
        "buy_reentry_trigger": "PREVIOUS_CLOSED_M5_HIGH_EXACT",
        "sell_reentry_trigger": "PREVIOUS_CLOSED_M5_LOW_EXACT",
        "reentry_requires_opposite_pullback_structure": True,
        "reentry_pullback_candles": MODEL_8_REENTRY_PULLBACK_CANDLES,
        "buy_reentry_pullback": "TWO_CLOSED_M5_LOWER_HIGHS_AND_LOWER_LOWS",
        "sell_reentry_pullback": "TWO_CLOSED_M5_HIGHER_HIGHS_AND_HIGHER_LOWS",
        "reentry_buy_structural_target": "LAST_CONFIRMED_M5_SWING_HIGH",
        "reentry_sell_structural_target": "LAST_CONFIRMED_M5_SWING_LOW",
        "reentry_buy_rsi_filter": "CLOSED_RSI14>50",
        "reentry_sell_rsi_filter": "CLOSED_RSI14<50",
        "entry_level": "MARKET_ONLY_ON_FRESH_CLOSED_SMA20_50_CROSS_WITH_RSI50",
        "reentries_unlimited_while_trend_valid": True,
        "swing_left": MODEL_8_SWING_LEFT,
        "swing_right": MODEL_8_SWING_RIGHT,
        "stop_buffer": MODEL_8_STOP_BUFFER,
        "take_profit_enabled": False,
        "reentry_take_profit_enabled": True,
        "reentry_take_profit_mode": "LAST_CONFIRMED_M5_SWING_BEFORE_PULLBACK",
        "full_exit_enabled": True,
        "trend_invalidation_exit": True,
        "buy_full_exit_cross": "PREVIOUS_RSI14>=70_AND_CLOSED_RSI14<70",
        "sell_full_exit_cross": "PREVIOUS_RSI14<=30_AND_CLOSED_RSI14>30",
        "rsi_exit_requires_closed_m5_confirmation": True,
        "reentry_buy_full_exit": "CLOSED_RSI14<=50",
        "reentry_sell_full_exit": "CLOSED_RSI14>=50",
        "pending_stop_validity": "ONE_M5_CANDLE",
        "pending_stop_reposition": "EACH_NEW_CLOSED_M5_CANDLE",
    }


def load_model8_runtime_state(
    path: Path | None = None,
    *,
    operational_model: str = MODEL_8_ID,
) -> dict[str, Any]:
    """Le o estado isolado de entrada/reentrada de cada modelo M8-M12."""
    state_path = path or _xau_runtime_state_path(operational_model)
    with _MODEL_8_STATE_LOCK:
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return dict(payload) if isinstance(payload, dict) else {}


def update_model8_runtime_state(
    *,
    entry_intent_side: str | None = None,
    entry_intent_kind: str | None = None,
    last_exit_status: str | None = None,
    last_exit_reason: str | None = None,
    signal_cycle_side: str | None = None,
    initial_entry_consumed: bool | None = None,
    reentry_consumed: bool | None = None,
    last_entry_kind: str | None = None,
    path: Path | None = None,
    operational_model: str = MODEL_8_ID,
    symbol: str = MODEL_8_SYMBOL,
) -> dict[str, Any]:
    """Atualiza o estado isolado de M8-M12 por escrita atomica."""
    state_path = path or _xau_runtime_state_path(operational_model)
    with _MODEL_8_STATE_LOCK:
        state = load_model8_runtime_state(
            state_path,
            operational_model=operational_model,
        )
        before = dict(state)
        if entry_intent_side is not None:
            normalized = str(entry_intent_side or "").upper()
            state["entry_intent_side"] = normalized if normalized in {"BUY", "SELL"} else ""
        if entry_intent_kind is not None:
            state["entry_intent_kind"] = str(entry_intent_kind or "").upper()
        if last_exit_status is not None:
            state["last_exit_status"] = str(last_exit_status or "")
        if last_exit_reason is not None:
            state["last_exit_reason"] = str(last_exit_reason or "")
        if signal_cycle_side is not None:
            normalized = str(signal_cycle_side or "").upper()
            state["signal_cycle_side"] = (
                normalized if normalized in {"BUY", "SELL"} else ""
            )
        if initial_entry_consumed is not None:
            state["initial_entry_consumed"] = bool(initial_entry_consumed)
        if reentry_consumed is not None:
            state["reentry_consumed"] = bool(reentry_consumed)
        if last_entry_kind is not None:
            state["last_entry_kind"] = str(last_entry_kind or "").upper()
        if state == before:
            return state
        state.update(
            {
                "symbol": str(symbol or MODEL_8_SYMBOL).upper(),
                "timeframe": MODEL_8_TIMEFRAME,
                "operational_model": str(operational_model or MODEL_8_ID).upper(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        temporary = state_path.with_name(
            f".{state_path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temporary, state_path)
        except OSError:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        return state


def _xau_runtime_state_path(operational_model: str) -> Path:
    normalized = str(operational_model or MODEL_8_ID).upper()
    try:
        number = int(normalized.split("_", 2)[1])
    except (IndexError, ValueError):
        number = 8
    if number not in {8, 9, 10, 11, 12, 18, 19, 20, 21, 22}:
        number = 8
    return Path(".traderia") / f"model{number}_runtime_state.json"


def _reentry_pullback_structure(
    rows: list[object],
    direction: str,
) -> tuple[bool, str]:
    """Confirma o recuo oposto nos dois ultimos candles M5 fechados."""
    if len(rows) < MODEL_8_REENTRY_PULLBACK_CANDLES:
        return False, "M8 reentrada aguarda dois candles M5 fechados para o recuo."
    previous = rows[-2]
    latest = rows[-1]
    previous_high = _candle_value(previous, "high")
    previous_low = _candle_value(previous, "low")
    latest_high = _candle_value(latest, "high")
    latest_low = _candle_value(latest, "low")
    if None in {previous_high, previous_low, latest_high, latest_low}:
        return False, "M8 reentrada recebeu maxima/minima M5 invalida."
    if direction == "SELL":
        confirmed = (
            float(latest_high) > float(previous_high)
            and float(latest_low) > float(previous_low)
        )
        description = "maxima e minima ascendentes"
    else:
        confirmed = (
            float(latest_high) < float(previous_high)
            and float(latest_low) < float(previous_low)
        )
        description = "maxima e minima descendentes"
    if confirmed:
        return True, f"Recuo M5 confirmado: {description}."
    trigger = "SELL STOP na minima" if direction == "SELL" else "BUY STOP na maxima"
    return False, (
        f"M8 reentrada aguarda recuo oposto com {description} em dois candles "
        f"M5 fechados; depois armara {trigger} do ultimo candle fechado."
    )


def _last_confirmed_swing(
    rows: list[object],
    direction: str,
) -> tuple[float | None, str]:
    field = "low" if direction == "BUY" else "high"
    values = [_candle_value(row, field) for row in rows]
    if any(value is None for value in values):
        return None, "N/D"
    parsed = [float(value) for value in values if value is not None]
    left = MODEL_8_SWING_LEFT
    right = MODEL_8_SWING_RIGHT
    for index in range(len(parsed) - right - 1, left - 1, -1):
        value = parsed[index]
        neighbors_left = parsed[index - left : index]
        neighbors_right = parsed[index + 1 : index + 1 + right]
        if field == "low":
            confirmed = all(value < item for item in neighbors_left) and all(
                value <= item for item in neighbors_right
            )
        else:
            confirmed = all(value > item for item in neighbors_left) and all(
                value >= item for item in neighbors_right
            )
        if confirmed:
            return value, _candle_time(rows[index])
    return None, "N/D"


def _pullback_origin_target(
    rows: list[object],
    direction: str,
) -> tuple[float | None, str]:
    """Extremo favoravel imediatamente anterior ao recuo de reentrada."""
    window_size = MODEL_8_REENTRY_PULLBACK_CANDLES + 1
    if len(rows) < window_size:
        return None, "N/D"
    field = "high" if str(direction or "").upper() == "BUY" else "low"
    candidates: list[tuple[float, str]] = []
    for row in rows[-window_size:]:
        value = _candle_value(row, field)
        if value is None:
            return None, "N/D"
        candidates.append((float(value), _candle_time(row)))
    return (
        max(candidates, key=lambda item: item[0])
        if field == "high"
        else min(candidates, key=lambda item: item[0])
    )


def _sma(values: list[float], period: int) -> float:
    if len(values) < period:
        return 0.0
    return sum(values[-period:]) / float(period)


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


def _candle_value(candle: object, field: str) -> float | None:
    aliases = {
        "open": ("open", "abertura"),
        "high": ("high", "maxima"),
        "low": ("low", "minima"),
        "close": ("close", "fechamento"),
    }
    for name in aliases.get(field, (field,)):
        value: Any
        if isinstance(candle, dict):
            value = candle.get(name)
        else:
            value = getattr(candle, name, None)
            if value is None:
                try:
                    value = candle[name]  # type: ignore[index]
                except (KeyError, IndexError, TypeError, ValueError):
                    value = None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0.0:
            return parsed
    return None


def _candle_time(candle: object) -> str:
    # Registros numpy/MT5 expõem ``.data`` como memoryview. Ler atributos antes
    # do campo indexado fazia esse endereço de memória virar a identidade do
    # candle no estado persistido, quebrando idempotência e o bloqueio de
    # reentrada após saída extrema.
    for name in ("time", "datetime", "timestamp", "data"):
        if isinstance(candle, dict):
            value = candle.get(name)
        else:
            try:
                value = candle[name]  # type: ignore[index]
            except (KeyError, IndexError, TypeError, ValueError):
                value = getattr(candle, name, None)
        if value in (None, "") or isinstance(value, memoryview):
            continue
        if isinstance(value, datetime):
            normalized = value
            if normalized.tzinfo is None:
                normalized = normalized.replace(tzinfo=timezone.utc)
            return normalized.isoformat()
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(
                    float(value), tz=timezone.utc
                ).isoformat()
            except (OverflowError, OSError, ValueError):
                continue
        return str(value)
    return "N/D"
