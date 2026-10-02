"""Cancel identified reinforcement pending orders when their current source filter blocks."""
import json
import re
from core.jsonl_tail import read_last_text_lines
from application.source_channel_gate import POLICY, SOURCES, reference_state


def identity(order, record, account, robot_magic):
    if not record.get('accepted') or record.get('execution_account_mode')!='DEMO':return None
    if (record.get('observed_account_login')!=account.login or record.get('observed_account_server')!=account.server):return None
    if str(record.get('ticket'))!=str(order.ticket) or record.get('symbol')!=order.symbol:return None
    if order.type not in (2,3,4,5,6,7):return None
    if record.get('side')!=('BUY' if order.type in (2,4,6) else 'SELL'):return None
    p=(record.get('plan_snapshot') or {}).get('stop_management_parameters') or {}
    if p.get('reinforcement_policy')!=POLICY:return None
    source=p.get('reinforcement_source')
    if source not in SOURCES:return None
    model=str(record.get('operational_model',''))
    if model.startswith('MODELO_30_'):
        expected_magic=260630; pattern=rf'\bM30 S{source}\b'
    elif model.startswith('MODELO_29_'):
        expected_magic=robot_magic;pattern=rf'\bM29 S{source}\b'
    elif model=='MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29':
        expected_magic=robot_magic;pattern=rf'\bM23 S29 M{source}\b'
    else:return None
    if order.magic!=expected_magic or not re.search(pattern,order.comment):return None
    return source


def cancel_downtrend_pending(provider):
    result=dict(cancelled=0,rejected=0,skipped=0)
    rejection=provider._initialize_check() or provider._demo_account_check()
    if rejection is not None:return {**result,'error':rejection.message}
    account=provider.mt5.account_info()
    if account is None or str(provider.execution_account.mode)!='DEMO':return {**result,'error':'Conta Demo nao confirmada'}
    orders=provider.mt5.orders_get()
    if orders is None:return {**result,'error':'Pendencias indisponiveis'}
    if not orders:return result
    tickets={str(o.ticket) for o in orders};records={}
    for line in read_last_text_lines(provider.log_path,limit=10000):
        try:r=json.loads(line)
        except (ValueError,TypeError):continue
        if isinstance(r,dict) and str(r.get('ticket')) in tickets and r.get('accepted'):
            records[str(r['ticket'])]=r
    states={}
    for order in orders:
        record=records.get(str(order.ticket),{})
        source=identity(order,record,account,provider.magic)
        if source is None:
            result['skipped']+=1;continue
        try:
            key=(source,order.symbol)
            if key not in states:states[key]=reference_state(provider,order.symbol,source)
            if not states[key]['blocked']:continue
            live=provider.mt5.orders_get(ticket=int(order.ticket))
            if not live or not any(identity(o,record,account,provider.magic)==source for o in live):continue
            response=provider._checked_order_send(dict(action=provider.mt5.TRADE_ACTION_REMOVE,
                order=int(order.ticket),symbol=order.symbol,comment='TraderIA channel filter'))
            accepted=getattr(response,'retcode',None)==getattr(provider.mt5,'TRADE_RETCODE_DONE',10009)
            result['cancelled' if accepted else 'rejected']+=1
            provider._write_management_log(dict(type='REINFORCEMENT_CHANNEL_FILTER_CANCEL',reason=states[key].get('reason','canal de baixa'),filter_version=states[key].get('filter_version'),channel=states[key].get('state'),zone=states[key].get('zone'),ticket=int(order.ticket),symbol=order.symbol,source=source,accepted=accepted,retcode=getattr(response,'retcode',None)))
        except Exception as exc:
            result['rejected']+=1
            provider._write_management_log(dict(type='REINFORCEMENT_CHANNEL_CANCEL_BLOCKED',ticket=int(order.ticket),reason=str(exc)[:200]))
    return result
