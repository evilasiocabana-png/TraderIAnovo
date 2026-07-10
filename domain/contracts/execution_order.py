"""Contrato de ordem operacional normalizada."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionOrder:
    """DTO padrao para ordens de execucao."""

    side: str
    quantity: float
    entry_price: float
    stop: float
    target: float
    symbol: str = "UNKNOWN"
    plan_identity: str = "N/D"
    entry_setup: str = "N/D"
    exit_setup: str = "DYNAMIC_POSITION_MANAGER"
    exit_policy: str = "DYNAMIC_POSITION_MANAGER"
    alpha_id: str = "ALPHA001"
    alpha_version: str = "v1"
    beta_id: str = "LEGACY_CURRENT_EXIT"
    beta_version: str = "BETA v1"
    beta_mode: str = "PROTECT_ONLY"
