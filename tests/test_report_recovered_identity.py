from application.dashboard_service import DashboardService

def test_exit_comment_preserves_entry_source_and_unknown_channel():
    s = DashboardService()
    history = {}
    entry = s._mt5_history_payload(dict(comment='TraderIA M23 S29 M18 NOR', entry=0, type=0, volume=.3, position_id=7), 7, 'DEAL')
    exit = s._mt5_history_payload(dict(comment='[sl 4000]', entry=1, type=1, volume=.3, position_id=7, profit=-10), 8, 'DEAL')
    s._merge_mt5_trade_payload(history, 7, entry, aggregate_profit=True)
    s._merge_mt5_trade_payload(history, 7, exit, aggregate_profit=True)
    row = s._mt5_only_trade_audit_row(history[7])
    assert row.operational_model.endswith('_SOURCE_M29')
    params = row.plan_snapshot['stop_management_parameters']
    assert params['m23_m29_origin_source'] == 'M18'
    assert 'reinforcement_policy' not in params
    assert 'reinforcement_state' not in params
    assert row.mt5_realized_profit == -10

def test_native_source_identity_and_unidentified_manual_entry():
    s = DashboardService()
    for comment, number in [('TraderIA M23 S8', 8), ('TraderIA M23 S20', 20)]:
        model, snapshot = s._mt5_recovered_entry_identity(comment)
        assert model.endswith(f'_SOURCE_M{number}')
    model, snapshot = s._mt5_recovered_entry_identity('TraderIA M30 S7 NOR')
    assert 'MODELO_30' in model
    assert snapshot['stop_management_parameters']['source_model_label'] == 'M7'
    model, snapshot = s._mt5_recovered_entry_identity('manual')
    assert model == 'N/D'

def test_entry_order_equal_position_counts_commission_once():
    from types import SimpleNamespace
    from datetime import datetime
    s=DashboardService(); history={}
    deals=[SimpleNamespace(ticket=100,order=7,position_id=7,entry=0,type=0,volume=.3,profit=0,commission=-1.05,comment='TraderIA M23 S29 M18 NOR'),SimpleNamespace(ticket=101,order=8,position_id=7,entry=1,type=1,volume=.3,profit=100,commission=-1.05,comment='[tp]')]
    mt5=SimpleNamespace(history_deals_get=lambda *_:deals)
    s._merge_mt5_history_deals(mt5,datetime.now(),datetime.now(),history)
    assert history[7]['commission']==-2.10
    assert history[7]['profit']==100
    assert history[7]['entry_comment']=='TraderIA M23 S29 M18 NOR'

def test_filled_pending_uses_deal_direction_not_pending_order_type():
    s=DashboardService();history={}
    s._merge_mt5_trade_payload(history,7,s._mt5_history_payload(dict(type=4,volume_initial=.3,comment='TraderIA M23 S10'),7,'ORDER'))
    s._merge_mt5_trade_payload(history,7,s._mt5_history_payload(dict(type=0,volume=.3,entry=0,commission=-1.05,comment='TraderIA M23 S10'),100,'DEAL'),aggregate_profit=True)
    assert history[7]['side']=='BUY'
    assert history[7]['commission']==-1.05
    assert s._mt5_operation_status({'source':'ORDER'})!='FECHADA/HISTORICO'
