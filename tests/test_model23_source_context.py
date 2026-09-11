from datetime import datetime,timedelta,timezone
from dataclasses import replace
from application.model23_source_context import M23SourceContextBuilder


def candles(count=201):
    start=datetime(2026,9,1,tzinfo=timezone.utc)
    return [dict(time=start+timedelta(minutes=5*i),open=100+i*.03,high=101+i*.03,
                 low=99+i*.03,close=100.2+i*.03,tick_volume=100+i%7,spread=2)
            for i in range(count)]


def test_aligned_without_m28_and_exact_declared_candle():
    rows=candles();b=M23SourceContextBuilder();r=b.build(rows,expected_candle=rows[-2]['time'])
    assert r.status=='ALIGNED' and r.record.timestamp==rows[-2]['time']
    assert r.record.warmup_complete and len(r.history)==200
    assert r.audit()['m23_context_gap_seconds']==0


def test_forming_bar_is_never_read_as_closed_or_used_in_indicators():
    rows=candles();b=M23SourceContextBuilder();a=b.build(rows)
    rows[-1].update(open=999,high=999,low=999,close=999)
    c=b.build(rows)
    assert a.history==c.history and a.input_fingerprint==c.input_fingerprint
    assert b.build(rows,expected_candle=rows[-1]['time']).status=='NOT_CLOSED'


def test_missing_exact_candle_does_not_fall_back_to_old_context():
    rows=candles();expected=rows[-2]['time'];del rows[-2]
    assert M23SourceContextBuilder().build(rows,expected_candle=expected).status=='MISSING_SIGNAL_CANDLE'


def test_insufficient_warmup_and_invalid_input():
    b=M23SourceContextBuilder()
    assert b.build(candles(200)).status=='WARMUP_INCOMPLETE'
    assert b.build([]).record is None
    rows=candles();rows[-2]['close']=float('nan')
    assert b.build(rows).status=='INVALID_DATA'


def test_corrected_closed_candle_invalidates_cache():
    rows=candles();b=M23SourceContextBuilder();a=b.build(rows)
    rows[-2]['close']+=.5
    c=b.build(rows)
    assert a.input_fingerprint!=c.input_fingerprint
    assert a.record.close!=c.record.close


def test_new_bar_advances_context_and_window_is_deterministic():
    b=M23SourceContextBuilder();a=b.build(candles(201));c=b.build(candles(202))
    independent=M23SourceContextBuilder().build(candles(202)[1:])
    assert c.record.timestamp-a.record.timestamp==timedelta(minutes=5)
    assert c.history==independent.history
