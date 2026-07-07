"""Validador declarativo de definicoes de features."""

from dataclasses import dataclass

from market.features.feature_definition import FeatureDefinition


@dataclass(frozen=True)
class FeatureValidationResult:
    """Resultado da validacao de uma definicao de feature."""

    is_valid: bool
    validation_messages: tuple[str, ...]


@dataclass(frozen=True)
class FeatureValidator:
    """Valida apenas campos declarativos de uma feature."""

    def validate(self, feature: FeatureDefinition) -> FeatureValidationResult:
        """Retorna mensagens sobre a definicao recebida."""
        messages: list[str] = []
        self._require_text(feature.name, "Nome da feature nao preenchido.", messages)
        self._require_text(feature.category, "Categoria da feature nao definida.", messages)
        self._require_text(feature.timeframe, "Timeframe da feature nao definido.", messages)
        self._require_version(feature.version, messages)
        self._require_enabled(feature.enabled, messages)
        return FeatureValidationResult(
            is_valid=not messages,
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

    def _require_version(self, version: int, messages: list[str]) -> None:
        if version < 1:
            messages.append("Versao da feature nao definida.")

    def _require_enabled(self, enabled: bool, messages: list[str]) -> None:
        if not enabled:
            messages.append("Feature desabilitada.")
