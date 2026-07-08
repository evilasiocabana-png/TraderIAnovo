"""Testes do servico de ingestao MT5 read-only."""

from __future__ import annotations

import inspect
import unittest

from application.mt5_market_data_service import MT5MarketDataService
from core.configuration_manager import ConfigurationManager
from core.event_bus import EventBus
from core.events import NEW_CANDLE
from domain.candle import Candle
from market.candle_history import CandleHistory
from research.quantitative_score_engine import QuantitativeScoreResult


class FakeProviderWithEventBus:
    def __init__(self, candles: list[Candle]) -> None:
        self.candles = candles
        self.event_bus = EventBus()
        self.connected = False
        self.selected_symbols: list[str] = []
        self.requests: list[tuple[str, str, int]] = []

    def connect(self) -> bool:
        self.connected = True
        return True

    def select_symbol(self, symbol: str) -> bool:
        self.selected_symbols.append(symbol)
        return True

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        self.requests.append((symbol, timeframe, count))
        candles = self.candles[:count]
        for candle in candles:
            self.event_bus.publish(NEW_CANDLE, candle)
        return candles

    def list_symbols(self) -> list[str]:
        return ["EURUSD", "GBPUSD"]

    def symbol_exists(self, symbol: str) -> bool:
        return symbol in {"EURUSD", "GBPUSD"}


class FakeProviderWithoutEventBus:
    def __init__(self, candles: list[Candle]) -> None:
        self.candles = candles

    def connect(self) -> bool:
        return True

    def select_symbol(self, symbol: str) -> bool:
        return bool(symbol)

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        return self.candles[:count]

    def list_symbols(self) -> list[str]:
        return ["EURUSD"]

    def symbol_exists(self, symbol: str) -> bool:
        return symbol == "EURUSD"


class FailingProvider:
    last_error = "MT5 desconectado: falha simulada de initialize."

    def connect(self) -> bool:
        return False

    def select_symbol(self, symbol: str) -> bool:
        return False

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        return []

    def list_symbols(self) -> list[str]:
        return []

    def symbol_exists(self, symbol: str) -> bool:
        return False


class ForexProvider:
    def __init__(self) -> None:
        self.selected_symbols: list[str] = []
        self.requests: list[tuple[str, str, int]] = []

    def connect(self) -> bool:
        return True

    def select_symbol(self, symbol: str) -> bool:
        self.selected_symbols.append(symbol)
        return True

    def symbol_exists(self, symbol: str) -> bool:
        return True

    def list_symbols(self) -> list[str]:
        return [
            "EURUSD",
            "GBPUSD",
            "USDCHF",
            "USDJPY",
            "EURJPY",
            "AUDUSD",
            "NZDUSD",
            "USDCAD",
        ]

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        self.requests.append((symbol, timeframe, count))
        base = 1.0 + (len(symbol) * 0.01)
        direction = -1 if symbol in {"USDCHF", "USDJPY"} else 1
        candles = []
        for index in range(count):
            close = base + (direction * index * 0.0005)
            candles.append(
                Candle(
                    data=f"2026-06-29T{index % 24:02d}:00:00+00:00",
                    abertura=close - (direction * 0.0001),
                    maxima=close + 0.0004,
                    minima=close - 0.0004,
                    fechamento=close,
                    volume=1000 + index,
                )
            )
        return candles

    def get_symbol_microstructure(self, symbol: str) -> dict[str, float | None]:
        base = 1.0 + (len(symbol) * 0.01)
        return {
            "bid": base,
            "ask": base + 0.0002,
            "point": 0.00001,
            "spread": 0.0002,
            "spread_points": 20.0,
        }


