"""Busca ampla, deterministica e causal de setups de entrada M15.

O modulo e deliberadamente isolado do motor operacional. Ele usa apenas candles
fechados e os campos de abertura das posicoes observadas. Saidas, lucro, swap e
comissao nunca participam da rotulagem, selecao ou validacao.
"""

from __future__ import annotations

from array import array
from bisect import bisect_right
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Mapping, Sequence

from research.multi_ea_trading_lab import MultiEACandle, MultiEATradePosition


M15_DURATION = timedelta(minutes=15)
WAIT = 0
BUY = 1
SELL = 2


@dataclass(frozen=True)
class MultiEAStrategySearchConfiguration:
    """Limites defensivos da busca de hipoteses M15."""

    train_fraction: float = 0.70
    minimum_positive_events_for_split: int = 20
    minimum_validation_positive_events: int = 5
    common_history_bars: int = 60
    embargo_bars: int = 4
    dedupe_bars: int = 4
    complexity_penalty: float = 0.02
    maximum_ranked_candidates: int = 100


@dataclass(frozen=True, slots=True)
class _Candidate:
    candidate_id: str
    family: str
    parameters: Mapping[str, object]
    minimum_history: int
    complexity: int = 1
    components: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Opportunity:
    symbol: str
    candle_index: int
    signal_time: datetime
    observed_directions: tuple[int, ...]

    @property
    def positive(self) -> bool:
        return bool(self.observed_directions)


@dataclass(frozen=True, slots=True)
class _FeatureSet:
    candles: Sequence[MultiEACandle]
    close: Sequence[float]
    ema9: Sequence[float]
    ema12: Sequence[float]
    ema20: Sequence[float]
    ema26: Sequence[float]
    ema50: Sequence[float]
    sma10: Sequence[float]
    sma20: Sequence[float]
    sma50: Sequence[float]
    std20: Sequence[float]
    rsi7: Sequence[float]
    rsi14: Sequence[float]
    atr14: Sequence[float]
    atr_mean50: Sequence[float]
    donchian_high20: Sequence[float]
    donchian_low20: Sequence[float]
    macd: Sequence[float]
    macd_signal: Sequence[float]
    stochastic_k14: Sequence[float]
    stochastic_d3: Sequence[float]


