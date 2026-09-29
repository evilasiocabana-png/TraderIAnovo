"""Independent M30 source route and causal floor policy (new entries only)."""
from dataclasses import replace
import json
import math
import os
import re
import threading
from application.learning_store import LearningStore, digest, encoded, now
from application.realized_equity_pivot_channels import analyze_pivot_channels
from domain.contracts.execution_result import ExecutionResult

POLICY = "M30_M23_ORIGINAL_M7_CHANNEL_V1"
_LOCK = threading.RLock()
SOURCES = frozenset({"M1", "M2", "M5", "M7", "M8", "M10", "M18", "M20"})


def floor_state(results):
    """Causal mode from ORIGINAL M23/M7 equity, not M29 or M30 outcomes.

    Rising channel: below floor mirrors, reentry (including roof breakout)
    normalizes. Falling channel mirrors; breaking its roof normalizes.
    A closure is compared to geometry known before that closure. New confirmed
    trend applies only after confirmation. Repeated below-floor closes hold mode.
    """
    unique, seen = [], set()
    for result in results:
        if result['id'] in seen:
            continue
        seen.add(result['id'])
        unique.append(result)
    study = analyze_pivot_channels(unique, confirmations=1, sensitivity=1.0)
    observations = {o['operation']: o for o in study['observations']}
    anchors = {c['anchor']: c for c in study['segments']}
    mode, events, channel = 'NORMAL', [], None
    for i in range(1, len(unique)+1):
        previous = mode
        observed = observations.get(i)
        if observed:
            mode = ('ESPELHADO' if observed['side'] == 'Abaixo' else 'NORMAL') if observed['trend'] == 'Alta' else ('NORMAL' if observed['side'] == 'Acima' else 'ESPELHADO')
        new = anchors.get(i)
        if new:
            if channel is None or new['trend'] != channel['trend']:
                mode = 'ESPELHADO' if new['trend'] == 'Baixa' else 'NORMAL'
            channel = new
        if mode != previous:
            events.append(dict(operation=i, mode=mode, result=unique[i-1]['id']))
    return dict(mode=mode, channel=channel, events=events, closed=len(unique),
                reference=digest(unique), policy=POLICY)


def tables(db):
    db.execute('''CREATE TABLE IF NOT EXISTS m30_independent_attempts
        (id TEXT PRIMARY KEY, account TEXT NOT NULL, source TEXT NOT NULL,
         symbol TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL,
         ticket INTEGER, snapshot TEXT NOT NULL, reason TEXT NOT NULL)''')


def account_id(provider):
    a = provider.mt5.account_info()
    if (a is None or a.trade_mode != provider.mt5.ACCOUNT_TRADE_MODE_DEMO
            or a.margin_mode != provider.mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
            or provider.execution_account.mode != 'DEMO'):
        raise ValueError('M30 independente exige Demo hedging confirmada')
    return str(a.login) + '@' + str(a.server)


def reference_state(provider, symbol, store=None):
    """Read broker-confirmed closed original M23/M7 positions, account isolated."""
    from application.model29_sequence_history import closed_m7_positions
    store = store or LearningStore()
    account = account_id(provider)
    payload = provider._external_mt5_read('m29_sequence', portable=os.getenv('MT5_PORTABLE','0') == '1')
    a = payload.get('account') or {}
    identity = str(a.get('login')) + '@' + str(a.get('server'))
    if not payload.get('ok') or identity != account or a.get('trade_mode') != provider.mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise ValueError('M30 aguarda historico nativo da mesma conta Demo')
    # Native tickets must not be counted twice; incomplete cost evidence fails closed.
    deals = {int(d['ticket']): d for d in payload.get('rows', [])}
    payload = dict(payload, rows=list(deals.values()))
    source = [r for r in closed_m7_positions(payload) if r['model'] == 23 and r['symbol'] == symbol.upper()]
    ids = {r['position'] for r in source}
    for d in deals.values():
        if str(d.get('position_id')) in ids and not all(k in d for k in ('profit','commission','swap','fee')):
            raise ValueError('M30 referencia sem custos completos')
    key = 'm30_channel_reference:' + digest([account, symbol, POLICY])
    with store.connect() as db:
        old = db.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
        if old and not set(json.loads(old[0])).issubset(ids):
            raise ValueError('M30 recebeu historico original M23 incompleto')
        db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', (key,encoded(sorted(ids))))
    return floor_state([dict(id=r['position'], net=r['net'], time=r['closed']) for r in source])


def variant(row, plan, source, state, volume):
    from application.model30_learning import MODEL_30_ID
    number = re.search(r'MODELO_(\d+)', source)[1]
    model = MODEL_30_ID + '_SOURCE_M' + number
    p = dict(plan.stop_management_parameters or {})
    if any(k.startswith('m29_') or k.startswith('m23_m29_') for k in p):
        raise ValueError('M30 exige fonte original, sem inversao herdada do M29')
    mode = state['mode'] if number == '7' else 'NORMAL'
    side, stop, target = plan.direction, plan.stop, plan.target
    if mode == 'ESPELHADO':
        risk = abs(float(plan.entry_price)-float(stop))
        if risk <= 0:
            raise ValueError('M30 M7 sem risco estrutural valido')
        side = 'SELL' if side == 'BUY' else 'BUY'
        target, stop = stop, 2*float(plan.entry_price)-float(stop)
        order_type = p.get('active_entry_order_type')
        if order_type:
            p['active_entry_order_type'] = {'BUY_STOP':'SELL_LIMIT','SELL_STOP':'BUY_LIMIT',
                'BUY_LIMIT':'SELL_STOP','SELL_LIMIT':'BUY_STOP','BUY':'SELL','SELL':'BUY'}.get(order_type, order_type)
    p.update(source_operational_model=source, source_entry_setup=row.active_model,
        source_initial_stop=plan.stop, source_target=plan.target,
        source_stop_management=plan.stop_management, source_exit_model=plan.exit_model,
        m30_policy=POLICY, m30_mode=mode, m30_reference=state['reference'],
        m30_baseline_model=source, m30_execution_volume=float(volume),
        m30_effective_stop=stop, m30_effective_target=target)
    new_plan = replace(plan, direction=side, stop=stop, target=target,
        risk_reward=1.0 if mode == 'ESPELHADO' else plan.risk_reward,
        stop_management_parameters=p)
    new_row = replace(row, decision=side, theoretical_entry_direction=side,
        active_model='M30 | ' + row.active_model)
    return model, new_row, new_plan


