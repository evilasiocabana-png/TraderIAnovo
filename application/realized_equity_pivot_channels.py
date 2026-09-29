"""Causal parallel channels from confirmed realized-equity pivots."""
import math

from application.realized_equity_structure import analyze_equity_structure


def _candidate(tops, bottoms):
    if min(len(tops), len(bottoms)) < 2:
        return None
    rising = all(pair[-1]['equity'] > pair[-2]['equity'] for pair in (tops, bottoms))
    falling = all(pair[-1]['equity'] < pair[-2]['equity'] for pair in (tops, bottoms))
    if not (rising or falling):
        return None
    anchors, opposite = (bottoms[-2:], tops[-2:]) if rising else (tops[-2:], bottoms[-2:])
    a, b = anchors
    slope = (b['equity'] - a['equity']) / (b['operation'] - a['operation'])
    intercept = a['equity'] - slope * a['operation']
    residuals = [p['equity'] - slope * p['operation'] for p in opposite]
    lower, upper = (intercept, max(residuals)) if rising else (min(residuals), intercept)
    if upper <= lower:
        return None
    return dict(slope=slope, intercept=0.0, lower=lower, upper=upper,
                trend='Alta' if rising else 'Baixa', pivots=tops[-2:] + bottoms[-2:])


def analyze_pivot_channels(results, confirmations=2, sensitivity=1.0):
    if confirmations not in (1, 2, 3):
        raise ValueError('Confirmacoes invalidas')
    structure = analyze_equity_structure(results, sensitivity)
    by_confirmation = {}
    for pivot in structure['pivots']:
        by_confirmation.setdefault(pivot['confirmed'], []).append(pivot)
    tops, bottoms, segments, observations, events = [], [], [], [], []
    channel, candidate = None, None
    previous_side, consecutive = '', 0
    for point in structure['points'][1:]:
        i, equity = point['operation'], point['equity']
        if channel:
            lower = channel['slope'] * i + channel['lower']
            upper = channel['slope'] * i + channel['upper']
            # Touching is inside; a flat result may cross a sloping border.
            side = 'Acima' if equity > upper + 1e-8 else 'Abaixo' if equity < lower - 1e-8 else 'Dentro'
            consecutive = consecutive + 1 if side == previous_side and side != 'Dentro' else 0 if side == 'Dentro' else 1
            previous_side = side
            observations.append(dict(operation=i, net=point['net'], equity=equity,
                lower=lower, upper=upper, side=side, consecutive=consecutive,
                anchor=channel['anchor'], trend=channel['trend']))
            if consecutive == confirmations:
                events.append(dict(operation=i, equity=equity, side=side,
                    previous=channel['trend'], current=channel['trend'], anchor=channel['anchor']))
        new_pivots = by_confirmation.get(i, [])
        for pivot in new_pivots:
            (tops if pivot['kind'] == 'Topo' else bottoms).append(pivot)
        if new_pivots:
            candidate = _candidate(tops, bottoms)
        # Keep the same channel throughout a pending breakout confirmation.
        if candidate and (channel is None or consecutive == 0 or consecutive >= confirmations):
            changed = channel is None or any(not math.isclose(candidate[k], channel[k], abs_tol=1e-8)
                                             for k in ('slope', 'lower', 'upper'))
            if changed:
                if channel:
                    segments.append({**channel, 'end': i})
                channel = {**candidate, 'anchor': i}
                previous_side, consecutive = '', 0
    if channel:
        segments.append({**channel, 'end': len(results)})
    return dict(segments=segments, observations=observations, events=events,
                trend=channel['trend'] if channel else 'Sem estrutura', consecutive=consecutive,
                pivots=structure['pivots'])
