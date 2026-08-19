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
    MODEL_24_FULL_EXIT_USD,
    MODEL_24_INITIAL_VOLUME,
    MODEL_24_PIP_SIZE,
    MODEL_24_REENTRY_VOLUME,
    MODEL_24_RUNTIME_SOURCE,
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
    assert MODEL_24_PIP_SIZE == MODEL_24_SETUP.pip_size
    assert MODEL_24_INITIAL_VOLUME == MODEL_24_SETUP.initial_volume
    assert MODEL_24_REENTRY_VOLUME == MODEL_24_SETUP.reentry_volume
    assert MODEL_24_FULL_EXIT_USD == MODEL_24_SETUP.basket_full_exit_usd


def test_m24_public_text_is_derived_from_current_rules() -> None:
    fields = model24_public_setup_fields()
    public_text = " ".join(fields.values()).lower()

    assert MODEL_24_SETUP.version in fields["Contrato"]
    assert "sem exigir novo cruzamento do rsi" in public_text
    assert "dois fechamentos favoraveis" in public_text
    assert "micro-pivo 1+1" in public_text
    assert "initial e reentry saem" in public_text
    assert "topo/fundo principal 2+2" not in public_text


def test_active_m24_documents_declare_exact_contract_fingerprint() -> None:
    project_root = Path(__file__).resolve().parents[1]
    marker = MODEL_24_SETUP.document_marker

    missing = [
        relative_path
        for relative_path in ACTIVE_M24_DOCUMENTS
        if marker not in (project_root / relative_path).read_text(encoding="utf-8")
    ]

    assert missing == [], f"Documentos M24 fora do contrato {marker}: {missing}"
