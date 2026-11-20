from application.learning_summary import learning_summary
from application.learning_store import LearningStore
from application.learning_policy import tables
from streamlit.testing.v1 import AppTest


def test_summary_reads_unique_candidates_and_actual_active_filter(tmp_path):
    store=LearningStore(tmp_path/'learning.sqlite3')
    with store.connect() as db:
        tables(db)
        db.execute("INSERT INTO baselines VALUES ('base','2026-09-25','{}')")
        for ident,state,base in [('one','TESTING','base'),('two','APPLIED','base'),('old','APPLIED','old'),('bad','REJECTED','base')]:
            db.execute('INSERT INTO learning_candidates VALUES (?,?,?,?,?,?,?,?)',(ident,base,'2026-09-25',state,'{}','{}','2026-09-25',None))
        db.execute("INSERT INTO metadata VALUES ('m30_active_filter:scope','two')")
    value=learning_summary(store)
    assert (value['candidates'],value['testing'],value['applied'],value['rejected'])==(4,1,1,1)
    with store.connect() as db:
        db.execute("UPDATE metadata SET value='old' WHERE key='m30_active_filter:scope'")
    assert learning_summary(store)['applied']==0


def test_summary_is_visible_before_charts():
    app=AppTest.from_string('''
from application.learning_dashboard import render_learning_summary
render_learning_summary(dict(m30_enabled=True,summary=dict(available=True,candidates=3,testing=1,applied=0,rejected=2,reverted=0,latest=None)))
''').run(timeout=20)
    assert not app.exception
    assert [x.value for x in app.metric]==['3','1','0','2']
    assert 'Candidato em teste' in app.info[0].value


def test_missing_summary_not_misrepresented_as_zero():
    app=AppTest.from_string('''
from application.learning_dashboard import render_learning_summary
render_learning_summary({})
''').run(timeout=20)
    assert not app.exception
    assert not app.metric
    assert 'indisponível' in app.info[0].value