class MultiEAStrategySearchEngine:
    """Pesquisa regras fixas em treino e congela cada escolha na validacao."""

    def __init__(
        self,
        configuration: MultiEAStrategySearchConfiguration | None = None,
    ) -> None:
        self.configuration = configuration or MultiEAStrategySearchConfiguration()
        _validate_configuration(self.configuration)
        self._candidates = _candidate_catalog()
        self._candidate_by_id = {
            item.candidate_id: item for item in self._candidates
        }

    def candidate_catalog(self) -> list[dict[str, object]]:
        """Retorna a grade fixa em ordem estavel, sem executar o fit."""

        return [self._candidate_metadata(item) for item in self._candidates]

    def analyze(
        self,
        positions: Sequence[MultiEATradePosition],
        candles: Sequence[MultiEACandle],
        *,
        symbol_clusters: Mapping[str, str] | None = None,
        source_timezone: str | None = None,
    ) -> dict[str, object]:
        """Executa ranking global, por simbolo e por cluster sem lookahead."""

        ordered_positions = sorted(positions, key=lambda item: _time_key(item.open_time))
        series = _m15_series(candles)
        features = {
            symbol: _feature_set(market) for symbol, market in series.items()
        }
        opportunities, coverage = self._opportunities(ordered_positions, series)
        segments, split = self._temporal_split(opportunities)
        raw_signals, deduped_signals = self._signal_matrix(opportunities, features)

        all_indexes = list(range(len(opportunities)))
        global_report = self._scope_report(
            all_indexes,
            opportunities,
            segments,
            raw_signals,
            deduped_signals,
        )

        symbols = sorted({item.symbol for item in opportunities})
        symbol_indexes = {
            symbol: [
                index
                for index, item in enumerate(opportunities)
                if item.symbol == symbol
            ]
            for symbol in symbols
        }
        by_symbol = {
            symbol: self._scope_report(
                indexes,
                opportunities,
                segments,
                raw_signals,
                deduped_signals,
            )
            for symbol, indexes in symbol_indexes.items()
        }

        assignments = {
            symbol: _cluster_for_symbol(symbol, symbol_clusters)
            for symbol in symbols
        }
        cluster_indexes: dict[str, list[int]] = {}
        for symbol, indexes in symbol_indexes.items():
            cluster_indexes.setdefault(assignments[symbol], []).extend(indexes)
        by_cluster = {
            cluster: self._scope_report(
                sorted(indexes),
                opportunities,
                segments,
                raw_signals,
                deduped_signals,
            )
            for cluster, indexes in sorted(cluster_indexes.items())
        }

        warnings = [
            "RESEARCH_ONLY: nenhuma configuracao pode alimentar conta Demo ou real.",
            (
                "VALIDACAO_CONGELADA: candidatos e desempates usam somente o "
                "segmento de treino."
            ),
            (
                "NEGATIVOS_INCLUIDOS: todos os candles elegiveis sem entrada "
                "observada entram nas metricas."
            ),
            (
                "ENTRADAS_SOMENTE: close_time, close_price, lucro, swap e comissao "
                "nao sao lidos pelo algoritmo."
            ),
        ]
        if not source_timezone:
            warnings.append(
                "FUSO_NAO_INFORMADO: timestamps naive sao tratados na mesma escala UTC."
            )

        return {
            "schema_version": "multi_ea_strategy_search_v1",
            "status": "OK" if opportunities else "SEM_SOBREPOSICAO_M15",
            "timeframe": "M15",
            "research_only": True,
            "operational_eligible": False,
            "uses_exit_data": False,
            "lookahead": False,
            "candidate_count": len(self._candidates),
            "families": sorted({item.family for item in self._candidates}),
            "candidate_catalog": self.candidate_catalog(),
            "coverage": coverage,
            "split": split,
            "deduplication": {
                "method": "MESMO_SIMBOLO_E_DIRECAO_APOS_ULTIMO_SINAL_EMITIDO",
                "window_bars": self.configuration.dedupe_bars,
            },
            "ranking_policy": {
                "selection_segment": "TRAIN",
                "validation_policy": "FROZEN",
                "score_formula": "F1 + 0.25*MCC - penalty*(complexity-1)",
                "complexity_penalty": self.configuration.complexity_penalty,
                "deterministic_tiebreak": (
                    "score,MCC,F1,precision,recall,menos_sinais,candidate_id"
                ),
            },
            "global": global_report,
            "by_symbol": by_symbol,
            "cluster_assignments": assignments,
            "by_cluster": by_cluster,
            "warnings": warnings,
        }

    run = analyze

    def _opportunities(
        self,
        positions: Sequence[MultiEATradePosition],
        series: Mapping[str, Sequence[MultiEACandle]],
    ) -> tuple[list[_Opportunity], dict[str, object]]:
        if not positions or not series:
            return [], _coverage(positions, (), 0, 0)

        close_times = {
            symbol: [_time_key(item.timestamp) + M15_DURATION for item in market]
            for symbol, market in series.items()
        }
        labels: dict[tuple[str, int], list[int]] = {}
        adjacent_positions = 0
        eligible_positions = 0
        for position in positions:
            symbol = str(position.symbol).strip().upper()
            market = series.get(symbol)
            if not market:
                continue
            entry_time = _time_key(position.open_time)
            times = close_times[symbol]
            candle_index = bisect_right(times, entry_time) - 1
            if candle_index < 0:
                continue
            distance = entry_time - times[candle_index]
            if distance < timedelta(0) or distance >= M15_DURATION:
                continue
            adjacent_positions += 1
            if candle_index < self.configuration.common_history_bars - 1:
                continue
            direction = _direction_code(position.direction)
            if direction == WAIT:
                continue
            labels.setdefault((symbol, candle_index), []).append(direction)
            eligible_positions += 1

        if not labels:
            return [], _coverage(
                positions,
                (),
                adjacent_positions,
                eligible_positions,
            )

        first_signal = min(
            close_times[symbol][index] for symbol, index in labels
        )
        last_entry = max(_time_key(item.open_time) for item in positions)
        opportunities: list[_Opportunity] = []
        for symbol, market in sorted(series.items()):
            for index in range(self.configuration.common_history_bars - 1, len(market)):
                signal_time = close_times[symbol][index]
                if signal_time < first_signal or signal_time > last_entry:
                    continue
                opportunities.append(
                    _Opportunity(
                        symbol=symbol,
                        candle_index=index,
                        signal_time=signal_time,
                        observed_directions=tuple(labels.get((symbol, index), ())),
                    )
                )
        opportunities.sort(
            key=lambda item: (item.signal_time, item.symbol, item.candle_index)
        )
        return opportunities, _coverage(
            positions,
            opportunities,
            adjacent_positions,
            eligible_positions,
        )

    def _temporal_split(
        self,
        opportunities: Sequence[_Opportunity],
    ) -> tuple[list[str], dict[str, object]]:
        positive_times = sorted(
            {item.signal_time for item in opportunities if item.positive}
        )
        if (
            len(positive_times)
            < self.configuration.minimum_positive_events_for_split
        ):
            segments = ["TRAIN"] * len(opportunities)
            return segments, {
                "method": "TREINO_UNICO_AMOSTRA_INSUFICIENTE",
                "train_end": (
                    opportunities[-1].signal_time.isoformat()
                    if opportunities
                    else "N/D"
                ),
                "validation_start": "N/D",
                "embargo_bars": 0,
                **_segment_counts(opportunities, segments),
            }

        maximum_cut = max(
            1,
            len(positive_times)
            - self.configuration.minimum_validation_positive_events,
        )
        cut = min(
            maximum_cut,
            max(1, int(len(positive_times) * self.configuration.train_fraction)),
        )
        while cut > 1:
            candidate_end = positive_times[cut - 1]
            candidate_start = candidate_end + M15_DURATION * (
                self.configuration.embargo_bars + 1
            )
            validation_count = sum(
                value >= candidate_start for value in positive_times
            )
            if validation_count >= self.configuration.minimum_validation_positive_events:
                break
            cut -= 1

        train_end = positive_times[cut - 1]
        validation_start = train_end + M15_DURATION * (
            self.configuration.embargo_bars + 1
        )
        segments = [
            "TRAIN"
            if item.signal_time <= train_end
            else "VALIDATION"
            if item.signal_time >= validation_start
            else "EMBARGO"
            for item in opportunities
        ]
        return segments, {
            "method": "CRONOLOGICO_TREINO_VALIDACAO_COM_EMBARGO",
            "train_end": train_end.isoformat(),
            "validation_start": validation_start.isoformat(),
            "embargo_bars": self.configuration.embargo_bars,
            **_segment_counts(opportunities, segments),
        }

    def _signal_matrix(
        self,
        opportunities: Sequence[_Opportunity],
        features: Mapping[str, _FeatureSet],
    ) -> tuple[dict[str, bytearray], dict[str, bytearray]]:
        raw_by_candidate: dict[str, bytearray] = {}
        deduped_by_candidate: dict[str, bytearray] = {}
        for candidate in self._candidates:
            raw = bytearray(len(opportunities))
            deduped = bytearray(len(opportunities))
            last_emitted: dict[tuple[str, int], int] = {}
            for row_index, opportunity in enumerate(opportunities):
                signal = _candidate_signal(
                    candidate,
                    features[opportunity.symbol],
                    opportunity.candle_index,
                    self._candidate_by_id,
                )
                raw[row_index] = signal
                if signal == WAIT:
                    continue
                dedupe_key = (opportunity.symbol, signal)
                previous_index = last_emitted.get(dedupe_key)
                if (
                    previous_index is not None
                    and opportunity.candle_index - previous_index
                    <= self.configuration.dedupe_bars
                ):
                    continue
                deduped[row_index] = signal
                last_emitted[dedupe_key] = opportunity.candle_index
            raw_by_candidate[candidate.candidate_id] = raw
            deduped_by_candidate[candidate.candidate_id] = deduped
        return raw_by_candidate, deduped_by_candidate

    def _scope_report(
        self,
        indexes: Sequence[int],
        opportunities: Sequence[_Opportunity],
        segments: Sequence[str],
        raw_signals: Mapping[str, bytearray],
        deduped_signals: Mapping[str, bytearray],
    ) -> dict[str, object]:
        train_indexes = [index for index in indexes if segments[index] == "TRAIN"]
        validation_indexes = [
            index for index in indexes if segments[index] == "VALIDATION"
        ]
        ranking = []
        for candidate in self._candidates:
            metrics = _directional_metrics(
                train_indexes,
                opportunities,
                raw_signals[candidate.candidate_id],
                deduped_signals[candidate.candidate_id],
            )
            ranking.append(self._ranked_row(candidate, metrics))
        ranking.sort(key=_ranking_key)
        ranking = ranking[: self.configuration.maximum_ranked_candidates]
        selected = ranking[0] if ranking and train_indexes else None

        if selected is None:
            validation: dict[str, object] = {}
        else:
            selected_candidate = self._candidate_by_id[
                str(selected["candidate_id"])
            ]
            validation = {
                **self._candidate_metadata(selected_candidate),
                **_directional_metrics(
                    validation_indexes,
                    opportunities,
                    raw_signals[selected_candidate.candidate_id],
                    deduped_signals[selected_candidate.candidate_id],
                ),
            }
        return {
            "opportunities": len(indexes),
            "train_opportunities": len(train_indexes),
            "validation_opportunities": len(validation_indexes),
            "candidate_count_evaluated": len(self._candidates),
            "ranking_train": ranking,
            "selected_candidate_id": (
                str(selected["candidate_id"]) if selected else "N/D"
            ),
            "selected_family": str(selected["family"]) if selected else "N/D",
            "selected_parameters": (
                dict(selected["parameters"]) if selected else {}
            ),
            "selection_metrics_train": selected or {},
            "validation_metrics_frozen": validation,
        }

    def _ranked_row(
        self,
        candidate: _Candidate,
        metrics: Mapping[str, object],
    ) -> dict[str, object]:
        f1 = float(metrics.get("f1", 0.0) or 0.0)
        mcc = float(metrics.get("mcc", 0.0) or 0.0)
        penalty = self.configuration.complexity_penalty * max(
            candidate.complexity - 1,
            0,
        )
        return {
            **self._candidate_metadata(candidate),
            **dict(metrics),
            "complexity_penalty_applied": round(penalty, 8),
            "ranking_score": round(f1 + 0.25 * mcc - penalty, 8),
        }

    @staticmethod
    def _candidate_metadata(candidate: _Candidate) -> dict[str, object]:
        return {
            "candidate_id": candidate.candidate_id,
            "family": candidate.family,
            "parameters": dict(candidate.parameters),
            "minimum_history": candidate.minimum_history,
            "complexity": candidate.complexity,
            "components": list(candidate.components),
        }


