"""Validador estatistico inicial para benchmarks do Research Lab."""

from dataclasses import dataclass, field

from research.strategy_benchmark import StrategyBenchmarkResult


@dataclass(frozen=True)
class ExperimentValidation:
    """Resultado da validacao estatistica de um experimento."""

    sample_size: int
    is_statistically_relevant: bool
    confidence_level: str
    warnings: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass(frozen=True)
class ExperimentValidator:
    """Valida relevancia estatistica sem IA ou execucao operacional."""

    def validate(
        self,
        benchmark: StrategyBenchmarkResult,
    ) -> ExperimentValidation:
        """Valida um benchmark com regras estatisticas simples."""
        sample_size = benchmark.total_trades
        confidence_level = self._confidence_level(sample_size)
        warnings = self._warnings(benchmark)
        return ExperimentValidation(
            sample_size=sample_size,
            is_statistically_relevant=sample_size >= 30,
            confidence_level=confidence_level,
            warnings=warnings,
            summary=self._summary(sample_size, confidence_level, warnings),
        )

    def _confidence_level(self, sample_size: int) -> str:
        if sample_size < 30:
            return "Nao confiavel"
        if sample_size <= 100:
            return "Confiabilidade media"
        return "Confiabilidade alta"

    def _warnings(self, benchmark: StrategyBenchmarkResult) -> list[str]:
        warnings: list[str] = []
        if benchmark.total_trades < 30:
            warnings.append("Pouca amostra")
        if benchmark.wins < 10:
            warnings.append("Poucas vitorias")
        if benchmark.profit_factor < 1.2:
            warnings.append("Profit Factor baixo")
        if benchmark.win_rate < 0.45:
            warnings.append("Win Rate baixo")
        return warnings

    def _summary(
        self,
        sample_size: int,
        confidence_level: str,
        warnings: list[str],
    ) -> str:
        base = (
            f"O experimento possui {sample_size} operacoes e foi classificado "
            f"como {confidence_level}."
        )
        if not warnings:
            return f"{base} Nenhum alerta estatistico relevante foi encontrado."
        return f"{base} Alertas: {', '.join(warnings)}."
