"""Read-only native MT5 check for rapid same-route XAU re-entry."""
from datetime import datetime, timezone


def route(model):
    model = str(model or '').upper()
    if model.startswith('MODELO_7_'):
        return {'M7'}
    return None


def rejection(mt5, order, tick, magic):
    expected = route(getattr(order, 'operational_model', ''))
    if str(order.symbol).upper() != 'XAUUSD' or expected is None:
        return None
    try:
        now = float(tick.time)
        if now <= 0:
            raise ValueError('tick sem horario')
        deals = mt5.history_deals_get(datetime.fromtimestamp(now-120, timezone.utc), datetime.fromtimestamp(now+1, timezone.utc))
        positions = mt5.positions_get(symbol=order.symbol)
        if deals is None or positions is None:
            raise ValueError('historico indisponivel')
        opened = {int(getattr(p, 'identifier', p.ticket)) for p in positions}
        candidates = []
        for d in deals:
            if d.symbol != order.symbol or d.entry not in (1, 3) or not 0 <= now-d.time <= 60 or d.position_id in opened:
                continue
            history = mt5.history_deals_get(position=d.position_id)
            if history is None:
                raise ValueError('posicao sem historico')
            entries = [x for x in history if x.entry == 0]
            if not entries:
                continue
            first = min(entries, key=lambda x:x.time)
            tokens = set(str(first.comment).upper().split())
            if first.magic != magic or not expected.issubset(tokens) or ('M23' in tokens and expected == {'M7'}):
                continue
            # Exclude partial exits even if terminal position data is delayed.
            exits = [x for x in history if x.entry in (1,3)]
            if abs(sum(x.volume for x in entries)-sum(x.volume for x in exits)) > 1e-8:
                continue
            candidates.append((max(x.time for x in exits), first.type))
        if not candidates:
            return None
        closed, direction = max(candidates)
        if direction != (0 if str(order.side).upper() == 'BUY' else 1):
            return None
        rates = mt5.copy_rates_from_pos(order.symbol, mt5.TIMEFRAME_M5, 0, 4)
        if rates is None or not len(rates):
            raise ValueError('candles M5 indisponiveis')
        if any(closed < int(r['time'])+300 <= now for r in rates):
            return None
        return 'M7 XAU: repeticao na mesma direcao em ate 60s, sem novo M5 fechado apos a saida.'
    except Exception:
        return 'M7 XAU: entrada suspensa porque nao foi possivel verificar a protecao de repeticao.'