def _candidate_catalog() -> tuple[_Candidate, ...]:
    atomic = (
        _Candidate("RSI_REV_7_25_75", "RSI_REVERSAL", {"period": 7, "low": 25.0, "high": 75.0}, 8),
        _Candidate("RSI_REV_14_30_70", "RSI_REVERSAL", {"period": 14, "low": 30.0, "high": 70.0}, 15),
        _Candidate("RSI_MOM_14_55_45", "RSI_MOMENTUM", {"period": 14, "buy": 55.0, "sell": 45.0}, 15),
        _Candidate("BOLLINGER_Z20_2", "BOLLINGER_ZSCORE", {"window": 20, "z": 2.0}, 20),
        _Candidate("EMA_CROSS_9_20", "EMA_CROSS", {"fast": 9, "slow": 20}, 21),
        _Candidate("EMA_TREND_20_50", "EMA_TREND", {"fast": 20, "slow": 50}, 50),
        _Candidate("EMA_PULLBACK_20_50", "EMA_PULLBACK", {"fast": 20, "slow": 50}, 51, 2),
        _Candidate("SMA_CROSS_10_20", "SMA_CROSS", {"fast": 10, "slow": 20}, 21),
        _Candidate("SMA_TREND_20_50", "SMA_TREND", {"fast": 20, "slow": 50}, 50),
        _Candidate("SMA_PULLBACK_20_50", "SMA_PULLBACK", {"fast": 20, "slow": 50}, 51, 2),
        _Candidate("DONCHIAN_BREAKOUT_20", "DONCHIAN_BREAKOUT", {"period": 20}, 21),
        _Candidate("MACD_CROSS_12_26_9", "MACD", {"fast": 12, "slow": 26, "signal": 9}, 35),
        _Candidate("STOCH_REV_14_3_20_80", "STOCHASTIC", {"k": 14, "d": 3, "low": 20.0, "high": 80.0}, 17),
        _Candidate("CANDLE_BODY_65", "CANDLE_BODY", {"minimum_body_ratio": 0.65}, 2),
        _Candidate("CANDLE_ENGULFING", "CANDLE_ENGULFING", {}, 2),
        _Candidate("ATR_HIGH_BODY_14_50", "ATR_VOLATILITY", {"atr_ratio": 1.15, "minimum_body_ratio": 0.45}, 64, 2),
        _Candidate("SESSION_ASIA_EMA_TREND", "TIME_SESSION_FILTER", {"start_hour_utc": 0, "end_hour_utc": 8}, 50, 2),
        _Candidate("SESSION_LONDON_EMA_TREND", "TIME_SESSION_FILTER", {"start_hour_utc": 7, "end_hour_utc": 16}, 50, 2),
        _Candidate("SESSION_NEW_YORK_EMA_TREND", "TIME_SESSION_FILTER", {"start_hour_utc": 12, "end_hour_utc": 21}, 50, 2),
    )
    combinations = (
        _Candidate("AND_RSI_BOLLINGER", "AND_COMBINATION", {}, 20, 2, ("RSI_REV_14_30_70", "BOLLINGER_Z20_2")),
        _Candidate("AND_RSI_STOCHASTIC", "AND_COMBINATION", {}, 17, 2, ("RSI_REV_14_30_70", "STOCH_REV_14_3_20_80")),
        _Candidate("AND_EMA_MACD", "AND_COMBINATION", {}, 50, 2, ("EMA_TREND_20_50", "MACD_CROSS_12_26_9")),
        _Candidate("AND_DONCHIAN_ATR", "AND_COMBINATION", {}, 64, 3, ("DONCHIAN_BREAKOUT_20", "ATR_HIGH_BODY_14_50")),
        _Candidate("AND_ENGULFING_LONDON", "AND_COMBINATION", {}, 50, 3, ("CANDLE_ENGULFING", "SESSION_LONDON_EMA_TREND")),
    )
    return atomic + combinations


