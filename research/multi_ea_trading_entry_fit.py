"""Fit causal e exploratorio das entradas M15 da amostra Multi EA Trading.

O modulo separa deliberadamente dois experimentos diferentes:

* o replay-oraculo copia as entradas observadas e, por construcao, cobre 100%;
* o fit causal avalia todos os candles M15 elegiveis, incluindo os candles sem
  entrada, e usa somente informacao fechada antes do horizonte previsto.

Nenhum resultado deste modulo identifica o EA original ou autoriza operacao.
"""

from __future__ import annotations

from array import array
from bisect import bisect_right
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from statistics import pstdev
from typing import Mapping, Sequence

from research.multi_ea_trading_lab import MultiEACandle, MultiEATradePosition


M15_DURATION = timedelta(minutes=15)


@dataclass(frozen=True)
class MultiEAM15EntryFitConfiguration:
    """Contrato compacto do experimento causal M15."""

    train_fraction: float = 0.70
    minimum_positive_events_for_split: int = 20
    minimum_validation_positive_events: int = 5
    common_history_bars: int = 61
    embargo_bars: int = 4
    minimum_validation_precision: float = 0.02
    minimum_validation_recall: float = 0.10
    minimum_precision_lift: float = 2.0


@dataclass(frozen=True)
class _Candidate:
    candidate_id: str
    family: str
    parameters: Mapping[str, object]


@dataclass(frozen=True)
class _FeatureSet:
    close: Sequence[float]
    ema20: Sequence[float]
    ema50: Sequence[float]
    mean20: Sequence[float]
    std20: Sequence[float]
    rsi14: Sequence[float]
    atr14: Sequence[float]
    adx14: Sequence[float]
    donchian_high20: Sequence[float]
    donchian_low20: Sequence[float]


@dataclass(frozen=True)
class _Opportunity:
    symbol: str
    candle_index: int
    signal_time: datetime
    observed_directions: tuple[str, ...]
    position_ids: tuple[str, ...]

    @property
    def positive(self) -> bool:
        return bool(self.observed_directions)


