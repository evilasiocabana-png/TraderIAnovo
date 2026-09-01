"""Model 28 promotion, live tracking and execution-boundary regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import replace
import inspect
import json

from application.model28_pattern_miner_shadow import (
    MODEL_28_BETA_ID,
    MODEL_28_SOURCE,
    MODEL_28_STOP_MANAGEMENT,
    MODEL_28_VOLUME,
    Model28LiveSelection,
    Model28ShadowRuntime,
    model28_parameters,
    synchronize_model28_replay_contracts,
)
from application.position_manager_service import (
    PositionManagerService,
    PositionStateSnapshot,
    PositionTradePlan,
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
from domain.market_universe import MT5_RESEARCH_MARKETS
from domain.operational_pattern import (
    OperationalPatternStatus,
    ShadowStatus,
    SignalCandidate,
)
from replay.pattern_miner.models import (
    EventRecord,
    MarketEvent,
    PatternOccurrence,
    PatternRanking,
)
from replay.pattern_miner.operational import (
    MODEL_28_CONTRACT_VERSION,
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
from scripts.analyze_model28_geometry_context import (
    _TradeSample,
    _empirical_geometry_candidates,
    _recommended_repeat_limit,
    _repeat_profile,
)


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
        first_passage_1_expectancy_net=0.18,
        first_passage_2_expectancy_net=0.24,
        fp1_discovery_net=0.14,
        fp1_validation_net=0.11,
        fp1_oos_net=0.09,
        fp2_discovery_net=0.19,
        fp2_validation_net=0.16,
        fp2_oos_net=0.12,
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


def _v6_spec(spec, *, evidence_tier: str = "VALIDATED", rank: int = 1):
    return replace(
        spec,
        contract_version=MODEL_28_CONTRACT_VERSION,
        evidence_tier=evidence_tier,
        adaptive_rank=rank,
        pattern_family="BUY:STRUCTURE",
        selection_score=0.27,
        repeat_limit=1,
        repeat_window_candles=100,
        repeat_probability=0.5,
        repeat_basis="MEDIAN_REACH_50_WITH_ROBUST_POSITIVE_POSITION_EXPECTANCY",
        source_cache_key=f"100k-empirical:{spec.pattern_id.lower()}",
        stop_rule="DISCOVERY_MAE_Q50_ATR",
        target_rule="DISCOVERY_MFE_Q35_ATR",
        expiration_rule="FULL_EXIT_AFTER_20_M5_CANDLES",
        stop_atr=1.25,
        target_atr=1.75,
        max_holding_candles=20,
        cost_rule="RECORDED_ENTRY_SPREAD_ONLY",
        geometry_method="PATTERN_DISCOVERY_EMPIRICAL_MAE_MFE",
        geometry_statistics=(
            ("stop_quantile", 0.50),
            ("target_quantile", 0.35),
        ),
        minimum_occurrences=max(int(spec.minimum_occurrences), 120),
        discovery_metrics=(("performance", 0.40), ("horizon_return_atr", 0.40)),
        validation_metrics=(("performance", 0.31), ("horizon_return_atr", 0.31)),
        oos_metrics=(("performance", 0.29), ("horizon_return_atr", 0.29)),
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
    assert first.entry_rule == "MARKET_ON_NEXT_BAR_AFTER_PATTERN_COMPLETION"
    assert first.stop_rule == "REPLAY_FIRST_PASSAGE_MINUS_1_ATR"
    assert first.target_atr == 2.0
    assert len(store.load()) == 2


def test_pattern_validator_rejects_when_no_target_survives_oos() -> None:
    failures = PatternPromotionValidator().validate(
        replace(_ranking(), fp1_oos_net=-0.1, fp2_oos_net=-0.1)
    )
    assert failures == ("NET_SPLIT_EXPECTANCY_TOO_LOW",)


def test_pattern_validator_requires_a_large_independent_sample() -> None:
    failures = PatternPromotionValidator().validate(
        replace(_ranking(), occurrences=99)
    )
    assert failures == ("INSUFFICIENT_OCCURRENCES",)


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


def test_empirical_tracker_requires_context_and_uses_pattern_geometry(tmp_path) -> None:
    store = OperationalPatternStore(tmp_path / "patterns.json")
    legacy = store.promote(
        _ranking(),
        symbol="AUDJPY",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-v4",
    )
    spec = replace(
        legacy,
        symbol="AUDJPY",
        context_filters=(("session", "Asia"), ("trend", "COUNTER"), ("adx", "MID")),
        stop_atr=2.0,
        target_atr=4.0,
        stop_rule="REPLAY_FIRST_PASSAGE_MINUS_2_ATR",
        target_rule="REPLAY_FIRST_PASSAGE_PLUS_4_ATR",
        contract_version=MODEL_28_CONTRACT_VERSION,
        evidence_tier="VALIDATED",
        shadow_status=ShadowStatus.RUNNING,
    )

    wrong_context = LivePatternTracker((spec,))
    wrong_context.consume(_record(210, _event("SWEEP_LOW", 210)))
    assert wrong_context.consume(_record(211, _event("BOS_UP", 211))) == ()

    matching_context = LivePatternTracker((spec,))
    matching_context.consume(_record(220, _event("SWEEP_LOW", 220)))
    completion = replace(
        _record(221, _event("BOS_UP", 221)),
        session="Asia",
        trend_state="bearish",
    )
    signals = matching_context.consume(completion)

    assert len(signals) == 1
    assert signals[0].entry_reference == 101.0
    assert signals[0].stop_reference == 97.0
    assert signals[0].target_reference == 109.0


def test_runtime_rejects_running_legacy_contract_and_accepts_v6(tmp_path) -> None:
    registry = tmp_path / "patterns.json"
    journal = tmp_path / "shadow.json"
    store = OperationalPatternStore(registry)
    legacy = store.promote(
        _ranking(),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-legacy",
    )
    legacy = store.set_shadow(legacy.versioned_id, True)

    assert not Model28ShadowRuntime(registry, journal).has_active_specs()

    v6 = replace(
        _v6_spec(legacy),
        stop_atr=2.0,
        target_atr=4.0,
    )
    store.save((v6,))

    assert Model28ShadowRuntime(registry, journal).has_active_specs()


def test_replay_approved_contract_activates_demo_without_forward_gate(tmp_path) -> None:
    report = tmp_path / "empirical_pattern_contracts_v6.json"
    registry = tmp_path / "patterns.json"
    split = {
        "trades": 40,
        "expectancy_r": 0.42,
        "net_r": 16.8,
        "win_rate": 0.65,
        "target_rate": 0.60,
        "stop_rate": 0.35,
        "time_exit_rate": 0.05,
        "lower_80_expectancy_r": 0.12,
    }
    report.write_text(
        json.dumps(
            {
                "schema_version": "model28-empirical-pattern-contracts-v6-research",
                "operational_total": 1,
                "operational_contracts": [
                    {
                        "symbol": "AUDJPY",
                        "pattern_id": "PAT-REPLAY",
                        "context": {"session": "Asia", "trend": "COUNTER"},
                        "stop_atr": 2.0,
                        "target_atr": 4.0,
                        "rr": 2.0,
                        "max_holding_candles": 20,
                        "stop_quantile": 0.50,
                        "target_quantile": 0.35,
                        "entry_rule": "MARKET_ON_NEXT_BAR_AFTER_PATTERN_COMPLETION",
                        "stop_rule": "DISCOVERY_MAE_Q50_ATR",
                        "target_rule": "DISCOVERY_MFE_Q35_ATR",
                        "expiration_rule": "FULL_EXIT_AFTER_20_M5_CANDLES",
                        "geometry_method": "PATTERN_DISCOVERY_EMPIRICAL_MAE_MFE",
                        "cost_rule": "RECORDED_ENTRY_SPREAD_ONLY",
                        "events": ["SWEEP_LOW", "BOS_UP"],
                        "gaps": ["1-2 candles"],
                        "direction": "BUY",
                        "discovery": split,
                        "validation": split,
                        "oos": split,
                        "approved": True,
                        "operational_tier": "VALIDATED",
                        "robust_floor_r": 0.42,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    synchronized = synchronize_model28_replay_contracts(
        registry_path=registry,
        report_path=report,
    )
    runtime = Model28ShadowRuntime(
        registry_path=registry,
        journal_path=tmp_path / "shadow.json",
        research_report_path=report,
    )

    assert len(synchronized) == 1
    assert runtime.has_active_specs()
    assert runtime.active_markets() == (("AUDJPY", "M5"),)
    spec = OperationalPatternStore(registry).load()[-1]
    assert spec.contract_version == MODEL_28_CONTRACT_VERSION
    assert spec.shadow_status == ShadowStatus.RUNNING
    assert spec.stop_atr == 2.0
    assert spec.target_atr == 4.0
    assert dict(spec.context_filters)["session"] == "Asia"


def test_empirical_v6_activates_exploration_contract_for_all_19_markets(tmp_path) -> None:
    report = tmp_path / "empirical_pattern_contracts_v6.json"
    registry = tmp_path / "patterns.json"
    positive_discovery = {
        "trades": 40,
        "expectancy_r": 0.42,
        "net_r": 16.8,
        "win_rate": 0.65,
        "target_rate": 0.60,
        "stop_rate": 0.35,
        "time_exit_rate": 0.05,
        "lower_80_expectancy_r": 0.12,
    }
    negative_future = {
        "trades": 20,
        "expectancy_r": -0.10,
        "net_r": -2.0,
        "win_rate": 0.45,
        "target_rate": 0.40,
        "stop_rate": 0.55,
        "time_exit_rate": 0.05,
        "lower_80_expectancy_r": -0.20,
    }
    contracts = [
        {
            "symbol": symbol,
            "pattern_id": f"PAT-{index:012X}",
            "context": {},
            "stop_atr": 1.0,
            "target_atr": 1.3 + index / 100.0,
            "rr": 1.3 + index / 100.0,
            "max_holding_candles": 10,
            "stop_quantile": 0.65,
            "target_quantile": 0.50,
            "entry_rule": "MARKET_ON_NEXT_BAR_AFTER_PATTERN_COMPLETION",
            "stop_rule": "DISCOVERY_MAE_Q65_ATR",
            "target_rule": "DISCOVERY_MFE_Q50_ATR",
            "expiration_rule": "FULL_EXIT_AFTER_10_M5_CANDLES",
            "geometry_method": "PATTERN_DISCOVERY_EMPIRICAL_MAE_MFE",
            "cost_rule": "RECORDED_ENTRY_SPREAD_ONLY",
            "events": ["SWING_LOW", "HIGHER_LOW"],
            "gaps": ["same candle"],
            "direction": "BUY",
            "discovery": positive_discovery,
            "validation": negative_future,
            "oos": negative_future,
            "approved": False,
            "operational_tier": "EXPLORATION_DEMO",
            "adaptive_rank": 1,
            "pattern_family": "BUY:STRUCTURE",
            "adaptive_score": 0.08,
            "selection_confidence": 0.35,
            "robust_floor_r": -0.10,
            "repeat_limit": 2,
            "repeat_window_candles": 100,
            "repeat_probability": 0.6,
            "repeat_basis": (
                "MEDIAN_REACH_50_WITH_ROBUST_POSITIVE_POSITION_EXPECTANCY"
            ),
            "repeat_analysis": {
                "all": {
                    "episodes": 100,
                    "length_counts": {
                        "1": 40,
                        "2": 35,
                        "3": 20,
                        "4": 5,
                        "5_plus": 0,
                    },
                    "modal_repeat_count": 1,
                    "median_repeat_count": 2,
                    "pair_or_more_probability": 0.6,
                    "triple_or_more_probability": 0.25,
                    "positions": {
                        "1": {
                            "trades": 100,
                            "expectancy_r": 0.10,
                            "lower_80_expectancy_r": 0.05,
                            "reach_probability": 1.0,
                            "continuation_probability": 1.0,
                        },
                        "2": {
                            "trades": 60,
                            "expectancy_r": 0.08,
                            "lower_80_expectancy_r": 0.02,
                            "reach_probability": 0.6,
                            "continuation_probability": 0.6,
                        },
                    },
                }
            },
        }
        for index, symbol in enumerate(MT5_RESEARCH_MARKETS, start=1)
    ]
    report.write_text(
        json.dumps(
            {
                "schema_version": "model28-empirical-pattern-contracts-v6-research",
                "operational_total": len(contracts),
                "operational_market_total": len(MT5_RESEARCH_MARKETS),
                "operational_contracts": contracts,
            }
        ),
        encoding="utf-8",
    )

    synchronized = synchronize_model28_replay_contracts(
        registry_path=registry,
        report_path=report,
    )
    runtime = Model28ShadowRuntime(
        registry_path=registry,
        journal_path=tmp_path / "shadow.json",
        research_report_path=report,
    )

    assert len(synchronized) == len(MT5_RESEARCH_MARKETS) == 19
    assert {symbol for symbol, _ in runtime.active_markets()} == set(
        MT5_RESEARCH_MARKETS
    )
    assert all(item.evidence_tier == "EXPLORATION_DEMO" for item in synchronized)
    assert all(item.shadow_status == ShadowStatus.RUNNING for item in synchronized)
    assert all(item.repeat_limit == 2 for item in synchronized)
    assert all(dict(item.repeat_statistics)["pairs"] == 35 for item in synchronized)


def test_exploration_pattern_sends_on_first_completed_occurrence(tmp_path) -> None:
    store = OperationalPatternStore(tmp_path / "patterns.json")
    promoted = store.promote(
        _ranking(),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-a",
    )
    spec = _v6_spec(
        store.set_shadow(promoted.versioned_id, True),
        evidence_tier="EXPLORATION_DEMO",
    )
    spec = replace(
        spec,
        validation_metrics=(("performance", -0.1), ("horizon_return_atr", -0.1)),
        oos_metrics=(("performance", -0.2), ("horizon_return_atr", -0.2)),
    )
    store.save((spec,))
    runtime = Model28ShadowRuntime(
        registry_path=store.path,
        journal_path=tmp_path / "shadow.json",
        auto_activate_replay_contracts=False,
    )

    runtime.engine.tracker.consume(_record(210, _event("SWEEP_LOW", 210)))
    signals = runtime.engine.tracker.consume(_record(211, _event("BOS_UP", 211)))

    assert runtime.has_active_specs()
    assert len(signals) == 1
    assert signals[0].pattern_occurrence_id


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
    assert parameters["automatic_replay_promotion"] is True
    assert parameters["adaptive_demo_portfolio"] is True
    assert parameters["exploration_contracts_can_send_demo"] is True
    assert parameters["forward_validation_blocks_demo"] is False
    assert parameters["first_occurrence_always_eligible"] is True
    assert parameters["repeat_limit_is_historical"] is True
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


def test_model28_reanchors_learned_distances_on_next_live_price() -> None:
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
        stop_rule="DISCOVERY_MAE_Q50_ATR",
        target_rule="DISCOVERY_MFE_Q35_ATR",
        expiration_rule="FULL_EXIT_AFTER_20_M5_CANDLES",
        max_holding_candles=20,
        cost_rule="RECORDED_ENTRY_SPREAD_ONLY",
        stop_atr=1.25,
        target_atr=2.50,
        geometry_method="PATTERN_DISCOVERY_EMPIRICAL_MAE_MFE",
    )
    service = object.__new__(DashboardService)
    object.__setattr__(service, "get_model28_live_selection", lambda: selection)
    fallback = MT5ResearchTradePlan(
        symbol="XAUUSD", timeframe="M5", direction="WAIT", entry_price=None,
        stop=None, target=None, risk_reward=0.0, stop_multiplier=0.0,
        exit_model="NONE", exit_score=0.0, exit_candidates=0, status="SEM_PLANO",
    )

    row, plan = service._mt5_model28_adaptive_plan(
        DashboardMT5ForexSignalRowViewModel(
            pair="XAUUSD",
            timeframe="M5",
            last_price=3402.0,
        ),
        fallback,
    )

    assert row.decision == "BUY"
    assert row.theoretical_entry_status == "SINAL_TEORICO"
    assert plan.status == "PLANO_VALIDO"
    assert plan.source == MODEL_28_SOURCE
    assert plan.entry_price == 3402.0
    assert plan.stop == 3397.0
    assert plan.target == 3412.0
    assert plan.stop_management_parameters["setup_id"] == "M28:occurrence-123"
    assert plan.stop_management_parameters["max_holding_candles"] == 20
    assert plan.stop_management_parameters["live_entry_reanchored"] is True
    assert plan.beta_mode == "EMPIRICAL_PATTERN_CONTRACT"


def test_model28_position_manager_holds_until_empirical_horizon() -> None:
    manager = PositionManagerService(assisted_execution_enabled=True)
    plan = PositionTradePlan(
        symbol="XAUUSD",
        side="BUY",
        entry=3400.0,
        stop=3395.0,
        target=3410.0,
        stop_management=MODEL_28_STOP_MANAGEMENT,
        stop_management_parameters={
            "contract_version": MODEL_28_CONTRACT_VERSION,
            "geometry_method": "PATTERN_DISCOVERY_EMPIRICAL_MAE_MFE",
            "expiration_rule": "FULL_EXIT_AFTER_20_M5_CANDLES",
            "max_holding_candles": 20,
        },
        beta_id=MODEL_28_BETA_ID,
        operational_model=MODEL_28_ID,
        timeframe="M5",
    )
    snapshot = PositionStateSnapshot(
        symbol="XAUUSD",
        ticket=28001,
        side="BUY",
        volume=0.11,
        entry_price=3400.0,
        current_price=3403.0,
        current_stop=3395.0,
        current_target=3410.0,
        r_multiple=0.6,
        distance_to_target_r=1.4,
        time_in_position_minutes=99.9,
        atr=4.0,
        momentum=None,
        volatility=None,
        spread=None,
        state="IN_PROGRESS",
    )

    decision = manager._decide(plan, snapshot)

    assert decision.action == "HOLD_POSITION"
    assert decision.state == "M28_EMPIRICAL_CONTRACT_ACTIVE"


def test_model28_position_manager_full_exits_at_empirical_horizon() -> None:
    manager = PositionManagerService(assisted_execution_enabled=True)
    plan = PositionTradePlan(
        symbol="XAUUSD",
        side="SELL",
        entry=3400.0,
        stop=3405.0,
        target=3390.0,
        stop_management=MODEL_28_STOP_MANAGEMENT,
        stop_management_parameters={
            "contract_version": MODEL_28_CONTRACT_VERSION,
            "geometry_method": "PATTERN_DISCOVERY_EMPIRICAL_MAE_MFE",
            "expiration_rule": "FULL_EXIT_AFTER_10_M5_CANDLES",
            "max_holding_candles": 10,
        },
        beta_id=MODEL_28_BETA_ID,
        operational_model=MODEL_28_ID,
        timeframe="M5",
    )
    snapshot = PositionStateSnapshot(
        symbol="XAUUSD",
        ticket=28002,
        side="SELL",
        volume=0.11,
        entry_price=3400.0,
        current_price=3398.0,
        current_stop=3405.0,
        current_target=3390.0,
        r_multiple=0.4,
        distance_to_target_r=1.6,
        time_in_position_minutes=50.0,
        atr=4.0,
        momentum=None,
        volatility=None,
        spread=None,
        state="IN_PROGRESS",
    )

    decision = manager._decide(plan, snapshot)

    assert decision.action == "FULL_EXIT"
    assert decision.state == "M28_EMPIRICAL_TIME_EXIT"
    assert decision.allowed_to_execute is True
    assert decision.requested_close_volume == 0.11


def test_model28_position_manager_rejects_incomplete_expiration_contract() -> None:
    manager = PositionManagerService(assisted_execution_enabled=True)
    plan = PositionTradePlan(
        symbol="XAUUSD",
        side="BUY",
        entry=3400.0,
        stop=3395.0,
        target=3410.0,
        stop_management=MODEL_28_STOP_MANAGEMENT,
        stop_management_parameters={"max_holding_candles": 5},
        operational_model=MODEL_28_ID,
    )
    snapshot = PositionStateSnapshot(
        symbol="XAUUSD",
        ticket=28003,
        side="BUY",
        volume=0.11,
        entry_price=3400.0,
        current_price=3401.0,
        current_stop=3395.0,
        current_target=3410.0,
        r_multiple=0.2,
        distance_to_target_r=1.8,
        time_in_position_minutes=500.0,
        atr=None,
        momentum=None,
        volatility=None,
        spread=None,
        state="IN_PROGRESS",
    )

    decision = manager._decide(plan, snapshot)

    assert decision.action == "HOLD_POSITION"
    assert decision.state == "M28_EMPIRICAL_CONTRACT_INVALID"


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


def test_v6_shadow_reanchors_next_bar_and_uses_empirical_time_exit(tmp_path) -> None:
    journal = ShadowSignalJournal(tmp_path / "shadow-v6.json")
    opened = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    signal = SignalCandidate(
        setup_id="XAU_PAT_EMPIRICAL",
        setup_version=1,
        symbol="XAUUSD",
        timeframe="M5",
        datetime=opened,
        direction="BUY",
        entry_reference=100.0,
        stop_reference=99.0,
        target_reference=102.0,
        confidence=0.3,
        pattern_occurrence_id="occ-v6",
        events_confirmed=("SWEEP_LOW", "BOS_UP"),
        context_snapshot=(
            ("entry_rule", "MARKET_ON_NEXT_BAR_AFTER_PATTERN_COMPLETION"),
            ("max_holding_candles", 2),
            ("cost_rule", "RECORDED_ENTRY_SPREAD_ONLY"),
        ),
    )
    journal.record((signal,))
    journal.evaluate(
        CandleBar(
            index=1,
            timestamp=opened + timedelta(minutes=5),
            open=101.0,
            high=102.0,
            low=100.5,
            close=101.5,
            volume=100.0,
            spread=10.0,
            real_volume=0.0,
        )
    )
    rows = journal.evaluate(
        CandleBar(
            index=2,
            timestamp=opened + timedelta(minutes=10),
            open=101.5,
            high=102.5,
            low=101.0,
            close=102.0,
            volume=100.0,
            spread=8.0,
            real_volume=0.0,
        )
    )

    assert rows[0].entry_reference == 101.0
    assert rows[0].stop_reference == 100.0
    assert rows[0].target_reference == 103.0
    assert rows[0].status == "TIME_EXIT"
    assert rows[0].candles_observed == 2
    assert rows[0].cost_r == 0.1
    assert rows[0].result_r == 0.9


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
            fp2_validation_net=0.44,
            fp2_oos_net=0.41,
        ),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-a",
    )
    weaker = store.set_shadow(weaker.versioned_id, True)
    stronger = store.set_shadow(stronger.versioned_id, True)
    weaker = _v6_spec(weaker, rank=2)
    stronger = replace(
        _v6_spec(stronger, rank=1),
        selection_score=0.51,
        validation_metrics=(("performance", 0.44), ("horizon_return_atr", 0.44)),
        oos_metrics=(("performance", 0.41), ("horizon_return_atr", 0.41)),
    )
    store.save((weaker, stronger))
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
    assert "tier e ranking" in selected.reason


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
    spec = _v6_spec(store.set_shadow(spec.versioned_id, True))
    store.save((spec,))
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


def test_repeat_profile_identifies_pairs_and_positive_second_entry() -> None:
    samples: list[_TradeSample] = []
    for episode_start in range(0, 3000, 300):
        samples.extend(
            (
                _TradeSample(episode_start, episode_start + 5, 1.0, "TARGET"),
                _TradeSample(episode_start + 20, episode_start + 25, 0.5, "TARGET"),
            )
        )

    profile = _repeat_profile(samples)

    assert profile["length_counts"]["2"] == 10
    assert profile["modal_repeat_count"] == 2
    assert profile["median_repeat_count"] == 2
    assert profile["pair_or_more_probability"] == 1.0
    assert profile["triple_or_more_probability"] == 0.0
    assert _recommended_repeat_limit(profile) == 2


def test_empirical_geometry_changes_with_each_pattern_path_distribution() -> None:
    def sample(adverse: float, favorable: float):
        occurrence_count = 60
        spacing = 110
        total = occurrence_count * spacing + 102
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        candles = [
            CandleBar(
                index=index,
                timestamp=start + timedelta(minutes=5 * index),
                open=100.0,
                high=100.0,
                low=100.0,
                close=100.0,
                volume=100.0,
                spread=2.0,
                real_volume=0.0,
            )
            for index in range(total)
        ]
        records = [_record(index) for index in range(total)]
        occurrences = []
        for number in range(occurrence_count):
            end_index = number * spacing
            entry_index = end_index + 1
            candles[entry_index] = replace(
                candles[entry_index],
                high=100.0 + favorable,
                low=100.0 - adverse,
            )
            occurrences.append(
                PatternOccurrence(
                    pattern_id="PAT-EMPIRICAL",
                    sequence=("SWEEP_LOW", "BOS_UP"),
                    gap_buckets=("1-2 candles",),
                    direction=1,
                    start_index=end_index,
                    end_index=end_index,
                    event_indices=(end_index, end_index),
                    split="DISCOVERY",
                )
            )
        return occurrences, candles, records

    calm = _empirical_geometry_candidates(*sample(1.0, 2.0))
    volatile = _empirical_geometry_candidates(*sample(4.0, 8.0))

    assert calm
    assert volatile
    assert {item.stop_atr for item in calm} == {0.5}
    assert {item.target_atr for item in calm} == {1.0}
    assert {item.stop_atr for item in volatile} == {2.0}
    assert {item.target_atr for item in volatile} == {4.0}


def test_repeat_limit_uses_reach_probability_instead_of_split_length_mode() -> None:
    samples: list[_TradeSample] = []
    episode = 0
    for length, quantity in ((1, 12), (2, 7), (3, 6)):
        for _ in range(quantity):
            start = episode * 300
            samples.extend(
                _TradeSample(
                    start + position * 20,
                    start + position * 20 + 5,
                    0.5,
                    "TARGET",
                )
                for position in range(length)
            )
            episode += 1

    profile = _repeat_profile(samples)

    assert profile["length_counts"] == {
        "1": 12,
        "2": 7,
        "3": 6,
        "4": 0,
        "5_plus": 0,
    }
    assert profile["modal_repeat_count"] == 1
    assert profile["median_repeat_count"] == 2
    assert profile["pair_or_more_probability"] == 13 / 25
    assert _recommended_repeat_limit(profile) == 2


def test_repeat_profile_resets_episode_after_real_time_market_gap() -> None:
    friday = datetime(2026, 8, 28, 21, 55, tzinfo=timezone.utc)
    monday = datetime(2026, 8, 31, 0, 5, tzinfo=timezone.utc)

    profile = _repeat_profile(
        (
            _TradeSample(100, 105, 0.5, "TARGET", friday),
            _TradeSample(101, 106, 0.5, "TARGET", monday),
        )
    )

    assert profile["episodes"] == 2
    assert profile["length_counts"]["1"] == 2
    assert profile["pair_or_more_probability"] == 0.0


def test_runtime_limits_same_pattern_to_historical_repeat_quota(tmp_path) -> None:
    registry = tmp_path / "patterns.json"
    journal_path = tmp_path / "shadow.json"
    store = OperationalPatternStore(registry)
    promoted = store.promote(
        _ranking(),
        symbol="XAUUSD",
        timeframe="M5",
        max_event_distance=12,
        source_cache_key="cache-a",
    )
    spec = replace(
        _v6_spec(store.set_shadow(promoted.versioned_id, True)),
        repeat_limit=2,
        repeat_window_candles=100,
    )
    store.save((spec,))
    runtime = Model28ShadowRuntime(
        registry_path=registry,
        journal_path=journal_path,
        auto_activate_replay_contracts=False,
    )

    def signal(index: int, occurrence: str) -> SignalCandidate:
        record = _record(index)
        return SignalCandidate(
            setup_id=spec.setup_id,
            setup_version=spec.version,
            symbol="XAUUSD",
            timeframe="M5",
            datetime=record.timestamp,
            direction="BUY",
            entry_reference=100.0,
            stop_reference=99.0,
            target_reference=102.0,
            confidence=0.5,
            pattern_occurrence_id=occurrence,
            events_confirmed=spec.event_sequence,
            context_snapshot=(),
        )

    first = signal(220, "occ-1")
    runtime.journal.record((first,))
    runtime._update_selection(_record(220), (first,))
    assert runtime.live_selection().repeat_position == 1

    second = signal(221, "occ-2")
    runtime.journal.record((second,))
    runtime._update_selection(_record(221), (second,))
    assert runtime.live_selection().repeat_position == 2

    third = signal(222, "occ-3")
    runtime.journal.record((third,))
    runtime._update_selection(_record(222), (third,))
    assert runtime.live_selection() is None

    new_episode = signal(323, "occ-4")
    runtime.journal.record((new_episode,))
    runtime._update_selection(_record(323), (new_episode,))
    assert runtime.live_selection().repeat_position == 1
