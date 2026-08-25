from __future__ import annotations

from pathlib import Path

from application.model24_setup_contract import (
    MODEL_24_SETUP,
    MODEL_24_SETUP_CONTRACT_FINGERPRINT,
    MODEL_24_SETUP_CONTRACT_VERSION,
    model24_public_setup_fields,
)
from application.model24_xau_basket import (
    MODEL_24_DISTANCE_ATR_MIN,
    MODEL_24_CONTINUATION_VOLUME,
    MODEL_24_FULL_EXIT_USD,
    MODEL_24_INITIAL_VOLUME,
    MODEL_24_INITIAL_TARGET_DISTANCE,
    MODEL_24_LATERALIZATION_VOLUME,
    MODEL_24_PIP_SIZE,
    MODEL_24_REENTRY_VOLUME,
    MODEL_24_RUNTIME_SOURCE,
    MODEL_24_CONTINUATION_TARGET_DISTANCE,
)


ACTIVE_M24_DOCUMENTS = (
    "docs/architecture/OPERATIONAL_MODEL_24_XAU_RSI50_BASKET.md",
    "docs/ACCEPTANCE_CRITERIA.md",
    "docs/ARCHITECTURE.md",
    "docs/architecture/END_TO_END_OPERATIONAL_FLOW.md",
    "docs/SETUP_LOGIC_TRACEABILITY.md",
    "governance/traceability/SETUP_INDEX.md",
    "governance/traceability/TRACEABILITY_MATRIX.md",
    "governance/execution/PROJECT_STATUS.md",
    "governance/execution/NEXT_MISSION.md",
    "governance/programs/PROGRAM_STATUS.md",
)


def test_m24_exported_constants_come_from_canonical_contract() -> None:
    assert MODEL_24_SETUP_CONTRACT_VERSION == MODEL_24_SETUP.version
    assert MODEL_24_SETUP_CONTRACT_FINGERPRINT == MODEL_24_SETUP.fingerprint
    assert len(MODEL_24_SETUP_CONTRACT_FINGERPRINT) == 64
    assert MODEL_24_RUNTIME_SOURCE == MODEL_24_SETUP.runtime_source
    assert MODEL_24_DISTANCE_ATR_MIN == MODEL_24_SETUP.distance_atr_min
    assert not MODEL_24_SETUP.distance_atr_filter_enabled
    assert MODEL_24_PIP_SIZE == MODEL_24_SETUP.pip_size
    assert MODEL_24_INITIAL_VOLUME == MODEL_24_SETUP.initial_volume == 0.10
    assert MODEL_24_REENTRY_VOLUME == MODEL_24_SETUP.reentry_volume == 0.10
    assert MODEL_24_CONTINUATION_VOLUME == MODEL_24_SETUP.continuation_volume == 0.10
    assert MODEL_24_LATERALIZATION_VOLUME == MODEL_24_SETUP.lateralization_volume == 0.10
    assert MODEL_24_SETUP.lateralization_enabled
    assert MODEL_24_SETUP.lateralization_risk_reward == 3.0
    assert "FAILED_FIBONACCI_REENTRY" in MODEL_24_SETUP.lateralization_target_source
    assert MODEL_24_INITIAL_TARGET_DISTANCE == 0.0
    assert MODEL_24_SETUP.initial_target_fibonacci_projection == 1.0
    assert "FIBONACCI_100" in MODEL_24_SETUP.initial_target_source
    assert MODEL_24_CONTINUATION_TARGET_DISTANCE == 0.0
    assert not MODEL_24_SETUP.continuation_individual_target
    assert "PREVIOUS_CLOSED_CANDLE_EXTREME" in (
        MODEL_24_SETUP.continuation_stop_source
    )
    assert "TRAILING_ONLY_FORWARD" in (
        MODEL_24_SETUP.continuation_stop_source
    )
    assert "FIBONACCI_100" in MODEL_24_SETUP.reentry_target_source
    assert MODEL_24_FULL_EXIT_USD == MODEL_24_SETUP.basket_full_exit_usd


def test_m24_public_text_is_derived_from_current_rules() -> None:
    fields = model24_public_setup_fields()
    public_text = " ".join(fields.values()).lower()

    assert MODEL_24_SETUP.version in fields["Contrato"]
    assert MODEL_24_SETUP.initial_requires_rsi_cross
    assert MODEL_24_SETUP.initial_crosses_may_be_asynchronous
    assert not MODEL_24_SETUP.initial_requires_micro_pivot
    assert "preco cruza sma20 e rsi14 cruza 50" in public_text
    assert "podem ocorrer em m5 diferentes" in public_text
    assert "candle que cruzou a sma20" in public_text
    assert "apenas informativo e nao bloqueia" in public_text
    assert "so move o sl abaixo do novo microfundo" in public_text
    assert "ao romper o fundo anterior" in public_text
    assert "micro-pivo 1+1" in public_text
    assert "fibonacci de 100%" in fields["TP inicial"].lower()
    assert "sem alvo fixo de 7,50" in fields["TP inicial"].lower()
    assert "continuation nao usa tp" in public_text
    assert "sl no fundo/topo do ultimo" in public_text
    assert "trailing pelo mesmo extremo a cada novo candle" in public_text
    assert "se o preco vivo ja rompeu o gatilho" in public_text
    assert "initial libera a inversao rsi50" in public_text
    assert MODEL_24_SETUP.initial_rsi50_exit_wait_closed_candles == 2
    assert "esperar 2 m5 fechados apos a entrada" in public_text
    assert "sem descarte da primeira reentrada" in public_text
    assert "minima do candle que cruzou a sma20" in public_text
    assert "nao abre nova ordem" in fields["Lateralizacao"].lower()
    assert "rr 3:1" in fields["Lateralizacao"].lower()
    assert "reaproveita a reentry 0,10 aberta" in fields["Volumes"].lower()


def test_active_m24_documents_declare_exact_contract_fingerprint() -> None:
    project_root = Path(__file__).resolve().parents[1]
    marker = MODEL_24_SETUP.document_marker

    missing = [
        relative_path
        for relative_path in ACTIVE_M24_DOCUMENTS
        if marker not in (project_root / relative_path).read_text(encoding="utf-8")
    ]

    assert missing == [], f"Documentos M24 fora do contrato {marker}: {missing}"