class MultiEAM15EntryFitEngine:
    """Compara regras M15 com uma grade temporal que contem negativos reais."""

    def __init__(
        self,
        configuration: MultiEAM15EntryFitConfiguration | None = None,
    ) -> None:
        self.configuration = configuration or MultiEAM15EntryFitConfiguration()
        if not 0.0 < self.configuration.train_fraction < 1.0:
            raise ValueError("train_fraction deve estar entre zero e um.")
        if self.configuration.common_history_bars < 2:
            raise ValueError("common_history_bars deve ser pelo menos 2.")

    def analyze(
        self,
        positions: Sequence[MultiEATradePosition],
        candles: Sequence[MultiEACandle],
        *,
        source_timezone: str | None = None,
    ) -> dict[str, object]:
        """Executa o oraculo descritivo e o fit causal, sem usar saidas/P&L."""

        ordered_positions = sorted(
            positions,
            key=lambda item: _time_key(item.open_time),
        )
        series = _m15_series(candles)
        features = {
            symbol: _feature_set(values)
            for symbol, values in series.items()
        }
        opportunities, coverage = self._opportunities(ordered_positions, series)
        split = self._split(opportunities)
        train_rows = [
            item for item in opportunities if split["segment_by_key"].get(_key(item)) == "TRAIN"
        ]
        validation_rows = [
            item
            for item in opportunities
            if split["segment_by_key"].get(_key(item)) == "VALIDATION"
        ]

        train_ranking = [
            self._candidate_row(candidate, train_rows, features)
            for candidate in self._candidates()
        ]
        train_ranking.sort(key=_selection_sort_key, reverse=True)
        selected = train_ranking[0] if train_ranking else None
        selected_candidate: _Candidate | None = None
        validation = self._empty_candidate_row("N/D", "N/D", {})
        if selected is not None:
            selected_candidate = next(
                item
                for item in self._candidates()
                if item.candidate_id == selected["candidate_id"]
            )
            validation = self._candidate_row(
                selected_candidate,
                validation_rows,
                features,
            )

        entry_records = self._entry_records(
            ordered_positions,
            opportunities,
            series,
            features,
            selected_candidate,
            split,
        )

        classification = self._classification(split, validation)
        public_split = {
            key: value
            for key, value in split.items()
            if key != "segment_by_key"
        }
        warnings = [
            "RESEARCH_ONLY: nenhuma regra pode alimentar Demo ou conta real.",
            (
                "ORACULO_NAO_PREDITIVO: os 100% do replay apenas copiam os "
                "rotulos de entrada do CSV."
            ),
            (
                "NEGATIVOS_INCLUIDOS: precision contabiliza sinais emitidos em "
                "candles M15 sem entrada observada."
            ),
            (
                "ENTRADAS_AGRUPADAS: varias posicoes no mesmo simbolo/janela M15 "
                "formam um unico evento para precision e recall por evento."
            ),
            (
                "SEM_RECONSTRUCAO: o fit nao conhece ticket, magic, comentario, "
                "SL, TP, cesta, spread historico ou codigo do EA."
            ),
        ]
        if not source_timezone:
            warnings.append(
                "FUSO_NAO_INFORMADO: timestamps sem timezone foram comparados "
                "na mesma escala temporal dos candles."
            )
        if not validation_rows:
            warnings.append(
                "VALIDACAO_INDISPONIVEL: a amostra temporal elegivel nao atingiu "
                "o minimo configurado para uma divisao defensavel."
            )

        return {
            "schema_version": "multi_ea_m15_entry_fit_v1",
            "status": "OK" if opportunities else "SEM_SOBREPOSICAO_M15",
            "classification": classification,
            "timeframe": "M15",
            "research_only": True,
            "operational_eligible": False,
            "warnings": warnings,
            "oracle_replay": self._oracle(ordered_positions),
            "causal_fit": {
                "predictive_setup": False,
                "uses_exit_data": False,
                "uses_observed_outcomes": False,
                "negative_opportunities_included": True,
                "feature_cutoff": "CANDLE_CLOSE_LESS_THAN_OR_EQUAL_TO_ENTRY",
                "coverage": coverage,
                "split": public_split,
                "selected_candidate_id": (
                    str(selected["candidate_id"]) if selected else "N/D"
                ),
                "selected_parameters": (
                    dict(selected["parameters"]) if selected else {}
                ),
                "selection_metrics_train": selected or {},
                "validation_metrics_frozen": validation,
                "ranking_train": train_ranking,
                "entry_records": entry_records,
            },
            "methodology": {
                "target_unit": "SIMBOLO_E_JANELA_M15",
                "positive_label": (
                    "uma ou mais entradas observadas depois do fechamento do "
                    "candle e antes do fechamento M15 seguinte"
                ),
                "negative_label": "janela M15 elegivel sem entrada observada",
                "primary_metrics": "precision, recall e F1 direcionais",
                "selection": "maior F1 no treino; validation nunca ordena candidatos",
                "temporal_split": "70/30 por horario dos eventos, com embargo",
                "lookahead": False,
                "claim_limit": "HIPOTESE_CAUSAL_EXPLORATORIA_NAO_IDENTIFICADA",
            },
        }

    run = analyze

    def _opportunities(
        self,
        positions: Sequence[MultiEATradePosition],
        series: Mapping[str, Sequence[MultiEACandle]],
    ) -> tuple[list[_Opportunity], dict[str, object]]:
        if not positions or not series:
            return [], self._coverage(positions, (), 0, 0, 0)

        labels: dict[tuple[str, int], list[tuple[str, str]]] = {}
        mapped_positions: set[str] = set()
        adjacent_positions: set[str] = set()
        for position in positions:
            symbol = str(position.symbol).upper()
            market = series.get(symbol)
            if not market:
                continue
            close_times = [
                _time_key(item.timestamp) + M15_DURATION for item in market
            ]
            entry_time = _time_key(position.open_time)
            index = bisect_right(close_times, entry_time) - 1
            if index < 0 or not _temporally_adjacent(close_times[index], entry_time):
                continue
            position_id = position.position_id or str(position.source_row)
            adjacent_positions.add(position_id)
            if index < self.configuration.common_history_bars - 1:
                continue
            direction = str(position.direction).upper()
            if direction not in {"BUY", "SELL"}:
                continue
            labels.setdefault((symbol, index), []).append((position_id, direction))
            mapped_positions.add(position_id)

        if not labels:
            return [], self._coverage(
                positions,
                (),
                len(adjacent_positions),
                0,
                0,
            )

        first_signal = min(
            _time_key(series[symbol][index].timestamp) + M15_DURATION
            for symbol, index in labels
        )
        last_entry = max(_time_key(position.open_time) for position in positions)
        opportunities: list[_Opportunity] = []
        for symbol, market in sorted(series.items()):
            for index in range(self.configuration.common_history_bars - 1, len(market)):
                signal_time = _time_key(market[index].timestamp) + M15_DURATION
                if signal_time < first_signal or signal_time > last_entry:
                    continue
                observed = labels.get((symbol, index), [])
                opportunities.append(
                    _Opportunity(
                        symbol=symbol,
                        candle_index=index,
                        signal_time=signal_time,
                        observed_directions=tuple(item[1] for item in observed),
                        position_ids=tuple(item[0] for item in observed),
                    )
                )
        opportunities.sort(key=lambda item: (item.signal_time, item.symbol))
        positive_events = sum(item.positive for item in opportunities)
        eligible_positions = sum(len(item.position_ids) for item in opportunities)
        return opportunities, self._coverage(
            positions,
            opportunities,
            len(adjacent_positions),
            len(mapped_positions),
            eligible_positions,
            positive_events=positive_events,
        )

    def _coverage(
        self,
        positions: Sequence[MultiEATradePosition],
        opportunities: Sequence[_Opportunity],
        temporally_adjacent_positions: int,
        history_ready_positions: int,
        eligible_positions: int,
        *,
        positive_events: int = 0,
    ) -> dict[str, object]:
        return {
            "source_positions": len(positions),
            "source_markets": len({str(item.symbol).upper() for item in positions}),
            "opportunity_bars": len(opportunities),
            "positive_events": positive_events,
            "negative_events": len(opportunities) - positive_events,
            "temporally_adjacent_positions": temporally_adjacent_positions,
            "history_ready_positions": history_ready_positions,
            "eligible_positions": eligible_positions,
            "collapsed_positions": max(eligible_positions - positive_events, 0),
        }

    def _split(self, opportunities: Sequence[_Opportunity]) -> dict[str, object]:
        positive_times = sorted({item.signal_time for item in opportunities if item.positive})
        segment_by_key: dict[tuple[str, int], str] = {}
        if len(positive_times) < self.configuration.minimum_positive_events_for_split:
            for item in opportunities:
                segment_by_key[_key(item)] = "TRAIN"
            return {
                "method": "TREINO_UNICO_AMOSTRA_INSUFICIENTE",
                "train_end": opportunities[-1].signal_time.isoformat()
                if opportunities
                else "N/D",
                "validation_start": "N/D",
                "embargo_bars": 0,
                "train_opportunities": len(opportunities),
                "validation_opportunities": 0,
                "train_positive_events": len(positive_times),
                "validation_positive_events": 0,
                "segment_by_key": segment_by_key,
            }

        cut = max(
            1,
            min(
                len(positive_times) - 1,
                int(len(positive_times) * self.configuration.train_fraction),
            ),
        )
        train_end = positive_times[cut - 1]
        validation_start = train_end + M15_DURATION * (
            self.configuration.embargo_bars + 1
        )
        for item in opportunities:
            if item.signal_time <= train_end:
                segment_by_key[_key(item)] = "TRAIN"
            elif item.signal_time >= validation_start:
                segment_by_key[_key(item)] = "VALIDATION"
            else:
                segment_by_key[_key(item)] = "EMBARGO"
        train_rows = [item for item in opportunities if segment_by_key[_key(item)] == "TRAIN"]
        validation_rows = [
            item for item in opportunities if segment_by_key[_key(item)] == "VALIDATION"
        ]
        return {
            "method": "CRONOLOGICO_TREINO_VALIDACAO_COM_EMBARGO",
            "train_end": train_end.isoformat(),
            "validation_start": validation_start.isoformat(),
            "embargo_bars": self.configuration.embargo_bars,
            "train_opportunities": len(train_rows),
            "validation_opportunities": len(validation_rows),
            "train_positive_events": sum(item.positive for item in train_rows),
            "validation_positive_events": sum(item.positive for item in validation_rows),
            "segment_by_key": segment_by_key,
        }

    def _candidate_row(
        self,
        candidate: _Candidate,
        opportunities: Sequence[_Opportunity],
        features: Mapping[str, _FeatureSet],
    ) -> dict[str, object]:
        evaluated: list[tuple[_Opportunity, str]] = []
        for opportunity in opportunities:
            signal = _signal_from_features(
                candidate,
                features[opportunity.symbol],
                opportunity.candle_index,
            )
            evaluated.append((opportunity, signal))
        return {
            "candidate_id": candidate.candidate_id,
            "family": candidate.family,
            "parameters": dict(candidate.parameters),
            **_classification_metrics(evaluated),
        }

    def _entry_records(
        self,
        positions: Sequence[MultiEATradePosition],
        opportunities: Sequence[_Opportunity],
        series: Mapping[str, Sequence[MultiEACandle]],
        features: Mapping[str, _FeatureSet],
        selected_candidate: _Candidate | None,
        split: Mapping[str, object],
    ) -> list[dict[str, object]]:
        by_position: dict[str, _Opportunity] = {}
        for opportunity in opportunities:
            for position_id in opportunity.position_ids:
                by_position[position_id] = opportunity
        segment_by_key = dict(split.get("segment_by_key", {}) or {})
        records: list[dict[str, object]] = []
        for position in positions:
            source_row = int(getattr(position, "source_row", 0) or 0)
            position_id = str(
                getattr(position, "position_id", "") or source_row
            )
            opportunity = by_position.get(position_id)
            if opportunity is None:
                records.append(
                    {
                        "source_row": source_row,
                        "position_id": position_id,
                        "source_symbol": str(
                            getattr(position, "source_symbol", position.symbol)
                        ),
                        "symbol": str(position.symbol).upper(),
                        "entry_time": position.open_time.isoformat(),
                        "entry_price": float(
                            getattr(position, "open_price", 0.0) or 0.0
                        ),
                        "observed_direction": str(
                            getattr(position, "direction", "")
                        ).upper(),
                        "eligible": False,
                        "eligibility_reason": self._ineligibility_reason(
                            position,
                            series,
                        ),
                        "split": "INELIGIBLE",
                        "candidate_id": selected_candidate.candidate_id
                        if selected_candidate
                        else "N/D",
                        "signal": "WAIT",
                        "outcome": "NOT_EVALUATED",
                        "direction_match": False,
                        "metrics": {
                            "evaluation_unit": "SOURCE_POSITION",
                            "signal_emitted": False,
                            "directional_hit": None,
                            "miss": None,
                        },
                        "event_position_count": 0,
                        "m15_candle": None,
                    }
                )
                continue
            candle = series[opportunity.symbol][opportunity.candle_index]
            signal = (
                _signal_from_features(
                    selected_candidate,
                    features[opportunity.symbol],
                    opportunity.candle_index,
                )
                if selected_candidate
                else "WAIT"
            )
            direction = str(position.direction).upper()
            direction_match = signal == direction
            outcome = (
                "TRUE_POSITIVE"
                if direction_match
                else "FALSE_NEGATIVE_WAIT"
                if signal == "WAIT"
                else "FALSE_NEGATIVE_WRONG_SIDE"
            )
            records.append(
                {
                    "source_row": position.source_row,
                    "position_id": position_id,
                    "source_symbol": position.source_symbol,
                    "symbol": opportunity.symbol,
                    "entry_time": position.open_time.isoformat(),
                    "entry_price": position.open_price,
                    "observed_direction": direction,
                    "eligible": True,
                    "eligibility_reason": "OK",
                    "split": str(segment_by_key.get(_key(opportunity), "N/D")),
                    "candidate_id": selected_candidate.candidate_id
                    if selected_candidate
                    else "N/D",
                    "signal": signal,
                    "outcome": outcome,
                    "direction_match": direction_match,
                    "metrics": {
                        "evaluation_unit": "SOURCE_POSITION",
                        "signal_emitted": signal in {"BUY", "SELL"},
                        "directional_hit": direction_match,
                        "miss": not direction_match,
                    },
                    "event_position_count": len(opportunity.position_ids),
                    "m15_candle": {
                        "timestamp": candle.timestamp.isoformat(),
                        "close_time": (
                            _time_key(candle.timestamp) + M15_DURATION
                        ).isoformat(),
                        "open": candle.open,
                        "high": candle.high,
                        "low": candle.low,
                        "close": candle.close,
                        "volume": candle.volume,
                    },
                }
            )
        return records

    def _ineligibility_reason(
        self,
        position: MultiEATradePosition,
        series: Mapping[str, Sequence[MultiEACandle]],
    ) -> str:
        market = series.get(str(position.symbol).upper())
        if not market:
            return "SEM_SERIE_M15"
        close_times = [
            _time_key(item.timestamp) + M15_DURATION for item in market
        ]
        entry_time = _time_key(position.open_time)
        index = bisect_right(close_times, entry_time) - 1
        if index < 0:
            return "ENTRADA_ANTES_DA_SERIE_M15"
        if not _temporally_adjacent(close_times[index], entry_time):
            return "SEM_CANDLE_M15_ADJACENTE"
        if index < self.configuration.common_history_bars - 1:
            return "WARMUP_M15_INSUFICIENTE"
        if str(position.direction).upper() not in {"BUY", "SELL"}:
            return "DIRECAO_INVALIDA"
        return "FORA_DA_JANELA_OBSERVADA"

    def _empty_candidate_row(
        self,
        candidate_id: str,
        family: str,
        parameters: Mapping[str, object],
    ) -> dict[str, object]:
        return {
            "candidate_id": candidate_id,
            "family": family,
            "parameters": dict(parameters),
            **_classification_metrics(()),
        }

    def _classification(
        self,
        split: Mapping[str, object],
        validation: Mapping[str, object],
    ) -> str:
        validation_events = int(split.get("validation_positive_events", 0) or 0)
        if validation_events < self.configuration.minimum_validation_positive_events:
            return "VALIDACAO_TEMPORAL_INSUFICIENTE"
        if int(validation.get("true_positive", 0) or 0) <= 0:
            return "SEM_EVIDENCIA_CAUSAL_NA_VALIDACAO"
        precision = float(validation.get("precision", 0.0) or 0.0)
        recall = float(validation.get("recall", 0.0) or 0.0)
        prevalence = float(validation.get("prevalence", 0.0) or 0.0)
        lift = float(
            validation.get("precision_lift_over_prevalence", 0.0) or 0.0
        )
        if precision < self.configuration.minimum_validation_precision:
            return "PRECISAO_CAUSAL_INSUFICIENTE_NA_VALIDACAO"
        if recall < self.configuration.minimum_validation_recall:
            return "RECALL_CAUSAL_INSUFICIENTE_NA_VALIDACAO"
        if lift < self.configuration.minimum_precision_lift:
            return "LIFT_CAUSAL_INSUFICIENTE_NA_VALIDACAO"
        if precision <= prevalence:
            return "SEM_VANTAGEM_SOBRE_PREVALENCIA"
        return "HIPOTESE_CAUSAL_EXPLORATORIA_NAO_IDENTIFICADA"

    def _oracle(
        self,
        positions: Sequence[MultiEATradePosition],
    ) -> dict[str, object]:
        return {
            "mode": "REPLAY_ORACULO_DAS_ENTRADAS_OBSERVADAS",
            "source_entries": len(positions),
            "replayed_entries": len(positions),
            "coverage_percent": 100.0 if positions else 0.0,
            "precision": 1.0 if positions else 0.0,
            "recall": 1.0 if positions else 0.0,
            "uses_target_labels": True,
            "includes_negative_opportunities": False,
            "predictive_setup": False,
            "interpretation": (
                "Resultado tautologico: simbolo, horario, direcao e preco sao "
                "copiados do proprio CSV e nao constituem previsao."
            ),
        }

    def _candidates(self) -> tuple[_Candidate, ...]:
        return (
            _Candidate(
                "M15_EMA_TREND_20_50",
                "EMA_TREND",
                {"ema_fast": 20, "ema_slow": 50},
            ),
            _Candidate(
                "M15_TREND_MOMENTUM_20_50_10",
                "TREND_MOMENTUM",
                {"ema_fast": 20, "ema_slow": 50, "momentum_period": 10},
            ),
            _Candidate(
                "M15_MEAN_REVERSION_Z2_RSI_30_70",
                "MEAN_REVERSION_ZSCORE_RSI",
                {
                    "window": 20,
                    "z_threshold": 2.0,
                    "rsi_period": 14,
                    "rsi_oversold": 30.0,
                    "rsi_overbought": 70.0,
                },
            ),
            _Candidate(
                "M15_ALPHA017_STRICT_Z2_ADX22",
                "ALPHA017_STRICT_MEAN_REVERSION",
                {
                    "window": 20,
                    "z_threshold": 2.0,
                    "rsi_period": 14,
                    "rsi_oversold": 25.0,
                    "rsi_overbought": 75.0,
                    "adx_period": 14,
                    "adx_max": 22.0,
                    "band_width_atr_max": 6.0,
                },
            ),
            _Candidate(
                "M15_DONCHIAN_BREAKOUT_20",
                "DONCHIAN_BREAKOUT",
                {"period": 20},
            ),
        )


