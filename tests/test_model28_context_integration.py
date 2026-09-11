"""M28 live-cache gate at selection, plan and execution queue boundaries."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import Mock
import json
import pytest
from application.dashboard_service import DashboardService
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.model28_pattern_miner_shadow import Model28LiveSelection
from research.mt5_research_trade_plan import MT5ResearchTradePlan


def setup_live(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stamp=datetime(2026,9,11,12,tzinfo=timezone.utc)
    closed=dict(time=stamp,open=3400.,high=3405.,low=3398.,close=3401.)
    rows=[closed,{**closed,'time':stamp+timedelta(minutes=5)}]
    record=SimpleNamespace(timestamp=stamp,index=200,warmup_complete=True,
                           **{k:v for k,v in closed.items() if k!='time'})
    selection=Model28LiveSelection(versioned_id='test_v1',pattern_id='test',direction='BUY',
        selected_at=stamp.isoformat(),confidence=.5,validation_performance=.2,oos_performance=.2,
        valid_until_index=220,occurrence_id='case',symbol='XAUUSD',timeframe='M5',
        entry_reference=3400.,stop_reference=3395.,target_reference=3410.,reason='fixture')
    runtime=SimpleNamespace(latest_record=Mock(return_value=record),
                            live_selection=Mock(return_value=selection),
                            active_markets=lambda:(('XAUUSD','M5'),))
    market=SimpleNamespace(latest_forex_candles={('XAUUSD','M5'):rows},
        m23_context_observed_at={('XAUUSD','M5'):perf_counter()},
        supplemental_forex_seed_only_keys=set())
    service=object.__new__(DashboardService)
    object.__setattr__(service,'model28_shadow_runtime',runtime)
    object.__setattr__(service,'mt5_market_data_service',market)
    row=DashboardMT5ForexSignalRowViewModel(pair='XAUUSD',timeframe='M5',last_price=3402.)
    fallback=MT5ResearchTradePlan(symbol='XAUUSD',timeframe='M5',direction='WAIT',
        entry_price=None,stop=None,target=None,risk_reward=0,stop_multiplier=0,
        exit_model='NONE',exit_score=0,exit_candidates=0,status='SEM_PLANO')
    return service,row,fallback,record,selection


def test_fresh_selection_preserves_learned_distances_and_logs(tmp_path,monkeypatch):
    service,row,base,record,selection=setup_live(tmp_path,monkeypatch)
    result_row,plan=service._mt5_model28_adaptive_plan(row,base)
    assert result_row.decision=='BUY' and plan.direction=='BUY'
    assert (plan.entry_price,plan.stop,plan.target)==(3402.,3397.,3412.)
    assert plan.stop_management_parameters['m28_context_candle']==record.timestamp.isoformat()
    assert service._model28_entry_context_check('XAUUSD',plan).ready
    payload=json.loads((tmp_path/'.traderia/runtime/m28_context_sync_latest.json').read_text())
    assert payload['markets']['XAUUSD']['m28_context_candle']==record.timestamp.isoformat()


@pytest.mark.parametrize('bad',['missing_read','aged','seed','missing_cache','wrong_record','warmup'])
def test_bad_context_never_exposes_selection_or_entry_plan(tmp_path,monkeypatch,bad):
    service,row,base,record,selection=setup_live(tmp_path,monkeypatch)
    market=service.mt5_market_data_service
    if bad=='missing_read':market.m23_context_observed_at={}
    elif bad=='aged':market.m23_context_observed_at[('XAUUSD','M5')]-=61
    elif bad=='seed':market.supplemental_forex_seed_only_keys={('XAUUSD','M5')}
    elif bad=='missing_cache':market.latest_forex_candles={}
    elif bad=='wrong_record':record.timestamp-=timedelta(minutes=5)
    elif bad=='warmup':record.warmup_complete=False
    assert service.get_model28_live_selection('XAUUSD') is None
    assert service.list_model28_live_selections()==()
    result_row,plan=service._mt5_model28_adaptive_plan(row,base)
    assert result_row.theoretical_entry_status=='M28_CONTEXT_WAITING'
    assert plan.direction=='WAIT' and plan.status=='M28_CONTEXT_WAITING'
    assert (plan.entry_price,plan.stop,plan.target)==(None,None,None)
    service.model28_shadow_runtime.live_selection.assert_not_called()


def test_existing_statistical_rejection_stays_rejected(tmp_path,monkeypatch):
    service,row,base,record,selection=setup_live(tmp_path,monkeypatch)
    service.model28_shadow_runtime.live_selection.return_value=None
    result_row,plan=service._mt5_model28_adaptive_plan(row,base)
    assert plan.direction=='WAIT' and plan.status=='M28_AGUARDA_PADRAO_RANQUEADO'


def test_selection_can_span_closed_candles_inside_original_validity(tmp_path,monkeypatch):
    service,row,base,record,selection=setup_live(tmp_path,monkeypatch)
    older=replace(selection,selected_at=(record.timestamp-timedelta(minutes=10)).isoformat())
    service.model28_shadow_runtime.live_selection.return_value=older
    assert service.get_model28_live_selection('XAUUSD')==older
    _,plan=service._mt5_model28_adaptive_plan(row,base)
    assert plan.direction=='BUY'


@pytest.mark.parametrize('change',['age','candle','occurrence','filter_block'])
def test_queued_plan_cannot_survive_stale_or_changed_context(tmp_path,monkeypatch,change):
    service,row,base,record,selection=setup_live(tmp_path,monkeypatch)
    _,plan=service._mt5_model28_adaptive_plan(row,base)
    assert plan.direction=='BUY'
    if change=='age':service.mt5_market_data_service.m23_context_observed_at[('XAUUSD','M5')]-=61
    elif change=='candle':
        for candle in service.mt5_market_data_service.latest_forex_candles[('XAUUSD','M5')]:
            candle['time']+=timedelta(minutes=5)
        record.timestamp+=timedelta(minutes=5);record.index+=1
    elif change=='occurrence':
        service.model28_shadow_runtime.live_selection.return_value=replace(selection,occurrence_id='other')
    else:service.model28_shadow_runtime.live_selection.return_value=None
    assert not service._model28_entry_context_check('XAUUSD',plan).ready


def test_fresh_read_resumes_same_still_valid_pattern(tmp_path,monkeypatch):
    service,row,base,record,selection=setup_live(tmp_path,monkeypatch)
    service.mt5_market_data_service.m23_context_observed_at[('XAUUSD','M5')]-=61
    assert service.get_model28_live_selection('XAUUSD') is None
    service.mt5_market_data_service.m23_context_observed_at[('XAUUSD','M5')]=perf_counter()
    assert service.get_model28_live_selection('XAUUSD')==selection
