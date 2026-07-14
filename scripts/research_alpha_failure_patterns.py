from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from research_alpha_beta_exit_timeframes import (
    BETA_CATALOG,
    ENTRY_TFS,
    EXIT_TF_BY_ENTRY_TF,
    PAIRS,
    TF_MINUTES,
    alpha_signal,
    atr,
    candle_index_at_or_after,
    ema,
    fetch_candles,
    load_alpha_contexts,
    load_alpha_specs,
    mt5,
    safe_float,
    simulate_exit,
)


@dataclass
class AlphaFailureSummary:
    alpha_id: str
    model: str
    signals: int
    signal_share_pct: float
    wins: int
    losses: int
    flats: int
    win_rate_pct: float
    avg_r: float
    best_context: str
    main_failure_pattern: str
    failure_notes: str


def _bucket(value: float, low: float, high: float) -> str:
    if value < low:
        return "BAIXO"
    if value > high:
        return "ALTO"
    return "MEDIO"


def _failure_pattern(
    direction: str,
    entry_close: float,
    exit_close: float,
    entry_atr: float,
    exit_atr: float,
    momentum: float,
    stop_r: float,
) -> str:
    if stop_r > -0.25:
        return "GANHO_NAO_ANDOU_O_SUFIENTE"
    against = (direction == "BUY" and exit_close < entry_close) or (
        direction == "SELL" and exit_close > entry_close
    )
    if against and abs(momentum) <= max(entry_atr, 1e-12) * 0.4:
        return "ENTRADA_SEM_MOMENTUM"
    if exit_atr > entry_atr * 1.4:
        return "EXPANSAO_DE_VOLATILIDADE_CONTRA"
    if against:
        return "REVERSAO_CURTA_CONTRA"
    return "NAO_ALCANCAR_TP_NO_INTERVALO"