def _classification_metrics(
    evaluated: Sequence[tuple[_Opportunity, str]],
) -> dict[str, object]:
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    timing_true_positive = 0
    negative_bar_false_positive = 0
    exact_positions = 0
    source_positions = 0
    signals = 0
    positive_events = 0
    for opportunity, raw_signal in evaluated:
        signal = str(raw_signal or "WAIT").upper()
        signaled = signal in {"BUY", "SELL"}
        signals += int(signaled)
        positive_events += int(opportunity.positive)
        source_positions += len(opportunity.observed_directions)
        if signaled and opportunity.positive:
            timing_true_positive += 1
        if signaled and signal in set(opportunity.observed_directions):
            true_positive += 1
            exact_positions += sum(
                direction == signal for direction in opportunity.observed_directions
            )
        elif signaled:
            false_positive += 1
            if not opportunity.positive:
                negative_bar_false_positive += 1
        if opportunity.positive and (
            not signaled or signal not in set(opportunity.observed_directions)
        ):
            false_negative += 1
        if not opportunity.positive and not signaled:
            true_negative += 1

    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = _safe_ratio(2.0 * precision * recall, precision + recall)
    prevalence = _safe_ratio(positive_events, len(evaluated))
    timing_precision = _safe_ratio(timing_true_positive, signals)
    timing_recall = _safe_ratio(timing_true_positive, positive_events)
    return {
        "opportunities": len(evaluated),
        "positive_events": positive_events,
        "negative_events": len(evaluated) - positive_events,
        "signals": signals,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "negative_bar_false_positive": negative_bar_false_positive,
        "precision": round(precision, 8),
        "recall": round(recall, 8),
        "f1": round(f1, 8),
        "prevalence": round(prevalence, 8),
        "precision_lift_over_prevalence": round(
            _safe_ratio(precision, prevalence),
            8,
        ),
        "timing_precision": round(timing_precision, 8),
        "timing_recall": round(timing_recall, 8),
        "position_recall": round(_safe_ratio(exact_positions, source_positions), 8),
        "signals_per_1000_bars": round(
            _safe_ratio(signals * 1000.0, len(evaluated)),
            4,
        ),
    }


