from time import perf_counter
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import application.dashboard_service as module
from application.dashboard_service import DashboardService
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.model23_pattern_filter import M23PatternFilterService
from research.mt5_research_trade_plan import MT5ResearchTradePlan
from tests.test_model23_source_context import candles


def setup_service(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    service=DashboardService()
    service.mt5_market_data_service.latest_forex_candles={('XAUUSD','M5'):candles()}
    service.mt5_market_data_service.m23_context_observed_at={('XAUUSD','M5'):perf_counter()}
    service.mt5_market_data_service.supplemental_forex_seed_only_keys=set()
    object.__setattr__(service,'model28_shadow_runtime',Mock())
    service.model28_shadow_runtime.latest_record.side_effect=AssertionError('M23 must not consult M28')
    monkeypatch.setattr(module,'_MODEL23_PATTERN_FILTER_SERVICE',M23PatternFilterService(tmp_path/'missing_report.json'))
    row=DashboardMT5ForexSignalRowViewModel(pair='XAUUSD',status='OK',timeframe='M5',decision='SELL',theoretical_entry_direction='SELL',theoretical_entry_price=100,active_model='TEST')
    plan=MT5ResearchTradePlan(symbol='XAUUSD',timeframe='M5',direction='SELL',entry_price=100,stop=110,target=80,risk_reward=2,stop_multiplier=1.5,exit_model='FIXED',exit_score=1,exit_candidates=1,status='PLANO_VALIDO',stop_management_parameters={'active_entry_order_type':'MARKET','indicator_closed_candle_time':candles()[-2]['time'].isoformat()})
    return service,row,plan


def test_valid_context_no_statistical_evidence_preserves_source_and_logs(tmp_path,monkeypatch):
    service,row,plan=setup_service(tmp_path,monkeypatch)
    _,result=service._mt5_model23_variant_from_source(row,plan,source_operational_model=module.MT5_OPERATIONAL_MODEL_8)
    assert result.direction=='SELL'
    p=result.stop_management_parameters
    assert p['m23_context_sync_status']=='ALIGNED'
    assert p['m23_pattern_filter_context_status']=='VALID'
    assert p['m23_pattern_filter_context_timestamp']==p['m23_context_expected_candle']
    assert p['m23_context_waiting_for_data'] is False
    assert p['m23_pattern_filter_context_snapshot']
    assert (tmp_path/'.traderia/runtime/m23_context_sync_latest.json').exists()


@pytest.mark.parametrize('problem',['missing','seed','aged','wrong_signal','insufficient'])
def test_bad_context_waits_before_provider(tmp_path,monkeypatch,problem):
    service,row,plan=setup_service(tmp_path,monkeypatch)
    if problem=='missing':service.mt5_market_data_service.latest_forex_candles={}
    elif problem=='seed':service.mt5_market_data_service.supplemental_forex_seed_only_keys={('XAUUSD','M5')}
    elif problem=='aged':service.mt5_market_data_service.m23_context_observed_at={('XAUUSD','M5'):perf_counter()-61}
    elif problem=='wrong_signal':plan.stop_management_parameters['indicator_closed_candle_time']=candles()[-1]['time'].isoformat()
    elif problem=='insufficient':service.mt5_market_data_service.latest_forex_candles={('XAUUSD','M5'):candles(30)}
    _,result=service._mt5_model23_variant_from_source(row,plan,source_operational_model=module.MT5_OPERATIONAL_MODEL_8)
    assert result.direction=='WAIT' and result.status=='M23_CONTEXT_WAITING'
    assert result.entry_price is None
    assert result.stop_management_parameters['m23_context_waiting_for_data'] is True
