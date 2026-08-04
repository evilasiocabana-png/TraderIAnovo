"""Mineracao causal e isolada de regras de entrada M15.

O minerador usa somente candles completamente fechados e os campos de entrada
observados. Os limiares de cada predicado sao quantis calculados no treino; as
regras ``AND`` e o portfolio ``OR`` tambem sao escolhidos apenas nesse segmento.
Saidas, lucro, comissao e swap nunca sao lidos.
"""

from __future__ import annotations

from array import array
from bisect import bisect_right
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Mapping, Sequence

from research.multi_ea_trading_lab import MultiEACandle, MultiEATradePosition


M15_DURATION = timedelta(minutes=15)
WAIT = 0
BUY = 1
SELL = 2

_FEATURE_NAMES = (
    "return_1",
    "return_3",
    "zscore_20",
    "rsi_14",
    "atr_pct_14",
    "body_atr_14",
    "range_atr_14",
    "ema_gap_9_21_pct",
    "donchian_position_20",
    "volume_zscore_20",
    "signal_hour",
)


@dataclass(frozen=True)
class MultiEAM15RuleMinerConfiguration:
    """Limites defensivos para uma busca reproduzivel em centenas de milhar de barras."""

    train_fraction: float = 0.70
    minimum_positive_events_for_split: int = 20
    minimum_validation_positive_events: int = 5
    common_history_bars: int = 60
    embargo_bars: int = 4
    quantiles: tuple[float, ...] = (0.10, 0.25, 0.75, 0.90)
    minimum_train_signals: int = 20
    minimum_train_true_positives: int = 2
    maximum_seed_predicates_per_direction: int = 12
    maximum_and_rules_per_direction: int = 16
    maximum_ranked_rules: int = 50
    maximum_portfolio_candidates: int = 24
    maximum_portfolio_rules: int = 6
    rule_complexity_penalty: float = 0.0001
    portfolio_rule_penalty: float = 0.00005
    minimum_portfolio_score_improvement: float = 1e-12


@dataclass(frozen=True, slots=True)
class RulePredicate:
    """Predicado univariado cujo limiar nasce exclusivamente do treino."""

    predicate_id: str
    feature: str
    operator: str
    threshold: float
    quantile: float

    def as_dict(self) -> dict[str, object]:
        return {
            "predicate_id": self.predicate_id,
            "feature": self.feature,
            "operator": self.operator,
            "threshold": _finite_round(self.threshold),
            "quantile": self.quantile,
            "threshold_source": "TRAIN_QUANTILE_ONLY",
        }


@dataclass(frozen=True, slots=True)
class _Opportunity:
    symbol: str
    candle_index: int
    signal_time: datetime
    observed_mask: int


@dataclass(slots=True)
class _RuleCandidate:
    rule_id: str
    direction: int
    predicates: tuple[RulePredicate, ...]
    mask: int
    train_metrics: dict[str, object]

    @property
    def complexity(self) -> int:
        return len(self.predicates)