def _m15_series(
    candles: Sequence[MultiEACandle],
) -> dict[str, list[MultiEACandle]]:
    grouped: dict[str, dict[datetime, MultiEACandle]] = {}
    for candle in candles:
        if str(getattr(candle, "timeframe", "")).upper() != "M15":
            continue
        symbol = str(candle.symbol).upper()
        grouped.setdefault(symbol, {})[_time_key(candle.timestamp)] = candle
    return {
        symbol: [values[key] for key in sorted(values)]
        for symbol, values in grouped.items()
    }


def _feature_set(candles: Sequence[MultiEACandle]) -> _FeatureSet:
    closes = array("d", (float(item.close) for item in candles))
    count = len(closes)
    nan_values = lambda: array("d", [math.nan]) * count
    mean20 = nan_values()
    std20 = nan_values()
    rsi14 = nan_values()
    atr14 = nan_values()
    adx14 = nan_values()

    prefix = array("d", [0.0])
    prefix_square = array("d", [0.0])
    for value in closes:
        prefix.append(prefix[-1] + value)
        prefix_square.append(prefix_square[-1] + value * value)
    for index in range(19, count):
        start = index - 19
        total = prefix[index + 1] - prefix[start]
        total_square = prefix_square[index + 1] - prefix_square[start]
        mean = total / 20.0
        variance = max(total_square / 20.0 - mean * mean, 0.0)
        mean20[index] = mean
        std20[index] = math.sqrt(variance)

    gain_prefix = array("d", [0.0])
    loss_prefix = array("d", [0.0])
    true_range_prefix = array("d", [0.0])
    plus_dm_prefix = array("d", [0.0])
    minus_dm_prefix = array("d", [0.0])
    for index in range(count):
        if index == 0:
            change = 0.0
            true_range = 0.0
            plus_dm = 0.0
            minus_dm = 0.0
        else:
            change = closes[index] - closes[index - 1]
            current = candles[index]
            previous = candles[index - 1]
            true_range = max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
            up = current.high - previous.high
            down = previous.low - current.low
            plus_dm = up if up > down and up > 0.0 else 0.0
            minus_dm = down if down > up and down > 0.0 else 0.0
        gain_prefix.append(gain_prefix[-1] + max(change, 0.0))
        loss_prefix.append(loss_prefix[-1] + max(-change, 0.0))
        true_range_prefix.append(true_range_prefix[-1] + true_range)
        plus_dm_prefix.append(plus_dm_prefix[-1] + plus_dm)
        minus_dm_prefix.append(minus_dm_prefix[-1] + minus_dm)

    for index in range(14, count):
        start = index + 1 - 14
        gains = (gain_prefix[index + 1] - gain_prefix[start]) / 14.0
        losses = (loss_prefix[index + 1] - loss_prefix[start]) / 14.0
        if losses <= 0.0:
            rsi14[index] = 100.0 if gains > 0.0 else 50.0
        else:
            rsi14[index] = 100.0 - 100.0 / (1.0 + gains / losses)
        true_range = true_range_prefix[index + 1] - true_range_prefix[start]
        atr14[index] = true_range / 14.0
        if true_range <= 0.0:
            adx14[index] = 0.0
            continue
        plus_di = 100.0 * (
            plus_dm_prefix[index + 1] - plus_dm_prefix[start]
        ) / true_range
        minus_di = 100.0 * (
            minus_dm_prefix[index + 1] - minus_dm_prefix[start]
        ) / true_range
        denominator = plus_di + minus_di
        adx14[index] = (
            100.0 * abs(plus_di - minus_di) / denominator
            if denominator
            else 0.0
        )

    return _FeatureSet(
        close=closes,
        ema20=_ema_series(closes, 20),
        ema50=_ema_series(closes, 50),
        mean20=mean20,
        std20=std20,
        rsi14=rsi14,
        atr14=atr14,
        adx14=adx14,
        donchian_high20=_previous_rolling_extreme(
            [float(item.high) for item in candles],
            20,
            maximum=True,
        ),
        donchian_low20=_previous_rolling_extreme(
            [float(item.low) for item in candles],
            20,
            maximum=False,
        ),
    )


