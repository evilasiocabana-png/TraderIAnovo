"""Persistencia local isolada para a pesquisa Multi EA Trading.

O adapter mantem a amostra fora do banco operacional do TraderIA. O banco
operacional e aberto exclusivamente em modo read-only; candles adicionais,
o CSV validado e o resultado do fit vivem em ``.traderia/research``.
"""

from __future__ import annotations

import csv
from contextlib import closing
from dataclasses import asdict, dataclass, is_dataclass, replace as dataclass_replace
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from typing import Any, Callable, Iterable, Mapping

from research.multi_ea_trading_lab import MultiEACandle, MultiEATradePosition


DEFAULT_RUNTIME_DIRECTORY = (
    Path(".traderia") / "research" / "multi_ea_trading"
)
DEFAULT_OPERATIONAL_DATABASE = Path(".traderia") / "traderia_mt5_history.sqlite"
HISTORY_SCHEMA_VERSION = "multi_ea_history_v1"
CSV_COLUMNS = (
    "TIME",
    "TYPE",
    "VOLUME",
    "SYMBOL",
    "PRICE",
    "VOLUME",
    "TIME",
    "PRICE",
    "COMMISSION",
    "SWAP",
    "PROFIT",
)
SYMBOL_ALIASES = {"GOLD": "XAUUSD"}


@dataclass(frozen=True)
class MultiEABalanceEntry:
    """Lancamento de saldo encontrado e excluido da lista de trades."""

    source_row: int
    timestamp: datetime
    amount: float


@dataclass(frozen=True)
class MultiEAImportIssue:
    """Linha ignorada durante a leitura posicional do CSV."""

    source_row: int
    reason: str
    raw_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class MultiEAImportReport:
    """Resultado auditavel da importacao das posicoes Multi EA."""

    positions: tuple[MultiEATradePosition, ...]
    balance_entries: tuple[MultiEABalanceEntry, ...]
    issues: tuple[MultiEAImportIssue, ...]
    source_path: str
    source_sha256: str
    total_rows: int
    trade_rows: int
    balance_rows: int
    ignored_rows: int
    persisted_path: str = ""


def canonicalize_multi_ea_symbol(symbol: object) -> str:
    """Normaliza o simbolo sem perder o valor original no DTO de origem."""

    normalized = str(symbol or "").strip().upper()
    if not normalized:
        raise ValueError("Simbolo vazio.")
    return SYMBOL_ALIASES.get(normalized, normalized)


