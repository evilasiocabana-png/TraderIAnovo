from unittest.mock import MagicMock
import pytest
from tests.test_model29_integration import deals
from application.model29_sequence_history import closed_m7_positions
from application.model29_m7_channel import channel_mode_state
from application.realized_equity_pivot_channels import analyze_pivot_channels, pivot_anchor_plot_rows


def test_chart_uses_exact_operational_positions_and_net(monkeypatch):
    import dashboard_app as app
    from infrastructure.execution.mt5_demo_execution_provider import MT5DemoExecutionProvider
    values = [100,-100,200,-100,200,-100,-200,-100,1000,-10]
    payload = dict(ok=True, account=dict(login=123,server='Demo'), open_positions=[],
        rows=sum((deals(i+1,v) for i,v in enumerate(values)), []) +
             deals(20,9000,symbol='BTCUSD') + deals(21,8000,model=29))
    monkeypatch.setenv('TRADERIA_DEMO_ACCOUNT_LOGIN','123')
    monkeypatch.setattr(MT5DemoExecutionProvider,'_external_mt5_read',lambda *a,**k:payload)
    displayed=app._m7_operational_chart_results.__wrapped__('DEMO','test-terminal')
    expected=[r for r in closed_m7_positions(payload) if r['model']==23 and r['symbol']=='XAUUSD']
    assert [r['ticket'] for r in displayed] == [r['position'] for r in expected]
    assert [r['net'] for r in displayed] == values
    assert channel_mode_state(displayed) == channel_mode_state(expected)
    all_rows=app._m7_operational_chart_results.__wrapped__('DEMO','test-terminal',None)
    assert len(all_rows)==len(values)+1
    assert sum(r['net'] for r in all_rows if r['symbol']=='BTCUSD')==9000
    payload['account']['login']=456
    with pytest.raises(RuntimeError):app._m7_operational_chart_results.__wrapped__('DEMO','test-terminal')


def test_reference_read_failure_does_not_use_mixed_audit(monkeypatch):
    import dashboard_app as app
    fake=MagicMock()
    fake.checkbox.return_value=True
    monkeypatch.setattr(app,'st',fake)
    def fail(*a):raise RuntimeError('no data')
    monkeypatch.setattr(app,'_m7_operational_chart_results',fail)
    app._render_m23_source_structure('M7',[dict(net=999,time='',letter='G')])
    fake.warning.assert_called_once()
    fake.vega_lite_chart.assert_not_called()


def test_anchor_lines_are_display_only_and_not_future_confirmations():
    rows=[dict(net=v) for v in [100,-100,200,-100,200,-100,-200,-100,1000,-10]]
    study=analyze_pivot_channels(rows)
    before=repr(study)
    anchors=pivot_anchor_plot_rows(study,1,len(rows))
    assert anchors and all(a['end']<=a['anchor'] for a in anchors)
    assert not pivot_anchor_plot_rows(study,1,4)
    assert repr(study)==before


def test_gold_and_bitcoin_have_independent_graphs_and_controls(monkeypatch):
    import dashboard_app as app
    import altair as alt
    fake=MagicMock()
    fake.checkbox.side_effect=lambda *a,**k:k.get('value',False)
    fake.select_slider.side_effect=lambda *a,**k:k.get('value')
    fake.slider.side_effect=lambda *a,**k:a[3]
    fake.columns.side_effect=lambda n:[MagicMock() for _ in range(n)]
    monkeypatch.setattr(app,'st',fake)
    rows=[dict(net=v,symbol=s,time='',letter='G' if v>0 else 'P')
          for s,values in [('XAUUSD',[100,-100,200,-100,200,-100]),('BTCUSD',[-20,5,-10])]
          for v in values]
    reader=MagicMock(return_value=rows)
    monkeypatch.setattr(app,'_m7_operational_chart_results',reader)
    app._render_m23_source_structure('M7',[])
    reader.assert_called_once()
    charts=[call.args[0] for call in fake.vega_lite_chart.call_args_list]
    assert len(charts)==2
    for spec in charts:alt.LayerChart.from_dict(spec)
    assert [spec['layer'][1]['data']['values'][-1]['equity'] for spec in charts]==[200,-25]
    assert [len(spec['layer'][1]['data']['values']) for spec in charts]==[6,3]
    titles=[call.args[0] for call in fake.markdown.call_args_list]
    assert any('Ouro (XAUUSD)' in title for title in titles)
    assert any('Bitcoin (BTCUSD)' in title for title in titles)
    keys=[call.kwargs['key'] for control in (fake.checkbox,fake.slider,fake.select_slider)
          for call in control.call_args_list if 'key' in call.kwargs]
    assert len(keys)==len(set(keys))
