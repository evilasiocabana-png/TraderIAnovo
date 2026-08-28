"""Download isolated 100k-candle M5 datasets from the configured MT5 terminal."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import MetaTrader5 as mt5


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / ".traderia" / "research" / "historicosMercado"
DEFAULT_TERMINAL_PATH = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")
TIMEFRAME_NAME = "M5"
TIMEFRAME_SECONDS = 5 * 60
REQUESTED_ROWS = 100_000

MARKETS = (
    "AUDUSD",
    "EURJPY",
    "EURUSD",
    "GBPUSD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "USDJPY",
    "AUDCAD",
    "AUDJPY",
    "CADCHF",
    "EURNZD",
    "GBPAUD",
    "GBPCAD",
    "GBPNZD",
    "NZDCAD",
    "NZDJPY",
    "BTCUSD",
)

CSV_FIELDS = (
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "spread",
    "real_volume",
    "is_closed",
)


def _atomic_write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso_utc(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _csv_datetime(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _normalize_rates(rates: Any, now_utc: int) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for rate in rates:
        timestamp = int(rate["time"])
        normalized.append(
            {
                "datetime": _csv_datetime(timestamp),
                "open": f"{float(rate['open']):.8f}",
                "high": f"{float(rate['high']):.8f}",
                "low": f"{float(rate['low']):.8f}",
                "close": f"{float(rate['close']):.8f}",
                "volume": int(rate["tick_volume"]),
                "spread": int(rate["spread"]),
                "real_volume": int(rate["real_volume"]),
                "is_closed": int(timestamp + TIMEFRAME_SECONDS <= now_utc),
                "_timestamp": timestamp,
            }
        )
    normalized.sort(key=lambda item: int(item["_timestamp"]))
    return normalized


def _public_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {field: row[field] for field in CSV_FIELDS}
        for row in rows
    ]


def _validate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    timestamps = [int(row["_timestamp"]) for row in rows]
    invalid_ohlc = 0
    for row in rows:
        open_price = float(row["open"])
        high_price = float(row["high"])
        low_price = float(row["low"])
        close_price = float(row["close"])
        if high_price < max(open_price, close_price) or low_price > min(
            open_price, close_price
        ):
            invalid_ohlc += 1
    return {
        "timestamps_unique": len(timestamps) == len(set(timestamps)),
        "timestamps_ascending": timestamps == sorted(timestamps),
        "invalid_ohlc_rows": invalid_ohlc,
    }


def _fetch_rates(symbol: str, attempts: int = 5) -> list[Any]:
    last_count = 0
    rates: list[Any] = []
    for attempt in range(1, attempts + 1):
        recent = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50_000)
        older = mt5.copy_rates_from_pos(
            symbol,
            mt5.TIMEFRAME_M5,
            50_000,
            50_000,
        )
        by_timestamp: dict[int, Any] = {}
        for batch in (older, recent):
            if batch is None:
                continue
            for rate in batch:
                by_timestamp[int(rate["time"])] = rate
        rates = [by_timestamp[key] for key in sorted(by_timestamp)]
        last_count = len(rates)
        if last_count >= REQUESTED_ROWS:
            return rates[-REQUESTED_ROWS:]
        print(
            f"[{symbol}] tentativa {attempt}/{attempts}: "
            f"MT5 retornou {last_count:,} candles; aguardando historico...",
            flush=True,
        )
        time.sleep(2.0 * attempt)
    if not rates:
        raise RuntimeError(f"{symbol}: copy_rates_from_pos falhou: {mt5.last_error()}")
    raise RuntimeError(
        f"{symbol}: historico incompleto; recebidos {last_count:,} de "
        f"{REQUESTED_ROWS:,} candles."
    )


def _download_symbol(symbol: str, terminal_path: Path) -> dict[str, Any]:
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"{symbol}: symbol_select falhou: {mt5.last_error()}")

    rates = _fetch_rates(symbol)
    tick = mt5.symbol_info_tick(symbol)
    market_clock_utc = int(getattr(tick, "time", 0) or 0)
    if market_clock_utc <= 0:
        market_clock_utc = int(datetime.now(tz=timezone.utc).timestamp())
    raw_rows = _normalize_rates(rates, market_clock_utc)
    closed_rows = [row for row in raw_rows if bool(row["is_closed"])]
    validation = _validate_rows(raw_rows)
    if not all(
        (
            validation["timestamps_unique"],
            validation["timestamps_ascending"],
            validation["invalid_ohlc_rows"] == 0,
        )
    ):
        raise RuntimeError(f"{symbol}: validacao OHLC/timestamps falhou: {validation}")

    dataset_name = f"historico{symbol}"
    dataset_dir = OUTPUT_ROOT / dataset_name
    raw_path = dataset_dir / f"{dataset_name}_raw_100000.csv"
    replay_path = dataset_dir / f"{dataset_name}.csv"
    manifest_path = dataset_dir / f"{dataset_name}_manifest.json"

    _atomic_write_csv(raw_path, _public_rows(raw_rows))
    _atomic_write_csv(replay_path, _public_rows(closed_rows))

    terminal_info = mt5.terminal_info()
    account_info = mt5.account_info()
    manifest = {
        "dataset_id": dataset_name,
        "display_name": dataset_name,
        "source": "MetaTrader5.copy_rates_from_pos",
        "symbol": symbol,
        "timeframe": TIMEFRAME_NAME,
        "timezone": "UTC",
        "terminal_path": str(terminal_path),
        "terminal_max_bars": int(getattr(terminal_info, "maxbars", 0) or 0),
        "server": str(getattr(account_info, "server", "") or ""),
        "account": int(getattr(account_info, "login", 0) or 0),
        "downloaded_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "market_clock_utc": _iso_utc(market_clock_utc),
        "raw": {
            "path": str(raw_path.resolve()),
            "rows": len(raw_rows),
            "first_candle_utc": _iso_utc(int(raw_rows[0]["_timestamp"])),
            "last_candle_utc": _iso_utc(int(raw_rows[-1]["_timestamp"])),
            "includes_current_forming_candle": any(
                not bool(row["is_closed"]) for row in raw_rows
            ),
            "sha256": _sha256(raw_path),
            "size_bytes": raw_path.stat().st_size,
        },
        "replay": {
            "path": str(replay_path.resolve()),
            "rows": len(closed_rows),
            "first_candle_utc": _iso_utc(int(closed_rows[0]["_timestamp"])),
            "last_candle_utc": _iso_utc(int(closed_rows[-1]["_timestamp"])),
            "includes_current_forming_candle": False,
            "sha256": _sha256(replay_path),
            "size_bytes": replay_path.stat().st_size,
        },
        "validation": validation,
        "integration_status": "download_only_not_registered_in_replay",
    }
    _atomic_write_json(manifest_path, manifest)
    print(
        f"[{symbol}] concluido: bruto={len(raw_rows):,}; "
        f"fechado={len(closed_rows):,}; arquivo={replay_path}",
        flush=True,
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--terminal-path",
        type=Path,
        default=DEFAULT_TERMINAL_PATH,
    )
    parser.add_argument("symbols", nargs="*", default=list(MARKETS))
    args = parser.parse_args()
    symbols = tuple(dict.fromkeys(str(item).upper() for item in args.symbols))
    terminal_path = args.terminal_path.resolve()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize(path=str(terminal_path)):
        raise RuntimeError(f"MT5 initialize falhou: {mt5.last_error()}")

    completed: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    try:
        account_info = mt5.account_info()
        if account_info is None:
            raise RuntimeError(f"MT5 sem conta conectada: {mt5.last_error()}")
        print(
            f"MT5 conectado: conta={account_info.login}; servidor={account_info.server}; "
            f"ativos={len(symbols)}",
            flush=True,
        )
        for index, symbol in enumerate(symbols, start=1):
            print(f"[{index}/{len(symbols)}] baixando {symbol}/M5...", flush=True)
            try:
                completed.append(_download_symbol(symbol, terminal_path))
            except Exception as exc:  # preserve remaining independent downloads
                failed.append({"symbol": symbol, "error": str(exc)})
                print(f"[{symbol}] FALHOU: {exc}", flush=True)
    finally:
        mt5.shutdown()

    summary = {
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "timeframe": TIMEFRAME_NAME,
        "requested_rows_per_symbol": REQUESTED_ROWS,
        "requested_symbols": list(symbols),
        "completed_symbols": [item["symbol"] for item in completed],
        "failed": failed,
        "manifests": [
            str(
                (
                    OUTPUT_ROOT
                    / str(item["dataset_id"])
                    / f"{item['dataset_id']}_manifest.json"
                ).resolve()
            )
            for item in completed
        ],
    }
    _atomic_write_json(OUTPUT_ROOT / "historicosM5_100000_resumo.json", summary)
    print(
        f"Resumo: concluidos={len(completed)}; falhas={len(failed)}; "
        f"destino={OUTPUT_ROOT}",
        flush=True,
    )
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
