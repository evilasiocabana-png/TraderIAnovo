"""Independent dynamic-exit variants of the active fixed models M1-M7."""

from __future__ import annotations

from dataclasses import dataclass

from application.lab_operational_model_service import (
    MODEL_2_ID,
    MODEL_4_ID,
    MODEL_5_ID,
)
from application.model3_all_forex_winners import MODEL_3_ID
from application.model6_lab_forex_expansion import MODEL_6_ID
from application.model7_lab_alternative_markets import MODEL_7_ID


MODEL_1_ID = "MODELO_1_ALPHA_ATUAL"
DYNAMIC_EXIT_POLICY = "DYNAMIC_PROTECT_ONLY"
DYNAMIC_EXIT_BETA_MODE = "DYNAMIC_PROTECT_ONLY"
DYNAMIC_EXIT_PROTOCOL_VERSION = "DYNAMIC_EXIT_FAMILY_V1"


@dataclass(frozen=True)
class DynamicExitModelSpec:
    """Identity and source contract for one dynamic-exit model."""

    number: int
    model_id: str
    source_number: int
    source_model_id: str
    beta_id: str
    beta_version: str

    @property
    def short_name(self) -> str:
        return f"M{self.number}"

    @property
    def source_short_name(self) -> str:
        return f"M{self.source_number}"


_SOURCE_MODELS = (
    MODEL_1_ID,
    MODEL_2_ID,
    MODEL_3_ID,
    MODEL_4_ID,
    MODEL_5_ID,
    MODEL_6_ID,
    MODEL_7_ID,
)


def _build_spec(number: int, source_number: int, source_model_id: str) -> DynamicExitModelSpec:
    beta_id = f"BETA{number:03d}_DYNAMIC_FROM_M{source_number}"
    return DynamicExitModelSpec(
        number=number,
        model_id=f"MODELO_{number}_DYNAMIC_EXIT_FROM_M{source_number}",
        source_number=source_number,
        source_model_id=source_model_id,
        beta_id=beta_id,
        beta_version=f"{beta_id}_V1",
    )


DYNAMIC_EXIT_MODEL_SPECS = tuple(
    _build_spec(number, source_number, source_model_id)
    for number, source_number, source_model_id in zip(
        range(8, 15),
        range(1, 8),
        _SOURCE_MODELS,
    )
)
DYNAMIC_EXIT_MODEL_IDS = tuple(spec.model_id for spec in DYNAMIC_EXIT_MODEL_SPECS)
DYNAMIC_EXIT_MODEL_BY_ID = {
    spec.model_id: spec for spec in DYNAMIC_EXIT_MODEL_SPECS
}
DYNAMIC_EXIT_SOURCE_BY_MODEL = {
    spec.model_id: spec.source_model_id for spec in DYNAMIC_EXIT_MODEL_SPECS
}

(
    MODEL_8_ID,
    MODEL_9_ID,
    MODEL_10_ID,
    MODEL_11_ID,
    MODEL_12_ID,
    MODEL_13_ID,
    MODEL_14_ID,
) = DYNAMIC_EXIT_MODEL_IDS


def dynamic_exit_model_spec(model_id: object) -> DynamicExitModelSpec | None:
    """Return the dynamic variant contract for an operational model ID."""
    return DYNAMIC_EXIT_MODEL_BY_ID.get(str(model_id or "").upper())


def dynamic_exit_source_model(model_id: object) -> str | None:
    """Return the fixed entry model copied by one dynamic variant."""
    spec = dynamic_exit_model_spec(model_id)
    return spec.source_model_id if spec is not None else None


def dynamic_exit_parameters(
    source_parameters: dict[str, object] | None = None,
) -> dict[str, object]:
    """Preserve entry parameters and append the shared protection thresholds."""
    return {
        **dict(source_parameters or {}),
        "break_even_trigger_rr": 1.5,
        "atr_trailing_activation_rr": 1.5,
        "atr_trailing_factor": 2.0,
        "early_exit_enabled": False,
        "full_exit_enabled": False,
        "dynamic_exit_protocol": DYNAMIC_EXIT_PROTOCOL_VERSION,
    }
