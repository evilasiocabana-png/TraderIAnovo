"""Servico de aplicacao para analise de regime de mercado."""

from dataclasses import dataclass

from domain.contracts.market_snapshot import MarketSnapshot
from market.regime_engine import RegimeEngine


@dataclass(frozen=True)
class RegimeData:
    """Dados de regime prontos para consumo da aplicacao."""

    regime: str
    confidence: float
    description: str


@dataclass(frozen=True)
class RegimeService:
    """Expoe o RegimeEngine sem acoplar consumidores ao motor."""

    regime_engine: RegimeEngine = RegimeEngine()

    def analyze(self, market_snapshot: MarketSnapshot) -> RegimeData:
        """Analisa o snapshot de mercado e retorna dados de aplicacao."""
        analysis = self.regime_engine.analyze(market_snapshot)
        return RegimeData(
            regime=analysis.regime.value,
            confidence=analysis.confidence,
            description=analysis.description,
        )
