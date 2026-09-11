"""Pure validation of M28 live context; no indicator or rule recalculation.

Timestamps stay in the supplied MT5 candle domain. Observation age uses the
caller's monotonic clock, never a guessed broker-to-UTC offset. An older selected
pattern can remain valid according to its original candle-index expiry.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from numbers import Real
from typing import Mapping

_MISSING = object()
_OHLC = ('open', 'high', 'low', 'close')


def _field(value, *names, default=_MISSING):
    for name in names:
        if isinstance(value, Mapping) and name in value:
            return value[name]
        if name in (getattr(getattr(value, 'dtype', None), 'names', ()) or ()):
            return value[name]
        if hasattr(value, name):
            return getattr(value, name)
    if default is not _MISSING:
        return default
    raise ValueError('Missing field')


def _time(value) -> datetime:
    if isinstance(value, bool) or value is None:
        raise ValueError('Invalid time')
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, Real):
        if not math.isfinite(float(value)):
            raise ValueError('Invalid epoch')
        result = datetime.fromtimestamp(float(value), timezone.utc)
    else:
        result = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def _price_values(value) -> tuple[float, float, float, float]:
    values = tuple(float(_field(value, *names)) for names in (
        ('open', 'abertura'), ('high', 'maxima'), ('low', 'minima'), ('close', 'fechamento'),
    ))
    if not all(math.isfinite(number) for number in values):
        raise ValueError('Invalid OHLC')
    return values


def _index(value) -> int:
    if isinstance(value, bool):
        raise ValueError('Invalid index')
    number = float(value)
    if not math.isfinite(number) or not number.is_integer() or number < 0:
        raise ValueError('Invalid index')
    return int(number)


@dataclass(frozen=True)
class Model28ContextSync:
    ready: bool = False
    status: str = 'MISSING'
    reason: str = 'Contexto M28 ainda não verificado.'
    observation_age_seconds: float | None = None
    seed_only: bool = False
    row_count: int = 0
    expected_time: datetime | None = None
    record_time: datetime | None = None
    forming_time: datetime | None = None
    selected_at: datetime | None = None
    record_index: int | None = None
    selection_index: int | None = None
    valid_until_index: int | None = None
    expected_ohlc: tuple[float, float, float, float] | None = None
    record_ohlc: tuple[float, float, float, float] | None = None

    def audit(self) -> dict:
        return {
            'm28_context_ready': self.ready,
            'm28_context_sync_status': self.status,
            'm28_context_sync_reason': self.reason,
            'm28_context_observation_age_seconds': self.observation_age_seconds,
            'm28_context_seed_only': self.seed_only,
            'm28_context_row_count': self.row_count,
            'm28_context_expected_candle': self.expected_time.isoformat() if self.expected_time else None,
            'm28_context_candle': self.record_time.isoformat() if self.record_time else None,
            'm28_context_forming_candle': self.forming_time.isoformat() if self.forming_time else None,
            'm28_context_selection_time': self.selected_at.isoformat() if self.selected_at else None,
            'm28_context_record_index': self.record_index,
            'm28_context_selection_index': self.selection_index,
            'm28_context_valid_until_index': self.valid_until_index,
            'm28_context_expected_ohlc': dict(zip(_OHLC, self.expected_ohlc)) if self.expected_ohlc else None,
            'm28_context_record_ohlc': dict(zip(_OHLC, self.record_ohlc)) if self.record_ohlc else None,
            'm28_context_gap_seconds': (self.expected_time - self.record_time).total_seconds() if self.expected_time and self.record_time else None,
            'm28_context_clock_domain': 'MT5_SOURCE_CANDLE_TIME',
        }


def validate_model28_context(
    *, rows, record, observed_at, now, seed_only=False, selection=None,
) -> Model28ContextSync:
    """Check current M5 context while preserving the selection's validity rule.

    Input order is authoritative: duplicate or reversed timestamps are rejected,
    not silently sorted. The final raw row is forming and cannot be the record.
    """
    state = {'seed_only': bool(seed_only)}

    def result(status, reason, *, ready=False):
        return Model28ContextSync(ready=ready, status=status, reason=reason, **state)

    if seed_only:
        return result('SEED_ONLY', 'Histórico restaurado ainda precisa de confirmação ao vivo do MT5.')
    if observed_at is None:
        return result('MISSING_OBSERVATION', 'M28 ainda não tem uma leitura MT5 confirmada neste processo.')
    try:
        if isinstance(observed_at, bool) or isinstance(now, bool):
            raise ValueError('Invalid monotonic clock')
        observed, current = float(observed_at), float(now)
        if not math.isfinite(observed) or not math.isfinite(current):
            raise ValueError('Invalid monotonic clock')
        age = current - observed
        if not math.isfinite(age):
            raise ValueError('Invalid monotonic interval')
        state['observation_age_seconds'] = age
    except (TypeError, ValueError, OverflowError):
        return result('INVALID_OBSERVATION', 'A idade da leitura MT5 não pode ser verificada.')
    if age < 0:
        return result('FUTURE_OBSERVATION', 'A marca de leitura MT5 está à frente do relógio de verificação.')
    if age > 60:
        return result('STALE_OBSERVATION', 'M28 aguarda leitura MT5 confirmada nos últimos 60 segundos.')
    try:
        candles = list(rows) if rows is not None else []
        state['row_count'] = len(candles)
        if len(candles) < 2:
            return result('MISSING_CANDLES', 'M28 precisa da última vela fechada e da vela atual em formação.')
        timestamps = tuple(_time(_field(row, 'data', 'time', 'timestamp')) for row in candles)
        if any(previous >= current for previous, current in zip(timestamps, timestamps[1:])):
            return result('UNORDERED_CANDLES', 'A série M5 tem horários duplicados ou fora de ordem.')
        state['expected_time'], state['forming_time'] = timestamps[-2:]
        if (timestamps[-1] - timestamps[-2]).total_seconds() != 300:
            return result('M5_GAP', 'Há uma lacuna entre a última vela fechada e a vela atual M5.')
        state['expected_ohlc'] = _price_values(candles[-2])
    except (AttributeError, TypeError, ValueError, OverflowError, OSError):
        return result('INVALID_CANDLES', 'A série M5 contém horário ou preços inválidos.')
    if record is None:
        return result('MISSING_RECORD', 'O minerador M28 ainda não forneceu o registro da última vela fechada.')
    try:
        state['record_time'] = _time(_field(record, 'timestamp', 'data', 'time'))
        state['record_ohlc'] = _price_values(record)
        raw_index = _field(record, 'index', default=None)
        if raw_index is not None:
            state['record_index'] = _index(raw_index)
        if _field(record, 'warmup_complete', default=False) is not True:
            return result('WARMUP_INCOMPLETE', 'O registro M28 ainda não completou o aquecimento dos indicadores.')
    except (AttributeError, TypeError, ValueError, OverflowError, OSError):
        return result('INVALID_RECORD', 'O registro M28 contém horário, preços ou índice inválidos.')
    if state['record_time'] >= state['forming_time']:
        return result('RECORD_NOT_CLOSED', 'O registro M28 aponta para vela em formação ou para horário futuro.')
    if state['record_time'] != state['expected_time']:
        return result('RECORD_MISMATCH', 'O registro M28 não corresponde à última vela M5 fechada.')
    if state['record_ohlc'] != state['expected_ohlc']:
        return result('OHLC_MISMATCH', 'Os preços do registro M28 diferem da vela fechada confirmada pelo MT5.')
    if selection is not None:
        try:
            state['selected_at'] = _time(_field(selection, 'selected_at'))
            raw_selected_index = _field(selection, 'selected_index', 'selection_index', 'index', default=None)
            raw_expiry = _field(selection, 'valid_until_index', default=None)
            if raw_selected_index is not None:
                state['selection_index'] = _index(raw_selected_index)
            if raw_expiry is not None:
                state['valid_until_index'] = _index(raw_expiry)
            selection_index = state.get('selection_index')
            expiry = state.get('valid_until_index')
            record_index = state.get('record_index')
            if (selection_index is not None or expiry is not None) and record_index is None:
                raise ValueError('Missing record index for selection bounds')
            if selection_index is not None and expiry is not None and selection_index > expiry:
                raise ValueError('Invalid selection bounds')
        except (AttributeError, TypeError, ValueError, OverflowError, OSError):
            return result('INVALID_SELECTION', 'A validade temporal da seleção M28 não pode ser verificada.')
        if state['selected_at'] > state['record_time'] or (selection_index is not None and selection_index > record_index):
            return result('FUTURE_SELECTION', 'A seleção M28 está à frente do contexto fechado disponível.')
        if expiry is not None and record_index > expiry:
            return result('EXPIRED_SELECTION', 'A seleção M28 ultrapassou o limite de validade do próprio contrato.')
    return result('ALIGNED', 'Contexto M28 alinhado à última vela fechada e confirmado por leitura recente.', ready=True)