class BatchForexProvider(ForexProvider):
    def __init__(self) -> None:
        super().__init__()
        self.batch_requests: list[tuple[dict[str, str], int]] = []

    def get_forex_batch(
        self,
        symbols_timeframes: dict[str, str],
        count: int,
    ) -> dict[str, dict[str, object]]:
        self.batch_requests.append((dict(symbols_timeframes), count))
        return {
            symbol: {
                "exists": True,
                "selected": True,
                "candles": self._batch_candles(symbol, count),
                "microstructure": self.get_symbol_microstructure(symbol),
            }
            for symbol, timeframe in symbols_timeframes.items()
        }

    def _batch_candles(self, symbol: str, count: int) -> list[Candle]:
        base = 1.0 + (len(symbol) * 0.01)
        return [
            Candle(
                data=f"2026-06-29T{index % 24:02d}:00:00+00:00",
                abertura=base + (index * 0.0001),
                maxima=base + (index * 0.0001) + 0.0004,
                minima=base + (index * 0.0001) - 0.0004,
                fechamento=base + (index * 0.0001),
                volume=1000 + index,
            )
            for index in range(count)
        ]


class DynamicForexProvider(ForexProvider):
    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        self.call_count += 1
        candles = super().get_candles(symbol, timeframe, count)
        suffix = f"refresh-{self.call_count}"
        return [
            Candle(
                data=f"{candle.data}-{suffix}",
                abertura=candle.abertura,
                maxima=candle.maxima,
                minima=candle.minima,
                fechamento=candle.fechamento + (self.call_count * 0.00001),
                volume=candle.volume,
            )
            for candle in candles
        ]


class ErrorForexProvider(ForexProvider):
    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        raise RuntimeError("provider failure")


class TimeoutForexProvider(ForexProvider):
    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        raise TimeoutError("provider timeout")


class DiagnosticProvider(ForexProvider):
    def __init__(self) -> None:
        super().__init__()
        self.diagnostic_calls: list[tuple[str, str]] = []

    def diagnose_connection(self, symbol: str, timeframe: str) -> dict[str, object]:
        self.diagnostic_calls.append((symbol, timeframe))
        return {
            "connection_status": "OFFLINE",
            "steps": [
                {
                    "name": "Terminal encontrado",
                    "status": "OK",
                    "message": "Modulo carregado.",
                    "last_error_code": 0,
                    "last_error_message": "OK",
                },
                {
                    "name": "initialize()",
                    "status": "FALHOU",
                    "message": "Terminal desconectado.",
                    "last_error_code": -10003,
                    "last_error_message": "IPC initialize failed",
                },
            ],
            "last_error_code": -10003,
            "last_error_message": "IPC initialize failed",
            "terminal_path": r"C:\MT5\terminal64.exe",
            "build": "4150",
            "server": "N/D",
            "account": "N/D",
            "connected": False,
            "trade_allowed": False,
            "community_connection": False,
            "failed_call": "initialize()",
            "diagnostic_message": "Falha em initialize().",
        }


class CountingScoreEngine:
    def __init__(self) -> None:
        self.calls = 0

    def calculate(self, context, observations):
        self.calls += 1
        return QuantitativeScoreResult(
            decision="WAIT",
            calibrated_confidence=0.25,
            sample_size=len(observations),
            win_rate=0.4,
            avg_return=0.0,
            profit_factor=0.8,
            max_drawdown=0.01,
            reason=f"score call {self.calls}",
            matched_context_count=len(observations),
            rejected_reason="LOW_PROFIT_FACTOR",
        )


