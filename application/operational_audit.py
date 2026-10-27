"""Durable operational events; no broker calls and no inferred historical decisions."""
import json
import logging
import os
import threading
from collections import deque
from dataclasses import asdict, is_dataclass
from datetime import datetime
from functools import wraps
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / '.traderia/runtime/operational_events.jsonl'
LOCK = threading.RLock()


def _json_default(value):
    if isinstance(value, (datetime, Path)):
        return str(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, 'item'):
        return value.item()
    raise TypeError('Unsupported audit value: ' + type(value).__name__)


def fallback_path(path):
    return Path(os.environ.get('LOCALAPPDATA', str(ROOT / '.traderia'))) / 'TraderIANovo' / 'audit_fallback' / path.name


def append_record(path, record):
    path = Path(path)
    payload = dict(record)
    payload.setdefault('event_id', uuid4().hex)
    payload.setdefault('timestamp', datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat())
    line = json.dumps(payload, ensure_ascii=True, default=_json_default) + '\n'
    errors = []
    with LOCK:
        for target in (path, fallback_path(path)):
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('a', encoding='utf-8') as f:
                    f.write(line)
                    f.flush()
                    os.fsync(f.fileno())
                if target != path:
                    logging.error('Audit primary unavailable; record saved in fallback: %s', path.name)
                return target
            except OSError as exc:
                errors.append(exc)
    raise OSError('Both audit destinations unavailable') from errors[-1]


def event(action, status, message='', *, details=None, path=None, timestamp=None):
    row = dict(action=action, status=status, message=message, details=details or {})
    if timestamp:
        row['timestamp'] = timestamp
    try:
        return append_record(path or EVENTS, row)
    except (OSError, TypeError):
        logging.exception('Operational event could not be persisted: %s', action)
        return None


def recent_events(path=None, limit=200):
    path = Path(path or EVENTS)
    rows = {}
    for source in (path, fallback_path(path)):
        if not source.exists():
            continue
        try:
            with source.open(encoding='utf-8') as f:
                lines = deque(f, maxlen=limit)
            for line in lines:
                try:
                    row = json.loads(line)
                    row['storage'] = 'Alternativo' if source != path else 'Principal'
                    rows[row.get('event_id') or line] = row
                except (ValueError, TypeError):
                    continue
        except OSError:
            logging.exception('Cannot read operational log')
    return sorted(rows.values(), key=lambda r:r.get('timestamp',''), reverse=True)[:limit]


def audited_submit(fn):
    @wraps(fn)
    def wrapped(provider, order):
        from domain.contracts.execution_result import ExecutionResult
        path = Path(provider.log_path).with_name('execution_attempts.jsonl')
        attempt = uuid4().hex
        base = dict(attempt_id=attempt, operational_model=order.operational_model,
                    symbol=order.symbol, plan_snapshot=order.plan_snapshot or {},
                    order=asdict(order), execution_account_mode=provider.execution_account.mode)
        try:
            append_record(path, dict(base, stage='ATTEMPT'))
        except (OSError, TypeError):
            event('Registro de envio', 'FALHA', 'Nova tentativa bloqueada: nao foi possivel persistir o plano.')
            return ExecutionResult(False, 'REJECTED', 'Registro persistente indisponivel; ordem nao enviada.')
        try:
            result = fn(provider, order)
        except Exception as exc:
            event('Registro de envio', 'INCERTO', 'Execucao interrompida; consultar MT5 antes de qualquer repeticao.',
                  details=dict(attempt_id=attempt, error_type=type(exc).__name__))
            try:
                append_record(path, dict(base, stage='UNCERTAIN', error_type=type(exc).__name__))
            except (OSError, TypeError):
                logging.exception('Cannot persist uncertain execution')
            raise
        try:
            append_record(path, dict(base, stage='RESULT', result=asdict(result)))
        except (OSError, TypeError):
            # Never turn an accepted broker order into a rejected/retryable order.
            event('Registro de envio', 'FALHA', 'Resultado conhecido, mas journal indisponivel; nao reenviar.',
                  details=dict(attempt_id=attempt, accepted=result.accepted, ticket=result.ticket))
        else:
            if result.accepted:
                snapshot = order.plan_snapshot or {}
                params = snapshot.get('stop_management_parameters') or {}
                source = params.get('reinforcement_source') or params.get('source_operational_model') or snapshot.get('source_operational_model') or 'Ver setup'
                summary = (f'Ativo: {order.symbol} | Setup: {order.entry_setup or "Nao registrado"} | '
                           f'Lote: {order.quantity} | Executor: {order.operational_model} | Fonte: {source} | '
                           f'Resultado: ACEITO | Ticket: {result.ticket}. Aceite nao confirma preenchimento.')
                event('Registro de envio', 'CONFIRMADO', summary,
                      details=dict(attempt_id=attempt, symbol=order.symbol, setup=order.entry_setup,
                                   quantity=order.quantity, executor=order.operational_model,
                                   source=source, ticket=result.ticket, broker_status=result.status))
        return result
    return wrapped