def run(
    *,
    candles_count: int = 5000,
    max_contexts_per_alpha: int = 6,
    max_signals_per_context: int = 80,
) -> dict[str, object]:
    snapshot = Path(".traderia/mt5_research_snapshot.json")
    alpha_specs = load_alpha_specs(snapshot)
    alpha_contexts = load_alpha_contexts(
        snapshot,
        max_contexts_per_alpha=max_contexts_per_alpha,
    )
    needed = set()
    for contexts in alpha_contexts.values():
        for pair, entry_tf in contexts:
            needed.add((pair, entry_tf))
            needed.add((pair, EXIT_TF_BY_ENTRY_TF[entry_tf]))
    if not mt5.initialize():
        raise SystemExit(f"Falha ao inicializar MT5: {mt5.last_error()}")
    try:
        candles = {
            (pair, timeframe): fetch_candles(pair, timeframe, candles_count)
            for pair, timeframe in sorted(needed)
        }
    finally:
        mt5.shutdown()

    records: list[dict[str, object]] = []
    for alpha in alpha_specs.values():
        contexts = alpha_contexts.get(alpha.alpha_id, [])
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
                stop = entry - risk if direction == "BUY" else entry + risk
                target = entry + (risk * rr) if direction == "BUY" else entry - (risk * rr)
                result_r = simulate_exit(
                    "BETA003",
                    direction,
                    entry,
                    stop,
                    target,
                    exit_candles,
                    start,
                    exit_atr,
                    max_bars,
                    atr_factor,
                )
                exit_index = min(len(exit_candles) - 1, start + max_bars - 1)
                exit_close = exit_candles[exit_index].close
                momentum = entry_candles[index].close - entry_candles[max(0, index - 14)].close
                pattern = (
                    "GANHO_CONCRETIZADO"
                    if result_r >= 1.0
                    else _failure_pattern(
                        direction,
                        entry,
                        exit_close,
                        entry_atr[index] or 0.0,
                        exit_atr[exit_index] or 0.0,
                        momentum,
                        result_r,
                    )
                )
                records.append(
                    {
                        "alpha_id": alpha.alpha_id,
                        "model": alpha.model,
                        "pair": pair,
                        "entry_timeframe": entry_tf,
                        "exit_timeframe": exit_tf,
                        "direction": direction,
                        "result_r": round(result_r, 4),
                        "pattern": pattern,
                        "momentum_bucket": _bucket(abs(momentum), risk * 0.25, risk * 0.85),
                        "atr_bucket": _bucket(entry_atr[index] or 0.0, risk / max(atr_factor, 1e-12) * 0.8, risk / max(atr_factor, 1e-12) * 1.2),
                    }
                )

    total_signals = len(records)
    summaries: list[AlphaFailureSummary] = []
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        grouped[str(record["alpha_id"])].append(record)
    for alpha_id, items in sorted(grouped.items()):
        model = str(items[0]["model"])
        wins = [item for item in items if float(item["result_r"]) > 0.0]
        losses = [item for item in items if float(item["result_r"]) < 0.0]
        flats = [item for item in items if float(item["result_r"]) == 0.0]
        context_counter = Counter(
            f"{item['pair']} {item['entry_timeframe']}->{item['exit_timeframe']}"
            for item in items
        )
        failure_counter = Counter(
            str(item["pattern"]) for item in items if str(item["pattern"]) != "GANHO_CONCRETIZADO"
        )
        main_failure = failure_counter.most_common(1)[0][0] if failure_counter else "N/D"
        summaries.append(
            AlphaFailureSummary(
                alpha_id=alpha_id,
                model=model,
                signals=len(items),
                signal_share_pct=round((len(items) / total_signals) * 100.0, 2)
                if total_signals
                else 0.0,
                wins=len(wins),
                losses=len(losses),
                flats=len(flats),
                win_rate_pct=round((len(wins) / len(items)) * 100.0, 2) if items else 0.0,
                avg_r=round(sum(float(item["result_r"]) for item in items) / len(items), 4)
                if items
                else 0.0,
                best_context=context_counter.most_common(1)[0][0],
                main_failure_pattern=main_failure,
                failure_notes=", ".join(
                    f"{name}: {count}" for name, count in failure_counter.most_common(3)
                )
                or "Sem falhas relevantes",
            )
        )
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candles_requested": candles_count,
        "total_signals": total_signals,
        "summaries": [asdict(item) for item in summaries],
        "records_sample": records[:200],
    }
    output_dir = Path(".traderia/research")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "alpha_failure_patterns.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def to_markdown(result: dict[str, object]) -> str:
    lines = [
        "# Auditoria de Repeticao e Falhas por Alpha",
        "",
        f"Gerado em: `{result['generated_at']}`",
        f"Candles solicitados: `{result['candles_requested']}`",
        f"Sinais simulados: `{result['total_signals']}`",
        "",
        "## Resumo por Alpha",
        "",
        "| Alpha | Modelo | % repeticao | Sinais | Win % | Avg R | Contexto mais comum | Falha principal |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in result["summaries"]:
        lines.append(
            f"| {item['alpha_id']} | {item['model']} | {item['signal_share_pct']}% | "
            f"{item['signals']} | {item['win_rate_pct']}% | {item['avg_r']} | "
            f"{item['best_context']} | {item['main_failure_pattern']} |"
        )
    lines.extend(
        [
            "",
            "## Como ler",
            "",
            "- `% repeticao`: quanto aquela Alpha apareceu dentro dos sinais simulados nessa auditoria.",
            "- `GANHO_NAO_ANDOU_O_SUFIENTE`: o trade nao virou perda forte, mas tambem nao andou para concretizar ganho.",
            "- `ENTRADA_SEM_MOMENTUM`: havia sinal, mas o impulso inicial era fraco.",
            "- `EXPANSAO_DE_VOLATILIDADE_CONTRA`: o mercado abriu volatilidade contra a entrada.",
            "- `REVERSAO_CURTA_CONTRA`: o movimento virou contra antes de desenvolver.",
            "- `NAO_ALCANCAR_TP_NO_INTERVALO`: direcao nao foi necessariamente errada, mas o alvo nao foi atingido no intervalo observado.",
            "",
            "## Falhas mais comuns por Alpha",
            "",
        ]
    )
    for item in result["summaries"]:
        lines.append(f"- `{item['alpha_id']}`: {item['failure_notes']}")
    lines.extend(
        [
            "",
            "## Observacao operacional",
            "",
            "Esta auditoria e diagnostica. Ela nao altera runtime, robô, Position Manager ou parametros do Lab.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    result = run()
    docs = Path("docs/research")
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "ALPHA_FAILURE_PATTERNS.md").write_text(to_markdown(result), encoding="utf-8")
    print(json.dumps({"ok": True, "signals": result["total_signals"]}, indent=2))


if __name__ == "__main__":
    main()
