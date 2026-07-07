"""Servico de aplicacao para expor o ResearchLab."""

import csv
from dataclasses import dataclass, field
from pathlib import Path

from application.alpha001_research_service import Alpha001ResearchService
from alpha.alpha001_config import Alpha001Config
from domain.candle import Candle
from market_data import HistoricalDataProvider, MarketDataProvider
from research.benchmark_comparator import BenchmarkComparison
from research.experiment_validator import ExperimentValidation
from research.alpha001_parameter_ranking import Alpha001ParameterRanking
from research.alpha001_parameter_sweep import (
    Alpha001ParameterSet,
    Alpha001ParameterSweep,
    Alpha001ParameterSweepResult,
)
from research.alpha001_result_exporter import Alpha001ResultExporter
from research.alpha001_research_summary import (
    Alpha001ResearchSummary,
    Alpha001ResearchSummaryResult,
)
from research.alpha001_robustness_analyzer import (
    Alpha001RobustnessAnalyzer,
    Alpha001RobustnessResult,
)
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_benchmark_comparator import (
    Alpha001BenchmarkComparator,
)
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_research_advisor import Alpha001ResearchAdvisor
from research.alpha001_research_validator import Alpha001ResearchValidator
from research.research_lab import (
    ParameterGridResult,
    ResearchExperiment,
    ResearchLab,
)
from research.live_experiment_runner import (
    LiveExperimentRunner,
    LiveExperimentSignal,
    LiveExperimentSummary,
)
from research.alpha001_experiment import Alpha001Experiment
from research.campaigns.research_campaign import ResearchCampaign
from research.research_execution_plan import ResearchExecutionPlan
from research.research_execution_result import ResearchExecutionResult
from research.research_runner import ResearchRunner
from research.research_report import ResearchReport, ResearchReportResult
from research.strategy_benchmark import StrategyBenchmarkResult
from strategies.strategy_factory import StrategyFactory


@dataclass(frozen=True)
class ResearchExperimentData:
    """DTO de experimento quantitativo pronto para dashboard."""

    experiment_name: str
    strategy_name: str
    stop_points: float
    target_points: float
    total_trades: int
    wins: int
    losses: int
    net_profit_points: float
    win_rate: float
    profit_factor: float
    max_drawdown_points: float


@dataclass(frozen=True)
class BenchmarkData:
    """DTO de benchmark de estrategia para dashboard."""

    strategy_name: str
    total_trades: int
    wins: int
    losses: int
    net_profit_points: float
    win_rate: float
    profit_factor: float
    max_drawdown_points: float
    equity_curve: list[float]


@dataclass(frozen=True)
class BenchmarkComparisonData:
    """DTO de comparacao de benchmarks para dashboard."""

    best_strategy: str | None
    best_profit: float
    best_profit_factor: float
    best_drawdown: float
    best_win_rate: float
    ranking: list[BenchmarkData]


@dataclass(frozen=True)
class ParameterGridData:
    """DTO de resultado da grade de parametros."""

    stop_points: float
    target_points: float
    strategy_name: str
    total_trades: int
    wins: int
    losses: int
    net_profit_points: float
    win_rate: float
    profit_factor: float
    max_drawdown_points: float


@dataclass(frozen=True)
class ExperimentValidationData:
    """DTO de validacao estatistica para dashboard."""

    sample_size: int
    is_statistically_relevant: bool
    confidence_level: str
    warnings: list[str]
    summary: str


@dataclass(frozen=True)
class Alpha001ResearchReportData:
    """Relatorio consolidado da validacao inicial da Alpha 001."""

    strategy_name: str
    validation_status: str
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_points: float
    net_profit_points: float
    real_trading_authorized: bool
    summary: str


@dataclass(frozen=True)
class Alpha001DashboardResearchData:
    """Metricas Alpha001 prontas para exibicao no dashboard."""

    total_trades: int = 0
    total_buy: int = 0
    total_sell: int = 0
    total_wait: int = 0
    net_profit: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    max_drawdown: float = 0.0
    drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    recommendation: str = "INSUFFICIENT_SAMPLE"
    equity_curve: list[float] = field(default_factory=lambda: [0.0])
    benchmark: "Alpha001DashboardBenchmarkData" = field(
        default_factory=lambda: Alpha001DashboardBenchmarkData()
    )


@dataclass(frozen=True)
class Alpha001DashboardBenchmarkData:
    """Benchmark Alpha001 entre experimentos pronto para dashboard."""

    total_results: int = 0
    best_overall: str | None = None
    best_total_trades: str | None = None
    best_net_profit: str | None = None
    best_max_drawdown: str | None = None
    best_profit_factor: str | None = None
    best_win_rate: str | None = None
    best_expectancy: str | None = None
    ranking: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Alpha001ParameterRankingData:
    """DTO do ranking de parametros da Alpha 001 para dashboard."""

    opening_range_minutes: int
    minimum_range_size: float
    minimum_volume: int
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_points: float
    net_profit_points: float
    validation_status: str