class MultiEAM15RuleMiner:
    """Extrai predicados por quantis, regras ``AND`` e portfolio ``OR`` guloso."""

    def __init__(
        self,
        configuration: MultiEAM15RuleMinerConfiguration | None = None,
    ) -> None:
        self.configuration = configuration or MultiEAM15RuleMinerConfiguration()
        _validate_configuration(self.configuration)

    def analyze(
        self,
        positions: Sequence[MultiEATradePosition],
        candles: Sequence[MultiEACandle],
        *,
        source_timezone: str | None = None,
    ) -> dict[str, object]:
        """Minera regras sem usar saidas e congela o portfolio na validacao."""

        ordered_positions = sorted(
            positions,
            key=lambda item: _time_key(item.open_time),
        )
        series = _m15_series(candles)
        opportunities, coverage = self._opportunities(ordered_positions, series)
        train_indexes, validation_indexes, split = self._temporal_split(
            opportunities
        )

        base = {
            "schema_version": "multi_ea_rule_miner_v1",
            "status": "OK" if train_indexes else "SEM_AMOSTRA_DE_TREINO",
            "timeframe": "M15",
            "research_only": True,
            "operational_eligible": False,
            "lookahead": False,
            "uses_exit_data": False,
            "uses_observed_outcomes": False,
            "target": "ENTRADAS_MULTI_LABEL_BUY_SELL",
            "coverage": coverage,
            "split": split,
            "feature_policy": {
                "features": list(_FEATURE_NAMES),
                "cutoff": "CANDLE_M15_COMPLETAMENTE_FECHADO_ANTES_DA_ENTRADA",
                "normalization": "FEATURES_DE_PRECO_NORMALIZADAS_POR_PRECO_OU_ATR",
                "future_candles": False,
            },
            "predicate_policy": {
                "threshold_source": "TRAIN_QUANTILE_ONLY",
                "quantiles": list(self.configuration.quantiles),
                "lower_tail_operator": "<=",
                "upper_tail_operator": ">=",
                "validation_in_thresholds": False,
            },
            "warnings": self._warnings(source_timezone),
        }
        if not train_indexes:
            return {
                **base,
                "predicate_catalog": [],
                "rule_search": self._empty_rule_search(),
                "selected_portfolio": self._empty_portfolio(),
            }

        feature_sets = {
            symbol: _closed_feature_set(market)
            for symbol, market in series.items()
        }
        feature_values = _global_feature_values(opportunities, feature_sets)
        predicates, predicate_masks = self._predicate_masks(
            feature_values,
            train_indexes,
        )
        label_buy, label_sell = _label_bitsets(opportunities)
        train_segment = _segment_bitset(len(opportunities), train_indexes)
        validation_segment = _segment_bitset(
            len(opportunities),
            validation_indexes,
        )
        rules, search_diagnostics = self._mine_rules(
            predicates,
            predicate_masks,
            label_buy,
            label_sell,
            train_segment,
            len(train_indexes),
        )
        portfolio = self._greedy_portfolio(
            rules,
            label_buy,
            label_sell,
            train_segment,
            len(train_indexes),
            validation_segment,
            len(validation_indexes),
        )

        ranking = sorted(rules, key=_rule_sort_key, reverse=True)
        ranking = ranking[: self.configuration.maximum_ranked_rules]
        return {
            **base,
            "predicate_catalog": [item.as_dict() for item in predicates],
            "rule_search": {
                **search_diagnostics,
                "selection_segment": "TRAIN",
                "validation_policy": "FROZEN_AFTER_ALL_SELECTIONS",
                "score_formula": (
                    "F1 + 0.25*max(MCC,0) - penalty*(predicates-1)"
                ),
                "ranking_train": [self._rule_row(item) for item in ranking],
            },
            "selected_portfolio": portfolio,
        }

    run = analyze

    def _opportunities(
        self,
        positions: Sequence[MultiEATradePosition],
        series: Mapping[str, Sequence[MultiEACandle]],
    ) -> tuple[list[_Opportunity], dict[str, object]]:
        labels: dict[tuple[str, int], int] = {}
        eligible_positions = 0
        adjacent_positions = 0
        coverage_by_symbol: dict[str, Counter[str]] = {}
        close_times = {
            symbol: [_time_key(item.timestamp) + M15_DURATION for item in market]
            for symbol, market in series.items()
        }

        for position in positions:
            symbol = str(position.symbol).strip().upper()
            counter = coverage_by_symbol.setdefault(symbol, Counter())
            counter["source_positions"] += 1
            market = series.get(symbol)
            if not market:
                counter["without_series"] += 1
                continue
            entry_time = _time_key(position.open_time)
            times = close_times[symbol]
            candle_index = bisect_right(times, entry_time) - 1
            if candle_index < 0:
                counter["before_series"] += 1
                continue
            if not _temporally_adjacent(times[candle_index], entry_time):
                counter["without_adjacent_candle"] += 1
                continue
            adjacent_positions += 1
            counter["adjacent_positions"] += 1
            if candle_index < self.configuration.common_history_bars - 1:
                counter["without_warmup"] += 1
                continue
            direction = _direction_code(position.direction)
            if direction == WAIT:
                counter["invalid_direction"] += 1
                continue
            eligible_positions += 1
            counter["eligible_positions"] += 1
            key = (symbol, candle_index)
            labels[key] = labels.get(key, WAIT) | direction

        if not labels:
            return [], _coverage_payload(
                positions,
                series,
                coverage_by_symbol,
                adjacent_positions,
                eligible_positions,
                labels,
                (),
            )

        first_signal = min(
            close_times[symbol][index] for symbol, index in labels
        )
        last_entry = max(_time_key(item.open_time) for item in positions)
        opportunities: list[_Opportunity] = []
        start_index = self.configuration.common_history_bars - 1
        for symbol, market in series.items():
            times = close_times[symbol]
            for index in range(start_index, len(market)):
                signal_time = times[index]
                if signal_time < first_signal:
                    continue
                if signal_time > last_entry:
                    break
                opportunities.append(
                    _Opportunity(
                        symbol=symbol,
                        candle_index=index,
                        signal_time=signal_time,
                        observed_mask=labels.get((symbol, index), WAIT),
                    )
                )
        opportunities.sort(
            key=lambda item: (item.signal_time, item.symbol, item.candle_index)
        )
        return opportunities, _coverage_payload(
            positions,
            series,
            coverage_by_symbol,
            adjacent_positions,
            eligible_positions,
            labels,
            opportunities,
        )

    def _temporal_split(
        self,
        opportunities: Sequence[_Opportunity],
    ) -> tuple[list[int], list[int], dict[str, object]]:
        positive_times = [
            item.signal_time for item in opportunities if item.observed_mask != WAIT
        ]
        if (
            len(positive_times)
            < self.configuration.minimum_positive_events_for_split
            or len(positive_times)
            <= self.configuration.minimum_validation_positive_events
        ):
            train = list(range(len(opportunities)))
            return train, [], {
                "method": "TREINO_UNICO_EVIDENCIA_INSUFICIENTE_PARA_VALIDACAO",
                "train_opportunities": len(train),
                "validation_opportunities": 0,
                "embargo_opportunities": 0,
                "train_positive_events": len(positive_times),
                "validation_positive_events": 0,
                "embargo_bars": self.configuration.embargo_bars,
                "train_end": (
                    opportunities[-1].signal_time.isoformat()
                    if opportunities
                    else None
                ),
                "validation_start": None,
            }

        validation_minimum = self.configuration.minimum_validation_positive_events
        desired_train = int(len(positive_times) * self.configuration.train_fraction)
        train_positive = max(1, min(desired_train, len(positive_times) - validation_minimum))
        train_end = positive_times[train_positive - 1]
        validation_start = train_end + M15_DURATION * (
            self.configuration.embargo_bars + 1
        )
        validation_positive = sum(
            item.observed_mask != WAIT and item.signal_time >= validation_start
            for item in opportunities
        )
        while validation_positive < validation_minimum and train_positive > 1:
            train_positive -= 1
            train_end = positive_times[train_positive - 1]
            validation_start = train_end + M15_DURATION * (
                self.configuration.embargo_bars + 1
            )
            validation_positive = sum(
                item.observed_mask != WAIT and item.signal_time >= validation_start
                for item in opportunities
            )

        train_indexes = [
            index
            for index, item in enumerate(opportunities)
            if item.signal_time <= train_end
        ]
        validation_indexes = [
            index
            for index, item in enumerate(opportunities)
            if item.signal_time >= validation_start
        ]
        embargo_opportunities = (
            len(opportunities) - len(train_indexes) - len(validation_indexes)
        )
        return train_indexes, validation_indexes, {
            "method": "CRONOLOGICO_TREINO_VALIDACAO_COM_EMBARGO",
            "train_opportunities": len(train_indexes),
            "validation_opportunities": len(validation_indexes),
            "embargo_opportunities": embargo_opportunities,
            "train_positive_events": sum(
                opportunities[index].observed_mask != WAIT
                for index in train_indexes
            ),
            "validation_positive_events": sum(
                opportunities[index].observed_mask != WAIT
                for index in validation_indexes
            ),
            "embargo_bars": self.configuration.embargo_bars,
            "train_end": train_end.isoformat(),
            "validation_start": validation_start.isoformat(),
        }

    def _predicate_masks(
        self,
        feature_values: Mapping[str, Sequence[float]],
        train_indexes: Sequence[int],
    ) -> tuple[list[RulePredicate], dict[str, int]]:
        predicates: list[RulePredicate] = []
        masks: dict[str, int] = {}
        seen: set[tuple[str, str, float]] = set()
        total = len(next(iter(feature_values.values()), ()))
        for feature in _FEATURE_NAMES:
            values = feature_values[feature]
            train_values = sorted(
                value
                for index in train_indexes
                if math.isfinite(value := float(values[index]))
            )
            if not train_values:
                continue
            for quantile in self.configuration.quantiles:
                operator = "<=" if quantile < 0.5 else ">="
                threshold = _quantile_sorted(train_values, quantile)
                identity = (feature, operator, round(threshold, 12))
                if identity in seen:
                    continue
                seen.add(identity)
                q_label = int(round(quantile * 100))
                op_label = "LE" if operator == "<=" else "GE"
                predicate_id = f"P_{feature.upper()}_{op_label}_Q{q_label:02d}"
                predicate = RulePredicate(
                    predicate_id=predicate_id,
                    feature=feature,
                    operator=operator,
                    threshold=threshold,
                    quantile=quantile,
                )
                if operator == "<=":
                    mask_bytes = bytearray(
                        1 if math.isfinite(value) and value <= threshold else 0
                        for value in values
                    )
                else:
                    mask_bytes = bytearray(
                        1 if math.isfinite(value) and value >= threshold else 0
                        for value in values
                    )
                if len(mask_bytes) != total:
                    raise RuntimeError("Mascara de predicado com tamanho inconsistente.")
                predicates.append(predicate)
                masks[predicate_id] = int.from_bytes(mask_bytes, "little")
        return predicates, masks

    def _mine_rules(
        self,
        predicates: Sequence[RulePredicate],
        masks: Mapping[str, int],
        label_buy: int,
        label_sell: int,
        train_segment: int,
        train_count: int,
    ) -> tuple[list[_RuleCandidate], dict[str, object]]:
        seeds_by_direction: dict[int, list[_RuleCandidate]] = {BUY: [], SELL: []}
        seed_evaluated = 0
        for predicate in predicates:
            mask = masks[predicate.predicate_id]
            for direction in (BUY, SELL):
                seed_evaluated += 1
                observed = label_buy if direction == BUY else label_sell
                metrics = _direction_metrics_bits(
                    mask,
                    observed,
                    train_segment,
                    train_count,
                )
                if not self._eligible_metrics(metrics):
                    continue
                metrics["selection_score"] = _rule_score(
                    metrics,
                    complexity=1,
                    penalty=self.configuration.rule_complexity_penalty,
                )
                seeds_by_direction[direction].append(
                    _RuleCandidate(
                        rule_id=(
                            f"RULE_{_direction_name(direction)}_"
                            f"{predicate.predicate_id}"
                        ),
                        direction=direction,
                        predicates=(predicate,),
                        mask=mask,
                        train_metrics=metrics,
                    )
                )

        selected_seeds: dict[int, list[_RuleCandidate]] = {}
        for direction, rows in seeds_by_direction.items():
            selected_seeds[direction] = sorted(
                rows,
                key=_rule_sort_key,
                reverse=True,
            )[: self.configuration.maximum_seed_predicates_per_direction]

        and_rules: list[_RuleCandidate] = []
        and_evaluated = 0
        for direction, seeds in selected_seeds.items():
            candidates: list[_RuleCandidate] = []
            for left_index, left in enumerate(seeds):
                for right in seeds[left_index + 1 :]:
                    if left.predicates[0].feature == right.predicates[0].feature:
                        continue
                    and_evaluated += 1
                    mask = left.mask & right.mask
                    observed = label_buy if direction == BUY else label_sell
                    metrics = _direction_metrics_bits(
                        mask,
                        observed,
                        train_segment,
                        train_count,
                    )
                    if not self._eligible_metrics(metrics):
                        continue
                    metrics["selection_score"] = _rule_score(
                        metrics,
                        complexity=2,
                        penalty=self.configuration.rule_complexity_penalty,
                    )
                    pair_predicates = tuple(
                        sorted(
                            (left.predicates[0], right.predicates[0]),
                            key=lambda item: item.predicate_id,
                        )
                    )
                    candidates.append(
                        _RuleCandidate(
                            rule_id=(
                                f"RULE_{_direction_name(direction)}_AND_"
                                f"{pair_predicates[0].predicate_id}__"
                                f"{pair_predicates[1].predicate_id}"
                            ),
                            direction=direction,
                            predicates=pair_predicates,
                            mask=mask,
                            train_metrics=metrics,
                        )
                    )
            and_rules.extend(
                sorted(candidates, key=_rule_sort_key, reverse=True)[
                    : self.configuration.maximum_and_rules_per_direction
                ]
            )

        rules = [
            item
            for direction in (BUY, SELL)
            for item in selected_seeds[direction]
        ]
        rules.extend(and_rules)
        return rules, {
            "predicates_evaluated": len(predicates),
            "seed_directional_rules_evaluated": seed_evaluated,
            "eligible_seed_rules": sum(len(rows) for rows in seeds_by_direction.values()),
            "seed_rules_retained": sum(len(rows) for rows in selected_seeds.values()),
            "and_rules_evaluated": and_evaluated,
            "and_rules_retained": len(and_rules),
            "eligible_rules_for_portfolio": len(rules),
        }

    def _greedy_portfolio(
        self,
        rules: Sequence[_RuleCandidate],
        label_buy: int,
        label_sell: int,
        train_segment: int,
        train_count: int,
        validation_segment: int,
        validation_count: int,
    ) -> dict[str, object]:
        ordered = sorted(rules, key=_rule_sort_key, reverse=True)
        remaining = ordered[: self.configuration.maximum_portfolio_candidates]
        buy_mask = 0
        sell_mask = 0
        selected: list[_RuleCandidate] = []
        trace: list[dict[str, object]] = []
        current_metrics = _multi_label_metrics_bits(
            buy_mask,
            sell_mask,
            label_buy,
            label_sell,
            train_segment,
            train_count,
        )
        current_score = _portfolio_score(
            current_metrics,
            rule_count=0,
            penalty=self.configuration.portfolio_rule_penalty,
        )

        while remaining and len(selected) < self.configuration.maximum_portfolio_rules:
            best: _RuleCandidate | None = None
            best_metrics: dict[str, object] | None = None
            best_score = current_score
            best_key: tuple[object, ...] | None = None
            for candidate in remaining:
                candidate_buy = (
                    buy_mask | candidate.mask
                    if candidate.direction == BUY
                    else buy_mask
                )
                candidate_sell = (
                    sell_mask | candidate.mask
                    if candidate.direction == SELL
                    else sell_mask
                )
                metrics = _multi_label_metrics_bits(
                    candidate_buy,
                    candidate_sell,
                    label_buy,
                    label_sell,
                    train_segment,
                    train_count,
                )
                score = _portfolio_score(
                    metrics,
                    rule_count=len(selected) + 1,
                    penalty=self.configuration.portfolio_rule_penalty,
                )
                key = (
                    score,
                    float(metrics["mcc"]),
                    float(metrics["f1"]),
                    float(metrics["precision"]),
                    -int(metrics["predicted_labels"]),
                    candidate.rule_id,
                )
                if best_key is None or key > best_key:
                    best = candidate
                    best_metrics = metrics
                    best_score = score
                    best_key = key
            if (
                best is None
                or best_metrics is None
                or best_score
                <= current_score
                + self.configuration.minimum_portfolio_score_improvement
            ):
                break
            if best.direction == BUY:
                buy_mask |= best.mask
            else:
                sell_mask |= best.mask
            selected.append(best)
            remaining = [item for item in remaining if item.rule_id != best.rule_id]
            trace.append(
                {
                    "step": len(selected),
                    "rule_id": best.rule_id,
                    "direction": _direction_name(best.direction),
                    "train_score_before": _finite_round(current_score),
                    "train_score_after": _finite_round(best_score),
                    "train_metrics_after": best_metrics,
                }
            )
            current_metrics = best_metrics
            current_score = best_score

        validation_metrics = _multi_label_metrics_bits(
            buy_mask,
            sell_mask,
            label_buy,
            label_sell,
            validation_segment,
            validation_count,
        )
        return {
            "method": "GREEDY_OR",
            "selection_segment": "TRAIN",
            "validation_policy": "FROZEN",
            "rule_count": len(selected),
            "rule_ids": [item.rule_id for item in selected],
            "rules": [self._rule_row(item) for item in selected],
            "selection_trace": trace,
            "train_score": _finite_round(current_score),
            "train_metrics": current_metrics,
            "validation_metrics_frozen": validation_metrics,
        }

    def _eligible_metrics(self, metrics: Mapping[str, object]) -> bool:
        return (
            int(metrics["signals"]) >= self.configuration.minimum_train_signals
            and int(metrics["true_positive"])
            >= self.configuration.minimum_train_true_positives
        )

    def _rule_row(self, candidate: _RuleCandidate) -> dict[str, object]:
        return {
            "rule_id": candidate.rule_id,
            "direction": _direction_name(candidate.direction),
            "logic": "AND" if candidate.complexity > 1 else "SINGLE_PREDICATE",
            "complexity": candidate.complexity,
            "predicates": [item.as_dict() for item in candidate.predicates],
            "train_metrics": candidate.train_metrics,
        }

    def _warnings(self, source_timezone: str | None) -> list[str]:
        warnings = [
            "RESEARCH_ONLY: regras mineradas nao podem alimentar Demo ou conta real.",
            "TRAIN_ONLY: quantis, regras AND e portfolio OR sao escolhidos no treino.",
            "VALIDACAO_CONGELADA: nenhuma metrica da validacao altera a selecao.",
            "MULTI_LABEL: BUY e SELL simultaneos no mesmo simbolo/janela sao preservados.",
            "ENTRADAS_SOMENTE: saida, P&L, comissao e swap nao sao lidos.",
        ]
        if not source_timezone:
            warnings.append(
                "FUSO_NAO_INFORMADO: timestamps naive permanecem na escala fornecida."
            )
        return warnings

    @staticmethod
    def _empty_rule_search() -> dict[str, object]:
        return {
            "predicates_evaluated": 0,
            "seed_directional_rules_evaluated": 0,
            "eligible_seed_rules": 0,
            "seed_rules_retained": 0,
            "and_rules_evaluated": 0,
            "and_rules_retained": 0,
            "eligible_rules_for_portfolio": 0,
            "selection_segment": "TRAIN",
            "validation_policy": "FROZEN_AFTER_ALL_SELECTIONS",
            "ranking_train": [],
        }

    @staticmethod
    def _empty_portfolio() -> dict[str, object]:
        empty = _empty_metrics()
        return {
            "method": "GREEDY_OR",
            "selection_segment": "TRAIN",
            "validation_policy": "FROZEN",
            "rule_count": 0,
            "rule_ids": [],
            "rules": [],
            "selection_trace": [],
            "train_score": 0.0,
            "train_metrics": empty,
            "validation_metrics_frozen": empty,
        }


