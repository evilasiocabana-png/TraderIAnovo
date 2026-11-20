from application.m29_equity_breakout import permission
from application.source_channel_gate import channel_state,m29_filter


def study(states,events,trend='Baixa'):
    return ({'points':[{'operation':i,'state':s} for i,s in enumerate(['Formacao']+states)]},
            {'segments':[{'anchor':1,'trend':trend}], 'events':[{'operation':i,'side':s} for i,s in events]})

def test_first_upper_break_activates_and_inside_transition_does_not_cancel():
    a,b=study(['Transicao']*4,[(2,'Acima')])
    assert permission(a,b)=={'enabled':True,'last_change':{'operation':2,'trigger':'ROMPIMENTO_SUPERIOR_TRANSICAO','enabled':True}}

def test_lower_break_cancels_and_a_later_upper_break_reactivates():
    a,b=study(['Transicao']*5,[(2,'Acima'),(4,'Abaixo')])
    assert not permission(a,b)['enabled']
    b['events'].append({'operation':5,'side':'Acima'})
    assert permission(a,b)['enabled']

def test_transition_without_break_and_no_channel_stay_blocked():
    a,b=study(['Transicao']*3,[])
    assert not permission(a,b)['enabled']
    assert not permission(a,{'segments':[],'events':[]})['enabled']

def test_lower_break_not_undone_by_unchanged_high_structure():
    a,b=study(['Alta']*4,[(2,'Abaixo')],trend='Alta')
    assert not permission(a,b)['enabled']

def test_down_structure_without_upper_transition_does_not_activate():
    a,b=study(['Baixa']*3,[(2,'Acima')])
    assert not permission(a,b)['enabled']

def test_no_open_results_or_price_input_and_prefix_is_causal():
    from application.realized_equity_structure import analyze_equity_structure
    from application.realized_equity_pivot_channels import analyze_pivot_channels
    values=[100,-70,150,-80,160,-90,-180,60,250,-80,-400,60,500]
    rows=[dict(id=str(i),net=n,time=i) for i,n in enumerate(values)]
    for n in range(1,len(rows)+1):
        state=channel_state(rows[:n])
        assert state['m29_latch']==permission(analyze_equity_structure(rows[:n]),analyze_pivot_channels(rows[:n],confirmations=1))
        assert m29_filter(state,8,'EURUSD')['blocked'] is not state['m29_latch']['enabled']


def test_each_new_close_updates_reference_once_and_excludes_open_and_other_sources():
    from application.source_channel_gate import reconciled_results
    from tests.test_source_channel_gate import deals
    first = deals(101, 'M8', 'EURUSD')
    second = deals(102, 'M8', 'EURUSD')
    before = reconciled_results(dict(rows=first+second, open_positions=[dict(identifier=102)]), 8, 'EURUSD')
    after = reconciled_results(dict(rows=first+second+second+deals(103, 'M18', 'EURUSD'), open_positions=[]), 8, 'EURUSD')
    a, b = channel_state(before), channel_state(after)
    assert a['closed'] == 1 and b['closed'] == 2
    assert a['reference'] != b['reference']
    assert [r['net'] for r in after] == [95., 95.]
    assert channel_state(after)['reference'] == b['reference']