@dataclass(frozen=True)
class Alpha001ResearchSummaryData:
    """DTO do resumo estatistico Alpha001 para dashboard."""

    total_experiments: int
    total_approved: int
    total_rejected: int
    best_profit_factor: float
    lowest_max_drawdown_points: float
    best_net_profit_points: float
    best_configuration: Alpha001ParameterRankingData | None
    approval_rate: float


@dataclass(frozen=True)
class Alpha001RobustnessData:
    """DTO da analise de robustez Alpha001 para dashboard."""

    robustness_score: float
    status: str
    reasons: list[str]


@dataclass(frozen=True)
class ResearchReportData:
    """DTO de relatorio consolidado de experimento para dashboard."""

    parameters: dict[str, object]
    metrics: dict[str, float | int]
    statistical_summary: str
    conclusion: str
    conclusion_reasons: list[str]


@dataclass(frozen=True)
class RealDataResearchData:
    """Resultado consolidado da pesquisa usando dataset historico real."""

    dataset_id: str
    campaign_id: str
    experiment: ResearchExperimentData
    research_runner_status: str
    validation_suite_status: str
    benchmark_comparison: BenchmarkComparisonData
    portfolio_status: str
    total_validations: int
    total_benchmarks: int
    total_candles: int


@dataclass(frozen=True)
class LiveExperimentSignalData:
    """DTO de sinal live registrado pelo Research Lab."""

    timestamp: str
    symbol: str
    timeframe: str
    strategy_name: str
    decision: str
    confidence: float
    regime: str


@dataclass(frozen=True)
class LiveExperimentSummaryData:
    """DTO do resumo estatistico live para aplicacao/dashboard."""

    total_signals: int = 0
    buy_count: int = 0
    sell_count: int = 0
    wait_count: int = 0
    average_confidence: float = 0.0
    confidence_std: float = 0.0
    by_regime: dict[str, int] = field(default_factory=dict)
    by_strategy: dict[str, int] = field(default_factory=dict)


