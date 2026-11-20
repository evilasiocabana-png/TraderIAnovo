"""Replay a source/asset realized-equity permission without future data."""

def permission(structure, channels):
    events = {e['operation']: e for e in channels['events']}
    segments = channels['segments']
    enabled = False
    previous_high = False
    last_change = None
    for point in structure['points'][1:]:
        i = point['operation']
        available = [s for s in segments if s['anchor'] <= i]
        channel = available[-1] if available else None
        high = point['state'] == 'Alta' and bool(channel) and channel['trend'] == 'Alta'
        event = events.get(i)
        side = event['side'] if event else None
        # The break uses the channel known before this result, never a refitted future line.
        if side == 'Abaixo':
            enabled = False
            last_change = dict(operation=i, trigger='ROMPIMENTO_INFERIOR', enabled=False)
        elif side == 'Acima' and point['state'] == 'Transicao':
            enabled = True
            last_change = dict(operation=i, trigger='ROMPIMENTO_SUPERIOR_TRANSICAO', enabled=True)
        elif high and not previous_high:
            enabled = True
            last_change = dict(operation=i, trigger='ALTA_CONFIRMADA', enabled=True)
        previous_high = high
    return dict(enabled=enabled, last_change=last_change)
