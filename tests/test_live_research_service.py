"""Testes do LiveResearchService em modo read-only."""

from __future__ import annotations

import inspect
import unittest

from application.live_research_service import (
    LiveResearchSignalRecord,
    LiveResearchService,
    LiveResearchSnapshotRecord,
)
from application.mt5_market_data_service import MT5IngestionSummary
from core.event_bus import EventBus
from core.events import DECISION_CREATED, STRATEGY_SIGNAL_CREATED
from domain.candle import Candle
from domain.contracts.decision_context import DecisionContext
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from market.candle_history import CandleHistory


class SpyDecisionPipeline:
    def __init__(self) -> None:
        self.calls: list[tuple[StrategySignal, MarketSnapshot, RiskDecision]] = []

    def processar(
        self,
        strategy_signal: StrategySignal,
        market_snapshot: MarketSnapshot,
        risk_decision: RiskDecision,
    ) -> DecisionContext:
        self.calls.append((strategy_signal, market_snapshot, risk_decision))
        return DecisionContext(
            strategy_signal=strategy_signal,
            market_snapshot=market_snapshot,
            risk_decision=risk_decision,
            final_decision=strategy_signal.decision,
            final_confidence=strategy_signal.confidence,
            approved=risk_decision.allowed,
        )


class FakeMT5MarketDataService:
    def __init__(self, history: CandleHistory, candles: list[Candle]) -> None:
        self.candle_history = history
        self.event_bus = EventBus()
        self.candles = candles

    def ingest_candles(
        self,
        symbol: str,
        timeframe: str,
        count: int,
    ) -> MT5IngestionSummary:
        selected = self.candles[:count]
        for candle in selected:
            self.candle_history.add_candle(candle)
        return MT5IngestionSummary(
            symbol=symbol,
            timeframe=timeframe,
            requested_candles=count,
            received_candles=len(selected),
            inserted_candles=len(selected),
            connected=True,
            symbol_selected=True,
            last_candle=selected[-1] if selected else None,
            message="fake ingestion",
        )