@dataclass
class ResearchLabService:
    """Fachada de aplicacao para experimentos quantitativos."""

    research_lab: ResearchLab = field(default_factory=ResearchLab)
    market_data_provider: MarketDataProvider = field(
        default_factory=HistoricalDataProvider
    )
    strategy_factory: StrategyFactory = field(default_factory=StrategyFactory)
    live_experiment_runner: LiveExperimentRunner = field(
        default_factory=LiveExperimentRunner
    )
    alpha001_parameter_sweep: Alpha001ParameterSweep = field(
        default_factory=Alpha001ParameterSweep,
    )
    alpha001_parameter_ranking: Alpha001ParameterRanking = field(
        default_factory=Alpha001ParameterRanking,
    )
    alpha001_result_exporter: Alpha001ResultExporter = field(
        default_factory=Alpha001ResultExporter,
    )
    alpha001_research_summary: Alpha001ResearchSummary = field(
        default_factory=Alpha001ResearchSummary,
    )
    alpha001_robustness_analyzer: Alpha001RobustnessAnalyzer = field(
        default_factory=Alpha001RobustnessAnalyzer,
    )
    alpha001_research_service: Alpha001ResearchService = field(
        default_factory=Alpha001ResearchService,
    )
    alpha001_research_validator: Alpha001ResearchValidator = field(
        default_factory=lambda: Alpha001ResearchValidator(
            minimum_trades=30,
            minimum_profit_factor=1.2,
            maximum_drawdown=100.0,
            minimum_win_rate=0.4,
        ),
    )
    alpha001_research_advisor: Alpha001ResearchAdvisor = field(
        default_factory=Alpha001ResearchAdvisor,
    )
    alpha001_ranking_results: list[Alpha001ParameterRankingData] = field(
        default_factory=list,
    )
    alpha001_raw_ranking_results: list[Alpha001ParameterSweepResult] = field(
        default_factory=list,
    )

    def run_demo_experiment(self) -> ResearchExperimentData:
        """Executa um experimento demonstrativo em memoria."""
        experiment = ResearchExperiment(
            experiment_name="Demo Research Lab",
            strategy_name="alpha001_iorb",
            stop_points=50.0,
            target_points=100.0,
            candles=self._demo_candles(),
        )
        return self._to_data(self.research_lab.run_experiment(experiment))

    def run_demo_alpha001_experiment(self) -> ResearchExperimentData:
        """Executa Alpha001Experiment demo pelo Research Lab."""
        experiment = ResearchExperiment(
            experiment_name="Demo Alpha001 Experiment",
            strategy_name="alpha001_iorb",
            stop_points=50.0,
            target_points=100.0,
            candles=self._demo_benchmark_candles(),
        )
        return self._to_data(
            self.research_lab.run_alpha001_experiment(
                experiment,
                config=Alpha001Config(),
            )
        )

    def run_alpha001_research(
        self,
        candles: list[Candle],
        config: Alpha001Config | None = None,
        experiment_name: str = "Alpha001 Research",
    ) -> Alpha001ResearchResult:
        """Executa Alpha001Experiment e consolida o resultado de pesquisa."""
        alpha_config = config or Alpha001Config()
        experiment = ResearchExperiment(
            experiment_name=experiment_name,
            strategy_name="alpha001_iorb",
            stop_points=alpha_config.initial_stop_points,
            target_points=alpha_config.initial_target_points,
            candles=list(candles),
        )
        completed = self.research_lab.run_alpha001_experiment(
            experiment,
            config=alpha_config,
        )
        if not isinstance(completed.result, Alpha001ExperimentResult):
            raise TypeError("Research Lab nao retornou Alpha001ExperimentResult.")
        return self.alpha001_research_service.run(completed.result)

    def run_historical_experiment(
        self,
        candles: list[Candle],
        experiment_name: str = "Historical WDO Research",
        strategy_name: str = "alpha001_iorb",
        stop_points: float = 50.0,
        target_points: float = 100.0,
    ) -> ResearchExperimentData:
        """Executa experimento com dataset historico ja importado."""
        experiment = ResearchExperiment(
            experiment_name=experiment_name,
            strategy_name=strategy_name,
            stop_points=stop_points,
            target_points=target_points,
            candles=list(candles),
        )
        return self._to_data(self.research_lab.run_experiment(experiment))

    def run_historical_csv_experiment(
        self,
        path: str | Path,
        experiment_name: str = "Historical WDO Research",
        strategy_name: str = "alpha001_iorb",
        stop_points: float = 50.0,
        target_points: float = 100.0,
    ) -> ResearchExperimentData:
        """Importa dataset historico via provider e executa experimento."""
        return self.run_historical_data_experiment(
            source=path,
            experiment_name=experiment_name,
            strategy_name=strategy_name,
            stop_points=stop_points,
            target_points=target_points,
        )

    def run_historical_data_experiment(
        self,
        source: object,
        experiment_name: str = "Historical WDO Research",
        strategy_name: str = "alpha001_iorb",
        stop_points: float = 50.0,
        target_points: float = 100.0,
        symbol: str = "WDO",
        timeframe: str = "UNKNOWN",
    ) -> ResearchExperimentData:
        """Resolve origem historica via provider e executa experimento."""
        dataset = self.market_data_provider.load(
            source,
            symbol=symbol,
            timeframe=timeframe,
        )
        if dataset.is_empty:
            raise ValueError(self._market_data_error_message())
        return self.run_historical_experiment(
            candles=dataset.candles,
            experiment_name=experiment_name,
            strategy_name=strategy_name,
            stop_points=stop_points,
            target_points=target_points,
        )

    def run_real_data_research(
        self,
        symbol: str = "WDO",
        timeframe: str = "1m",
        period: str = "2025",
    ) -> RealDataResearchData:
        """Executa pesquisa quantitativa completa com dataset real catalogado."""
        dataset = self._load_real_dataset(symbol, timeframe, period)
        dataset_id = self._dataset_id(symbol, timeframe, period)
        campaign = ResearchCampaign(
            campaign_id=f"campaign-{dataset_id}",
            name=f"Real Data Research {dataset_id}",
            description="Campanha de pesquisa com dataset historico real.",
            alpha_id="Alpha001",
            objective="Validar Research Lab com dados historicos reais.",
            status="RUNNING",
            created_at="2026-06-28",
            created_by="TraderIA",
            metadata={"dataset_id": dataset_id},
        )
        experiment = self.run_historical_experiment(
            candles=dataset.candles,
            experiment_name=f"Real Data Research {dataset_id}",
            strategy_name="alpha001_iorb",
        )
        runner_result = self._run_real_data_runner(dataset.candles)
        benchmarks = self._run_real_data_benchmarks(dataset.candles)
        comparison = self.compare_benchmarks()
        validations = self.validate_all_benchmarks()
        return RealDataResearchData(
            dataset_id=dataset_id,
            campaign_id=campaign.campaign_id,
            experiment=experiment,
            research_runner_status=self._status_value(runner_result.status),
            validation_suite_status=self._validation_suite_status(validations),
            benchmark_comparison=comparison,
            portfolio_status=self._portfolio_status(comparison),
            total_validations=len(validations),
            total_benchmarks=len(benchmarks),
            total_candles=dataset.total_candles,
        )

    def list_experiments(self) -> list[ResearchExperimentData]:
        """Lista experimentos executados em memoria."""
        return [
            self._to_data(experiment)
            for experiment in self.research_lab.list_experiments()
        ]

    def list_live_experiment_signals(self) -> list[LiveExperimentSignalData]:
        """Lista sinais do experimento live em memoria."""
        return [
            self._to_live_experiment_signal_data(signal)
            for signal in self.live_experiment_runner.list_signals()
        ]

    def live_experiment_summary(self) -> LiveExperimentSummaryData:
        """Retorna estatisticas do experimento live em memoria."""
        return self._to_live_experiment_summary_data(
            self.live_experiment_runner.summary()
        )

    def last_experiment(self) -> ResearchExperimentData | None:
        """Retorna o ultimo experimento executado."""
        experiment = self.research_lab.last_experiment()
        if experiment is None:
            return None
        return self._to_data(experiment)

    def clear(self) -> None:
        """Limpa experimentos armazenados em memoria."""
        self.research_lab.clear()
        self.live_experiment_runner.clear()
        self.alpha001_ranking_results.clear()
        self.alpha001_raw_ranking_results.clear()

    def run_demo_benchmarks(self) -> list[BenchmarkData]:
        """Executa benchmarks demonstrativos em memoria."""
        candles = self._demo_benchmark_candles()
        for strategy in self._demo_strategies():
            self.research_lab.run_strategy_benchmark(strategy, candles)
        return self.list_benchmarks()

    def run_real_data_benchmarks(
        self,
        symbol: str = "WDO",
        timeframe: str = "1m",
        period: str = "2025",
    ) -> list[BenchmarkData]:
        """Executa benchmarks com dataset historico real catalogado."""
        dataset = self._load_real_dataset(symbol, timeframe, period)
        self._run_real_data_benchmarks(dataset.candles)
        return self.list_benchmarks()

    def compare_benchmarks(self) -> BenchmarkComparisonData:
        """Compara benchmarks armazenados no laboratorio."""
        comparison = self.research_lab.compare_benchmarks()
        return self._comparison_to_data(comparison)

    def last_comparison(self) -> BenchmarkComparisonData | None:
        """Retorna a ultima comparacao de benchmarks."""
        comparison = self.research_lab.last_comparison()
        if comparison is None:
            return None
        return self._comparison_to_data(comparison)

    def list_benchmarks(self) -> list[BenchmarkData]:
        """Lista benchmarks executados em memoria."""
        return [
            self._benchmark_to_data(benchmark)
            for benchmark in self.research_lab.list_benchmarks()
        ]

    def list_available_strategies(self) -> list[str]:
        """Lista estrategias disponiveis para pesquisa quantitativa."""
        return self.strategy_factory.list_available()

    def run_demo_parameter_grid(self) -> list[ParameterGridData]:
        """Executa grade demonstrativa de stop e alvo."""
        results = self.research_lab.run_parameter_grid(
            self.strategy_factory.create("score_contexto"),
            stop_values=[30.0, 50.0],
            target_values=[60.0, 100.0],
        )
        return [self._grid_to_data(result) for result in results]

    def list_parameter_grid_results(self) -> list[ParameterGridData]:
        """Lista resultados da grade de parametros."""
        return [
            self._grid_to_data(result)
            for result in self.research_lab.list_parameter_grid_results()
        ]

    def best_parameter_grid_result(self) -> ParameterGridData | None:
        """Retorna a melhor combinacao da grade por lucro liquido."""
        result = self.research_lab.best_parameter_grid_result()
        if result is None:
            return None
        return self._grid_to_data(result)

    def validate_all_benchmarks(self) -> list[ExperimentValidationData]:
        """Valida todos os benchmarks armazenados."""
        return [
            self._validation_to_data(validation)
            for validation in self.research_lab.validate_all_benchmarks()
        ]

    def list_validations(self) -> list[ExperimentValidationData]:
        """Lista validacoes estatisticas armazenadas."""
        return [
            self._validation_to_data(validation)
            for validation in self.research_lab.list_validations()
        ]

    def last_validation(self) -> ExperimentValidationData | None:
        """Retorna a ultima validacao estatistica."""
        validation = self.research_lab.last_validation()
        if validation is None:
            return None
        return self._validation_to_data(validation)

    def alpha001_research_report(self) -> Alpha001ResearchReportData:
        """Consolida metricas ja calculadas para a Alpha 001."""
        benchmark = self._latest_alpha001_benchmark()
        if benchmark is None:
            return self._empty_alpha001_report()
        return self._alpha001_report_from_benchmark(benchmark)

    def alpha001_dashboard_research_metrics(self) -> Alpha001DashboardResearchData:
        """Consolida resultados dos engines Alpha001 para o dashboard."""
        experiment = self.research_lab.last_experiment()
        if experiment is None or not isinstance(
            experiment.result,
            Alpha001ExperimentResult,
        ):
            return Alpha001DashboardResearchData()

        experiment_result = experiment.result
        research_result = self._alpha001_research_result_from_experiment(
            experiment_result,
        )
        return Alpha001DashboardResearchData(
            total_trades=research_result.metrics.total_trades,
            total_buy=research_result.metrics.total_buy,
            total_sell=research_result.metrics.total_sell,
            total_wait=research_result.metrics.total_wait,
            net_profit=research_result.profit.net_profit_points,
            gross_profit=research_result.profit.gross_profit_points,
            gross_loss=research_result.profit.gross_loss_points,
            max_drawdown=research_result.drawdown.max_drawdown_points,
            drawdown=research_result.drawdown.max_drawdown_points,
            win_rate=research_result.win_rate.win_rate,
            profit_factor=research_result.profit_factor.profit_factor,
            expectancy=research_result.expectancy.expectancy,
            recommendation=self._alpha001_research_recommendation(
                research_result,
            ),
            equity_curve=list(research_result.drawdown.equity_curve),
            benchmark=self._alpha001_dashboard_benchmark(),
        )

    def _alpha001_dashboard_benchmark(self) -> Alpha001DashboardBenchmarkData:
        experiments = [
            experiment for experiment in self.research_lab.list_experiments()
            if isinstance(experiment.result, Alpha001ExperimentResult)
        ]
        research_results = [
            self._alpha001_research_result_from_experiment(experiment.result)
            for experiment in experiments
        ]
        comparison = Alpha001BenchmarkComparator().compare(research_results)
        return Alpha001DashboardBenchmarkData(
            total_results=comparison.total_results,
            best_overall=self._alpha001_benchmark_label(
                comparison.best_overall,
                experiments,
                research_results,
            ),
            best_total_trades=self._alpha001_benchmark_label(
                comparison.best_total_trades,
                experiments,
                research_results,
            ),
            best_net_profit=self._alpha001_benchmark_label(
                comparison.best_net_profit,
                experiments,
                research_results,
            ),
            best_max_drawdown=self._alpha001_benchmark_label(
                comparison.best_max_drawdown,
                experiments,
                research_results,
            ),
            best_profit_factor=self._alpha001_benchmark_label(
                comparison.best_profit_factor,
                experiments,
                research_results,
            ),
            best_win_rate=self._alpha001_benchmark_label(
                comparison.best_win_rate,
                experiments,
                research_results,
            ),
            best_expectancy=self._alpha001_benchmark_label(
                comparison.best_expectancy,
                experiments,
                research_results,
            ),
            ranking=[
                self._alpha001_benchmark_label(result, experiments, research_results)
                or ""
                for result in comparison.ranking
            ],
        )

    def _alpha001_research_result_from_experiment(
        self,
        experiment_result: Alpha001ExperimentResult,
    ) -> Alpha001ResearchResult:
        return self.alpha001_research_service.run(experiment_result)

    def _alpha001_research_recommendation(
        self,
        research_result: Alpha001ResearchResult,
    ) -> str:
        validation = self.alpha001_research_validator.validate(research_result)
        recommendation = self.alpha001_research_advisor.recommend(validation)
        return recommendation.recommendation

    def _alpha001_benchmark_label(
        self,
        result: Alpha001ResearchResult | None,
        experiments: list[ResearchExperiment],
        research_results: list[Alpha001ResearchResult],
    ) -> str | None:
        if result is None:
            return None
        for index, candidate in enumerate(research_results):
            if candidate is result:
                return experiments[index].experiment_name
        return None

    def run_alpha001_parameter_ranking(
        self,
    ) -> list[Alpha001ParameterRankingData]:
        """Executa sweep demo e retorna ranking Alpha 001 ordenado."""
        sweep_results = self.alpha001_parameter_sweep.run(
            self._alpha001_demo_parameter_grid(),
        )
        ranking = self.alpha001_parameter_ranking.rank(sweep_results)
        self.alpha001_raw_ranking_results = list(ranking)
        self.alpha001_ranking_results = [
            self._alpha001_ranking_to_data(result)
            for result in ranking
        ]
        return self.list_alpha001_parameter_ranking()

    def list_alpha001_parameter_ranking(
        self,
    ) -> list[Alpha001ParameterRankingData]:
        """Lista ultimo ranking Alpha 001 gerado em memoria."""
        return list(self.alpha001_ranking_results)

    def get_alpha001_research_summary(self) -> Alpha001ResearchSummaryData:
        """Resume os resultados Alpha001 ja existentes."""
        summary = self.alpha001_research_summary.summarize(
            self.alpha001_raw_ranking_results,
        )
        return self._alpha001_summary_to_data(summary)

    def get_alpha001_robustness(self) -> Alpha001RobustnessData:
        """Analisa robustez dos resultados Alpha001 ja existentes."""
        result = self.alpha001_robustness_analyzer.analyze(
            self.alpha001_raw_ranking_results,
        )
        return self._alpha001_robustness_to_data(result)

    def research_report(self) -> ResearchReportData:
        """Gera relatorio consolidado do ultimo Alpha001Experiment."""
        experiment = self.research_lab.last_experiment()
        if experiment is None or not isinstance(
            experiment.result,
            Alpha001ExperimentResult,
        ):
            return self._empty_research_report()
        report = ResearchReport(
            parameters=self._experiment_parameters(experiment),
            experiment_result=experiment.result,
        ).generate()
        return self._research_report_to_data(report)

    def export_alpha001_results_to_csv(
        self,
        output_path: str | Path,
    ) -> Path:
        """Persiste CSV Alpha001 somente sob chamada explicita."""
        path = Path(output_path)
        rows = self.alpha001_result_exporter.to_csv_rows(
            self.alpha001_raw_ranking_results,
        )
        self._write_csv(path, rows)
        return path

    def _market_data_error_message(self) -> str:
        errors = getattr(self.market_data_provider, "errors", [])
        if errors:
            return "; ".join(errors)
        return "Dataset historico vazio."

    def _load_real_dataset(
        self,
        symbol: str,
        timeframe: str,
        period: str,
    ) -> object:
        load_dataset = getattr(self.market_data_provider, "load_dataset", None)
        if not callable(load_dataset):
            raise ValueError("Provider nao suporta dataset historico catalogado.")
        dataset = load_dataset(symbol, timeframe, period)
        if dataset.is_empty:
            raise ValueError(self._market_data_error_message())
        return dataset

    def _run_real_data_runner(
        self,
        candles: list[Candle],
    ) -> ResearchExecutionResult:
        return ResearchRunner(plan=ResearchExecutionPlan()).run(
            Alpha001Experiment(
                config=Alpha001Config(),
                candles=list(candles),
            )
        )

    def _run_real_data_benchmarks(
        self,
        candles: list[Candle],
    ) -> list[BenchmarkData]:
        for strategy in self._demo_strategies():
            self.research_lab.run_strategy_benchmark(strategy, list(candles))
        return self.list_benchmarks()

    def _validation_suite_status(
        self,
        validations: list[ExperimentValidationData],
    ) -> str:
        if not validations:
            return "NOT_EXECUTED"
        if all(validation.is_statistically_relevant for validation in validations):
            return "VALIDATED_WITH_REAL_DATA"
        return "INSUFFICIENT_REAL_DATA_SAMPLE"

    def _portfolio_status(
        self,
        comparison: BenchmarkComparisonData,
    ) -> str:
        if comparison.best_strategy is None:
            return "PORTFOLIO_NOT_EVALUATED"
        return "PORTFOLIO_EVALUATED_WITH_REAL_DATA"

    def _dataset_id(self, symbol: str, timeframe: str, period: str) -> str:
        return f"{symbol}_{timeframe}_{period}".lower()

    def _status_value(self, status: object) -> str:
        return str(getattr(status, "value", status))

    def _to_data(
        self,
        experiment: ResearchExperiment,
    ) -> ResearchExperimentData:
        metrics = self._metrics(experiment)
        return ResearchExperimentData(
            experiment_name=experiment.experiment_name,
            strategy_name=experiment.strategy_name,
            stop_points=experiment.stop_points,
            target_points=experiment.target_points,
            total_trades=metrics.total_trades,
            wins=metrics.wins,
            losses=metrics.losses,
            net_profit_points=float(metrics.net_profit_points),
            win_rate=float(metrics.win_rate),
            profit_factor=float(metrics.profit_factor),
            max_drawdown_points=float(metrics.max_drawdown_points),
        )

    def _metrics(self, experiment: ResearchExperiment) -> object:
        if experiment.result is None:
            return _EmptyMetrics()
        if isinstance(experiment.result, Alpha001ExperimentResult):
            return _Alpha001ExperimentMetrics.from_result(experiment.result)
        return experiment.result.paper_metrics

    def _to_live_experiment_signal_data(
        self,
        signal: LiveExperimentSignal,
    ) -> LiveExperimentSignalData:
        return LiveExperimentSignalData(
            timestamp=signal.timestamp,
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            strategy_name=signal.strategy_name,
            decision=signal.decision,
            confidence=signal.confidence,
            regime=signal.regime,
        )

    def _to_live_experiment_summary_data(
        self,
        summary: LiveExperimentSummary,
    ) -> LiveExperimentSummaryData:
        return LiveExperimentSummaryData(
            total_signals=summary.total_signals,
            buy_count=summary.buy_count,
            sell_count=summary.sell_count,
            wait_count=summary.wait_count,
            average_confidence=summary.average_confidence,
            confidence_std=summary.confidence_std,
            by_regime=dict(summary.by_regime),
            by_strategy=dict(summary.by_strategy),
        )

    def _benchmark_to_data(
        self,
        benchmark: StrategyBenchmarkResult,
    ) -> BenchmarkData:
        return BenchmarkData(
            strategy_name=benchmark.strategy_name,
            total_trades=benchmark.total_trades,
            wins=benchmark.wins,
            losses=benchmark.losses,
            net_profit_points=float(benchmark.net_profit_points),
            win_rate=float(benchmark.win_rate),
            profit_factor=float(benchmark.profit_factor),
            max_drawdown_points=float(benchmark.max_drawdown_points),
            equity_curve=list(benchmark.equity_curve),
        )

    def _comparison_to_data(
        self,
        comparison: BenchmarkComparison,
    ) -> BenchmarkComparisonData:
        return BenchmarkComparisonData(
            best_strategy=comparison.best_strategy,
            best_profit=float(comparison.best_profit),
            best_profit_factor=float(comparison.best_profit_factor),
            best_drawdown=float(comparison.best_drawdown),
            best_win_rate=float(comparison.best_win_rate),
            ranking=[
                self._benchmark_to_data(benchmark)
                for benchmark in comparison.ranking
            ],
        )

    def _grid_to_data(self, result: ParameterGridResult) -> ParameterGridData:
        benchmark = result.benchmark
        return ParameterGridData(
            stop_points=result.stop_points,
            target_points=result.target_points,
            strategy_name=benchmark.strategy_name,
            total_trades=benchmark.total_trades,
            wins=benchmark.wins,
            losses=benchmark.losses,
            net_profit_points=float(benchmark.net_profit_points),
            win_rate=float(benchmark.win_rate),
            profit_factor=float(benchmark.profit_factor),
            max_drawdown_points=float(benchmark.max_drawdown_points),
        )

    def _validation_to_data(
        self,
        validation: ExperimentValidation,
    ) -> ExperimentValidationData:
        return ExperimentValidationData(
            sample_size=validation.sample_size,
            is_statistically_relevant=validation.is_statistically_relevant,
            confidence_level=validation.confidence_level,
            warnings=list(validation.warnings),
            summary=validation.summary,
        )

    def _latest_alpha001_benchmark(self) -> StrategyBenchmarkResult | None:
        benchmarks = [
            benchmark
            for benchmark in self.research_lab.list_benchmarks()
            if benchmark.strategy_name == "alpha001_iorb"
        ]
        if not benchmarks:
            return None
        return benchmarks[-1]

    def _empty_alpha001_report(self) -> Alpha001ResearchReportData:
        return Alpha001ResearchReportData(
            strategy_name="alpha001_iorb",
            validation_status="VALIDATION_PENDING",
            total_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            max_drawdown_points=0.0,
            net_profit_points=0.0,
            real_trading_authorized=False,
            summary="Aguardando amostra suficiente no Research Lab.",
        )

    def _alpha001_report_from_benchmark(
        self,
        benchmark: StrategyBenchmarkResult,
    ) -> Alpha001ResearchReportData:
        status = self._alpha001_validation_status(benchmark)
        return Alpha001ResearchReportData(
            strategy_name=benchmark.strategy_name,
            validation_status=status,
            total_trades=benchmark.total_trades,
            win_rate=float(benchmark.win_rate),
            profit_factor=float(benchmark.profit_factor),
            max_drawdown_points=float(benchmark.max_drawdown_points),
            net_profit_points=float(benchmark.net_profit_points),
            real_trading_authorized=False,
            summary=self._alpha001_report_summary(status),
        )

    def _alpha001_validation_status(
        self,
        benchmark: StrategyBenchmarkResult,
    ) -> str:
        if benchmark.total_trades < 30:
            return "VALIDATION_PENDING"
        if self._alpha001_metrics_are_bad(benchmark):
            return "VALIDATION_REJECTED"
        return "VALIDATION_ACCEPTABLE"

    def _alpha001_metrics_are_bad(
        self,
        benchmark: StrategyBenchmarkResult,
    ) -> bool:
        return (
            benchmark.net_profit_points <= 0
            or benchmark.profit_factor < 1.0
            or benchmark.win_rate <= 0.0
        )

    def _alpha001_report_summary(self, status: str) -> str:
        summaries = {
            "VALIDATION_PENDING": "Amostra insuficiente para conclusao.",
            "VALIDATION_REJECTED": "Metricas iniciais rejeitam a hipotese.",
            "VALIDATION_ACCEPTABLE": "Metricas iniciais aceitaveis para pesquisa.",
        }
        return summaries[status]

    def _alpha001_demo_parameter_grid(self) -> list[Alpha001ParameterSet]:
        return [
            Alpha001ParameterSet(5, 20.0, 1000),
            Alpha001ParameterSet(10, 25.0, 1200),
            Alpha001ParameterSet(15, 30.0, 1500),
            Alpha001ParameterSet(20, 35.0, 1800),
        ]

    def _alpha001_ranking_to_data(
        self,
        result: Alpha001ParameterSweepResult,
    ) -> Alpha001ParameterRankingData:
        return Alpha001ParameterRankingData(
            opening_range_minutes=result.parameters.opening_range_minutes,
            minimum_range_size=result.parameters.minimum_range_size,
            minimum_volume=result.parameters.minimum_volume,
            total_trades=result.total_trades,
            win_rate=float(result.win_rate),
            profit_factor=float(result.profit_factor),
            max_drawdown_points=float(result.max_drawdown_points),
            net_profit_points=float(result.net_profit_points),
            validation_status=result.validation_status,
        )

    def _alpha001_summary_to_data(
        self,
        summary: Alpha001ResearchSummaryResult,
    ) -> Alpha001ResearchSummaryData:
        return Alpha001ResearchSummaryData(
            total_experiments=summary.total_experiments,
            total_approved=summary.total_approved,
            total_rejected=summary.total_rejected,
            best_profit_factor=float(summary.best_profit_factor),
            lowest_max_drawdown_points=float(
                summary.lowest_max_drawdown_points,
            ),
            best_net_profit_points=float(summary.best_net_profit_points),
            best_configuration=self._summary_configuration_to_data(summary),
            approval_rate=float(summary.approval_rate),
        )

    def _summary_configuration_to_data(
        self,
        summary: Alpha001ResearchSummaryResult,
    ) -> Alpha001ParameterRankingData | None:
        if summary.best_configuration is None:
            return None
        matches = [
            result for result in self.alpha001_ranking_results
            if self._same_parameter_set(result, summary.best_configuration)
        ]
        if not matches:
            return None
        return matches[0]

    def _same_parameter_set(
        self,
        result: Alpha001ParameterRankingData,
        parameter_set: object,
    ) -> bool:
        return (
            result.opening_range_minutes == parameter_set.opening_range_minutes
            and result.minimum_range_size == parameter_set.minimum_range_size
            and result.minimum_volume == parameter_set.minimum_volume
        )

    def _alpha001_robustness_to_data(
        self,
        result: Alpha001RobustnessResult,
    ) -> Alpha001RobustnessData:
        return Alpha001RobustnessData(
            robustness_score=float(result.robustness_score),
            status=result.status,
            reasons=list(result.reasons),
        )

    def _experiment_parameters(
        self,
        experiment: ResearchExperiment,
    ) -> Alpha001Config:
        return Alpha001Config(
            initial_stop_points=experiment.stop_points,
            initial_target_points=experiment.target_points,
        )

    def _research_report_to_data(
        self,
        report: ResearchReportResult,
    ) -> ResearchReportData:
        return ResearchReportData(
            parameters=dict(report.parameters),
            metrics=dict(report.metrics),
            statistical_summary=report.statistical_summary,
            conclusion=report.conclusion,
            conclusion_reasons=list(report.conclusion_reasons),
        )

    def _empty_research_report(self) -> ResearchReportData:
        return ResearchReportData(
            parameters={},
            metrics={},
            statistical_summary="Nenhum Alpha001Experiment executado.",
            conclusion="INCONCLUSIVE",
            conclusion_reasons=["sem experimento Alpha001 disponivel"],
        )

    def _write_csv(self, path: Path, rows: list[list[object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(rows)

    def _demo_candles(self) -> list[Candle]:
        return [
            Candle("2026-06-26 09:00", 1000.0, 1010.0, 995.0, 1008.0, 1000),
            Candle("2026-06-26 09:01", 1008.0, 1020.0, 1005.0, 1018.0, 1000),
            Candle("2026-06-26 09:02", 1018.0, 1030.0, 1010.0, 1028.0, 1000),
        ]

    def _demo_benchmark_candles(self) -> list[Candle]:
        return [
            Candle("2026-06-26 09:00", 1000.0, 1005.0, 995.0, 1000.0, 1000),
            Candle("2026-06-26 09:01", 1000.0, 1100.0, 999.0, 1100.0, 1000),
            Candle("2026-06-26 09:02", 1100.0, 1110.0, 1040.0, 1050.0, 1200),
        ]

    def _demo_strategies(self) -> list[object]:
        return [
            self.strategy_factory.create("alpha001_iorb"),
            self.strategy_factory.create("breakout"),
            self.strategy_factory.create("pullback"),
            self.strategy_factory.create("score_contexto"),
        ]


@dataclass(frozen=True)
class _EmptyMetrics:
    """Metricas vazias para experimentos ainda nao executados."""

    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    net_profit_points: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_points: float = 0.0


@dataclass(frozen=True)
class _Alpha001ExperimentMetrics:
    """Adapta Alpha001ExperimentResult para DTOs de application."""

    total_trades: int
    wins: int
    losses: int
    net_profit_points: float
    win_rate: float
    profit_factor: float
    max_drawdown_points: float

    @classmethod
    def from_result(
        cls,
        result: Alpha001ExperimentResult,
    ) -> "_Alpha001ExperimentMetrics":
        return cls(
            total_trades=result.total_signals,
            wins=0,
            losses=0,
            net_profit_points=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            max_drawdown_points=0.0,
        )
