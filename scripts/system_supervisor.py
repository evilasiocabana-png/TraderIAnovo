"""Scheduled independent supervisor. Probe never sends orders; weekly close is explicit."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from application.system_supervisor import (CONFIG, STATE, RUNTIME, read_json, atomic_json,
                                         assess, age, display_state)
from application.operational_audit import event, fallback_path
from core.weekly_robot_schedule import weekly_robot_schedule_decision


def child(mode, timeout=25):
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), mode], cwd=ROOT,
        capture_output=True, text=True, encoding='utf-8', timeout=timeout,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('Consulta isolada falhou; código ' + str(result.returncode))
    return json.loads(result.stdout.strip().splitlines()[-1])


def configure():
    cfg = read_json(CONFIG)
    if not cfg.get('enabled'):
        raise RuntimeError('Supervisor não instalado ou configuração inválida')
    for name in ['abrir_traderianovo.ps1', 'traderianovo_ram_guard.ps1']:
        text = (ROOT/'scripts'/name).read_text(encoding='utf-8-sig')
        for key, expected in [('TRADERIA_DEMO_ACCOUNT_LOGIN', str(cfg['login'])), ('TRADERIA_DEMO_ACCOUNT_SERVER', cfg['server'])]:
            match = re.search(key + r'''\s*=\s*['"]([^'"]+)['"]''', text)
            if not match or match[1] != expected:
                raise RuntimeError('Inicializador diverge da conta Demo autorizada')
        if 'TraderIANovo' not in text or 'MT5-Demo' not in text:
            raise RuntimeError('Terminal Demo do inicializador não confirmado')
    os.environ.update(MT5_PATH=cfg['terminal'], MT5_PORTABLE='1',
        TRADERIA_DEMO_ACCOUNT_LOGIN=str(cfg['login']), TRADERIA_DEMO_ACCOUNT_SERVER=cfg['server'],
        TRADERIA_EXECUTION_ACCOUNT_MODE='DEMO', TRADERIA_REAL_EXECUTION_ENABLED='0',
        TRADERIA_DEMO_EXECUTION_ENABLED='1', TRADERIA_WEEKLY_ROBOT_SCHEDULE_ENABLED='1',
        TRADERIA_MT5_INPROCESS_ENABLED='1', TRADERIA_MT5_REPORT_EXTERNAL_PROCESS_ENABLED='1')
    return cfg


def probe():
    cfg = configure()
    import MetaTrader5 as mt5
    if not mt5.initialize(cfg['terminal'], portable=True, timeout=10000):
        raise RuntimeError('MT5 não respondeu à leitura')
    try:
        a, t = mt5.account_info(), mt5.terminal_info()
        identity = bool(a and t and a.login == cfg['login'] and a.server == cfg['server'] and a.trade_mode == 0
                        and os.path.normcase(t.path) == os.path.normcase(str(Path(cfg['terminal']).parent)))
        result = dict(identity_ok=identity, connected=bool(t and t.connected))
        if not identity:
            return result
        positions, orders = mt5.positions_get(), mt5.orders_get()
        if positions is None or orders is None:
            raise RuntimeError('Leitura de posições ou pendentes indisponível')
        result.update(positions=len(positions), pending=len(orders), markets={})
        cache = read_json(ROOT/'.traderia/mt5_m5_warm_cache.json')
        for key, candles in cache.get('markets', {}).items():
            symbol = key.split('|')[0]
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 201)
            tick = mt5.symbol_info_tick(symbol)
            times = [int(x['time']) for x in rates] if rates is not None else []
            cached_times = [int(datetime.fromisoformat(x['data']).timestamp()) for x in candles]
            result['markets'][symbol] = dict(native=times[-1] if times else None,
                cache=cached_times[-1] if cached_times else None, tick=tick.time if tick else None,
                valid=len(times)==201 and len(set(times))==201 and times==sorted(times)
                    and len(cached_times)>=200 and len(set(cached_times))==len(cached_times) and cached_times==sorted(cached_times))
        return result
    finally:
        mt5.shutdown()


def journal():
    from core.execution_log_storage import execution_log_path
    path = execution_log_path().with_name('execution_attempts.jsonl')
    attempts, results = {}, {}
    for p in (path, fallback_path(path)):
        if p.exists():
            for line in p.read_text(encoding='utf-8-sig').splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get('stage') == 'ATTEMPT': attempts[row['attempt_id']] = row
                if row.get('stage') == 'RESULT': results[row['attempt_id']] = row
    # A live in-flight send is not an orphan; do not convert uncertainty to a retry.
    orphan = [k for k in attempts.keys()-results.keys() if age(attempts[k].get('timestamp')) > 120]
    return dict(ok=bool(attempts or results), attempts=len(attempts), results=len(results), orphans=len(orphan))


def observe():
    observation = dict(operating=weekly_robot_schedule_decision().operating,
        cycle=read_json(ROOT/'.traderia/mt5_demo_robot_background_state.json'),
        online=read_json(ROOT/'.traderia/mt5_demo_robot_online_state.json'),
        daily=read_json(RUNTIME/'supervisor_daily.json'))
    # The one-minute check must never open a competing MT5 connection.
    cfg = configure()
    saved = read_json(RUNTIME/'supervisor_observations/m29_sequence.json')
    payload = saved.get('payload', {})
    a = payload.get('account') or {}
    recent = 0 <= age(saved.get('observed_at')) <= 180
    identity = a.get('login') == cfg['login'] and a.get('server') == cfg['server'] and a.get('trade_mode') == 0
    observation['passive'] = True
    observation['native'] = dict(identity_ok=recent and identity, connected=recent and payload.get('ok'),
        positions=len(payload.get('open_positions', [])) if recent and payload.get('ok') else None,
        pending=None, evidence_at=saved.get('observed_at'), mismatch=bool(a) and not identity)
    batch = read_json(RUNTIME/'supervisor_observations/forex_batch.json')
    cache = read_json(ROOT/'.traderia/mt5_m5_warm_cache.json')
    markets = {}
    if 0 <= age(batch.get('observed_at')) <= 180 and batch.get('payload', {}).get('timeframe') == 'M5':
        for symbol, values in batch.get('payload', {}).get('symbols', {}).items():
            native = [int(r['time']) for r in values.get('rates', [])]
            cached = [int(datetime.fromisoformat(r['data']).timestamp()) for r in cache.get('markets', {}).get(symbol+'|M5', [])]
            markets[symbol] = dict(native=native[-1] if native else None, cache=cached[-1] if cached else None,
                valid=len(native)>=1 and len(native)==len(set(native)) and native==sorted(native)
                and len(cached)>=200 and len(cached)==len(set(cached)) and cached==sorted(cached))
    observation['markets'] = markets
    try: observation['journal'] = journal()
    except Exception: observation['journal'] = dict(ok=False)
    try:
        with urllib.request.urlopen('http://127.0.0.1:8532/_stcore/health', timeout=4) as response:
            observation['server_ok'] = response.status == 200
    except Exception: observation['server_ok'] = False
    return observation


def notify(state):
    """Local desktop alert only, deduplicated; no messages to third parties."""
    signature = '|'.join(row['name'] for row in state.get('checks', []) if row['status']=='FAIL')
    if not signature:
        return
    path = RUNTIME/'supervisor_notification.json'
    previous = read_json(path)
    if previous.get('signature') == signature and 0 <= age(previous.get('time')) < 1800:
        return
    message = 'TraderIA: atenção no supervisor. ' + signature + '. Consulte Sistema Forex.'
    try:
        result = subprocess.run(['msg.exe', os.environ.get('USERNAME', ''), '/time:30', message],
            capture_output=True, timeout=5, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        delivered = result.returncode == 0
    except Exception: delivered = False
    atomic_json(path, dict(signature=signature, time=datetime.now(timezone.utc).isoformat(), delivered=delivered))
    event('Alerta do supervisor', 'CONFIRMADO' if delivered else 'PENDENTE',
        'Aviso enviado à sessão local do Windows.' if delivered else 'Não foi possível entregar aviso na sessão do Windows; consulte o painel.', details={'components':signature})


def run_once(repair=True):
    from filelock import FileLock, Timeout
    RUNTIME.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(str(RUNTIME/'supervisor.lock'), timeout=0):
            old = read_json(STATE)
            observation = observe()
            state = assess(observation, old)
            atomic_json(STATE, state)  # Publish holds before attempting any recovery.
            failing = [r['name'] for r in state['checks'] if r['status']=='FAIL']
            actions = []
            recovery = read_json(RUNTIME/'supervisor_recovery.json')
            repairable = any(name in failing for name in ('Painel', 'Ciclo do robô', 'Agenda e fechamento'))
            if repair and repairable and age(recovery.get('attempted_at')) > 300:
                atomic_json(RUNTIME/'supervisor_recovery.json', dict(attempted_at=datetime.now(timezone.utc).isoformat()))
                event('Reparador automático', 'TENTATIVA', 'Falha detectada; recuperação permitida acionada no mesmo ciclo. Aguardar confirmação independente.', details={'components':failing})
                state['actions'] = ['Reparador acionado; ainda não confirmado como corrigido.']
                atomic_json(STATE, state)
                if not observation.get('passive') and observation.get('native', {}).get('identity_ok') and not observation['operating'] and 'Agenda e fechamento' in failing:
                    try:
                        result = child('--weekly-close', timeout=40)
                        actions.append('Acionada a rotina existente de fechamento semanal; resultado será confirmado novamente no MT5.')
                    except Exception:
                        actions.append('Não foi possível concluir o fechamento independente; requer atenção. Nenhuma nova entrada liberada.')
                elif any(name in failing for name in ('Painel', 'Ciclo do robô', 'Agenda e fechamento')):
                    try:
                        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/ensure_traderianovo.ps1')],
                            timeout=55, capture_output=True, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                        actions.append('Executada recuperação existente do aplicativo e da sessão interna. Confirmação separada abaixo.')
                    except Exception:
                        actions.append('Recuperação não confirmou conclusão no prazo; não foi forçado reenvio ou reinício de ordens.')
                if actions:
                    state = assess(observe(), old)
                    for row in state['checks']:
                        if row['name'] in failing:
                            row.update(corrected='SIM' if row['status']=='OK' else 'NÃO', action=actions[-1])
            state['actions'] = actions
            atomic_json(STATE, state)
            # Log transitions and periodic evidence, not one identical line per minute.
            if old.get('status') != state['status'] or actions or age(old.get('last_event_at')) >= 600:
                event('Supervisor automático', {'OK':'CONFIRMADO','FAIL':'FALHA','PENDING':'PENDENTE'}[state['status']],
                    display_state(state)['label'], details={'checks':state['checks'],'actions':actions})
                state['last_event_at'] = state['updated_at']
            else: state['last_event_at'] = old.get('last_event_at')
            atomic_json(STATE, state)
            notify(state)
            return state
    except Timeout:
        return dict(status='BUSY', message='Outra checagem está em andamento.')


def weekly_close():
    configure()
    if weekly_robot_schedule_decision().operating:
        return dict(status='SKIPPED', message='Janela aberta; fechamento não permitido por esta rotina.')
    if not probe().get('identity_ok'):
        raise RuntimeError('Conta autorizada não confirmada')
    from application.dashboard_service import DashboardService
    event('Fechamento independente', 'TENTATIVA', 'Fora da janela semanal: confirmar fechamento e cancelamento na Demo autorizada.')
    result = DashboardService().close_all_demo_positions(reason='WEEKLY_FRIDAY_1730_BRT', cancel_pending=True)
    # Do not trust an accepted close: inspect the native state again.
    native = probe()
    confirmed = native.get('positions') == 0 and native.get('pending') == 0
    event('Fechamento independente', 'CONFIRMADO' if confirmed else 'PENDENTE',
          'Ausência de posições e pendências confirmada.' if confirmed else 'Ainda não foi possível confirmar conta zerada.', details=result)
    return dict(confirmed=confirmed, result=result)


def watch():
    state = read_json(STATE)
    if 0 <= age(state.get('updated_at')) <= 180:
        return dict(status='OK')
    event('Vigilância do supervisor','FALHA','Supervisor sem conclusão recente; solicitada execução pelo Windows. Novas entradas permanecem protegidas.')
    result = subprocess.run(['schtasks.exe','/Run','/TN','TraderIANovo Supervisor'], capture_output=True,
        timeout=10, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    notify(dict(checks=[dict(name='Supervisor sem atualização',status='FAIL')]))
    return dict(status='REQUESTED' if result.returncode==0 else 'FAILED')


if __name__ == '__main__':
    os.chdir(ROOT)
    parser=argparse.ArgumentParser()
    parser.add_argument('--probe',action='store_true')
    parser.add_argument('--weekly-close',action='store_true')
    parser.add_argument('--watch',action='store_true')
    parser.add_argument('--no-repair',action='store_true')
    parser.add_argument('--daily',action='store_true')
    args=parser.parse_args()
    try:
        if args.daily:
            from application.supervisor_daily import run
            result=run()
        else:
            result=probe() if args.probe else weekly_close() if args.weekly_close else watch() if args.watch else run_once(not args.no_repair)
        print(json.dumps(result,ensure_ascii=True))
    except Exception as exc:
        event('Supervisor automático','FALHA','Checagem interrompida; não marcar saudável.',details={'error_type':type(exc).__name__})
        print(json.dumps({'status':'FAIL','error_type':type(exc).__name__}))
        raise SystemExit(1)
