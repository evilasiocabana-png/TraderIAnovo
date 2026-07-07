"""Pipeline oficial de geracao de features."""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from market.features.feature_definition import FeatureDefinition


FeatureExecutor = Callable[[Any], Any]


@dataclass(frozen=True)
class FeatureExecutionResult:
    """Resultado produzido por uma etapa de feature."""

    feature_id: str
    feature_name: str
    value: Any
    success: bool
    message: str


@dataclass(frozen=True)
class FeatureReport:
    """Relatorio consolidado produzido pelo pipeline."""

    ordered_feature_ids: tuple[str, ...]
    results: tuple[FeatureExecutionResult, ...]
    skipped_feature_ids: tuple[str, ...]
    success: bool


@dataclass(frozen=True)
class FeaturePipeline:
    """Coordena features registradas na ordem recebida."""

    def execute(
        self,
        candles: Any,
        features: Iterable[FeatureDefinition],
        executors: Mapping[str, FeatureExecutor],
    ) -> FeatureReport:
        """Executa os handlers das features sem conhecer sua implementacao."""
        ordered_feature_ids: list[str] = []
        results: list[FeatureExecutionResult] = []
        skipped_feature_ids: list[str] = []

        for feature in features:
            ordered_feature_ids.append(feature.feature_id)
            executor = executors.get(feature.feature_id)
            if executor is None:
                skipped_feature_ids.append(feature.feature_id)
                results.append(
                    FeatureExecutionResult(
                        feature_id=feature.feature_id,
                        feature_name=feature.name,
                        value=None,
                        success=False,
                        message="Executor de feature nao encontrado.",
                    )
                )
                continue

            value = executor(candles)
            results.append(
                FeatureExecutionResult(
                    feature_id=feature.feature_id,
                    feature_name=feature.name,
                    value=value,
                    success=True,
                    message="Feature executada.",
                )
            )

        return FeatureReport(
            ordered_feature_ids=tuple(ordered_feature_ids),
            results=tuple(results),
            skipped_feature_ids=tuple(skipped_feature_ids),
            success=not skipped_feature_ids,
        )