def _candidate_signal(
    candidate: _Candidate,
    features: _FeatureSet,
    index: int,
    candidates: Mapping[str, _Candidate],
) -> int:
    if index < candidate.minimum_history - 1:
        return WAIT
    if candidate.components:
        component_signals = [
            _candidate_signal(candidates[item], features, index, candidates)
            for item in candidate.components
        ]
        first = component_signals[0] if component_signals else WAIT
        return first if first != WAIT and all(item == first for item in component_signals) else WAIT

    family = candidate.family
    params = candidate.parameters
    if family in {"RSI_REVERSAL", "RSI_MOMENTUM"}:
        rsi = features.rsi7 if int(params["period"]) == 7 else features.rsi14
        value = float(rsi[index])
        if not math.isfinite(value):
            return WAIT
        if family == "RSI_REVERSAL":
            return BUY if value <= float(params["low"]) else SELL if value >= float(params["high"]) else WAIT
        return BUY if value >= float(params["buy"]) else SELL if value <= float(params["sell"]) else WAIT

    if family == "BOLLINGER_ZSCORE":
        mean = float(features.sma20[index])
        deviation = float(features.std20[index])
        if not math.isfinite(mean) or not math.isfinite(deviation) or deviation <= 0.0:
            return WAIT
        z_score = (float(features.close[index]) - mean) / deviation
        return BUY if z_score <= -float(params["z"]) else SELL if z_score >= float(params["z"]) else WAIT

    if family.startswith("EMA_") or family.startswith("SMA_"):
        average_kind = "EMA" if family.startswith("EMA_") else "SMA"
        fast, slow = _average_pair(features, average_kind, int(params["fast"]), int(params["slow"]))
        if not _finite_at(fast, slow, index):
            return WAIT
        if family.endswith("CROSS"):
            return _cross_signal(fast, slow, index)
        trend = BUY if fast[index] > slow[index] else SELL if fast[index] < slow[index] else WAIT
        if family.endswith("TREND") or trend == WAIT or index <= 0:
            return trend
        close = features.close
        if not _finite_at(close, fast, index - 1):
            return WAIT
        if trend == BUY and close[index - 1] < fast[index - 1] and close[index] >= fast[index]:
            return BUY
        if trend == SELL and close[index - 1] > fast[index - 1] and close[index] <= fast[index]:
            return SELL
        return WAIT

    if family == "DONCHIAN_BREAKOUT":
        upper = float(features.donchian_high20[index])
        lower = float(features.donchian_low20[index])
        close = float(features.close[index])
        if not math.isfinite(upper) or not math.isfinite(lower):
            return WAIT
        return BUY if close > upper else SELL if close < lower else WAIT

    if family == "MACD":
        return _cross_signal(features.macd, features.macd_signal, index)

    if family == "STOCHASTIC":
        if index <= 0 or not _finite_at(features.stochastic_k14, features.stochastic_d3, index) or not _finite_at(features.stochastic_k14, features.stochastic_d3, index - 1):
            return WAIT
        current_k = float(features.stochastic_k14[index])
        previous_k = float(features.stochastic_k14[index - 1])
        current_d = float(features.stochastic_d3[index])
        low = float(params["low"])
        high = float(params["high"])
        if previous_k <= low < current_k and current_k > current_d:
            return BUY
        if previous_k >= high > current_k and current_k < current_d:
            return SELL
        return WAIT

    if family == "CANDLE_BODY":
        return _body_direction(features.candles[index], float(params["minimum_body_ratio"]))

    if family == "CANDLE_ENGULFING":
        return _engulfing_direction(features.candles, index)

    if family == "ATR_VOLATILITY":
        atr = float(features.atr14[index])
        baseline = float(features.atr_mean50[index])
        if not math.isfinite(atr) or not math.isfinite(baseline) or baseline <= 0.0:
            return WAIT
        if atr / baseline < float(params["atr_ratio"]):
            return WAIT
        return _body_direction(features.candles[index], float(params["minimum_body_ratio"]))

    if family == "TIME_SESSION_FILTER":
        signal_time = _time_key(features.candles[index].timestamp) + M15_DURATION
        if not _hour_in_session(signal_time.hour, int(params["start_hour_utc"]), int(params["end_hour_utc"])):
            return WAIT
        if not _finite_at(features.ema20, features.ema50, index):
            return WAIT
        return BUY if features.ema20[index] > features.ema50[index] else SELL if features.ema20[index] < features.ema50[index] else WAIT
    return WAIT