def _ema_series(values: Sequence[float], period: int) -> Sequence[float]:
    result = array("d", [math.nan]) * len(values)
    if len(values) < period:
        return result
    seed = sum(values[:period]) / period
    result[period - 1] = seed
    multiplier = 2.0 / (period + 1.0)
    for index in range(period, len(values)):
        result[index] = (
            (float(values[index]) - result[index - 1]) * multiplier
            + result[index - 1]
        )
    return result


def _previous_rolling_extreme(
    values: Sequence[float],
    period: int,
    *,
    maximum: bool,
) -> Sequence[float]:
    result = array("d", [math.nan]) * len(values)
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


def _signal_from_features(
    candidate: _Candidate,
    features: _FeatureSet,
    index: int,
) -> str:
    family = candidate.family
    parameters = candidate.parameters
    if family in {"EMA_TREND", "TREND_MOMENTUM"}:
        fast = float(features.ema20[index])
        slow = float(features.ema50[index])
        if not math.isfinite(fast) or not math.isfinite(slow):
            return "WAIT"
        trend = "BUY" if fast > slow else "SELL" if fast < slow else "WAIT"
        if family == "EMA_TREND" or trend == "WAIT":
            return trend
        period = int(parameters["momentum_period"])
        momentum = features.close[index] - features.close[index - period]
        if trend == "BUY" and momentum > 0.0:
            return "BUY"
        if trend == "SELL" and momentum < 0.0:
            return "SELL"
        return "WAIT"

    if family in {
        "MEAN_REVERSION_ZSCORE_RSI",
        "ALPHA017_STRICT_MEAN_REVERSION",
    }:
        deviation = float(features.std20[index])
        rsi = float(features.rsi14[index])
        if not math.isfinite(deviation) or deviation <= 0.0 or not math.isfinite(rsi):
            return "WAIT"
        z_score = (
            features.close[index] - float(features.mean20[index])
        ) / deviation
        if z_score <= -float(parameters["z_threshold"]) and rsi <= float(parameters["rsi_oversold"]):
            signal = "BUY"
        elif z_score >= float(parameters["z_threshold"]) and rsi >= float(parameters["rsi_overbought"]):
            signal = "SELL"
        else:
            return "WAIT"
        if family == "MEAN_REVERSION_ZSCORE_RSI":
            return signal
        atr = float(features.atr14[index])
        adx = float(features.adx14[index])
        width = 4.0 * deviation
        if not math.isfinite(atr) or atr <= 0.0 or not math.isfinite(adx):
            return "WAIT"
        if adx > float(parameters["adx_max"]):
            return "WAIT"
        if width / atr > float(parameters["band_width_atr_max"]):
            return "WAIT"
        return signal

    if family == "DONCHIAN_BREAKOUT":
        high = float(features.donchian_high20[index])
        low = float(features.donchian_low20[index])
        if not math.isfinite(high) or not math.isfinite(low):
            return "WAIT"
        close = features.close[index]
        return "BUY" if close > high else "SELL" if close < low else "WAIT"
    return "WAIT"


