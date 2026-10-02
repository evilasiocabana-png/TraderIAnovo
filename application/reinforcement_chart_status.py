"""Read-only chart indication; never represents an order as executed."""
from application.source_channel_gate import SOURCES, reconciled_results, channel_state


def chart_status(payload, source, symbols=()):
    try:
        number=int(source.removeprefix('M'))
    except (ValueError,AttributeError):
        return []
    if number not in SOURCES:
        return ["Sem reforco M29/M30 configurado para esta fonte."]
    account=payload.get('account') or {}
    if not payload.get('ok') or account.get('trade_mode') != 0 or account.get('margin_mode') != 2:
        return ["Reforco: status indisponivel; referencia Demo nao confirmada."]
    symbols=sorted(set(symbols)) or ['XAUUSD']
    result=[]
    for symbol in symbols:
        destinations='M29 e M30' if symbol=='XAUUSD' else 'M30'
        try:
            state=channel_state(reconciled_results(payload,number,symbol))
            from application.gold_reinforcement_filter import apply_filter
            state=apply_filter(state,number,symbol)
            status='SUSPENSO' if state['blocked'] else 'PERMITIDO'
            result.append(f"{symbol}: reforco {destinations} {status} pelo canal ({state['state']}).")
        except (ValueError,TypeError,KeyError,OverflowError):
            result.append(f"{symbol}: reforco {destinations} INDISPONIVEL; aguardando conciliacao.")
    return result


def trading_reinforcement_text(rows):
    """Describe only broker-confirmed open positions/pending orders of this policy."""
    from application.source_channel_gate import POLICY
    groups={"ABERTA":set(),"ORDEM_ABERTA":set()}
    for row in rows:
        status=str(getattr(row,'operation_status','')).upper()
        if status not in groups or not getattr(row,'mt5_found',False) or not getattr(row,'mt5_ticket',None):
            continue
        snapshot=getattr(row,'plan_snapshot',None)
        if not isinstance(snapshot,dict):continue
        p=snapshot.get('stop_management_parameters') or {}
        if not isinstance(p,dict) or p.get('reinforcement_policy')!=POLICY:continue
        model=str(getattr(row,'operational_model',''))
        if model.startswith('MODELO_30_'):route='M30'
        elif model.startswith('MODELO_29_'):route='M29'
        elif model.startswith('MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29'):route='M29 executado pelo M23'
        else:continue
        source=p.get('reinforcement_source')
        if source not in SOURCES:continue
        groups[status].add(f"M{source} / {getattr(row,'symbol','N/D')} via {route}")
    text=["Modelos com reforco em posicao: " + ("; ".join(sorted(groups['ABERTA'])) if groups['ABERTA'] else "nenhum confirmado na politica atual.")]
    if groups['ORDEM_ABERTA']:
        text.append("Reforcos com ordem pendente, ainda sem entrada: " + "; ".join(sorted(groups['ORDEM_ABERTA'])))
    text.append("Ausencia de reforco aberto nao significa suspensao pelo canal. Posicoes de regras anteriores nao entram neste resumo.")
    return text