def _directional_metrics(
    indexes: Sequence[int],
    opportunities: Sequence[_Opportunity],
    raw_signals: Sequence[int],
    signals: Sequence[int],
) -> dict[str, object]:
    true_positive = false_positive = false_negative = true_negative = 0
    timing_true_positive = timing_false_positive = timing_false_negative = timing_true_negative = 0
    source_positions = direction_matches = raw_count = signal_count = 0
    positive_events = 0
    for index in indexes:
        opportunity = opportunities[index]
        raw = int(raw_signals[index])
        signal = int(signals[index])
        target = set(opportunity.observed_directions)
        positive = bool(target)
        emitted = signal in {BUY, SELL}
        raw_count += int(raw in {BUY, SELL})
        signal_count += int(emitted)
        positive_events += int(positive)
        source_positions += len(opportunity.observed_directions)
        exact = emitted and signal in target
        if exact:
            true_positive += 1
            direction_matches += sum(item == signal for item in opportunity.observed_directions)
        elif emitted:
            false_positive += 1
        if positive and not exact:
            false_negative += 1
        if not positive and not emitted:
            true_negative += 1

        if emitted and positive:
            timing_true_positive += 1
        elif emitted:
            timing_false_positive += 1
        elif positive:
            timing_false_negative += 1
        else:
            timing_true_negative += 1

    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1 = _ratio(2.0 * precision * recall, precision + recall)
    return {
        "opportunities": len(indexes),
        "positive_events": positive_events,
        "negative_events": len(indexes) - positive_events,
        "raw_signals": raw_count,
        "signals": signal_count,
        "suppressed_duplicate_signals": max(raw_count - signal_count, 0),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision": round(precision, 8),
        "recall": round(recall, 8),
        "f1": round(f1, 8),
        "mcc": round(_mcc(true_positive, false_positive, false_negative, true_negative), 8),
        "direction_matches": direction_matches,
        "source_positions": source_positions,
        "direction_match_rate": round(_ratio(direction_matches, source_positions), 8),
        "timing_mcc": round(_mcc(timing_true_positive, timing_false_positive, timing_false_negative, timing_true_negative), 8),
    }


