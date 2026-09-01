from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.model28_forward_validation_service import (
    MODEL28_COMPARISON_START_BRT,
    Model28ForwardValidationService,
    _broker_clock_offsets,
    _compare_signals,
    _read_operational_availability,
    _realized_mt5_curve,
    _signal_has_active_observation,
    _signal_is_in_comparison_period,
    _theoretical_result_curve,
    _with_projected_financials,
    _with_operational_candle_time,
    record_model28_operational_heartbeat,
)
from replay.pattern_miner.models import CandleBar
from domain.candle import Candle


class _RangeProvider:
    def __init__(self, candles_by_symbol: dict[str, list[Candle]]) -> None:
        self.candles_by_symbol = candles_by_symbol
        self.calls = 0
        self.ranges: list[tuple[datetime, datetime]] = []
        self.requests: list[tuple[tuple[str, ...], datetime, datetime]] = []

    def get_research_range(
        self,
        symbols: list[str],
        timeframe: int,
        date_from: datetime,
        date_to: datetime,
    ) -> dict[str, dict[str, object]]:
        self.calls += 1
        self.ranges.append((date_from, date_to))
        self.requests.append((tuple(symbols), date_from, date_to))
        return {
            symbol: {
                "exists": True,
                "selected": True,
                "candles": list(self.candles_by_symbol.get(symbol, [])),
            }
            for symbol in symbols
        }


