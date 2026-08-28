"""Model 28 promotion, live tracking and execution-boundary regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import replace
import inspect

from application.model28_pattern_miner_shadow import (
    MODEL_28_SOURCE,
    MODEL_28_VOLUME,
    Model28LiveSelection,
    Model28ShadowRuntime,
    model28_parameters,
)
from application.dashboard_service import DashboardService
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.mt5_demo_robot_service import MT5DemoRobotService, MT5DemoRobotSignal, MT5DemoTradePlan
from application.demo_execution_service import DemoExecutionService
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
    is_shadow_operational_model,
    operational_model_number,
)
from domain.operational_pattern import (
    OperationalPatternStatus,
    ShadowStatus,
    SignalCandidate,
)
from replay.pattern_miner.models import EventRecord, MarketEvent, PatternRanking
from replay.pattern_miner.operational import (
    MODEL_28_ID,
    LivePatternEngine,
    LivePatternTracker,
    OperationalPatternStore,
    PatternPromotionValidator,
    ShadowSignalJournal,
)
from replay.pattern_miner.config import PatternMinerConfig
from replay.pattern_miner.detectors import CausalEventDetector
from replay.pattern_miner.indicators import IndicatorEngine
from replay.pattern_miner.models import CandleBar
from research.mt5_research_trade_plan import MT5ResearchTradePlan


def _ranking(
    *,
    pattern_id: str = "PAT-ABC123",
    sequence: tuple[str, ...] = ("SWEEP_LOW", "BOS_UP"),
    gaps: tuple[str, ...] = ("1-2 candles",),
) -> PatternRanking:
    return PatternRanking(
        pattern_id=pattern_id,
        sequence=sequence,
        gap_buckets=gaps,
        direction=1,
        occurrences=120,
        frequency=0.12,
        mfe_mean_atr=1.8,
        mfe_median_atr=1.5,
        mae_mean_atr=0.7,
        mae_median_atr=0.6,
        return_mean_atr=0.4,
        return_median_atr=0.3,
        first_passage_1_atr=0.66,
        first_passage_2_atr=0.58,
        expectancy=0.35,
        discovery_performance=0.40,
        validation_performance=0.31,
        oos_performance=0.29,
        score=0.27,
    )


def _record(index: int, *events: MarketEvent) -> EventRecord:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=5 * index)
    return EventRecord(
        index=index,
        timestamp=timestamp,
        open=100.0,
        high=102.0,
        low=99.0,
        close=101.0,
        volume=100.0,
        spread=2.0,
        real_volume=0.0,
        ema9=100.5,
        ema20=100.0,
        ema50=99.0,
        ema200=95.0,
        rsi14=55.0,
        atr14=2.0,
        adx14=28.0,
        plus_di14=25.0,
        minus_di14=15.0,
        volume_average=90.0,
        volume_relative=1.1,
        volume_zscore=0.5,
        volume_percentile=0.7,
        trend_state="bullish",
        structure_state="bullish",
        warmup_complete=True,
        session="London",
        events=events,
    )


def _event(event_type: str, index: int, direction: int = 1) -> MarketEvent:
    return MarketEvent(
        event_type=event_type,
        index=index,
        origin_index=index,
        direction=direction,
    )


def test_manual_promotion_is_versioned_persistent_and_idempotent(tmp_path) -> None:
    store = OperationalPatternStore(tmp_path / "patterns.json")
    first = store.promote(
        _ranking(),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-a",
    )
    repeated = store.promote(
        _ranking(),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-a",
    )
    second_version = store.promote(
        _ranking(),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-b",
    )

    assert first == repeated
    assert first.version == 1
    assert second_version.version == 2
    assert first.status == OperationalPatternStatus.OPERATIONAL_CANDIDATE
    assert first.shadow_status == ShadowStatus.OFF
    assert first.entry_rule == "MARKET_REFERENCE_ON_PATTERN_COMPLETION_CLOSE"
    assert first.stop_rule == "REPLAY_FIRST_PASSAGE_MINUS_1_ATR"
    assert first.target_atr == 2.0
    assert len(store.load()) == 2


def test_pattern_validator_requires_positive_validation_and_oos() -> None:
    failures = PatternPromotionValidator().validate(
        replace(_ranking(), oos_performance=-0.1)
    )
    assert failures == ("OOS_NOT_POSITIVE",)


def test_shadow_tracker_generates_signal_only_after_exact_sequence(tmp_path) -> None:
    store = OperationalPatternStore(tmp_path / "patterns.json")
    spec = store.promote(
        _ranking(),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-a",
    )
    spec = store.set_shadow(spec.versioned_id, True)
    tracker = LivePatternTracker((spec,))

    assert tracker.consume(_record(210, _event("SWEEP_LOW", 210))) == ()
    signals = tracker.consume(_record(211, _event("BOS_UP", 211)))

    assert len(signals) == 1
    signal = signals[0]
    assert signal.status == "SHADOW_SIGNAL"
    assert signal.direction == "BUY"
    assert signal.entry_reference == 101.0
    assert signal.stop_reference == 99.0
    assert signal.target_reference == 105.0
    assert signal.events_confirmed == ("SWEEP_LOW", "BOS_UP")


def test_shadow_tracker_rejects_wrong_gap_and_expired_occurrence(tmp_path) -> None:
    store = OperationalPatternStore(tmp_path / "patterns.json")
    spec = store.promote(
        _ranking(),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-a",
    )
    spec = store.set_shadow(spec.versioned_id, True)
    tracker = LivePatternTracker((spec,))

    tracker.consume(_record(210, _event("SWEEP_LOW", 210)))
    assert tracker.consume(_record(213, _event("BOS_UP", 213))) == ()
    tracker.consume(_record(220, _event("SWEEP_LOW", 220)))
    assert tracker.consume(_record(240, _event("BOS_UP", 240))) == ()


def test_multiple_shadow_specs_are_tracked_independently(tmp_path) -> None:
    store = OperationalPatternStore(tmp_path / "patterns.json")
    one = store.promote(
        _ranking(), symbol="XAUUSD", timeframe="M5",
        max_event_distance=12, source_cache_key="cache-a",
    )
    two = store.promote(
        _ranking(
            pattern_id="PAT-SECOND",
            sequence=("FVG_UP", "ADX_HIGH"),
            gaps=("same candle",),
        ),
        symbol="XAUUSD", timeframe="M5",
        max_event_distance=12, source_cache_key="cache-a",
    )
    one = store.set_shadow(one.versioned_id, True)
    two = store.set_shadow(two.versioned_id, True)
    tracker = LivePatternTracker((one, two))

    signals = tracker.consume(
        _record(210, _event("FVG_UP", 210), _event("ADX_HIGH", 210, 0))
    )
    assert [item.setup_id for item in signals] == [two.setup_id]
    assert tracker.state_label(one.versioned_id) == "WAITING_SWEEP_LOW"


def test_model28_is_demo_adaptive_and_active_for_execution() -> None:
    parameters = model28_parameters()
    assert parameters["model_id"] == MODEL_28_ID
    assert parameters["execution_mode"] == "DEMO_ADAPTIVE"
    assert parameters["execution_volume"] == 0.11
    assert parameters["can_send_orders"] is True
    assert parameters["real_account_allowed"] is False
    assert operational_model_number(MODEL_28_ID) == 28
    assert not is_shadow_operational_model(MODEL_28_ID)
    assert is_active_operational_model(MODEL_28_ID)
    assert not is_retired_operational_model(MODEL_28_ID)


def test_model28_pattern_runtime_has_no_direct_provider_dependency() -> None:
    import application.model28_pattern_miner_shadow as contract_module
    import replay.pattern_miner.operational as operational_module

    source = inspect.getsource(contract_module) + inspect.getsource(operational_module)
    assert "order_send" not in source
    assert "DemoExecutionService" not in source
    assert "mt5_demo_execution_provider" not in source


def test_model28_materializes_valid_demo_plan_from_live_selection() -> None:
    selection = Model28LiveSelection(
        versioned_id="XAU_PAT_TEST_v1",
        pattern_id="PAT-TEST",
        direction="BUY",
        selected_at="2026-08-28T12:00:00+00:00",
        confidence=0.42,
        validation_performance=0.31,
        oos_performance=0.27,
        valid_until_index=220,
        occurrence_id="occurrence-123",
        symbol="XAUUSD",
        timeframe="M5",
        entry_reference=3400.0,
        stop_reference=3395.0,
        target_reference=3410.0,
        reason="Padrao causal concluido.",
    )
    service = object.__new__(DashboardService)
    object.__setattr__(service, "get_model28_live_selection", lambda: selection)
    fallback = MT5ResearchTradePlan(
        symbol="XAUUSD", timeframe="M5", direction="WAIT", entry_price=None,
        stop=None, target=None, risk_reward=0.0, stop_multiplier=0.0,
        exit_model="NONE", exit_score=0.0, exit_candidates=0, status="SEM_PLANO",
    )

    row, plan = service._mt5_model28_adaptive_plan(
        DashboardMT5ForexSignalRowViewModel(pair="XAUUSD", timeframe="M5"),
        fallback,
    )

    assert row.decision == "BUY"
    assert row.theoretical_entry_status == "SINAL_TEORICO"
    assert plan.status == "PLANO_VALIDO"
    assert plan.source == MODEL_28_SOURCE
    assert plan.entry_price == 3400.0
    assert plan.stop == 3395.0
    assert plan.target == 3410.0
    assert plan.stop_management_parameters["setup_id"] == "M28:occurrence-123"


def test_model28_uses_contract_volume_and_bypasses_legacy_regime() -> None:
    service = MT5DemoRobotService()
    signal = MT5DemoRobotSignal(
        symbol="XAUUSD",
        timeframe="M5",
        candle_time="2026-08-28T12:00:00+00:00",
        decision="BUY",
        confidence=0.42,
        active_model="M28_ADAPTIVE_PAT_TEST",
        reason="Padrao causal concluido.",
        operational_model=MODEL_28_ID,
    )
    plan = MT5DemoTradePlan(
        symbol="XAUUSD",
        timeframe="M5",
        entry_price=3400.0,
        stop=3395.0,
        target=3410.0,
        risk_reward=2.0,
        source=MODEL_28_SOURCE,
        status="PLANO_VALIDO",
        stop_management_parameters={"execution_volume": MODEL_28_VOLUME},
        operational_model=MODEL_28_ID,
    )

    assert service._regime_validation_signal(signal) is None
    assert service._execution_volume(signal, plan) == 0.11


def test_model28_reaches_demo_execution_with_frozen_geometry() -> None:
    class AcceptingProvider:
        def __init__(self) -> None:
            self.orders: list[ExecutionOrder] = []

        def has_open_position(self, symbol: str) -> bool:
            return False

        def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
            self.orders.append(order)
            return ExecutionResult(True, "ACCEPTED", "demo", ticket=28)

    provider = AcceptingProvider()
    service = MT5DemoRobotService(
        execution_service=DemoExecutionService(provider=provider),
        enabled=True,
    )
    signal = MT5DemoRobotSignal(
        symbol="XAUUSD",
        timeframe="M5",
        candle_time="2026-08-28T12:00:00+00:00",
        decision="SELL",
        confidence=0.51,
        active_model="M28_ADAPTIVE_PAT_TEST",
        reason="Padrao causal concluido.",
        entry_route="ADAPTIVE_PATTERN",
        setup_id="M28:occurrence-456",
        operational_model=MODEL_28_ID,
    )
    plan = MT5DemoTradePlan(
        symbol="XAUUSD",
        timeframe="M5",
        entry_price=3400.0,
        stop=3405.0,
        target=3390.0,
        risk_reward=2.0,
        source=MODEL_28_SOURCE,
        status="PLANO_VALIDO",
        stop_management_parameters={
            "execution_volume": MODEL_28_VOLUME,
            "setup_id": "M28:occurrence-456",
        },
        operational_model=MODEL_28_ID,
    )

    result = service.evaluate_once(signal, plan)

    assert result.status == "EXECUTED"
    assert len(provider.orders) == 1
    order = provider.orders[0]
    assert order.quantity == 0.11
    assert order.side == "SELL"
    assert order.entry_price == 3400.0
    assert order.stop == 3405.0
    assert order.target == 3390.0
    assert order.plan_snapshot["setup_id"] == "M28:occurrence-456"


def test_live_engine_matches_replay_event_engine_on_same_closed_candles() -> None:
    config = PatternMinerConfig(warmup_candles=20)
    candles = []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index in range(80):
        base = 100.0 + index * 0.08 + (0.7 if index % 7 == 0 else 0.0)
        close = base + (0.35 if index % 3 else -0.2)
        candles.append(
            CandleBar(
                index=index,
                timestamp=start + timedelta(minutes=5 * index),
                open=base,
                high=max(base, close) + 0.4,
                low=min(base, close) - 0.4,
                close=close,
                volume=100.0 + index,
                spread=2.0,
                real_volume=0.0,
            )
        )

    frame = IndicatorEngine(config).compute(candles)
    replay_detector = CausalEventDetector(config)
    expected = [
        replay_detector.process(index, candles, frame)
        for index in range(len(candles))
    ]
    live = LivePatternEngine(config)
    actual = [live.consume_closed_candle(candle)[0] for candle in candles]

    assert actual == expected


def test_shadow_journal_records_and_evaluates_hypothetical_result(tmp_path) -> None:
    journal = ShadowSignalJournal(tmp_path / "shadow.json")
    opened = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    signal = SignalCandidate(
        setup_id="XAU_PAT_TEST",
        setup_version=1,
        symbol="XAUUSD",
        timeframe="M5",
        datetime=opened,
        direction="BUY",
        entry_reference=100.0,
        stop_reference=99.0,
        target_reference=102.0,
        confidence=0.3,
        pattern_occurrence_id="occ-1",
        events_confirmed=("SWEEP_LOW", "BOS_UP"),
        context_snapshot=(("atr14", 1.0),),
    )
    journal.record((signal,))
    rows = journal.evaluate(
        CandleBar(
            index=1,
            timestamp=opened + timedelta(minutes=5),
            open=100.5,
            high=102.2,
            low=100.0,
            close=102.0,
            volume=100.0,
            spread=2.0,
            real_volume=0.0,
        )
    )

    assert len(rows) == 1
    assert rows[0].status == "TARGET"
    assert rows[0].result_r == 2.0


def test_live_adaptive_selector_uses_strongest_validated_pattern(tmp_path) -> None:
    registry = tmp_path / "patterns.json"
    store = OperationalPatternStore(registry)
    weaker = store.promote(
        _ranking(pattern_id="PAT-WEAKER"),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-a",
    )
    stronger = store.promote(
        replace(
            _ranking(pattern_id="PAT-STRONGER"),
            score=0.51,
            validation_performance=0.44,
            oos_performance=0.41,
        ),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-a",
    )
    weaker = store.set_shadow(weaker.versioned_id, True)
    stronger = store.set_shadow(stronger.versioned_id, True)
    runtime = Model28ShadowRuntime(
        registry_path=registry,
        journal_path=tmp_path / "shadow.json",
    )
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    signals = (
        SignalCandidate(
            setup_id=weaker.setup_id,
            setup_version=weaker.version,
            symbol="XAUUSD",
            timeframe="M5",
            datetime=timestamp,
            direction="BUY",
            entry_reference=100.0,
            stop_reference=99.0,
            target_reference=102.0,
            confidence=weaker.minimum_score,
            pattern_occurrence_id="weak-occurrence",
            events_confirmed=weaker.event_sequence,
            context_snapshot=(),
        ),
        SignalCandidate(
            setup_id=stronger.setup_id,
            setup_version=stronger.version,
            symbol="XAUUSD",
            timeframe="M5",
            datetime=timestamp,
            direction="BUY",
            entry_reference=100.0,
            stop_reference=99.0,
            target_reference=102.0,
            confidence=stronger.minimum_score,
            pattern_occurrence_id="strong-occurrence",
            events_confirmed=stronger.event_sequence,
            context_snapshot=(),
        ),
    )

    runtime._update_selection(_record(220), signals)

    selected = runtime.live_selection()
    assert selected is not None
    assert selected.pattern_id == "PAT-STRONGER"
    assert selected.versioned_id == stronger.versioned_id
    assert selected.oos_performance == 0.41
    assert "score, validacao e OOS" in selected.reason


def test_live_candle_sync_does_not_process_same_closed_candle_twice(tmp_path) -> None:
    registry = tmp_path / "patterns.json"
    store = OperationalPatternStore(registry)
    spec = store.promote(
        _ranking(),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-a",
    )
    store.set_shadow(spec.versioned_id, True)
    runtime = Model28ShadowRuntime(
        registry_path=registry,
        journal_path=tmp_path / "shadow.json",
        config=PatternMinerConfig(warmup_candles=20),
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        {
            "time": int((start + timedelta(minutes=5 * index)).timestamp()),
            "open": 100.0 + index * 0.1,
            "high": 100.8 + index * 0.1,
            "low": 99.5 + index * 0.1,
            "close": 100.4 + index * 0.1,
            "tick_volume": 100 + index,
            "spread": 2,
            "real_volume": 0,
        }
        for index in range(40)
    ]

    runtime.synchronize_mt5_closed_candles(rows)
    first_count = len(runtime.engine.candles)
    runtime.synchronize_mt5_closed_candles(rows)

    assert first_count == 40
    assert len(runtime.engine.candles) == first_count