def _signal_ema_trend(
    candles: Sequence[MultiEACandle],
    index: int,
    parameters: Mapping[str, object],
) -> str:
    fast = int(parameters["ema_fast"])
    slow = int(parameters["ema_slow"])
    closes = [item.close for item in candles[max(0, index - slow * 4 + 1) : index + 1]]
    fast_value = _ema_last(closes, fast)
    slow_value = _ema_last(closes, slow)
    return "BUY" if fast_value > slow_value else "SELL" if fast_value < slow_value else "WAIT"


def _signal_trend_momentum(
    candles: Sequence[MultiEACandle],
    index: int,
    parameters: Mapping[str, object],
) -> str:
    trend = _signal_ema_trend(candles, index, parameters)
    period = int(parameters["momentum_period"])
    momentum = candles[index].close - candles[index - period].close
    if trend == "BUY" and momentum > 0.0:
        return "BUY"
    if trend == "SELL" and momentum < 0.0:
        return "SELL"
    return "WAIT"


def _signal_mean_reversion(
    candles: Sequence[MultiEACandle],
    index: int,
    parameters: Mapping[str, object],
) -> str:
    window = int(parameters["window"])
    closes = [item.close for item in candles[index - window + 1 : index + 1]]
    deviation = pstdev(closes)
    if deviation <= 0.0:
        return "WAIT"
    z_score = (closes[-1] - sum(closes) / len(closes)) / deviation
    period = int(parameters["rsi_period"])
    rsi = _rsi([item.close for item in candles[index - period : index + 1]], period)
    if z_score <= -float(parameters["z_threshold"]) and rsi <= float(parameters["rsi_oversold"]):
        return "BUY"
    if z_score >= float(parameters["z_threshold"]) and rsi >= float(parameters["rsi_overbought"]):
        return "SELL"
    return "WAIT"


