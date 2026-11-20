import pytest
from application.realized_equity_channels import analyze_equity_channels, channel_plot_rows


def rows(values):
    return [dict(net=v) for v in values]


@pytest.mark.parametrize("value,trend", [(10,"Alta"),(-10,"Baixa"),(0,"Lateral")])
def test_parallel_stable_channels(value,trend):
    result=analyze_equity_channels(rows([value]*40))
    assert result['trend']==trend
    assert len(result['segments'])==1
    lower,upper=channel_plot_rows(result,1,40)
    assert upper['begin']-lower['begin']==pytest.approx(upper['finish']-lower['finish'])


@pytest.mark.parametrize("confirmations",[2,3])
def test_no_future_repainting(confirmations):
    data=rows([100]*18+[-250]*18+[500]*10)
    complete=analyze_equity_channels(data,confirmations=confirmations)
    for n in range(12,len(data)+1):
        part=analyze_equity_channels(data[:n],confirmations=confirmations)
        assert part['observations']==[p for p in complete['observations'] if p['operation']<=n]
        assert part['events']==[p for p in complete['events'] if p['operation']<=n]


def test_third_close_required_and_reset_inside():
    data=rows([10]*12+[100,100])
    assert len(analyze_equity_channels(data,confirmations=2)['events'])==1
    study=analyze_equity_channels(data,confirmations=3)
    assert not study['events'] and study['consecutive']==2
    assert analyze_equity_channels(data+rows([100]),confirmations=3)['events'][-1]['operation']==15
    assert analyze_equity_channels(data+rows([-170]),confirmations=3)['consecutive']==0


def test_empty_short_validation_and_clipping():
    assert analyze_equity_channels([])['trend']=='Sem amostra'
    assert not analyze_equity_channels(rows([1]*11))['segments']
    result=analyze_equity_channels(rows([10]*40))
    plotted=channel_plot_rows(result,20,30)
    assert all(r['start']==19 and r['end']==30 and r['anchor']==12 for r in plotted)
    with pytest.raises(ValueError):analyze_equity_channels(rows([float('nan')]))
    with pytest.raises(ValueError):analyze_equity_channels([],window=1)


def test_m23_m7_overlay_schema_and_last_three_table(monkeypatch):
    from unittest.mock import MagicMock
    import altair as alt
    import dashboard_app as app
    fake = MagicMock()
    fake.checkbox.side_effect = lambda *a, **k: k.get('value',False)
    fake.select_slider.side_effect = lambda *a, **k: k.get('value')
    fake.slider.side_effect = lambda *a, **k: a[3]
    fake.columns.side_effect = lambda n: [MagicMock() for _ in range(n)]
    monkeypatch.setattr(app,'st',fake)
    values = [100,-100,200,-100,200,-100,-200,-100,1000,-10]
    results = [dict(position=str(i),net=v,time=str(i),letter='G' if v>0 else 'P') for i,v in enumerate(values)]
    monkeypatch.setattr(app, '_m7_operational_chart_results', lambda *a: results)
    app._render_m23_source_structure('M7',results,reference_symbol='XAUUSD')
    spec = fake.vega_lite_chart.call_args.args[0]
    alt.LayerChart.from_dict(spec)
    assert any((layer.get('encoding',{}).get('color',{}).get('legend') or {}).get('title')=='Canal (estudo)' for layer in spec['layer'])
    table = fake.dataframe.call_args_list[0].args[0]
    assert [r['Operacao'] for r in table] == [8,9,10]
    assert any(r['Fora consecutivos']==2 for r in table)
    assert not any(layer['mark']['type']=='rect' for layer in spec['layer'])
    assert any(layer['mark'].get('strokeDash') for layer in spec['layer'])
    channel_layer = next(layer for layer in spec['layer'] if (layer.get('encoding',{}).get('color',{}).get('legend') or {}).get('title')=='Canal (estudo)')
    assert len(channel_layer['data']['values']) <= 4
    assert len(spec['layer'][1]['data']['values']) == len(results)
    assert spec['layer'][0]['data']['values'][0]['previous_operation'] == 0


def test_recent_channel_display_does_not_change_calculation():
    data=rows([100]*18+[-250]*18+[500]*10)
    study=analyze_equity_channels(data)
    all_rows=channel_plot_rows(study,1,len(data))
    recent=channel_plot_rows(study,1,len(data),max_channels=2)
    assert len(all_rows)>4 and len(recent)==4
    for shown, original in zip(recent,all_rows[-4:]):
        for key in ('start','end','begin','finish','anchor'):
            assert shown[key]==original[key]
    assert [r['opacity'] for r in recent]==[.35,.35,1.,1.]
