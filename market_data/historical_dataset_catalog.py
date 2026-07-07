"""Catalogo de datasets historicos disponiveis."""

from dataclasses import dataclass, field

from market_data.historical_data_source_registry import (
    HistoricalDataSourceRegistry,
    create_default_historical_data_source_registry,
)


@dataclass(frozen=True)
class HistoricalDatasetMetadata:
    """Metadados publicos de um dataset historico."""

    dataset_id: str
    ativo: str
    timeframe: str
    start_date: str
    end_date: str
    estimated_candles: int
    provider: str


@dataclass
class HistoricalDatasetCatalog:
    """Catalogo simples de descoberta de datasets historicos."""

    registry: HistoricalDataSourceRegistry = field(
        default_factory=create_default_historical_data_source_registry
    )
    datasets: list[HistoricalDatasetMetadata] = field(default_factory=list)
    dataset_sources: dict[str, object] = field(default_factory=dict)

    def register_dataset(
        self,
        metadata: HistoricalDatasetMetadata,
        source: object | None = None,
    ) -> None:
        """Registra metadados de um dataset historico disponivel."""
        self._ensure_provider_registered(metadata.provider)
        self.datasets.append(metadata)
        self.dataset_sources[metadata.dataset_id] = (
            metadata.dataset_id if source is None else source
        )

    def list_datasets(
        self,
        provider: str | None = None,
    ) -> list[HistoricalDatasetMetadata]:
        """Lista metadados de datasets sem expor origem fisica."""
        if provider is None:
            return self._sorted_datasets(self.datasets)
        normalized = self._normalize(provider)
        return self._sorted_datasets(
            [
                metadata
                for metadata in self.datasets
                if self._normalize(metadata.provider) == normalized
            ]
        )

    def get_dataset(
        self,
        dataset_id: str,
    ) -> HistoricalDatasetMetadata | None:
        """Busca metadados de dataset por identificador."""
        for metadata in self.datasets:
            if metadata.dataset_id == dataset_id:
                return metadata
        return None

    def get_dataset_source(self, dataset_id: str) -> object | None:
        """Retorna origem opaca de um dataset para a camada de aplicacao."""
        if self.get_dataset(dataset_id) is None:
            return None
        return self.dataset_sources.get(dataset_id, dataset_id)

    def available_providers(self) -> list[str]:
        """Lista providers conhecidos pelo catalogo."""
        return self.registry.names()

    def _ensure_provider_registered(self, provider: str) -> None:
        normalized = self._normalize(provider)
        if normalized not in self.registry.names():
            raise KeyError(f"Provider historico nao registrado: {provider}")

    def _sorted_datasets(
        self,
        datasets: list[HistoricalDatasetMetadata],
    ) -> list[HistoricalDatasetMetadata]:
        return sorted(datasets, key=lambda metadata: metadata.dataset_id)

    def _normalize(self, value: str) -> str:
        return value.strip().lower()
