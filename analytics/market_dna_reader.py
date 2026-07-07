"""Leitor de MARKET DNA para camadas de apresentacao."""

from market.market_dna import MarketDNA, MarketPattern


def get_latest_market_dna(dna: MarketDNA | None = None) -> MarketPattern | None:
    """Retorna o ultimo MARKET DNA disponivel ou None."""
    market_dna = dna or MarketDNA()
    patterns = market_dna.carregar()

    if not patterns:
        return None

    return patterns[-1]
