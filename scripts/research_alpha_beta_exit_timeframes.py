from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    import MetaTrader5 as mt5
except ImportError as exc:  # pragma: no cover - ambiente local sem MT5
    raise SystemExit(f"MetaTrader5 indisponivel: {exc}") from exc


PAIRS = ("EURUSD", "GBPUSD", "USDCHF", "USDJPY", "EURJPY", "AUDUSD", "NZDUSD", "USDCAD")
ENTRY_TFS = ("M1", "M5", "M15", "M30", "H1")
EXIT_TF_BY_ENTRY_TF = {
    "M1": "M1",
    "M5": "M1",
    "M15": "M1",
    "M30": "M5",
    "H1": "M5",
}
MT5_TFS = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
}
TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60}

BETA_CATALOG = {
    "BETA003": {
        "name": "FIXED_RISK_TARGET",
        "mode": "HOLD",
        "description": "Mantem stop inicial e alvo RR; base de comparacao.",
    },
    "BETA004": {
        "name": "BREAK_EVEN_AFTER_1R",
        "mode": "PROTECT",
        "description": "Move para break-even somente depois de 1R.",
    },
    "BETA005": {
        "name": "ATR_TRAILING_AFTER_1R",
        "mode": "PROTECT",
        "description": "Aciona trailing por ATR depois de 1R; nunca afasta stop.",
    },
    "BETA006": {
        "name": "STRUCTURE_TRAILING_AFTER_1R",
        "mode": "PROTECT",
        "description": "Protege por estrutura/swing depois de 1R.",
    },
    "BETA007": {
        "name": "MOMENTUM_DECAY_FULL_EXIT",
        "mode": "FULL_EXIT",
        "description": "Fecha quando momentum curto vira contra a posicao.",
    },
    "BETA008": {
        "name": "CHANDELIER_ATR_EXIT",
        "mode": "PROTECT",
        "description": "Trailing tipo chandelier baseado em maxima/minima e ATR.",
    },
}


@dataclass(frozen=True)
class Candle:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class AlphaSpec:
    alpha_id: str
    model: str
    parameters: dict[str, object]


@dataclass
class ExitResult:
    beta_id: str
    beta_name: str
    exit_tf: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    avg_r: float = 0.0
    total_r: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_r: float = 0.0
    score: float = 0.0


def ema(values: list[float], period: int) -> list[float | None]:
    if not values or period <= 0:
        return [None] * len(values)
    alpha = 2.0 / (period + 1.0)
    out: list[float | None] = []
    current: float | None = None
    for value in values:
        current = value if current is None else (value * alpha) + (current * (1.0 - alpha))
        out.append(current)
    return out


def atr(candles: list[Candle], period: int = 14) -> list[float | None]:
    trs: list[float] = []
    previous_close: float | None = None
    for candle in candles:
        if previous_close is None:
            tr = candle.high - candle.low
        else:
            tr = max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        trs.append(tr)
        previous_close = candle.close
    out: list[float | None] = []
    current: float | None = None
    for index, tr in enumerate(trs):
        if index + 1 < period:
            out.append(None)
            continue
        if current is None:
            current = sum(trs[index + 1 - period : index + 1]) / period
        else:
            current = ((current * (period - 1)) + tr) / period
        out.append(current)
    return out


def rolling_high(candles: list[Candle], index: int, period: int) -> float:
    start = max(0, index - period)
    return max(c.high for c in candles[start:index]) if index > start else candles[index].high


def rolling_low(candles: list[Candle], index: int, period: int) -> float:
    start = max(0, index - period)
    return min(c.low for c in candles[start:index]) if index > start else candles[index].low


def safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def fetch_candles(symbol: str, timeframe: str, count: int) -> list[Candle]:
    rates = mt5.copy_rates_from_pos(symbol, MT5_TFS[timeframe], 0, count)
    if rates is None:
        return []
    candles = [
        Candle(
            time=int(row["time"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["tick_volume"]),
        )
        for row in rates
    ]
    return sorted(candles, key=lambda item: item.time)


def load_alpha_specs(snapshot_path: Path) -> dict[str, AlphaSpec]:
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    scenarios = data.get("scenario_ranking", [])
    best: dict[str, tuple[tuple[float, float, int], AlphaSpec]] = {}
    for row in scenarios:
        alpha_id = str(row.get("alpha_id") or "").upper()
        if not alpha_id:
            continue
        params = dict(row.get("parameters") or {})
        model = str(row.get("model") or params.get("modelo") or "")
        score = safe_float(row.get("score"), 0.0)
        confidence = safe_float(row.get("lab_confidence"), 0.0)
        approved = 1 if str(row.get("status") or "").upper() == "APROVADO" else 0
        rank = (approved, score, confidence)
        spec = AlphaSpec(alpha_id=alpha_id, model=model, parameters=params)
        if alpha_id not in best or rank > best[alpha_id][0]:
            best[alpha_id] = (rank, spec)
    return {key: value for key, (_, value) in sorted(best.items())}


def load_alpha_contexts(
    snapshot_path: Path,
    *,
    max_contexts_per_alpha: int,
) -> dict[str, list[tuple[str, str]]]:
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    scenarios = data.get("scenario_ranking", [])
    grouped: dict[str, dict[tuple[str, str], tuple[float, float, int]]] = {}
    for row in scenarios:
        if str(row.get("status") or "").upper() != "APROVADO":
            continue
        alpha_id = str(row.get("alpha_id") or "").upper()
        pair = str(row.get("pair") or "").upper()
        timeframe = str(row.get("timeframe") or "").upper()
        if not alpha_id or pair not in PAIRS or timeframe not in ENTRY_TFS:
            continue
        key = (pair, timeframe)
        rank = (
            safe_float(row.get("score"), 0.0),
            safe_float(row.get("lab_confidence"), 0.0),
            int(safe_float((row.get("parameters") or {}).get("rr"), 0.0) * 10),
        )
        alpha_group = grouped.setdefault(alpha_id, {})
        if key not in alpha_group or rank > alpha_group[key]:
            alpha_group[key] = rank
    contexts: dict[str, list[tuple[str, str]]] = {}
    for alpha_id, values in grouped.items():
        ordered = sorted(values.items(), key=lambda item: item[1], reverse=True)
        contexts[alpha_id] = [key for key, _ in ordered[:max_contexts_per_alpha]]
    return contexts


def alpha_signal(
    alpha: AlphaSpec,
    candles: list[Candle],
    index: int,
    ema_fast: list[float | None],
    ema_slow: list[float | None],
    atr_values: list[float | None],
) -> str:
    if index < 60:
        return "WAIT"
    fast = ema_fast[index]
    slow = ema_slow[index]
    if fast is None or slow is None:
        return "WAIT"
    close = candles[index].close
    previous = candles[index - 14].close
    momentum = close - previous
    atr_now = atr_values[index] or 0.0
    if atr_now <= 0.0:
        return "WAIT"
    model = alpha.model.upper()
    alpha_id = alpha.alpha_id
    trend_buy = fast > slow and momentum > 0.0
    trend_sell = fast < slow and momentum < 0.0
    if model in {"TREND_MOMENTUM", "ADX_TREND_STRENGTH", "MULTI_TIMEFRAME_ALIGNMENT"}:
        if trend_buy:
            return "BUY"
        if trend_sell:
            return "SELL"
    if model in {"TREND_PULLBACK"}:
        if fast > slow and candles[index].low <= fast <= candles[index].high and close > fast:
            return "BUY"
        if fast < slow and candles[index].low <= fast <= candles[index].high and close < fast:
            return "SELL"
    if model in {"BREAKOUT_CONSOLIDATION", "DONCHIAN_BREAKOUT", "DONCHIAN_STRUCTURE_BREAKOUT"}:
        period = int(safe_float(alpha.parameters.get("donchian_period"), 20.0))
        if close > rolling_high(candles, index, period):
            return "BUY"
        if close < rolling_low(candles, index, period):
            return "SELL"
    if model in {"MACD_MOMENTUM_SHIFT"}:
        prev_fast = ema_fast[index - 3] or fast
        prev_slow = ema_slow[index - 3] or slow
        if prev_fast <= prev_slow and fast > slow and momentum > 0.0:
            return "BUY"
        if prev_fast >= prev_slow and fast < slow and momentum < 0.0:
            return "SELL"
    if model in {"RSI_REVERSAL", "VWAP_MEAN_REVERSION", "PIVOT_REJECTION", "SUPPORT_RESISTANCE_REACTION"}:
        recent_high = rolling_high(candles, index, 20)
        recent_low = rolling_low(candles, index, 20)
        if close <= recent_low + (atr_now * 0.35):
            return "BUY"
        if close >= recent_high - (atr_now * 0.35):
            return "SELL"
    if model in {"BOLLINGER_VOLATILITY_EXPANSION", "ATR_VOLATILITY_REGIME", "LIQUIDITY_SPREAD_FILTER"}:
        if atr_now > (sum(v for v in atr_values[max(0, index - 50) : index] if v) / max(1, len([v for v in atr_values[max(0, index - 50) : index] if v]))):
            if trend_buy:
                return "BUY"
            if trend_sell:
                return "SELL"
    if alpha_id == "ALPHA016":
        if fast > slow and momentum > atr_now * 1.5:
            return "BUY"
        if fast < slow and -momentum > atr_now * 1.5:
            return "SELL"
    return "WAIT"


def candle_index_at_or_after(candles: list[Candle], timestamp: int) -> int | None:
    lo, hi = 0, len(candles)
    while lo < hi:
        mid = (lo + hi) // 2
        if candles[mid].time < timestamp:
            lo = mid + 1
        else:
            hi = mid
    return lo if lo < len(candles) else None


def r_value(direction: str, entry: float, exit_price: float, risk: float) -> float:
    if risk <= 0:
        return 0.0
    return ((exit_price - entry) / risk) if direction == "BUY" else ((entry - exit_price) / risk)


def simulate_exit(
    beta_id: str,
    direction: str,
    entry: float,
    initial_stop: float,
    target: float,
    exit_candles: list[Candle],
    start_index: int,
    atr_exit: list[float | None],
    max_bars: int,
    atr_factor: float,
) -> float:
    risk = abs(entry - initial_stop)
    if risk <= 0.0:
        return 0.0
    stop = initial_stop
    best_high = entry
    best_low = entry
    end_index = min(len(exit_candles), start_index + max_bars)
    for index in range(start_index, end_index):
        candle = exit_candles[index]
        best_high = max(best_high, candle.high)
        best_low = min(best_low, candle.low)
        progress_r = (
            (best_high - entry) / risk if direction == "BUY" else (entry - best_low) / risk
        )
        atr_now = atr_exit[index] or risk
        if beta_id == "BETA004" and progress_r >= 1.0:
            stop = max(stop, entry) if direction == "BUY" else min(stop, entry)
        elif beta_id == "BETA005" and progress_r >= 1.0:
            candidate = candle.close - (atr_now * atr_factor) if direction == "BUY" else candle.close + (atr_now * atr_factor)
            stop = max(stop, candidate) if direction == "BUY" else min(stop, candidate)
        elif beta_id == "BETA006" and progress_r >= 1.0 and index - start_index >= 6:
            lookback = exit_candles[max(start_index, index - 8) : index + 1]
            candidate = min(c.low for c in lookback) if direction == "BUY" else max(c.high for c in lookback)
            stop = max(stop, candidate) if direction == "BUY" else min(stop, candidate)
        elif beta_id == "BETA007" and progress_r >= 0.6 and index >= 14:
            previous_close = exit_candles[index - 5].close
            momentum = candle.close - previous_close
            if (direction == "BUY" and momentum < 0.0) or (direction == "SELL" and momentum > 0.0):
                return r_value(direction, entry, candle.close, risk)
        elif beta_id == "BETA008" and progress_r >= 1.0:
            candidate = best_high - (atr_now * atr_factor) if direction == "BUY" else best_low + (atr_now * atr_factor)
            stop = max(stop, candidate) if direction == "BUY" else min(stop, candidate)

        if direction == "BUY":
            if candle.low <= stop:
                return r_value(direction, entry, stop, risk)
            if candle.high >= target:
                return r_value(direction, entry, target, risk)
        else:
            if candle.high >= stop:
                return r_value(direction, entry, stop, risk)
            if candle.low <= target:
                return r_value(direction, entry, target, risk)
    if end_index <= start_index:
        return 0.0
    return r_value(direction, entry, exit_candles[end_index - 1].close, risk)


def max_drawdown(values: Iterable[float]) -> float:
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def summarize(beta_id: str, exit_tf: str, returns: list[float]) -> ExitResult:
    wins = [value for value in returns if value > 0.0]
    losses = [value for value in returns if value < 0.0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss else (999.0 if gross_profit > 0 else 0.0)
    avg_r = sum(returns) / len(returns) if returns else 0.0
    dd = max_drawdown(returns)
    score = avg_r + min(profit_factor, 5.0) * 0.06 + (len(wins) / len(returns) if returns else 0.0) * 0.12 - dd * 0.04
    catalog = BETA_CATALOG[beta_id]
    return ExitResult(
        beta_id=beta_id,
        beta_name=str(catalog["name"]),
        exit_tf=exit_tf,
        trades=len(returns),
        wins=len(wins),
        losses=len(losses),
        avg_r=avg_r,
        total_r=sum(returns),
        profit_factor=profit_factor,
        max_drawdown_r=dd,
        score=score,
    )


def run(
    count: int,
    output_dir: Path,
    *,
    max_contexts_per_alpha: int,
    max_signals_per_context: int,
) -> dict[str, object]:
    snapshot_path = Path(".traderia/mt5_research_snapshot.json")
    alpha_specs = load_alpha_specs(snapshot_path)
    alpha_contexts = load_alpha_contexts(
        snapshot_path,
        max_contexts_per_alpha=max_contexts_per_alpha,
    )
    needed_markets = set()
    for contexts in alpha_contexts.values():
        for pair, entry_tf in contexts:
            needed_markets.add((pair, entry_tf))
            needed_markets.add((pair, EXIT_TF_BY_ENTRY_TF[entry_tf]))
    if not needed_markets:
        needed_markets = {(pair, tf) for pair in PAIRS for tf in ENTRY_TFS}

    if not mt5.initialize():
        raise SystemExit(f"Falha ao inicializar MT5: {mt5.last_error()}")
    try:
        candles: dict[tuple[str, str], list[Candle]] = {}
        for pair, tf in sorted(needed_markets):
            candles[(pair, tf)] = fetch_candles(pair, tf, count)
    finally:
        mt5.shutdown()

    recommendations: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    for alpha in alpha_specs.values():
        alpha_results: list[dict[str, object]] = []
        contexts = alpha_contexts.get(alpha.alpha_id, [])
        if not contexts:
            contexts = [(pair, tf) for pair in PAIRS for tf in ENTRY_TFS]
        for pair, entry_tf in contexts:
            exit_tf = EXIT_TF_BY_ENTRY_TF[entry_tf]
            entry_candles = candles.get((pair, entry_tf), [])
            exit_candles = candles.get((pair, exit_tf), [])
            if len(entry_candles) < 300 or len(exit_candles) < 300:
                continue
            fast_period = int(safe_float(alpha.parameters.get("ema_curta"), 14.0))
            slow_period = int(safe_float(alpha.parameters.get("ema_longa"), 50.0))
            fast = ema([c.close for c in entry_candles], fast_period)
            slow = ema([c.close for c in entry_candles], slow_period)
            entry_atr = atr(entry_candles)
            exit_atr = atr(exit_candles)
            atr_factor = safe_float(alpha.parameters.get("atr_stop_factor"), 2.0)
            rr = safe_float(alpha.parameters.get("rr"), 3.0)
            beta_returns: dict[str, list[float]] = {beta_id: [] for beta_id in BETA_CATALOG}
            step = max(1, len(entry_candles) // max_signals_per_context)
            max_bars = max(12, int((TF_MINUTES[entry_tf] * 12) / TF_MINUTES[exit_tf]))
            for index in range(80, len(entry_candles) - 2, step):
                direction = alpha_signal(alpha, entry_candles, index, fast, slow, entry_atr)
                if direction not in {"BUY", "SELL"}:
                    continue
                start = candle_index_at_or_after(exit_candles, entry_candles[index].time)
                if start is None:
                    continue
                entry = entry_candles[index].close
                risk = (entry_atr[index] or 0.0) * atr_factor
                if risk <= 0.0:
                    continue
                initial_stop = entry - risk if direction == "BUY" else entry + risk
                target = entry + (risk * rr) if direction == "BUY" else entry - (risk * rr)
                for beta_id in BETA_CATALOG:
                    beta_returns[beta_id].append(
                        simulate_exit(
                            beta_id,
                            direction,
                            entry,
                            initial_stop,
                            target,
                            exit_candles,
                            start,
                            exit_atr,
                            max_bars,
                            atr_factor,
                        )
                    )
            summaries = [
                summarize(beta_id, exit_tf, values)
                for beta_id, values in beta_returns.items()
                if len(values) >= 8
            ]
            alpha_results.extend(
                {
                    "pair": pair,
                    "entry_timeframe": entry_tf,
                    "exit_timeframe": item.exit_tf,
                    "beta_id": item.beta_id,
                    "beta_name": item.beta_name,
                    "trades": item.trades,
                    "win_rate": round(item.wins / item.trades, 4) if item.trades else 0.0,
                    "avg_r": round(item.avg_r, 4),
                    "total_r": round(item.total_r, 4),
                    "profit_factor": round(item.profit_factor, 4),
                    "max_drawdown_r": round(item.max_drawdown_r, 4),
                    "score": round(item.score, 4),
                }
                for item in summaries
            )
        alpha_results.sort(key=lambda item: (float(item["score"]), float(item["avg_r"]), int(item["trades"])), reverse=True)
        best = alpha_results[0] if alpha_results else None
        recommendations.append(
            {
                "alpha_id": alpha.alpha_id,
                "model": alpha.model,
                "best": best,
                "top_candidates": alpha_results[:8],
            }
        )
    for (pair, tf), values in sorted(candles.items()):
        diagnostics.append(
            {
                "pair": pair,
                "timeframe": tf,
                "candles": len(values),
                "first": datetime.fromtimestamp(values[0].time, timezone.utc).isoformat() if values else None,
                "last": datetime.fromtimestamp(values[-1].time, timezone.utc).isoformat() if values else None,
            }
        )
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requested_candles": count,
        "max_contexts_per_alpha": max_contexts_per_alpha,
        "max_signals_per_context": max_signals_per_context,
        "timeframe_mapping": EXIT_TF_BY_ENTRY_TF,
        "beta_catalog": BETA_CATALOG,
        "diagnostics": diagnostics,
        "recommendations": recommendations,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "alpha_beta_exit_timeframe_research.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# Pesquisa Alpha x Beta de Saida por Timeframe",
        "",
        f"Gerado em: `{result['generated_at']}`",
        f"Candles solicitados por par/timeframe: `{result['requested_candles']}`",
        "",
        "## Mapeamento de timeframe",
        "",
    ]
    for entry_tf, exit_tf in result["timeframe_mapping"].items():
        lines.append(f"- Entrada `{entry_tf}` -> Saida `{exit_tf}`")
    lines.extend(["", "## Catalogo BETA003+", ""])
    for beta_id, beta in result["beta_catalog"].items():
        lines.append(f"- `{beta_id}` `{beta['name']}`: {beta['mode']} - {beta['description']}")
    lines.extend(["", "## Cobertura de candles", ""])
    for item in result["diagnostics"]:
        lines.append(
            f"- `{item['pair']} {item['timeframe']}`: {item['candles']} candles, "
            f"{item['first']} -> {item['last']}"
        )
    lines.extend(["", "## Recomendacao por Alpha", ""])
    for rec in result["recommendations"]:
        best = rec.get("best")
        if not best:
            lines.append(f"### {rec['alpha_id']} - {rec['model']}")
            lines.append("")
            lines.append("Sem amostra suficiente para recomendacao.")
            lines.append("")
            continue
        lines.append(f"### {rec['alpha_id']} - {rec['model']}")
        lines.append("")
        lines.append(
            f"Recomendado: `{best['beta_id']} {best['beta_name']}` | "
            f"Par teste dominante `{best['pair']}` | Entrada `{best['entry_timeframe']}` -> Saida `{best['exit_timeframe']}` | "
            f"trades `{best['trades']}` | win `{best['win_rate']}` | avg R `{best['avg_r']}` | PF `{best['profit_factor']}` | DD `{best['max_drawdown_r']}`"
        )
        lines.append("")
        lines.append("| Beta | Par | Entrada | Saida | Trades | Win | Avg R | PF | DD | Score |")
        lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for item in rec.get("top_candidates", [])[:5]:
            lines.append(
                f"| {item['beta_id']} {item['beta_name']} | {item['pair']} | {item['entry_timeframe']} | {item['exit_timeframe']} | "
                f"{item['trades']} | {item['win_rate']} | {item['avg_r']} | {item['profit_factor']} | {item['max_drawdown_r']} | {item['score']} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Observacoes",
            "",
            "- Esta pesquisa nao ativa nenhuma BETA no runtime.",
            "- O teste usa candles reais lidos do MT5 e uma simulacao local de saida por R.",
            "- A entrada simulada respeita a familia da Alpha, mas nao substitui a validacao pesada oficial do Research Lab.",
            "- Para virar operacional, a BETA escolhida deve entrar no catalogo oficial e depois passar por backtest do Lab.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candles", type=int, default=5000)
    parser.add_argument("--output-dir", default=".traderia/research")
    parser.add_argument("--max-contexts-per-alpha", type=int, default=6)
    parser.add_argument("--max-signals-per-context", type=int, default=45)
    args = parser.parse_args()
    result = run(
        args.candles,
        Path(args.output_dir),
        max_contexts_per_alpha=args.max_contexts_per_alpha,
        max_signals_per_context=args.max_signals_per_context,
    )
    docs_dir = Path("docs/research")
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "ALPHA_BETA_EXIT_TIMEFRAME_RESEARCH.md").write_text(
        markdown_report(result),
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "output": str(Path(args.output_dir)), "alphas": len(result["recommendations"])}, indent=2))


if __name__ == "__main__":
    main()
