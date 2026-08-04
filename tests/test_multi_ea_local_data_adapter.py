from __future__ import annotations

import csv
from contextlib import closing
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest

from infrastructure.research.multi_ea_local_data_adapter import (
    MultiEALocalDataAdapter,
    canonicalize_multi_ea_symbol,
)
from research.multi_ea_trading_lab import MultiEACandle, MultiEATradePosition


CSV_HEADER = [
    "Time",
    "Type",
    "Volume",
    "Symbol",
    "Price",
    "Volume",
    "Time",
    "Price",
    "Commission",
    "Swap",
    "Profit",
]


class MultiEALocalDataAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.runtime_directory = self.root / "runtime"
        self.operational_database = self.root / "operational.sqlite"
        self.adapter = MultiEALocalDataAdapter(
            runtime_directory=self.runtime_directory,
            operational_database_path=self.operational_database,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_alias_btcusd_preserva_bitcoin_como_simbolo_do_extrato(self) -> None:
        self.assertEqual(canonicalize_multi_ea_symbol("BTCUSD"), "BITCOIN")
        self.assertEqual(canonicalize_multi_ea_symbol("BITCOIN"), "BITCOIN")

    def test_parseia_csv_posicional_com_headers_duplicados_e_ignora_balance(
        self,
    ) -> None:
        source = self._write_positions_csv(
            [
                [
                    "2025.01.02 10:00:00",
                    "Buy",
                    "0.10",
                    "GOLD",
                    "2640.50",
                    "0.10",
                    "2025.01.02 11:00:00",
                    "2645.50",
                    "-1.25",
                    "",
                    "50.00",
                ],
                [
                    "2025.01.02 12:00:00",
                    "Balance",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "10000.00",
                ],
            ]
        )

        report = self.adapter.parse_positions_csv(source)

        self.assertEqual(report.total_rows, 2)
        self.assertEqual(report.trade_rows, 1)
        self.assertEqual(report.balance_rows, 1)
        self.assertEqual(report.ignored_rows, 0)
        self.assertEqual(report.issues, ())
        self.assertEqual(len(report.balance_entries), 1)
        self.assertEqual(report.balance_entries[0].amount, 10000.0)
        position = report.positions[0]
        self.assertIsInstance(position, MultiEATradePosition)
        self.assertEqual(position.source_symbol, "GOLD")
        self.assertEqual(position.symbol, "XAUUSD")
        self.assertEqual(position.direction, "BUY")
        self.assertEqual(position.source_row, 2)
        self.assertEqual(position.commission, -1.25)
        self.assertIsNone(position.swap)
        self.assertEqual(len(position.position_id), 24)

    def test_importa_csv_atomicamente_e_nao_persiste_balance_como_trade(self) -> None:
        source = self._write_positions_csv(
            [
                [
                    "2025.01.02 10:00:00",
                    "Sell",
                    "0.20",
                    "EURUSD",
                    "1.0400",
                    "0.20",
                    "2025.01.02 11:00:00",
                    "1.0300",
                    "-2.00",
                    "0.50",
                    "198.00",
                ],
                [
                    "2025.01.02 12:00:00",
                    "Balance",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "10000.00",
                ],
            ]
        )
        original_bytes = source.read_bytes()

        report = self.adapter.import_positions_csv(source)

        self.assertEqual(Path(report.persisted_path), self.adapter.positions_path.resolve())
        self.assertEqual(self.adapter.positions_path.read_bytes(), original_bytes)
        self.assertTrue(self.adapter.history_database_path.exists())
        loaded = self.adapter.load_positions()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].direction, "SELL")
        metadata = self.adapter.get_history_metadata()["positions_import"]
        self.assertEqual(metadata["trade_rows"], 1)
        self.assertEqual(metadata["balance_rows"], 1)
        self.assertEqual(
            metadata["source_sha256"],
            hashlib.sha256(original_bytes).hexdigest(),
        )
        self.assertEqual(
            {item.name for item in self.runtime_directory.iterdir()},
            {"history.sqlite", "positions.csv"},
        )
        with closing(
            sqlite3.connect(self.adapter.history_database_path)
        ) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertEqual(tables, {"candles", "metadata"})

    def test_store_provider_batch_combina_bancos_sem_alterar_operacional(
        self,
    ) -> None:
        self._create_operational_database(
            [
                (
                    "XAUUSD",
                    "M1",
                    "2025-01-01T10:00:00",
                    2640.0,
                    2642.0,
                    2639.0,
                    2641.0,
                    100.0,
                ),
                (
                    "XAUUSD",
                    "M1",
                    "2025-01-01T10:01:00",
                    2641.0,
                    2643.0,
                    2640.0,
                    2642.0,
                    110.0,
                ),
            ]
        )
        operational_hash = _file_hash(self.operational_database)
        operational_mtime = self.operational_database.stat().st_mtime_ns
        batch = {
            "m1": {
                "GOLD": {
                    "exists": True,
                    "selected": True,
                    "candles": [
                        SimpleNamespace(
                            data="2025-01-01T10:01:00",
                            abertura=2641.0,
                            maxima=2644.0,
                            minima=2640.0,
                            fechamento=2643.5,
                            volume=120,
                        ),
                        {
                            "timestamp": "2025-01-01T10:02:00",
                            "open": 2643.5,
                            "high": 2645.0,
                            "low": 2643.0,
                            "close": 2644.0,
                            "tick_volume": 130,
                        },
                        {
                            "timestamp": "2025-01-01T10:02:00",
                            "open": 2643.5,
                            "high": 2645.0,
                            "low": 2643.0,
                            "close": 2644.0,
                            "tick_volume": 130,
                        },
                    ],
                    "microstructure": {"spread_points": 20},
                }
            },
            "h1": {
                "EURUSD": {
                    "exists": True,
                    "selected": True,
                    "candles": [
                        {
                            "time": "2025-01-01T10:00:00",
                            "open": 1.04,
                            "high": 1.05,
                            "low": 1.03,
                            "close": 1.045,
                            "real_volume": 25,
                        }
                    ],
                    "microstructure": {},
                }
            },
        }

        summary = self.adapter.store_provider_candles(
            batch,
            requested_count=5000,
            source="MT5_READ_ONLY",
        )
        candles = self.adapter.load_candles("GOLD", "M1", limit=5000)

        self.assertEqual(
            summary,
            {
                "received_by_timeframe": {"M1": 2, "H1": 1},
                "raw_received_by_timeframe": {"M1": 3, "H1": 1},
                "total_candles": 3,
                "database_path": str(self.adapter.history_database_path.resolve()),
                "status": "OK",
            },
        )
        json.dumps(summary, allow_nan=False)
        self.assertEqual(len(candles), 3)
        self.assertTrue(all(isinstance(item, MultiEACandle) for item in candles))
        self.assertEqual(
            [item.timestamp.minute for item in candles],
            [0, 1, 2],
        )
        self.assertEqual(candles[1].close, 2643.5)
        self.assertEqual(candles[1].symbol, "XAUUSD")
        self.assertEqual(candles[1].source_symbol, "GOLD")
        self.assertEqual(_file_hash(self.operational_database), operational_hash)
        self.assertEqual(
            self.operational_database.stat().st_mtime_ns,
            operational_mtime,
        )
        with closing(
            sqlite3.connect(self.adapter.history_database_path)
        ) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertEqual(tables, {"candles", "metadata"})

    def test_le_snapshot_atual_do_wal_em_modo_read_only(self) -> None:
        writer = sqlite3.connect(self.operational_database)
        try:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            self._create_operational_schema(writer)
            writer.commit()
            writer.execute(
                """
                INSERT INTO mt5_history_candles (
                    pair, timeframe, candle_time, open, high, low, close, volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "EURUSD",
                    "M5",
                    "2025-01-01T10:00:00",
                    1.04,
                    1.05,
                    1.03,
                    1.045,
                    90.0,
                ),
            )
            writer.commit()
            wal_path = Path(f"{self.operational_database}-wal")
            main_hash = _file_hash(self.operational_database)
            wal_hash = _file_hash(wal_path)

            candles = self.adapter.load_operational_candles("EURUSD", "M5")

            self.assertEqual(len(candles), 1)
            self.assertEqual(candles[0].close, 1.045)
            self.assertEqual(_file_hash(self.operational_database), main_hash)
            self.assertEqual(_file_hash(wal_path), wal_hash)
        finally:
            writer.close()

    def test_fit_json_e_mutacao_sqlite_sao_atomicos(self) -> None:
        self.assertEqual(self.adapter.read_fit_result(), {})
        fit_path = self.adapter.write_fit_result(
            {
                "score": float("nan"),
                "generated_at": datetime(2025, 1, 2, 12, 0, 0),
                "input": Path("positions.csv"),
            }
        )
        self.assertEqual(
            self.adapter.read_fit_result(),
            {
                "generated_at": "2025-01-02T12:00:00",
                "input": "positions.csv",
                "score": None,
            },
        )
        before_fit = fit_path.read_bytes()
        self.adapter.write_fit_result(self.adapter.read_fit_result())
        self.assertEqual(fit_path.read_bytes(), before_fit)

        self.adapter.store_candles(
            [
                MultiEACandle(
                    symbol="EURUSD",
                    source_symbol="EURUSD",
                    timeframe="M1",
                    timestamp=datetime(2025, 1, 1, 10, 0, 0),
                    open=1.04,
                    high=1.05,
                    low=1.03,
                    close=1.045,
                    volume=90.0,
                )
            ]
        )
        history_hash = _file_hash(self.adapter.history_database_path)

        def failing_mutation(connection: sqlite3.Connection) -> None:
            connection.execute("DELETE FROM candles")
            raise RuntimeError("falha simulada")

        with self.assertRaisesRegex(RuntimeError, "falha simulada"):
            self.adapter._mutate_history_database(failing_mutation)

        self.assertEqual(_file_hash(self.adapter.history_database_path), history_hash)
        self.assertFalse(
            any(item.suffix == ".tmp" for item in self.runtime_directory.iterdir())
        )

    def _write_positions_csv(self, rows: list[list[str]]) -> Path:
        path = self.root / "Multi EA Trading.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter=";", lineterminator="\n")
            writer.writerow(CSV_HEADER)
            writer.writerows(rows)
        return path

    def _create_operational_database(
        self,
        rows: list[tuple[object, ...]],
    ) -> None:
        with closing(sqlite3.connect(self.operational_database)) as connection:
            self._create_operational_schema(connection)
            connection.executemany(
                """
                INSERT INTO mt5_history_candles (
                    pair, timeframe, candle_time, open, high, low, close, volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            connection.commit()

    @staticmethod
    def _create_operational_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE mt5_history_candles (
                pair TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                candle_time TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                PRIMARY KEY (pair, timeframe, candle_time)
            )
            """
        )


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
