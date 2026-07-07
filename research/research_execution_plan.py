"""Plano declarativo de execucao do Research Pipeline."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResearchExecutionStep:
    """Etapa declarativa do pipeline de pesquisa."""

    name: str
    order: int
    description: str
    enabled: bool
    required: bool


@dataclass(frozen=True)
class ResearchExecutionPlan:
    """Representa a sequencia oficial sem executar etapas."""

    steps: tuple[ResearchExecutionStep, ...] = field(
        default_factory=lambda: (
            ResearchExecutionStep(
                name="Alpha001Experiment",
                order=1,
                description="Executa o experimento estrutural da Alpha 001.",
                enabled=True,
                required=True,
            ),
            ResearchExecutionStep(
                name="Alpha001MetricsEngine",
                order=2,
                description="Calcula metricas estruturais do experimento.",
                enabled=True,
                required=True,
            ),
            ResearchExecutionStep(
                name="Alpha001ProfitEngine",
                order=3,
                description="Calcula resultado financeiro basico.",
                enabled=True,
                required=True,
            ),
            ResearchExecutionStep(
                name="Alpha001DrawdownEngine",
                order=4,
                description="Calcula drawdown do experimento.",
                enabled=True,
                required=True,
            ),
            ResearchExecutionStep(
                name="Alpha001WinRateEngine",
                order=5,
                description="Calcula taxa de acerto.",
                enabled=True,
                required=True,
            ),
            ResearchExecutionStep(
                name="Alpha001ProfitFactorEngine",
                order=6,
                description="Calcula Profit Factor a partir do lucro.",
                enabled=True,
                required=True,
            ),
            ResearchExecutionStep(
                name="Alpha001ExpectancyEngine",
                order=7,
                description="Calcula Expectancy do experimento.",
                enabled=True,
                required=True,
            ),
            ResearchExecutionStep(
                name="Alpha001BenchmarkComparator",
                order=8,
                description="Compara o resultado com pesquisas de referencia.",
                enabled=True,
                required=True,
            ),
            ResearchExecutionStep(
                name="Alpha001ResearchReport",
                order=9,
                description="Agrega os resultados produzidos pelos engines.",
                enabled=True,
                required=True,
            ),
            ResearchExecutionStep(
                name="Alpha001ResearchValidator",
                order=10,
                description="Valida qualidade estatistica da pesquisa.",
                enabled=True,
                required=True,
            ),
            ResearchExecutionStep(
                name="Alpha001ResearchAdvisor",
                order=11,
                description="Interpreta a validacao estatistica.",
                enabled=True,
                required=True,
            ),
        ),
    )
