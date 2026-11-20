from types import SimpleNamespace as NS
import pytest
from infrastructure.execution.mt5_demo_execution_provider import MT5DemoExecutionProvider as Provider
from application.model23_basket_accumulator import model23_position_source, model23_position_entry_type_token

@pytest.mark.parametrize("source",[7,8,10,18,20])
def test_copy_comment_preserves_all_identity_tokens(source):
    original=f"TraderIA M23 S29 M{source} T717F7BC2"
    comment=Provider._compact_mt5_comment(original)
    assert len(comment)<=29
    assert f"M{source}" in comment
    assert model23_position_source(NS(comment=comment))=="M29"
    assert model23_position_entry_type_token(NS(comment=comment))=="T717F7BC2"

@pytest.mark.parametrize("source",[8,10,18,20])
def test_replacement_comment_short_without_losing_setup(source):
    original=f"TraderIA M23 S{source} T393D6B69"
    assert Provider._compact_mt5_comment(original+" replace")==original

@pytest.mark.parametrize("comment",["TraderIA M30 S18 NOR","TraderIA M23 S7 T717F7BC2","TraderIA PM EXIT"])
def test_short_comments_unchanged(comment):
    assert Provider._compact_mt5_comment(comment)==comment

def test_never_truncates_unrecognized_long_identity():
    with pytest.raises(ValueError):Provider._compact_mt5_comment("X"*30)

def test_transport_compacts_before_check_and_send(monkeypatch):
    import infrastructure.execution.mt5_demo_execution_provider as mod
    import core.weekly_robot_schedule as schedule
    seen=[]
    broker=NS(order_check=lambda req:(seen.append(dict(req)) or NS(retcode=0)),order_send=lambda req:(seen.append(dict(req)) or NS(retcode=10009)),TRADE_ACTION_PENDING=5,TRADE_ACTION_DEAL=1)
    p=Provider(mt5=broker)
    monkeypatch.setattr(p,"_additional_real_consent_check",lambda req:None)
    monkeypatch.setattr(p,"_demo_account_check",lambda:None)
    monkeypatch.setattr(mod,"read_permissions",lambda broker:{})
    monkeypatch.setattr(mod,"permissions_allowed",lambda permissions:True)
    monkeypatch.setattr(schedule,"weekly_entry_allowed",lambda symbol:True)
    request=dict(action=5,symbol="XAUUSD",comment="TraderIA M23 S29 M10 T717F7BC2",volume=.3,sl=10,tp=20)
    p._checked_order_send(request)
    assert len(seen)==2 and seen[0]==seen[1]
    assert seen[0]["comment"]=="M23 S29 M10 T717F7BC2"
    assert request["comment"].startswith("TraderIA")
    assert seen[0]["volume"]==.3 and seen[0]["sl"]==10 and seen[0]["tp"]==20
