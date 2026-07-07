"""Repositorio em memoria para features de mercado."""

from dataclasses import asdict, dataclass

from market.feature_engine import FeatureSnapshot


@dataclass
class FeatureStore:
    """Armazena apenas o ultimo snapshot de features calculado."""

    current_snapshot: FeatureSnapshot | None = None

    def store(self, feature_snapshot: FeatureSnapshot) -> None:
        """Armazena o snapshot de features mais recente."""
        self.current_snapshot = feature_snapshot

    def latest(self) -> FeatureSnapshot | None:
        """Retorna o ultimo snapshot armazenado."""
        return self.current_snapshot

    def clear(self) -> None:
        """Remove o snapshot armazenado."""
        self.current_snapshot = None

    def has_feature(self, nome: str) -> bool:
        """Verifica se a feature existe no snapshot atual."""
        if self.current_snapshot is None:
            return False
        return hasattr(self.current_snapshot, nome)

    def get(self, nome: str) -> object | None:
        """Retorna o valor de uma feature pelo nome."""
        if self.current_snapshot is None:
            return None
        return getattr(self.current_snapshot, nome, None)

    def list_features(self) -> list[str]:
        """Lista os nomes das features disponiveis."""
        if self.current_snapshot is None:
            return []
        return list(asdict(self.current_snapshot).keys())