def _closed_feature_set(
    candles: Sequence[MultiEACandle],
) -> dict[str, array]:
    count = len(candles)
    result = {
        name: array("d", [math.nan]) * count for name in _FEATURE_NAMES
    }
    if not candles:
        return result

    closes = [float(item.close) for item in candles]
    ema9 = closes[0]
    ema21 = closes[0]
    alpha9 = 2.0 / 10.0
    alpha21 = 2.0 / 22.0
    close20: deque[float] = deque()
    volume20: deque[float] = deque()
    gain14: deque[float] = deque()
    loss14: deque[float] = deque()
    true_range14: deque[float] = deque()
    close_sum = 0.0
    close_sumsq = 0.0
    volume_sum = 0.0
    volume_sumsq = 0.0
    gain_sum = 0.0
    loss_sum = 0.0
    tr_sum = 0.0
    high_queue: deque[int] = deque()
    low_queue: deque[int] = deque()

    for index, candle in enumerate(candles):
        close = closes[index]
        if index:
            ema9 += alpha9 * (close - ema9)
            ema21 += alpha21 * (close - ema21)
            change = close - closes[index - 1]
            gain = max(change, 0.0)
            loss = max(-change, 0.0)
            gain14.append(gain)
            loss14.append(loss)
            gain_sum += gain
            loss_sum += loss
            if len(gain14) > 14:
                gain_sum -= gain14.popleft()
                loss_sum -= loss14.popleft()
            true_range = max(
                float(candle.high) - float(candle.low),
                abs(float(candle.high) - closes[index - 1]),
                abs(float(candle.low) - closes[index - 1]),
            )
        else:
            true_range = float(candle.high) - float(candle.low)
        true_range14.append(true_range)
        tr_sum += true_range
        if len(true_range14) > 14:
            tr_sum -= true_range14.popleft()

        close20.append(close)
        close_sum += close
        close_sumsq += close * close
        if len(close20) > 20:
            old = close20.popleft()
            close_sum -= old
            close_sumsq -= old * old

        volume = float(candle.volume or 0.0)
        volume20.append(volume)
        volume_sum += volume
        volume_sumsq += volume * volume
        if len(volume20) > 20:
            old_volume = volume20.popleft()
            volume_sum -= old_volume
            volume_sumsq -= old_volume * old_volume

        while high_queue and float(candles[high_queue[-1]].high) <= float(candle.high):
            high_queue.pop()
        high_queue.append(index)
        while low_queue and float(candles[low_queue[-1]].low) >= float(candle.low):
            low_queue.pop()
        low_queue.append(index)
        first_donchian = index - 19
        while high_queue and high_queue[0] < first_donchian:
            high_queue.popleft()
        while low_queue and low_queue[0] < first_donchian:
            low_queue.popleft()

        if index >= 1 and closes[index - 1]:
            result["return_1"][index] = close / closes[index - 1] - 1.0
        if index >= 3 and closes[index - 3]:
            result["return_3"][index] = close / closes[index - 3] - 1.0
        if len(close20) == 20:
            mean = close_sum / 20.0
            variance = max(close_sumsq / 20.0 - mean * mean, 0.0)
            deviation = math.sqrt(variance)
            result["zscore_20"][index] = (
                (close - mean) / deviation if deviation else 0.0
            )
        if len(gain14) == 14:
            if loss_sum == 0.0:
                rsi = 100.0 if gain_sum > 0.0 else 50.0
            else:
                rsi = 100.0 - 100.0 / (1.0 + gain_sum / loss_sum)
            result["rsi_14"][index] = rsi
        atr = tr_sum / len(true_range14) if len(true_range14) == 14 else math.nan
        if math.isfinite(atr) and close:
            result["atr_pct_14"][index] = atr / abs(close)
            if atr:
                result["body_atr_14"][index] = (
                    float(candle.close) - float(candle.open)
                ) / atr
                result["range_atr_14"][index] = (
                    float(candle.high) - float(candle.low)
                ) / atr
        if close:
            result["ema_gap_9_21_pct"][index] = (ema9 - ema21) / abs(close)
        if index >= 19:
            donchian_high = float(candles[high_queue[0]].high)
            donchian_low = float(candles[low_queue[0]].low)
            width = donchian_high - donchian_low
            result["donchian_position_20"][index] = (
                (close - donchian_low) / width if width else 0.5
            )
        if len(volume20) == 20:
            volume_mean = volume_sum / 20.0
            volume_variance = max(
                volume_sumsq / 20.0 - volume_mean * volume_mean,
                0.0,
            )
            volume_deviation = math.sqrt(volume_variance)
            result["volume_zscore_20"][index] = (
                (volume - volume_mean) / volume_deviation
                if volume_deviation
                else 0.0
            )
        close_time = _time_key(candle.timestamp) + M15_DURATION
        result["signal_hour"][index] = (
            close_time.hour + close_time.minute / 60.0
        )
    return result


