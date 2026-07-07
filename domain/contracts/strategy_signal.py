"""Contrato de sinal produzido por estrategias."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StrategySignal:
    """DTO padrao para comunicar decisoes de estrategia."""

    decision: str
    score: int
    confidence: float
    reasons: list[str] = field(default_factory=list)

    @property
    def decisao(self) -> str:
        """Compatibiliza o contrato com consumidores legados."""
        mapa = {"BUY": "COMPRA", "SELL": "VENDA", "WAIT": "NEUTRO"}
        return mapa.get(self.decision, self.decision)

    @property
    def motivo(self) -> str:
        """Retorna os motivos como texto unico."""
        return ", ".join(self.reasons)

    @property
    def motivos(self) -> list[str]:
        """Compatibiliza reasons com a nomenclatura anterior."""
        return self.reasons
