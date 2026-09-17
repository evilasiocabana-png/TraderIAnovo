from application.realized_equity_structure import analyze_equity_structure
import pytest


def study(values):
    return analyze_equity_structure([dict(net=v,time=str(i)) for i,v in enumerate(values)],0.5)


def test_rising_structure_survives_losing_operations():
    data=study([10,-4,10,-4,10,-4,10,-4])
    assert data['state']=='Alta'
    assert data['points'][-1]['letter']=='P'
    assert all(p['confirmed']>p['operation'] for p in data['pivots'])
    assert data['points'][0]['equity']==0
    assert data['net']==24


def test_descending_structure_can_have_winners():
    data=study([-10,4,-10,4,-10,4,-10,4])
    assert data['state']=='Baixa'
    assert data['points'][-1]['letter']=='G'


def test_future_outcomes_do_not_relabel_past_and_extremes_need_confirmation():
    prefix=[10,-4,10,-4,10,-4,10,-4]
    before=study(prefix)
    after=study(prefix+[-20,8,-15,8,-15,8])
    assert after['points'][:len(before['points'])]==before['points']
    assert after['state']=='Baixa'
    assert after['transitions'][-1]['previous']=='Alta'
    assert after['transitions'][-1]['current']=='Baixa'
    assert after['points'][9]['state']=='Transicao'
    assert all(p['operation']<len(after['points'])-1 for p in after['pivots'])


def test_empty_flat_and_unbroken_rise_do_not_invent_pivots():
    for values in ([],[0,0,0],[1,1,1,1]):
        data=study(values)
        assert data['state']=='Formacao'
        assert data['pivots']==[]
    with pytest.raises(ValueError):study([float('nan')])
