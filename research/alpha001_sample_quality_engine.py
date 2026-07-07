"""Motor de qualidade da amostra de pesquisa Alpha 001."""

from dataclasses import dataclass

from research.alpha001_research_report import Alpha001ResearchResult


@dataclass(frozen=True)
class Alpha001SampleQualityResult:
    """Resultado da avaliacao estrutural da amostra Alpha 001."""

    total_trading_days: int
    average_trades_per_day: float
    maximum_trades_per_day: int
    minimum_trades_per_day: int
    sufficient_sample: bool


@dataclass(frozen=True)
class Alpha001SampleQualityEngine:
    """Avalia qualidade de amostra sem acessar camadas operacionais."""

    minimum_trading_days: int = 1
    minimum_average_trades_per_day: float = 1.0

    def calculate(
        self,
        research_result: Alpha001ResearchResult,
    ) -> Alpha001SampleQualityResult:
        """Calcula estatisticas de amostra a partir do resultado agregado.

        O contrato atual de pesquisa nao possui distribuicao temporal por
        trade. Por isso, esta versao representa a amostra agregada como um
        unico dia logico quando ha operacoes.
        """
        total_trades = research_result.metrics.total_trades
        total_trading_days = 1 if total_trades > 0 else 0
        average = self._average(total_trades, total_trading_days)
        return Alpha001SampleQualityResult(
            total_trading_days=total_trading_days,
            average_trades_per_day=average,
            maximum_trades_per_day=total_trades if total_trading_days else 0,
            minimum_trades_per_day=total_trades if total_trading_days else 0,
            sufficient_sample=self._sufficient(total_trading_days, average),
        )

    def _average(self, total_trades: int, total_trading_days: int) -> float:
        if total_trading_days == 0:
            return 0.0
        return float(total_trades / total_trading_days)

    def _sufficient(
        self,
        total_trading_days: int,
        average_trades_per_day: float,
    ) -> bool:
        return (
            total_trading_days >= self.minimum_trading_days
            and average_trades_per_day >= self.minimum_average_trades_per_day
        )