def _feature_set(candles: Sequence[MultiEACandle]) -> _FeatureSet:
    close = array("d", (float(item.close) for item in candles))
    ema9 = _ema(close, 9)
    ema12 = _ema(close, 12)
    ema20 = _ema(close, 20)
    ema26 = _ema(close, 26)
    ema50 = _ema(close, 50)
    sma10 = _rolling_mean(close, 10)
    sma20 = _rolling_mean(close, 20)
    sma50 = _rolling_mean(close, 50)
    std20 = _rolling_std(close, 20)
    atr14 = _atr(candles, 14)
    macd = _difference(ema12, ema26)
    stochastic_k = _stochastic_k(candles, 14)
    return _FeatureSet(
        candles=candles,
        close=close,
        ema9=ema9,
        ema12=ema12,
        ema20=ema20,
        ema26=ema26,
        ema50=ema50,
        sma10=sma10,
        sma20=sma20,
        sma50=sma50,
        std20=std20,
        rsi7=_rsi(close, 7),
        rsi14=_rsi(close, 14),
        atr14=atr14,
        atr_mean50=_rolling_finite_mean(atr14, 50),
        donchian_high20=_previous_extreme([float(item.high) for item in candles], 20, maximum=True),
        donchian_low20=_previous_extreme([float(item.low) for item in candles], 20, maximum=False),
        macd=macd,
        macd_signal=_ema_finite(macd, 9),
        stochastic_k14=stochastic_k,
        stochastic_d3=_rolling_finite_mean(stochastic_k, 3),
    )


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


def _rolling_mean(values: Sequence[float], period: int) -> array:
    result = _nan_array(len(values))
    prefix = array("d", [0.0])
    for value in values:
        prefix.append(prefix[-1] + float(value))
    for index in range(period - 1, len(values)):
        result[index] = (prefix[index + 1] - prefix[index + 1 - period]) / period
    return result


def _rolling_std(values: Sequence[float], period: int) -> array:
    result = _nan_array(len(values))
    prefix = array("d", [0.0])
    squares = array("d", [0.0])
    for value in values:
        numeric = float(value)
        prefix.append(prefix[-1] + numeric)
        squares.append(squares[-1] + numeric * numeric)
    for index in range(period - 1, len(values)):
        start = index + 1 - period
        mean = (prefix[index + 1] - prefix[start]) / period
        variance = max((squares[index + 1] - squares[start]) / period - mean * mean, 0.0)
        result[index] = math.sqrt(variance)
    return result


def _ema(values: Sequence[float], period: int) -> array:
    result = _nan_array(len(values))
    if len(values) < period:
        return result
    result[period - 1] = sum(float(item) for item in values[:period]) / period
    multiplier = 2.0 / (period + 1.0)
    for index in range(period, len(values)):
        result[index] = (float(values[index]) - result[index - 1]) * multiplier + result[index - 1]
    return result


