"""Independent supervision: observations are not execution confirmations."""
import json
import os
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.traderia/runtime'
CONFIG = RUNTIME / 'supervisor_config.json'
STATE = RUNTIME / 'supervisor_state.json'
MAX_AGE = 180


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {} if default is None else default


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.new')
    with tmp.open('w', encoding='utf-8') as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def age(timestamp, now=None):
    try:
        value = datetime.fromisoformat(timestamp)
        if value.tzinfo is None:
            return float('inf')
        return ((now or datetime.now(timezone.utc)) - value).total_seconds()
    except (ValueError, TypeError):
        return float('inf')


def check(name, status, explanation, *, corrected=None, action=None, critical=False):
    corrected = corrected or ('NÃO NECESSÁRIO' if status == 'OK' else 'NÃO')
    action = action or ('Nenhuma intervenção necessária.' if status == 'OK' else 'Verificar evidência e causa antes de reparar.')
    return dict(name=name, status=status, explanation=explanation, action=action,
                checked='NÃO' if status=='PENDING' else 'SIM', error={'OK':'NÃO', 'FAIL':'SIM', 'PENDING':'NÃO DETERMINADO'}[status],
                corrected=corrected, critical=critical)


def assess(observation, previous=None, now=None):
    now = now or datetime.now(timezone.utc)
    previous = previous or {}
    rows = []
    operating = observation['operating']
    native = observation.get('native') or {}
    identity = native.get('identity_ok', False)
    rows.append(check('Conta e conexão MT5', 'OK' if identity and native.get('connected') else 'PENDING' if observation.get('passive') and not native.get('mismatch') else 'FAIL',
        'Conta Demo autorizada e conexão confirmadas.' if identity and native.get('connected') else
        'Não foi possível confirmar a conta Demo autorizada e a conexão nesta checagem; proteção operacional existente preservada.', critical=True))
    cycle_age = age(observation.get('cycle', {}).get('updated_at'), now)
    cycle_ok = 0 <= cycle_age <= MAX_AGE
    online = observation.get('online', {}).get('online') is True
    rows.append(check('Ciclo do robô', 'OK' if cycle_ok or not operating else 'FAIL',
        ('Ciclo recente; ausência de sinal não significa falha.' if operating else 'Fora da janela semanal: não é exigido ciclo de entradas.')
        if cycle_ok or not operating else 'Ciclo sem confirmação recente. Servidor responder não comprova funcionamento.', critical=operating))
    counts_known = isinstance(native.get('positions'), int) and isinstance(native.get('pending'), int)
    agenda_ok = online if operating else (not online and counts_known and native['positions'] == 0 and native['pending'] == 0)
    rows.append(check('Agenda e fechamento', 'OK' if agenda_ok else 'PENDING' if observation.get('passive') and not operating and not counts_known else 'FAIL',
        ('Janela aberta e robô armado.' if operating else 'Desligado e ausência de posições e ordens confirmada no MT5.') if agenda_ok else
        ('Horário de operação, mas ativação não confirmada.' if operating else 'Fechamento ainda não confirmado: verificar posições e ordens no MT5.'), critical=True))
    journal = observation.get('journal', {})
    good = journal.get('ok') is True and journal.get('orphans', 0) == 0
    rows.append(check('Gravação de tentativas e resultados', 'OK' if good else 'FAIL',
        f"{journal.get('attempts', 0)} tentativas e {journal.get('results', 0)} resultados; sem envio incerto pendente." if good else
        'Registro indisponível, corrompido ou tentativa antiga sem resultado. Não repetir ordens automaticamente.', critical=True))
    cycle_status = str(observation.get('cycle', {}).get('result_status', ''))
    if 'READ_ERROR' in cycle_status:
        rows.append(check('Leitura operacional', 'FAIL', 'O próprio ciclo informou falha de leitura; ciclo recente não comprova leitura saudável.', critical=True))
    blocked_symbols = []
    lagging, unknown, no_quotes = [], [], []
    for symbol, market in observation.get('markets', {}).items():
        if not market.get('native') or not market.get('cache') or not market.get('valid'):
            unknown.append(symbol); blocked_symbols.append(symbol)
        elif market['native'] - market['cache'] > 300:
            lagging.append(symbol); blocked_symbols.append(symbol)
        elif market['native'] > market['cache']:
            lagging.append(symbol)
        elif market['cache'] > market['native']:
            lagging.append(symbol)  # Different observation instants are not proof of alignment.
        old = previous.get('markets', {}).get(symbol, {})
        if old.get('tick') and old['tick'] == market.get('tick'):
            no_quotes.append(symbol)
    if not observation.get('markets'):
        unknown.append('universo não disponível')
    market_status = 'PENDING' if observation.get('passive') and not observation.get('markets') else 'FAIL' if blocked_symbols or unknown else 'PENDING' if lagging else 'OK'
    rows.append(check('Janelas e candles', market_status,
        'Janelas válidas e alinhadas ao MT5.' if market_status == 'OK' else
        'Divergência ou leitura incompleta: ' + ', '.join(sorted(set(lagging + unknown))), critical=not observation.get('markets')))
    if no_quotes:
        rows.append(check('Cotação e sessão dos ativos', 'PENDING',
            'Sem novo tick entre consultas também no terminal: ' + ', '.join(no_quotes) + '. Não foi interpretado como falha de cache; sessão requer confirmação.'))
    if observation.get('server_ok') is not True:
        rows.append(check('Painel', 'FAIL', 'O painel não respondeu à verificação.', critical=False))
    else:
        rows.append(check('Painel', 'OK', 'Servidor respondeu. Resultado independente da saúde do ciclo.'))
    daily = observation.get('daily', {})
    rows.append(check('Auditoria horária', 'OK' if daily.get('ok') and 0 <= age(daily.get('finished_at'), now) < 75*60 else 'FAIL' if daily.get('status') == 'FAIL' else 'PENDING',
        daily.get('summary') or 'Ainda não há auditoria horária recente confirmada. Não equivale à checagem de um minuto.'))
    blocked = any(x['status'] == 'FAIL' and x['critical'] for x in rows)
    status = 'FAIL' if any(x['status'] == 'FAIL' for x in rows) else 'PENDING' if any(x['status'] == 'PENDING' for x in rows) else 'OK'
    return dict(updated_at=now.isoformat(), status=status, checks=rows, block_entries=blocked,
                blocked_symbols=sorted(set(blocked_symbols)), markets=observation.get('markets', {}),
                cycle_updated_at=observation.get('cycle', {}).get('updated_at'), operating=operating,
                actions=[], next_check_seconds=60)


