"""Geracao deterministica de fingerprint de experimentos."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from research.reproducibility.research_snapshot import ResearchSnapshot


@dataclass(frozen=True)
class ExperimentFingerprintResult:
    """Resultado da assinatura unica de um experimento."""

    snapshot_id: str
    experiment_id: str
    fingerprint: str
    algorithm: str
    payload: Mapping[str, object]


@dataclass(frozen=True)
class ExperimentFingerprint:
    """Gera fingerprint deterministico a partir de um snapshot."""

    algorithm: str = "sha256"

    def generate(
        self,
        snapshot: ResearchSnapshot,
    ) -> ExperimentFingerprintResult:
        """Assina somente campos reprodutiveis do experimento."""
        payload = self._payload(snapshot)
        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return ExperimentFingerprintResult(
            snapshot_id=snapshot.snapshot_id,
            experiment_id=snapshot.experiment_id,
            fingerprint=fingerprint,
            algorithm=self.algorithm,
            payload=payload,
        )

    def _payload(self, snapshot: ResearchSnapshot) -> Mapping[str, object]:
        parameters = snapshot.metadata.get("parameters", {})
        return {
            "alpha_id": snapshot.alpha_id,
            "alpha_version": snapshot.alpha_version,
            "configuration_version": snapshot.configuration_version,
            "feature_version": snapshot.feature_version,
            "context_version": snapshot.context_version,
            "risk_version": snapshot.risk_version,
            "research_pipeline_version": snapshot.research_pipeline_version,
            "dataset": snapshot.dataset,
            "replay_period": snapshot.replay_period,
            "random_seed": snapshot.random_seed,
            "parameters": parameters,
        }
