"""Compara no Lab a continuidade M26 confirmada pelo fechamento do candle."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import application.model26_xau_m5_smart_money as model26
import scripts.research_model26_m5_5000 as baseline


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = (
    ROOT
    / ".traderia"
    / "research"
    / "model26_continuation_close_m5_5000_backtest.json"
)
OUTPUT_MD = (
    ROOT
    / ".traderia"
    / "research"
    / "model26_continuation_close_m5_5000_backtest.md"
)
VARIANT_ID = "M26_LAB_CONTINUATION_CLOSE_MARKET_V1"


def _continuation_after_closed_confirmation(
    bars: list[model26._Bar],
    common: dict[str, object],
) -> model26.Model26Decision | None:
    """Entra no proximo mercado somente apos o candle de retomada fechar."""
    if len(bars) < model26.MODEL_26_RSI_PERIOD + 1:
        return None

    confirmation = bars[-1]
    pause = bars[-2]
    rsi14 = float(common.get("rsi14") or 50.0)

    if (
        confirmation.bullish
        and pause.bearish
        and confirmation.close > pause.high
    ):
        direction = "BUY"
        trend_test = lambda bar: bar.bullish
        stop = pause.low - model26.MODEL_26_STOP_BUFFER
        rsi_allowed = (
            model26.MODEL_26_RSI_BUY_MIN
            < rsi14
            <= model26.MODEL_26_RSI_BUY_MAX
        )
    elif (
        confirmation.bearish
        and pause.bullish
        and confirmation.close < pause.low
    ):
        direction = "SELL"
        trend_test = lambda bar: bar.bearish
        stop = pause.high + model26.MODEL_26_STOP_BUFFER
        rsi_allowed = (
            model26.MODEL_26_RSI_SELL_MIN
            <= rsi14
            < model26.MODEL_26_RSI_SELL_MAX
        )
    else:
        return None

    if not rsi_allowed:
        return None

    index = len(bars) - 3
    trend_count = 0
    while index >= 0 and trend_test(bars[index]):
        trend_count += 1
        index -= 1
    if trend_count < model26.MODEL_26_MIN_TREND_CANDLES:
        return None

    return model26.Model26Decision(
        direction=direction,
        status=f"M26_LAB_CONTINUATION_{direction}_MARKET_APOS_FECHAMENTO",
        reason=(
            f"{direction}: {trend_count} candle(s) a favor + pausa oposta + "
            f"candle de retomada fechado alem da pausa; RSI14={rsi14:.2f}; "
            "entrada no proximo mercado e SL alem da extremidade da pausa."
        ),
        signal_kind="CONTINUATION",
        entry_order_type="MARKET",
        entry_price=confirmation.close,
        initial_stop=stop,
        target=0.0,
        last_swing_price=pause.low if direction == "BUY" else pause.high,
        last_swing_time=pause.time,
        pullback_candles=1,
        trend_candles_before_pullback=trend_count,
        setup_id=f"M26_LAB|CONTINUATION_CLOSE|{direction}|{confirmation.time}",
        **common,
    )


def _markdown(result: dict[str, object]) -> str:
    text = baseline._markdown(result)
    marker = "## Resultado bruto"
    explanation = "\n".join(
        (
            "## Variante simulada",
            "",
            "- Somente a rota `CONTINUATION` foi alterada.",
            "- BUY: candle de retomada verde deve fechar acima da maxima da pausa vermelha.",
            "- SELL: candle de retomada vermelho deve fechar abaixo da minima da pausa verde.",
            "- Entrada: mercado na abertura seguinte ao candle confirmador fechado.",
            "- SL: preservado alem da extremidade oposta da vela de pausa.",
            "- Lateralizacao, exaustao e todas as saidas permanecem iguais ao M26 atual.",
            "",
        )
    )
    return text.replace(marker, explanation + marker, 1).replace(
        "# Lab M26 - XAUUSD M5 - 5.000 velas",
        "# Lab M26 - continuidade apos fechamento - XAUUSD M5 - 5.000 velas",
        1,
    )


def run() -> dict[str, object]:
    original = model26._continuation_decision
    model26._continuation_decision = _continuation_after_closed_confirmation
    try:
        result = baseline.run()
    finally:
        model26._continuation_decision = original

    result["schema_version"] = "model26_lab_continuation_close_backtest_v1"
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["variant"] = {
        "id": VARIANT_ID,
        "production_changed": False,
        "changed_route": "CONTINUATION",
        "entry_timing": "NEXT_MARKET_AFTER_CONFIRMATION_CANDLE_CLOSE",
        "confirmation_buy": "GREEN_CLOSE_ABOVE_RED_PAUSE_HIGH",
        "confirmation_sell": "RED_CLOSE_BELOW_GREEN_PAUSE_LOW",
    }
    return result


def main() -> None:
    result = run()
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(result, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    OUTPUT_MD.write_text(_markdown(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "json": str(OUTPUT_JSON.resolve()),
                "markdown": str(OUTPUT_MD.resolve()),
                "variant": result["variant"],
                "overall": result["overall"],
                "by_route": result["by_route"],
                "exit_reasons": result["exit_reasons"],
                "counters": result["counters"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
