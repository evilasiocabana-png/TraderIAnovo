from dataclasses import replace
from types import SimpleNamespace
import json
import pytest
from application.dashboard_service import DashboardService
from application.model29_entry_sync import CHANNEL_SOURCES, GoldM7EntrySync, original_plan_for_copy, pair_has_open_copy
from application.model29_sequence_history import closed_m7_positions, sequence_mode
from application.model23_m29_copy import copy_m29_signal, copy_order_error
from application.model29_basket_accumulator import MODEL_29_ID
from application.mt5_demo_robot_service import MT5DemoRobotService
from tests.test_model29_entry_sync import plan, result
from tests.test_model23_context_integration import setup_service


@pytest.mark.parametrize('source', ['M7'])
@pytest.mark.parametrize('mode', ['NORMAL'])
def test_mode_prices_lot_and_matching(tmp_path, monkeypatch, source, mode):
    service, row, original = setup_service(tmp_path, monkeypatch)
    calls = []
    def read(*a, **kw):
        calls.append(a[2])
        return dict(mode='NORMAL',state='Alta',blocked=False,reference='x')
    monkeypatch.setattr('application.source_channel_gate.reference_state', read)
    original = replace(original, direction='SELL', entry_price=100, stop=110, target=75,
        stop_management_parameters=dict(source_operational_model=CHANNEL_SOURCES[source],
            source_initial_stop=110, source_target=75, source_entry_setup='TEST', m29_entry_type='TEST'))
    rr, pp = service._apply_model29_m7_mode(row, original, source)
    assert calls == [int(source[1:])]
    assert pp.direction == ('BUY' if mode == 'ESPELHADO' else 'SELL')
    if mode == 'ESPELHADO':
        assert (pp.stop, pp.target, pp.risk_reward) == (90, 110, 1)
    model, cr, cp = copy_m29_signal(MODEL_29_ID+'_SOURCE_'+source, rr, pp)
    p = cp.stop_management_parameters
    assert p['m23_m29_origin_source'] == source
    assert p['m23_m29_mode'] == mode
    volume = .2
    assert p['execution_volume'] == volume
    order = SimpleNamespace(operational_model=model, symbol='XAUUSD', quantity=volume,
                            plan_snapshot={'stop_management_parameters': p})
    assert copy_order_error(order) is None
    own_signal = SimpleNamespace(operational_model=MODEL_29_ID+'_SOURCE_'+source)
    assert MT5DemoRobotService._execution_volume(None, own_signal, pp) == volume
    sync = GoldM7EntrySync()
    sync.record('MODELO_23_TEST', original, 'candle', result())
    assert sync.claim(original_plan_for_copy(cp), 'candle') == 123
    assert sync.claim(original_plan_for_copy(cp), 'candle') is None


@pytest.mark.parametrize('source', ['M7'])
def test_missing_history_blocks_only_requested_source(tmp_path, monkeypatch, source):
    service, row, pp = setup_service(tmp_path, monkeypatch)
    def unavailable(*a, **kw):
        raise RuntimeError('Sem canal')
    monkeypatch.setattr('application.source_channel_gate.reference_state', unavailable)
    assert service._apply_model29_m7_mode(row, pp, source)[1].status == 'SOURCE_CHANNEL_WAITING'
    assert service._apply_model29_m7_mode(row, pp, 'M5')[1].status == 'SOURCE_CHANNEL_WAITING'


def test_source_history_and_persistence_are_isolated(tmp_path):
    rows=[]
    for source in (7,8,10,18,20):
        for i,net in enumerate([100,-100,200,-100,200,-100,-200]):
            pid=source*100+i
            base=dict(position_id=pid,type=0,volume=.1,symbol='XAUUSD',swap=0,commission=0,fee=0,time=pid,time_msc=pid*1000)
            rows.extend([{**base,'entry':0,'profit':0,'comment':f'TraderIA M23 S{source} TEST'},
                         {**base,'entry':1,'profit':net,'comment':'[sl]'}])
    payload=dict(ok=True,account=dict(login=1,server='Test'),rows=rows,open_positions=[])
    provider=SimpleNamespace(_external_mt5_read=lambda *a,**kw:payload)
    for source in (7,8,10,18,20):
        found=closed_m7_positions(payload,source)
        assert len(found)==7 and all(int(r['position'])//100==source for r in found)
        assert sequence_mode(provider,'XAUUSD',tmp_path,source_number=source)==('ESPELHADO' if source == 7 else 'NORMAL')
    docs=[json.loads(p.read_text()) for p in tmp_path.rglob('*.json')]
    assert len(docs)==5
    assert {d['symbols']['XAUUSD']['reference_source'] for d in docs}=={7,8,10,18,20}


def test_pair_matching_does_not_cross_sources(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    m7=plan()
    m8=replace(m7,stop_management_parameters={**m7.stop_management_parameters,'source_operational_model':'MODELO_8_XAU_M5_SMA_RSI_REENTRY'})
    sync=GoldM7EntrySync()
    sync.record('MODELO_23_TEST',m7,'candle',result())
    assert sync.claim(m8,'candle') is None
    assert sync.claim(m7,'candle')==123
    opened=[SimpleNamespace(symbol='XAUUSD',comment='TraderIA M23 S8 TEST')]
    assert pair_has_open_copy(opened,'M8')
    assert not pair_has_open_copy(opened,'M7')
    tagged=[SimpleNamespace(symbol='XAUUSD',comment='TraderIA M23 S29 M8 TEST')]
    assert pair_has_open_copy(tagged,'M8')
    assert not pair_has_open_copy(tagged,'M7')
