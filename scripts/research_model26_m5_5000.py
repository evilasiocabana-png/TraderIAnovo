"""Backtest local auditavel do contrato operacional M26 em XAUUSD/M5."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import median
from typing import Any

from application.model26_xau_m5_smart_money import (
    MODEL_26_CONTRACT_FINGERPRINT,
    MODEL_26_CONTRACT_VERSION,
    MODEL_26_CONTINUATION_VOLUME,
    MODEL_26_LATERALIZATION_VOLUME,
    Model26Decision,
    evaluate_model26_entries,
    evaluate_model26_exit,
    evolve_model26_exhaustion_state,
)
from infrastructure.research.multi_ea_local_data_adapter import (
    MultiEALocalDataAdapter,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / ".traderia" / "research" / "model26_m5_5000_backtest.json"
OUTPUT_MD = ROOT / ".traderia" / "research" / "model26_m5_5000_backtest.md"
CONTRACT_SIZE = 100.0


@dataclass
class PendingOrder:
    route: str
    direction: str
    order_type: str
    entry: float
    stop: float
    target: float
    volume: float
    signal_time: str
    setup_id: str


@dataclass
class Position:
    route: str
    direction: str
    entry: float
    stop: float
    initial_stop: float
    target: float
    volume: float
    signal_time: str
    entry_time: str
    setup_id: str
    bars_held: int = 0


@dataclass
class Trade:
    route: str
    direction: str
    signal_time: str
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    initial_stop: float
    final_stop: float
    target: float
    volume: float
    bars_held: int
    exit_reason: str
    pnl_points: float
    pnl_r: float
    gross_usd: float


def _time(candle: Any) -> str:
    value = getattr(candle, "timestamp", None)
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _volume(route: str) -> float:
    return (
        MODEL_26_LATERALIZATION_VOLUME
        if route == "LATERALIZATION"
        else MODEL_26_CONTINUATION_VOLUME
    )


def _pnl(direction: str, entry: float, exit_price: float) -> float:
    return exit_price - entry if direction == "BUY" else entry - exit_price


def _fill_price(order: PendingOrder, bar: Any) -> float | None:
    if order.order_type == "BUY_STOP" and float(bar.high) >= order.entry:
        return max(order.entry, float(bar.open))
    if order.order_type == "SELL_STOP" and float(bar.low) <= order.entry:
        return min(order.entry, float(bar.open))
    if order.order_type == "BUY_LIMIT" and float(bar.low) <= order.entry:
        return min(order.entry, float(bar.open))
    if order.order_type == "SELL_LIMIT" and float(bar.high) >= order.entry:
        return max(order.entry, float(bar.open))
    return None


def _intrabar_exit(position: Position, bar: Any) -> tuple[float, str] | None:
    low, high = float(bar.low), float(bar.high)
    stop_hit = low <= position.stop if position.direction == "BUY" else high >= position.stop
    target_hit = bool(position.target) and (
        high >= position.target if position.direction == "BUY" else low <= position.target
    )
    if stop_hit:
        return position.stop, "STOP_LOSS_CONSERVATIVE"
    if target_hit:
        return position.target, "TAKE_PROFIT"
    return None


def _close_trade(
    position: Position,
    *,
    exit_price: float,
    exit_time: str,
    reason: str,
) -> Trade:
    points = _pnl(position.direction, position.entry, exit_price)
    risk = abs(position.entry - position.initial_stop)
    return Trade(
        route=position.route,
        direction=position.direction,
        signal_time=position.signal_time,
        entry_time=position.entry_time,
        exit_time=exit_time,
        entry=position.entry,
        exit=exit_price,
        initial_stop=position.initial_stop,
        final_stop=position.stop,
        target=position.target,
        volume=position.volume,
        bars_held=position.bars_held,
        exit_reason=reason,
        pnl_points=points,
        pnl_r=(points / risk) if risk else 0.0,
        gross_usd=points * CONTRACT_SIZE * position.volume,
    )


def _decision_to_order(decision: Model26Decision) -> PendingOrder:
    return PendingOrder(
        route=str(decision.signal_kind),
        direction=str(decision.direction),
        order_type=str(decision.entry_order_type),
        entry=float(decision.entry_price or 0.0),
        stop=float(decision.initial_stop or 0.0),
        target=float(decision.target or 0.0),
        volume=_volume(str(decision.signal_kind)),
        signal_time=str(decision.closed_candle_time),
        setup_id=str(decision.setup_id),
    )


def _consume_exhaustion(state: dict[str, Any], direction: str) -> None:
    prefix = "buy" if direction == "BUY" else "sell"
    state[f"{prefix}_armed"] = False
    state[f"{prefix}_armed_at"] = "N/D"
    state[f"{prefix}_entry_price"] = None
    state[f"{prefix}_initial_stop"] = None


def _snapshot(candles: list[Any], closed_index: int) -> list[Any]:
    # O contrato recebe 200 candles fechados e uma vela corrente, que nao entra
    # no calculo. No historico, a proxima vela ocupa exatamente esse papel.
    return candles[closed_index - 199 : closed_index + 2]


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
        order = _decision_to_order(decision)
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
    # O provider substitui a pendencia por rota a cada fechamento. Se o setup
    # desapareceu no novo candle, a ordem anterior deixa de representar o plano.
    for route in list(pending):
        if route not in ready_routes:
            pending.pop(route, None)
            counters[f"pending_expired_{route}"] += 1
    return markets


def _metrics(trades: list[Trade]) -> dict[str, Any]:
    wins = [trade for trade in trades if trade.gross_usd > 1e-9]
    losses = [trade for trade in trades if trade.gross_usd < -1e-9]
    flat = len(trades) - len(wins) - len(losses)
    gross_profit = sum(trade.gross_usd for trade in wins)
    gross_loss = abs(sum(trade.gross_usd for trade in losses))
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for trade in trades:
        equity += trade.gross_usd
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": flat,
        "win_rate": (len(wins) / len(trades)) if trades else 0.0,
        "gross_profit_usd": gross_profit,
        "gross_loss_usd": gross_loss,
        "net_gross_usd": sum(trade.gross_usd for trade in trades),
        "profit_factor": (gross_profit / gross_loss) if gross_loss else None,
        "max_drawdown_usd": max_drawdown,
        "expectancy_usd": (sum(trade.gross_usd for trade in trades) / len(trades)) if trades else 0.0,
        "median_r": median([trade.pnl_r for trade in trades]) if trades else 0.0,
        "average_r": (sum(trade.pnl_r for trade in trades) / len(trades)) if trades else 0.0,
        "average_bars": (sum(trade.bars_held for trade in trades) / len(trades)) if trades else 0.0,
    }


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
            valid = order.stop < fill if order.direction == "BUY" else order.stop > fill
            if not valid:
                counters[f"market_invalid_stop_{order.route}"] += 1
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
                _consume_exhaustion(exhaustion_state, order.direction)
        market_next = []

        for route, order in list(pending.items()):
            if route in positions:
                pending.pop(route, None)
                continue
            fill = _fill_price(order, bar)
            if fill is None:
                continue
            valid = order.stop < fill if order.direction == "BUY" else order.stop > fill
            if not valid:
                counters[f"pending_invalid_stop_{route}"] += 1
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
        for route, position in list(positions.items()):
            exit_decision = evaluate_model26_exit(
                snapshot,
                position.direction,
                reentry_route=position.route,
                entry_candle_time=position.signal_time,
            )
            if exit_decision.action == "FULL_EXIT":
                trades.append(
                    _close_trade(
                        position,
                        exit_price=float(bar.close),
                        exit_time=bar_time,
                        reason=exit_decision.status,
                    )
                )
                positions.pop(route, None)
                continue
            candidate = exit_decision.candidate_stop
            if candidate is None:
                continue
            candidate = float(candidate)
            better = (
                candidate > position.stop and candidate < float(bar.close)
                if position.direction == "BUY"
                else candidate < position.stop and candidate > float(bar.close)
            )
            if better:
                position.stop = candidate
                counters[f"stop_moves_{route}"] += 1

        exhaustion_state = evolve_model26_exhaustion_state(snapshot, exhaustion_state)
        decisions = evaluate_model26_entries(snapshot, exhaustion_state=exhaustion_state)
        market_next = _schedule(decisions, positions, pending, counters)

    grouped: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        grouped[trade.route].append(trade)
    open_mark = sum(
        _pnl(position.direction, position.entry, float(candles[-1].close))
        * CONTRACT_SIZE
        * position.volume
        for position in positions.values()
    )
    result = {
        "schema_version": "model26_lab_backtest_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "M26",
        "contract_version": MODEL_26_CONTRACT_VERSION,
        "contract_fingerprint": MODEL_26_CONTRACT_FINGERPRINT,
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
            "decision_timing": "CLOSED_CANDLE_ONLY",
            "pending_validity": "REPLACED_EACH_NEW_CLOSED_CANDLE_PER_ROUTE",
            "pending_gap_fill": "NEXT_OPEN_WHEN_OPEN_ALREADY_CROSSED",
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
    return result


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "N/D"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _markdown(result: dict[str, Any]) -> str:
    dataset = result["dataset"]
    overall = result["overall"]
    lines = [
        "# Lab M26 - XAUUSD M5 - 5.000 velas",
        "",
        f"Gerado em: `{result['generated_at']}`",
        f"Contrato: `{result['contract_version']}` / `{result['contract_fingerprint']}`",
        "",
        "## Amostra",
        "",
        f"- Fonte local: `{dataset['source']}`",
        f"- Velas: **{dataset['candles']}**",
        f"- Periodo UTC: `{dataset['first_candle']}` ate `{dataset['last_candle']}`",
        f"- Aquecimento: {dataset['warmup_closed_candles']} velas fechadas",
        f"- Velas avaliadas: {dataset['evaluated_execution_candles']}",
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
        "## Por rota",
        "",
        "| Rota | Trades | Win rate | Liquido bruto USD | PF | DD USD | R medio |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for route, metrics in result["by_route"].items():
        lines.append(
            "| "
            + " | ".join(
                (
                    route,
                    str(metrics["trades"]),
                    f"{metrics['win_rate'] * 100:.2f}%",
                    _fmt(metrics["net_gross_usd"]),
                    _fmt(metrics["profit_factor"]),
                    _fmt(metrics["max_drawdown_usd"]),
                    _fmt(metrics["average_r"]),
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "## Saidas",
            "",
        )
    )
    for reason, count in sorted(result["exit_reasons"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- `{reason}`: {count}")
    lines.extend(
        (
            "",
            "## Limites do ensaio",
            "",
            "- Resultado bruto, sem spread, comissao, swap ou slippage.",
            "- Colisao de SL e TP na mesma vela e tratada de forma conservadora: SL primeiro.",
            "- A janela operacional e deslizante, com 200 velas fechadas e sem olhar o futuro.",
            "- Posicoes ainda abertas no fim nao entram nas metricas fechadas.",
            "- Este relatorio mede o contrato atual; nao promove o setup para conta real.",
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
