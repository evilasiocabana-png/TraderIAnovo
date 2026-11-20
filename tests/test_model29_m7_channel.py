import pytest
from application.model29_m7_channel import channel_mode_state, POLICY


@pytest.mark.parametrize('trends,breaks,expected', [
    (['Baixa'], [], 'ESPELHADO'),
    (['Alta'], [], 'NORMAL'),
    (['Alta'], [(7, 'Abaixo')], 'ESPELHADO'),
    (['Baixa'], [(7, 'Acima')], 'NORMAL'),
    (['Alta', 'Alta'], [(7, 'Abaixo')], 'ESPELHADO'),
    (['Baixa', 'Baixa'], [(7, 'Acima')], 'NORMAL'),
    (['Alta', 'Baixa'], [], 'ESPELHADO'),
    (['Baixa', 'Alta'], [], 'NORMAL'),
])
def test_trend_and_anticipatory_break(monkeypatch, trends, breaks, expected):
    study = dict(segments=[dict(anchor=6+2*i, trend=t) for i,t in enumerate(trends)],
                 events=[dict(operation=i, side=s) for i,s in breaks], consecutive=0)
    monkeypatch.setattr('application.model29_m7_channel.analyze_pivot_channels',
                        lambda *args, **kwargs: study)
    assert channel_mode_state([])['mode'] == expected


def evaluate(values):
    return channel_mode_state([dict(net=v) for v in values])


def test_one_below_mirror_one_above_normal():
    base=[100,-100,200,-100,200,-100]
    assert evaluate(base+[-200])['mode']=='ESPELHADO'
    assert evaluate(base+[-200,-100])['mode']=='ESPELHADO'
    assert evaluate(base+[-200,-100,1000])['mode']=='NORMAL'
    normal=evaluate(base+[-200,-100,1000,1000])
    assert normal['mode']=='NORMAL'
    assert normal['mode_policy']==POLICY


def test_inside_resets_count_not_mode_and_gp_no_longer_triggers():
    base=[100,-100,200,-100,200,-100]
    assert evaluate(base+[-100,200])['channel_outside_count']==0
    assert evaluate(base+[-100,200,-100])['mode']=='ESPELHADO'
    # Zero results can break an ascending floor without a new pivot or loss.
    result=evaluate(base+[0,0,0])
    assert result['mode']=='ESPELHADO'
    assert result['mode_policy']==POLICY


def test_insufficient_history_and_prefix_causality():
    for n in (0,1,11,50):
        with pytest.raises(RuntimeError):evaluate([10]*n)
    values=[100,-100,200,-100,200,-100]+[-200]*6+[1000]*5
    from application.realized_equity_pivot_channels import analyze_pivot_channels
    full=analyze_pivot_channels([dict(net=v) for v in values], confirmations=1)
    for n in range(6,len(values)+1):
        short=evaluate(values[:n])
        prior=[e for e in full['events'] if e['operation']<=n]
        expected='ESPELHADO' if prior and prior[-1]['side']=='Abaixo' else 'NORMAL'
        assert short['mode']==expected
        assert short['channel']['anchor']<=n


def test_two_outside_are_not_two_same_result_signs():
    result=evaluate([100,-100,200,-100,200,-100,-200,-100,1000,-10])
    assert result['mode']=='NORMAL'
    assert result['channel_last_break']['side']=='Acima'