def key_for(order, account):
    s = order.plan_snapshot or {}
    p = s.get('stop_management_parameters') or {}
    # One source signal cannot be sent again merely because the mode changed.
    return digest([POLICY, account, order.symbol, p.get('source_operational_model'),
                   s.get('timeframe'), s.get('candle_time'), p.get('source_entry_setup')])


def submit(fn, provider, order, store=None):
    store = store or LearningStore()
    def rejected(reason):
        result = ExecutionResult(False, 'REJECTED', reason)
        provider._write_log(order, result)
        return result
    try:
        account = account_id(provider)
        p = (order.plan_snapshot or {}).get('stop_management_parameters') or {}
        source = re.search(r'MODELO_(\d+)', p.get('source_operational_model',''))
        if p.get('m30_policy') != POLICY or not source:
            return rejected('M30 requer plano independente da politica atual')
        source = 'M' + source[1]
        if any(k.startswith('m29_') or k.startswith('m23_m29_') for k in p):
            return rejected('M30 nao herda contratos espelhados do M29')
        if (order.plan_snapshot or {}).get('candle_time') in (None, '', 'N/D', 'UNKNOWN'):
            return rejected('M30 sem candle de origem identificado')
        with _LOCK:
            if source not in SOURCES:
                return rejected('M30 fonte original nao autorizada')
            if source == 'M7':
                state = reference_state(provider, order.symbol, store)
                if state['reference'] != p.get('m30_reference') or state['mode'] != p.get('m30_mode'):
                    return rejected('M30 aguarda plano atualizado do M7 original no M23')
            from application.learning_policy import admission
            decision = admission(order.plan_snapshot, store, account=account)
            identity = key_for(order, account)
            with store.connect() as db:
                tables(db)
                db.execute('BEGIN IMMEDIATE')
                if db.execute("SELECT 1 FROM m30_independent_attempts WHERE account=? AND source=? AND symbol=? AND status IN ('SENDING','UNCERTAIN')", (account,source,order.symbol)).fetchone():
                    return rejected('M30 aguarda resolver envio anterior da mesma fonte')
                added = db.execute('INSERT OR IGNORE INTO m30_independent_attempts VALUES (?,?,?,?,?,?,?,?,?)',
                    (identity,account,source,order.symbol,now(),'SENDING' if decision['allowed'] else 'FILTERED',None,encoded(order.plan_snapshot),decision['reason'])).rowcount
            if not added:
                return rejected('M30 sinal independente ja avaliado; envio duplicado bloqueado')
            if not decision['allowed']:
                return rejected(decision['reason'])
            try:
                result = fn(provider, order)
            except Exception:
                with store.connect() as db:
                    db.execute("UPDATE m30_independent_attempts SET status='UNCERTAIN',reason='Resultado de envio desconhecido' WHERE id=?", (identity,))
                raise
            with store.connect() as db:
                db.execute('UPDATE m30_independent_attempts SET status=?,ticket=?,reason=? WHERE id=?',
                    ('ACCEPTED' if result.accepted else 'REJECTED',result.ticket,result.message,identity))
            return result
    except Exception as exc:
        return rejected('M30 independente indisponivel: ' + str(exc)[:200])


def preflight(provider, order, store=None):
    from application.model30_learning import matches
    store = store or LearningStore()
    account = account_id(provider)
    with store.connect() as db:
        tables(db)
        row = db.execute('SELECT * FROM m30_independent_attempts WHERE id=?', (key_for(order,account),)).fetchone()
    if not row or row['status'] != 'SENDING' or row['snapshot'] != encoded(order.plan_snapshot):
        return 'M30 sem contrato independente persistido'
    p = order.plan_snapshot.get('stop_management_parameters') or {}
    if (float(p.get('m30_execution_volume',0)) != order.quantity or
            float(p.get('m30_effective_stop',0)) != order.stop or
            float(p.get('m30_effective_target',0) or 0) != float(order.target or 0)):
        return 'M30 contrato independente divergente'
    positions, orders = provider.mt5.positions_get(), provider.mt5.orders_get()
    if positions is None or orders is None:
        return 'M30 nao confirmou posicoes e pendencias'
    source = row['source'][1:]
    if any(matches(p) and ('S'+source) in str(getattr(p,'comment','')).split() and p.symbol == order.symbol for p in [*positions,*orders]):
        return 'M30 aguarda encerrar posicao ou pendencia propria da fonte'
    return ''


def page(store=None):
    store = store or LearningStore()
    if not store.path.exists():
        return []
    with store.connect() as db:
        tables(db)
        return [dict(r) for r in db.execute("SELECT * FROM m30_independent_attempts ORDER BY created_at DESC LIMIT 100")]
