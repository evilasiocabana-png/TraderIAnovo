"""Orquestracao sob demanda do sublaboratorio Multi EA Trading."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from infrastructure.research.multi_ea_local_data_adapter import (
    MultiEALocalDataAdapter,
)
from research.multi_ea_trading_lab import MultiEATradingLabEngine


MULTI_EA_TRADING_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1")
MULTI_EA_TRADING_TIMEFRAME_VALUES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 16385,
}


@dataclass
class MultiEATradingLabUseCase:
    """Coordena CSV, caches locais e motor puro sem tocar execucao."""

    adapter: MultiEALocalDataAdapter = field(default_factory=MultiEALocalDataAdapter)
    engine: MultiEATradingLabEngine = field(default_factory=MultiEATradingLabEngine)
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

        candles = []
        series_loaded: list[dict[str, Any]] = []
        for symbol in sorted({position.symbol for position in positions}):
            for timeframe in self.timeframes:
                series = self.adapter.load_candles(
                    symbol,
                    timeframe,
                    limit=self.candle_count,
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
        result.update(
            {
                "name": "Multi EA Trading",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "research_only": True,
                "operational_eligible": False,
                "candle_limit_per_series": self.candle_count,
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
        self.adapter.write_fit_result(result)
        return result

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
