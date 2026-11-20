"""M7 mode from confirmed breaks of the original M23 realized-equity channel."""
from application.realized_equity_pivot_channels import analyze_pivot_channels

POLICY = "M23_M7_PIVOT_CHANNEL_TREND_BREAK_1_V2"
CONFIRMATIONS = 1


def channel_mode_state(results):
    study = analyze_pivot_channels(results, confirmations=CONFIRMATIONS)
    if not study['segments']:
        raise RuntimeError("M29 M7 aguarda dois topos e dois fundos confirmados para formar o canal")
    mode = "NORMAL"
    transitions = []
    previous_trend = None
    for segment in study['segments']:
        if segment['trend'] != previous_trend:
            transitions.append((segment['anchor'], 0,
                                'ESPELHADO' if segment['trend'] == 'Baixa' else 'NORMAL'))
        previous_trend = segment['trend']
    # Breaks anticipate a reversal; rebuilding the same trend must not undo them.
    transitions.extend((event['operation'], 1,
                        'ESPELHADO' if event['side'] == 'Abaixo' else 'NORMAL')
                       for event in study['events'])
    for _, _, next_mode in sorted(transitions):
        mode = next_mode
    return dict(mode=mode, mode_policy=POLICY, channel_method='PIVOS', channel_window=None,
                channel_confirmations=CONFIRMATIONS, channel=study['segments'][-1],
                channel_last_break=study['events'][-1] if study['events'] else None,
                channel_outside_count=study['consecutive'])
