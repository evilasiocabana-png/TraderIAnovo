"""Repair a stale display snapshot from captured native deals, never from guesses."""
import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from functools import wraps
from types import SimpleNamespace
from application.system_supervisor import RUNTIME, atomic_json


def report_write_guard(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        from filelock import FileLock, Timeout
        RUNTIME.mkdir(parents=True, exist_ok=True)
        try:
            with FileLock(str(RUNTIME/'report_snapshot_write.lock'), timeout=0):
                return fn(*args, **kwargs)
        except Timeout:
            return None  # Keep the existing display snapshot; never delay trading.
    return wrapped


def rebuild(report, payload):
    from collections import defaultdict
    from application.dashboard_service import DashboardService
    service = DashboardService()
    grouped = defaultdict(list)
    opened = {int(p.get('identifier') or p['ticket']) for p in payload.get('open_positions', [])}
    unique = {}
    for deal in payload['rows']:
        unique[int(deal['ticket'])] = deal
    for d in unique.values():
        if d.get('type') in (0, 1) and d.get('position_id'):
            grouped[int(d['position_id'])].append(d)
    closed = {}
    for key, deals in grouped.items():
        if key in opened or any(d.get('entry') == 2 for d in deals): continue
        vin = sum(d['volume'] for d in deals if d['entry'] == 0)
        vout = sum(d['volume'] for d in deals if d['entry'] in (1,3))
        if vin <= 0 or abs(vin-vout) > 1e-8: continue
        if any(not all(k in d for k in ('profit','commission','swap','fee')) for d in deals):
            raise ValueError('Custos incompletos; nao reparar')
        closed[key] = deals
    history = {}
    values = [SimpleNamespace(_asdict=lambda d=d:dict(d)) for ds in closed.values() for d in ds]
    service._merge_mt5_history_deals(SimpleNamespace(history_deals_get=lambda *args:values), None, None, history)
    fresh = {key:asdict(service._mt5_only_trade_audit_row(history[key])) for key in closed}
    output = []
    used = set()
    from application.account_channel_continuity import CONFIG
    config = json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else {}
    cutover = config.get('report_cutover_utc')
    for old in report.get('rows', []):
        key = old.get('mt5_ticket') or old.get('local_ticket')
        try: key=int(key)
        except (TypeError,ValueError): key=None
        historical = bool(cutover and str(old.get('mt5_time','')) < cutover)
        if key not in fresh or historical:
            output.append(old);continue
        if key in used: continue
        used.add(key)
        new = dict(old)
        for field,value in fresh[key].items():
            if field.startswith('mt5_') or field in {'operation_status','audit_status','audit_message'}:
                new[field] = value
        output.append(new)
    output.extend(value for key,value in fresh.items() if key not in used)
    # Independently validate every fully closed native position's four cost components.
    for key,deals in closed.items():
        row = fresh[key]
        native = sum(float(d[k]) for d in deals for k in ('profit','commission','swap','fee'))
        shown = sum(float(row.get(k) or 0) for k in ('mt5_realized_profit','mt5_commission','mt5_swap','mt5_fee'))
        if abs(native-shown) > .011: raise ValueError('Conciliacao de custos falhou')
    return {**report, 'rows':output, 'last_update':datetime.now(timezone.utc).isoformat()}, len(closed)


def repair(report_path, payload, backup_dir):
    from filelock import FileLock
    with FileLock(str(RUNTIME/'report_snapshot_write.lock'), timeout=0):
        report = json.loads(report_path.read_text(encoding='utf-8'))
        updated, count = rebuild(report, payload)
        shutil.copy2(report_path, backup_dir/'report_before_repair.json')
        atomic_json(report_path, updated)
        verified = json.loads(report_path.read_text(encoding='utf-8'))
        if verified != updated: raise ValueError('Persistencia da correcao nao confirmada')
        return verified, count
