import json
from datetime import datetime

from streamlit.testing.v1 import AppTest
from application.learning_candidate_chart import candidate_curve
from application.learning_policy import context


SNAP = dict(symbol="XAUUSD", direction="BUY", features=dict(trend="UP"),
            stop_management_parameters=dict(source_operational_model="M8"))
CANDIDATE = dict(baseline="b", frozen_at="2026-09-25T00:00:00+00:00", context=json.dumps(context(SNAP)))


def sample(key, **changes):
    row = dict(pair_id=key, created_at="2026-09-26T00:00:00+00:00", status="ACCEPTED",
               m23_state="CLOSED", m30_state="CLOSED", m23_net=-11, m30_net=-12,
               provenance="PROSPECTIVE", baseline="b", first_seen="2026-09-26T00:00:00+00:00",
               signal_snapshot=json.dumps(SNAP), evidence=json.dumps(dict(deals=[dict(
                   time=datetime.fromisoformat("2026-09-26T00:00:00+00:00").timestamp())])))
    return {**row, **changes}


def test_curve_uses_same_pairs_costs_and_frozen_context():
    other = {**SNAP, "direction": "SELL"}
    rows = [sample("1"), sample("1"), sample("2", signal_snapshot=json.dumps(other), m23_net=20, m30_net=18)]
    curve = candidate_curve(CANDIDATE, rows)
    assert curve == [dict(Par=1, M23=-11, M30=-12, **{"Candidato em teste": 0}),
                     dict(Par=2, M23=9, M30=6, **{"Candidato em teste": 20})]


def test_no_backfill_or_unconfirmed_outcomes():
    rows = [sample("old", first_seen=CANDIDATE["frozen_at"]), sample("import", provenance="EXECUTION_LOG_IMPORT"),
            sample("baseline", baseline="other"), sample("open", m30_state="OPEN"),
            sample("cost", m30_net=None), sample("missing", evidence='{}'),
            sample("old_entry", evidence=json.dumps(dict(deals=[dict(time=1)])))]
    assert candidate_curve(CANDIDATE, rows) == []


def test_candidate_render_red_explicit_simulation():
    app = AppTest.from_string('''
from application.learning_dashboard import render_comparison
render_comparison({"candidate_comparison": {"state":"TESTING", "version":"v1", "start":"2026-09-25",
 "rows":[{"Par":1,"M23":-11,"M30":-12,"Candidato em teste":0}]}})
''').run(timeout=20)
    assert not app.exception
    spec = app.get("vega_lite_chart")[0].proto.spec
    assert "#dc2626" in spec
    assert "Candidato em teste" in spec
    assert any("simulacao" in c.value for c in app.caption)


def test_waiting_candidate_has_no_fake_curve():
    app = AppTest.from_string('''
from application.learning_dashboard import render_comparison
render_comparison({"candidate_comparison": {"state":"WAITING", "version":"v1", "start":"2026-09-25", "rows":[]}})
''').run(timeout=20)
    assert not app.exception
    assert any("Aguardando resultados prospectivos" in c.value for c in app.info)
    assert not app.get("vega_lite_chart")
