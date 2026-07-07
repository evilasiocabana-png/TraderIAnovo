"""Validador de reprodutibilidade de experimentos."""

from __future__ import annotations

from dataclasses import dataclass

from research.reproducibility.experiment_fingerprint import (
    ExperimentFingerprint,
    ExperimentFingerprintResult,
)
from research.reproducibility.research_snapshot import ResearchSnapshot


@dataclass(frozen=True)
class ReproducibilityValidationResult:
    """Resultado da validacao de reprodutibilidade."""

    versions_compatible: bool
    configuration_compatible: bool
    fingerprint_valid: bool
    dataset_compatible: bool
    replay_compatible: bool
    is_reproducible: bool
    validation_messages: tuple[str, ...]


@dataclass(frozen=True)
class ReproducibilityValidator:
    """Valida a compatibilidade entre snapshot e fingerprint."""

    def validate(
        self,
        snapshot: ResearchSnapshot,
        fingerprint_result: ExperimentFingerprintResult,
    ) -> ReproducibilityValidationResult:
        """Verifica criterios institucionais de reprodutibilidade."""
        expected = ExperimentFingerprint().generate(snapshot)
        payload = fingerprint_result.payload

        versions_compatible = self._versions_compatible(snapshot, payload)
        configuration_compatible = (
            payload.get("configuration_version") == snapshot.configuration_version
        )
        fingerprint_valid = (
            fingerprint_result.snapshot_id == snapshot.snapshot_id
            and fingerprint_result.experiment_id == snapshot.experiment_id
            and fingerprint_result.fingerprint == expected.fingerprint
            and fingerprint_result.algorithm == expected.algorithm
            and fingerprint_result.payload == expected.payload
        )
        dataset_compatible = payload.get("dataset") == snapshot.dataset
        replay_compatible = payload.get("replay_period") == snapshot.replay_period

        messages = self._messages(
            versions_compatible=versions_compatible,
            configuration_compatible=configuration_compatible,
            fingerprint_valid=fingerprint_valid,
            dataset_compatible=dataset_compatible,
            replay_compatible=replay_compatible,
        )
        is_reproducible = not messages

        return ReproducibilityValidationResult(
            versions_compatible=versions_compatible,
            configuration_compatible=configuration_compatible,
            fingerprint_valid=fingerprint_valid,
            dataset_compatible=dataset_compatible,
            replay_compatible=replay_compatible,
            is_reproducible=is_reproducible,
            validation_messages=messages,
        )

    def _versions_compatible(
        self,
        snapshot: ResearchSnapshot,
        payload: object,
    ) -> bool:
        if not isinstance(payload, dict):
            return False
        return (
            payload.get("alpha_version") == snapshot.alpha_version
            and payload.get("feature_version") == snapshot.feature_version
            and payload.get("context_version") == snapshot.context_version
            and payload.get("risk_version") == snapshot.risk_version
            and payload.get("research_pipeline_version")
            == snapshot.research_pipeline_version
        )

    def _messages(
        self,
        versions_compatible: bool,
        configuration_compatible: bool,
        fingerprint_valid: bool,
        dataset_compatible: bool,
        replay_compatible: bool,
    ) -> tuple[str, ...]:
        messages: list[str] = []
        if not versions_compatible:
            messages.append("Versions are not compatible.")
        if not configuration_compatible:
            messages.append("Configuration is not compatible.")
        if not fingerprint_valid:
            messages.append("Fingerprint is not valid.")
        if not dataset_compatible:
            messages.append("Dataset is not compatible.")
        if not replay_compatible:
            messages.append("Replay period is not compatible.")
        return tuple(messages)