class MT5MarketDataServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        ConfigurationManager.reset_configuration()

    def tearDown(self) -> None:
        ConfigurationManager.reset_configuration()

    def test_ingest_candles_insere_no_candle_history(self) -> None:
        candles = [self._candle(1), self._candle(2), self._candle(3)]
        provider = FakeProviderWithEventBus(candles)
        history = CandleHistory()
        service = MT5MarketDataService(
            provider=provider,
            candle_history=history,
            event_bus=EventBus(),
        )

        summary = service.ingest_candles("EURUSD", "H1", 3)

        self.assertTrue(summary.connected)
        self.assertTrue(summary.symbol_selected)
        self.assertEqual(summary.received_candles, 3)
        self.assertEqual(summary.inserted_candles, 3)
        self.assertEqual(summary.last_candle, candles[-1])
        self.assertEqual(history.last_n(3), candles)
        self.assertEqual(provider.selected_symbols, ["EURUSD"])
        self.assertEqual(provider.requests, [("EURUSD", "H1", 3)])

    def test_ingest_candles_publica_new_candle_quando_provider_nao_publica(
        self,
    ) -> None:
        candles = [self._candle(1), self._candle(2)]
        event_bus = EventBus()
        published: list[Candle] = []
        event_bus.subscribe(NEW_CANDLE, published.append)
        service = MT5MarketDataService(
            provider=FakeProviderWithoutEventBus(candles),
            event_bus=event_bus,
        )

        service.ingest_candles("EURUSD", "H1", 2)

        self.assertEqual(published, candles)

    def test_ingest_candles_nao_duplica_eventos_quando_provider_publica(
        self,
    ) -> None:
        candles = [self._candle(1), self._candle(2)]
        event_bus = EventBus()
        published: list[Candle] = []
        event_bus.subscribe(NEW_CANDLE, published.append)
        service = MT5MarketDataService(
            provider=FakeProviderWithEventBus(candles),
            event_bus=event_bus,
        )

        service.ingest_candles("EURUSD", "H1", 2)

        self.assertEqual(published, candles)

    def test_ingest_candles_falha_sem_conexao_sem_alterar_history(self) -> None:
        history = CandleHistory()
        service = MT5MarketDataService(
            provider=FailingProvider(),
            candle_history=history,
        )

        summary = service.ingest_candles("EURUSD", "H1", 5)

        self.assertFalse(summary.connected)
        self.assertEqual(summary.inserted_candles, 0)
        self.assertEqual(history.count(), 0)

    def test_load_dashboard_market_data_retorna_snapshot_read_only(self) -> None:
        candles = [self._candle(1), self._candle(2)]
        service = MT5MarketDataService(
            provider=FakeProviderWithoutEventBus(candles),
            event_bus=EventBus(),
        )

        data = service.load_dashboard_market_data("EURUSD", "H1", 2)

        self.assertEqual(data.connection_status, "CONNECTED")
        self.assertEqual(data.selected_symbol, "EURUSD")
        self.assertEqual(data.selected_timeframe, "H1")
        self.assertEqual(data.candles_loaded, 2)
        self.assertEqual(data.last_candle.close, candles[-1].fechamento)
        self.assertEqual(data.read_only_status, "SOMENTE MARKET DATA")
        self.assertFalse(data.real_operation_authorized)
        self.assertEqual(data.available_symbols, ["EURUSD"])

    def test_load_forex_signal_dashboard_analisa_oito_pares(self) -> None:
        ConfigurationManager.update_configuration(quantitative_score_candles_loaded=100)
        provider = ForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        data = service.load_forex_signal_dashboard("H1")

        self.assertEqual(data.connection_status, "CONNECTED")
        self.assertEqual(len(data.pairs), 8)
        self.assertEqual(data.timeframe, "H1")
        self.assertEqual(data.read_only_status, "SOMENTE ANALISE DE MERCADO")
        self.assertFalse(data.real_operation_authorized)
        pairs = {row.pair: row for row in data.pairs}
        self.assertEqual(set(pairs), {
            "EURUSD",
            "GBPUSD",
            "USDCHF",
            "USDJPY",
            "EURJPY",
            "AUDUSD",
            "NZDUSD",
            "USDCAD",
        })
        self.assertIn(pairs["EURUSD"].decision, {"BUY", "SELL", "WAIT"})
        self.assertIn(pairs["USDCAD"].decision, {"BUY", "SELL", "WAIT"})
        self.assertTrue(pairs["EURUSD"].reason)
        self.assertIsInstance(pairs["EURUSD"].matched_context_count, int)
        self.assertIn(
            pairs["EURUSD"].volatility_bucket,
            {"LOW", "NORMAL", "HIGH", "UNKNOWN"},
        )
        self.assertIsInstance(pairs["EURUSD"].confidence_penalties, tuple)
        self.assertIsInstance(pairs["EURUSD"].confidence_drivers, tuple)
        self.assertTrue(provider.requests)

    def test_load_forex_signal_dashboard_falha_com_oito_waits_sem_mt5(self) -> None:
        service = MT5MarketDataService(provider=FailingProvider())

        data = service.load_forex_signal_dashboard()

        self.assertEqual(data.connection_status, "DISCONNECTED")
        self.assertEqual(len(data.pairs), 8)
        self.assertTrue(all(row.decision == "WAIT" for row in data.pairs))
        self.assertTrue(all(row.status == "MT5 DESCONECTADO" for row in data.pairs))

    def test_load_forex_signal_dashboard_le_parametros_simples_do_mt5(
        self,
    ) -> None:
        ConfigurationManager.update_configuration(
            mt5_safe_mode_candles_loaded=120,
        )
        provider = ForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        data = service.load_forex_signal_dashboard("H1")

        self.assertTrue(provider.requests)
        self.assertTrue(all(request[2] == 120 for request in provider.requests))
        rows = [row for row in data.pairs if row.status == "OK"]
        self.assertTrue(rows)
        self.assertTrue(all(row.decision in {"BUY", "SELL", "WAIT"} for row in rows))

    def test_forex_signal_dashboard_preenche_indicadores_expandidos(self) -> None:
        provider = ForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        data = service.load_forex_signal_dashboard("H1")

        row = next(item for item in data.pairs if item.status == "OK")
        self.assertIsNotNone(row.ema_fast)
        self.assertIsNotNone(row.ema_mid)
        self.assertIsNotNone(row.ema_slow)
        self.assertIsNotNone(row.adx)
        self.assertIsNotNone(row.macd)
        self.assertIsNotNone(row.macd_signal)
        self.assertIsNotNone(row.atr)
        self.assertIsNotNone(row.atr_average)
        self.assertIsNotNone(row.bollinger_upper)
        self.assertIsNotNone(row.bollinger_lower)
        self.assertIsNotNone(row.tick_volume)
        self.assertIsNotNone(row.tick_volume_average)
        self.assertIsNotNone(row.donchian_high)
        self.assertIsNotNone(row.donchian_low)
        self.assertIsNotNone(row.pivot)
        self.assertIsNotNone(row.vwap)
        self.assertIsNotNone(row.z_score)
        self.assertIsNotNone(row.support)
        self.assertIsNotNone(row.resistance)
        self.assertIsNotNone(row.swing_high)
        self.assertIsNotNone(row.swing_low)
        self.assertIsNotNone(row.price_speed)
        self.assertEqual(row.spread, 0.0002)
        self.assertEqual(row.spread_average, 0.0002)
        self.assertIsNotNone(row.slippage_estimate)

    def test_default_carrega_1000_candles_por_simbolo(self) -> None:
        provider = ForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        data = service.load_forex_signal_dashboard("H1")

        self.assertTrue(provider.requests)
        self.assertTrue(all(request[2] == 1000 for request in provider.requests))
        rows = [row for row in data.pairs if row.status == "OK"]
        self.assertTrue(rows)
        self.assertTrue(all(row.configured_candles == 1000 for row in rows))
        self.assertTrue(all(row.requested_candles == 1000 for row in rows))
        self.assertTrue(all(row.received_candles == 1000 for row in rows))
        self.assertTrue(all(row.research_candles_used == 0 for row in rows))
        self.assertTrue(all(row.research_cache_status == "HEURISTIC_ONLY" for row in rows))
        self.assertTrue(data.mt5_safe_mode)
        self.assertEqual(data.safe_mode_source, "MT5_SAFE_MODE")
        self.assertEqual(data.safe_mode_status, "ONLINE")
        self.assertGreater(data.safe_mode_received_candles, 0)
        self.assertIsNotNone(data.safe_mode_last_price)
        self.assertEqual(data.safe_mode_error, "")

    def test_snapshot_de_pesquisa_carrega_5000_sem_substituir_painel_online(
        self,
    ) -> None:
        provider = ForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        online = service.load_forex_signal_dashboard("M1")
        snapshot = service.load_forex_research_snapshot("M1")

        self.assertIs(service.latest_forex_signal_dashboard, online)
        self.assertEqual(snapshot.safe_mode_source, "MT5_RESEARCH_CALIBRATION")
        self.assertTrue(provider.requests)
        research_requests = provider.requests[-8:]
        self.assertTrue(all(request[2] == 5000 for request in research_requests))
        rows = [row for row in snapshot.pairs if row.status == "OK"]
        self.assertTrue(rows)
        self.assertTrue(all(row.configured_candles == 5000 for row in rows))
        self.assertTrue(all(row.requested_candles == 5000 for row in rows))
        self.assertTrue(all(row.received_candles == 5000 for row in rows))
        self.assertTrue(
            all(row.research_cache_status == "RECALCULATED" for row in rows)
        )
        self.assertTrue(all(row.research_candles_used > 0 for row in rows))
        self.assertTrue(all(row.confidence != 0.55 for row in rows))
        self.assertEqual(online.safe_mode_source, "MT5_SAFE_MODE")
        self.assertEqual(online.pairs[0].configured_candles, 1000)

    def test_fluxo_forex_nao_aceita_count_publico(self) -> None:
        service_signature = inspect.signature(
            MT5MarketDataService.load_forex_signal_dashboard
        )

        self.assertNotIn("count", service_signature.parameters)

    def test_diagnostico_expoe_configurado_solicitado_recebido_e_usado(
        self,
    ) -> None:
        provider = ForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        data = service.load_forex_signal_dashboard("H1")

        rows = [row for row in data.pairs if row.status == "OK"]
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row.configured_candles, 1000)
            self.assertEqual(row.requested_candles, 1000)
            self.assertEqual(row.received_candles, 1000)
            self.assertEqual(row.research_candles_used, 0)
            self.assertIn("configurados=1000", row.diagnostics_log)
            self.assertIn("solicitados=1000", row.diagnostics_log)

    def test_refresh_leve_consulta_provider_sem_recalcular_score(self) -> None:
        ConfigurationManager.update_configuration(quantitative_score_candles_loaded=80)
        provider = DynamicForexProvider()
        score_engine = CountingScoreEngine()
        service = MT5MarketDataService(
            provider=provider,
            event_bus=EventBus(),
            quantitative_score_engine=score_engine,
        )

        first = service.load_forex_signal_dashboard("H1")
        second = service.load_forex_signal_dashboard("H1")

        first_eurusd = next(row for row in first.pairs if row.pair == "EURUSD")
        second_eurusd = next(row for row in second.pairs if row.pair == "EURUSD")
        self.assertNotEqual(
            first_eurusd.last_candle_time,
            second_eurusd.last_candle_time,
        )
        self.assertGreaterEqual(len(provider.requests), 14)
        self.assertEqual(score_engine.calls, 0)
        self.assertNotEqual(first_eurusd.last_update, second_eurusd.last_update)
        self.assertEqual(second_eurusd.diagnostics_status, "OK")

    def test_safe_mode_nao_chama_quantitative_score_mesmo_com_recalculo(self) -> None:
        provider = DynamicForexProvider()
        score_engine = CountingScoreEngine()
        service = MT5MarketDataService(
            provider=provider,
            event_bus=EventBus(),
            quantitative_score_engine=score_engine,
        )

        data = service.load_forex_signal_dashboard(
            "H1",
            recalculate_research=True,
        )

        rows = [row for row in data.pairs if row.status == "OK"]
        self.assertTrue(data.mt5_safe_mode)
        self.assertEqual(score_engine.calls, 0)
        self.assertTrue(rows)
        self.assertTrue(all(row.research_cache_status == "HEURISTIC_ONLY" for row in rows))
        self.assertIn("heuristico", data.safe_mode_message)

    def test_safe_mode_nao_roda_timeframe_optimizer(self) -> None:
        provider = ForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        results = service.load_timeframe_optimization_results()

        self.assertEqual(results, [])

    def test_parametro_quebrado_do_research_nao_derruba_mt5_safe_mode(self) -> None:
        ConfigurationManager.update_configuration(
            quantitative_score_slow_ma_period=None,
            quantitative_score_candles_loaded=None,
        )
        provider = ForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        data = service.load_forex_signal_dashboard("H1")

        self.assertEqual(data.connection_status, "CONNECTED")
        self.assertTrue(data.mt5_safe_mode)
        self.assertEqual(len(data.pairs), 8)
        ok_rows = [row for row in data.pairs if row.status == "OK"]
        self.assertTrue(ok_rows)
        self.assertTrue(provider.requests)
        self.assertTrue(all(request[2] == 1000 for request in provider.requests))

    def test_forex_timeframes_usa_batch_por_padrao(self) -> None:
        provider = BatchForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        data = service.load_forex_signal_dashboard_for_timeframes(
            {"EURUSD": "M1", "GBPUSD": "H1"},
            fallback_timeframe="M1",
        )

        self.assertEqual(data.connection_status, "CONNECTED")
        self.assertEqual(len(provider.batch_requests), 1)
        self.assertEqual(provider.requests, [])
        requested_symbols, requested_count = provider.batch_requests[0]
        self.assertEqual(requested_count, 1000)
        self.assertIn("EURUSD", requested_symbols)
        self.assertIn("USDCAD", requested_symbols)

    def test_refresh_id_incrementa_em_safe_mode(self) -> None:
        provider = ForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        first = service.load_forex_signal_dashboard("H1")
        second = service.load_forex_signal_dashboard("H1")

        self.assertEqual(first.refresh_id + 1, second.refresh_id)
        self.assertNotEqual(first.last_update, "")
        self.assertNotEqual(second.last_update, "")

    def test_safe_mode_provider_falha_retorna_offline_com_erro_explicito(self) -> None:
        service = MT5MarketDataService(provider=FailingProvider(), event_bus=EventBus())

        data = service.load_forex_signal_dashboard("H1")

        self.assertTrue(data.mt5_safe_mode)
        self.assertEqual(data.safe_mode_source, "MT5_SAFE_MODE")
        self.assertEqual(data.safe_mode_status, "OFFLINE")
        self.assertEqual(data.safe_mode_received_candles, 0)
        self.assertIsNone(data.safe_mode_last_price)
        self.assertIn("desconectado", data.safe_mode_error.lower())

    def test_recalculo_research_nao_chama_quantitative_score_no_fluxo_mt5(self) -> None:
        provider = DynamicForexProvider()
        score_engine = CountingScoreEngine()
        service = MT5MarketDataService(
            provider=provider,
            event_bus=EventBus(),
            quantitative_score_engine=score_engine,
        )

        data = service.load_forex_signal_dashboard(
            "H1",
            recalculate_research=True,
        )

        rows = [row for row in data.pairs if row.status == "OK"]
        self.assertEqual(score_engine.calls, 0)
        self.assertTrue(rows)
        self.assertEqual(data.research_cache_status, "NO_MARKET_DATA")
        self.assertTrue(all(row.research_cache_status == "HEURISTIC_ONLY" for row in rows))

    def test_refresh_com_mesmo_candle_permanece_heuristico(self) -> None:
        provider = ForexProvider()
        score_engine = CountingScoreEngine()
        service = MT5MarketDataService(
            provider=provider,
            event_bus=EventBus(),
            quantitative_score_engine=score_engine,
        )

        service.load_forex_signal_dashboard("H1", recalculate_research=True)
        calls_after_research = score_engine.calls
        data = service.load_forex_signal_dashboard("H1")

        self.assertEqual(score_engine.calls, calls_after_research)
        self.assertEqual(data.research_cache_status, "NO_MARKET_DATA")

    def test_health_online_com_dados_atualizados_fica_verde(self) -> None:
        provider = DynamicForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        data = service.load_forex_signal_dashboard("H1")

        self.assertEqual(data.connection_health, "ONLINE")
        self.assertEqual(data.connection_health_icon, "🟢")
        self.assertIn("Dados atualizados", data.health_message)
        self.assertGreater(data.refresh_id, 0)
        self.assertNotEqual(data.last_candle_time, "N/D")

    def test_health_online_sem_nova_vela_fica_amarelo(self) -> None:
        provider = ForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        service.load_forex_signal_dashboard("H1")
        data = service.load_forex_signal_dashboard("H1")

        self.assertEqual(data.connection_health, "ONLINE — Aguardando nova vela")
        self.assertEqual(data.connection_health_icon, "🟡")
        self.assertIn("Aguardando fechamento", data.health_message)

    def test_health_offline_fica_vermelho(self) -> None:
        service = MT5MarketDataService(provider=FailingProvider(), event_bus=EventBus())

        data = service.load_forex_signal_dashboard("H1")

        self.assertEqual(data.connection_health, "OFFLINE")
        self.assertEqual(data.connection_health_icon, "🔴")
        self.assertIn("desconectado", data.health_message.lower())

    def test_health_erro_de_leitura_fica_vermelho(self) -> None:
        service = MT5MarketDataService(provider=ErrorForexProvider(), event_bus=EventBus())

        data = service.load_forex_signal_dashboard("H1")

        self.assertEqual(data.connection_health, "OFFLINE")
        self.assertEqual(data.connection_health_icon, "🔴")
        self.assertIn("provider failure", data.health_message)

    def test_health_timeout_fica_vermelho(self) -> None:
        service = MT5MarketDataService(
            provider=TimeoutForexProvider(),
            event_bus=EventBus(),
        )

        data = service.load_forex_signal_dashboard("H1")

        self.assertEqual(data.connection_health, "OFFLINE")
        self.assertEqual(data.connection_health_icon, "🔴")
        self.assertIn("timeout", data.health_message.lower())

    def test_diagnose_mt5_connection_propaga_etapa_e_last_error(self) -> None:
        provider = DiagnosticProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        diagnostic = service.diagnose_mt5_connection("EURUSD", "H1")

        self.assertEqual(provider.diagnostic_calls, [("EURUSD", "H1")])
        self.assertEqual(diagnostic.connection_status, "OFFLINE")
        self.assertEqual(diagnostic.failed_call, "initialize()")
        self.assertEqual(diagnostic.last_error_code, -10003)
        self.assertEqual(diagnostic.last_error_message, "IPC initialize failed")
        self.assertEqual(diagnostic.terminal_path, r"C:\MT5\terminal64.exe")
        self.assertEqual(
            [step.name for step in diagnostic.steps],
            ["Terminal encontrado", "initialize()"],
        )
        self.assertEqual(diagnostic.steps[1].status, "FALHOU")
        self.assertEqual(
            service.get_forex_signal_dashboard().connection_diagnostic.failed_call,
            "initialize()",
        )

    def test_load_timeframe_optimizer_fica_desconectado_do_fluxo_mt5(self) -> None:
        provider = ForexProvider()
        service = MT5MarketDataService(provider=provider, event_bus=EventBus())

        results = service.load_timeframe_optimization_results()

        self.assertEqual(results, [])
        self.assertEqual(provider.requests, [])

    def test_service_nao_expoe_capacidade_operacional(self) -> None:
        source = inspect.getsource(MT5MarketDataService)
        forbidden_fragments = {
            "order" + "_send",
            "orders" + "_get",
            "positions" + "_get",
            "positions" + "_total",
            "send" + "_order",
            "place" + "_order",
            "execute" + "_order",
            "Broker",
        }

        self.assertEqual(
            [item for item in forbidden_fragments if item in source],
            [],
        )

    def _candle(self, index: int) -> Candle:
        return Candle(
            data=f"2026-06-29T0{index}:00:00+00:00",
            abertura=1.10 + index,
            maxima=1.20 + index,
            minima=1.00 + index,
            fechamento=1.15 + index,
            volume=1000 + index,
        )


if __name__ == "__main__":
    unittest.main()
