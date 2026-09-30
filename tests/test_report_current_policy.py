from types import SimpleNamespace
from application.report_current_policy import current_policy_rows, M30_POLICY


def row(**parameters):
    return SimpleNamespace(plan_snapshot={"stop_management_parameters": parameters})


def test_m30_uses_policy_not_date_or_mode():
    normal = row(m30_policy=M30_POLICY, m30_mode="NORMAL")
    mirror = row(m30_policy=M30_POLICY, m30_mode="ESPELHADO")
    legacy = row(m30_mode="ESPELHADO")
    unknown = SimpleNamespace(plan_snapshot=None)
    assert current_policy_rows([legacy, normal, unknown, mirror], "M30") == [normal, mirror]


def test_m29_sequence_excludes_channel_and_unknown():
    sequence = row(m23_m29_origin_source="M7", m29_sequence_mode="ESPELHADO")
    normal = row(m23_m29_origin_source="M7", m29_sequence_mode="NORMAL")
    channel = row(m23_m29_origin_source="M7", m29_channel_mode="ESPELHADO")
    unknown = row(m23_m29_origin_source="M7", m29_mirrored=True)
    other = row(m23_m29_origin_source="M8", m29_sequence_mode="NORMAL")
    assert current_policy_rows([sequence, channel, unknown, normal, other], "M29") == [sequence]


def test_scope_does_not_modify_history_or_other_models():
    rows = [row(m30_mode="NORMAL")]
    assert current_policy_rows(rows, "M30") == []
    assert len(rows) == 1
    assert current_policy_rows(rows, "M23") == rows