def _signal_alpha017(
    candles: Sequence[MultiEACandle],
    index: int,
    parameters: Mapping[str, object],
) -> str:
    base = _signal_mean_reversion(candles, index, parameters)
    if base == "WAIT":
        return "WAIT"
    period = int(parameters["adx_period"])
    adx = _adx(candles, index, period)
    atr = _atr(candles, index, period)
    window = int(parameters["window"])
    closes = [item.close for item in candles[index - window + 1 : index + 1]]
    width = 4.0 * pstdev(closes)
    if atr <= 0.0 or adx > float(parameters["adx_max"]):
        return "WAIT"
    if width / atr > float(parameters["band_width_atr_max"]):
        return "WAIT"
    return base


def _signal_donchian(
    candles: Sequence[MultiEACandle],
    index: int,
    parameters: Mapping[str, object],
) -> str:
    period = int(parameters["period"])
    previous = candles[index - period : index]
    close = candles[index].close
    if close > max(item.high for item in previous):
        return "BUY"
    if close < min(item.low for item in previous):
        return "SELL"
    return "WAIT"


def _ema_last(values: Sequence[float], period: int) -> float:
    seed = sum(values[:period]) / period
    multiplier = 2.0 / (period + 1.0)
    result = seed
    for value in values[period:]:
        result = (value - result) * multiplier + result
    return result


