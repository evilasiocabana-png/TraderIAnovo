"""Conservative Demo replay guard. Never resolves an uncertain send by guessing."""
import json
from pathlib import Path
from contextlib import contextmanager
from filelock import FileLock


def replay_reason(path, order, mode):
    from application.operational_audit import fallback_path
    attempts={}; results={}
    for source in (Path(path),fallback_path(Path(path))):
        if not source.exists():continue
        for line in source.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            row=json.loads(line)  # corrupt journal is a failure, not permission to resend
            if row.get('execution_account_mode')!=mode:continue
            key=row.get('attempt_id')
            if row.get('stage')=='ATTEMPT':attempts[key]=row
            elif row.get('stage')=='RESULT':results[key]=row
    identity=order.plan_identity
    for key,row in attempts.items():
        if row.get('symbol')!=order.symbol or row.get('operational_model')!=order.operational_model:continue
        result=results.get(key)
        if result is None:
            return 'Envio anterior sem resultado conclusivo; conciliar MT5 antes de nova tentativa.'
        old=row.get('order') or {}
        if identity not in ('','N/D',None) and old.get('plan_identity')==identity and result.get('result',{}).get('accepted'):
            return 'Plano ja aceito e persistido; repeticao bloqueada mesmo apos reinicio.'
    return ''


@contextmanager
def send_guard(path):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with FileLock(str(p)+'.send.lock',timeout=0):yield
