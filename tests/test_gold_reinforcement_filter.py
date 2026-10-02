from dataclasses import replace
from itertools import product
import pytest
from application.gold_reinforcement_filter import CONTEXTS, VERSION, apply_filter, location
from application import source_channel_gate as gate
from tests.test_model30_independent import provider, order, rows


def test_only_exact_six_combinations_are_allowed():
    allowed=set()
    for source,state,zone in product(gate.SOURCES,["Alta","Baixa","Transicao","Formacao"],
            ["Abaixo do piso","Perto do piso","Meio","Perto do teto","Acima do teto","Sem canal"]):
        result=apply_filter(dict(state=state,zone=zone,blocked=False,mode="NORMAL"),source,"XAUUSD")
        if not result["blocked"]:allowed.add((source,state,zone))
        assert result["mode"]=="NORMAL"
    assert allowed==CONTEXTS and len(allowed)==6

@pytest.mark.parametrize("value,zone",[(-1,"Abaixo do piso"),(0,"Perto do piso"),
    (99,"Perto do piso"),(100,"Meio"),(199,"Meio"),(200,"Perto do teto"),
    (300,"Perto do teto"),(301,"Acima do teto")])
def test_boundaries_match_study(value,zone):
    assert location(value,0,dict(slope=0,lower=0,upper=300))[0]==zone

def test_no_channel_and_invalid_geometry():
    assert location(1,2,None)==("Sem canal",None)
    with pytest.raises(ValueError):location(1,2,dict(slope=0,lower=2,upper=1))
    assert apply_filter(dict(state="Formacao",blocked=False),8,"XAUUSD")["blocked"]

@pytest.mark.parametrize("symbol",["BTCUSD","EURJPY"])
def test_other_assets_keep_downtrend_only(symbol):
    for blocked in [False,True]:
        state=dict(state="Transicao",zone="Meio",blocked=blocked)
        assert apply_filter(state,7,symbol)==state

@pytest.mark.parametrize("model",["MODELO_29_BASKET_ACCUMULATOR_SOURCE_M18",
    "MODELO_30_ADAPTIVE_M23_SOURCE_M18","MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29"])
@pytest.mark.parametrize("side",["BUY","SELL"])
def test_all_routes_allow_downtrend_exception_and_reject_new_invalid_state(monkeypatch,model,side):
    state=apply_filter({**gate.channel_state([]),"state":"Baixa","zone":"Meio"},18,"XAUUSD")
    o=replace(order(),operational_model=model,quantity=.2,side=side)
    p=o.plan_snapshot["stop_management_parameters"]
    p.update(gate.parameters(state,18,side),source_operational_model="MODELO_18_TEST",m23_m29_origin_source="M18")
    monkeypatch.setattr(gate,"reference_state",lambda *a,**k:state)
    assert gate.order_error(provider(),o) is None
    assert gate.loss_limit(o)==400
    p.pop("reinforcement_filter_version")
    assert "seis recortes" in gate.order_error(provider(),o)
    p["reinforcement_filter_version"]=VERSION
    state.update(apply_filter({**state,"zone":"Perto do teto"},18,"XAUUSD"))
    assert "fora dos seis" in gate.order_error(provider(),o)
    original=replace(o,operational_model="MODELO_23_BASKET_ACCUMULATOR_SOURCE_M18",quantity=.1)
    assert gate.order_error(provider(),original) is None and gate.loss_limit(original)==200


def test_pending_uses_same_filter_including_low_exception(tmp_path,monkeypatch):
    from tests.test_reinforcement_pending import setup
    from application import reinforcement_pending as pending
    p,o,r,sends,logs=setup(tmp_path,monkeypatch)
    state=apply_filter(dict(state="Baixa",zone="Meio",blocked=True),18,"XAUUSD")
    monkeypatch.setattr(pending,"reference_state",lambda *a:state)
    assert pending.cancel_downtrend_pending(p)["cancelled"]==0 and not sends
    state=apply_filter(dict(state="Alta",zone="Meio",blocked=False),8,"XAUUSD")
    assert pending.cancel_downtrend_pending(p)["cancelled"]==1
    assert logs[-1]["filter_version"]==VERSION
