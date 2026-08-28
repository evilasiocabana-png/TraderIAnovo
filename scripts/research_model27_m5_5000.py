"""Backtest local do M27, espelho RR1 dos gatilhos atuais do M26."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from application.model26_xau_m5_smart_money import (
    MODEL_26_CONTRACT_FINGERPRINT,
    MODEL_26_CONTRACT_VERSION,
    Model26Decision,
    evaluate_model26_entries,
    evolve_model26_exhaustion_state,
)
from application.model27_mirror_m26 import (
    MODEL_27_CONTRACT_VERSION,
    MODEL_27_VOLUME,
    mirror_model26_geometry,
    mirror_model26_order_type,
)
from infrastructure.research.multi_ea_local_data_adapter import MultiEALocalDataAdapter
from scripts.research_model26_m5_5000 import (
    CONTRACT_SIZE,
    PendingOrder,
    Position,
    Trade,
    _close_trade,
    _consume_exhaustion,
    _fill_price,
    _intrabar_exit,
    _metrics,
    _snapshot,
    _time,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / ".traderia" / "research" / "model27_m5_5000_backtest.json"
OUTPUT_MD = ROOT / ".traderia" / "research" / "model27_m5_5000_backtest.md"


def _mirror_order(decision: Model26Decision) -> PendingOrder:
    geometry = mirror_model26_geometry(
        decision.direction,
        decision.entry_price,
        decision.initial_stop,
    )
    return PendingOrder(
        route=str(decision.signal_kind),
        direction=geometry.direction,
        order_type=mirror_model26_order_type(decision.entry_order_type),
        entry=geometry.entry_price,
        stop=geometry.stop,
        target=geometry.target,
        volume=MODEL_27_VOLUME,
        signal_time=str(decision.closed_candle_time),
        setup_id=f"M27|{decision.signal_kind}|{geometry.direction}|{decision.closed_candle_time}",
    )


def _schedule(
    decisions: tuple[Model26Decision, ...],
    positions: dict[str, Position],
    pending: dict[str, PendingOrder],
    counters: Counter[str],
) -> list[PendingOrder]:
    markets: list[PendingOrder] = []
    ready_routes: set[str] = set()
    for decision in decisions:
        if not decision.ready:
            continue
        order = _mirror_order(decision)
        ready_routes.add(order.route)
        counters[f"signals_{order.route}"] += 1
        if order.route in positions:
            counters[f"blocked_open_{order.route}"] += 1
            continue
        if order.order_type == "MARKET":
            markets.append(order)
            pending.pop(order.route, None)
        else:
            if order.route in pending:
                counters[f"pending_replaced_{order.route}"] += 1
            pending[order.route] = order
    for route in list(pending):
        if route not in ready_routes:
            pending.pop(route, None)
            counters[f"pending_expired_{route}"] += 1
    return markets


def run() -> dict[str, Any]:
    adapter = MultiEALocalDataAdapter()
    candles = adapter.load_operational_candles("XAUUSD", "M5", limit=5000)
    if len(candles) != 5000:
        raise RuntimeError(f"Esperadas 5000 velas XAUUSD/M5; recebidas {len(candles)}.")

    positions: dict[str, Position] = {}
    pending: dict[str, PendingOrder] = {}
    trades: list[Trade] = []
    counters: Counter[str] = Counter()
    exhaustion_state: dict[str, Any] = {}

    initial_snapshot = _snapshot(candles, 199)
    exhaustion_state = evolve_model26_exhaustion_state(initial_snapshot, exhaustion_state)
    decisions = evaluate_model26_entries(initial_snapshot, exhaustion_state=exhaustion_state)
    market_next = _schedule(decisions, positions, pending, counters)

    for execution_index in range(200, len(candles)):
        bar = candles[execution_index]
        bar_time = _time(bar)

        for order in market_next:
            if order.route in positions:
                counters[f"market_blocked_open_{order.route}"] += 1
                continue
            fill = float(bar.open)
            valid = order.stop < fill < order.target if order.direction == "BUY" else order.target < fill < order.stop
            if not valid:
                counters[f"market_invalid_geometry_{order.route}"] += 1
                continue
            positions[order.route] = Position(
                route=order.route,
                direction=order.direction,
                entry=fill,
                stop=order.stop,
                initial_stop=order.stop,
                target=order.target,
                volume=order.volume,
                signal_time=order.signal_time,
                entry_time=bar_time,
                setup_id=order.setup_id,
            )
            counters[f"fills_{order.route}"] += 1
            if order.route == "EXHAUSTION":
                # Consumo no aceite evita reaproveitar indefinidamente o mesmo
                # cruzamento extremo no estudo historico.
                source_side = "SELL" if order.direction == "BUY" else "BUY"
                _consume_exhaustion(exhaustion_state, source_side)
        market_next = []

        for route, order in list(pending.items()):
            if route in positions:
                pending.pop(route, None)
                continue
            fill = _fill_price(order, bar)
            if fill is None:
                continue
            valid = order.stop < fill < order.target if order.direction == "BUY" else order.target < fill < order.stop
            if not valid:
                counters[f"pending_invalid_geometry_{route}"] += 1
                pending.pop(route, None)
                continue
            positions[route] = Position(
                route=route,
                direction=order.direction,
                entry=fill,
                stop=order.stop,
                initial_stop=order.stop,
                target=order.target,
                volume=order.volume,
                signal_time=order.signal_time,
                entry_time=bar_time,
                setup_id=order.setup_id,
            )
            pending.pop(route, None)
            counters[f"fills_{route}"] += 1

        for route, position in list(positions.items()):
            position.bars_held += 1
            hit = _intrabar_exit(position, bar)
            if hit is None:
                continue
            exit_price, reason = hit
            trades.append(
                _close_trade(
                    position,
                    exit_price=exit_price,
                    exit_time=bar_time,
                    reason=reason,
                )
            )
            positions.pop(route, None)

        if execution_index >= len(candles) - 1:
            break
        snapshot = _snapshot(candles, execution_index)
        exhaustion_state = evolve_model26_exhaustion_state(snapshot, exhaustion_state)
        decisions = evaluate_model26_entries(snapshot, exhaustion_state=exhaustion_state)
        market_next = _schedule(decisions, positions, pending, counters)

    grouped: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        grouped[trade.route].append(trade)
    open_mark = sum(
        ((float(candles[-1].close) - position.entry) if position.direction == "BUY" else (position.entry - float(candles[-1].close)))
        * CONTRACT_SIZE
        * position.volume
        for position in positions.values()
    )
    return {
        "schema_version": "model27_lab_backtest_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "M27",
        "contract_version": MODEL_27_CONTRACT_VERSION,
        "source_contract_version": MODEL_26_CONTRACT_VERSION,
        "source_contract_fingerprint": MODEL_26_CONTRACT_FINGERPRINT,
        "dataset": {
            "source": str(adapter.operational_database_path.resolve()),
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "candles": len(candles),
            "first_candle": _time(candles[0]),
            "last_candle": _time(candles[-1]),
            "warmup_closed_candles": 200,
            "evaluated_execution_candles": len(candles) - 200,
        },
        "execution_assumptions": {
            "data_access": "LOCAL_SQLITE_READ_ONLY",
            "entry_source": "EXACT_M26_SIGNALS_MIRRORED",
            "direction": "OPPOSITE_TO_M26",
            "target": "SOURCE_M26_STOP",
            "stop": "RR1_OPPOSITE_SIDE",
            "volume": MODEL_27_VOLUME,
            "decision_timing": "CLOSED_CANDLE_ONLY",
            "pending_validity": "REPLACED_EACH_NEW_CLOSED_CANDLE_PER_ROUTE",
            "same_candle_collision": "STOP_FIRST_CONSERVATIVE",
            "route_overlap": "ONE_POSITION_PER_ROUTE; ROUTES_CAN_COEXIST",
            "open_trade_at_end": "MARK_TO_MARKET_EXCLUDED_FROM_CLOSED_METRICS",
            "costs": "GROSS_WITHOUT_SPREAD_COMMISSION_SWAP_SLIPPAGE",
            "xau_contract_size": CONTRACT_SIZE,
        },
        "overall": _metrics(trades),
        "by_route": {route: _metrics(items) for route, items in sorted(grouped.items())},
        "exit_reasons": dict(Counter(trade.exit_reason for trade in trades)),
        "counters": dict(sorted(counters.items())),
        "open_positions_at_end": [asdict(position) for position in positions.values()],
        "open_mark_to_market_gross_usd": open_mark,
        "pending_orders_at_end": [asdict(order) for order in pending.values()],
        "trades": [asdict(trade) for trade in trades],
    }


def _fmt(value: Any) -> str:
    return "N/D" if value is None else f"{value:.2f}" if isinstance(value, float) else str(value)


def _markdown(result: dict[str, Any]) -> str:
    data, overall = result["dataset"], result["overall"]
    lines = [
        "# Lab M27 - espelho do M26 - XAUUSD M5 - 5.000 velas",
        "",
        f"Gerado em: `{result['generated_at']}`",
        f"Contrato M27: `{result['contract_version']}`",
        f"Fonte M26: `{result['source_contract_version']}` / `{result['source_contract_fingerprint']}`",
        "",
        "## Amostra",
        "",
        f"- Fonte local: `{data['source']}`",
        f"- Velas: **{data['candles']}**",
        f"- Periodo UTC: `{data['first_candle']}` ate `{data['last_candle']}`",
        f"- Velas avaliadas depois do aquecimento: {data['evaluated_execution_candles']}",
        "",
        "## Resultado bruto",
        "",
        f"- Trades encerrados: **{overall['trades']}**",
        f"- Vitorias / derrotas / zero: **{overall['wins']} / {overall['losses']} / {overall['breakeven']}**",
        f"- Taxa de acerto: **{overall['win_rate'] * 100:.2f}%**",
        f"- Resultado bruto teorico: **US$ {_fmt(overall['net_gross_usd'])}**",
        f"- Profit factor: **{_fmt(overall['profit_factor'])}**",
        f"- Expectativa: **US$ {_fmt(overall['expectancy_usd'])} por trade**",
        f"- Drawdown maximo fechado: **US$ {_fmt(overall['max_drawdown_usd'])}**",
        f"- R medio / mediano: **{_fmt(overall['average_r'])} / {_fmt(overall['median_r'])}**",
        "",
        "## Por rota espelhada",
        "",
        "| Rota fonte | Trades | Win rate | Liquido bruto USD | PF | DD USD | R medio |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for route, metrics in result["by_route"].items():
        lines.append(
            f"| {route} | {metrics['trades']} | {metrics['win_rate'] * 100:.2f}% | "
            f"{_fmt(metrics['net_gross_usd'])} | {_fmt(metrics['profit_factor'])} | "
            f"{_fmt(metrics['max_drawdown_usd'])} | {_fmt(metrics['average_r'])} |"
        )
    lines.extend(
        (
            "",
            "## Limites do ensaio",
            "",
            "- Entradas derivadas dos mesmos sinais M26 e espelhadas pelo contrato M27.",
            "- SL e TP fixos em RR 1:1; nao usa o Position Manager dinamico do M26.",
            "- Resultado bruto, sem spread, comissao, swap ou slippage.",
            "- Colisao de SL e TP na mesma vela usa SL primeiro.",
            "- Janela deslizante de 200 velas fechadas, sem olhar o futuro.",
            "- Resultado historico nao constitui aprovacao para conta real.",
            "",
        )
    )
    return "\n".join(lines)


def main() -> None:
    result = run()
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    OUTPUT_MD.write_text(_markdown(result), encoding="utf-8")
    print(json.dumps({
        "json": str(OUTPUT_JSON.resolve()),
        "markdown": str(OUTPUT_MD.resolve()),
        "overall": result["overall"],
        "by_route": result["by_route"],
        "exit_reasons": result["exit_reasons"],
        "counters": result["counters"],
        "open_positions_at_end": len(result["open_positions_at_end"]),
        "pending_orders_at_end": len(result["pending_orders_at_end"]),
    }, indent=2))


if __name__ == "__main__":
    main()