def _global_feature_values(
    opportunities: Sequence[_Opportunity],
    feature_sets: Mapping[str, Mapping[str, Sequence[float]]],
) -> dict[str, array]:
    return {
        feature: array(
            "d",
            (
                feature_sets[item.symbol][feature][item.candle_index]
                for item in opportunities
            ),
        )
        for feature in _FEATURE_NAMES
    }


def _label_bitsets(
    opportunities: Sequence[_Opportunity],
) -> tuple[int, int]:
    buy = bytearray(
        1 if item.observed_mask & BUY else 0 for item in opportunities
    )
    sell = bytearray(
        1 if item.observed_mask & SELL else 0 for item in opportunities
    )
    return int.from_bytes(buy, "little"), int.from_bytes(sell, "little")


def _segment_bitset(length: int, indexes: Sequence[int]) -> int:
    values = bytearray(length)
    for index in indexes:
        values[index] = 1
    return int.from_bytes(values, "little")


def _direction_metrics_bits(
    signal_mask: int,
    observed_mask: int,
    segment_mask: int,
    opportunities: int,
) -> dict[str, object]:
    predicted = signal_mask & segment_mask
    observed = observed_mask & segment_mask
    true_positive = (predicted & observed).bit_count()
    false_positive = (predicted & ~observed & segment_mask).bit_count()
    false_negative = (observed & ~predicted & segment_mask).bit_count()
    true_negative = opportunities - true_positive - false_positive - false_negative
    return _metrics_payload(
        true_positive,
        false_positive,
        false_negative,
        true_negative,
        opportunities=opportunities,
        signals=true_positive + false_positive,
    )


