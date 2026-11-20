from application.supervisor_report_repair import rebuild
from tests.test_source_channel_gate import deals


def test_repair_native_closures_preserves_unrelated_history():
    old={'mt5_ticket':999,'mt5_time':'2026-01-01','operation_status':'FECHADA/HISTORICO','marker':'keep'}
    report={'rows':[old]}
    result,count=rebuild(report,dict(rows=deals(1),open_positions=[]))
    assert count==1 and old in result['rows']
    new=next(r for r in result['rows'] if r.get('mt5_ticket')==1)
    assert sum(new[k] for k in ('mt5_realized_profit','mt5_commission','mt5_swap','mt5_fee'))==95


def test_open_positions_never_converted_to_closed():
    result,count=rebuild({'rows':[]},dict(rows=deals(1),open_positions=[dict(ticket=1)]))
    assert count==0 and not result['rows']


def test_duplicate_deals_do_not_double_costs():
    ds=deals(1)
    result,count=rebuild({'rows':[]},dict(rows=ds+ds,open_positions=[]))
    assert count==1 and len(result['rows'])==1
    assert result['rows'][0]['mt5_realized_profit']==100
