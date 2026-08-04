"""Busca de niveis M15 predefinidos tocados no candle seguinte.

Todos os niveis e filtros usam somente candles fechados. O candle de execucao
contribui com horario e faixa ``high/low`` completos; por isso a confirmacao da
execucao e ex post no nivel do candle, sem conhecer a ordem intrabar dos ticks.
O alvo admite BUY e SELL simultaneos para representar hedge.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from typing import Mapping, Sequence

import numpy as np

from research.multi_ea_trading_lab import MultiEACandle, MultiEATradePosition


M15_DURATION = timedelta(minutes=15)
TRAIN = np.int8(1)
EMBARGO = np.int8(2)
VALIDATION = np.int8(3)


@dataclass(frozen=True)
class MultiEAIntrabarSearchConfiguration:
    """Parametros de busca, validacao e selecao de portfolio."""

    train_fraction: float = 0.70
    minimum_positive_events_for_split: int = 20
    minimum_validation_positive_events: int = 5
    common_history_bars: int = 210
    embargo_bars: int = 8
    maximum_ranked_candidates: int = 100
    candidate_complexity_penalty: float = 0.005
    portfolio_maximum_setups: int = 8
    portfolio_candidate_pool: int = 48
    portfolio_false_positive_penalty: float = 0.50
    portfolio_complexity_penalty: float = 0.005


@dataclass(frozen=True, slots=True)
class _BaseSpec:
    base_id: str
    family: str
    parameters: Mapping[str, object]
    complexity: int


@dataclass(frozen=True, slots=True)
class _Schedule:
    delay_bars: int
    cooldown_bars: int
    session: str
    filter_id: str


@dataclass(frozen=True, slots=True)
class _Hypothesis:
    candidate_id: str
    base: _BaseSpec
    delay_bars: int
    cooldown_bars: int
    session: str
    filter_id: str
    complexity: int


@dataclass(slots=True)
class _Counts:
    opportunities: int = 0
    positive_events: int = 0
    positive_directions: int = 0
    raw_direction_signals: int = 0
    direction_signals: int = 0
    buy_tp: int = 0
    buy_fp: int = 0
    buy_fn: int = 0
    buy_tn: int = 0
    sell_tp: int = 0
    sell_fp: int = 0
    sell_fn: int = 0
    sell_tn: int = 0
    event_tp: int = 0
    event_fp: int = 0
    event_fn: int = 0
    event_tn: int = 0
    exact_direction_set_matches: int = 0

    def add(self, other: "_Counts") -> None:
        for name in self.__dataclass_fields__:
            setattr(self, name, int(getattr(self, name)) + int(getattr(other, name)))


@dataclass(slots=True)
class _FeatureStore:
    candles: Sequence[MultiEACandle]
    open: np.ndarray = field(init=False)
    high: np.ndarray = field(init=False)
    low: np.ndarray = field(init=False)
    close: np.ndarray = field(init=False)
    _cache: dict[tuple[str, int], np.ndarray] = field(default_factory=dict)
    _true_range: np.ndarray | None = None

    def __post_init__(self) -> None:
        self.open = np.asarray([float(item.open) for item in self.candles], dtype=np.float64)
        self.high = np.asarray([float(item.high) for item in self.candles], dtype=np.float64)
        self.low = np.asarray([float(item.low) for item in self.candles], dtype=np.float64)
        self.close = np.asarray([float(item.close) for item in self.candles], dtype=np.float64)

    def sma(self, period: int) -> np.ndarray:
        key = ("SMA", period)
        if key not in self._cache:
            self._cache[key] = _rolling_mean(self.close, period)
        return self._cache[key]

    def ema(self, period: int) -> np.ndarray:
        key = ("EMA", period)
        if key not in self._cache:
            self._cache[key] = _ema(self.close, period)
        return self._cache[key]

    def std(self, period: int) -> np.ndarray:
        key = ("STD", period)
        if key not in self._cache:
            self._cache[key] = _rolling_std(self.close, period)
        return self._cache[key]

    def atr(self, period: int) -> np.ndarray:
        key = ("ATR", period)
        if key not in self._cache:
            if self._true_range is None:
                previous = np.r_[self.close[0], self.close[:-1]]
                self._true_range = np.maximum.reduce(
                    (self.high - self.low, np.abs(self.high - previous), np.abs(self.low - previous))
                )
            self._cache[key] = _rolling_mean(self._true_range, period)
        return self._cache[key]

    def donchian_high(self, period: int) -> np.ndarray:
        key = ("DONCHIAN_HIGH", period)
        if key not in self._cache:
            self._cache[key] = _rolling_extreme(self.high, period, maximum=True)
        return self._cache[key]

    def donchian_low(self, period: int) -> np.ndarray:
        key = ("DONCHIAN_LOW", period)
        if key not in self._cache:
            self._cache[key] = _rolling_extreme(self.low, period, maximum=False)
        return self._cache[key]

    def rsi14(self) -> np.ndarray:
        key = ("RSI", 14)
        if key not in self._cache:
            change = np.diff(self.close, prepend=self.close[0])
            gains = _rolling_mean(np.maximum(change, 0.0), 14)
            losses = _rolling_mean(np.maximum(-change, 0.0), 14)
            ratio = np.divide(gains, losses, out=np.full_like(gains, np.nan), where=losses > 0.0)
            result = 100.0 - 100.0 / (1.0 + ratio)
            result[(losses <= 0.0) & (gains > 0.0)] = 100.0
            result[(losses <= 0.0) & (gains <= 0.0)] = 50.0
            self._cache[key] = result
        return self._cache[key]

    def stochastic14(self) -> np.ndarray:
        key = ("STOCHASTIC", 14)
        if key not in self._cache:
            highest = _rolling_extreme(self.high, 14, maximum=True)
            lowest = _rolling_extreme(self.low, 14, maximum=False)
            width = highest - lowest
            self._cache[key] = np.divide(
                100.0 * (self.close - lowest),
                width,
                out=np.full_like(width, np.nan),
                where=width > 0.0,
            )
        return self._cache[key]

    def adx_like14(self) -> np.ndarray:
        key = ("ADX_LIKE", 14)
        if key not in self._cache:
            up = np.diff(self.high, prepend=self.high[0])
            down = -np.diff(self.low, prepend=self.low[0])
            plus_dm = np.where((up > down) & (up > 0.0), up, 0.0)
            minus_dm = np.where((down > up) & (down > 0.0), down, 0.0)
            atr = self.atr(14)
            plus_di = np.divide(100.0 * _rolling_mean(plus_dm, 14), atr, out=np.zeros_like(atr), where=atr > 0.0)
            minus_di = np.divide(100.0 * _rolling_mean(minus_dm, 14), atr, out=np.zeros_like(atr), where=atr > 0.0)
            denominator = plus_di + minus_di
            dx = np.divide(100.0 * np.abs(plus_di - minus_di), denominator, out=np.zeros_like(denominator), where=denominator > 0.0)
            self._cache[key] = _rolling_finite_mean(dx, 14)
        return self._cache[key]


@dataclass(slots=True)
class _SymbolData:
    symbol: str
    candles: Sequence[MultiEACandle]
    features: _FeatureStore
    execution_indexes: np.ndarray
    hours_utc: np.ndarray
    label_buy: np.ndarray
    label_sell: np.ndarray
    segments: np.ndarray


class MultiEAIntrabarSearchEngine:
    """Varre niveis predefinidos e seleciona sub-setups sem usar saidas."""

    def __init__(
        self,
        configuration: MultiEAIntrabarSearchConfiguration | None = None,
    ) -> None:
        self.configuration = configuration or MultiEAIntrabarSearchConfiguration()
        _validate_configuration(self.configuration)
        self._base_specs = _base_catalog()
        self._schedules = _schedule_catalog()
        self._hypotheses = _hypothesis_catalog(self._base_specs, self._schedules)
        self._hypothesis_by_id = {item.candidate_id: item for item in self._hypotheses}
        self._hypotheses_by_base: dict[str, list[_Hypothesis]] = {}
        for item in self._hypotheses:
            self._hypotheses_by_base.setdefault(item.base.base_id, []).append(item)

    def candidate_catalog(self) -> list[dict[str, object]]:
        return [_hypothesis_metadata(item) for item in self._hypotheses]

    def analyze(
        self,
        positions: Sequence[MultiEATradePosition],
        candles: Sequence[MultiEACandle],
        *,
        source_timezone: str | None = None,
    ) -> dict[str, object]:
        """Executa a grade completa com treino temporal e holdout congelado."""

        ordered_positions = sorted(positions, key=lambda item: _time_key(item.open_time))
        series = _m15_series(candles)
        datasets, coverage = self._build_datasets(ordered_positions, series)
        split = self._assign_segments(datasets)
        global_rows, symbol_rows = self._train_rankings(datasets)
        global_rows.sort(key=_ranking_key)
        selected_global = global_rows[0] if global_rows else None
        global_validation = (
            self._evaluate_hypothesis(
                self._hypothesis_by_id[str(selected_global["candidate_id"])],
                datasets,
                segment=VALIDATION,
            )
            if selected_global
            else {}
        )

        by_symbol: dict[str, dict[str, object]] = {}
        for symbol, rows in sorted(symbol_rows.items()):
            rows.sort(key=_ranking_key)
            selected = rows[0] if rows else None
            validation = (
                self._evaluate_hypothesis(
                    self._hypothesis_by_id[str(selected["candidate_id"])],
                    [datasets[symbol]],
                    segment=VALIDATION,
                )
                if selected
                else {}
            )
            by_symbol[symbol] = {
                "candidate_count_evaluated": len(rows),
                "ranking_train": rows[: self.configuration.maximum_ranked_candidates],
                "selected_candidate_id": str(selected["candidate_id"]) if selected else "N/D",
                "selection_metrics_train": selected or {},
                "validation_metrics_frozen": validation,
            }

        symbol_portfolio = self._symbol_portfolio(datasets, by_symbol)
        portfolio = self._greedy_portfolio(datasets, global_rows)
        catalog = self.candidate_catalog()
        catalog_sha256 = hashlib.sha256(
            json.dumps(
                catalog,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        warnings = [
            "RESEARCH_ONLY: nenhum setup pode alimentar conta Demo ou real.",
            (
                "NIVEL_PREDEFINIDO_BAR_EVENT: indicadores e niveis usam somente "
                "candles anteriores fechados; o candle seguinte fornece hora e "
                "high/low completos para confirmacao ex post."
            ),
            (
                "MULTI_LABEL: BUY e SELL podem coexistir na mesma oportunidade "
                "para representar hedge."
            ),
            (
                "NEGATIVOS_INCLUIDOS: toda barra elegivel sem entrada observada "
                "participa de precision, MCC e penalidade de falso positivo."
            ),
            (
                "NEGATIVOS_ASSUMIDOS: a interpretacao de falso positivo pressupoe "
                "que o CSV contenha todas as entradas do periodo; se estiver "
                "incompleto, o problema e positive-unlabeled."
            ),
            (
                "FAIXA_NAO_E_TICK: high/low do candle seguinte apenas confirma que "
                "o nivel foi executavel na janela; nao reconstroi o segundo da entrada "
                "nem a ordem em que os precos ocorreram."
            ),
            (
                "ENTRADAS_SOMENTE: close_time, close_price, lucro, swap e comissao "
                "nao sao lidos."
            ),
        ]
        if not source_timezone:
            warnings.append(
                "FUSO_NAO_INFORMADO: timestamps naive sao comparados na mesma escala UTC."
            )
        return {
            "schema_version": "multi_ea_intrabar_search_v1",
            "status": "OK" if datasets else "SEM_SOBREPOSICAO_M15",
            "timeframe": "M15",
            "research_only": True,
            "operational_eligible": False,
            "uses_exit_data": False,
            "execution_candle_fields_used": ["timestamp", "high", "low"],
            "execution_candle_close_used": False,
            "signal_level_lookahead": False,
            "causal_entry_test": False,
            "evaluation_uses_full_execution_bar": True,
            "execution_confirmation_ex_post": True,
            "intrabar_path_known": False,
            "exact_entry_reconstruction": False,
            "evaluation_unit": "SYMBOL_M15_DIRECTION_LABEL",
            "source_row_multiplicity_preserved": False,
            "candidate_count": len(self._hypotheses),
            "base_rule_count": len(self._base_specs),
            "candidate_catalog": catalog,
            "catalog_sha256": catalog_sha256,
            "grid_dimensions": {
                "ma_periods": [5, 10, 20, 50, 100, 200],
                "band_periods": [10, 20, 50],
                "multipliers": [0.5, 1.0, 1.5, 2.0, 2.5],
                "delays": sorted({item.delay_bars for item in self._hypotheses}),
                "cooldowns": sorted({item.cooldown_bars for item in self._hypotheses}),
                "sessions": sorted({item.session for item in self._hypotheses}),
                "filters": sorted({item.filter_id for item in self._hypotheses}),
            },
            "coverage": coverage,
            "split": split,
            "ranking_policy": {
                "selection_segment": "TRAIN",
                "validation_policy": "FROZEN",
                "score_formula": (
                    "0.45*direction_F1 + 0.25*event_F1 + 0.15*direction_MCC "
                    "+ 0.15*event_MCC - complexity_penalty"
                ),
                "complexity_penalty": self.configuration.candidate_complexity_penalty,
            },
            "global": {
                "candidate_count_evaluated": len(global_rows),
                "ranking_train": global_rows[: self.configuration.maximum_ranked_candidates],
                "selected_candidate_id": str(selected_global["candidate_id"]) if selected_global else "N/D",
                "selection_metrics_train": selected_global or {},
                "validation_metrics_frozen": global_validation,
            },
            "by_symbol": by_symbol,
            "symbol_portfolio": symbol_portfolio,
            "portfolio": portfolio,
            "warnings": warnings,
        }

    run = analyze

    def _build_datasets(
        self,
        positions: Sequence[MultiEATradePosition],
        series: Mapping[str, Sequence[MultiEACandle]],
    ) -> tuple[dict[str, _SymbolData], dict[str, object]]:
        if not positions or not series:
            return {}, _coverage(positions, {}, 0, 0)
        open_times = {
            symbol: [_time_key(item.timestamp) for item in market]
            for symbol, market in series.items()
        }
        labels: dict[tuple[str, int], int] = {}
        adjacent_positions = 0
        eligible_positions = 0
        for position in positions:
            symbol = str(position.symbol).strip().upper()
            market = series.get(symbol)
            if not market:
                continue
            entry_time = _time_key(position.open_time)
            index = bisect_right(open_times[symbol], entry_time) - 1
            if index < 0:
                continue
            distance = entry_time - open_times[symbol][index]
            if distance < timedelta(0) or distance >= M15_DURATION:
                continue
            adjacent_positions += 1
            if index < self.configuration.common_history_bars:
                continue
            direction = str(position.direction).strip().upper()
            bit = 1 if direction == "BUY" else 2 if direction == "SELL" else 0
            if bit == 0:
                continue
            labels[(symbol, index)] = labels.get((symbol, index), 0) | bit
            eligible_positions += 1
        if not labels:
            return {}, _coverage(positions, {}, adjacent_positions, eligible_positions)

        first_time = min(open_times[symbol][index] for symbol, index in labels)
        last_entry = max(_time_key(item.open_time) for item in positions)
        datasets: dict[str, _SymbolData] = {}
        for symbol, market in sorted(series.items()):
            indexes = np.asarray(
                [
                    index
                    for index in range(self.configuration.common_history_bars, len(market))
                    if first_time <= open_times[symbol][index] <= last_entry
                ],
                dtype=np.int32,
            )
            if indexes.size == 0:
                continue
            label_values = np.asarray(
                [labels.get((symbol, int(index)), 0) for index in indexes],
                dtype=np.uint8,
            )
            label_buy = (label_values & 1) != 0
            label_sell = (label_values & 2) != 0
            datasets[symbol] = _SymbolData(
                symbol=symbol,
                candles=market,
                features=_FeatureStore(market),
                execution_indexes=indexes,
                hours_utc=np.asarray(
                    [open_times[symbol][int(index)].hour for index in indexes],
                    dtype=np.int8,
                ),
                label_buy=label_buy,
                label_sell=label_sell,
                segments=np.full(indexes.size, TRAIN, dtype=np.int8),
            )
        return datasets, _coverage(
            positions,
            datasets,
            adjacent_positions,
            eligible_positions,
        )

    def _assign_segments(
        self,
        datasets: Mapping[str, _SymbolData],
    ) -> dict[str, object]:
        opportunity_times = sorted(
            {
                _time_key(data.candles[int(index)].timestamp)
                for data in datasets.values()
                for index in data.execution_indexes
            }
        )
        if (
            len(opportunity_times)
            < self.configuration.minimum_positive_events_for_split
            + self.configuration.embargo_bars
            + 1
        ):
            return {
                "method": "TREINO_UNICO_AMOSTRA_INSUFICIENTE",
                "train_end": opportunity_times[-1].isoformat()
                if opportunity_times
                else "N/D",
                "validation_start": "N/D",
                "embargo_bars": 0,
                **_split_counts(datasets),
            }
        cut = max(1, int(len(opportunity_times) * self.configuration.train_fraction))
        cut = min(
            cut,
            len(opportunity_times) - self.configuration.embargo_bars - 1,
        )
        validation_index = cut + self.configuration.embargo_bars
        train_end = opportunity_times[cut - 1]
        validation_start = opportunity_times[validation_index]
        for data in datasets.values():
            times = [_time_key(data.candles[int(index)].timestamp) for index in data.execution_indexes]
            data.segments = np.asarray(
                [TRAIN if value <= train_end else VALIDATION if value >= validation_start else EMBARGO for value in times],
                dtype=np.int8,
            )
        counts = _split_counts(datasets)
        return {
            "method": "CRONOLOGICO_TREINO_VALIDACAO_COM_EMBARGO",
            "cut_basis": "TIMESTAMPS_M15_UNICOS_SEM_CONSULTAR_ROTULOS",
            "train_end": train_end.isoformat(),
            "validation_start": validation_start.isoformat(),
            "embargo_bars": self.configuration.embargo_bars,
            **counts,
            "validation_sufficient": (
                counts["validation_positive_events"]
                >= self.configuration.minimum_validation_positive_events
            ),
        }

    def _train_rankings(
        self,
        datasets: Mapping[str, _SymbolData],
    ) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
        global_rows: list[dict[str, object]] = []
        symbol_rows: dict[str, list[dict[str, object]]] = {symbol: [] for symbol in datasets}
        for base in self._base_specs:
            raw_cache: dict[int, dict[str, tuple[np.ndarray, np.ndarray]]] = {}
            for hypothesis in self._hypotheses_by_base[base.base_id]:
                if hypothesis.delay_bars not in raw_cache:
                    raw_cache[hypothesis.delay_bars] = {
                        symbol: _base_signals(base, data, hypothesis.delay_bars)
                        for symbol, data in datasets.items()
                    }
                aggregate = _Counts()
                for symbol, data in datasets.items():
                    raw_buy, raw_sell = raw_cache[hypothesis.delay_bars][symbol]
                    buy, sell = _apply_constraints(hypothesis, data, raw_buy, raw_sell)
                    counts = _signal_counts(data, raw_buy, raw_sell, buy, sell, data.segments == TRAIN)
                    aggregate.add(counts)
                    symbol_rows[symbol].append(self._ranked_row(hypothesis, counts))
                global_rows.append(self._ranked_row(hypothesis, aggregate))
        return global_rows, symbol_rows

    def _ranked_row(self, hypothesis: _Hypothesis, counts: _Counts) -> dict[str, object]:
        metrics = _finalize_counts(counts)
        directional = dict(metrics["direction_micro"])
        event = dict(metrics["event"])
        penalty = self.configuration.candidate_complexity_penalty * max(hypothesis.complexity - 1, 0)
        score = (
            0.45 * float(directional["f1"])
            + 0.25 * float(event["f1"])
            + 0.15 * float(directional["mcc"])
            + 0.15 * float(event["mcc"])
            - penalty
        )
        return {
            **_hypothesis_metadata(hypothesis),
            **metrics,
            "complexity_penalty_applied": round(penalty, 8),
            "ranking_score": round(score, 8),
        }

    def _evaluate_hypothesis(
        self,
        hypothesis: _Hypothesis,
        datasets: Sequence[_SymbolData] | Mapping[str, _SymbolData],
        *,
        segment: np.int8,
    ) -> dict[str, object]:
        values = list(datasets.values()) if isinstance(datasets, Mapping) else list(datasets)
        aggregate = _Counts()
        for data in values:
            raw_buy, raw_sell = _base_signals(hypothesis.base, data, hypothesis.delay_bars)
            buy, sell = _apply_constraints(hypothesis, data, raw_buy, raw_sell)
            aggregate.add(_signal_counts(data, raw_buy, raw_sell, buy, sell, data.segments == segment))
        return {**_hypothesis_metadata(hypothesis), **_finalize_counts(aggregate)}

    def _greedy_portfolio(
        self,
        datasets: Mapping[str, _SymbolData],
        global_rows: Sequence[Mapping[str, object]],
    ) -> dict[str, object]:
        if not datasets or not global_rows:
            return {
                "selection_method": "GREEDY_UNION_TRAIN_ONLY",
                "selected_candidate_ids": [],
                "selection_steps": [],
                "metrics_train": _finalize_counts(_Counts()),
                "validation_metrics_frozen": _finalize_counts(_Counts()),
            }
        pool_rows = list(global_rows[: self.configuration.portfolio_candidate_pool])
        train_targets_buy = np.concatenate([data.label_buy[data.segments == TRAIN] for data in datasets.values()])
        train_targets_sell = np.concatenate([data.label_sell[data.segments == TRAIN] for data in datasets.values()])
        pool_signals: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for row in pool_rows:
            hypothesis = self._hypothesis_by_id[str(row["candidate_id"])]
            buys: list[np.ndarray] = []
            sells: list[np.ndarray] = []
            for data in datasets.values():
                raw_buy, raw_sell = _base_signals(hypothesis.base, data, hypothesis.delay_bars)
                buy, sell = _apply_constraints(hypothesis, data, raw_buy, raw_sell)
                mask = data.segments == TRAIN
                buys.append(buy[mask])
                sells.append(sell[mask])
            pool_signals[hypothesis.candidate_id] = (np.concatenate(buys), np.concatenate(sells))

        current_buy = np.zeros(train_targets_buy.size, dtype=np.bool_)
        current_sell = np.zeros(train_targets_sell.size, dtype=np.bool_)
        selected: list[_Hypothesis] = []
        steps: list[dict[str, object]] = []
        current_score = -math.inf
        for _ in range(self.configuration.portfolio_maximum_setups):
            best: tuple[float, str, _Hypothesis, np.ndarray, np.ndarray, dict[str, object]] | None = None
            for row in pool_rows:
                hypothesis = self._hypothesis_by_id[str(row["candidate_id"])]
                if hypothesis in selected:
                    continue
                candidate_buy, candidate_sell = pool_signals[hypothesis.candidate_id]
                union_buy = current_buy | candidate_buy
                union_sell = current_sell | candidate_sell
                metrics = _finalize_counts(
                    _counts_from_arrays(
                        train_targets_buy,
                        train_targets_sell,
                        union_buy,
                        union_sell,
                        union_buy,
                        union_sell,
                    )
                )
                complexity = sum(item.complexity for item in selected) + hypothesis.complexity
                score = self._portfolio_score(metrics, complexity)
                choice = (score, hypothesis.candidate_id, hypothesis, union_buy, union_sell, metrics)
                if best is None or score > best[0] + 1e-12 or (abs(score - best[0]) <= 1e-12 and hypothesis.candidate_id < best[1]):
                    best = choice
            if best is None or (
                selected and best[0] <= current_score + 1e-12
            ):
                break
            current_score, _, chosen, current_buy, current_sell, metrics = best
            selected.append(chosen)
            steps.append(
                {
                    "step": len(selected),
                    "added_candidate_id": chosen.candidate_id,
                    "portfolio_score": round(current_score, 8),
                    "total_complexity": sum(item.complexity for item in selected),
                    "metrics_train": metrics,
                }
            )

        train_metrics = _finalize_counts(
            _counts_from_arrays(
                train_targets_buy,
                train_targets_sell,
                current_buy,
                current_sell,
                current_buy,
                current_sell,
            )
        )
        validation_counts = _Counts()
        for data in datasets.values():
            union_buy = np.zeros(data.execution_indexes.size, dtype=np.bool_)
            union_sell = np.zeros(data.execution_indexes.size, dtype=np.bool_)
            for hypothesis in selected:
                raw_buy, raw_sell = _base_signals(hypothesis.base, data, hypothesis.delay_bars)
                buy, sell = _apply_constraints(hypothesis, data, raw_buy, raw_sell)
                union_buy |= buy
                union_sell |= sell
            validation_counts.add(
                _signal_counts(
                    data,
                    union_buy,
                    union_sell,
                    union_buy,
                    union_sell,
                    data.segments == VALIDATION,
                )
            )
        return {
            "selection_method": "GREEDY_UNION_TRAIN_ONLY",
            "validation_policy": "FROZEN",
            "candidate_pool_size": len(pool_rows),
            "maximum_setups": self.configuration.portfolio_maximum_setups,
            "false_positive_penalty": self.configuration.portfolio_false_positive_penalty,
            "complexity_penalty": self.configuration.portfolio_complexity_penalty,
            "selected_candidate_ids": [item.candidate_id for item in selected],
            "selected_setups": [_hypothesis_metadata(item) for item in selected],
            "selection_steps": steps,
            "portfolio_score_train": round(
                current_score if math.isfinite(current_score) else 0.0,
                8,
            ),
            "metrics_train": train_metrics,
            "validation_metrics_frozen": _finalize_counts(validation_counts),
        }

    def _symbol_portfolio(
        self,
        datasets: Mapping[str, _SymbolData],
        by_symbol: Mapping[str, Mapping[str, object]],
    ) -> dict[str, object]:
        """Congela o melhor candidato de treino de cada simbolo e os agrega."""

        selected_setup_by_symbol: dict[str, dict[str, object]] = {}
        excluded_symbols: list[dict[str, object]] = []
        train_counts = _Counts()
        validation_counts = _Counts()
        for symbol, data in sorted(datasets.items()):
            train_mask = data.segments == TRAIN
            validation_mask = data.segments == VALIDATION
            train_positive_events = int(
                np.count_nonzero(
                    (data.label_buy | data.label_sell) & train_mask
                )
            )
            validation_positive_events = int(
                np.count_nonzero(
                    (data.label_buy | data.label_sell) & validation_mask
                )
            )
            if train_positive_events <= 0:
                excluded_symbols.append(
                    {
                        "symbol": symbol,
                        "reason": "SEM_POSITIVOS_NO_TREINO",
                        "train_positive_events": 0,
                        "validation_positive_events": validation_positive_events,
                    }
                )
                continue

            symbol_report = dict(by_symbol.get(symbol, {}) or {})
            candidate_id = str(
                symbol_report.get("selected_candidate_id", "N/D") or "N/D"
            )
            hypothesis = self._hypothesis_by_id.get(candidate_id)
            if hypothesis is None:
                excluded_symbols.append(
                    {
                        "symbol": symbol,
                        "reason": "SEM_SETUP_SELECIONAVEL_NO_TREINO",
                        "train_positive_events": train_positive_events,
                        "validation_positive_events": validation_positive_events,
                    }
                )
                continue

            raw_buy, raw_sell = _base_signals(
                hypothesis.base,
                data,
                hypothesis.delay_bars,
            )
            buy, sell = _apply_constraints(
                hypothesis,
                data,
                raw_buy,
                raw_sell,
            )
            per_symbol_train = _signal_counts(
                data,
                raw_buy,
                raw_sell,
                buy,
                sell,
                train_mask,
            )
            per_symbol_validation = _signal_counts(
                data,
                raw_buy,
                raw_sell,
                buy,
                sell,
                validation_mask,
            )
            train_counts.add(per_symbol_train)
            validation_counts.add(per_symbol_validation)
            selection_metrics = dict(
                symbol_report.get("selection_metrics_train", {}) or {}
            )
            selected_setup_by_symbol[symbol] = {
                **_hypothesis_metadata(hypothesis),
                "train_positive_events": train_positive_events,
                "selection_ranking_score": float(
                    selection_metrics.get("ranking_score", 0.0) or 0.0
                ),
            }

        return {
            "selection_method": "BEST_SETUP_PER_SYMBOL_TRAIN_ONLY",
            "selection_segment": "TRAIN",
            "validation_policy": "FROZEN",
            "aggregation_scope": "SOMENTE_SIMBOLOS_COM_POSITIVOS_NO_TREINO",
            "selected_setup_by_symbol": selected_setup_by_symbol,
            "included_symbols": len(selected_setup_by_symbol),
            "excluded_symbols_count": len(excluded_symbols),
            "excluded_validation_positive_events": sum(
                int(item["validation_positive_events"])
                for item in excluded_symbols
            ),
            "excluded_symbols": excluded_symbols,
            "metrics_train": _finalize_counts(train_counts),
            "validation_metrics_frozen": _finalize_counts(validation_counts),
        }

    def _portfolio_score(self, metrics: Mapping[str, object], complexity: int) -> float:
        directional = dict(metrics["direction_micro"])
        event = dict(metrics["event"])
        opportunities = int(metrics.get("opportunities", 0) or 0)
        fp_rate = _ratio(float(directional["false_positive"]), 2.0 * opportunities)
        return (
            0.50 * float(directional["f1"])
            + 0.25 * float(event["f1"])
            + 0.15 * float(directional["mcc"])
            + 0.10 * float(event["mcc"])
            - self.configuration.portfolio_false_positive_penalty * fp_rate
            - self.configuration.portfolio_complexity_penalty * max(complexity - 1, 0)
        )


def _base_catalog() -> tuple[_BaseSpec, ...]:
    result: list[_BaseSpec] = []
    ma_periods = (5, 10, 20, 50, 100, 200)
    for kind in ("EMA", "SMA"):
        for period in ma_periods:
            for mode in ("TREND", "REVERSAL"):
                result.append(_BaseSpec(f"{kind}_TOUCH_{period}_{mode}", "MA_TOUCH", {"kind": kind, "period": period, "mode": mode}, 2))
            result.append(_BaseSpec(f"PRICE_{kind}_CROSS_{period}", "PRICE_MA_CROSS", {"kind": kind, "period": period}, 2))
        for fast, slow in ((5, 20), (10, 50), (20, 100), (50, 200)):
            result.append(_BaseSpec(f"{kind}_CROSS_{fast}_{slow}", "MA_CROSS", {"kind": kind, "fast": fast, "slow": slow}, 2))

    for family, periods, multipliers in (
        ("BOLLINGER", (10, 20, 50), (1.0, 1.5, 2.0, 2.5)),
        ("KELTNER", (10, 20, 50), (1.0, 1.5, 2.0, 2.5)),
        ("ATR_LEVEL", (7, 14, 28), (0.5, 1.0, 1.5, 2.0)),
    ):
        for period in periods:
            for multiplier in multipliers:
                multiplier_id = str(multiplier).replace(".", "P")
                for mode in ("BREAKOUT", "REVERSAL"):
                    result.append(
                        _BaseSpec(
                            f"{family}_{period}_{multiplier_id}_{mode}",
                            family,
                            {"period": period, "multiplier": multiplier, "mode": mode},
                            3,
                        )
                    )
    for period in ma_periods:
        for mode in ("BREAKOUT", "REVERSAL"):
            result.append(_BaseSpec(f"DONCHIAN_{period}_{mode}", "DONCHIAN", {"period": period, "mode": mode}, 2))
    return tuple(result)


def _schedule_catalog() -> tuple[_Schedule, ...]:
    return (
        _Schedule(0, 1, "ALL", "NONE"),
        _Schedule(1, 2, "ALL", "NONE"),
        _Schedule(2, 4, "ALL", "NONE"),
        _Schedule(4, 8, "ALL", "NONE"),
        _Schedule(8, 16, "ALL", "NONE"),
        _Schedule(0, 2, "ASIA_00_08", "RSI_REVERSAL"),
        _Schedule(1, 4, "LONDON_07_16", "RSI_MOMENTUM"),
        _Schedule(2, 8, "NEW_YORK_12_21", "STOCH_REVERSAL"),
        _Schedule(4, 16, "OVERLAP_12_16", "ADX_TREND"),
        _Schedule(8, 1, "ALL", "ADX_RANGE"),
    )


def _hypothesis_catalog(base_specs: Sequence[_BaseSpec], schedules: Sequence[_Schedule]) -> tuple[_Hypothesis, ...]:
    result: list[_Hypothesis] = []
    for base in base_specs:
        for schedule in schedules:
            candidate_id = (
                f"{base.base_id}__D{schedule.delay_bars}_C{schedule.cooldown_bars}_"
                f"{schedule.session}_{schedule.filter_id}"
            )
            complexity = base.complexity + int(schedule.session != "ALL") + int(schedule.filter_id != "NONE")
            result.append(
                _Hypothesis(
                    candidate_id,
                    base,
                    schedule.delay_bars,
                    schedule.cooldown_bars,
                    schedule.session,
                    schedule.filter_id,
                    complexity,
                )
            )
    return tuple(result)


def _base_signals(base: _BaseSpec, data: _SymbolData, delay: int) -> tuple[np.ndarray, np.ndarray]:
    execution = data.execution_indexes.astype(np.int64, copy=False)
    reference = execution - 1 - int(delay)
    store = data.features
    execution_high = store.high[execution]
    execution_low = store.low[execution]
    reference_close = store.close[reference]
    parameters = base.parameters
    family = base.family

    if family in {"MA_TOUCH", "PRICE_MA_CROSS"}:
        level = store.ema(int(parameters["period"])) if parameters["kind"] == "EMA" else store.sma(int(parameters["period"]))
        selected_level = level[reference]
        valid = np.isfinite(selected_level)
        if family == "PRICE_MA_CROSS":
            buy = valid & (reference_close <= selected_level) & (execution_high >= selected_level)
            sell = valid & (reference_close >= selected_level) & (execution_low <= selected_level)
            return buy, sell
        touch = valid & (execution_low <= selected_level) & (execution_high >= selected_level)
        above = reference_close >= selected_level
        if parameters["mode"] == "TREND":
            return touch & above, touch & ~above
        return touch & ~above, touch & above

    if family == "MA_CROSS":
        fast = store.ema(int(parameters["fast"])) if parameters["kind"] == "EMA" else store.sma(int(parameters["fast"]))
        slow = store.ema(int(parameters["slow"])) if parameters["kind"] == "EMA" else store.sma(int(parameters["slow"]))
        previous_reference = reference - 1
        valid = np.isfinite(fast[reference]) & np.isfinite(slow[reference]) & np.isfinite(fast[previous_reference]) & np.isfinite(slow[previous_reference])
        executable = (execution_low <= fast[reference]) & (execution_high >= fast[reference])
        buy = valid & executable & (fast[previous_reference] <= slow[previous_reference]) & (fast[reference] > slow[reference])
        sell = valid & executable & (fast[previous_reference] >= slow[previous_reference]) & (fast[reference] < slow[reference])
        return buy, sell

    period = int(parameters["period"])
    multiplier = float(parameters.get("multiplier", 1.0))
    mode = str(parameters["mode"])
    if family == "BOLLINGER":
        center = store.sma(period)[reference]
        width = multiplier * store.std(period)[reference]
        upper, lower = center + width, center - width
    elif family == "KELTNER":
        center = store.ema(period)[reference]
        width = multiplier * store.atr(period)[reference]
        upper, lower = center + width, center - width
    elif family == "ATR_LEVEL":
        width = multiplier * store.atr(period)[reference]
        upper, lower = reference_close + width, reference_close - width
    elif family == "DONCHIAN":
        upper = store.donchian_high(period)[reference]
        lower = store.donchian_low(period)[reference]
    else:
        return np.zeros(execution.size, dtype=np.bool_), np.zeros(execution.size, dtype=np.bool_)
    valid = np.isfinite(upper) & np.isfinite(lower)
    upper_touch = valid & (execution_high >= upper)
    lower_touch = valid & (execution_low <= lower)
    return (upper_touch, lower_touch) if mode == "BREAKOUT" else (lower_touch, upper_touch)


def _apply_constraints(
    hypothesis: _Hypothesis,
    data: _SymbolData,
    raw_buy: np.ndarray,
    raw_sell: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    buy = raw_buy.copy()
    sell = raw_sell.copy()
    session_mask = _session_mask(data.hours_utc, hypothesis.session)
    buy &= session_mask
    sell &= session_mask
    reference = data.execution_indexes.astype(np.int64, copy=False) - 1 - hypothesis.delay_bars
    if hypothesis.filter_id == "RSI_REVERSAL":
        values = data.features.rsi14()[reference]
        buy &= values <= 35.0
        sell &= values >= 65.0
    elif hypothesis.filter_id == "RSI_MOMENTUM":
        values = data.features.rsi14()[reference]
        buy &= values >= 55.0
        sell &= values <= 45.0
    elif hypothesis.filter_id == "STOCH_REVERSAL":
        values = data.features.stochastic14()[reference]
        buy &= values <= 25.0
        sell &= values >= 75.0
    elif hypothesis.filter_id == "ADX_TREND":
        values = data.features.adx_like14()[reference]
        mask = values >= 20.0
        buy &= mask
        sell &= mask
    elif hypothesis.filter_id == "ADX_RANGE":
        values = data.features.adx_like14()[reference]
        mask = values <= 20.0
        buy &= mask
        sell &= mask
    return _cooldown_by_episode(buy, hypothesis.cooldown_bars), _cooldown_by_episode(sell, hypothesis.cooldown_bars)


def _cooldown_by_episode(raw: np.ndarray, cooldown: int) -> np.ndarray:
    if raw.size == 0 or not np.any(raw):
        return raw.copy()
    indexes = np.arange(raw.size, dtype=np.int64)
    starts = raw & np.r_[True, ~raw[:-1]]
    last_start = np.maximum.accumulate(np.where(starts, indexes, -raw.size - 1))
    return raw & ((indexes - last_start) % (int(cooldown) + 1) == 0)


def _session_mask(hours: np.ndarray, session: str) -> np.ndarray:
    if session == "ALL":
        return np.ones(hours.size, dtype=np.bool_)
    start, end = {
        "ASIA_00_08": (0, 8),
        "LONDON_07_16": (7, 16),
        "NEW_YORK_12_21": (12, 21),
        "OVERLAP_12_16": (12, 16),
    }[session]
    return (hours >= start) & (hours < end)


def _signal_counts(
    data: _SymbolData,
    raw_buy: np.ndarray,
    raw_sell: np.ndarray,
    buy: np.ndarray,
    sell: np.ndarray,
    mask: np.ndarray,
) -> _Counts:
    return _counts_from_arrays(
        data.label_buy[mask],
        data.label_sell[mask],
        raw_buy[mask],
        raw_sell[mask],
        buy[mask],
        sell[mask],
    )


def _counts_from_arrays(
    target_buy: np.ndarray,
    target_sell: np.ndarray,
    raw_buy: np.ndarray,
    raw_sell: np.ndarray,
    buy: np.ndarray,
    sell: np.ndarray,
) -> _Counts:
    target_event = target_buy | target_sell
    predicted_event = buy | sell
    return _Counts(
        opportunities=int(target_buy.size),
        positive_events=int(np.count_nonzero(target_event)),
        positive_directions=int(np.count_nonzero(target_buy) + np.count_nonzero(target_sell)),
        raw_direction_signals=int(np.count_nonzero(raw_buy) + np.count_nonzero(raw_sell)),
        direction_signals=int(np.count_nonzero(buy) + np.count_nonzero(sell)),
        buy_tp=int(np.count_nonzero(buy & target_buy)),
        buy_fp=int(np.count_nonzero(buy & ~target_buy)),
        buy_fn=int(np.count_nonzero(~buy & target_buy)),
        buy_tn=int(np.count_nonzero(~buy & ~target_buy)),
        sell_tp=int(np.count_nonzero(sell & target_sell)),
        sell_fp=int(np.count_nonzero(sell & ~target_sell)),
        sell_fn=int(np.count_nonzero(~sell & target_sell)),
        sell_tn=int(np.count_nonzero(~sell & ~target_sell)),
        event_tp=int(np.count_nonzero(predicted_event & target_event)),
        event_fp=int(np.count_nonzero(predicted_event & ~target_event)),
        event_fn=int(np.count_nonzero(~predicted_event & target_event)),
        event_tn=int(np.count_nonzero(~predicted_event & ~target_event)),
        exact_direction_set_matches=int(np.count_nonzero(target_event & (buy == target_buy) & (sell == target_sell))),
    )


def _finalize_counts(counts: _Counts) -> dict[str, object]:
    buy = _binary_metrics(counts.buy_tp, counts.buy_fp, counts.buy_fn, counts.buy_tn)
    sell = _binary_metrics(counts.sell_tp, counts.sell_fp, counts.sell_fn, counts.sell_tn)
    direction = _binary_metrics(
        counts.buy_tp + counts.sell_tp,
        counts.buy_fp + counts.sell_fp,
        counts.buy_fn + counts.sell_fn,
        counts.buy_tn + counts.sell_tn,
    )
    event = _binary_metrics(counts.event_tp, counts.event_fp, counts.event_fn, counts.event_tn)
    return {
        "opportunities": counts.opportunities,
        "positive_events": counts.positive_events,
        "negative_events": counts.opportunities - counts.positive_events,
        "positive_directions": counts.positive_directions,
        "raw_direction_signals": counts.raw_direction_signals,
        "direction_signals": counts.direction_signals,
        "suppressed_by_constraints_and_cooldown": max(
            counts.raw_direction_signals - counts.direction_signals,
            0,
        ),
        "buy": buy,
        "sell": sell,
        "direction_micro": direction,
        "event": event,
        "direction_matches": counts.buy_tp + counts.sell_tp,
        "direction_match_rate": round(_ratio(counts.buy_tp + counts.sell_tp, counts.positive_directions), 8),
        "exact_direction_set_matches": counts.exact_direction_set_matches,
        "exact_direction_set_rate": round(_ratio(counts.exact_direction_set_matches, counts.positive_events), 8),
    }


def _binary_metrics(tp: int, fp: int, fn: int, tn: int) -> dict[str, object]:
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = _ratio(2.0 * precision * recall, precision + recall)
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / denominator if denominator else 0.0
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": round(precision, 8),
        "recall": round(recall, 8),
        "f1": round(f1, 8),
        "mcc": round(mcc, 8),
    }


def _hypothesis_metadata(hypothesis: _Hypothesis) -> dict[str, object]:
    return {
        "candidate_id": hypothesis.candidate_id,
        "base_id": hypothesis.base.base_id,
        "family": hypothesis.base.family,
        "parameters": dict(hypothesis.base.parameters),
        "delay_bars": hypothesis.delay_bars,
        "cooldown_bars": hypothesis.cooldown_bars,
        "session": hypothesis.session,
        "filter": hypothesis.filter_id,
        "complexity": hypothesis.complexity,
    }


def _ranking_key(row: Mapping[str, object]) -> tuple[float, float, float, float, int, str]:
    directional = dict(row.get("direction_micro", {}) or {})
    event = dict(row.get("event", {}) or {})
    return (
        -float(row.get("ranking_score", 0.0) or 0.0),
        -float(directional.get("mcc", 0.0) or 0.0),
        -float(directional.get("f1", 0.0) or 0.0),
        -float(event.get("f1", 0.0) or 0.0),
        int(row.get("direction_signals", 0) or 0),
        str(row.get("candidate_id", "")),
    )


def _coverage(
    positions: Sequence[MultiEATradePosition],
    datasets: Mapping[str, _SymbolData],
    adjacent_positions: int,
    eligible_positions: int,
) -> dict[str, object]:
    opportunities = int(sum(data.execution_indexes.size for data in datasets.values()))
    positive_events = int(
        sum(np.count_nonzero(data.label_buy | data.label_sell) for data in datasets.values())
    )
    positive_directions = int(
        sum(
            np.count_nonzero(data.label_buy) + np.count_nonzero(data.label_sell)
            for data in datasets.values()
        )
    )
    return {
        "source_positions": len(positions),
        "source_symbols": len({str(item.symbol).upper() for item in positions}),
        "opportunity_bars": int(opportunities),
        "positive_events": int(positive_events),
        "negative_events": int(opportunities - positive_events),
        "positive_directions": int(positive_directions),
        "hedged_events": int(sum(np.count_nonzero(data.label_buy & data.label_sell) for data in datasets.values())),
        "temporally_adjacent_positions": adjacent_positions,
        "eligible_positions": eligible_positions,
        "collapsed_positions": int(max(eligible_positions - positive_directions, 0)),
    }


def _split_counts(datasets: Mapping[str, _SymbolData]) -> dict[str, int]:
    result: dict[str, int] = {}
    for code, name in ((TRAIN, "train"), (EMBARGO, "embargo"), (VALIDATION, "validation")):
        result[f"{name}_opportunities"] = int(sum(np.count_nonzero(data.segments == code) for data in datasets.values()))
        result[f"{name}_positive_events"] = int(
            sum(np.count_nonzero((data.label_buy | data.label_sell) & (data.segments == code)) for data in datasets.values())
        )
    return result


def _m15_series(candles: Sequence[MultiEACandle]) -> dict[str, list[MultiEACandle]]:
    grouped: dict[str, dict[datetime, MultiEACandle]] = {}
    for candle in candles:
        if str(getattr(candle, "timeframe", "")).upper() != "M15":
            continue
        symbol = str(candle.symbol).strip().upper()
        grouped.setdefault(symbol, {})[_time_key(candle.timestamp)] = candle
    return {
        symbol: [values[key] for key in sorted(values)]
        for symbol, values in sorted(grouped.items())
    }


def _rolling_mean(values: np.ndarray, period: int) -> np.ndarray:
    result = np.full(values.size, np.nan, dtype=np.float64)
    if values.size < period:
        return result
    cumulative = np.r_[0.0, np.cumsum(values, dtype=np.float64)]
    result[period - 1 :] = (cumulative[period:] - cumulative[:-period]) / period
    return result


def _rolling_finite_mean(values: np.ndarray, period: int) -> np.ndarray:
    finite = np.isfinite(values)
    safe = np.where(finite, values, 0.0)
    sums = np.r_[0.0, np.cumsum(safe, dtype=np.float64)]
    counts = np.r_[0, np.cumsum(finite, dtype=np.int64)]
    result = np.full(values.size, np.nan, dtype=np.float64)
    if values.size >= period:
        window_counts = counts[period:] - counts[:-period]
        means = (sums[period:] - sums[:-period]) / period
        result[period - 1 :] = np.where(window_counts == period, means, np.nan)
    return result


def _rolling_std(values: np.ndarray, period: int) -> np.ndarray:
    mean = _rolling_mean(values, period)
    mean_square = _rolling_mean(values * values, period)
    return np.sqrt(np.maximum(mean_square - mean * mean, 0.0))


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    result = np.full(values.size, np.nan, dtype=np.float64)
    if values.size < period:
        return result
    result[period - 1] = float(np.mean(values[:period]))
    multiplier = 2.0 / (period + 1.0)
    for index in range(period, values.size):
        result[index] = (values[index] - result[index - 1]) * multiplier + result[index - 1]
    return result


def _rolling_extreme(values: np.ndarray, period: int, *, maximum: bool) -> np.ndarray:
    result = np.full(values.size, np.nan, dtype=np.float64)
    indexes: deque[int] = deque()
    for index, value in enumerate(values):
        while indexes and indexes[0] <= index - period:
            indexes.popleft()
        if maximum:
            while indexes and values[indexes[-1]] <= value:
                indexes.pop()
        else:
            while indexes and values[indexes[-1]] >= value:
                indexes.pop()
        indexes.append(index)
        if index >= period - 1:
            result[index] = values[indexes[0]]
    return result


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _time_key(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _validate_configuration(configuration: MultiEAIntrabarSearchConfiguration) -> None:
    if not 0.0 < configuration.train_fraction < 1.0:
        raise ValueError("train_fraction deve estar entre zero e um.")
    if configuration.common_history_bars < 201:
        raise ValueError("common_history_bars deve cobrir periodo 200 e atrasos.")
    if configuration.embargo_bars < 0:
        raise ValueError("embargo_bars nao pode ser negativo.")
    if configuration.maximum_ranked_candidates <= 0:
        raise ValueError("maximum_ranked_candidates deve ser positivo.")
    if not 1 <= configuration.portfolio_maximum_setups <= 8:
        raise ValueError("portfolio_maximum_setups deve estar entre 1 e 8.")
    if configuration.portfolio_candidate_pool < configuration.portfolio_maximum_setups:
        raise ValueError("portfolio_candidate_pool menor que o portfolio maximo.")
