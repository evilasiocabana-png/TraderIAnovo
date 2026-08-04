"""Orquestracao sob demanda do sublaboratorio Multi EA Trading."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import math
import os
from pathlib import Path
from typing import Any

from infrastructure.research.multi_ea_local_data_adapter import (
    MultiEALocalDataAdapter,
)
from research.multi_ea_entry_architecture import MultiEAEntryArchitectureEngine
from research.multi_ea_intrabar_search import MultiEAIntrabarSearchEngine
from research.multi_ea_rule_miner import MultiEAM15RuleMiner
from research.multi_ea_strategy_search import MultiEAStrategySearchEngine
from research.multi_ea_trading_entry_fit import MultiEAM15EntryFitEngine
from research.multi_ea_trading_lab import MultiEATradingLabEngine


MULTI_EA_TRADING_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1")
MULTI_EA_TRADING_TIMEFRAME_VALUES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 16385,
}
MULTI_EA_M15_MINIMUM_CANDLES = 5000
MULTI_EA_M15_WARMUP_DAYS = 7
MULTI_EA_M15_MAX_INTERNAL_GAP_DAYS = 7
MULTI_EA_PROVIDER_SYMBOLS = {"BITCOIN": "BTCUSD"}


@dataclass
class MultiEATradingLabUseCase:
    """Coordena CSV, caches locais e motor puro sem tocar execucao."""

    adapter: MultiEALocalDataAdapter = field(default_factory=MultiEALocalDataAdapter)
    engine: MultiEATradingLabEngine = field(default_factory=MultiEATradingLabEngine)
    entry_fit_engine: MultiEAM15EntryFitEngine = field(
        default_factory=MultiEAM15EntryFitEngine
    )
    entry_architecture_engine: MultiEAEntryArchitectureEngine = field(
        default_factory=MultiEAEntryArchitectureEngine
    )
    strategy_search_engine: MultiEAStrategySearchEngine = field(
        default_factory=MultiEAStrategySearchEngine
    )
    intrabar_search_engine: MultiEAIntrabarSearchEngine = field(
        default_factory=MultiEAIntrabarSearchEngine
    )
    rule_miner_engine: MultiEAM15RuleMiner = field(
        default_factory=MultiEAM15RuleMiner
    )
    candle_count: int = 5000
    timeframes: tuple[str, ...] = MULTI_EA_TRADING_TIMEFRAMES

    def get_report(self) -> dict[str, Any]:
        """Retorna somente o artefato compacto previamente calculado."""

        stored = self.adapter.read_fit_result()
        if stored:
            return stored
        return self._empty_report(
            "SEM_RESULTADO",
            "A amostra Multi EA Trading ainda nao foi executada.",
        )

    def run(self, source_path: str | Path | None = None) -> dict[str, Any]:
        """Executa o fit exploratorio usando apenas dados locais existentes."""

        previous_report = self.adapter.read_fit_result()
        import_summary: dict[str, Any] = {}
        if source_path is None:
            configured_source = os.getenv(
                "TRADERIA_MULTI_EA_POSITIONS_CSV",
                "",
            ).strip()
            if configured_source:
                source_path = configured_source
        if source_path is not None:
            imported = self.adapter.import_positions_csv(source_path, strict=True)
            import_summary = {
                "source_name": Path(source_path).name,
                "source_sha256": imported.source_sha256,
                "total_rows": imported.total_rows,
                "trade_rows": imported.trade_rows,
                "balance_rows": imported.balance_rows,
                "ignored_rows": imported.ignored_rows,
                "persisted_path": imported.persisted_path,
            }
        positions = self.adapter.load_positions(strict=True)
        if not positions:
            return self._empty_report(
                "SEM_FONTE",
                "positions.csv ainda nao foi importado. Informe source_path na "
                "fachada ou configure TRADERIA_MULTI_EA_POSITIONS_CSV.",
            )

        first_entry = min(_utc_datetime(item.open_time) for item in positions)
        last_entry = max(_utc_datetime(item.open_time) for item in positions)
        m15_required_start = first_entry - timedelta(
            days=MULTI_EA_M15_WARMUP_DAYS
        )
        candles = []
        series_loaded: list[dict[str, Any]] = []
        for symbol in sorted({position.symbol for position in positions}):
            for timeframe in self.timeframes:
                limit = (
                    None
                    if timeframe == "M15"
                    else self.candle_count
                )
                series = self.adapter.load_candles(
                    symbol,
                    timeframe,
                    limit=limit,
                )
                if timeframe == "M15":
                    series = self._filter_m15_analysis_window(
                        series,
                        required_start=m15_required_start,
                        required_end=last_entry,
                    )
                candles.extend(series)
                if series:
                    series_loaded.append(
                        {
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "candles": len(series),
                            "first_candle": series[0].timestamp.isoformat(),
                            "last_candle": series[-1].timestamp.isoformat(),
                        }
                    )

        result = dict(
            self.engine.analyze(
                positions,
                candles,
                source_timezone=None,
            )
        )
        result["m15_entry_fit"] = self.entry_fit_engine.analyze(
            positions,
            candles,
            source_timezone=None,
        )
        result["entry_architecture"] = self.entry_architecture_engine.analyze(
            positions,
        )
        result["strategy_search"] = self.strategy_search_engine.analyze(
            positions,
            candles,
            source_timezone=None,
        )
        result["intrabar_search"] = self.intrabar_search_engine.analyze(
            positions,
            candles,
            source_timezone=None,
        )
        result["rule_miner"] = self.rule_miner_engine.analyze(
            positions,
            candles,
            source_timezone=None,
        )
        result["m15_history_coverage"] = self._summarize_m15_history_coverage(
            positions,
            candles,
        )
        fit_coverage = dict(
            dict(result["m15_entry_fit"].get("causal_fit", {}) or {}).get(
                "coverage", {}
            )
            or {}
        )
        result["m15_history_coverage"].update(
            {
                "entry_rows_with_adjacent_m15": int(
                    fit_coverage.get("eligible_positions", 0) or 0
                ),
                "source_entry_rows": int(
                    fit_coverage.get("source_positions", len(positions))
                    or len(positions)
                ),
            }
        )
        result.update(
            {
                "name": "Multi EA Trading",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "research_only": True,
                "operational_eligible": False,
                "candle_limit_per_series": self.candle_count,
                "candle_limits_by_timeframe": {
                    timeframe: (
                        None
                        if timeframe == "M15"
                        else self.candle_count
                    )
                    for timeframe in self.timeframes
                },
                "m15_load_policy": (
                    "FULL_LOCAL_RANGE_FILTERED_TO_CSV_PERIOD_PLUS_7D_WARMUP"
                ),
                "requested_timeframes": list(self.timeframes),
                "source_import": import_summary
                or self.adapter.get_history_metadata().get("positions_import", {}),
                "series_loaded": series_loaded,
                "local_artifacts": {
                    "positions": str(self.adapter.positions_path),
                    "history_database": str(self.adapter.history_database_path),
                    "fit_result": str(self.adapter.fit_result_path),
                },
            }
        )
        cached_gold = self._cached_gold_summary()
        if isinstance(previous_report.get("gold_download"), dict):
            gold_download = dict(previous_report["gold_download"])
            if cached_gold:
                gold_download["persisted_by_timeframe"] = dict(
                    cached_gold["persisted_by_timeframe"]
                )
            result["gold_download"] = gold_download
        elif cached_gold:
            result["gold_download"] = cached_gold
        previous_source = dict(previous_report.get("source_import", {}) or {})
        current_source = dict(result.get("source_import", {}) or {})
        current_source_hash = str(
            current_source.get("source_sha256", "") or ""
        ).lower()
        previous_source_hash = str(
            previous_source.get("source_sha256", "") or ""
        ).lower()
        same_positions_source = bool(
            current_source_hash
            and current_source_hash == previous_source_hash
        )
        if (
            same_positions_source
            and isinstance(previous_report.get("full_m15_download"), dict)
        ):
            result["full_m15_download"] = dict(
                previous_report["full_m15_download"]
            )
        self._add_reverse_engineering_audit(result)
        self.adapter.write_fit_result(result)
        return result

    def download_full_m15_history(
        self,
        provider: object,
        progress_callback: object | None = None,
    ) -> dict[str, Any]:
        """Baixa M15 suficiente para cobrir todas as entradas do CSV."""

        positions = self.adapter.load_positions(strict=True)
        if not positions:
            raise RuntimeError(
                "positions.csv precisa ser importado antes do historico M15 completo."
            )
        batch_reader = getattr(provider, "get_research_batch", None)
        range_reader = getattr(provider, "get_research_range", None)
        if not callable(batch_reader) and not callable(range_reader):
            raise RuntimeError("Provider read-only nao oferece leitura M15 em lote.")

        first_entry = min(_utc_datetime(item.open_time) for item in positions)
        last_entry = max(_utc_datetime(item.open_time) for item in positions)
        required_start = first_entry - timedelta(days=MULTI_EA_M15_WARMUP_DAYS)
        requested_count = self._full_m15_request_count(positions)
        minimum_period_candles = self._minimum_m15_period_candles(
            required_start,
            last_entry,
        )
        symbols = sorted({str(item.symbol).upper() for item in positions})
        by_symbol: list[dict[str, Any]] = []
        incomplete: list[str] = []

        for symbol in symbols:
            provider_symbol = MULTI_EA_PROVIDER_SYMBOLS.get(symbol, symbol)
            persisted = self._load_effective_candles(
                symbol,
                "M15",
                limit=None,
            )
            persisted_in_window = self._filter_m15_analysis_window(
                persisted,
                required_start=required_start,
                required_end=last_entry,
            )
            first_candle, last_candle, coverage_ok = self._m15_coverage(
                persisted_in_window,
                required_start=required_start,
                required_end=last_entry,
                minimum_candles=minimum_period_candles,
            )
            gap_diagnostics = self._m15_gap_diagnostics(persisted_in_window)
            exists = bool(persisted)
            selected = False
            raw_candles: list[object] = []
            source = "CACHE"

            if not coverage_ok:
                source = "MT5_RANGE" if callable(range_reader) else "MT5_BATCH"
                if callable(range_reader):
                    range_payload = range_reader(
                        [provider_symbol],
                        MULTI_EA_TRADING_TIMEFRAME_VALUES["M15"],
                        required_start,
                        last_entry + timedelta(minutes=15),
                    )
                    payload = {"M15": dict(range_payload or {})}
                else:
                    payload = batch_reader(
                        [provider_symbol],
                        {"M15": MULTI_EA_TRADING_TIMEFRAME_VALUES["M15"]},
                        requested_count,
                    )
                row = dict(
                    dict(payload.get("M15", {}) or {}).get(provider_symbol, {})
                    or {}
                )
                exists = bool(row.get("exists", False))
                selected = bool(row.get("selected", False))
                raw_candles = list(row.get("candles", []) or [])
                if exists and selected and raw_candles:
                    self.adapter.store_provider_candles(
                        {"M15": {provider_symbol: row}},
                        requested_count=requested_count,
                        source="MT5_READ_ONLY_FULL_M15",
                    )
                persisted = self._load_effective_candles(
                    symbol,
                    "M15",
                    limit=None,
                )
                persisted_in_window = self._filter_m15_analysis_window(
                    persisted,
                    required_start=required_start,
                    required_end=last_entry,
                )
                first_candle, last_candle, coverage_ok = self._m15_coverage(
                    persisted_in_window,
                    required_start=required_start,
                    required_end=last_entry,
                    minimum_candles=minimum_period_candles,
                )
                gap_diagnostics = self._m15_gap_diagnostics(
                    persisted_in_window
                )
            if not coverage_ok:
                incomplete.append(symbol)
            progress = {
                "symbol": symbol,
                "provider_symbol": provider_symbol,
                "exists": exists,
                "selected": selected,
                "received_candles": len(raw_candles),
                "persisted_unique_candles": len(persisted),
                "period_candles": len(persisted_in_window),
                "first_candle": first_candle.isoformat() if first_candle else None,
                "last_candle": last_candle.isoformat() if last_candle else None,
                "covers_csv_period_with_warmup": coverage_ok,
                **gap_diagnostics,
                "source": source,
            }
            by_symbol.append(progress)
            if callable(progress_callback):
                progress_callback(dict(progress))

        result = self.run()
        result["full_m15_download"] = {
            "status": "OK" if not incomplete else "PARCIAL",
            "timeframe": "M15",
            "requested_candles_per_symbol": requested_count,
            "minimum_candles_per_symbol": MULTI_EA_M15_MINIMUM_CANDLES,
            "minimum_expected_period_candles": minimum_period_candles,
            "warmup_days": MULTI_EA_M15_WARMUP_DAYS,
            "csv_first_entry": first_entry.isoformat(),
            "csv_last_entry": last_entry.isoformat(),
            "required_first_candle": required_start.isoformat(),
            "symbols_requested": len(symbols),
            "symbols_complete": len(symbols) - len(incomplete),
            "incomplete_symbols": incomplete,
            "by_symbol": by_symbol,
            "read_only": True,
            "operational_database_modified": False,
        }
        self.adapter.write_fit_result(result)
        return result

    def _load_effective_candles(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int | None,
    ) -> list[object]:
        """Le a serie combinada; mantem compatibilidade com adapters de teste."""

        combined_loader = getattr(self.adapter, "load_candles", None)
        if callable(combined_loader):
            combined = list(combined_loader(symbol, timeframe, limit=limit) or [])
            if combined:
                return combined
        research_loader = getattr(self.adapter, "load_research_candles", None)
        if callable(research_loader):
            return list(research_loader(symbol, timeframe, limit=limit) or [])
        return []

    def _add_reverse_engineering_audit(self, result: dict[str, Any]) -> None:
        """Consolida escopo, unidades de avaliacao e limites no artefato final."""

        strategy = dict(result.get("strategy_search", {}) or {})
        intrabar = dict(result.get("intrabar_search", {}) or {})
        rule_miner = dict(result.get("rule_miner", {}) or {})
        rule_search = dict(rule_miner.get("rule_search", {}) or {})
        rule_tests = sum(
            int(rule_search.get(key, 0) or 0)
            for key in ("seed_directional_rules_evaluated", "and_rules_evaluated")
        )
        sample = dict(result.get("sample", {}) or {})
        reported = dict(result.get("reported_profile", {}) or {})
        public_statistics = dict(reported.get("estatistica", {}) or {})
        source_rows = int(sample.get("positions", 0) or 0)
        public_operations = int(public_statistics.get("operacoes", 0) or 0)
        result["reverse_engineering_audit"] = {
            "total_hypotheses_and_rules": (
                int(strategy.get("candidate_count", 0) or 0)
                + int(intrabar.get("candidate_count", 0) or 0)
                + rule_tests
            ),
            "source_entry_rows": source_rows,
            "public_operations_at_capture": public_operations,
            "source_share_of_public_operations_percent": (
                round(source_rows / public_operations * 100.0, 6)
                if public_operations
                else None
            ),
            "oracle_entry_replay": "SOURCE_ROW_EX_POST",
            "full_source_row_causal_replication": False,
            "causal_seed_trigger_identified": False,
            "stateful_seed_plus_followers_simulator_built": False,
            "source_timezone_resolved": False,
            "sub_ea_activation_windows_known": False,
            "evaluation_units_directly_comparable": False,
            "evaluation_units": {
                "indicator_search": "SYMBOL_M15_EVENT",
                "intrabar_search": intrabar.get(
                    "evaluation_unit", "SYMBOL_M15_DIRECTION_LABEL"
                ),
                "rule_miner": "SYMBOL_M15_EVENT",
                "oracle_replay": "SOURCE_ROW",
            },
            "target_informed_temporal_splits": [
                "m15_entry_fit",
                "strategy_search",
                "rule_miner",
            ],
        }

        warnings = [str(item) for item in list(result.get("warnings", []) or [])]
        for section_name in (
            "m15_entry_fit",
            "entry_architecture",
            "strategy_search",
            "intrabar_search",
            "rule_miner",
        ):
            section = dict(result.get(section_name, {}) or {})
            warnings.extend(
                str(item)
                for item in list(section.get("warnings", []) or [])
            )
        warnings.extend(
            [
                (
                    "UNIDADES_NAO_COMPARAVEIS: os motores medem eventos, rotulos "
                    "direcionais ou linhas de origem diferentes; precisao e recall "
                    "nao devem ser comparados diretamente entre eles."
                ),
                (
                    "MULTIPLICIDADE_AGRUPADA: os motores causais M15 agrupam tickets "
                    "repetidos e hedges por ativo/candle/direcao; nao reproduzem "
                    f"individualmente as {source_rows} linhas de entrada."
                ),
                (
                    "ARQUITETURA_SEM_SIMULADOR: os seguidores stateful foram "
                    "classificados depois das entradas, mas ainda nao alimentam um "
                    "simulador seed+split+grade+piramidagem+hedge."
                ),
                (
                    "JANELAS_DE_ATIVACAO_DESCONHECIDAS: os testes assumem cada "
                    "sub-EA ativo continuamente no periodo global, o que pode inflar "
                    "falsos positivos."
                ),
                (
                    "SPLITS_PARCIALMENTE_INFORMADOS_PELO_ALVO: tres motores usam "
                    "timestamps positivos para garantir amostras de validacao; falta "
                    "um teste final intocado ou walk-forward."
                ),
            ]
        )
        if public_operations > source_rows > 0:
            warnings.append(
                "CSV_PUBLICO_INCOMPLETO: o CSV contem "
                f"{source_rows} de {public_operations} operacoes exibidas na captura "
                "publica; barras sem registro sao negativos assumidos (problema "
                "positive-unlabeled)."
            )
        m15_history = dict(result.get("m15_history_coverage", {}) or {})
        incomplete_symbols = list(m15_history.get("incomplete_symbols", []) or [])
        if incomplete_symbols:
            warnings.append(
                "M15_PERIODO_COM_WARMUP_PARCIAL: a serie combinada cobre o "
                f"periodo completo em {int(m15_history.get('symbols_complete', 0) or 0)}/"
                f"{int(m15_history.get('symbols_requested', 0) or 0)} ativos; "
                "quantidade, limites temporais ou gaps internos falharam em "
                + ", ".join(str(item) for item in incomplete_symbols)
                + ". A cobertura de entradas e informada separadamente."
            )
        result["warnings"] = list(dict.fromkeys(warnings))

    def _summarize_m15_history_coverage(
        self,
        positions: list[object],
        candles: list[object],
    ) -> dict[str, Any]:
        """Resume a serie efetiva combinada usada no calculo, sem novo download."""

        if not positions:
            return {}
        first_entry = min(
            _utc_datetime(getattr(item, "open_time")) for item in positions
        )
        last_entry = max(
            _utc_datetime(getattr(item, "open_time")) for item in positions
        )
        required_start = first_entry - timedelta(days=MULTI_EA_M15_WARMUP_DAYS)
        minimum_candles = self._minimum_m15_period_candles(
            required_start,
            last_entry,
        )
        symbols = sorted(
            {str(getattr(item, "symbol", "")).upper() for item in positions}
        )
        grouped: dict[str, list[object]] = {symbol: [] for symbol in symbols}
        for candle in candles:
            if str(getattr(candle, "timeframe", "")).upper() != "M15":
                continue
            symbol = str(getattr(candle, "symbol", "")).upper()
            if symbol in grouped:
                grouped[symbol].append(candle)
        rows: list[dict[str, Any]] = []
        incomplete: list[str] = []
        total_candles = 0
        for symbol in symbols:
            series = sorted(
                grouped.get(symbol, []),
                key=lambda item: _utc_datetime(getattr(item, "timestamp")),
            )
            total_candles += len(series)
            first_candle, last_candle, coverage_ok = self._m15_coverage(
                series,
                required_start=required_start,
                required_end=last_entry,
                minimum_candles=minimum_candles,
            )
            gap_diagnostics = self._m15_gap_diagnostics(series)
            if not coverage_ok:
                incomplete.append(symbol)
            rows.append(
                {
                    "symbol": symbol,
                    "candles": len(series),
                    "first_candle": (
                        first_candle.isoformat() if first_candle else None
                    ),
                    "last_candle": (
                        last_candle.isoformat() if last_candle else None
                    ),
                    "covers_csv_period_with_warmup": coverage_ok,
                    **gap_diagnostics,
                }
            )
        return {
            "status": "OK" if not incomplete else "PARCIAL",
            "source": "OPERATIONAL_PLUS_RESEARCH_EFFECTIVE_SERIES",
            "timeframe": "M15",
            "warmup_days": MULTI_EA_M15_WARMUP_DAYS,
            "csv_first_entry": first_entry.isoformat(),
            "csv_last_entry": last_entry.isoformat(),
            "required_first_candle": required_start.isoformat(),
            "minimum_expected_period_candles": minimum_candles,
            "symbols_requested": len(symbols),
            "symbols_complete": len(symbols) - len(incomplete),
            "incomplete_symbols": incomplete,
            "total_effective_candles": total_candles,
            "by_symbol": rows,
        }

    def download_gold(self, provider: object) -> dict[str, Any]:
        """Baixa XAUUSD read-only para a base isolada e recalcula a amostra."""

        batch_reader = getattr(provider, "get_research_batch", None)
        if not callable(batch_reader):
            raise RuntimeError("Provider read-only nao oferece leitura multi-timeframe.")
        payload = batch_reader(
            ["XAUUSD"],
            dict(MULTI_EA_TRADING_TIMEFRAME_VALUES),
            self.candle_count,
        )
        download_summary = dict(
            self.adapter.store_provider_candles(
                payload,
                requested_count=self.candle_count,
                source="MT5_READ_ONLY_XAUUSD",
            )
        )
        if int(download_summary.get("total_candles", 0) or 0) <= 0:
            provider_error = str(getattr(provider, "last_error", "") or "")
            raise RuntimeError(
                provider_error
                or "MT5 nao retornou candles de XAUUSD para os timeframes solicitados."
            )
        received = dict(download_summary.get("received_by_timeframe", {}) or {})
        persisted = dict(received)
        research_loader = getattr(self.adapter, "load_research_candles", None)
        if callable(research_loader):
            persisted = {
                timeframe: len(
                    research_loader(
                        "XAUUSD",
                        timeframe,
                        limit=self.candle_count,
                    )
                )
                for timeframe in self.timeframes
            }
        download_summary["persisted_by_timeframe"] = persisted
        incomplete = [
            timeframe
            for timeframe in self.timeframes
            if int(persisted.get(timeframe, 0) or 0) < self.candle_count
        ]
        if incomplete:
            raise RuntimeError(
                "Download XAUUSD incompleto em: "
                + ", ".join(incomplete)
                + ". Os dados parciais ficaram isolados e nao alteraram o banco operacional."
            )
        result = self.run()
        result["gold_download"] = {
            **download_summary,
            "symbol": "XAUUSD",
            "alias_publico": "GOLD",
            "requested_candles_per_timeframe": self.candle_count,
            "requested_timeframes": list(self.timeframes),
            "read_only": True,
            "operational_database_modified": False,
        }
        self.adapter.write_fit_result(result)
        return result

    def _cached_gold_summary(self) -> dict[str, Any]:
        loader = getattr(self.adapter, "load_research_candles", None)
        if not callable(loader):
            return {}
        received = {
            timeframe: len(
                loader("XAUUSD", timeframe, limit=self.candle_count)
            )
            for timeframe in self.timeframes
        }
        total = sum(received.values())
        if total <= 0:
            return {}
        return {
            "received_by_timeframe": received,
            "persisted_by_timeframe": received,
            "total_candles": total,
            "database_path": str(self.adapter.history_database_path),
            "status": "CACHED",
            "symbol": "XAUUSD",
            "alias_publico": "GOLD",
            "requested_candles_per_timeframe": self.candle_count,
            "requested_timeframes": list(self.timeframes),
            "read_only": True,
            "operational_database_modified": False,
        }

    def _full_m15_request_count(self, positions: list[object]) -> int:
        """Teto 24/7 desde o aquecimento ate agora, arredondado a mil."""

        if not positions:
            return MULTI_EA_M15_MINIMUM_CANDLES
        first_entry = min(
            _utc_datetime(getattr(item, "open_time")) for item in positions
        )
        required_start = first_entry - timedelta(days=MULTI_EA_M15_WARMUP_DAYS)
        last_entry = max(
            _utc_datetime(getattr(item, "open_time")) for item in positions
        )
        tail_end = max(last_entry, datetime.now(timezone.utc))
        elapsed = max(0.0, (tail_end - required_start).total_seconds())
        continuous_m15 = math.ceil(elapsed / timedelta(minutes=15).total_seconds())
        safe_count = max(continuous_m15 + 1, MULTI_EA_M15_MINIMUM_CANDLES)
        return int(math.ceil(safe_count / 1000.0) * 1000)

    def _minimum_m15_period_candles(
        self,
        required_start: datetime,
        required_end: datetime,
    ) -> int:
        continuous = max(
            0.0,
            (required_end - required_start).total_seconds()
            / timedelta(minutes=15).total_seconds(),
        )
        # Piso conservador para mercados 24/5, tolerando feriados e pausas.
        market_floor = math.floor(continuous * (5.0 / 7.0) * 0.85)
        return max(market_floor, MULTI_EA_M15_MINIMUM_CANDLES)

    def _m15_coverage(
        self,
        candles: list[object],
        *,
        required_start: datetime,
        required_end: datetime,
        minimum_candles: int,
    ) -> tuple[datetime | None, datetime | None, bool]:
        if not candles:
            return None, None, False
        first_candle = _utc_datetime(getattr(candles[0], "timestamp"))
        last_candle = _utc_datetime(getattr(candles[-1], "timestamp"))
        coverage_ok = bool(
            len(candles) >= minimum_candles
            and first_candle <= required_start
            and last_candle + timedelta(minutes=15) >= required_end
            and int(
                self._m15_gap_diagnostics(candles).get(
                    "large_internal_gaps", 0
                )
                or 0
            )
            == 0
        )
        return first_candle, last_candle, coverage_ok

    def _filter_m15_analysis_window(
        self,
        candles: list[object],
        *,
        required_start: datetime,
        required_end: datetime,
    ) -> list[object]:
        """Ancora o fit no CSV e impede que a cauda posterior desloque o warmup."""

        lower_bound = required_start - timedelta(minutes=15)
        return [
            candle
            for candle in candles
            if lower_bound
            <= _utc_datetime(getattr(candle, "timestamp"))
            <= required_end
        ]

    def _m15_gap_diagnostics(
        self,
        candles: list[object],
    ) -> dict[str, float | int | None]:
        """Sinaliza buracos internos muito maiores que fins de semana/feriados."""

        timestamps = sorted(
            {
                _utc_datetime(getattr(candle, "timestamp"))
                for candle in candles
            }
        )
        if len(timestamps) < 2:
            return {
                "maximum_internal_gap_hours": None,
                "large_internal_gaps": 0,
                "large_gap_threshold_days": MULTI_EA_M15_MAX_INTERNAL_GAP_DAYS,
            }
        threshold = timedelta(days=MULTI_EA_M15_MAX_INTERNAL_GAP_DAYS)
        gaps = [
            current - previous
            for previous, current in zip(timestamps, timestamps[1:])
        ]
        return {
            "maximum_internal_gap_hours": round(
                max(gaps).total_seconds() / 3600.0,
                6,
            ),
            "large_internal_gaps": sum(gap > threshold for gap in gaps),
            "large_gap_threshold_days": MULTI_EA_M15_MAX_INTERNAL_GAP_DAYS,
        }

    def _empty_report(self, status: str, message: str) -> dict[str, Any]:
        return {
            "schema_version": "multi_ea_trading_fit_v1",
            "name": "Multi EA Trading",
            "status": status,
            "classification": "AMOSTRA_EXPLORATORIA",
            "message": message,
            "research_only": True,
            "operational_eligible": False,
            "warnings": [
                "RESEARCH_ONLY",
                "AMOSTRA_EXPLORATORIA",
                "FUSO_NAO_INFORMADO",
            ],
            "sample": {},
            "behavior": {},
            "coverage": {},
            "split": {},
            "ranking_global": [],
            "ranking_by_market": {},
            "reported_profile": {},
            "methodology": {},
        }


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
