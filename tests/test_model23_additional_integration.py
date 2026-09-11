from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path
import json
import pytest
import application.dashboard_service as module
from application.model23_pattern_filter import M23PatternFilterDecision
from application.model23_additional_filters import load_catalog, SOURCE_MODEL
from tests.test_model23_context_integration import setup_service

CATALOG_PATH = Path(__file__).resolve().parents[1]/'config/m23_additional_filters.json'

def prepare(tmp_path, monkeypatch, rule_index=0, mode='BLOCK', original='NO_EVIDENCE'):
    catalog=replace(load_catalog(CATALOG_PATH),mode=mode)
    assert catalog.status=='READY' and len(catalog.rules)==3
    service,row,plan=setup_service(tmp_path,monkeypatch)
    row=replace(row,decision='BUY',theoretical_entry_direction='BUY')
    plan=replace(plan,direction='BUY',entry_price=100,stop=90,target=120)
    decision=M23PatternFilterDecision(decision=original,context_status='VALID',
        context_snapshot=dict(catalog.rules[rule_index].context_snapshot),reason='original-rule-result')
    monkeypatch.setattr(module,'_MODEL23_PATTERN_FILTER_SERVICE',SimpleNamespace(evaluate=lambda **kw:decision))
    monkeypatch.setattr(module,'load_catalog',lambda:catalog)
    return service,row,plan,catalog


@pytest.mark.parametrize('rule_index',[0,1,2])
@pytest.mark.parametrize('original',['NO_EVIDENCE','APPROVE'])
def test_exact_additional_blocks_m23_candidate_after_original_allows(tmp_path,monkeypatch,rule_index,original):
    service,row,plan,catalog=prepare(tmp_path,monkeypatch,rule_index,original=original)
    view,result=service._mt5_model23_variant_from_source(row,plan,source_operational_model=SOURCE_MODEL)
    assert result.direction==view.decision=='WAIT'
    assert result.status=='M23_ADDITIONAL_FILTER_BLOCKED'
    assert result.entry_price is None and result.stop is None and result.target is None
    params=result.stop_management_parameters
    assert params['m23_pattern_filter_decision']==original
    assert params['m23_pattern_filter_blocks_execution'] is False
    assert params['m23_additional_matched_ids']==[catalog.rules[rule_index].rule_id]
    assert params['m23_additional_blocks_execution'] is True
    persisted=json.loads((tmp_path/'.traderia/runtime/m23_context_sync_latest.json').read_text())
    assert persisted['m23_additional_matched_ids']==params['m23_additional_matched_ids']


def test_observation_keeps_source_stop_and_plan(tmp_path,monkeypatch):
    service,row,plan,_=prepare(tmp_path,monkeypatch,mode='OBSERVE')
    _,result=service._mt5_model23_variant_from_source(row,plan,source_operational_model=SOURCE_MODEL)
    assert result.direction=='BUY' and result.stop==plan.stop and result.target==plan.target
    assert result.stop_management_parameters['m23_additional_matched_ids']
    assert not result.stop_management_parameters['m23_additional_blocks_execution']


def test_original_block_keeps_precedence(tmp_path,monkeypatch):
    service,row,plan,_=prepare(tmp_path,monkeypatch,original='BLOCK')
    _,result=service._mt5_model23_variant_from_source(row,plan,source_operational_model=SOURCE_MODEL)
    assert result.status=='M23_PATTERN_FILTER_BLOCKED'
    assert result.reason=='original-rule-result'


@pytest.mark.parametrize('difference',['source','symbol','direction','context','synchronization'])
def test_scope_and_data_guards_are_preserved(tmp_path,monkeypatch,difference):
    service,row,plan,catalog=prepare(tmp_path,monkeypatch)
    source=SOURCE_MODEL
    if difference=='source':source=module.MT5_OPERATIONAL_MODEL_8
    if difference=='symbol':
        row=replace(row,pair='BTCUSD');plan=replace(plan,symbol='BTCUSD')
        svc=service.mt5_market_data_service
        svc.latest_forex_candles[('BTCUSD','M5')]=svc.latest_forex_candles[('XAUUSD','M5')]
        svc.m23_context_observed_at[('BTCUSD','M5')]=svc.m23_context_observed_at[('XAUUSD','M5')]
    if difference=='direction':
        row=replace(row,decision='SELL');plan=replace(plan,direction='SELL')
    if difference=='context':
        different=dict(catalog.rules[0].context_snapshot);different['atr_regime']='ATR_EXPANSION'
        monkeypatch.setattr(module,'_MODEL23_PATTERN_FILTER_SERVICE',SimpleNamespace(evaluate=lambda **kw:M23PatternFilterDecision(context_status='VALID',context_snapshot=different)))
    if difference=='synchronization':service.mt5_market_data_service.m23_context_observed_at={}
    _,result=service._mt5_model23_variant_from_source(row,plan,source_operational_model=source)
    assert not result.stop_management_parameters['m23_additional_blocks_execution']
    if difference=='synchronization':
        assert result.status=='M23_CONTEXT_WAITING' and result.direction=='WAIT'
    else:
        assert result.direction==plan.direction and result.stop==plan.stop