def _multi_label_metrics_bits(
    buy_mask: int,
    sell_mask: int,
    label_buy: int,
    label_sell: int,
    segment_mask: int,
    opportunities: int,
) -> dict[str, object]:
    buy_predicted = buy_mask & segment_mask
    sell_predicted = sell_mask & segment_mask
    buy_observed = label_buy & segment_mask
    sell_observed = label_sell & segment_mask

    buy_true_positive = (buy_predicted & buy_observed).bit_count()
    sell_true_positive = (sell_predicted & sell_observed).bit_count()
    true_positive = buy_true_positive + sell_true_positive
    false_positive = (
        (buy_predicted & ~buy_observed & segment_mask).bit_count()
        + (sell_predicted & ~sell_observed & segment_mask).bit_count()
    )
    false_negative = (
        (buy_observed & ~buy_predicted & segment_mask).bit_count()
        + (sell_observed & ~sell_predicted & segment_mask).bit_count()
    )
    true_negative = (
        opportunities * 2 - true_positive - false_positive - false_negative
    )
    predicted_event_mask = buy_predicted | sell_predicted
    observed_event_mask = buy_observed | sell_observed
    matched_event_mask = (
        (buy_predicted & buy_observed) | (sell_predicted & sell_observed)
    )
    mismatch_mask = (
        (buy_predicted ^ buy_observed) | (sell_predicted ^ sell_observed)
    ) & segment_mask
    exact_event_mask = observed_event_mask & ~mismatch_mask & segment_mask
    predicted_events = predicted_event_mask.bit_count()
    observed_events = observed_event_mask.bit_count()
    matched_events = matched_event_mask.bit_count()
    exact_events = exact_event_mask.bit_count()

    payload = _metrics_payload(
        true_positive,
        false_positive,
        false_negative,
        true_negative,
        opportunities=opportunities,
        signals=true_positive + false_positive,
    )
    payload.update(
        {
            "evaluation": "MICRO_AVERAGE_BUY_SELL_MULTI_LABEL",
            "predicted_labels": true_positive + false_positive,
            "observed_labels": true_positive + false_negative,
            "predicted_events": predicted_events,
            "observed_events": observed_events,
            "matched_events": matched_events,
            "exact_multi_label_events": exact_events,
            "event_recall": _safe_ratio(matched_events, observed_events),
            "event_precision": _safe_ratio(matched_events, predicted_events),
        }
    )
    return payload