class Model28ForwardValidationServiceTests(unittest.TestCase):
    def test_projected_profit_uses_confirmed_order_geometry_and_contract(self) -> None:
        rows = _with_projected_financials(
            [
                {
                    "symbol": "EURUSD",
                    "mt5_entry_plan": 1.10000,
                    "mt5_executed_price": 1.10002,
                    "mt5_target": 1.10022,
                    "mt5_quantity": 0.11,
                }
            ],
            {"EURUSD": {"tick_size": 0.00001, "tick_value": 1.0}},
        )

        self.assertAlmostEqual(rows[0]["projected_profit_usd"], 2.2)

    def test_update_compensa_relogio_broker_e_persiste_utc_fisico(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original.csv"
            self._write_original(original)

            class _BrokerClockProvider(_RangeProvider):
                def get_server_time(self, _symbol: str = "EURUSD") -> str:
                    return "2026-08-28T13:15:00+00:00"

            provider = _BrokerClockProvider(
                {
                    "XAUUSD": [
                        self._candle("2026-08-28 13:05:00", 101.0),
                        self._candle("2026-08-28 13:10:00", 102.0),
                    ]
                }
            )
            service = Model28ForwardValidationService(
                provider,
                markets=("XAUUSD",),
                forward_root=root / "forward",
                operational_store_path=root / "patterns.json",
                execution_log_path=root / "execution.jsonl",
                original_path_resolver=lambda _symbol: original,
            )

            service.update(
                now=datetime(2026, 8, 28, 10, 15, tzinfo=timezone.utc)
            )

            self.assertEqual(
                provider.ranges,
                [(
                    datetime(2026, 8, 28, 13, 5, tzinfo=timezone.utc),
                    datetime(2026, 8, 28, 13, 15, tzinfo=timezone.utc),
                )],
            )
            incremental = (
                root / "forward" / "XAUUSD" / "historicoXAUUSD_M5_incremental.csv"
            )
            with incremental.open(encoding="utf-8") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(
                [row["datetime"] for row in rows],
                ["2026-08-28 10:05:00", "2026-08-28 10:10:00"],
            )

    def test_update_preserva_base_e_grava_apenas_incremento_fechado(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            originals = {"XAUUSD": root / "original.csv"}
            self._write_original(originals["XAUUSD"])
            before = originals["XAUUSD"].read_bytes()
            provider = _RangeProvider(
                {
                    "XAUUSD": [
                        self._candle("2026-08-28 10:05:00", 101.0),
                        self._candle("2026-08-28 10:10:00", 102.0),
                        self._candle("2026-08-28 10:15:00", 103.0),
                    ]
                }
            )
            service = Model28ForwardValidationService(
                provider,
                markets=("XAUUSD",),
                forward_root=root / "forward",
                operational_store_path=root / "patterns.json",
                execution_log_path=root / "execution.jsonl",
                original_path_resolver=lambda symbol: originals[symbol],
            )

            report = service.update(
                now=datetime(2026, 8, 28, 10, 15, tzinfo=timezone.utc)
            )

            self.assertEqual(originals["XAUUSD"].read_bytes(), before)
            self.assertEqual(report["total_incremental_candles"], 2)
            incremental = root / "forward" / "XAUUSD" / "historicoXAUUSD_M5_incremental.csv"
            with incremental.open(encoding="utf-8") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual([row["datetime"] for row in rows], [
                "2026-08-28 10:05:00",
                "2026-08-28 10:10:00",
            ])

    def test_repetir_atualizacao_nao_duplica_candles(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original.csv"
            self._write_original(original)
            provider = _RangeProvider(
                {"XAUUSD": [self._candle("2026-08-28 10:05:00", 101.0)]}
            )
            service = Model28ForwardValidationService(
                provider,
                markets=("XAUUSD",),
                forward_root=root / "forward",
                operational_store_path=root / "patterns.json",
                execution_log_path=root / "execution.jsonl",
                original_path_resolver=lambda _symbol: original,
            )
            now = datetime(2026, 8, 28, 10, 10, tzinfo=timezone.utc)

            first = service.update(now=now)
            second = service.update(now=now)

            self.assertEqual(first["total_incremental_candles"], 1)
            self.assertEqual(second["total_incremental_candles"], 1)
            self.assertEqual(second["markets"][0]["new_candles"], 0)

    def test_atualizacao_consulta_cada_ativo_depois_do_ultimo_candle_salvo(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original.csv"
            self._write_original(original)
            provider = _RangeProvider(
                {
                    "XAUUSD": [
                        self._candle("2026-08-28 10:05:00", 101.0),
                        self._candle("2026-08-28 10:10:00", 102.0),
                    ],
                    "EURUSD": [self._candle("2026-08-28 10:05:00", 1.0)],
                }
            )
            service = Model28ForwardValidationService(
                provider,
                markets=("XAUUSD", "EURUSD"),
                forward_root=root / "forward",
                operational_store_path=root / "patterns.json",
                execution_log_path=root / "execution.jsonl",
                original_path_resolver=lambda _symbol: original,
            )
            service.update(
                now=datetime(2026, 8, 28, 10, 15, tzinfo=timezone.utc)
            )
            provider.requests.clear()
            provider.candles_by_symbol = {
                "XAUUSD": [self._candle("2026-08-28 10:15:00", 103.0)],
                "EURUSD": [
                    self._candle("2026-08-28 10:10:00", 1.1),
                    self._candle("2026-08-28 10:15:00", 1.2),
                ],
            }

            service.update(
                now=datetime(2026, 8, 28, 10, 20, tzinfo=timezone.utc)
            )

            starts = {
                symbols[0]: date_from
                for symbols, date_from, _date_to in provider.requests
            }
            self.assertEqual(
                starts,
                {
                    "XAUUSD": datetime(2026, 8, 28, 10, 15, tzinfo=timezone.utc),
                    "EURUSD": datetime(2026, 8, 28, 10, 10, tzinfo=timezone.utc),
                },
            )

    def test_load_report_inicial_nao_le_base_congelada(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = Model28ForwardValidationService(
                _RangeProvider({}),
                markets=("XAUUSD", "EURUSD"),
                forward_root=root / "forward",
                original_path_resolver=lambda symbol: root / f"{symbol}.csv",
            )

            report = service.load_report()

            self.assertEqual(len(report["markets"]), 2)
            self.assertTrue(all(
                row["status"] == "CLIQUE_EM_ATUALIZAR_DADOS"
                for row in report["markets"]
            ))

    def test_curva_teorica_resolve_alvo_sem_consultar_resultado_real(self) -> None:
        signal = {
            "symbol": "XAUUSD",
            "candle_time": "2026-08-28T10:00:00+00:00",
            "entry_time": "2026-08-28T10:05:00+00:00",
            "pattern_id": "PAT-TESTE",
            "direction": "BUY",
            "entry": 100.0,
            "stop": 99.0,
            "target": 102.0,
            "max_holding_candles": 20,
            "entry_spread_points": 0,
        }
        candles = {
            "XAUUSD": [
                CandleBar(0, datetime(2026, 8, 28, 10, 5, tzinfo=timezone.utc), 100, 102.2, 99.5, 102, 1, 0, 0),
            ]
        }

        curve = _theoretical_result_curve(
            [signal], candles, chart_day="2026-08-28"
        )

        self.assertEqual(curve[0]["outcome"], "TARGET")
        self.assertEqual(curve[0]["result_r"], 2.0)
        self.assertEqual(curve[0]["cumulative_r"], 2.0)

    def test_curva_teorica_aplica_spread_registrado_do_contrato(self) -> None:
        signal = {
            "symbol": "XAUUSD",
            "candle_time": "2026-08-28T10:00:00+00:00",
            "entry_time": "2026-08-28T10:05:00+00:00",
            "pattern_id": "PAT-CUSTO",
            "direction": "BUY",
            "entry": 100.0,
            "stop": 99.0,
            "target": 102.0,
            "max_holding_candles": 20,
            "entry_spread_points": 10,
        }
        candles = {
            "XAUUSD": [
                CandleBar(0, datetime(2026, 8, 28, 10, 5, tzinfo=timezone.utc), 100, 102.2, 99.5, 102, 1, 10, 0),
            ]
        }

        curve = _theoretical_result_curve(
            [signal], candles, chart_day="2026-08-28"
        )

        self.assertEqual(curve[0]["outcome"], "TARGET")
        self.assertAlmostEqual(curve[0]["cost_r"], 0.1)
        self.assertAlmostEqual(curve[0]["result_r"], 1.9)

    def test_curva_teorica_fecha_no_prazo_empirico_do_pattern_id(self) -> None:
        signal = {
            "symbol": "EURUSD",
            "candle_time": "2026-08-28T10:00:00+00:00",
            "entry_time": "2026-08-28T10:05:00+00:00",
            "pattern_id": "PAT-PRAZO",
            "direction": "BUY",
            "entry": 1.1000,
            "stop": 1.0990,
            "target": 1.1020,
            "max_holding_candles": 2,
            "entry_spread_points": 0,
        }
        candles = {
            "EURUSD": [
                CandleBar(0, datetime(2026, 8, 28, 10, 5, tzinfo=timezone.utc), 1.1000, 1.1006, 1.0995, 1.1005, 1, 0, 0),
                CandleBar(1, datetime(2026, 8, 28, 10, 10, tzinfo=timezone.utc), 1.1005, 1.1012, 1.1002, 1.1010, 1, 0, 0),
            ]
        }

        curve = _theoretical_result_curve(
            [signal], candles, chart_day="2026-08-28"
        )

        self.assertEqual(curve[0]["outcome"], "TIME_EXIT")
        self.assertEqual(curve[0]["bars_held"], 2)
        self.assertAlmostEqual(curve[0]["result_r"], 1.0)

    def test_curva_real_soma_resultado_e_custos_apenas_do_m28(self) -> None:
        with TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "audit.json"
            snapshot.write_text(
                __import__("json").dumps(
                    {
                        "rows": [
                            {
                                "operational_model": "MODELO_28_PATTERN_MINER_SHADOW",
                                "operation_status": "FECHADA/HISTORICO",
                                "mt5_time": "2026-08-28T12:00:00+00:00",
                                "symbol": "EURUSD",
                                "mt5_ticket": 123,
                                "entry_price": 1.10,
                                "stop": 1.09,
                                "quantity": 0.10,
                                "mt5_realized_profit": 10.0,
                                "mt5_commission": -1.2,
                                "mt5_swap": -0.3,
                                "mt5_fee": 0.0,
                            },
                            {
                                "operational_model": "MODELO_27",
                                "operation_status": "FECHADA/HISTORICO",
                                "mt5_time": "2026-08-28T12:05:00+00:00",
                                "symbol": "EURUSD",
                                "mt5_ticket": 124,
                                "mt5_realized_profit": 100.0,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            curve = _realized_mt5_curve(
                snapshot,
                chart_day="2026-08-28",
                symbol_costs={
                    "EURUSD": {"tick_size": 0.00001, "tick_value": 1.0}
                },
            )

            self.assertEqual(len(curve), 1)
            self.assertAlmostEqual(curve[0]["result_usd"], 8.5)
            self.assertAlmostEqual(curve[0]["cumulative_usd"], 8.5)
            self.assertAlmostEqual(curve[0]["risk_usd"], 100.0)
            self.assertAlmostEqual(curve[0]["result_r"], 0.085)
            self.assertAlmostEqual(curve[0]["cumulative_r"], 0.085)

    def test_comparacao_exige_heartbeat_ativo_no_fechamento_do_candle(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "availability.jsonl"
            record_model28_operational_heartbeat(
                online=True,
                model_selected=True,
                cycle_completed=True,
                ready_symbols=("XAUUSD",),
                status="ARMED_WAITING",
                observed_at=datetime(2026, 8, 28, 10, 5, 10, tzinfo=timezone.utc),
                path=path,
            )
            observations = _read_operational_availability(path)
            signal = {
                "symbol": "XAUUSD",
                "candle_time": "2026-08-28T10:00:00+00:00",
            }

            self.assertTrue(_signal_has_active_observation(signal, observations))
            self.assertFalse(
                _signal_has_active_observation(
                    {**signal, "symbol": "EURUSD"}, observations
                )
            )

    def test_comparacao_exclui_periodo_sem_ciclo_concluido(self) -> None:
        observations = [
            {
                "observed_at": "2026-08-28T10:05:10+00:00",
                "active": False,
                "ready_symbols": ["XAUUSD"],
            }
        ]
        signal = {
            "symbol": "XAUUSD",
            "candle_time": "2026-08-28T10:00:00+00:00",
        }

        self.assertFalse(_signal_has_active_observation(signal, observations))

    def test_comparacao_inicia_domingo_as_19_brt_pelo_fechamento_m5(self) -> None:
        self.assertEqual(
            MODEL28_COMPARISON_START_BRT.isoformat(),
            "2026-08-30T19:00:00-03:00",
        )
        self.assertFalse(
            _signal_is_in_comparison_period(
                {"candle_time": "2026-08-30T21:50:00+00:00"}
            )
        )
        self.assertTrue(
            _signal_is_in_comparison_period(
                {"candle_time": "2026-08-30T21:55:00+00:00"}
            )
        )

    def test_normaliza_relogio_broker_mais_tres_horas_antes_da_comparacao(self) -> None:
        attempts = [
            {
                "symbol": "BTCUSD",
                "candle_time": "2026-08-31T01:10:00+00:00",
                "attempted_at": "2026-08-30T19:15:15-03:00",
                "accepted": True,
            }
        ]

        offsets = _broker_clock_offsets(attempts)
        normalized = _with_operational_candle_time(
            attempts[0],
            offsets["BTCUSD"],
        )

        self.assertEqual(offsets["BTCUSD"], timedelta(hours=3))
        self.assertEqual(
            normalized["source_candle_time"],
            "2026-08-31T01:10:00+00:00",
        )
        self.assertEqual(
            normalized["operational_candle_time"],
            "2026-08-30T22:10:00+00:00",
        )

    def test_comparador_preserva_identidade_bruta_e_exibe_horario_operacional(self) -> None:
        clock_offset = timedelta(hours=3)
        theoretical = _with_operational_candle_time(
            {
                "symbol": "BTCUSD",
                "candle_time": "2026-08-31T01:10:00+00:00",
                "pattern_id": "PAT-TESTE",
                "pattern_occurrence_id": "OCC-1",
                "direction": "BUY",
                "entry": 100.0,
                "stop": 99.0,
                "target": 101.0,
            },
            clock_offset,
        )
        actual = _with_operational_candle_time(
            {
                **theoretical,
                "accepted": True,
                "ticket": 123,
                "status": "ACCEPTED",
                "attempted_at": "2026-08-30T19:15:15-03:00",
            },
            clock_offset,
        )

        rows = _compare_signals([theoretical], [actual])

        self.assertEqual(rows[0]["comparison_status"], "CONFERE")
        self.assertEqual(rows[0]["candle_time"], "2026-08-30T22:10:00+00:00")
        self.assertEqual(rows[0]["source_candle_time"], "2026-08-31T01:10:00+00:00")

    def test_comparador_casa_utc_fisico_com_relogio_bruto_do_broker(self) -> None:
        theoretical = _with_operational_candle_time(
            {
                "symbol": "BTCUSD",
                "candle_time": "2026-08-30T22:10:00+00:00",
                "pattern_id": "PAT-TESTE",
                "pattern_occurrence_id": "REPLAY-OCC",
                "direction": "BUY",
                "entry": 100.0,
                "stop": 99.0,
                "target": 101.0,
            },
            timedelta(),
        )
        actual = _with_operational_candle_time(
            {
                "symbol": "BTCUSD",
                "candle_time": "2026-08-31T01:10:00+00:00",
                "pattern_id": "PAT-TESTE",
                "pattern_occurrence_id": "LIVE-OCC",
                "direction": "BUY",
                "entry": 100.0,
                "stop": 99.0,
                "target": 101.0,
                "accepted": True,
                "ticket": 123,
                "status": "ACCEPTED",
            },
            timedelta(hours=3),
        )

        rows = _compare_signals([theoretical], [actual])

        self.assertEqual(rows[0]["comparison_status"], "CONFERE")

    def test_comparador_separa_pequena_deriva_atr_de_geometria_incorreta(self) -> None:
        theoretical = {
            "symbol": "XAUUSD",
            "candle_time": "2026-08-30T22:10:00+00:00",
            "pattern_id": "PAT-TESTE",
            "pattern_occurrence_id": "OCC-1",
            "direction": "BUY",
            "entry": 100.0,
            "stop": 99.01,
            "target": 101.98,
        }
        actual = {
            **theoretical,
            "pattern_occurrence_id": "OCC-2",
            "stop": 99.0,
            "target": 102.0,
            "accepted": True,
            "ticket": 123,
            "status": "ACCEPTED",
        }

        rows = _compare_signals([theoretical], [actual])

        self.assertEqual(
            rows[0]["comparison_status"],
            "CONFERE_TOLERANCIA_ATR",
        )

    def test_curva_teorica_exibe_saida_no_relogio_operacional(self) -> None:
        signal = _with_operational_candle_time(
            {
                "symbol": "BTCUSD",
                "candle_time": "2026-08-31T01:10:00+00:00",
                "entry_time": "2026-08-31T01:15:00+00:00",
                "pattern_id": "PAT-TESTE",
                "direction": "BUY",
                "entry": 100.0,
                "stop": 99.0,
                "target": 101.0,
                "max_holding_candles": 20,
                "entry_spread_points": 0,
            },
            timedelta(hours=3),
        )
        candles = {
            "BTCUSD": [
                CandleBar(
                    0,
                    datetime(2026, 8, 31, 1, 15, tzinfo=timezone.utc),
                    100,
                    101.2,
                    99.5,
                    101,
                    1,
                    0,
                    0,
                )
            ]
        }

        curve = _theoretical_result_curve(
            [signal],
            candles,
            chart_day="2026-08-30",
        )

        self.assertEqual(curve[0]["signal_time"], "2026-08-30T22:10:00+00:00")
        self.assertEqual(curve[0]["time"], "2026-08-30T22:15:00+00:00")

    def test_relatorio_inicial_expoe_marco_fixo_da_comparacao(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = Model28ForwardValidationService(
                _RangeProvider({}),
                markets=("XAUUSD",),
                forward_root=root / "forward",
                original_path_resolver=lambda symbol: root / f"{symbol}.csv",
            )

            report = service.load_report()

            self.assertEqual(
                report["comparison_start_brt"],
                "2026-08-30T19:00:00-03:00",
            )

    @staticmethod
    def _write_original(path: Path) -> None:
        path.write_text(
            "datetime,open,high,low,close,volume,spread,real_volume,is_closed\n"
            "2026-08-28 09:50:00,98,100,97,99,10,1,0,1\n"
            "2026-08-28 09:55:00,99,101,98,100,10,1,0,1\n"
            "2026-08-28 10:00:00,100,102,99,101,10,1,0,1\n",
            encoding="utf-8",
        )

    @staticmethod
    def _candle(timestamp: str, price: float) -> Candle:
        return Candle(
            data=timestamp,
            abertura=price,
            maxima=price + 1.0,
            minima=price - 1.0,
            fechamento=price + 0.5,
            volume=10,
        )


if __name__ == "__main__":
    unittest.main()
