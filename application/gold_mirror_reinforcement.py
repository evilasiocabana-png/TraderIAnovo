"""Versioned RR1 mirrors; no retroactive management of legacy positions."""
from dataclasses import replace
import json
import math
import re
from core.jsonl_tail import read_last_text_lines

EXIT_POLICY = 'GOLD_MIRROR_RR1_SLTP_V1'


def is_mirror(p):
    return p.get('reinforcement_exit_policy') == EXIT_POLICY and p.get('reinforcement_mode') == 'ESPELHADO'


def mirror_plan(plan, parameters):
    p = dict(parameters)
    entry, stop = float(plan.entry_price), float(plan.stop)
    sign = 1 if plan.direction == 'BUY' else -1
    distance = sign * (entry-stop)
    if plan.direction not in ('BUY','SELL') or not all(math.isfinite(x) and x>0 for x in (entry,stop,distance)):
        raise ValueError('Espelho sem distancia estrutural valida')
    side = 'SELL' if plan.direction == 'BUY' else 'BUY'
    p.update(reinforcement_mode='ESPELHADO',reinforcement_exit_policy=EXIT_POLICY,
             reinforcement_original_entry=entry,reinforcement_original_stop=stop,
             reinforcement_risk_distance=distance,reinforcement_original_direction=plan.direction,
             active_entry_order_type='MARKET',m29_structural_target_enabled=False,
             m29_original_direction=plan.direction)
    return replace(plan,direction=side,stop=entry+sign*distance,target=entry-sign*distance,
                   risk_reward=1.0,stop_management=EXIT_POLICY,exit_model=EXIT_POLICY,
                   stop_management_parameters=p)


def original_confirmation(provider, order):
    """An accepted pending order is NOT a confirmed original fill."""
    p=(order.plan_snapshot or {}).get('stop_management_parameters') or {}
    if not is_mirror(p):return None
    source=int(p['reinforcement_source']);snapshot=order.plan_snapshot
    candle=snapshot.get('candle_time')
    if not candle or candle in ('N/D','UNKNOWN'):raise ValueError('Espelho sem candle identificado')
    account=provider.mt5.account_info()
    if account is None or account.trade_mode!=provider.mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise ValueError('Espelho exige Demo confirmada')
    positions=provider.mt5.positions_get()
    if positions is None:raise ValueError('Posicoes originais indisponiveis')
    candidates=[]
    for line in read_last_text_lines(provider.log_path,limit=10000):
        try:r=json.loads(line)
        except (ValueError,TypeError):continue
        if (not r.get('accepted') or r.get('execution_account_mode')!='DEMO'
            or r.get('observed_account_login')!=account.login or r.get('observed_account_server')!=account.server
            or r.get('operational_model')!=f'MODELO_23_BASKET_ACCUMULATOR_SOURCE_M{source}'
            or r.get('symbol')!=order.symbol or r.get('side')!=p['reinforcement_original_direction']):continue
        original=r.get('plan_snapshot') or {};op=original.get('stop_management_parameters') or {}
        if original.get('candle_time')!=candle or original.get('timeframe')!=snapshot.get('timeframe'):continue
        if op.get('source_entry_setup')!=p.get('source_entry_setup'):continue
        # Ticket can refer to a pending order: require filled broker order and its open position.
        ticket=int(r.get('ticket') or 0)
        hist=provider.mt5.history_orders_get(ticket=ticket)
        if hist is None:raise ValueError('Confirmacao da ordem original indisponivel')
        for native in hist:
            if native.state!=provider.mt5.ORDER_STATE_FILLED:continue
            for pos in positions:
                if (pos.identifier==native.position_id and pos.symbol==order.symbol and pos.magic==provider.magic
                    and re.search(rf'\bM23 S{source}\b',pos.comment)
                    and pos.type==(0 if p['reinforcement_original_direction']=='BUY' else 1)):
                    candidates.append((ticket,pos))
    unique={ticket:pos for ticket,pos in candidates}
    if len(unique)!=1:raise ValueError('Espelho aguarda uma entrada M23 executada do mesmo sinal')
    ticket,pos=next(iter(unique.items()))
    return dict(ticket=ticket,position=int(pos.identifier))


def protect_request(provider, order, request):
    p=(order.plan_snapshot or {}).get('stop_management_parameters') or {}
    if not is_mirror(p):return order,request
    from application.model23_fixed_loss_stop import protected_request
    from types import SimpleNamespace
    entry=float(request['price']);distance=float(p['reinforcement_risk_distance'])
    if not math.isfinite(distance) or distance<=0:raise ValueError('Distancia do espelho invalida')
    sign=1 if order.side=='BUY' else -1
    info=provider.mt5.symbol_info(order.symbol);tick=float(info.trade_tick_size);digits=int(info.digits)
    # Align inward, never increase structural risk.
    raw=entry-sign*distance
    stop=round((math.ceil(raw/tick) if sign==1 else math.floor(raw/tick))*tick,digits)
    proxy=SimpleNamespace(operational_model='MODELO_23_BASKET_ACCUMULATOR_SOURCE_M7',symbol=order.symbol,side=order.side)
    req=protected_request(proxy,dict(request,sl=stop),provider.mt5,limit_usd=400.0)
    req['tp']=round(2*entry-float(req['sl']),digits)
    if sign*(entry-req['sl'])<=0 or sign*(req['tp']-entry)<=0:raise ValueError('RR1 nao representavel')
    snap=dict(order.plan_snapshot or {});pp=dict(p)
    pp.update(m30_effective_stop=req['sl'],m30_effective_target=req['tp'])
    snap.update(stop_management_parameters=pp,stop=req['sl'],target=req['tp'],risk_reward=1.0,
                reinforcement_applied_entry=entry,reinforcement_applied_stop=req['sl'],reinforcement_applied_target=req['tp'],reinforcement_loss_limit=400.0)
    return replace(order,stop=req['sl'],target=req['tp'],plan_snapshot=snap),req