def _direction_metrics(
    signal_mask: Sequence[int],
    labels: Sequence[int],
    direction: int,
    indexes: Sequence[int],
) -> dict[str, object]:
    true_positive = false_positive = false_negative = true_negative = 0
    for index in indexes:
        predicted = bool(signal_mask[index])
        observed = bool(labels[index] & direction)
        if predicted and observed:
            true_positive += 1
        elif predicted:
            false_positive += 1
        elif observed:
            false_negative += 1
        else:
            true_negative += 1
    return _metrics_payload(
        true_positive,
        false_positive,
        false_negative,
        true_negative,
        opportunities=len(indexes),
        signals=true_positive + false_positive,
    )


def _multi_label_metrics(
    buy_mask: Sequence[int],
    sell_mask: Sequence[int],
    labels: Sequence[int],
    indexes: Sequence[int],
) -> dict[str, object]:
    true_positive = false_positive = false_negative = true_negative = 0
    matched_events = predicted_events = observed_events = exact_events = 0
    for index in indexes:
        observed_mask = int(labels[index])
        predicted_mask = (BUY if buy_mask[index] else WAIT) | (
            SELL if sell_mask[index] else WAIT
        )
        observed_events += observed_mask != WAIT
        predicted_events += predicted_mask != WAIT
        matched_events += bool(observed_mask & predicted_mask)
        exact_events += observed_mask != WAIT and observed_mask == predicted_mask
        for direction in (BUY, SELL):
            predicted = bool(predicted_mask & direction)
            observed = bool(observed_mask & direction)
            if predicted and observed:
                true_positive += 1
            elif predicted:
                false_positive += 1
            elif observed:
                false_negative += 1
            else:
                true_negative += 1
    payload = _metrics_payload(
        true_positive,
        false_positive,
        false_negative,
        true_negative,
        opportunities=len(indexes),
        signals=true_positive + false_positive,
    )
    payload.update(
        {
            "evaluation": "MICRO_AVERAGE_BUY_SELL_MULTI_LABEL",
            "predicted_labels": true_positive + false_positive,
            "observed_labels": true_positive + false_negative,
            "predicted_events": predicted_events,
            "observed_events": observed_events,
            "matched_events": matched_events,
            "exact_multi_label_events": exact_events,
            "event_recall": _safe_ratio(matched_events, observed_events),
            "event_precision": _safe_ratio(matched_events, predicted_events),
        }
    )
    return payload


