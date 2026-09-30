from types import SimpleNamespace
from application.report_current_policy import current_policy_rows, M30_POLICY, REINFORCEMENT_POLICY


def row(**parameters):
    return SimpleNamespace(plan_snapshot={"stop_management_parameters": parameters})


def test_m30_uses_policy_not_date_or_mode():
    normal = row(m30_policy=M30_POLICY, m30_baseline_model="MODELO_7_LAB_XAU_BTC", m30_mode="NORMAL")
    mirror = row(m30_policy=M30_POLICY, m30_baseline_model="MODELO_7_LAB_XAU_BTC", m30_mode="ESPELHADO")
    legacy = row(m30_mode="ESPELHADO")
    unknown = SimpleNamespace(plan_snapshot=None)
    assert current_policy_rows([legacy, normal, unknown, mirror], "M30") == [normal, mirror]


def test_m29_sequence_excludes_channel_and_unknown():
    sequence = row(m23_m29_origin_source="M7", reinforcement_policy=REINFORCEMENT_POLICY, m23_m29_mode="NORMAL")
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


def test_m30_excludes_other_sources_and_missing_source():
    m7 = row(m30_policy=M30_POLICY, m30_baseline_model="MODELO_7_LAB_XAU_BTC")
    m18 = row(m30_policy=M30_POLICY, m30_baseline_model="MODELO_18_XAU_M5_SMA_RSI_REENTRY_TP75")
    unknown = row(m30_policy=M30_POLICY)
    assert current_policy_rows([m18, unknown, m7], "M30", m7_only=True) == [m7]


def test_general_retains_other_sources_and_m7_is_subset():
    m7 = row(m30_policy=M30_POLICY, m30_baseline_model="MODELO_7_LAB_XAU_BTC")
    m18 = row(m30_policy=M30_POLICY, m30_baseline_model="MODELO_18_XAU_M5_SMA_RSI_REENTRY_TP75")
    assert current_policy_rows([m7, m18], "M30") == [m7, m18]
    mirror = row(m23_m29_origin_source="M7", reinforcement_policy=REINFORCEMENT_POLICY, m23_m29_mode="NORMAL")
    normal = row(m23_m29_origin_source="M18", reinforcement_policy=REINFORCEMENT_POLICY, m23_m29_mode="NORMAL")
    assert current_policy_rows([mirror, normal], "M29") == [mirror, normal]
    assert current_policy_rows([mirror, normal], "M29", m7_only=True) == [mirror]
