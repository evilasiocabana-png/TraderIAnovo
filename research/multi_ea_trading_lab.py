"""Motor puro e exploratorio para a amostra publica Multi EA Trading."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from statistics import median, pstdev
from typing import Callable, Mapping, Sequence


@dataclass(frozen=True)
class MultiEATradePosition:
    """Posicao fechada observada no extrato publico."""

    source_symbol: str
    symbol: str
    direction: str
    volume: float
    open_time: datetime
    open_price: float
    close_time: datetime
    close_price: float
    commission: float | None
    swap: float | None
    profit: float
    source_row: int = 0
    position_id: str = ""


@dataclass(frozen=True)
class MultiEACandle:
    """Candle canonico usado somente pelo sublaboratorio."""

    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    source_symbol: str = ""


@dataclass(frozen=True)
class MultiEATradingLabConfiguration:
    """Limites explicitos da primeira amostra exploratoria."""

    minimum_history: int = 55
    holdout_minimum_events: int = 20
    train_fraction: float = 0.70
    cluster_seconds: int = 120


@dataclass(frozen=True)
class _Candidate:
    candidate_id: str
    family: str
    parameters: Mapping[str, object]
    minimum_history: int
    evaluator: Callable[[Sequence[MultiEACandle], int, Mapping[str, object]], str]


TIMEFRAME_SECONDS = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "M30": 1800,
    "H1": 3600,
}

DEFAULT_REPORTED_PROFILE: dict[str, object] = {
    "identificacao": {
        "nome": "Multi EA Trading",
        "autor": "Alexander Pavlenko",
        "corretora": "Alpari-MT5",
        "alavancagem": "1:500",
        "preco_da_copia_usd_por_mes": 30.00,
        "assinantes": 15,
        "capital_de_assinantes_indicado_usd": 20000,
        "crescimento_desde_2025_percentual": 3361.18,
        "semanas": 57,
        "dias_de_negociacao": 102,
        "negociacoes_por_semana": 4,
        "tempo_medio_de_espera": "2 dias",
        "ultimo_negocio_no_registro": "3 dias antes da captura",
    },
    "conta": {
        "deposito_inicial_usd": 10.00,
        "depositos_usd": 613.00,
        "retiradas_usd": 100.00,
        "lucro_usd": 415.06,
        "saldo_usd": 938.06,
        "capital_liquido_usd": 925.79,
    },
    "estatistica": {
        "operacoes": 346,
        "operacoes_com_lucro": 204,
        "taxa_de_acerto_percentual": 58.95,
        "operacoes_com_perda": 142,
        "longas": 143,
        "curtas": 203,
        "melhor_operacao_usd": 96.18,
        "pior_operacao_usd": -17.86,
        "lucro_bruto_usd": 831.07,
        "perda_bruta_usd": -416.01,
        "fator_de_lucro": 2.00,
        "valor_esperado_usd": 1.20,
        "lucro_medio_usd": 4.07,
        "perda_media_usd": -2.93,
        "maximo_vitorias_consecutivas": 14,
        "maximo_perdas_consecutivas": 11,
        "maxima_perda_consecutiva_usd": -40.38,
        "fator_de_recuperacao": 9.10,
        "indice_de_sharpe": 0.21,
    },
    "risco_e_atividade": {
        "atividade_de_negociacao_percentual": 89.42,
        "deposito_maximo_carregado_percentual": 2.73,
        "algorTrading_percentual": 96.0,
        "crescimento_mensal_percentual": 7.85,
        "previsao_anual_percentual": 95.91,
        "drawdown_saldo_absoluto_usd": 0.06,
        "drawdown_saldo_maximo_usd": 45.62,
        "drawdown_saldo_maximo_percentual": 16.30,
        "drawdown_saldo_relativo_percentual": 23.49,
        "drawdown_saldo_relativo_usd": 45.56,
        "drawdown_equity_relativo_percentual": 5.05,
        "drawdown_equity_relativo_usd": 42.10,
    },
    "regras_publicas_da_copia": {
        "alias_de_simbolo": "GOLD == XAUUSD",
        "volume_da_copia": (
            "calculado automaticamente pela relacao entre saldo do assinante "
            "e saldo do provedor"
        ),
        "crescimento": "depositos e retiradas nao entram no calculo",
    },
    "distribuicao_publica_operacoes": {
        "GBPUSD": 80,
        "EURUSD": 49,
        "XAUUSD": 43,
        "USDCAD": 39,
        "AUDJPY": 34,
        "NZDCAD": 19,
        "AUDUSD": 17,
        "EURJPY": 15,
        "NZDUSD": 14,
        "CADCHF": 12,
        "GBPAUD": 9,
        "AUDCAD": 5,
        "GBPCAD": 4,
        "EURNZD": 2,
        "USDJPY": 1,
        "NZDJPY": 1,
        "GBPNZD": 1,
        "BITCOIN": 1,
    },
}


class MultiEATradingLabEngine:
    """Compara hipoteses com entradas observadas, sem acesso externo."""

    def __init__(
        self,
        configuration: MultiEATradingLabConfiguration | None = None,
    ) -> None:
        self.configuration = configuration or MultiEATradingLabConfiguration()

    def analyze(
        self,
        positions: Sequence[MultiEATradePosition],
        candles: Sequence[MultiEACandle],
        *,
        source_timezone: str | None = None,
        reported_profile: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        ordered_positions = sorted(positions, key=lambda item: _time_key(item.open_time))
        series = self._series(candles)
        coverage = self._coverage(ordered_positions, series)
        ranking_global, ranking_by_market = self._rank(ordered_positions, series)
        warnings = [
            "RESEARCH_ONLY: o resultado nao pode alimentar operacao Demo ou real.",
            (
                "AMOSTRA_EXPLORATORIA: aproximacao estatistica nao identifica "
                "o codigo ou os parametros proprietarios do EA."
            ),
            (
                "SAIDAS_NAO_INFERIDAS: o extrato nao revela SL, TP, trailing, "
                "fechamento por cesta ou regra de dimensionamento."
            ),
        ]
        if not source_timezone:
            warnings.append(
                "FUSO_NAO_INFORMADO: timestamps do CSV foram comparados como UTC; "
                "a cobertura e o fit podem mudar com o fuso real da corretora."
            )
        warnings.append(
            "EVENTOS_MULTI_TIMEFRAME_NAO_INDEPENDENTES: a mesma posicao pode "
            "ser elegivel em mais de um timeframe; o score global usa macro-media."
        )
        if not candles:
            warnings.append("HISTORICO_INDISPONIVEL: nenhuma hipotese temporal foi testada.")
        return {
            "schema_version": "multi_ea_trading_fit_v1",
            "status": "OK" if positions else "SEM_POSICOES",
            "classification": "AMOSTRA_EXPLORATORIA",
            "research_only": True,
            "operational_eligible": False,
            "warnings": warnings,
            "reported_profile": dict(reported_profile or DEFAULT_REPORTED_PROFILE),
            "sample": self._sample(ordered_positions),
            "behavior": self._behavior(ordered_positions),
            "coverage": coverage,
            "split": {
                "method": "CRONOLOGICO_70_30_QUANDO_N_MAIOR_OU_IGUAL_20",
                "train_fraction": self.configuration.train_fraction,
                "minimum_events": self.configuration.holdout_minimum_events,
            },
            "ranking_global": ranking_global,
            "ranking_by_market": ranking_by_market,
            "methodology": {
                "entry_alignment": (
                    "ultimo candle completamente fechado antes da entrada"
                ),
                "lookahead": False,
                "timeframes": sorted(TIMEFRAME_SECONDS),
                "candidate_families": sorted(
                    {candidate.family for candidate in self._candidates()}
                ),
                "ranking": (
                    "selecao exclusivamente no treino cronologico por macro-media "
                    "do score de vantagem direcional contra o acaso"
                ),
                "holdout": (
                    "auditoria cronologica fora da ordenacao; nenhuma metrica do "
                    "holdout altera a escolha dos parametros"
                ),
                "score": (
                    "vantagem sobre o baseline aleatorio de 50%, ajustada pela "
                    "cobertura dos gatilhos; 0 significa nenhuma vantagem observada"
                ),
                "global_aggregation": (
                    "macro-media dos scores por ativo/timeframe; contagens e "
                    "demais taxas permanecem agregadas sobre todos os eventos"
                ),
                "claim_limit": (
                    "HIPOTESE_INFERIDA; nenhuma regra e rotulada como setup original"
                ),
            },
        }

    run = analyze

    def _series(
        self,
        candles: Sequence[MultiEACandle],
    ) -> dict[tuple[str, str], list[MultiEACandle]]:
        grouped: dict[tuple[str, str], list[MultiEACandle]] = {}
        for candle in candles:
            key = (str(candle.symbol).upper(), str(candle.timeframe).upper())
            grouped.setdefault(key, []).append(candle)
        for values in grouped.values():
            values.sort(key=lambda item: _time_key(item.timestamp))
        return grouped

    def _rank(
        self,
        positions: Sequence[MultiEATradePosition],
        series: Mapping[tuple[str, str], Sequence[MultiEACandle]],
    ) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
        global_rows: list[dict[str, object]] = []
        by_market: dict[str, list[dict[str, object]]] = {}
        for candidate in self._candidates():
            events_by_market: dict[str, list[dict[str, object]]] = {}
            candidate_market_rows: list[dict[str, object]] = []
            for (symbol, timeframe), market_candles in series.items():
                symbol_positions = [
                    position
                    for position in positions
                    if str(position.symbol).upper() == symbol
                ]
                events = self._candidate_events(
                    candidate,
                    symbol_positions,
                    market_candles,
                    timeframe,
                )
                if not events:
                    continue
                market = f"{symbol}/{timeframe}"
                events_by_market[market] = events
                row = self._ranking_row(candidate, events, market=market)
                candidate_market_rows.append(row)
                by_market.setdefault(market, []).append(row)
            all_events = [
                event
                for market_events in events_by_market.values()
                for event in market_events
            ]
            market_scores = [float(item["score"]) for item in candidate_market_rows]
            train_scores = [
                float(item["selection_score"])
                for item in candidate_market_rows
                if int(dict(item["train"])["eligible"]) > 0
            ]
            holdout_scores = [
                float(dict(item["holdout"])["score"])
                for item in candidate_market_rows
                if int(dict(item["holdout"])["eligible"]) > 0
            ]
            row = self._ranking_row(candidate, all_events, market="TODOS")
            row["score"] = (
                round(sum(market_scores) / len(market_scores), 6)
                if market_scores
                else 0.0
            )
            row["selection_score"] = (
                round(sum(train_scores) / len(train_scores), 6)
                if train_scores
                else 0.0
            )
            train = dict(row["train"])
            holdout = dict(row["holdout"])
            row["holdout_score"] = (
                round(sum(holdout_scores) / len(holdout_scores), 6)
                if holdout_scores
                else 0.0
            )
            row["classification"] = _fit_classification(
                {**train, "score": row["selection_score"]},
                {**holdout, "score": row["holdout_score"]},
            )
            global_rows.append(row)
        global_rows.sort(key=_ranking_sort_key, reverse=True)
        for market, rows in list(by_market.items()):
            rows.sort(key=_ranking_sort_key, reverse=True)
            by_market[market] = rows[:5]
        return global_rows, by_market

    def _candidate_events(
        self,
        candidate: _Candidate,
        positions: Sequence[MultiEATradePosition],
        candles: Sequence[MultiEACandle],
        timeframe: str,
    ) -> list[dict[str, object]]:
        duration = timedelta(seconds=TIMEFRAME_SECONDS.get(timeframe, 60))
        candle_close_times = [
            _time_key(candle.timestamp) + duration for candle in candles
        ]
        events: list[dict[str, object]] = []
        for position in positions:
            entry_time = _time_key(position.open_time)
            index = bisect_right(candle_close_times, entry_time) - 1
            if index >= 0 and not _temporally_adjacent(
                candle_close_times[index],
                entry_time,
                duration,
            ):
                continue
            if index < max(candidate.minimum_history - 1, 0):
                continue
            signal = candidate.evaluator(candles, index, candidate.parameters)
            observed = str(position.direction).upper()
            events.append(
                {
                    "time": _time_key(position.open_time),
                    "observed": observed,
                    "signal": signal,
                    "exact": signal == observed,
                    "opposite": signal in {"BUY", "SELL"} and signal != observed,
                    "wait": signal == "WAIT",
                    "position_id": position.position_id or str(position.source_row),
                }
            )
        return events

    def _ranking_row(
        self,
        candidate: _Candidate,
        events: Sequence[Mapping[str, object]],
        *,
        market: str,
    ) -> dict[str, object]:
        metrics = self._event_metrics(events)
        ordered = sorted(events, key=lambda event: event["time"])
        if len(ordered) >= self.configuration.holdout_minimum_events:
            cut = max(
                1,
                min(
                    len(ordered) - 1,
                    int(len(ordered) * self.configuration.train_fraction),
                ),
            )
            train = self._event_metrics(ordered[:cut])
            holdout = self._event_metrics(ordered[cut:])
        else:
            train = self._empty_metrics()
            holdout = self._empty_metrics()
        selection_score = float(train["score"])
        return {
            "candidate_id": candidate.candidate_id,
            "family": candidate.family,
            "parameters": dict(candidate.parameters),
            "market": market,
            **metrics,
            "selection_score": selection_score,
            "holdout_score": float(holdout["score"]),
            "classification": _fit_classification(train, holdout),
            "train": train,
            "holdout": holdout,
        }

    def _event_metrics(
        self,
        events: Sequence[Mapping[str, object]],
    ) -> dict[str, object]:
        eligible = len(events)
        signaled = sum(event["signal"] in {"BUY", "SELL"} for event in events)
        exact = sum(bool(event["exact"]) for event in events)
        opposite = sum(bool(event["opposite"]) for event in events)
        wait = sum(bool(event["wait"]) for event in events)
        buy_events = [event for event in events if event["observed"] == "BUY"]
        sell_events = [event for event in events if event["observed"] == "SELL"]
        recalls = []
        if buy_events:
            recalls.append(sum(bool(event["exact"]) for event in buy_events) / len(buy_events))
        if sell_events:
            recalls.append(sum(bool(event["exact"]) for event in sell_events) / len(sell_events))
        balanced_accuracy = sum(recalls) / len(recalls) if recalls else 0.0
        observed_recall = signaled / eligible if eligible else 0.0
        direction_accuracy = exact / signaled if signaled else 0.0
        # Uma regra aleatoria que sempre sinaliza tem balanced accuracy e
        # acerto direcional proximos de 0,5. O score mede somente a vantagem
        # acima desse baseline e reduz o credito de regras muito esparsas.
        chance_balanced_accuracy = 0.5 * observed_recall
        available_balanced_edge = max(1.0 - chance_balanced_accuracy, 1e-12)
        balanced_edge = max(
            0.0,
            min(
                1.0,
                (balanced_accuracy - chance_balanced_accuracy)
                / available_balanced_edge,
            ),
        )
        direction_edge = max(0.0, min(1.0, 2.0 * direction_accuracy - 1.0))
        score = (
            0.65 * balanced_edge + 0.35 * direction_edge
        ) * math.sqrt(observed_recall)
        return {
            "eligible": eligible,
            "signaled": signaled,
            "exact_side": exact,
            "opposite_side": opposite,
            "wait": wait,
            "observed_recall": round(observed_recall, 6),
            "direction_accuracy": round(direction_accuracy, 6),
            "balanced_accuracy": round(balanced_accuracy, 6),
            "chance_balanced_accuracy": round(chance_balanced_accuracy, 6),
            "balanced_edge": round(balanced_edge, 6),
            "direction_edge": round(direction_edge, 6),
            "score": round(score, 6),
        }

    def _empty_metrics(self) -> dict[str, object]:
        return self._event_metrics([])

    def _coverage(
        self,
        positions: Sequence[MultiEATradePosition],
        series: Mapping[tuple[str, str], Sequence[MultiEACandle]],
    ) -> dict[str, object]:
        by_series: list[dict[str, object]] = []
        eligible_by_symbol: dict[str, set[str]] = {}
        series_by_symbol: dict[str, list[dict[str, object]]] = {}
        for (symbol, timeframe), values in sorted(series.items()):
            if not values:
                continue
            duration = timedelta(seconds=TIMEFRAME_SECONDS.get(timeframe, 60))
            close_times = [_time_key(item.timestamp) + duration for item in values]
            eligible_ids: set[str] = set()
            for position in positions:
                if str(position.symbol).upper() != symbol:
                    continue
                entry_time = _time_key(position.open_time)
                index = bisect_right(close_times, entry_time) - 1
                if index < 0 or not _temporally_adjacent(
                    close_times[index],
                    entry_time,
                    duration,
                ):
                    continue
                eligible_ids.add(position.position_id or str(position.source_row))
            eligible_by_symbol.setdefault(symbol, set()).update(eligible_ids)
            row = {
                "market": symbol,
                "timeframe": timeframe,
                "candles": len(values),
                "first_candle": values[0].timestamp.isoformat(),
                "last_candle": values[-1].timestamp.isoformat(),
                "eligible_positions": len(eligible_ids),
                "status": "AMOSTRA_5000" if len(values) >= 5000 else "PARCIAL",
            }
            by_series.append(row)
            series_by_symbol.setdefault(symbol, []).append(row)
        position_counts: dict[str, int] = {}
        for position in positions:
            position_counts[position.symbol] = position_counts.get(position.symbol, 0) + 1
        by_market = [
            {
                "market": symbol,
                "positions": count,
                "timeframes": [
                    row["timeframe"] for row in series_by_symbol.get(symbol, [])
                ],
                "candles": sum(
                    int(row["candles"]) for row in series_by_symbol.get(symbol, [])
                ),
                "eligible_positions": len(eligible_by_symbol.get(symbol, set())),
                "temporal_coverage": round(
                    len(eligible_by_symbol.get(symbol, set())) / count,
                    6,
                )
                if count
                else 0.0,
                "status": "COM_HISTORICO" if symbol in series_by_symbol else "SEM_HISTORICO",
            }
            for symbol, count in sorted(position_counts.items())
        ]
        position_ids = set().union(*eligible_by_symbol.values()) if eligible_by_symbol else set()
        markets_with_history = len(series_by_symbol)
        return {
            "total_markets": len(position_counts),
            "markets_with_history": markets_with_history,
            "markets_without_history": len(position_counts) - markets_with_history,
            "positions_with_history": len(position_ids),
            "position_coverage": round(len(position_ids) / len(positions), 6)
            if positions
            else 0.0,
            "series": len(by_series),
            "full_series": sum(int(row["candles"]) >= 5000 for row in by_series),
            "total_candles": sum(int(row["candles"]) for row in by_series),
            "by_market": by_market,
            "by_series": by_series,
        }

    def _sample(
        self,
        positions: Sequence[MultiEATradePosition],
    ) -> dict[str, object]:
        net_values = [
            position.profit + (position.commission or 0.0) + (position.swap or 0.0)
            for position in positions
        ]
        trade_results = [position.profit for position in positions]
        lots: dict[str, int] = {}
        markets: dict[str, int] = {}
        for position in positions:
            lot = f"{position.volume:.2f}"
            lots[lot] = lots.get(lot, 0) + 1
            markets[position.symbol] = markets.get(position.symbol, 0) + 1
        return {
            "positions": len(positions),
            "markets": len(markets),
            "wins": sum(value > 0 for value in trade_results),
            "losses": sum(value < 0 for value in trade_results),
            "flat": sum(
                math.isclose(value, 0.0, abs_tol=1e-12)
                for value in trade_results
            ),
            "buy": sum(position.direction.upper() == "BUY" for position in positions),
            "sell": sum(position.direction.upper() == "SELL" for position in positions),
            "profit_only_usd": round(sum(position.profit for position in positions), 2),
            "commission_usd": round(sum(position.commission or 0.0 for position in positions), 2),
            "swap_usd": round(sum(position.swap or 0.0 for position in positions), 2),
            "net_usd": round(sum(net_values), 2),
            "first_entry": positions[0].open_time.isoformat() if positions else "N/D",
            "last_entry": positions[-1].open_time.isoformat() if positions else "N/D",
            "lot_distribution": lots,
            "position_distribution": dict(sorted(markets.items())),
        }

    def _behavior(
        self,
        positions: Sequence[MultiEATradePosition],
    ) -> dict[str, object]:
        events: list[tuple[datetime, int, int]] = []
        for index, position in enumerate(positions):
            events.append((_time_key(position.open_time), 1, index))
            events.append((_time_key(position.close_time), -1, index))
        events.sort(key=lambda item: (item[0], item[1]))
        concurrent = 0
        maximum_concurrent = 0
        for _, delta, _ in events:
            concurrent += delta
            maximum_concurrent = max(maximum_concurrent, concurrent)
        hedge_ids: set[str] = set()
        for index, left in enumerate(positions):
            for right in positions[index + 1 :]:
                if left.symbol != right.symbol or left.direction == right.direction:
                    continue
                if _intervals_overlap(left, right):
                    hedge_ids.add(left.position_id or str(left.source_row))
                    hedge_ids.add(right.position_id or str(right.source_row))
        clusters = 0
        clustered_positions = 0
        for symbol in {position.symbol for position in positions}:
            closed = sorted(
                (
                    position
                    for position in positions
                    if position.symbol == symbol
                ),
                key=lambda item: _time_key(item.close_time),
            )
            group_size = 1
            for previous, current in zip(closed, closed[1:]):
                gap = (
                    _time_key(current.close_time) - _time_key(previous.close_time)
                ).total_seconds()
                if gap <= self.configuration.cluster_seconds:
                    group_size += 1
                else:
                    if group_size >= 2:
                        clusters += 1
                        clustered_positions += group_size
                    group_size = 1
            if group_size >= 2:
                clusters += 1
                clustered_positions += group_size
        holds = [
            max(
                0.0,
                (_time_key(position.close_time) - _time_key(position.open_time)).total_seconds(),
            )
            for position in positions
        ]
        return {
            "maximum_concurrent_positions": maximum_concurrent,
            "opposite_overlap_positions": len(hedge_ids),
            "same_symbol_close_clusters_120s": clusters,
            "positions_in_close_clusters_120s": clustered_positions,
            "median_holding_minutes": round(median(holds) / 60.0, 2) if holds else 0.0,
            "interpretation": (
                "Sobreposicao, hedge e fechamentos agrupados sao compativeis "
                "com varios EAs ou gestao por cesta; nao provam uma grade especifica."
            ),
        }

    def _candidates(self) -> tuple[_Candidate, ...]:
        candidates: list[_Candidate] = []
        for fast, slow in ((9, 21), (14, 50), (20, 50)):
            parameters = {"ema_fast": fast, "ema_slow": slow}
            candidates.append(
                _Candidate(
                    f"EMA_TREND_{fast}_{slow}",
                    "EMA_TREND",
                    parameters,
                    slow + 1,
                    _signal_ema_trend,
                )
            )
            for momentum_period in (3, 5, 10):
                values = {**parameters, "momentum_period": momentum_period}
                candidates.append(
                    _Candidate(
                        f"TREND_MOMENTUM_{fast}_{slow}_{momentum_period}",
                        "TREND_MOMENTUM",
                        values,
                        slow + momentum_period + 1,
                        _signal_trend_momentum,
                    )
                )
        for threshold, oversold, overbought in (
            (1.5, 25.0, 75.0),
            (1.5, 30.0, 70.0),
            (2.0, 25.0, 75.0),
            (2.0, 30.0, 70.0),
            (2.5, 25.0, 75.0),
        ):
            parameters = {
                "window": 20,
                "z_threshold": threshold,
                "rsi_period": 14,
                "rsi_oversold": oversold,
                "rsi_overbought": overbought,
            }
            candidates.append(
                _Candidate(
                    f"MEAN_REVERSION_Z{threshold:g}_RSI{oversold:g}_{overbought:g}",
                    "MEAN_REVERSION_ZSCORE_RSI",
                    parameters,
                    22,
                    _signal_mean_reversion,
                )
            )
        for threshold, adx_max in ((1.5, 18.0), (2.0, 22.0), (2.5, 25.0)):
            parameters = {
                "window": 20,
                "z_threshold": threshold,
                "rsi_period": 14,
                "rsi_oversold": 25.0,
                "rsi_overbought": 75.0,
                "adx_period": 14,
                "adx_max": adx_max,
                "band_width_atr_max": 6.0,
            }
            candidates.append(
                _Candidate(
                    f"ALPHA017_STRICT_Z{threshold:g}_ADX{adx_max:g}",
                    "ALPHA017_STRICT_MEAN_REVERSION",
                    parameters,
                    30,
                    _signal_alpha017,
                )
            )
        for period in (10, 20, 50):
            candidates.append(
                _Candidate(
                    f"DONCHIAN_BREAKOUT_{period}",
                    "DONCHIAN_BREAKOUT",
                    {"period": period},
                    period + 1,
                    _signal_donchian,
                )
            )
        return tuple(candidates)


def _signal_ema_trend(
    candles: Sequence[MultiEACandle],
    index: int,
    parameters: Mapping[str, object],
) -> str:
    fast_period = int(parameters["ema_fast"])
    slow_period = int(parameters["ema_slow"])
    lookback = max(fast_period, slow_period) * 4
    closes = [
        item.close for item in candles[max(0, index - lookback + 1) : index + 1]
    ]
    fast = _ema_last(closes, fast_period)
    slow = _ema_last(closes, slow_period)
    return "BUY" if fast > slow else "SELL" if fast < slow else "WAIT"


def _signal_trend_momentum(
    candles: Sequence[MultiEACandle],
    index: int,
    parameters: Mapping[str, object],
) -> str:
    direction = _signal_ema_trend(candles, index, parameters)
    period = int(parameters["momentum_period"])
    current = candles[index].close
    previous = candles[index - period].close
    momentum = current / previous - 1.0 if previous else 0.0
    if direction == "BUY" and momentum > 0.0:
        return "BUY"
    if direction == "SELL" and momentum < 0.0:
        return "SELL"
    return "WAIT"


def _signal_mean_reversion(
    candles: Sequence[MultiEACandle],
    index: int,
    parameters: Mapping[str, object],
) -> str:
    window = int(parameters["window"])
    closes = [item.close for item in candles[max(0, index - window + 1) : index + 1]]
    deviation = pstdev(closes)
    if deviation <= 0.0:
        return "WAIT"
    z_score = (closes[-1] - sum(closes) / len(closes)) / deviation
    rsi_period = int(parameters["rsi_period"])
    rsi = _rsi(
        [
            item.close
            for item in candles[max(0, index - rsi_period) : index + 1]
        ],
        rsi_period,
    )
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
    base_signal = _signal_mean_reversion(candles, index, parameters)
    if base_signal == "WAIT":
        return "WAIT"
    period = int(parameters["adx_period"])
    recent = candles[max(0, index - period) : index + 1]
    atr = _atr(recent)
    closes = [item.close for item in candles[max(0, index - 19) : index + 1]]
    width = 4.0 * pstdev(closes) if len(closes) >= 2 else 0.0
    adx = _adx(recent)
    if atr <= 0.0 or width / atr > float(parameters["band_width_atr_max"]):
        return "WAIT"
    if adx > float(parameters["adx_max"]):
        return "WAIT"
    return base_signal


def _signal_donchian(
    candles: Sequence[MultiEACandle],
    index: int,
    parameters: Mapping[str, object],
) -> str:
    period = int(parameters["period"])
    prior = candles[index - period : index]
    close = candles[index].close
    upper = max(item.high for item in prior)
    lower = min(item.low for item in prior)
    if close > upper:
        return "BUY"
    if close < lower:
        return "SELL"
    return "WAIT"


def _ema_last(values: Sequence[float], period: int) -> float:
    selected = list(values[-max(period * 4, period) :])
    if not selected:
        return 0.0
    alpha = 2.0 / (period + 1.0)
    result = selected[0]
    for value in selected[1:]:
        result = value * alpha + result * (1.0 - alpha)
    return result


def _rsi(values: Sequence[float], period: int) -> float:
    if len(values) <= period:
        return 50.0
    changes = [
        current - previous
        for previous, current in zip(values[-period - 1 : -1], values[-period:])
    ]
    gains = sum(max(change, 0.0) for change in changes) / period
    losses = sum(max(-change, 0.0) for change in changes) / period
    if losses <= 0.0:
        return 100.0 if gains > 0.0 else 50.0
    return 100.0 - 100.0 / (1.0 + gains / losses)


def _atr(candles: Sequence[MultiEACandle]) -> float:
    if len(candles) < 2:
        return 0.0
    ranges = [
        max(
            candle.high - candle.low,
            abs(candle.high - previous.close),
            abs(candle.low - previous.close),
        )
        for previous, candle in zip(candles[:-1], candles[1:])
    ]
    return sum(ranges) / len(ranges) if ranges else 0.0


def _adx(candles: Sequence[MultiEACandle]) -> float:
    if len(candles) < 3:
        return 0.0
    plus_dm = 0.0
    minus_dm = 0.0
    true_range = 0.0
    for previous, current in zip(candles[:-1], candles[1:]):
        up = current.high - previous.high
        down = previous.low - current.low
        plus_dm += up if up > down and up > 0.0 else 0.0
        minus_dm += down if down > up and down > 0.0 else 0.0
        true_range += max(
            current.high - current.low,
            abs(current.high - previous.close),
            abs(current.low - previous.close),
        )
    if true_range <= 0.0:
        return 0.0
    plus_di = 100.0 * plus_dm / true_range
    minus_di = 100.0 * minus_dm / true_range
    denominator = plus_di + minus_di
    return 100.0 * abs(plus_di - minus_di) / denominator if denominator else 0.0


def _time_key(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _intervals_overlap(
    left: MultiEATradePosition,
    right: MultiEATradePosition,
) -> bool:
    return (
        _time_key(left.open_time) < _time_key(right.close_time)
        and _time_key(right.open_time) < _time_key(left.close_time)
    )


def _temporally_adjacent(
    candle_close: datetime,
    entry_time: datetime,
    duration: timedelta,
) -> bool:
    gap = entry_time - candle_close
    if gap < timedelta(0):
        return False
    if gap <= duration * 2:
        return True
    return (
        entry_time.weekday() == 0
        and candle_close.weekday() in {4, 5, 6}
        and gap <= timedelta(hours=72)
    )


def _fit_classification(
    train: Mapping[str, object],
    holdout: Mapping[str, object],
) -> str:
    train_events = int(train.get("eligible", 0) or 0)
    train_signals = int(train.get("signaled", 0) or 0)
    train_score = float(train.get("score", 0.0) or 0.0)
    if train_events < 14:
        return "EVIDENCIA_INSUFICIENTE"
    if train_signals == 0:
        return "NAO_SUPORTADA_PELA_AMOSTRA"
    if train_signals < 8:
        return "EVIDENCIA_INSUFICIENTE"
    if train_score < 0.10:
        return "NAO_SUPORTADA_PELA_AMOSTRA"
    holdout_score = float(holdout.get("score", 0.0) or 0.0)
    holdout_events = int(holdout.get("eligible", 0) or 0)
    holdout_signals = int(holdout.get("signaled", 0) or 0)
    if holdout_events < 10 or holdout_signals < 8:
        return "HOLDOUT_INCONCLUSIVO"
    if holdout_score < 0.05:
        return "INSTAVEL_NO_HOLDOUT"
    if train_score >= 0.25 and holdout_score >= 0.15:
        return "HIPOTESE_PLAUSIVEL_NAO_IDENTIFICADA"
    return "HIPOTESE_FRACA"


def _ranking_sort_key(
    row: Mapping[str, object],
) -> tuple[float, int, int, float]:
    """Ordena somente com informacao do treino; holdout fica intocado."""

    train = dict(row.get("train", {}) or {})
    return (
        float(row.get("selection_score", 0.0) or 0.0),
        int(train.get("signaled", 0) or 0),
        int(train.get("eligible", 0) or 0),
        float(train.get("observed_recall", 0.0) or 0.0),
    )
