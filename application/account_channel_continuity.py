"""Explicit, integrity-checked continuation of realized curves across Demo accounts."""
import hashlib
import json
import math
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / '.traderia/channel_continuity.json'


def seed_groups(account, config_path=None):
    path = Path(config_path) if config_path is not None else CONFIG
    if not path.exists():
        return {}
    config = json.loads(path.read_text(encoding='utf-8'))
    if (str(account.get('login')) != config['target_login'] or
            account.get('server') != config['target_server'] or account.get('trade_mode') != 0):
        return {}
    raw = Path(config['seed_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != config['sha256']:
        raise ValueError('Historico de continuidade alterado; exige conciliacao')
    seed = json.loads(raw)
    if seed['origin_login'] == config['target_login']:
        raise ValueError('Origem de continuidade coincide com conta atual')
    groups = {}
    for key, rows in seed['groups'].items():
        seen = set()
        output = []
        for row in rows:
            identity = str(row['id'])
            if identity in seen or not math.isfinite(float(row['net'])) or int(row['time']) <= 0:
                raise ValueError('Historico de continuidade invalido')
            seen.add(identity)
            output.append(dict(row, id=f"{seed['origin_login']}:{identity}"))
        groups[key] = output
    return groups


def continue_results(account, source, symbol, current, config_path=None):
    seed = seed_groups(account, config_path).get(f'{int(source)}/{symbol.upper()}', [])
    if not seed:
        return current
    current = [dict(row, id=f"{account['login']}:{row['id']}") for row in current]
    return sorted(seed + current, key=lambda r: (r['time'], r['id']))