def _rsi(values: Sequence[float], period: int) -> float:
    changes = [current - previous for previous, current in zip(values, values[1:])]
    gains = sum(max(change, 0.0) for change in changes[-period:]) / period
    losses = sum(max(-change, 0.0) for change in changes[-period:]) / period
    if losses <= 0.0:
        return 100.0 if gains > 0.0 else 50.0
    return 100.0 - 100.0 / (1.0 + gains / losses)


def _atr(candles: Sequence[MultiEACandle], index: int, period: int) -> float:
    ranges = []
    for position in range(index - period + 1, index + 1):
        current = candles[position]
        previous_close = candles[position - 1].close
        ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous_close),
                abs(current.low - previous_close),
            )
        )
    return sum(ranges) / len(ranges) if ranges else 0.0


def _adx(candles: Sequence[MultiEACandle], index: int, period: int) -> float:
    true_range = 0.0
    plus_dm = 0.0
    minus_dm = 0.0
    for position in range(index - period + 1, index + 1):
        current = candles[position]
        previous = candles[position - 1]
        true_range += max(
            current.high - current.low,
            abs(current.high - previous.close),
            abs(current.low - previous.close),
        )
        up = current.high - previous.high
        down = previous.low - current.low
        plus_dm += up if up > down and up > 0.0 else 0.0
        minus_dm += down if down > up and down > 0.0 else 0.0
    if true_range <= 0.0:
        return 0.0
    plus_di = 100.0 * plus_dm / true_range
    minus_di = 100.0 * minus_dm / true_range
    denominator = plus_di + minus_di
    return 100.0 * abs(plus_di - minus_di) / denominator if denominator else 0.0


def _selection_sort_key(row: Mapping[str, object]) -> tuple[float, float, float, int, str]:
    return (
        float(row.get("f1", 0.0) or 0.0),
        float(row.get("precision", 0.0) or 0.0),
        float(row.get("recall", 0.0) or 0.0),
        -int(row.get("signals", 0) or 0),
        str(row.get("candidate_id", "")),
    )


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


def _key(item: _Opportunity) -> tuple[str, int]:
    return item.symbol, item.candle_index


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0 or not math.isfinite(denominator):
        return 0.0
    result = numerator / denominator
    return result if math.isfinite(result) else 0.0
