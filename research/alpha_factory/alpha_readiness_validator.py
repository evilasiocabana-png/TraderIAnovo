"""Validador de prontidao de hipotese para pesquisa quantitativa."""

from dataclasses import dataclass

from research.alpha_factory.alpha_hypothesis import AlphaHypothesis
from research.alpha_factory.alpha_playbook_template import AlphaPlaybookTemplate


@dataclass(frozen=True)
class AlphaReadinessResult:
    """Resultado da validacao de prontidao de uma Alpha candidata."""

    approved: bool
    validation_messages: tuple[str, ...]


@dataclass(frozen=True)
class AlphaReadinessValidator:
    """Valida apenas criterios declarativos antes da pesquisa."""

    def validate(
        self,
        hypothesis: AlphaHypothesis,
        playbook: AlphaPlaybookTemplate,
    ) -> AlphaReadinessResult:
        """Retorna mensagens de prontidao sem iniciar execucao."""
        messages: list[str] = []
        self._require_text(hypothesis.title, "Hipotese nao definida.", messages)
        self._require_allowed_market(hypothesis, playbook, messages)
        self._require_text(hypothesis.timeframe, "Timeframe nao definido.", messages)
        self._require_text(hypothesis.trigger, "Gatilho nao definido.", messages)
        self._require_items(hypothesis.used_layers, "Camadas usadas ausentes.", messages)
        self._require_items(
            hypothesis.searchable_parameters,
            "Parametros pesquisaveis ausentes.",
            messages,
        )
        self._require_items(playbook.entry_rules, "Regras de entrada ausentes.", messages)
        self._require_items(playbook.exit_rules, "Regras de saida ausentes.", messages)
        self._require_validation_plan(hypothesis, playbook, messages)
        self._require_items(
            hypothesis.approval_criteria or playbook.acceptance_criteria,
            "Criterios de aceitacao ausentes.",
            messages,
        )
        self._require_items(
            hypothesis.rejection_criteria or playbook.rejection_criteria,
            "Criterios de rejeicao ausentes.",
            messages,
        )
        return AlphaReadinessResult(
            approved=not messages,
            validation_messages=tuple(messages),
        )

    def _require_text(
        self,
        value: str,
        message: str,
        messages: list[str],
    ) -> None:
        if not value.strip():
            messages.append(message)

    def _require_items(
        self,
        values: tuple[str, ...],
        message: str,
        messages: list[str],
    ) -> None:
        if not any(value.strip() for value in values):
            messages.append(message)

    def _require_allowed_market(
        self,
        hypothesis: AlphaHypothesis,
        playbook: AlphaPlaybookTemplate,
        messages: list[str],
    ) -> None:
        market = hypothesis.market
        if not market.strip():
            messages.append("Mercado nao definido.")
            return
        forbidden_markets = hypothesis.forbidden_markets or playbook.forbidden_markets
        allowed_markets = hypothesis.allowed_markets or playbook.allowed_markets
        if market in forbidden_markets:
            messages.append("Mercado proibido para a hipotese.")
            return
        if allowed_markets and market not in allowed_markets:
            messages.append("Mercado nao permitido para a hipotese.")

    def _require_validation_plan(
        self,
        hypothesis: AlphaHypothesis,
        playbook: AlphaPlaybookTemplate,
        messages: list[str],
    ) -> None:
        if (
            not hypothesis.validation_plan.strip()
            and not playbook.research_validation.strip()
            and not playbook.replay_validation.strip()
        ):
            messages.append("Plano de validacao ausente.")