def entry_hold_reason(symbol, *, root=ROOT, now=None):
    config_path = Path(root)/'.traderia/runtime/supervisor_config.json'
    if not config_path.exists():
        return ''  # Existing installations opt in explicitly.
    config = read_json(config_path)
    if not config or config.get('enabled') is not True:
        return 'Supervisor instalado sem configuração válida; novas entradas bloqueadas.'
    state = read_json(Path(root)/'.traderia/runtime/supervisor_state.json')
    elapsed = age(state.get('updated_at'), now)
    if not 0 <= elapsed <= MAX_AGE:
        return 'Supervisor sem verificação recente; novas entradas bloqueadas, saídas preservadas.'
    if state.get('block_entries') or symbol.upper() in state.get('blocked_symbols', []):
        return 'Supervisor identificou falha de integridade; aguarde verificação e recuperação.'
    return ''


def serialized_weekly_close(fn):
    """One weekly close worker at a time, including the independent supervisor."""
    @wraps(fn)
    def wrapped(*args, **kwargs):
        from filelock import FileLock, Timeout
        RUNTIME.mkdir(parents=True, exist_ok=True)
        try:
            with FileLock(str(RUNTIME/'weekly_close.lock'), timeout=0):
                return fn(*args, **kwargs)
        except Timeout:
            return dict(status='BUSY', remaining=None, message='Outro fechamento em andamento; aguardar confirmação.')
    return wrapped


def display_state(state, now=None):
    result = dict(state or {})
    if not 0 <= age(result.get('updated_at'), now) <= MAX_AGE:
        result.update(status='FAIL', label='Supervisor sem confirmação recente — atenção necessária')
    else:
        result['label'] = {'OK':'Supervisor funcionando — itens verificados sem erro',
                           'FAIL':'Supervisor detectou falha — reparo ou intervenção necessária',
                           'PENDING':'Supervisor funcionando — há verificações pendentes'}.get(result.get('status'), 'Verificação incompleta')
    return result


def render(st):
    state = display_state(read_json(STATE))
    with st.expander('Supervisor automático — o que foi feito', expanded=True):
        color = {'OK':st.success, 'FAIL':st.error, 'PENDING':st.warning}.get(state['status'], st.warning)
        color(state['label'])
        st.checkbox('Checagem recente concluída sem falhas nem pendências', value=state['status']=='OK', disabled=True, key='supervisor_health_indicator')
        st.caption('Verificação prevista a cada minuto. Verde: confirmado; vermelho: falha; amarelo: pendência. Não promete ausência de falhas.')
        stamp = state.get('updated_at')
        if stamp:
            from zoneinfo import ZoneInfo
            st.caption('Última checagem: ' + datetime.fromisoformat(stamp).astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M:%S') + ' — Brasília')
        for row in state.get('checks', []):
            show = {'OK':st.success, 'FAIL':st.error, 'PENDING':st.warning}.get(row['status'], st.warning)
            show(row['name'] + ': ' + row['explanation'])
            st.caption('Checado: '+row['checked']+' | Erro: '+row['error']+' | Corrigido: '+row['corrected']+' | Ação: '+row['action'])
        for action in state.get('actions', []):
            st.info(action)
        hourly = read_json(RUNTIME/'supervisor_daily.json')
        for row in hourly.get('checks', []):
            show = {'OK':st.success, 'FAIL':st.error, 'PENDING':st.warning}.get(row['status'], st.warning)
            show('Auditoria horária — '+row['name']+': '+row['explanation'])
            st.caption('Checado: '+row['checked']+' | Erro: '+row['error']+' | Corrigido: '+row['corrected'])
        st.caption('Supervisor observa e registra; as proteções operacionais existentes continuam sendo a barreira antes do envio. Auditoria horária não consulta o MT5 em paralelo e não altera estratégias ou posições.')
