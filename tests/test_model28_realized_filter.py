import json
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from application.model28_realized_filter import evaluate_realized_pattern, allows_realized_pattern, DEFAULT_POLICY
from application.model28_pattern_miner_shadow import Model28ShadowRuntime
from application.model23_pattern_filter import (
    M23PatternSample,M23PatternContext,_assign_chronological_splits,_build_rules,
)


def spec():
    return SimpleNamespace(versioned_id='TEST_v1',symbol='BTCUSD',direction='SELL',
        contract_version='V6',stop_atr=2.,target_atr=3.,max_holding_candles=20)


def record():
    return SimpleNamespace(timestamp=datetime(2026,9,1,tzinfo=timezone.utc),
        warmup_complete=True,trend_state='down',structure_state='down',
        rsi14=40.,adx14=30.,atr14=1.,session='ASIA',events=())


def make_policy(tmp_path, n=30, net=-1.):
    context=M23PatternContext('ALIGNED','ALIGNED','RSI_30_50','ADX_GE25','ATR_NORMAL','ASIA','NO_MAJOR_EVENT')
    samples=[M23PatternSample('identity','BTCUSD','TEST','TEST','SELL',
        (datetime(2026,9,1,tzinfo=timezone.utc)+timedelta(minutes=i)).isoformat(),net,'','p',context) for i in range(n)]
    assigned=_assign_chronological_splits(samples)
    rules=[asdict(r) for r in _build_rules(assigned)]
    payload=dict(schema_version=2,mode='CONTEXT_BLOCK_ONLY',contracts={'identity':vars(spec())},rules=rules)
    p=tmp_path/'policy.json';p.write_text(json.dumps(payload))
    return p,payload


def test_negative_context_blocks_after_three_temporal_splits(tmp_path):
    p,_=make_policy(tmp_path)
    assert evaluate_realized_pattern(spec(),record(),policy_path=p).decision=='BLOCK'


def test_insufficient_sample_preserves_signal(tmp_path):
    p,_=make_policy(tmp_path,n=19)
    assert allows_realized_pattern(spec(),record(),policy_path=p)


def test_positive_context_is_allowed(tmp_path):
    p,_=make_policy(tmp_path,net=2.)
    assert evaluate_realized_pattern(spec(),record(),policy_path=p).decision=='APPROVE'


def test_missing_context_or_policy_is_not_a_blanket_ban(tmp_path):
    assert allows_realized_pattern(spec(),None,policy_path=tmp_path/'missing')
    p=tmp_path/'invalid';p.write_text('{')
    assert allows_realized_pattern(spec(),record(),policy_path=p)


def test_pattern_asset_version_and_geometry_are_isolated(tmp_path):
    p,_=make_policy(tmp_path)
    for field,value in [('versioned_id','OTHER_v1'),('symbol','USDJPY'),('direction','BUY'),
                        ('contract_version','V7'),('stop_atr',4.),('target_atr',5.),('max_holding_candles',30)]:
        s=spec();setattr(s,field,value)
        assert allows_realized_pattern(s,record(),policy_path=p)


def test_only_matching_context_blocks_and_future_records_are_excluded(tmp_path):
    p,payload=make_policy(tmp_path)
    payload['rules']=[r for r in payload['rules'] if r['pattern_scope']=='RSI']
    p.write_text(json.dumps(payload))
    r=record();r.rsi14=60
    assert allows_realized_pattern(spec(),r,policy_path=p)
    r=record();future=record();future.timestamp+=timedelta(days=1);future.atr14=100
    assert not allows_realized_pattern(spec(),r,[r,future],policy_path=p)


def test_runtime_blocks_before_ranking():
    runtime=object.__new__(Model28ShadowRuntime);runtime._realized_filter_enabled=True
    runtime._selections={};runtime.journal=SimpleNamespace(load=lambda:())
    runtime._engines={('XAUUSD','M5'):SimpleNamespace(records=[],tracker=SimpleNamespace(specs=[spec()]))}
    signal=SimpleNamespace(setup_id='TEST',setup_version=1)
    with patch('application.model28_pattern_miner_shadow.allows_realized_pattern',return_value=False),patch.object(runtime,'_repeat_position',side_effect=AssertionError('blocked reached ranking')):
        runtime._update_selection(SimpleNamespace(index=1),(signal,))
    assert not runtime._selections


def test_installed_policy_is_contextual():
    policy=json.loads(DEFAULT_POLICY.read_text())
    assert policy['mode']=='CONTEXT_BLOCK_ONLY'
    assert 'allowed_patterns' not in policy