class LiveResearchServiceTest(unittest.TestCase):
    def test_process_candle_executa_cadeia_ate_decision_pipeline(self) -> None:
        pipeline = SpyDecisionPipeline()
        event_bus = EventBus()
        signal_events: list[StrategySignal] = []
        decision_events: list[DecisionContext] = []
        event_bus.subscribe(STRATEGY_SIGNAL_CREATED, signal_events.append)
        event_bus.subscribe(DECISION_CREATED, decision_events.append)
        service = LiveResearchService(
            decision_pipeline=pipeline,
            event_bus=event_bus,
        )

        data = service.process_candle(self._candle(1), symbol="EURUSD", timeframe="H1")

        strategy_count = len(service.strategy_factory.list_available())
        self.assertEqual(len(data.strategy_results), strategy_count)
        self.assertEqual(len(pipeline.calls), strategy_count)
        self.assertEqual(len(signal_events), strategy_count)
        self.assertEqual(len(decision_events), strategy_count)
        self.assertTrue(all(not result.decision_context.approved for result in data.strategy_results))
        self.assertEqual(service.candle_history.count(), 1)
        self.assertIs(service.get_latest_data(), data)
        self.assertEqual(len(service.list_snapshot_history()), 1)
        self.assertEqual(service.list_snapshot_history()[0].symbol, "EURUSD")
        self.assertEqual(service.list_snapshot_history()[0].timeframe, "H1")
        self.assertEqual(
            len(service.list_snapshot_history()[0].signals),
            strategy_count,
        )
        self.assertEqual(
            service.live_experiment_runner.summary().total_signals,
            strategy_count,
        )

    def test_ingest_from_mt5_processa_candles_inseridos_no_history(self) -> None:
        history = CandleHistory()
        candles = [self._candle(index) for index in range(1, 4)]
        pipeline = SpyDecisionPipeline()
        fake_mt5_service = FakeMT5MarketDataService(history, candles)
        service = LiveResearchService(
            mt5_market_data_service=fake_mt5_service,
            candle_history=history,
            decision_pipeline=pipeline,
        )

        data = service.ingest_from_mt5("EURUSD", "H1", 3)

        self.assertIsNotNone(data)
        self.assertEqual(history.count(), 3)
        self.assertEqual(data.current_candle, candles[-1])
        self.assertEqual(data.ingestion_summary.inserted_candles, 3)
        self.assertGreaterEqual(len(pipeline.calls), 3)
        self.assertEqual(len(service.list_snapshot_history()), 3)

    def test_historico_live_respeita_limite_configuravel(self) -> None:
        service = LiveResearchService(snapshot_history_limit=2)

        service.process_candle(self._candle(1), symbol="EURUSD", timeframe="H1")
        service.process_candle(self._candle(2), symbol="EURUSD", timeframe="H1")
        service.process_candle(self._candle(3), symbol="GBPUSD", timeframe="H1")

        history = service.list_snapshot_history()

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].symbol, "EURUSD")
        self.assertEqual(history[1].symbol, "GBPUSD")

    def test_limite_do_historico_live_pode_ser_reconfigurado(self) -> None:
        service = LiveResearchService(snapshot_history_limit=3)
        for index in range(1, 4):
            service.process_candle(
                self._candle(index),
                symbol=f"EURUSD{index}",
                timeframe="H1",
            )

        service.set_snapshot_history_limit(1)

        history = service.list_snapshot_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].symbol, "EURUSD3")

    def test_session_summary_calcula_estatisticas_em_memoria(self) -> None:
        service = LiveResearchService(
            snapshot_history=[
                self._snapshot("2026-06-29T01:00:00+00:00", "BUY", 0.20),
                self._snapshot("2026-06-29T02:00:00+00:00", "SELL", 0.80),
                self._snapshot("2026-06-29T03:00:00+00:00", "WAIT", 0.50),
            ]
        )

        summary = service.get_session_summary()

        self.assertEqual(summary.total_snapshots, 3)
        self.assertEqual(summary.buy_count, 1)
        self.assertEqual(summary.sell_count, 1)
        self.assertEqual(summary.wait_count, 1)
        self.assertAlmostEqual(summary.average_confidence, 0.50)
        self.assertEqual(summary.highest_confidence, 0.80)
        self.assertEqual(summary.lowest_confidence, 0.20)
        self.assertEqual(summary.last_decision, "WAIT")
        self.assertEqual(summary.last_timestamp, "2026-06-29T03:00:00+00:00")

    def test_signal_quality_calcula_metricas_por_estrategia(self) -> None:
        service = LiveResearchService(
            snapshot_history=[
                self._snapshot(
                    "2026-06-29T01:00:00+00:00",
                    "BUY",
                    0.20,
                    signals=[
                        self._signal("alpha_a", "BUY", 0.60),
                        self._signal("alpha_b", "WAIT", 0.20),
                    ],
                ),
                self._snapshot(
                    "2026-06-29T02:00:00+00:00",
                    "SELL",
                    0.80,
                    signals=[
                        self._signal("alpha_a", "SELL", 0.80),
                        self._signal("alpha_b", "WAIT", 0.40),
                    ],
                ),
            ]
        )

        quality = service.list_signal_quality()

        self.assertEqual([row.strategy_name for row in quality], ["alpha_a", "alpha_b"])
        alpha_a = quality[0]
        alpha_b = quality[1]
        self.assertEqual(alpha_a.signal_count, 2)
        self.assertEqual(alpha_a.buy_count, 1)
        self.assertEqual(alpha_a.sell_count, 1)
        self.assertEqual(alpha_a.wait_count, 0)
        self.assertAlmostEqual(alpha_a.average_confidence, 0.70)
        self.assertEqual(alpha_a.last_decision, "SELL")
        self.assertEqual(alpha_b.signal_count, 2)
        self.assertEqual(alpha_b.wait_count, 2)
        self.assertAlmostEqual(alpha_b.average_confidence, 0.30)
        self.assertEqual(alpha_b.last_decision, "WAIT")

    def test_service_nao_cria_ordens_nem_capacidade_operacional(self) -> None:
        source = inspect.getsource(LiveResearchService)
        forbidden_fragments = {
            "order" + "_send",
            "orders" + "_get",
            "positions" + "_get",
            "positions" + "_total",
            "Broker",
            "Execution",
            "Order",
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

    def _snapshot(
        self,
        timestamp: str,
        decision: str,
        confidence: float,
        signals: list[LiveResearchSignalRecord] | None = None,
    ) -> LiveResearchSnapshotRecord:
        return LiveResearchSnapshotRecord(
            timestamp=timestamp,
            symbol="EURUSD",
            timeframe="H1",
            decision=decision,
            confidence=confidence,
            strategy_signals=1,
            decision_contexts=1,
            signals=signals or [],
        )

    def _signal(
        self,
        strategy_name: str,
        decision: str,
        confidence: float,
    ) -> LiveResearchSignalRecord:
        return LiveResearchSignalRecord(
            strategy_name=strategy_name,
            decision=decision,
            confidence=confidence,
        )


if __name__ == "__main__":
    unittest.main()
