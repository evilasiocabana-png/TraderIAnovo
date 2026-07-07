"""Servico de aplicacao para dados de mercado."""

from dataclasses import dataclass, field
from typing import Callable

from analytics.market_dna_reader import get_latest_market_dna
from core.configuration_manager import ConfigurationManager, SystemConfiguration
from domain.contracts.market_snapshot import MarketSnapshot
from market.market_dna import MarketPattern


@dataclass(frozen=True)
class MarketService:
    """Fornece dados de mercado para camadas de apresentacao."""

    latest_market_dna_reader: Callable[[], MarketPattern | None] = get_latest_market_dna
    configuration: SystemConfiguration = field(
        default_factory=ConfigurationManager.get_configuration
    )

    def get_latest_market_dna(self) -> MarketSnapshot | None:
        """Retorna o ultimo MARKET DNA como contrato de dominio."""
        pattern = self.latest_market_dna_reader()
        if pattern is None:
            return None
        return self._to_snapshot(pattern)

    def get_regime(self) -> str:
        """Retorna o regime do ultimo MARKET DNA."""
        snapshot = self.get_latest_market_dna()
        return snapshot.regime if snapshot else "N/D"

    def get_score(self) -> float | None:
        """Retorna o score do ultimo MARKET DNA."""
        snapshot = self.get_latest_market_dna()
        return snapshot.market_dna_score if snapshot else None

    def get_volatility(self) -> float | None:
        """Retorna a volatilidade do ultimo MARKET DNA."""
        snapshot = self.get_latest_market_dna()
        return snapshot.volatility if snapshot else None

    def get_liquidity(self) -> float | None:
        """Retorna a liquidez do ultimo MARKET DNA."""
        snapshot = self.get_latest_market_dna()
        return snapshot.liquidity if snapshot else None

    def _to_snapshot(self, pattern: MarketPattern) -> MarketSnapshot:
        return MarketSnapshot(
            symbol=self.configuration.symbol,
            datetime=f"{pattern.data} {pattern.horario}".strip(),
            regime=pattern.direcao,
            volatility=pattern.atr,
            liquidity=float(pattern.volume),
            trend_strength=pattern.posicao_no_dia,
            market_dna_score=0.0,
        )
