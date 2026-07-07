"""Estrategia de score baseada em contexto operacional."""

from domain.market_state import MarketState
from strategies.base import Strategy, StrategySignal


class ScoreContextoStrategy(Strategy):
    """Pontua volatilidade, volume, horario e direcao."""

    nome = "score_contexto"

    def analisar(self, estado: MarketState) -> StrategySignal:
        """Gera sinal operacional por score de contexto."""
        score = 0
        motivos: list[str] = []
        score += self._pontuar_volatilidade(estado, motivos)
        score += self._pontuar_volume(estado, motivos)
        score += self._pontuar_horario(estado, motivos)
        decision = self._decidir_direcao(estado, motivos)

        if score < 70 or decision == "WAIT":
            decision = "WAIT"

        return StrategySignal(
            decision=decision,
            score=score,
            confidence=score / 100,
            reasons=motivos,
        )

    def _pontuar_volatilidade(self, estado: MarketState, motivos: list[str]) -> int:
        if estado.candle.amplitude >= 50:
            motivos.append("Volatilidade OK")
            return 20
        motivos.append("Volatilidade baixa")
        return 0

    def _pontuar_volume(self, estado: MarketState, motivos: list[str]) -> int:
        if estado.candle.volume >= 1000:
            motivos.append("Volume OK")
            return 20
        motivos.append("Volume baixo")
        return 0

    def _pontuar_horario(self, estado: MarketState, motivos: list[str]) -> int:
        if 9 <= estado.horario <= 17:
            motivos.append("Horario OK")
            return 10
        motivos.append("Fora do horario")
        return 0

    def _decidir_direcao(self, estado: MarketState, motivos: list[str]) -> str:
        if estado.direcao == "ALTA":
            motivos.append("Tendencia de alta")
            return "BUY"
        if estado.direcao == "BAIXA":
            motivos.append("Tendencia de baixa")
            return "SELL"
        motivos.append("Sem tendencia")
        return "WAIT"
