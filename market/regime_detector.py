"""Detector de regime de mercado."""

from dataclasses import dataclass

from domain.market_state import MarketState


@dataclass(frozen=True)
class RegimeDetector:
    """Classifica o regime atual em tendencia ou consolidacao."""

    def detectar(self, estado: MarketState) -> str:
        """Detecta regime usando amplitude, VWAP e posicao no dia."""
        amplitude_ok = estado.candle.amplitude >= estado.atr
        acima_vwap = estado.preco > estado.vwap
        abaixo_vwap = estado.preco < estado.vwap

        if amplitude_ok and acima_vwap and estado.posicao_no_dia > 0.65:
            return "TENDENCIA_ALTA"

        if amplitude_ok and abaixo_vwap and estado.posicao_no_dia < 0.35:
            return "TENDENCIA_BAIXA"

        return "CONSOLIDACAO"
