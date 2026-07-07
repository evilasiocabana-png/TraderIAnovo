"""Motor institucional de avaliacao de descontinuacao de Alpha."""

from __future__ import annotations

from dataclasses import dataclass

from research.alpha_factory.alpha_health_engine import AlphaHealthResult


@dataclass(frozen=True)
class AlphaDeprecationResult:
    """Resultado da avaliacao de descontinuacao de uma Alpha."""

    decision: str
    reasons: tuple[str, ...]
    keep_threshold: float
    watch_threshold: float
    deprecate_threshold: float
    lifecycle_changed: bool = False
    alpha_deleted: bool = False


@dataclass(frozen=True)
class AlphaDeprecationEngine:
    """Avalia se uma Alpha deve ser mantida, observada ou descontinuada."""

    keep_threshold: float = 0.70
    watch_threshold: float = 0.40
    deprecate_threshold: float = 0.30

    def evaluate(
        self,
        health_result: AlphaHealthResult,
    ) -> AlphaDeprecationResult:
        """Produz uma decisao institucional sem alterar lifecycle ou registry."""
        critical_reasons = tuple(self._critical_reasons(health_result))
        warning_reasons = tuple(self._warning_reasons(health_result))

        if health_result.health_score < self.watch_threshold or critical_reasons:
            decision = "DEPRECATE"
            reasons = critical_reasons or (
                "Saude geral abaixo do limite de descontinuacao.",
            )
        elif health_result.health_score < self.keep_threshold or warning_reasons:
            decision = "WATCH"
            reasons = warning_reasons or (
                "Saude geral abaixo do limite de manutencao.",
            )
        else:
            decision = "KEEP"
            reasons = ("Alpha permanece dentro dos limites institucionais.",)

        return AlphaDeprecationResult(
            decision=decision,
            reasons=reasons,
            keep_threshold=self.keep_threshold,
            watch_threshold=self.watch_threshold,
            deprecate_threshold=self.deprecate_threshold,
            lifecycle_changed=False,
            alpha_deleted=False,
        )

    def _critical_reasons(
        self,
        health_result: AlphaHealthResult,
    ) -> list[str]:
        reasons: list[str] = []
        if health_result.robustness_score < self.deprecate_threshold:
            reasons.append("Baixa robustez estatistica.")
        if health_result.reproducibility_score < self.deprecate_threshold:
            reasons.append("Baixa reprodutibilidade.")
        if health_result.campaign_score < self.deprecate_threshold:
            reasons.append("Excesso de campanhas reprovadas.")
        if health_result.validation_score < self.deprecate_threshold:
            reasons.append("Degradacao estatistica.")
        return reasons

    def _warning_reasons(
        self,
        health_result: AlphaHealthResult,
    ) -> list[str]:
        reasons: list[str] = []
        if health_result.robustness_score < self.keep_threshold:
            reasons.append("Robustez abaixo do ideal.")
        if health_result.reproducibility_score < self.keep_threshold:
            reasons.append("Reprodutibilidade abaixo do ideal.")
        if health_result.campaign_score < self.keep_threshold:
            reasons.append("Campanhas com performance abaixo do ideal.")
        if health_result.validation_score < self.keep_threshold:
            reasons.append("Validacao estatistica abaixo do ideal.")
        return reasons
