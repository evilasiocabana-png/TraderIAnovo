from streamlit.testing.v1 import AppTest


def test_learning_panel_renders_empty_truthful_state():
    app=AppTest.from_string('''
from application.learning_dashboard import render_learning_dashboard
class Service:
    def get_learning_dashboard(self, **kwargs):
        return dict(rows=[],total=0,groups=0,bytes=0,sources=[],executions=[],baselines=[],journal=[],pairs=[],comparison=[],m30_enabled=False,
          health=dict(running=True,dropped=0,errors=0,last_error='',path='test.sqlite3',queue=0,queue_limit=512,last_write='',started_at=''))
render_learning_dashboard(Service())
''').run(timeout=20)
    assert not app.exception
    assert any('Aguardando pares' in x.value for x in app.info)
    assert [x.value for x in app.metric][:2] == ['0','0']


def test_learning_has_storage_and_m30_surfaces():
    app=AppTest.from_string('''
from application.learning_dashboard import render_model30_panel
class Service:
    def get_learning_dashboard(self,**kwargs):
        assert kwargs.get('executor') == 'M23'
        return dict(rows=[],pairs=[],comparison=[],m30_enabled=False)
render_model30_panel(Service())
''').run(timeout=20)
    assert not app.exception
    assert app.toggle[0].label=='Executar M30 na mesma Demo do M23'
    assert app.toggle[0].value is False
