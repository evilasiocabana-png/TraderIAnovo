from types import SimpleNamespace
from application.report_source_channels import source_channel_groups

def test_channels_separate_assets_exclude_reinforcement_and_open_and_deduplicate():
    def row(ticket, source, symbol, status='FECHADA/HISTORICO'):
        return SimpleNamespace(operational_model=f'MODELO_23_BASKET_ACCUMULATOR_SOURCE_M{source}',symbol=symbol,mt5_found=True,operation_status=status,mt5_ticket=ticket,local_ticket=None,mt5_time=f'2026-10-21T12:00:0{ticket}+00:00',mt5_realized_profit=10,mt5_commission=-1,mt5_swap=0,mt5_fee=0)
    a=row(1,8,'XAUUSD')
    groups=source_channel_groups([a,a,row(2,8,'EURUSD'),row(3,29,'XAUUSD'),row(4,8,'XAUUSD','ABERTA')])
    assert set(groups)=={'M8 / XAUUSD','M8 / EURUSD'}
    assert all(g['summary']['Encerramentos']==1 for g in groups.values())
    assert all(g['summary']['Saldo liquido']==9 for g in groups.values())


def test_continuity_does_not_duplicate_archived_report_and_keeps_reused_ticket(monkeypatch, tmp_path):
    from application import account_channel_continuity
    from datetime import datetime, timezone
    monkeypatch.setattr(account_channel_continuity, 'CONFIG', tmp_path/'missing')
    stamp = int(datetime(2026, 10, 21, 12, 0, 1, tzinfo=timezone.utc).timestamp()*1000)
    monkeypatch.setattr(account_channel_continuity, 'seed_groups', lambda account: {'8/XAUUSD':[dict(id='old:1',time=stamp,net=9)]})
    monkeypatch.setenv('TRADERIA_DEMO_ACCOUNT_LOGIN','new')
    def row(time):
        return SimpleNamespace(operational_model='MODELO_23_BASKET_ACCUMULATOR_SOURCE_M8',symbol='XAUUSD',mt5_found=True,operation_status='FECHADA/HISTORICO',mt5_ticket=1,local_ticket=None,mt5_time=time,mt5_realized_profit=10,mt5_commission=-1,mt5_swap=0,mt5_fee=0)
    old=source_channel_groups([row('2026-10-21T12:00:01+00:00')])['M8 / XAUUSD']
    assert old['summary']['Encerramentos']==1
    new=source_channel_groups([row('2026-11-03T15:00:01+00:00')])['M8 / XAUUSD']
    assert new['summary']['Encerramentos']==2
    assert [r['ticket'] for r in new['results']]==['old:1','new:1']


def test_cutover_excludes_stale_report_even_with_different_close_time(monkeypatch, tmp_path):
    import json
    from application import account_channel_continuity
    cfg=tmp_path/'config.json'
    cfg.write_text(json.dumps({'report_cutover_utc':'2026-11-03T15:33:26+00:00'}))
    monkeypatch.setattr(account_channel_continuity,'CONFIG',cfg)
    monkeypatch.setattr(account_channel_continuity,'seed_groups',lambda account:{'8/XAUUSD':[dict(id='old:1',time=1793620000000,net=9)]})
    row=SimpleNamespace(mt5_time='2026-11-02T09:00:00+00:00')
    out=source_channel_groups([row])['M8 / XAUUSD']
    assert out['summary']['Encerramentos']==1
