import pytest

from application.model29_m7_sequence import M7SequenceState, mirrored_prices
from application.model29_basket_accumulator import model29_variant_id


def test_complete_cycle_uses_six_distinct_results():
    state = M7SequenceState()
    for i, v in enumerate([1, -1, 1, -1, -1]):
        assert not state.record(str(i), v)
    assert state.record("5", -1)
    assert state.mode == "ESPELHADO"
    assert not state.record("5", -1)
    for i, v in enumerate([-1, 1, -1, 1, 1, 1], 6):
        state.record(str(i), v)
    assert state.mode == "NORMAL"


def test_bootstrap_once_and_no_hypothetical_mirrored_history():
    state = M7SequenceState()
    state.bootstrap([1, -1, 1, -1, -1, -1])
    assert state.mode == "ESPELHADO"
    state.bootstrap([-1, 1, -1, 1, 1, 1])
    assert state.mode == "ESPELHADO"
    other = M7SequenceState()
    other.bootstrap([1, -1, 1, -1, -1, -1, -1, -1])
    assert other.mode == "ESPELHADO"


def test_break_even_breaks_sequence_and_other_instances_are_isolated():
    state = M7SequenceState()
    for i, v in enumerate([1, -1, 1, -1, 0, -1, -1]):
        state.record(str(i), v)
    assert state.mode == "NORMAL"
    assert M7SequenceState().outcomes == []


@pytest.mark.parametrize("side,entry,sl,expected", [
    ("BUY", 100, 90, ("SELL", 110, 90)),
    ("SELL", 100, 110, ("BUY", 90, 110)),
])
def test_rr_one(side, entry, sl, expected):
    assert mirrored_prices(side, entry, sl) == expected


@pytest.mark.parametrize("side,entry,sl", [("BUY", 100, 110), ("SELL", 100, 90), ("BUY", 100, 100), ("BUY", float("nan"), 90)])
def test_invalid_protection(side, entry, sl):
    with pytest.raises(ValueError):
        mirrored_prices(side, entry, sl)


def test_exact_source_universe():
    for number in (7,):
        assert model29_variant_id(f"MODELO_{number}").endswith(f"SOURCE_M{number}")
    for number in (0, 1, 2, 3, 5, 8, 10, 18, 20, 21, 22, 23, 26, 28, 29):
        with pytest.raises(ValueError):
            model29_variant_id(f"MODELO_{number}")


@pytest.mark.parametrize("mode,values,expected",[
    ("NORMAL",[-1]*4,"ESPELHADO"),
    ("ESPELHADO",[1]*4,"NORMAL"),
    ("NORMAL",[1,-1,1,-1,-1,-1],"ESPELHADO"),
    ("ESPELHADO",[-1,1,-1,1,1,1],"NORMAL"),
])
def test_gold_four_triggers(mode,values,expected):
    state=M7SequenceState(mode=mode,four_result_trigger=True)
    for i,v in enumerate(values[:-1]):assert not state.record(str(i),v)
    assert state.record(str(len(values)-1),values[-1])
    assert state.mode==expected and state.outcomes==[]
    assert not state.record(str(len(values)-1),values[-1])

@pytest.mark.parametrize("value,mode",[(-1,"ESPELHADO"),(1,"NORMAL")])
def test_repeated_same_result_does_not_toggle(mode,value):
    state=M7SequenceState(mode=mode,four_result_trigger=True)
    for i in range(12):assert not state.record(str(i),value)
    assert state.mode==mode

@pytest.mark.parametrize("value,mode",[(-1,"NORMAL"),(1,"ESPELHADO")])
@pytest.mark.parametrize("breaker",[0,"opposite"])
def test_three_results_and_break_do_not_trigger(value,mode,breaker):
    state=M7SequenceState(mode=mode,four_result_trigger=True)
    values=[value]*3+[0 if breaker==0 else -value]+[value]*3
    for i,v in enumerate(values):assert not state.record(str(i),v)
    assert state.mode==mode


def test_full_four_result_cycle_and_legacy_scope():
    state=M7SequenceState(four_result_trigger=True)
    for i,v in enumerate([-1]*4+[1]*4):state.record(str(i),v)
    assert state.mode=="NORMAL"
    legacy=M7SequenceState()
    for i in range(4):legacy.record(str(i),-1)
    assert legacy.mode=="NORMAL"
