"""Registro oficial de definicoes de features."""

from dataclasses import dataclass, field

from market.features.feature_definition import FeatureDefinition


DEFAULT_FEATURE_DEFINITIONS: tuple[FeatureDefinition, ...] = (
    FeatureDefinition(
        feature_id="ATR",
        name="ATR",
        description="Definicao oficial da feature ATR.",
        category="volatility",
        timeframe="1m",
        data_type="float",
        source="market_data",
        version=1,
        author="TraderIA",
        created_at="2026-06-27T22:10:00-03:00",
        enabled=True,
    ),
    FeatureDefinition(
        feature_id="EMA",
        name="EMA",
        description="Definicao oficial da feature EMA.",
        category="trend",
        timeframe="1m",
        data_type="float",
        source="market_data",
        version=1,
        author="TraderIA",
        created_at="2026-06-27T22:10:00-03:00",
        enabled=True,
    ),
    FeatureDefinition(
        feature_id="VWAP",
        name="VWAP",
        description="Definicao oficial da feature VWAP.",
        category="price_volume",
        timeframe="1m",
        data_type="float",
        source="market_data",
        version=1,
        author="TraderIA",
        created_at="2026-06-27T22:10:00-03:00",
        enabled=True,
    ),
    FeatureDefinition(
        feature_id="OpeningRange",
        name="OpeningRange",
        description="Definicao oficial da feature OpeningRange.",
        category="session_structure",
        timeframe="1m",
        data_type="float",
        source="market_data",
        version=1,
        author="TraderIA",
        created_at="2026-06-27T22:10:00-03:00",
        enabled=True,
    ),
    FeatureDefinition(
        feature_id="Momentum",
        name="Momentum",
        description="Definicao oficial da feature Momentum.",
        category="price_action",
        timeframe="1m",
        data_type="float",
        source="market_data",
        version=1,
        author="TraderIA",
        created_at="2026-06-27T22:10:00-03:00",
        enabled=True,
    ),
    FeatureDefinition(
        feature_id="Volume",
        name="Volume",
        description="Definicao oficial da feature Volume.",
        category="participation",
        timeframe="1m",
        data_type="float",
        source="market_data",
        version=1,
        author="TraderIA",
        created_at="2026-06-27T22:10:00-03:00",
        enabled=True,
    ),
    FeatureDefinition(
        feature_id="Volatility",
        name="Volatility",
        description="Definicao oficial da feature Volatility.",
        category="volatility",
        timeframe="1m",
        data_type="float",
        source="market_data",
        version=1,
        author="TraderIA",
        created_at="2026-06-27T22:10:00-03:00",
        enabled=True,
    ),
    FeatureDefinition(
        feature_id="Liquidity",
        name="Liquidity",
        description="Definicao oficial da feature Liquidity.",
        category="liquidity",
        timeframe="1m",
        data_type="float",
        source="market_data",
        version=1,
        author="TraderIA",
        created_at="2026-06-27T22:10:00-03:00",
        enabled=True,
    ),
    FeatureDefinition(
        feature_id="Session",
        name="Session",
        description="Definicao oficial da feature Session.",
        category="session",
        timeframe="1m",
        data_type="str",
        source="market_data",
        version=1,
        author="TraderIA",
        created_at="2026-06-27T22:10:00-03:00",
        enabled=True,
    ),
    FeatureDefinition(
        feature_id="Regime",
        name="Regime",
        description="Definicao oficial da feature Regime.",
        category="market_state",
        timeframe="1m",
        data_type="str",
        source="market_data",
        version=1,
        author="TraderIA",
        created_at="2026-06-27T22:10:00-03:00",
        enabled=True,
    ),
)


@dataclass
class FeatureRegistry:
    """Gerencia definicoes de features em memoria."""

    _features: dict[str, FeatureDefinition] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        for feature in DEFAULT_FEATURE_DEFINITIONS:
            self.register(feature)

    def register(self, feature: FeatureDefinition) -> FeatureDefinition:
        """Registra ou substitui uma definicao de feature."""
        self._features[feature.feature_id] = feature
        return feature

    def unregister(self, feature_id: str) -> bool:
        """Remove uma definicao registrada quando existir."""
        if feature_id not in self._features:
            return False
        del self._features[feature_id]
        return True

    def get(self, feature_id: str) -> FeatureDefinition | None:
        """Retorna uma definicao pelo identificador."""
        return self._features.get(feature_id)

    def list(self) -> tuple[FeatureDefinition, ...]:
        """Lista definicoes registradas."""
        return tuple(self._features.values())

    def exists(self, feature_id: str) -> bool:
        """Indica se uma definicao esta registrada."""
        return feature_id in self._features
