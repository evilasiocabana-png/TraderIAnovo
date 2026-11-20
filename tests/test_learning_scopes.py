import json
from types import SimpleNamespace
from datetime import datetime, timezone
from application.learning_store import LearningStore, encoded
from application.learning_scopes import scope_identity, scope_tables, active_key
from application.learning_policy import cycle, tables, admission
from application.model30_learning import comparison_group, paired_curve


def snap(source='M8',setup='A'):
    return dict(symbol='XAUUSD',timeframe='M5',entry_setup=setup,direction='BUY',
                stop_management_parameters=dict(source_operational_model=source))


def test_canonical_ownership_and_chart_separation():
    assert scope_identity(snap('M8'),'a')==scope_identity(snap('MODELO_8_FULL'),'a')
    scopes={scope_identity(snap(s,k),a) for s,k,a in [('M8','A','a'),('M10','A','a'),('M8','B','a'),('M8','A','b')]}
    assert len(scopes)==4
    assert scope_identity({},'a')==''
    keys={comparison_group(dict(source=s,symbol='XAUUSD',account=a,route_snapshot=encoded(snap(s,k)))) for s,k,a in [('M8','A','a'),('M10','A','a'),('M8','B','a'),('M8','A','b')]}
    assert len(keys)==4


def test_other_scope_cannot_promote_candidate(tmp_path,monkeypatch):
    import application.learning_policy as p
    store=LearningStore(tmp_path/'x.db')
    a,b=scope_identity(snap(),'a'),scope_identity(snap('M10'),'a')
    with store.connect() as db:
        tables(db); scope_tables(db)
        base=store.baseline(db,{'v':1})
        db.execute("INSERT INTO learning_candidates VALUES ('c',?,'2026-09-01T00:00:00+00:00','TESTING',?,'{}','2026-09-01T00:00:00+00:00',NULL)",(base,encoded({'source':'M8'})))
        db.execute('INSERT INTO learning_candidate_scopes VALUES (?,?)',('c',a))
    samples=[dict(scope=b,context={'source':'M8'},net=-10,day=f'2026-09-{i%20+2:02}',opened_at=f'2026-09-{i%20+2:02}T00:00:00+00:00') for i in range(100)]
    monkeypatch.setattr(p,'read_samples',lambda *args:samples)
    cycle(store,'2026-09-25T00:00:00+00:00')
    with store.connect() as db:
        assert db.execute("SELECT state FROM learning_candidates WHERE id='c'").fetchone()[0]=='TESTING'
        assert not db.execute('SELECT 1 FROM metadata WHERE key=?',(active_key(a),)).fetchone()


def test_global_legacy_not_assigned_to_a_model(tmp_path):
    store=LearningStore(tmp_path/'x.db')
    with store.connect() as db:
        tables(db)
        db.execute("INSERT INTO learning_candidates VALUES ('old','b','2026-09-01','APPLIED','{}','{}','2026-09-01',NULL)")
        db.execute("INSERT INTO metadata VALUES ('m30_active_filter','old')")
    cycle(store,'2026-09-25T00:00:00+00:00')
    with store.connect() as db:
        assert db.execute('SELECT state FROM learning_candidates').fetchone()[0]=='LEGACY_UNSCOPED'
    assert admission(snap(),store,account='a')['allowed']


def test_channel_replay_uses_quotes_not_negated_pnl(monkeypatch,capsys):
    from application.learning_channel_replay import SCRIPT
    import sys
    ts=datetime(2026,9,28,10,tzinfo=timezone.utc).timestamp()
    request=dict(path='demo',account='1@demo',symbol='XAUUSD',opened=ts,original_side='BUY',original_stop=90,volume=.1,reference_fees=-.7)
    fake=SimpleNamespace(initialize=lambda **kw:True,shutdown=lambda:None,ACCOUNT_TRADE_MODE_DEMO=0,COPY_TICKS_ALL=0,ORDER_TYPE_BUY=0,ORDER_TYPE_SELL=1,
        account_info=lambda:SimpleNamespace(login=1,server='demo',trade_mode=0),
        copy_ticks_from=lambda *a:[dict(time_msc=ts*1000,bid=100,ask=101),dict(time_msc=(ts+1)*1000,bid=88,ask=89)],
        order_calc_profit=lambda side,symbol,volume,entry,exit:entry-exit)
    monkeypatch.setitem(sys.modules,'MetaTrader5',fake)
    monkeypatch.setattr(sys,'argv',['test',json.dumps(request)])
    exec(compile(SCRIPT,'replay','exec'),{})
    value=json.loads(capsys.readouterr().out)
    assert value['state']=='RESOLVED_ESTIMATED_COSTS'
    assert value['entry']==100 and value['exit']==89 and value['net']==10.3


def test_channel_upper_exit_normal_without_rising_pivot(monkeypatch):
    import application.learning_channel_hypothesis as h
    monkeypatch.setattr(h,'analyze_pivot_channels',lambda *a,**kw:dict(segments=[dict(trend='Baixa',anchor=5)],events=[dict(operation=7,side='Acima')]))
    assert h.channel_decision([])=='NORMAL'


def test_manual_channel_future_ledger_and_graph(tmp_path,monkeypatch):
    import application.learning_channel_hypothesis as h
    import application.learning_channel_replay as replay
    from application.model30_learning import tables as pair_tables
    store=LearningStore(tmp_path/'manual.db')
    snapshot=snap()
    snapshot['initial_stop']=90
    snapshot['stop_management_parameters']['m30_execution_volume']=.1
    timestamp='2026-09-26T10:00:00+00:00'
    opened=datetime.fromisoformat(timestamp).timestamp()
    with store.connect() as db:
        pair_tables(db)
        base=store.baseline(db,{'v':1})
        ident=store.register(db,dict(source='M8',executor='M23',symbol='XAUUSD',timeframe='M5',candle=timestamp,
            direction='BUY',setup='A',mode='NORMAL',provenance='PROSPECTIVE',baseline=base,observed_at=timestamp,
            status='ACCEPTED',snapshot=snapshot))
        for ticket,net in [(1,-17),(2,-18)]:
            db.execute('''INSERT INTO executions (id,signal_id,ticket,account_mode,account,recorded_at,status,net,evidence,snapshot)
                VALUES (?,?,?,'DEMO','a',?,'CLOSED',?,?,?)''',
                (str(ticket),ident,ticket,timestamp,net,encoded(dict(deals=[dict(time=opened,commission=-.7,fee=0)])),encoded(snapshot)))
        h.register_scopes(db,'2026-09-25T00:00:00+00:00')
        db.execute('INSERT INTO m30_pairs VALUES (?,?,?,?,?,?,?,?,?,?,?)',('pair',1,'a','M8','XAUUSD',timestamp,'ACCEPTED',2,'BASELINE','',encoded(snapshot)))
    monkeypatch.setattr(h,'channel_decision',lambda values:'ESPELHADO')
    requests=[]
    def simulate(request):
        requests.append(request)
        return dict(state='RESOLVED_ESTIMATED_COSTS',net=5)
    monkeypatch.setattr(replay,'replay',simulate)
    h.evaluate_future(store)
    assert len(requests)==1 and requests[0]['original_side']=='BUY'
    chart=next(iter(h.manual_comparison(store).values()))
    assert chart['rows']==[{'Par':1,'M23':-17,'M30':-18,'Candidato em teste':5}]
    assert chart['manual']