def _ema_finite(values: Sequence[float], period: int) -> array:
    result = _nan_array(len(values))
    finite_indexes = [index for index, value in enumerate(values) if math.isfinite(float(value))]
    if len(finite_indexes) < period:
        return result
    seed_indexes = finite_indexes[:period]
    seed_index = seed_indexes[-1]
    result[seed_index] = sum(float(values[index]) for index in seed_indexes) / period
    multiplier = 2.0 / (period + 1.0)
    previous = result[seed_index]
    for index in finite_indexes[period:]:
        previous = (float(values[index]) - previous) * multiplier + previous
        result[index] = previous
    return result


def _rsi(values: Sequence[float], period: int) -> array:
    result = _nan_array(len(values))
    gain_prefix = array("d", [0.0])
    loss_prefix = array("d", [0.0])
    for index, value in enumerate(values):
        change = 0.0 if index == 0 else float(value) - float(values[index - 1])
        gain_prefix.append(gain_prefix[-1] + max(change, 0.0))
        loss_prefix.append(loss_prefix[-1] + max(-change, 0.0))
    for index in range(period, len(values)):
        start = index + 1 - period
        gains = (gain_prefix[index + 1] - gain_prefix[start]) / period
        losses = (loss_prefix[index + 1] - loss_prefix[start]) / period
        result[index] = 100.0 if losses <= 0.0 and gains > 0.0 else 50.0 if losses <= 0.0 else 100.0 - 100.0 / (1.0 + gains / losses)
    return result


def _atr(candles: Sequence[MultiEACandle], period: int) -> array:
    true_ranges = array("d")
    for index, candle in enumerate(candles):
        if index == 0:
            true_ranges.append(float(candle.high) - float(candle.low))
        else:
            previous_close = float(candles[index - 1].close)
            true_ranges.append(max(float(candle.high) - float(candle.low), abs(float(candle.high) - previous_close), abs(float(candle.low) - previous_close)))
    return _rolling_mean(true_ranges, period)


def _rolling_finite_mean(values: Sequence[float], period: int) -> array:
    result = _nan_array(len(values))
    window: deque[float] = deque()
    total = 0.0
    for index, value in enumerate(values):
        numeric = float(value)
        window.append(numeric)
        if math.isfinite(numeric):
            total += numeric
        if len(window) > period:
            removed = window.popleft()
            if math.isfinite(removed):
                total -= removed
        if len(window) == period and all(math.isfinite(item) for item in window):
            result[index] = total / period
    return result


def _previous_extreme(values: Sequence[float], period: int, *, maximum: bool) -> array:
    result = _nan_array(len(values))
    indexes: deque[int] = deque()
    for index, value in enumerate(values):
        while indexes and indexes[0] < index - period:
            indexes.popleft()
        if index >= period and indexes:
            result[index] = float(values[indexes[0]])
        if maximum:
            while indexes and float(values[indexes[-1]]) <= float(value):
                indexes.pop()
        else:
            while indexes and float(values[indexes[-1]]) >= float(value):
                indexes.pop()
        indexes.append(index)
    return result


def _stochastic_k(candles: Sequence[MultiEACandle], period: int) -> array:
    result = _nan_array(len(candles))
    for index in range(period - 1, len(candles)):
        window = candles[index + 1 - period : index + 1]
        lowest = min(float(item.low) for item in window)
        highest = max(float(item.high) for item in window)
        width = highest - lowest
        result[index] = 50.0 if width <= 0.0 else 100.0 * (float(candles[index].close) - lowest) / width
    return result


def _difference(left: Sequence[float], right: Sequence[float]) -> array:
    result = _nan_array(min(len(left), len(right)))
    for index in range(len(result)):
        if math.isfinite(float(left[index])) and math.isfinite(float(right[index])):
            result[index] = float(left[index]) - float(right[index])
    return result


def _average_pair(features: _FeatureSet, kind: str, fast: int, slow: int) -> tuple[Sequence[float], Sequence[float]]:
    values = {
        ("EMA", 9): features.ema9,
        ("EMA", 20): features.ema20,
        ("EMA", 50): features.ema50,
        ("SMA", 10): features.sma10,
        ("SMA", 20): features.sma20,
        ("SMA", 50): features.sma50,
    }
    return values[(kind, fast)], values[(kind, slow)]


def _cross_signal(fast: Sequence[float], slow: Sequence[float], index: int) -> int:
    if index <= 0 or not _finite_at(fast, slow, index) or not _finite_at(fast, slow, index - 1):
        return WAIT
    if fast[index - 1] <= slow[index - 1] and fast[index] > slow[index]:
        return BUY
    if fast[index - 1] >= slow[index - 1] and fast[index] < slow[index]:
        return SELL
    return WAIT


