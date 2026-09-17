import json
from application.model23_display_history import closed_m29_m7_copies
from application.model29_entry_sync import pair_has_open_copy
from types import SimpleNamespace

def test_history_reconciles_account_lineage_costs_and_open(tmp_path):
    audit=tmp_path/'audit.jsonl'
    record=dict(accepted=True,operational_model='MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29',ticket=1,
        execution_account_login=123,execution_account_server='Demo',
        plan_snapshot={'stop_management_parameters':{'m23_m29_origin_source':'M7'}})
    audit.write_text(json.dumps(record))
    snap={'account':{'login':123,'server':'Demo'},'open_positions':[], 'rows':[
        dict(position_id=1,type=0,entry=0,volume=.2,comment='TraderIA M23 S29 TX',symbol='XAUUSD',commission=-1,time=1),
        dict(position_id=1,type=1,entry=1,volume=.2,profit=11,swap=-2,time=2)]}
    assert closed_m29_m7_copies(snap,audit)[0]['net']==8
    snap['open_positions']=[{'ticket':1}]
    assert closed_m29_m7_copies(snap,audit)==[]
    snap['open_positions']=[];snap['rows'][1]['volume']=.1
    assert closed_m29_m7_copies(snap,audit)==[]
    snap['rows'][1]['volume']=.2;snap['account']['login']=124
    assert closed_m29_m7_copies(snap,audit)==[]

def test_open_copy_alone_blocks_next_pair(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert pair_has_open_copy([SimpleNamespace(symbol='XAUUSD',comment='TraderIA M23 S29 M7 T123',ticket=55)])
    assert not pair_has_open_copy([])


def test_continuation_uses_only_available_results_and_old_seed():
    from application.model23_display_history import m29_display_continuation
    own=[dict(model=29,symbol="XAUUSD",position=str(i),closed=i,net=(-1 if i%2 else 1)) for i in range(1,7)]
    assert len(m29_display_continuation(own,[]))==6
    copies=[dict(symbol="XAUUSD",position="20",opened=10,closed=20,net=-2)]
    merged=m29_display_continuation(own,copies)
    assert len(merged)==7
    assert [r["position"] for r in merged]==[str(i) for i in range(1,7)]+["20"]
    assert merged[-1]["display_origin"]=="M23 via M29"
    own.append(dict(model=29,symbol="XAUUSD",position="15",closed=15,net=3))
    assert m29_display_continuation(own,copies)==merged
    copies=[dict(symbol="XAUUSD",position=str(i),opened=10,closed=i,net=1) for i in range(20,28)]
    merged=m29_display_continuation(own,copies)
    assert len(merged)==7 and all(r["display_origin"]=="M23 via M29" for r in merged)
    assert [r["position"] for r in merged]==[str(i) for i in range(21,28)]


def test_native_sequence_query_includes_recent_broker_clock_exit(tmp_path):
    import inspect,textwrap
    from datetime import datetime,timezone,timedelta
    from infrastructure.execution.mt5_demo_execution_provider import MT5DemoExecutionProvider
    from application.model23_display_history import m29_display_continuation
    now=datetime.now(timezone.utc)
    entry=dict(position_id=77,type=0,entry=0,volume=.2,symbol="XAUUSD",comment="TraderIA M23 S29 M7 TEST",profit=0,commission=-.7,time=int(now.timestamp())-3600)
    close=dict(position_id=77,type=1,entry=1,volume=.2,symbol="XAUUSD",profit=-469.2,commission=-.7,time=int((now+timedelta(hours=3)).timestamp()))
    def native(d):return SimpleNamespace(_asdict=lambda:d)
    def history(start,end):return [native(d) for d in (entry,close) if start.timestamp()<=d['time']<=end.timestamp()]
    mt5=SimpleNamespace(account_info=lambda:native(dict(login=1,server="Demo")),positions_get=lambda:[],history_deals_get=history)
    source=inspect.getsource(MT5DemoExecutionProvider._external_mt5_read)
    block=source.split('elif action == "m29_sequence":\n',1)[1].split('elif action == "history_deals":',1)[0]
    scope={'mt5':mt5};exec(textwrap.dedent(block),scope)
    audit=tmp_path/'audit.jsonl';audit.write_text('')
    rows=closed_m29_m7_copies(scope['payload'],audit)
    assert len(rows)==1 and round(rows[0]['net'],2)==-470.6
    assert m29_display_continuation([],rows)[-1]['net']<0