class MultiEALocalDataAdapter:
    """Porta local para posicoes, candles e fit da pesquisa Multi EA."""

    def __init__(
        self,
        runtime_directory: str | Path = DEFAULT_RUNTIME_DIRECTORY,
        operational_database_path: str | Path = DEFAULT_OPERATIONAL_DATABASE,
    ) -> None:
        self.runtime_directory = Path(runtime_directory)
        self.operational_database_path = Path(operational_database_path)

    @property
    def history_database_path(self) -> Path:
        return self.runtime_directory / "history.sqlite"

    @property
    def positions_path(self) -> Path:
        return self.runtime_directory / "positions.csv"

    @property
    def fit_result_path(self) -> Path:
        return self.runtime_directory / "fit_v1.json"

    def parse_positions_csv(
        self,
        source_path: str | Path,
        *,
        strict: bool = False,
    ) -> MultiEAImportReport:
        """Le o CSV por indice, preservando os tres cabecalhos duplicados."""

        path = Path(source_path)
        raw = path.read_bytes()
        text = _decode_csv(raw)
        reader = csv.reader(io.StringIO(text), delimiter=";")
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("CSV Multi EA vazio.") from exc
        _validate_csv_header(header)

        positions: list[MultiEATradePosition] = []
        balances: list[MultiEABalanceEntry] = []
        issues: list[MultiEAImportIssue] = []
        total_rows = 0
        for source_row, values in enumerate(reader, start=2):
            if not values or not any(str(value).strip() for value in values):
                continue
            total_rows += 1
            row_type = str(values[1] if len(values) > 1 else "").strip().upper()
            if row_type == "BALANCE":
                try:
                    balances.append(_balance_from_csv_row(values, source_row))
                except (TypeError, ValueError) as exc:
                    issues.append(
                        MultiEAImportIssue(
                            source_row=source_row,
                            reason=f"Balance invalido: {exc}",
                            raw_values=tuple(values),
                        )
                    )
                continue
            if row_type not in {"BUY", "SELL"}:
                issues.append(
                    MultiEAImportIssue(
                        source_row=source_row,
                        reason=f"Tipo de linha nao suportado: {row_type or 'VAZIO'}.",
                        raw_values=tuple(values),
                    )
                )
                continue
            try:
                positions.append(_position_from_csv_row(values, source_row))
            except (IndexError, TypeError, ValueError) as exc:
                issues.append(
                    MultiEAImportIssue(
                        source_row=source_row,
                        reason=f"Trade invalido: {exc}",
                        raw_values=tuple(values),
                    )
                )

        if strict and issues:
            details = "; ".join(
                f"linha {issue.source_row}: {issue.reason}" for issue in issues[:5]
            )
            raise ValueError(f"CSV Multi EA possui linhas invalidas: {details}")
        return MultiEAImportReport(
            positions=tuple(positions),
            balance_entries=tuple(balances),
            issues=tuple(issues),
            source_path=str(path.resolve()),
            source_sha256=hashlib.sha256(raw).hexdigest(),
            total_rows=total_rows,
            trade_rows=len(positions),
            balance_rows=len(balances),
            ignored_rows=len(issues),
        )

    def import_positions_csv(
        self,
        source_path: str | Path,
        *,
        strict: bool = True,
    ) -> MultiEAImportReport:
        """Valida e persiste somente o ``positions.csv`` canonico da pesquisa."""

        report = self.parse_positions_csv(source_path, strict=strict)
        source_bytes = Path(source_path).read_bytes()
        _atomic_write_bytes(self.positions_path, source_bytes)
        imported_at = _utc_now_text()

        def update_metadata(connection: sqlite3.Connection) -> None:
            _upsert_metadata(
                connection,
                {
                    "schema_version": HISTORY_SCHEMA_VERSION,
                    "positions_import": {
                        "source_name": Path(source_path).name,
                        "source_sha256": report.source_sha256,
                        "total_rows": report.total_rows,
                        "trade_rows": report.trade_rows,
                        "balance_rows": report.balance_rows,
                        "ignored_rows": report.ignored_rows,
                        "imported_at": imported_at,
                    },
                },
            )

        self._mutate_history_database(update_metadata)
        return dataclass_replace(
            report,
            persisted_path=str(self.positions_path.resolve()),
        )

    def load_positions(self, *, strict: bool = True) -> list[MultiEATradePosition]:
        """Reabre as posicoes persistidas sem acessar o arquivo original."""

        if not self.positions_path.exists():
            return []
        return list(
            self.parse_positions_csv(self.positions_path, strict=strict).positions
        )

    def store_provider_candles(
        self,
        batch: Mapping[str, Mapping[str, Mapping[str, Any]]],
        *,
        requested_count: int = 5000,
        source: str = "MT5_READ_ONLY",
    ) -> dict[str, Any]:
        """Persiste o lote retornado por ``provider.get_research_batch``.

        O contrato do provider e ``{TF: {simbolo: {candles: [...]}}}``. Os
        campos ``exists``, ``selected`` e ``microstructure`` sao apenas
        diagnosticos do provider e, por isso, nao entram no banco historico.
        """

        count_limit = _positive_limit(requested_count)
        if not isinstance(batch, Mapping):
            raise TypeError("Batch do provider deve ser um mapeamento por timeframe.")
        normalized: list[MultiEACandle] = []
        received_by_timeframe: dict[str, int] = {}
        raw_received_by_timeframe: dict[str, int] = {}
        for raw_timeframe, raw_symbols in batch.items():
            timeframe = str(raw_timeframe or "").strip().upper()
            if not timeframe:
                raise ValueError("Timeframe vazio no batch do provider.")
            if not isinstance(raw_symbols, Mapping):
                raise TypeError(
                    f"Conteudo do timeframe {timeframe} deve ser um mapeamento."
                )
            timeframe_count = 0
            timeframe_keys: set[tuple[str, str, str]] = set()
            for raw_symbol, raw_payload in raw_symbols.items():
                source_symbol = str(raw_symbol or "").strip()
                if not source_symbol:
                    raise ValueError(
                        f"Simbolo vazio no batch do provider ({timeframe})."
                    )
                if not isinstance(raw_payload, Mapping):
                    raise TypeError(
                        f"Payload de {source_symbol}/{timeframe} deve ser um mapeamento."
                    )
                raw_candles = raw_payload.get("candles", ())
                if raw_candles is None:
                    raw_candles = ()
                if isinstance(raw_candles, (str, bytes, Mapping)):
                    raise TypeError(
                        f"Candles de {source_symbol}/{timeframe} devem ser iteraveis."
                    )
                for candle in list(raw_candles)[-count_limit:]:
                    normalized_candle = _normalize_provider_candle(
                        candle,
                        fallback_symbol=source_symbol,
                        fallback_timeframe=timeframe,
                    )
                    normalized.append(normalized_candle)
                    timeframe_keys.add(_candle_identity(normalized_candle))
                    timeframe_count += 1
            raw_received_by_timeframe[timeframe] = timeframe_count
            received_by_timeframe[timeframe] = len(timeframe_keys)

        stored_count = self.store_candles(normalized, source=source)
        return {
            "received_by_timeframe": received_by_timeframe,
            "raw_received_by_timeframe": raw_received_by_timeframe,
            "total_candles": stored_count,
            "database_path": str(self.history_database_path.resolve()),
            "status": "OK" if stored_count else "EMPTY",
        }

    def store_candles(
        self,
        candles: Iterable[MultiEACandle],
        *,
        source: str = "LOCAL_RESEARCH",
    ) -> int:
        """Faz upsert atomico de candles canonicos no banco da pesquisa."""

        unique: dict[tuple[str, str, str], MultiEACandle] = {}
        for item in candles:
            candle = _normalize_provider_candle(
                item,
                fallback_symbol=getattr(item, "symbol", ""),
                fallback_timeframe=getattr(item, "timeframe", ""),
            )
            key = (
                candle.symbol,
                candle.timeframe,
                _datetime_text(candle.timestamp),
            )
            unique[key] = candle
        if not unique:
            return 0
        imported_at = _utc_now_text()

        def persist(connection: sqlite3.Connection) -> None:
            connection.executemany(
                """
                INSERT INTO candles (
                    symbol, source_symbol, timeframe, timestamp,
                    open, high, low, close, volume, source, imported_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, timeframe, timestamp) DO UPDATE SET
                    source_symbol = excluded.source_symbol,
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume,
                    source = excluded.source,
                    imported_at = excluded.imported_at
                """,
                [
                    (
                        candle.symbol,
                        candle.source_symbol or candle.symbol,
                        candle.timeframe,
                        _datetime_text(candle.timestamp),
                        candle.open,
                        candle.high,
                        candle.low,
                        candle.close,
                        candle.volume,
                        str(source or "LOCAL_RESEARCH"),
                        imported_at,
                    )
                    for candle in unique.values()
                ],
            )
            _upsert_metadata(
                connection,
                {
                    "schema_version": HISTORY_SCHEMA_VERSION,
                    "last_candle_import": {
                        "source": str(source or "LOCAL_RESEARCH"),
                        "count": len(unique),
                        "imported_at": imported_at,
                    },
                },
            )

        self._mutate_history_database(persist)
        return len(unique)

    def load_operational_candles(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int | None = 5000,
    ) -> list[MultiEACandle]:
        """Le o banco operacional sem criar journal, WAL ou qualquer escrita."""

        database = self.operational_database_path
        if not database.exists():
            return []
        candidates = _symbol_candidates(symbol)
        placeholders = ",".join("?" for _ in candidates)
        parameters: list[object] = [*candidates, str(timeframe).upper()]
        inner_limit = ""
        if limit is not None:
            inner_limit = " LIMIT ?"
            parameters.append(_positive_limit(limit))
        query = f"""
            SELECT pair, timeframe, candle_time, open, high, low, close, volume
            FROM (
                SELECT pair, timeframe, candle_time, open, high, low, close, volume
                FROM mt5_history_candles
                WHERE pair IN ({placeholders}) AND timeframe = ?
                ORDER BY candle_time DESC
                {inner_limit}
            )
            ORDER BY candle_time ASC
        """
        rows = _read_only_rows(
            database,
            table_name="mt5_history_candles",
            query=query,
            parameters=tuple(parameters),
        )
        return [
            MultiEACandle(
                symbol=canonicalize_multi_ea_symbol(row[0]),
                source_symbol=str(row[0]),
                timeframe=str(row[1]).upper(),
                timestamp=_parse_datetime(row[2]),
                open=float(row[3]),
                high=float(row[4]),
                low=float(row[5]),
                close=float(row[6]),
                volume=float(row[7] or 0.0),
            )
            for row in rows
        ]

    def load_research_candles(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int | None = 5000,
    ) -> list[MultiEACandle]:
        """Le candles adicionais do banco isolado da pesquisa."""

        database = self.history_database_path
        if not database.exists():
            return []
        parameters: list[object] = [
            canonicalize_multi_ea_symbol(symbol),
            str(timeframe).upper(),
        ]
        inner_limit = ""
        if limit is not None:
            inner_limit = " LIMIT ?"
            parameters.append(_positive_limit(limit))
        query = f"""
            SELECT symbol, source_symbol, timeframe, timestamp,
                   open, high, low, close, volume
            FROM (
                SELECT symbol, source_symbol, timeframe, timestamp,
                       open, high, low, close, volume
                FROM candles
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                {inner_limit}
            )
            ORDER BY timestamp ASC
        """
        rows = _read_only_rows(
            database,
            table_name="candles",
            query=query,
            parameters=tuple(parameters),
        )
        return [
            MultiEACandle(
                symbol=str(row[0]),
                source_symbol=str(row[1] or row[0]),
                timeframe=str(row[2]).upper(),
                timestamp=_parse_datetime(row[3]),
                open=float(row[4]),
                high=float(row[5]),
                low=float(row[6]),
                close=float(row[7]),
                volume=float(row[8] or 0.0),
            )
            for row in rows
        ]

    def load_candles(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int | None = 5000,
    ) -> list[MultiEACandle]:
        """Combina banco operacional e banco da pesquisa; o separado prevalece."""

        combined: dict[tuple[str, str, str], MultiEACandle] = {}
        for candle in self.load_operational_candles(
            symbol,
            timeframe,
            limit=limit,
        ):
            combined[_candle_identity(candle)] = candle
        for candle in self.load_research_candles(
            symbol,
            timeframe,
            limit=limit,
        ):
            combined[_candle_identity(candle)] = candle
        ordered = sorted(combined.values(), key=lambda item: _datetime_sort_key(item.timestamp))
        if limit is not None:
            ordered = ordered[-_positive_limit(limit) :]
        return ordered

    def get_history_metadata(self) -> dict[str, Any]:
        """Retorna metadata do banco separado sem alterar o arquivo."""

        database = self.history_database_path
        if not database.exists():
            return {}
        rows = _read_only_rows(
            database,
            table_name="metadata",
            query="SELECT key, value_json FROM metadata ORDER BY key",
            parameters=(),
        )
        result: dict[str, Any] = {}
        for key, value in rows:
            try:
                result[str(key)] = json.loads(str(value))
            except json.JSONDecodeError:
                result[str(key)] = str(value)
        return result

    def write_fit_result(self, payload: Mapping[str, Any]) -> Path:
        """Grava o unico artefato de fit autorizado, com substituicao atomica."""

        encoded = json.dumps(
            _json_compatible(dict(payload)),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
        _atomic_write_bytes(self.fit_result_path, encoded)
        return self.fit_result_path

    def read_fit_result(self) -> dict[str, Any]:
        """Le ``fit_v1.json``; ausencia e representada por dicionario vazio."""

        if not self.fit_result_path.exists():
            return {}
        try:
            payload = json.loads(self.fit_result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("fit_v1.json invalido.") from exc
        if not isinstance(payload, dict):
            raise ValueError("fit_v1.json deve conter um objeto JSON.")
        return payload

    def _mutate_history_database(
        self,
        mutation: Callable[[sqlite3.Connection], None],
    ) -> None:
        """Aplica uma mutacao em copia temporaria e troca o DB atomicamente."""

        target = self.history_database_path
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            if target.exists():
                shutil.copyfile(target, temporary)
            with closing(sqlite3.connect(temporary, timeout=10.0)) as connection:
                connection.execute("PRAGMA journal_mode=DELETE")
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("PRAGMA temp_store=MEMORY")
                _create_history_schema(connection)
                mutation(connection)
                connection.commit()
            _fsync_file(temporary)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()


def _create_history_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS candles (
            symbol TEXT NOT NULL,
            source_symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL DEFAULT 0,
            source TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            PRIMARY KEY (symbol, timeframe, timestamp),
            CHECK (high >= low)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_candles_market "
        "ON candles(symbol, timeframe, timestamp)"
    )
    connection.execute("PRAGMA user_version=1")


def _upsert_metadata(
    connection: sqlite3.Connection,
    values: Mapping[str, Any],
) -> None:
    updated_at = _utc_now_text()
    connection.executemany(
        """
        INSERT INTO metadata (key, value_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value_json = excluded.value_json,
            updated_at = excluded.updated_at
        """,
        [
            (
                str(key),
                json.dumps(
                    _json_compatible(value),
                    ensure_ascii=False,
                    sort_keys=True,
                    allow_nan=False,
                ),
                updated_at,
            )
            for key, value in values.items()
        ],
    )


def _position_from_csv_row(
    values: list[str],
    source_row: int,
) -> MultiEATradePosition:
    if len(values) < len(CSV_COLUMNS):
        raise ValueError(f"esperadas 11 colunas; recebidas {len(values)}")
    source_symbol = str(values[3]).strip()
    symbol = canonicalize_multi_ea_symbol(source_symbol)
    direction = str(values[1]).strip().upper()
    open_time = _parse_datetime(values[0], csv_format=True)
    close_time = _parse_datetime(values[6], csv_format=True)
    volume = _required_float(values[2], "volume")
    close_volume = _optional_float(values[5])
    if close_volume is not None and not math.isclose(
        volume,
        close_volume,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise ValueError("volume de abertura difere do fechamento")
    open_price = _required_float(values[4], "preco de abertura")
    close_price = _required_float(values[7], "preco de fechamento")
    commission = _optional_float(values[8])
    swap = _optional_float(values[9])
    profit = _optional_float(values[10]) or 0.0
    identity = "|".join(
        (
            str(source_row),
            source_symbol,
            direction,
            _datetime_text(open_time),
            format(open_price, ".12g"),
            _datetime_text(close_time),
            format(close_price, ".12g"),
            format(volume, ".12g"),
        )
    )
    return MultiEATradePosition(
        source_symbol=source_symbol,
        symbol=symbol,
        direction=direction,
        volume=volume,
        open_time=open_time,
        open_price=open_price,
        close_time=close_time,
        close_price=close_price,
        commission=commission,
        swap=swap,
        profit=profit,
        source_row=source_row,
        position_id=hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24],
    )


def _balance_from_csv_row(
    values: list[str],
    source_row: int,
) -> MultiEABalanceEntry:
    if len(values) < len(CSV_COLUMNS):
        raise ValueError(f"esperadas 11 colunas; recebidas {len(values)}")
    return MultiEABalanceEntry(
        source_row=source_row,
        timestamp=_parse_datetime(values[0], csv_format=True),
        amount=_required_float(values[10], "valor do Balance"),
    )


def _normalize_provider_candle(
    candle: object,
    *,
    fallback_symbol: object,
    fallback_timeframe: object,
) -> MultiEACandle:
    source_symbol = str(
        _value_from(candle, "source_symbol", default="")
        or _value_from(candle, "symbol", "pair", default=fallback_symbol)
        or fallback_symbol
    ).strip()
    symbol = canonicalize_multi_ea_symbol(
        _value_from(candle, "symbol", "pair", default=fallback_symbol)
        or fallback_symbol
    )
    timeframe = str(
        _value_from(candle, "timeframe", default=fallback_timeframe)
        or fallback_timeframe
    ).strip().upper()
    if not timeframe:
        raise ValueError("Timeframe vazio.")
    timestamp = _parse_datetime(
        _value_from(candle, "timestamp", "candle_time", "data", "time")
    )
    open_price = _finite_float(
        _value_from(candle, "open", "abertura"),
        "open",
    )
    high = _finite_float(_value_from(candle, "high", "maxima"), "high")
    low = _finite_float(_value_from(candle, "low", "minima"), "low")
    close = _finite_float(
        _value_from(candle, "close", "fechamento"),
        "close",
    )
    volume = _finite_float(
        _value_from(candle, "volume", "tick_volume", "real_volume", default=0.0),
        "volume",
    )
    if high < max(open_price, low, close) or low > min(open_price, high, close):
        raise ValueError("OHLC inconsistente.")
    if volume < 0.0:
        raise ValueError("Volume negativo.")
    return MultiEACandle(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        source_symbol=source_symbol or symbol,
    )


def _value_from(
    item: object,
    *names: str,
    default: object = None,
) -> object:
    if isinstance(item, Mapping):
        lowered = {str(key).lower(): value for key, value in item.items()}
        for name in names:
            if name.lower() in lowered:
                return lowered[name.lower()]
    for name in names:
        if hasattr(item, name):
            return getattr(item, name)
    if default is not None:
        return default
    raise ValueError(f"Campo ausente: {'/'.join(names)}")


def _read_only_rows(
    database_path: Path,
    *,
    table_name: str,
    query: str,
    parameters: tuple[object, ...],
) -> list[tuple[Any, ...]]:
    uri = f"{database_path.resolve().as_uri()}?mode=ro"
    with closing(
        sqlite3.connect(uri, uri=True, timeout=10.0)
    ) as connection:
        connection.execute("PRAGMA query_only=ON")
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        if exists is None:
            return []
        return list(connection.execute(query, parameters).fetchall())


def _validate_csv_header(header: list[str]) -> None:
    normalized = tuple(str(value).strip().upper() for value in header[:11])
    if len(header) < len(CSV_COLUMNS) or normalized != CSV_COLUMNS:
        raise ValueError(
            "Cabecalho Multi EA inesperado; a leitura posicional exige as "
            "11 colunas Time..Profit na ordem original."
        )


def _decode_csv(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def _required_float(value: object, label: str) -> float:
    parsed = _optional_float(value)
    if parsed is None:
        raise ValueError(f"{label} ausente")
    return parsed


def _optional_float(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    parsed = float(text)
    if not math.isfinite(parsed):
        raise ValueError(f"Numero nao finito: {value}")
    return parsed


def _finite_float(value: object, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} invalido: {value}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{label} nao finito.")
    return parsed


def _parse_datetime(value: object, *, csv_format: bool = False) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    text = str(value or "").strip()
    if not text:
        raise ValueError("Timestamp vazio.")
    if csv_format:
        return datetime.strptime(text, "%Y.%m.%d %H:%M:%S")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        for pattern in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, pattern)
            except ValueError:
                continue
    raise ValueError(f"Timestamp invalido: {text}")


def _datetime_text(value: datetime) -> str:
    return value.isoformat()


def _datetime_sort_key(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _candle_identity(candle: MultiEACandle) -> tuple[str, str, str]:
    timestamp = _datetime_sort_key(candle.timestamp).isoformat()
    return candle.symbol, candle.timeframe, timestamp


def _symbol_candidates(symbol: str) -> tuple[str, ...]:
    canonical = canonicalize_multi_ea_symbol(symbol)
    values = [canonical]
    if canonical == "XAUUSD":
        values.append("GOLD")
    return tuple(dict.fromkeys(values))


def _positive_limit(limit: object) -> int:
    parsed = int(limit)
    if parsed <= 0:
        raise ValueError("Limit deve ser positivo.")
    return parsed


def _atomic_write_bytes(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() == content:
        return
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _fsync_file(path: Path) -> None:
    with path.open("rb+") as handle:
        os.fsync(handle.fileno())


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_compatible(value: Any) -> Any:
    if is_dataclass(value):
        return _json_compatible(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_compatible(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