def _body_direction(candle: MultiEACandle, threshold: float) -> int:
    width = float(candle.high) - float(candle.low)
    if width <= 0.0 or abs(float(candle.close) - float(candle.open)) / width < threshold:
        return WAIT
    return BUY if candle.close > candle.open else SELL if candle.close < candle.open else WAIT


def _engulfing_direction(candles: Sequence[MultiEACandle], index: int) -> int:
    if index <= 0:
        return WAIT
    previous = candles[index - 1]
    current = candles[index]
    if previous.close < previous.open and current.close > current.open and current.open <= previous.close and current.close >= previous.open:
        return BUY
    if previous.close > previous.open and current.close < current.open and current.open >= previous.close and current.close <= previous.open:
        return SELL
    return WAIT


def _hour_in_session(hour: int, start: int, end: int) -> bool:
    return start <= hour < end if start < end else hour >= start or hour < end


def _finite_at(left: Sequence[float], right: Sequence[float], index: int) -> bool:
    return index >= 0 and index < len(left) and index < len(right) and math.isfinite(float(left[index])) and math.isfinite(float(right[index]))


def _ranking_key(row: Mapping[str, object]) -> tuple[float, float, float, float, float, int, str]:
    return (
        -float(row.get("ranking_score", 0.0) or 0.0),
        -float(row.get("mcc", 0.0) or 0.0),
        -float(row.get("f1", 0.0) or 0.0),
        -float(row.get("precision", 0.0) or 0.0),
        -float(row.get("recall", 0.0) or 0.0),
        int(row.get("signals", 0) or 0),
        str(row.get("candidate_id", "")),
    )


def _coverage(positions: Sequence[MultiEATradePosition], opportunities: Sequence[_Opportunity], adjacent_positions: int, eligible_positions: int) -> dict[str, object]:
    positive_events = sum(item.positive for item in opportunities)
    return {
        "source_positions": len(positions),
        "source_symbols": len({str(item.symbol).upper() for item in positions}),
        "opportunity_bars": len(opportunities),
        "positive_events": positive_events,
        "negative_events": len(opportunities) - positive_events,
        "temporally_adjacent_positions": adjacent_positions,
        "eligible_positions": eligible_positions,
        "collapsed_positions": max(eligible_positions - positive_events, 0),
    }


def _segment_counts(opportunities: Sequence[_Opportunity], segments: Sequence[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for name in ("TRAIN", "EMBARGO", "VALIDATION"):
        indexes = [index for index, value in enumerate(segments) if value == name]
        result[f"{name.lower()}_opportunities"] = len(indexes)
        result[f"{name.lower()}_positive_events"] = sum(opportunities[index].positive for index in indexes)
    return result


def _cluster_for_symbol(symbol: str, overrides: Mapping[str, str] | None) -> str:
    normalized = str(symbol).strip().upper()
    if overrides:
        normalized_overrides = {str(key).strip().upper(): str(value).strip().upper() for key, value in overrides.items()}
        if normalized in normalized_overrides and normalized_overrides[normalized]:
            return normalized_overrides[normalized]
    if normalized.startswith(("XAU", "XAG", "GOLD", "SILVER")):
        return "METALS"
    if normalized.startswith(("BTC", "ETH", "BITCOIN")):
        return "CRYPTO"
    if len(normalized) == 6 and normalized.endswith("JPY"):
        return "FX_JPY"
    if normalized in {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF"}:
        return "FX_MAJORS"
    if len(normalized) == 6:
        return "FX_CROSSES"
    return "OTHER"


def _direction_code(value: object) -> int:
    normalized = str(value or "").strip().upper()
    return BUY if normalized == "BUY" else SELL if normalized == "SELL" else WAIT


def _mcc(tp: int, fp: int, fn: int, tn: int) -> float:
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return (tp * tn - fp * fn) / denominator if denominator else 0.0


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _nan_array(count: int) -> array:
    return array("d", [math.nan]) * count


def _time_key(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _validate_configuration(configuration: MultiEAStrategySearchConfiguration) -> None:
    if not 0.0 < configuration.train_fraction < 1.0:
        raise ValueError("train_fraction deve estar entre zero e um.")
    if configuration.common_history_bars < 2:
        raise ValueError("common_history_bars deve ser pelo menos 2.")
    if configuration.embargo_bars < 0 or configuration.dedupe_bars < 0:
        raise ValueError("embargo_bars e dedupe_bars nao podem ser negativos.")
    if configuration.complexity_penalty < 0.0:
        raise ValueError("complexity_penalty nao pode ser negativa.")
    if configuration.maximum_ranked_candidates <= 0:
        raise ValueError("maximum_ranked_candidates deve ser positivo.")
