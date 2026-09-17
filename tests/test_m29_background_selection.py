import ast,json
from pathlib import Path
from types import SimpleNamespace
import pytest
P=Path(__file__).resolve().parents[1]
def load(path,selections,tmp_path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_apply_persisted_operational_model_to_service')
    state=tmp_path/'selection.json';state.write_text(json.dumps({'model':'MODELOS_SELECIONADOS'}))
    ns={'json':json,'DashboardService':object,'MT5_OPERATIONAL_MODEL_STATE_PATH':state,'_load_persisted_mt5_operational_selections':lambda:selections,'MT5_ACTIVE_SOURCE_MODEL_IDS':('M28',),'MT5_OPERATIONAL_MODEL_23':'M23','MT5_OPERATIONAL_MODEL_29':'M29'}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),ns)
    calls=[];ns[fn.name](SimpleNamespace(set_mt5_operational_models=lambda *a,**kw:calls.append((a,kw))))
    return calls[0]
@pytest.mark.parametrize('selected,expected,direct',[(('M23','M29','M28'),('M23','M29'),True),(('M29',),('M29',),False),(('M23',),('M23',),False)])
def test_selected_baskets_survive_background_reload(tmp_path,selected,expected,direct):
    args,kw=load(P/'dashboard_app.py',selected,tmp_path)
    assert kw['basket_models']==expected
    assert kw['direct_models_enabled']==direct
    assert args==(('M28',) if direct else (),)
