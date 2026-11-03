import hashlib
import json
import pytest
from application.account_channel_continuity import continue_results, seed_groups


def config(tmp_path):
    seed=tmp_path/'seed.json'
    seed.write_text(json.dumps({'origin_login':'old','origin_server':'Demo','groups':{'7/XAUUSD':[{'id':'10','time':1000,'net':12}]}}))
    path=tmp_path/'config.json'
    path.write_text(json.dumps({'target_login':'new','target_server':'Demo','seed_path':str(seed),'sha256':hashlib.sha256(seed.read_bytes()).hexdigest()}))
    return path,seed


def test_continues_without_ticket_collision_or_mutating_input(tmp_path):
    path,_=config(tmp_path)
    rows=[{'id':'10','time':2000,'net':-3}]
    out=continue_results({'login':'new','server':'Demo','trade_mode':0},7,'XAUUSD',rows,path)
    assert [r['id'] for r in out]==['old:10','new:10']
    assert sum(r['net'] for r in out)==9
    assert rows[0]['id']=='10'


@pytest.mark.parametrize('account',[{'login':'other','server':'Demo','trade_mode':0},{'login':'new','server':'Other','trade_mode':0},{'login':'new','server':'Demo','trade_mode':2}])
def test_other_accounts_and_real_never_inherit(tmp_path,account):
    path,_=config(tmp_path)
    assert seed_groups(account,path)=={}


def test_corrupt_seed_fails_closed(tmp_path):
    path,seed=config(tmp_path);seed.write_text('{}')
    with pytest.raises(ValueError):seed_groups({'login':'new','server':'Demo','trade_mode':0},path)


def test_missing_config_keeps_original_results(tmp_path):
    rows=[{'id':'1','net':3,'time':2000}]
    assert continue_results({},7,'XAUUSD',rows,tmp_path/'absent') is rows


def test_other_source_does_not_inherit(tmp_path):
    path,_=config(tmp_path)
    assert continue_results({'login':'new','server':'Demo','trade_mode':0},8,'XAUUSD',[],path)==[]