def _metrics_payload(
    true_positive: int,
    false_positive: int,
    false_negative: int,
    true_negative: int,
    *,
    opportunities: int,
    signals: int,
) -> dict[str, object]:
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = _safe_ratio(2.0 * precision * recall, precision + recall)
    denominator = math.sqrt(
        (true_positive + false_positive)
        * (true_positive + false_negative)
        * (true_negative + false_positive)
        * (true_negative + false_negative)
    )
    mcc = (
        (true_positive * true_negative - false_positive * false_negative)
        / denominator
        if denominator
        else 0.0
    )
    prevalence = _safe_ratio(
        true_positive + false_negative,
        opportunities,
    )
    return {
        "opportunities": opportunities,
        "signals": signals,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision": _finite_round(precision),
        "recall": _finite_round(recall),
        "f1": _finite_round(f1),
        "mcc": _finite_round(mcc),
        "prevalence": _finite_round(prevalence),
        "precision_lift_over_prevalence": _finite_round(
            precision / prevalence if prevalence else 0.0
        ),
        "signals_per_1000_bars": _finite_round(
            1000.0 * signals / opportunities if opportunities else 0.0
        ),
    }


def _rule_score(
    metrics: Mapping[str, object],
    *,
    complexity: int,
    penalty: float,
) -> float:
    return _finite_round(
        float(metrics["f1"])
        + 0.25 * max(float(metrics["mcc"]), 0.0)
        - penalty * max(complexity - 1, 0)
    )


def _portfolio_score(
    metrics: Mapping[str, object],
    *,
    rule_count: int,
    penalty: float,
) -> float:
    return _finite_round(
        float(metrics["f1"])
        + 0.25 * max(float(metrics["mcc"]), 0.0)
        - penalty * rule_count
    )


def _rule_sort_key(candidate: _RuleCandidate) -> tuple[object, ...]:
    metrics = candidate.train_metrics
    return (
        float(metrics.get("selection_score", 0.0)),
        float(metrics["mcc"]),
        float(metrics["f1"]),
        float(metrics["precision"]),
        float(metrics["recall"]),
        -int(metrics["signals"]),
        candidate.rule_id,
    )


