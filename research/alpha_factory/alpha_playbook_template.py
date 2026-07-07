"""Template oficial para documentacao de novas Alphas."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AlphaPlaybookTemplate:
    """Representa um playbook declarativo de Alpha."""

    hypothesis: str
    objective: str
    allowed_markets: tuple[str, ...]
    forbidden_markets: tuple[str, ...]
    context: str
    trigger: str
    filters: tuple[str, ...]
    entry_rules: tuple[str, ...]
    exit_rules: tuple[str, ...]
    risk_management: tuple[str, ...]
    replay_validation: str
    research_validation: str
    rejection_criteria: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
