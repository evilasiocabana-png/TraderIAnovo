"""Deterministic M23 context from the source's shared M5 candles, without M28.

MT5 candle timestamps and source-declared timestamps stay in the same domain.
No orders, report rebuilds or network access occur here. The final raw row is
always treated as forming; a declared signal cannot consume that row.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from collections import OrderedDict
import hashlib
import json
import math
import threading
from typing import Mapping, Sequence
from replay.pattern_miner.config import PatternMinerConfig
from replay.pattern_miner.models import CandleBar, EventRecord
from replay.pattern_miner.indicators import IndicatorEngine
from replay.pattern_miner.detectors import CausalEventDetector

M23_CONTEXT_WINDOW = 200


def candle_time(value: object) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, (int, float)):
        result = datetime.fromtimestamp(value, timezone.utc)
    else:
        result = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def _value(row, *names, default=None):
    for name in names:
        if isinstance(row, Mapping) and name in row:
            return row[name]
        if name in (getattr(getattr(row, 'dtype', None), 'names', ()) or ()):
            return row[name]
        if hasattr(row, name):
            return getattr(row, name)
    if default is not None:
        return default
    raise ValueError('Missing candle field: ' + names[0])


def _bar(row, index):
    result = CandleBar(index, candle_time(_value(row, 'data', 'time', 'timestamp')),
        float(_value(row, 'abertura', 'open')), float(_value(row, 'maxima', 'high')),
        float(_value(row, 'minima', 'low')), float(_value(row, 'fechamento', 'close')),
        float(_value(row, 'volume', 'tick_volume', default=0)),
        float(_value(row, 'spread', default=0)), float(_value(row, 'real_volume', default=0)))
    values=(result.open,result.high,result.low,result.close,result.volume,result.spread,result.real_volume)
    if not all(math.isfinite(v) for v in values) or min(values[:4]) <= 0:
        raise ValueError('Invalid candle values')
    if result.low > min(result.open,result.close) or result.high < max(result.open,result.close):
        raise ValueError('Invalid candle range')
    return result


@dataclass(frozen=True)
class M23ContextWindow:
    record: EventRecord | None = None
    history: tuple[EventRecord, ...] = ()
    expected_time: datetime | None = None
    decision_time: datetime | None = None
    status: str = 'MISSING'
    reason: str = 'M23 sem candles M5 disponiveis.'
    basis: str = 'LATEST_CLOSED_M5'
    input_fingerprint: str = ''
    config_fingerprint: str = ''

    def audit(self):
        return dict(
            m23_context_sync_status=self.status,
            m23_context_sync_reason=self.reason,
            m23_context_signal_basis=self.basis,
            m23_context_expected_candle=self.expected_time.isoformat() if self.expected_time else None,
            m23_context_candle=self.record.timestamp.isoformat() if self.record else None,
            m23_context_reference_time=self.decision_time.isoformat() if self.decision_time else None,
            m23_context_clock_domain='MT5_SOURCE_CANDLE_TIME',
            m23_context_history_start=self.history[0].timestamp.isoformat() if self.history else None,
            m23_context_history_count=len(self.history),
            m23_context_input_fingerprint=self.input_fingerprint,
            m23_context_config_fingerprint=self.config_fingerprint,
            m23_context_gap_seconds=(self.expected_time-self.record.timestamp).total_seconds()
                if self.expected_time and self.record else None,
        )


class M23SourceContextBuilder:
    def __init__(self, max_cache_entries=32):
        self.config=PatternMinerConfig()
        self._cache=OrderedDict()
        self._max_cache_entries=max_cache_entries
        self._lock=threading.RLock()

    def build(self, rows: Sequence[object], *, expected_candle=None) -> M23ContextWindow:
        basis='DECLARED_SIGNAL_M5' if expected_candle not in (None,'','N/D') else 'LATEST_CLOSED_M5'
        expected=None
        reference=None
        try:
            if basis=='DECLARED_SIGNAL_M5':
                expected=candle_time(expected_candle)
            bars=sorted({_bar(row,0).timestamp:_bar(row,0) for row in rows}.values(),key=lambda b:b.timestamp)
            if len(bars)<2:
                return M23ContextWindow(expected_time=expected,basis=basis)
            reference=bars[-1].timestamp
            expected=expected if expected is not None else reference-timedelta(minutes=5)
            if expected+timedelta(minutes=5)>reference:
                return M23ContextWindow(expected_time=expected,decision_time=reference,status='NOT_CLOSED',basis=basis,
                    reason='Candle do sinal ainda nao fechado na serie M5.')
            closed=[b for b in bars[:-1] if b.timestamp<=expected]
            if not closed or closed[-1].timestamp!=expected:
                return M23ContextWindow(expected_time=expected,decision_time=reference,status='MISSING_SIGNAL_CANDLE',basis=basis,
                    reason='Serie M5 nao contem o candle fechado exato do sinal.')
            if len(closed)<M23_CONTEXT_WINDOW:
                return M23ContextWindow(expected_time=expected,decision_time=reference,status='WARMUP_INCOMPLETE',basis=basis,
                    reason='M23 exige 200 candles fechados ate o sinal para reconstruir contexto.')
            closed=closed[-M23_CONTEXT_WINDOW:]
            normalized=[CandleBar(i,b.timestamp,b.open,b.high,b.low,b.close,b.volume,b.spread,b.real_volume) for i,b in enumerate(closed)]
            payload=[(b.timestamp.isoformat(),b.open,b.high,b.low,b.close,b.volume,b.spread,b.real_volume) for b in normalized]
            signature=hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()
            key=(self.config.fingerprint(),signature)
            with self._lock:
                records=self._cache.get(key)
                if records is None:
                    frame=IndicatorEngine(self.config).compute(normalized)
                    detector=CausalEventDetector(self.config)
                    records=tuple(detector.process(i,normalized,frame) for i in range(len(normalized)))
                    self._cache[key]=records
                    while len(self._cache)>self._max_cache_entries:self._cache.popitem(last=False)
                else:self._cache.move_to_end(key)
            return M23ContextWindow(record=records[-1],history=records,expected_time=expected,decision_time=reference,
                status='ALIGNED',reason='Contexto M5 reconstruido no candle do sinal; independente de contratos M28.',
                basis=basis,input_fingerprint=signature,config_fingerprint=self.config.fingerprint())
        except (ValueError,TypeError,OverflowError,KeyError,AttributeError) as exc:
            return M23ContextWindow(expected_time=expected,decision_time=reference,status='INVALID_DATA',basis=basis,
                reason='Dados de contexto M23 invalidos: '+type(exc).__name__)