def _coverage_payload(
    positions: Sequence[MultiEATradePosition],
    series: Mapping[str, Sequence[MultiEACandle]],
    by_symbol: Mapping[str, Counter[str]],
    adjacent_positions: int,
    eligible_positions: int,
    labels: Mapping[tuple[str, int], int],
    opportunities: Sequence[_Opportunity],
) -> dict[str, object]:
    positive_events = len(labels)
    return {
        "source_positions": len(positions),
        "source_markets": len({str(item.symbol).upper() for item in positions}),
        "m15_markets": len(series),
        "m15_candles": sum(len(items) for items in series.values()),
        "temporally_adjacent_positions": adjacent_positions,
        "eligible_positions": eligible_positions,
        "positive_events": positive_events,
        "collapsed_positions": max(eligible_positions - positive_events, 0),
        "multi_label_events": sum(mask == (BUY | SELL) for mask in labels.values()),
        "opportunity_bars": len(opportunities),
        "negative_events": sum(item.observed_mask == WAIT for item in opportunities),
        "by_symbol": {
            symbol: dict(sorted(counter.items()))
            for symbol, counter in sorted(by_symbol.items())
        },
    }


def _m15_series(
    candles: Sequence[MultiEACandle],
) -> dict[str, list[MultiEACandle]]:
    grouped: dict[str, dict[datetime, MultiEACandle]] = {}
    for candle in candles:
        if str(getattr(candle, "timeframe", "")).upper() != "M15":
            continue
        symbol = str(candle.symbol).strip().upper()
        if not symbol:
            continue
        grouped.setdefault(symbol, {})[_time_key(candle.timestamp)] = candle
    return {
        symbol: [by_time[key] for key in sorted(by_time)]
        for symbol, by_time in sorted(grouped.items())
    }


def _temporally_adjacent(candle_close: datetime, entry_time: datetime) -> bool:
    gap = entry_time - candle_close
    if gap < timedelta(0):
        return False
    if gap <= M15_DURATION * 2:
        return True
    return (
        entry_time.weekday() == 0
        and candle_close.weekday() in {4, 5, 6}
        and gap <= timedelta(hours=72)
    )


def _time_key(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _direction_code(value: object) -> int:
    normalized = str(value or "").strip().upper()
    if normalized == "BUY":
        return BUY
    if normalized == "SELL":
        return SELL
    return WAIT


def _direction_name(value: int) -> str:
    return "BUY" if value == BUY else "SELL" if value == SELL else "WAIT"


def _quantile_sorted(values: Sequence[float], quantile: float) -> float:
    if not values:
        return 0.0
    position = (len(values) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return float(values[lower] + (values[upper] - values[lower]) * fraction)


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _finite_round(value: float, digits: int = 8) -> float:
    return round(float(value), digits) if math.isfinite(float(value)) else 0.0


def _empty_metrics() -> dict[str, object]:
    payload = _metrics_payload(0, 0, 0, 0, opportunities=0, signals=0)
    payload.update(
        {
            "evaluation": "MICRO_AVERAGE_BUY_SELL_MULTI_LABEL",
            "predicted_labels": 0,
            "observed_labels": 0,
            "predicted_events": 0,
            "observed_events": 0,
            "matched_events": 0,
            "exact_multi_label_events": 0,
            "event_recall": 0.0,
            "event_precision": 0.0,
        }
    )
    return payload


def _validate_configuration(configuration: MultiEAM15RuleMinerConfiguration) -> None:
    if not 0.0 < configuration.train_fraction < 1.0:
        raise ValueError("train_fraction deve estar entre zero e um.")
    if configuration.minimum_positive_events_for_split < 2:
        raise ValueError("minimum_positive_events_for_split deve ser pelo menos 2.")
    if configuration.minimum_validation_positive_events < 1:
        raise ValueError("minimum_validation_positive_events deve ser positivo.")
    if configuration.common_history_bars < 20:
        raise ValueError("common_history_bars deve ser pelo menos 20.")
    if configuration.embargo_bars < 0:
        raise ValueError("embargo_bars nao pode ser negativo.")
    if not configuration.quantiles:
        raise ValueError("quantiles nao pode ser vazio.")
    if any(not 0.0 < item < 1.0 or item == 0.5 for item in configuration.quantiles):
        raise ValueError("quantis devem estar entre zero e um e excluir 0.5.")
    integer_fields = (
        configuration.minimum_train_signals,
        configuration.minimum_train_true_positives,
        configuration.maximum_seed_predicates_per_direction,
        configuration.maximum_and_rules_per_direction,
        configuration.maximum_ranked_rules,
        configuration.maximum_portfolio_candidates,
        configuration.maximum_portfolio_rules,
    )
    if any(item < 1 for item in integer_fields):
        raise ValueError("limites de busca devem ser positivos.")
    if configuration.rule_complexity_penalty < 0.0:
        raise ValueError("rule_complexity_penalty nao pode ser negativo.")
    if configuration.portfolio_rule_penalty < 0.0:
        raise ValueError("portfolio_rule_penalty nao pode ser negativo.")
    if configuration.minimum_portfolio_score_improvement < 0.0:
        raise ValueError(
            "minimum_portfolio_score_improvement nao pode ser negativo."
        )


__all__ = [
    "BUY",
    "SELL",
    "WAIT",
    "MultiEAM15RuleMiner",
    "MultiEAM15RuleMinerConfiguration",
    "RulePredicate",
]
