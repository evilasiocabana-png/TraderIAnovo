"""Servico de aplicacao para dados do dashboard."""

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta, timezone
import importlib
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
from typing import Any
import warnings

from application.configuration_service import (
    ConfigurationData,
    ConfigurationService,
)
from application.data_readiness_gate_log import (
    DataReadinessGateLog,
    DataReadinessGateLogger,
    InMemoryDataReadinessGateLogger,
)
from application.demo_execution_service import (
    DemoExecutionAuditRecord,
    DemoExecutionPolicy,
    DemoExecutionService,
)
from application.dashboard_view_model import (
    DASHBOARD_VIEW_MODEL_CONTRACT_VERSION,
    DashboardLiveHistoryViewModel,
    DashboardLiveResearchStatusViewModel,
    DashboardLiveSessionSummaryViewModel,
    DashboardLiveSignalQualityViewModel,
    DashboardMT5CandleViewModel,
    DashboardMT5ConnectionDiagnosticViewModel,
    DashboardMT5DiagnosticStepViewModel,
    DashboardMT5HeuristicResearchRowViewModel,
    DashboardMT5HeuristicResearchViewModel,
    DashboardMT5ScenarioViewModel,
    DashboardMT5SetupSuggestionViewModel,
    DashboardMT5AlphaResearchReportViewModel,
    DashboardMT5ForexSignalRowViewModel,
    DashboardMT5ForexSignalViewModel,
    DashboardMT5MarketDataViewModel,
    DashboardMT5TradeAuditRowViewModel,
    DashboardMT5TradeAuditViewModel,
    DashboardDemoRobotAuditViewModel,
    DashboardDemoRobotRejectionStepViewModel,
    DashboardDemoRobotViewModel,
    DashboardReplayStatusViewModel,
    DashboardResearchStatusViewModel,
    DashboardSafetyStatusViewModel,
    DashboardSystemStatusViewModel,
    DashboardTimeframeCandidateViewModel,
    DashboardTimeframeOptimizationViewModel,
    DashboardViewModel,
    format_dashboard_timestamp,
)
from application.live_research_service import (
    LiveResearchData,
    LiveResearchService,
    LiveResearchSignalQuality,
    LiveResearchSessionSummary,
    LiveResearchSnapshotRecord,
)
from application.market_service import MarketService
from application.mt5_market_data_service import (
    MT5ConnectionDiagnostic,
    MT5DashboardMarketData,
    MT5ForexSignalDashboard,
    MT5ForexSignalRow,
    MT5MarketDataService,
)
from application.dynamic_exit_market_state_service import (
    DynamicExitMarketStateClassifier,
)
from application.dynamic_exit_recommendation_service import (
    DynamicExitRecommendationEngine,
)
from application.mt5_visual_signal_exporter import (
    MT5VisualSignalExportResult,
    MT5VisualSignalExporter,
)
from application.mt5_demo_robot_service import (
    MT5DemoRobotService,
    MT5DemoRobotSignal,
    MT5DemoTradePlan,
)
from application.paper_trading_service import PaperTradingReport
from application.paper_trading_service import PaperTradingService
from application.regime_service import RegimeData, RegimeService
from domain.candle import Candle


MT5_LAB_TARGET_CONFIDENCE = 0.70
_DYNAMIC_EXIT_MARKET_STATE_CLASSIFIER = DynamicExitMarketStateClassifier()
_DYNAMIC_EXIT_RECOMMENDATION_ENGINE = DynamicExitRecommendationEngine()
from application.replay_service import ReplayData, ReplayService
from application.research_lab_service import (
    Alpha001DashboardResearchData,
    Alpha001ParameterRankingData,
    Alpha001ResearchReportData,
    Alpha001ResearchSummaryData,
    Alpha001RobustnessData,
    BenchmarkComparisonData,
    BenchmarkData,
    ExperimentValidationData,
    LiveExperimentSignalData,
    LiveExperimentSummaryData,
    ParameterGridData,
    ResearchExperimentData,
    ResearchLabService,
    ResearchReportData,
)
from application.research_service import ResearchData, ResearchService
from application.session_service import (
    SessionService,
    SessionSnapshot,
    empty_session_snapshot,
)
from application.system_service import SystemService, SystemStatus
from core.mt5_process_probe import probe_mt5_initialize
from core.operation_session import OperationSession
from domain.contracts.decision_context import DecisionContext
from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from infrastructure.mt5_visual_signal_path_resolver import (
    MT5VisualSignalPathResolver,
)
from research.mt5_research_trade_plan import (
    MT5ResearchTradePlan,
    MT5ResearchTradePlanEngine,
    MT5ResearchTradePlanInput,
)
from research.traderia_certification_index import (
    TraderIACertificationEngine,
    TraderIACertificationResult,
)
from research.forex_time_layer import ForexTimeLayer
from research.research_layer import OFFICIAL_RESEARCH_LAYERS
from market.feature_engine import FeatureSnapshot
from market.market_memory import MarketMemory
from market.regime_engine import MarketRegime, RegimeAnalysis
from market_data import (
    HistoricalDataProvider,
    HistoricalDataset,
    HistoricalDatasetCatalog,
    HistoricalDatasetMetadata,
    HistoricalDatasetQualityRepository,
    HistoricalDatasetQualityStatus,
    HistoricalDatasetQualityValidationRecord,
    MarketDataProvider,
    create_default_historical_dataset_quality_repository,
)
from paper.paper_trading_engine import PaperTradingEngine
from paper.paper_trading_engine import PaperTradingResult
from research.research_seed import build_demo_market_memory
from research.timeframe_optimizer import TimeframeOptimizationResult


_MT5_IMPORT_LOCK = threading.Lock()
_MT5_MODULE: Any | None = None


def _import_mt5_module() -> Any:
    """Importa MetaTrader5 uma vez, evitando falhas concorrentes no Streamlit."""
    global _MT5_MODULE
    with _MT5_IMPORT_LOCK:
        sys.modules.setdefault("sys", sys)
        sys.modules.setdefault("warnings", warnings)
        if _MT5_MODULE is None:
            _MT5_MODULE = importlib.import_module("MetaTrader5")
        return _MT5_MODULE


def _probe_mt5_before_inline_initialize() -> tuple[bool, str]:
    timeout_seconds = float(os.getenv("TRADERIA_MT5_PROBE_TIMEOUT_SECONDS", "3"))
    result = probe_mt5_initialize(timeout_seconds)
    return result.ok, result.message


@dataclass(frozen=True)
class ActiveDatasetDashboardData:
    """DTO de observabilidade do dataset historico ativo."""

    asset: str
    timeframe: str
    source: str
    provider: str
    dataset_id: str
    status: str
    period: str
    candles: int | None
    last_update: str
    checksum: str
    metadata_version: str
    dataset_certification: str
    replay_status: str
    research_status: str
    architecture_status: str
    selected: bool = False


@dataclass(frozen=True)
class DatasetProfilePoint:
    """Ponto pronto para graficos do perfil do dataset."""

    label: str
    value: float


@dataclass(frozen=True)
class DatasetProfileData:
    """Perfil quantitativo pronto para exibicao no dashboard."""

    asset: str
    timeframe: str
    period: str
    candles: int
    initial_price: float
    final_price: float
    accumulated_return: float
    annualized_return: float
    annualized_volatility: float
    max_drawdown: float
    best_day: str
    best_day_return: float
    worst_day: str
    worst_day_return: float
    positive_days: int
    negative_days: int
    average_volume: float
    max_volume: int
    quality_status: str
    price_curve: list[DatasetProfilePoint] = field(default_factory=list)
    accumulated_return_curve: list[DatasetProfilePoint] = field(
        default_factory=list
    )
    daily_return_histogram: list[DatasetProfilePoint] = field(
        default_factory=list
    )
    volume_curve: list[DatasetProfilePoint] = field(default_factory=list)


@dataclass(frozen=True)
class MT5ScenarioHistoricalEvidence:
    """Evidencia historica propria de um cenario pesquisado."""

    sample_size: int = 0
    win_rate: float = 0.0
    avg_return: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    source: str = "SCENARIO_HISTORICAL_EVIDENCE"


@dataclass(frozen=True)
class LiveResearchDashboardData:
    """Estado live read-only pronto para exibicao no dashboard."""

    symbol: str = "N/D"
    timeframe: str = "N/D"
    candles_ingested: int = 0
    strategies_evaluated: int = 0
    strategy_signals: int = 0
    decision_contexts: int = 0
    last_decision: str = "N/D"
    last_confidence: float = 0.0
    safety_status: str = "READ ONLY"
    has_data: bool = False
    history: list["LiveResearchHistoryRow"] = field(default_factory=list)
    session_summary: "LiveResearchSessionSummaryData" = field(
        default_factory=lambda: LiveResearchSessionSummaryData()
    )
    signal_quality: list["LiveResearchSignalQualityRow"] = field(
        default_factory=list
    )


@dataclass(frozen=True)
class LiveResearchHistoryRow:
    """Linha de historico live read-only pronta para exibicao."""

    timestamp: str
    symbol: str
    timeframe: str
    decision: str
    confidence: float
    strategy_signals: int
    decision_contexts: int


@dataclass(frozen=True)
class LiveResearchSessionSummaryData:
    """Resumo estatistico live read-only pronto para exibicao."""

    total_snapshots: int = 0
    buy_count: int = 0
    sell_count: int = 0
    wait_count: int = 0
    average_confidence: float = 0.0
    highest_confidence: float = 0.0
    lowest_confidence: float = 0.0
    last_decision: str = "N/D"
    last_timestamp: str = "N/D"


@dataclass(frozen=True)
class LiveResearchSignalQualityRow:
    """Linha de qualidade de sinal live por estrategia."""

    strategy_name: str
    signal_count: int
    buy_count: int
    sell_count: int
    wait_count: int
    average_confidence: float
    last_decision: str


@dataclass(frozen=True)
class DashboardData:
    """Dados prontos para renderizacao no dashboard."""

    system_status: SystemStatus
    market_snapshot: MarketSnapshot | None
    strategy_signal: StrategySignal | None
    session_snapshot: SessionSnapshot = empty_session_snapshot()
    configuration_data: ConfigurationData | None = None
    regime_data: RegimeData | None = None
    research_data: ResearchData | None = None
    replay_data: ReplayData | None = None
    research_lab_experiments: list[ResearchExperimentData] = field(
        default_factory=list
    )
    last_research_experiment: ResearchExperimentData | None = None
    research_benchmarks: list[BenchmarkData] = field(default_factory=list)
    benchmark_comparison: BenchmarkComparisonData | None = None
    parameter_grid_results: list[ParameterGridData] = field(
        default_factory=list
    )
    best_parameter_grid_result: ParameterGridData | None = None
    benchmark_validations: list[ExperimentValidationData] = field(
        default_factory=list
    )
    last_benchmark_validation: ExperimentValidationData | None = None
    available_research_strategies: list[str] = field(default_factory=list)
    alpha001_status: "Alpha001StatusData" = field(
        default_factory=lambda: Alpha001StatusData()
    )
    alpha001_research_report: Alpha001ResearchReportData | None = None
    alpha001_dashboard_research: Alpha001DashboardResearchData = field(
        default_factory=Alpha001DashboardResearchData
    )
    alpha001_parameter_ranking: list[Alpha001ParameterRankingData] = field(
        default_factory=list
    )
    alpha001_research_summary: Alpha001ResearchSummaryData | None = None
    alpha001_robustness: Alpha001RobustnessData | None = None
    research_report: ResearchReportData | None = None
    live_experiment_signals: list[LiveExperimentSignalData] = field(
        default_factory=list
    )
    live_experiment_summary: LiveExperimentSummaryData = field(
        default_factory=LiveExperimentSummaryData
    )
    alpha001_paper_status: "Alpha001PaperStatusData" = field(
        default_factory=lambda: Alpha001PaperStatusData()
    )
    alpha001_paper_report: "Alpha001PaperReportData" = field(
        default_factory=lambda: Alpha001PaperReportData()
    )
    active_dataset: ActiveDatasetDashboardData | None = None
    available_datasets: list[ActiveDatasetDashboardData] = field(
        default_factory=list
    )
    dataset_profile: DatasetProfileData | None = None
    live_research_data: LiveResearchDashboardData = field(
        default_factory=LiveResearchDashboardData
    )
    mt5_market_data: MT5DashboardMarketData = field(
        default_factory=MT5DashboardMarketData
    )
    mt5_forex_signals: MT5ForexSignalDashboard = field(
        default_factory=MT5ForexSignalDashboard
    )
    timeframe_optimizer: list[TimeframeOptimizationResult] = field(
        default_factory=list
    )


@dataclass(frozen=True)
class Alpha001StatusData:
    """Status operacional e arquitetural da Alpha 001."""

    strategy_name: str = "Alpha 001 - IORB"
    status: str = "pesquisa/simulação"
    real_trading_authorized: bool = False
    broker_mt5_integrated: bool = False
    ai_authorized: bool = False
    research_lab_integrated: bool = True
    benchmark_integrated: bool = True
    statistical_validation_status: str = (
        "validação estatística ainda depende do Research Lab"
    )


@dataclass(frozen=True)
class Alpha001PaperPositionData:
    """DTO de posicao paper atual da Alpha001."""

    side: str
    quantity: int
    entry_price: float
    stop: float
    target: float
    status: str
    exit_price: float | None
    result_points: float
    close_reason: str | None


@dataclass(frozen=True)
class Alpha001PaperTradeData:
    """DTO de trade paper fechado da Alpha001."""

    side: str
    quantity: int
    entry_price: float
    exit_price: float
    result_points: float
    close_reason: str


@dataclass(frozen=True)
class Alpha001PaperStatusData:
    """Estado paper da Alpha001 pronto para o dashboard."""

    status: str = "PAPER ONLY"
    position: Alpha001PaperPositionData | None = None
    trades_history: list[Alpha001PaperTradeData] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=lambda: [0.0])
    accumulated_result_points: float = 0.0
    total_trades: int = 0
    real_trading_authorized: bool = False
    broker_integrated: bool = False
    mt5_integrated: bool = False


@dataclass(frozen=True)
class Alpha001PaperReportData:
    """Relatorio operacional paper Alpha001 para dashboard."""

    status: str = "PAPER ONLY"
    total_operations: int = 0
    paper_win_rate: float = 0.0
    accumulated_result_points: float = 0.0
    max_drawdown_points: float = 0.0
    max_loss_sequence: int = 0
    current_position: Alpha001PaperPositionData | None = None


@dataclass(frozen=True)
class HistoricalDatasetQualityReport:
    """Relatorio de qualidade de dataset historico."""

    dataset_id: str
    total_candles: int
    start_datetime: str | None
    end_datetime: str | None
    invalid_ohlc_candles: int = 0
    invalid_volume_candles: int = 0
    temporal_gaps: int = 0
    duplicate_timestamps: int = 0


@dataclass(frozen=True)
class HistoricalDatasetHealthSummary:
    """Resumo consolidado de saude dos datasets historicos."""

    total_datasets: int
    total_validated: int
    total_approved: int
    total_rejected: int
    total_unvalidated: int
    last_validation_at: str | None = None


@dataclass(frozen=True)
class HistoricalDatasetReadiness:
    """Classificacao de prontidao de um dataset historico."""

    dataset_id: str
    readiness: str
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DataReadinessGateMetrics:
    """Metricas agregadas da auditoria do Data Readiness Gate."""

    total_evaluations: int = 0
    total_allowed: int = 0
    total_blocked: int = 0
    total_replay_evaluations: int = 0
    total_research_evaluations: int = 0
    last_blocked_dataset_id: str | None = None
    last_block_reason: str | None = None
    last_evaluation_at: str | None = None


@dataclass(frozen=True)
class HistoricalProviderMetrics:
    """Metricas agregadas de datasets historicos por provider."""

    provider: str
    total_datasets: int = 0
    total_validated: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    total_unvalidated: int = 0
    total_gate_evaluations: int = 0
    total_allowed: int = 0
    total_blocked: int = 0
    last_validation_at: str | None = None
    last_gate_evaluation_at: str | None = None


@dataclass(frozen=True)
class DashboardService:
    """Fachada unica consumida pelo dashboard visual."""

    market_service: MarketService = MarketService()
    system_service: SystemService = SystemService()
    configuration_service: ConfigurationService = ConfigurationService()
    regime_service: RegimeService = RegimeService()
    research_service: ResearchService = ResearchService()
    research_lab_service: ResearchLabService = field(
        default_factory=ResearchLabService
    )
    live_research_service: LiveResearchService = field(
        default_factory=LiveResearchService
    )
    mt5_market_data_service: MT5MarketDataService = field(
        default_factory=MT5MarketDataService
    )
    replay_service: ReplayService = field(default_factory=ReplayService)
    historical_dataset_catalog: HistoricalDatasetCatalog = field(
        default_factory=HistoricalDatasetCatalog
    )
    historical_data_provider: MarketDataProvider = field(
        default_factory=HistoricalDataProvider
    )
    historical_dataset_quality_repository: HistoricalDatasetQualityRepository = field(
        default_factory=create_default_historical_dataset_quality_repository
    )
    data_readiness_gate_logger: DataReadinessGateLogger = field(
        default_factory=InMemoryDataReadinessGateLogger
    )
    paper_trading_engine: PaperTradingEngine = field(
        default_factory=PaperTradingEngine
    )
    paper_trading_service: PaperTradingService = field(
        default_factory=PaperTradingService
    )
    demo_execution_service: DemoExecutionService = field(
        default_factory=DemoExecutionService
    )
    demo_robot_execution_service: DemoExecutionService = field(
        default_factory=DemoExecutionService
    )
    mt5_demo_robot_service: MT5DemoRobotService = field(
        default_factory=MT5DemoRobotService
    )
    mt5_research_trade_plan_engine: MT5ResearchTradePlanEngine = field(
        default_factory=MT5ResearchTradePlanEngine
    )
    traderia_certification_engine: TraderIACertificationEngine = field(
        default_factory=TraderIACertificationEngine
    )
    forex_time_layer: ForexTimeLayer = field(default_factory=ForexTimeLayer)
    mt5_visual_signal_exporter: MT5VisualSignalExporter = field(
        default_factory=MT5VisualSignalExporter
    )
    mt5_visual_signal_path_resolver: MT5VisualSignalPathResolver = field(
        default_factory=MT5VisualSignalPathResolver
    )
    mt5_research_constants: DashboardMT5HeuristicResearchViewModel = field(
        default_factory=lambda: DashboardMT5HeuristicResearchViewModel(
            status="SEM_CALIBRACAO",
            timeframe="M1",
            source="MT5_RESEARCH_SNAPSHOT",
            message=(
                "Nenhuma calibracao MT5 executada. Clique em Atualizar "
                "historico de pesquisa (5000 candles) no Laboratorio de "
                "Pesquisa para atualizar o snapshot historico."
            ),
        )
    )
    mt5_research_snapshot_cache: DashboardMT5HeuristicResearchViewModel | None = None
    last_demo_robot_status: DashboardDemoRobotViewModel = field(
        default_factory=DashboardDemoRobotViewModel
    )
    mt5_trade_history_cache: dict[int, dict[str, Any]] = field(default_factory=dict)
    mt5_trade_open_ticket_cache: set[int] = field(default_factory=set)
    mt5_trade_history_cache_status: str = "SEM_CACHE"
    mt5_trade_history_cache_message: str = "Historico MT5 ainda nao carregado."
    session_service: SessionService = SessionService(
        OperationSession("N/D", "09:00", "18:00")
    )
    feature_snapshot: FeatureSnapshot | None = None
    regime_analysis: RegimeAnalysis | None = None
    market_memory: MarketMemory | None = None
    selected_historical_dataset_id: str | None = None

    def __post_init__(self) -> None:
        self.research_lab_service.live_experiment_runner = (
            self.live_research_service.live_experiment_runner
        )
        self.live_research_service.mt5_market_data_service = (
            self.mt5_market_data_service
        )
        if self._should_preload_mt5_research_snapshot():
            stored_research = self._load_mt5_research_snapshot()
            if stored_research is not None:
                object.__setattr__(self, "mt5_research_constants", stored_research)
                object.__setattr__(
                    self,
                    "mt5_research_snapshot_cache",
                    stored_research,
                )

    def get_dashboard_data(self) -> DashboardData:
        """Retorna dados legados do dashboard para compatibilidade temporaria."""
        snapshot = self.market_service.get_latest_market_dna()
        signal = self._to_signal(snapshot)
        configuration = self.configuration_service.get_configuration_data()
        return DashboardData(
            system_status=self.system_service.get_status(),
            market_snapshot=snapshot,
            strategy_signal=signal,
            session_snapshot=self.session_service.get_session_snapshot(),
            configuration_data=configuration,
            regime_data=self._to_regime(snapshot),
            research_data=self._to_research(snapshot),
            replay_data=self.replay_service.get_replay_data(),
            active_dataset=self._get_active_dataset_dashboard_data(),
            available_datasets=self._list_dataset_dashboard_data(),
            dataset_profile=self._get_dataset_profile_data(),
            live_research_data=self.get_live_research_data(),
            mt5_market_data=self.get_mt5_market_data(),
            mt5_forex_signals=self.get_mt5_forex_signals(),
            timeframe_optimizer=self.get_timeframe_optimization_results(),
            live_experiment_signals=self.list_live_experiment_signals(),
            live_experiment_summary=self.get_live_experiment_summary(),
            **self._research_lab_dashboard_fields(),
        )

    def get_dashboard_contract_version(self) -> str:
        """Retorna a versao do contrato DashboardService-DashboardViewModel."""
        return DASHBOARD_VIEW_MODEL_CONTRACT_VERSION

    def get_dashboard_view_model(self) -> DashboardViewModel:
        """Retorna contrato unico e estavel para a UI do dashboard."""
        data = self.get_dashboard_data()
        mt5_heuristic_research = self.get_mt5_research_constants()
        return DashboardViewModel(
            contract_version=self.get_dashboard_contract_version(),
            system_status=self._to_view_model_system_status(data),
            replay_status=self._to_view_model_replay_status(data),
            live_research_status=self._to_view_model_live_status(data),
            live_session_summary=self._to_view_model_live_summary(data),
            live_signal_quality=self._to_view_model_signal_quality(data),
            live_history=self._to_view_model_live_history(data),
            research_status=self._to_view_model_research_status(data),
            safety_status=self._to_view_model_safety_status(data),
            mt5_market_data=self._to_view_model_mt5_market_data(data),
            mt5_forex_signals=self._to_view_model_mt5_forex_signals(
                data,
                mt5_heuristic_research,
            ),
            timeframe_optimizer=self._to_view_model_timeframe_optimizer(data),
            mt5_heuristic_research=mt5_heuristic_research,
            demo_robot=self.get_demo_robot_status(),
            mt5_trade_audit=self.get_mt5_trade_audit_report(),
            compatibility_data=data,
        )

    def get_light_dashboard_view_model(self) -> DashboardViewModel:
        """Retorna contrato leve para a abertura do dashboard."""
        snapshot = self.market_service.get_latest_market_dna()
        mt5_heuristic_research = self.get_mt5_research_constants()
        data = DashboardData(
            system_status=self.system_service.get_status(),
            market_snapshot=snapshot,
            strategy_signal=self._to_signal(snapshot),
            session_snapshot=self.session_service.get_session_snapshot(),
            configuration_data=self.configuration_service.get_configuration_data(),
            regime_data=self._to_regime(snapshot),
            research_data=self._to_research(snapshot),
            replay_data=self.replay_service.get_replay_data(),
            active_dataset=self._get_active_dataset_dashboard_data(),
            available_datasets=self._list_dataset_dashboard_data(),
            dataset_profile=self._get_dataset_profile_data(),
            live_research_data=self.get_live_research_data(),
            mt5_market_data=self.get_mt5_market_data(),
            mt5_forex_signals=self.mt5_market_data_service.latest_forex_signal_dashboard,
            timeframe_optimizer=self.get_timeframe_optimization_results(),
            live_experiment_signals=self.list_live_experiment_signals(),
            live_experiment_summary=self.get_live_experiment_summary(),
            **self._research_lab_dashboard_fields(),
        )
        return DashboardViewModel(
            contract_version=self.get_dashboard_contract_version(),
            system_status=self._to_view_model_system_status(data),
            replay_status=self._to_view_model_replay_status(data),
            live_research_status=self._to_view_model_live_status(data),
            live_session_summary=self._to_view_model_live_summary(data),
            live_signal_quality=self._to_view_model_signal_quality(data),
            live_history=self._to_view_model_live_history(data),
            research_status=self._to_view_model_research_status(data),
            safety_status=self._to_view_model_safety_status(data),
            mt5_market_data=self._to_view_model_mt5_market_data(data),
            mt5_forex_signals=self._to_view_model_mt5_forex_signals(
                data,
                mt5_heuristic_research,
            ),
            timeframe_optimizer=self._to_view_model_timeframe_optimizer(data),
            mt5_heuristic_research=mt5_heuristic_research,
            demo_robot=self.get_demo_robot_status(),
            compatibility_data=data,
        )

    def get_mt5_market_data(self) -> MT5DashboardMarketData:
        """Retorna estado MT5 read-only pela fachada do dashboard."""
        return self.mt5_market_data_service.get_dashboard_market_data()

    def load_mt5_market_data(
        self,
        symbol: str = "EURUSD",
        timeframe: str = "M1",
        count: int | None = None,
    ) -> MT5DashboardMarketData:
        """Carrega candles MT5 em modo somente leitura pela fachada."""
        return self.mt5_market_data_service.load_dashboard_market_data(
            symbol=symbol,
            timeframe=timeframe,
            count=count,
        )

    def get_mt5_forex_signals(self) -> MT5ForexSignalDashboard:
        """Retorna o painel Forex MT5 pela fachada do dashboard."""
        return self.mt5_market_data_service.get_forex_signal_dashboard()

    def load_mt5_forex_signals(
        self,
        timeframe: str = "M1",
    ) -> MT5ForexSignalDashboard:
        """Atualiza leitura Forex MT5 em modo leve e somente analise."""
        timeframes_by_pair = self._mt5_lab_timeframes_by_pair()
        if timeframes_by_pair and hasattr(
            self.mt5_market_data_service,
            "load_forex_signal_dashboard_for_timeframes",
        ):
            data = self.mt5_market_data_service.load_forex_signal_dashboard_for_timeframes(
                timeframes_by_pair,
                fallback_timeframe=timeframe,
            )
        else:
            data = self.mt5_market_data_service.load_forex_signal_dashboard(
                timeframe=timeframe,
            )
        self._auto_export_mt5_visual_signals()
        return data

    def _mt5_lab_timeframes_by_pair(self) -> dict[str, str]:
        research = self.get_mt5_research_constants()
        timeframes: dict[str, str] = {}
        for row in list(getattr(research, "rows", []) or []):
            pair = str(getattr(row, "pair", "") or "").upper()
            timeframe = self._research_row_winner_timeframe(row)
            if pair and timeframe:
                timeframes[pair] = timeframe
        return timeframes

    def get_mt5_research_constants(self) -> DashboardMT5HeuristicResearchViewModel:
        """Retorna a ultima calibracao MT5 aprovada pelo Research Lab."""
        if list(getattr(self.mt5_research_constants, "rows", []) or []):
            return self.mt5_research_constants
        current_status = str(getattr(self.mt5_research_constants, "status", ""))
        if current_status not in {"SEM_DADOS", "SEM_CALIBRACAO"}:
            return self.mt5_research_constants
        stored_research = self._mt5_research_rows_snapshot()
        if stored_research is not None:
            return stored_research
        return self.mt5_research_constants

    def get_mt5_research_report_snapshot(self) -> DashboardMT5HeuristicResearchViewModel:
        """Retorna o snapshot completo quando a aba Lab precisa de relatorios."""
        return self._mt5_research_source_for_reports()

    def get_research_layer_definitions(self) -> list[dict[str, object]]:
        """Retorna a ordem oficial das camadas de conhecimento do Research Lab."""
        return [
            {
                "index": definition.index,
                "layer": definition.layer.value,
                "title": definition.title,
                "question": definition.question,
                "responsibility": definition.responsibility,
            }
            for definition in OFFICIAL_RESEARCH_LAYERS
        ]

    def suggest_mt5_lab_setups(
        self,
        target_confidence: float = MT5_LAB_TARGET_CONFIDENCE,
    ) -> list[DashboardMT5SetupSuggestionViewModel]:
        """Sugere setups a partir do snapshot persistido do Research Lab."""
        research = self._mt5_research_source_for_reports()
        if list(getattr(research, "rows", []) or []):
            return self._mt5_setup_suggestions_from_rows(research, target_confidence)
        scenarios = list(getattr(research, "scenario_ranking", []) or [])
        if not scenarios:
            return self._mt5_setup_suggestions_from_rows(research, target_confidence)
        pairs = sorted(
            {
                str(getattr(scenario, "pair", "") or "").upper()
                for scenario in scenarios
                if str(getattr(scenario, "pair", "") or "").strip()
            }
        )
        suggestions: list[DashboardMT5SetupSuggestionViewModel] = []
        for pair in pairs:
            pair_scenarios = [
                scenario
                for scenario in scenarios
                if str(getattr(scenario, "pair", "") or "").upper() == pair
            ]
            selected = self._select_mt5_setup_suggestion(
                pair_scenarios,
                target_confidence,
            )
            if selected is not None:
                suggestions.append(
                    DashboardMT5SetupSuggestionViewModel(
                        alpha_id=str(getattr(selected, "alpha_id", "ALPHA001")),
                        pair=str(getattr(selected, "pair", pair)),
                        timeframe=str(getattr(selected, "timeframe", "M1")),
                        model=str(getattr(selected, "model", "WAIT_NO_EDGE")),
                        decision=str(getattr(selected, "decision", "WAIT")),
                        parameters=dict(getattr(selected, "parameters", {}) or {}),
                        score=float(getattr(selected, "score", 0.0) or 0.0),
                        lab_confidence=float(
                            getattr(selected, "lab_confidence", 0.0) or 0.0
                        ),
                        target_confidence=float(target_confidence),
                        status=self._mt5_setup_suggestion_status(
                            selected,
                            target_confidence,
                        ),
                        reason=str(getattr(selected, "reason", "N/D")),
                        source=str(getattr(research, "source", "MT5_RESEARCH_SNAPSHOT")),
                    )
                )
        return suggestions

    def _mt5_setup_suggestions_from_rows(
        self,
        research: DashboardMT5HeuristicResearchViewModel,
        target_confidence: float,
    ) -> list[DashboardMT5SetupSuggestionViewModel]:
        """Monta sugestoes pelo resumo leve rows quando o ranking completo e grande."""
        suggestions: list[DashboardMT5SetupSuggestionViewModel] = []
        for row in list(getattr(research, "rows", []) or []):
            pair = str(getattr(row, "pair", "") or "").upper()
            if not pair:
                continue
            configuration = dict(getattr(row, "final_configuration", {}) or {})
            timeframe = str(
                configuration.get(
                    "timeframe",
                    getattr(row, "ideal_timeframe", getattr(row, "timeframe", "M1")),
                )
                or "M1"
            )
            suggestions.append(
                DashboardMT5SetupSuggestionViewModel(
                    alpha_id=str(configuration.get("alpha", "ALPHA001")),
                    pair=pair,
                    timeframe=timeframe,
                    model=str(
                        configuration.get(
                            "modelo",
                            getattr(row, "recommended_heuristic", "WAIT_NO_EDGE"),
                        )
                    ),
                    decision=str(getattr(row, "decision", "WAIT")),
                    parameters=configuration,
                    score=float(getattr(row, "score", 0.0) or 0.0),
                    lab_confidence=float(getattr(row, "confidence", 0.0) or 0.0),
                    target_confidence=float(target_confidence),
                    status=(
                        "SUGERIDO_70"
                        if float(getattr(row, "confidence", 0.0) or 0.0)
                        >= target_confidence
                        else "MAIS_PROXIMO_DE_70"
                    ),
                    reason=str(getattr(row, "reason", "N/D")),
                    source=str(getattr(research, "source", "MT5_RESEARCH_SNAPSHOT")),
                )
            )
        return sorted(
            suggestions,
            key=lambda item: (
                str(getattr(item, "pair", "")),
                -float(getattr(item, "lab_confidence", 0.0) or 0.0),
            ),
        )

    def get_mt5_alpha_research_ranking(
        self,
        target_confidence: float = MT5_LAB_TARGET_CONFIDENCE,
    ) -> list[DashboardMT5AlphaResearchReportViewModel]:
        """Retorna ranking final das Alphas pesquisadas pelo Lab."""
        research = self._mt5_research_source_for_reports()
        scenarios = list(getattr(research, "scenario_ranking", []) or [])
        if not scenarios:
            return self._mt5_alpha_research_ranking_from_rows(
                research,
                target_confidence,
            )
        ranking = [
            self._mt5_alpha_research_report_from_scenarios(
                alpha_id,
                scenarios,
                research,
                target_confidence,
            )
            for alpha_id in self._mt5_alpha_library().keys()
        ]
        return sorted(
            ranking,
            key=lambda report: (
                str(getattr(report, "status", "") or "") == "APROVADA",
                float(getattr(report, "best_confidence", 0.0) or 0.0),
                float(getattr(report, "best_score", 0.0) or 0.0),
                int(getattr(report, "tested_scenarios", 0) or 0),
            ),
            reverse=True,
        )

    def _select_mt5_setup_suggestion(
        self,
        scenarios: list[DashboardMT5ScenarioViewModel],
        target_confidence: float,
    ) -> DashboardMT5ScenarioViewModel | None:
        valid = [
            scenario
            for scenario in scenarios
            if str(getattr(scenario, "status", "") or "").upper() == "APROVADO"
            and str(getattr(scenario, "decision", "") or "").upper() in {"BUY", "SELL"}
        ]
        if not valid:
            valid = list(scenarios)
        if not valid:
            return None
        return max(
            valid,
            key=lambda scenario: (
                float(getattr(scenario, "lab_confidence", 0.0) or 0.0)
                >= target_confidence,
                -abs(
                    float(getattr(scenario, "lab_confidence", 0.0) or 0.0)
                    - target_confidence
                ),
                float(getattr(scenario, "score", 0.0) or 0.0),
            ),
        )

    def _mt5_setup_suggestion_status(
        self,
        scenario: DashboardMT5ScenarioViewModel,
        target_confidence: float,
    ) -> str:
        if float(getattr(scenario, "lab_confidence", 0.0) or 0.0) >= target_confidence:
            return "SUGERIDO_70"
        return "MAIS_PROXIMO_DE_70"

    def _mt5_research_source_for_reports(
        self,
    ) -> DashboardMT5HeuristicResearchViewModel:
        if (
            type(self)._load_mt5_research_snapshot
            is not DashboardService._load_mt5_research_snapshot
        ):
            return self._load_mt5_research_snapshot() or self.get_mt5_research_constants()
        return self._load_mt5_research_snapshot() or self.get_mt5_research_constants()

    def get_mt5_alpha_research_report(
        self,
        alpha_id: str = "ALPHA001",
        target_confidence: float = MT5_LAB_TARGET_CONFIDENCE,
    ) -> DashboardMT5AlphaResearchReportViewModel:
        """Retorna relatorio tecnico de aprovacao/reprovacao da Alpha."""
        research = self._mt5_research_source_for_reports()
        scenarios = list(getattr(research, "scenario_ranking", []) or [])
        if scenarios:
            return self._mt5_alpha_research_report_from_scenarios(
                alpha_id,
                scenarios,
                research,
                target_confidence,
            )
        reports = self._mt5_alpha_research_ranking_from_rows(
            research,
            target_confidence,
        )
        for report in reports:
            if str(report.alpha_id).upper() == str(alpha_id).upper():
                return report
        return self._mt5_alpha_research_report_from_scenarios(
            alpha_id,
            [],
            research,
            target_confidence,
        )

    def _mt5_alpha_research_ranking_from_rows(
        self,
        research: DashboardMT5HeuristicResearchViewModel,
        target_confidence: float,
    ) -> list[DashboardMT5AlphaResearchReportViewModel]:
        """Monta ranking leve de Alphas usando somente o resumo final rows."""
        rows = list(getattr(research, "rows", []) or [])
        alpha_library = self._mt5_alpha_library()
        reports: list[DashboardMT5AlphaResearchReportViewModel] = []
        for alpha_id in alpha_library.keys():
            alpha_rows = [
                row
                for row in rows
                if str(
                    dict(getattr(row, "final_configuration", {}) or {}).get(
                        "alpha",
                        "ALPHA001",
                    )
                ).upper()
                == str(alpha_id).upper()
            ]
            best_row = max(
                alpha_rows,
                key=lambda row: (
                    float(getattr(row, "confidence", 0.0) or 0.0),
                    float(getattr(row, "score", 0.0) or 0.0),
                ),
                default=None,
            )
            reports.append(
                DashboardMT5AlphaResearchReportViewModel(
                    alpha_id=alpha_id,
                    tested_scenarios=len(alpha_rows),
                    evaluated_pairs=len(
                        {
                            str(getattr(row, "pair", "") or "").upper()
                            for row in alpha_rows
                            if str(getattr(row, "pair", "") or "").strip()
                        }
                    ),
                    best_pair=str(getattr(best_row, "pair", "NONE") or "NONE"),
                    best_timeframe=str(
                        getattr(best_row, "ideal_timeframe", "NONE") or "NONE"
                    ),
                    best_model=str(
                        dict(
                            getattr(best_row, "final_configuration", {}) or {}
                        ).get(
                            "modelo",
                            getattr(best_row, "recommended_heuristic", "NONE"),
                        )
                        if best_row is not None
                        else "NONE"
                    ),
                    best_decision=str(
                        getattr(best_row, "decision", "WAIT") or "WAIT"
                    ),
                    best_score=float(getattr(best_row, "score", 0.0) or 0.0),
                    best_confidence=float(
                        getattr(best_row, "confidence", 0.0) or 0.0
                    ),
                    ict_score=float(getattr(best_row, "ict_score", 0.0) or 0.0),
                    ict_grade=str(getattr(best_row, "ict_grade", "E") or "E"),
                    ict_status=str(
                        getattr(best_row, "ict_status", "REJEITADA")
                        or "REJEITADA"
                    ),
                    ict_usage=str(
                        getattr(best_row, "ict_usage", "Rejeitada.")
                        or "Rejeitada."
                    ),
                    ict_demo_allowed=bool(
                        getattr(best_row, "ict_demo_allowed", False)
                    ),
                    target_confidence=float(target_confidence),
                    status=(
                        "APROVADA"
                        if best_row is not None
                        and float(getattr(best_row, "confidence", 0.0) or 0.0)
                        >= target_confidence
                        else "REJEITADA"
                        if best_row is not None
                        else "SEM_DADOS"
                    ),
                    alpha_name=self._mt5_alpha_name(alpha_id),
                    hypothesis=self._mt5_alpha_hypothesis(alpha_id),
                    used_indicators=self._mt5_alpha_used_indicators(alpha_id),
                    failure_reasons=(
                        []
                        if best_row is not None
                        and float(getattr(best_row, "confidence", 0.0) or 0.0)
                        >= target_confidence
                        else ["Sem evidencia final acima do alvo no resumo rows."]
                    ),
                    recommendations=[
                        "Ranking leve gerado pelo resumo final do Lab."
                    ],
                    source=str(
                        getattr(research, "source", "MT5_RESEARCH_SNAPSHOT_ROWS")
                    ),
                )
            )
        return sorted(
            reports,
            key=lambda report: (
                str(getattr(report, "status", "") or "") == "APROVADA",
                float(getattr(report, "best_confidence", 0.0) or 0.0),
                float(getattr(report, "best_score", 0.0) or 0.0),
                int(getattr(report, "tested_scenarios", 0) or 0),
            ),
            reverse=True,
        )

    def _mt5_alpha_research_report_from_scenarios(
        self,
        alpha_id: str,
        all_scenarios: list[DashboardMT5ScenarioViewModel],
        research: object,
        target_confidence: float,
    ) -> DashboardMT5AlphaResearchReportViewModel:
        scenarios = [
            scenario
            for scenario in all_scenarios
            if str(getattr(scenario, "alpha_id", "ALPHA001")).upper()
            == str(alpha_id).upper()
        ]
        pairs = {
            str(getattr(scenario, "pair", "") or "").upper()
            for scenario in scenarios
            if str(getattr(scenario, "pair", "") or "").strip()
        }
        if not scenarios:
            return DashboardMT5AlphaResearchReportViewModel(
                alpha_id=alpha_id,
                target_confidence=target_confidence,
                status="SEM_DADOS",
                alpha_name=self._mt5_alpha_name(alpha_id),
                hypothesis=self._mt5_alpha_hypothesis(alpha_id),
                used_indicators=self._mt5_alpha_used_indicators(alpha_id),
                failure_reasons=["Nenhum cenario pesquisado para a Alpha."],
                recommendations=["Executar Pesquisa no Lab antes de avaliar a Alpha."],
                source=str(getattr(research, "source", "MT5_RESEARCH_SNAPSHOT")),
            )
        best = self._select_mt5_alpha_report_scenario(
            scenarios,
            target_confidence,
        )
        if best is None:
            return DashboardMT5AlphaResearchReportViewModel(
                alpha_id=alpha_id,
                target_confidence=target_confidence,
                status="SEM_DADOS",
                alpha_name=self._mt5_alpha_name(alpha_id),
                hypothesis=self._mt5_alpha_hypothesis(alpha_id),
                used_indicators=self._mt5_alpha_used_indicators(alpha_id),
                failure_reasons=["Nenhum cenario selecionavel para a Alpha."],
                recommendations=["Executar Pesquisa no Lab antes de avaliar a Alpha."],
                source=str(getattr(research, "source", "MT5_RESEARCH_SNAPSHOT")),
            )
        best_confidence = float(getattr(best, "lab_confidence", 0.0) or 0.0)
        status = (
            "APROVADA"
            if bool(getattr(best, "ict_demo_allowed", False))
            else "REPROVADA"
        )
        failure_reasons = self._mt5_alpha_failure_reasons(
            best,
            scenarios,
            target_confidence,
        )
        return DashboardMT5AlphaResearchReportViewModel(
            alpha_id=str(alpha_id).upper(),
            tested_scenarios=len(scenarios),
            evaluated_pairs=len(pairs),
            best_pair=str(getattr(best, "pair", "NONE")),
            best_timeframe=str(getattr(best, "timeframe", "NONE")),
            best_model=str(getattr(best, "model", "NONE")),
            best_decision=str(getattr(best, "decision", "WAIT")),
            best_score=float(getattr(best, "score", 0.0) or 0.0),
            best_confidence=best_confidence,
            ict_score=float(getattr(best, "ict_score", 0.0) or 0.0),
            ict_grade=str(getattr(best, "ict_grade", "E")),
            ict_status=str(getattr(best, "ict_status", "REJEITADA")),
            ict_usage=str(getattr(best, "ict_usage", "Rejeitada.")),
            ict_demo_allowed=bool(getattr(best, "ict_demo_allowed", False)),
            target_confidence=target_confidence,
            status=status,
            alpha_name=self._mt5_alpha_name(alpha_id),
            hypothesis=self._mt5_alpha_hypothesis(alpha_id),
            used_indicators=self._mt5_alpha_used_indicators(alpha_id),
            failure_reasons=failure_reasons,
            recommendations=self._mt5_alpha_recommendations(status),
            unavailable_evidence=[
                "Walk-forward por cenario",
                "Out-of-sample por cenario",
                "MAE/MFE por cenario",
            ],
            source=str(getattr(research, "source", "MT5_RESEARCH_SNAPSHOT")),
        )

    def _select_mt5_alpha_report_scenario(
        self,
        scenarios: list[DashboardMT5ScenarioViewModel],
        target_confidence: float,
    ) -> DashboardMT5ScenarioViewModel | None:
        """Seleciona melhor evidencia historica para auditoria da Alpha.

        A classificacao final da Alpha nao pode zerar a Confirmacao Historica
        apenas porque o melhor cenario historico ainda nao e operacionalmente
        elegivel. A elegibilidade continua refletida por ICT/status.
        """
        if not scenarios:
            return None
        return max(
            scenarios,
            key=lambda scenario: (
                float(getattr(scenario, "lab_confidence", 0.0) or 0.0) > 0.0,
                float(getattr(scenario, "lab_confidence", 0.0) or 0.0)
                >= target_confidence,
                bool(getattr(scenario, "ict_demo_allowed", False)),
                float(getattr(scenario, "lab_confidence", 0.0) or 0.0),
                int(getattr(scenario, "lab_confidence_sample_size", 0) or 0),
                float(getattr(scenario, "score", 0.0) or 0.0),
            ),
        )

    def _mt5_alpha_failure_reasons(
        self,
        best: DashboardMT5ScenarioViewModel | None,
        scenarios: list[DashboardMT5ScenarioViewModel],
        target_confidence: float,
    ) -> list[str]:
        reasons: list[str] = []
        if best is None:
            return ["Nenhum melhor cenario selecionavel."]
        best_confidence = float(getattr(best, "lab_confidence", 0.0) or 0.0)
        if best_confidence < target_confidence:
            reasons.append(
                "Nao atingiu confianca minima de certificacao "
                f"({best_confidence:.2%} < {target_confidence:.2%})."
            )
        ict_score = float(getattr(best, "ict_score", 0.0) or 0.0)
        ict_grade = str(getattr(best, "ict_grade", "E"))
        ict_demo_allowed = bool(getattr(best, "ict_demo_allowed", False))
        if not ict_demo_allowed:
            reasons.append(
                f"ICT nao libera Demo ({ict_score:.2f}, classe {ict_grade})."
            )
        reasons.extend(
            str(item)
            for item in tuple(getattr(best, "ict_rejection_reasons", ()) or ())
        )
        approved_pairs = {
            str(getattr(scenario, "pair", "") or "").upper()
            for scenario in scenarios
            if float(getattr(scenario, "lab_confidence", 0.0) or 0.0)
            >= target_confidence
        }
        total_pairs = {
            str(getattr(scenario, "pair", "") or "").upper()
            for scenario in scenarios
            if str(getattr(scenario, "pair", "") or "").strip()
        }
        if len(approved_pairs) < max(1, len(total_pairs) // 2):
            reasons.append("Pouca consistencia entre pares no alvo de confianca.")
        if not reasons:
            reasons.append("Sem motivo critico de reprovacao pelo criterio atual.")
        return reasons

    def _mt5_alpha_recommendations(self, status: str) -> list[str]:
        if status == "APROVADA":
            return [
                "Submeter a Alpha a validacao complementar de drawdown, profit factor e expectancy.",
                "Validar estabilidade fora da amostra antes de liberar constantes para uso operacional.",
            ]
        return [
            "Nao certificar a Alpha para uso operacional.",
            "Criar nova hipotese Alpha com outro comportamento de mercado.",
            "Adicionar evidencias estatisticas completas antes de nova certificacao.",
        ]

    def run_mt5_research_calibration(
        self,
        timeframe: str = "M1",
    ) -> DashboardMT5HeuristicResearchViewModel:
        """Executa calibracao MT5 sob demanda sem afetar o refresh online."""
        configuration = self.configuration_service.get_configuration_data()
        snapshots = [
            self.mt5_market_data_service.load_forex_research_snapshot(
                timeframe=candidate_timeframe,
                count=configuration.quantitative_score_candles_loaded,
            )
            for candidate_timeframe in self._mt5_research_timeframes(
                configuration,
                timeframe,
            )
        ]
        all_pairs = [
            row
            for snapshot in snapshots
            for row in list(getattr(snapshot, "pairs", []) or [])
        ]
        base_data = self.get_dashboard_data()
        pair_calibrations = [
            self._run_mt5_research_for_pair(
                pair,
                snapshots,
                base_data,
                configuration,
            )
            for pair in self._ordered_mt5_research_pairs(all_pairs)
        ]
        calibration = self._combine_mt5_pair_research_calibrations(
            pair_calibrations,
            MT5ForexSignalDashboard(timeframe="MULTI", pairs=all_pairs),
            configuration,
        )
        total_candles = sum(
            int(getattr(row, "received_candles", 0) or 0)
            for row in all_pairs
        )
        calibration = replace(
            calibration,
            last_update=datetime.now(timezone.utc).isoformat(),
            candles_loaded=total_candles,
            timeframe=timeframe,
            source="MT5_RESEARCH_ALPHA_LIBRARY_SEARCH_SPACE_5000",
        )
        object.__setattr__(self, "mt5_research_constants", calibration)
        self._save_mt5_research_snapshot(calibration)
        return calibration

    def run_mt5_research_calibration_for_pair(
        self,
        pair: str,
        timeframe: str = "M1",
    ) -> DashboardMT5HeuristicResearchViewModel:
        """Executa calibracao MT5 sob demanda apenas para um par Forex."""
        configuration = self.configuration_service.get_configuration_data()
        snapshots = [
            self.mt5_market_data_service.load_forex_research_snapshot(
                timeframe=candidate_timeframe,
                count=configuration.quantitative_score_candles_loaded,
            )
            for candidate_timeframe in self._mt5_research_timeframes(
                configuration,
                timeframe,
            )
        ]
        base_data = self.get_dashboard_data()
        calibration = self._run_mt5_research_for_pair(
            str(pair or "").upper(),
            snapshots,
            base_data,
            configuration,
        )
        pair_rows = [
            row
            for snapshot in snapshots
            for row in list(getattr(snapshot, "pairs", []) or [])
            if str(getattr(row, "pair", "") or "").upper()
            == str(pair or "").upper()
        ]
        calibration = replace(
            calibration,
            last_update=datetime.now(timezone.utc).isoformat(),
            candles_loaded=sum(
                int(getattr(row, "received_candles", 0) or 0)
                for row in pair_rows
            ),
            timeframe=timeframe,
            source="MT5_RESEARCH_ALPHA_LIBRARY_SINGLE_PAIR_SEARCH_SPACE_5000",
            message=(
                "Calibracao MT5 somente leitura executada para um par Forex. "
                "Nao autoriza operacao real."
            ),
        )
        object.__setattr__(self, "mt5_research_constants", calibration)
        self._save_mt5_research_snapshot(calibration)
        return calibration

    def _run_mt5_research_for_pair(
        self,
        pair: str,
        snapshots: list[MT5ForexSignalDashboard],
        base_data: DashboardData,
        configuration: ConfigurationData,
    ) -> DashboardMT5HeuristicResearchViewModel:
        pair_key = str(pair).upper()
        pair_rows = [
            row
            for snapshot in snapshots
            for row in list(getattr(snapshot, "pairs", []) or [])
            if str(getattr(row, "pair", "") or "").upper() == pair_key
        ]
        pair_snapshot = replace(
            snapshots[0],
            timeframe="MULTI",
            pairs=pair_rows,
        ) if snapshots else MT5ForexSignalDashboard(timeframe="MULTI", pairs=[])
        research_data = replace(
            base_data,
            mt5_forex_signals=pair_snapshot,
            configuration_data=configuration,
        )
        return self._to_view_model_mt5_heuristic_research(research_data)

    def _combine_mt5_pair_research_calibrations(
        self,
        pair_calibrations: list[DashboardMT5HeuristicResearchViewModel],
        forex: MT5ForexSignalDashboard,
        configuration: ConfigurationData,
    ) -> DashboardMT5HeuristicResearchViewModel:
        rows = [
            row
            for calibration in pair_calibrations
            for row in list(getattr(calibration, "rows", []) or [])
        ]
        scenario_ranking = sorted(
            [
                scenario
                for calibration in pair_calibrations
                for scenario in list(getattr(calibration, "scenario_ranking", []) or [])
            ],
            key=lambda scenario: (
                -float(scenario.score),
                str(scenario.pair),
                str(scenario.timeframe),
                str(scenario.model),
            ),
        )
        best_scenarios = self._best_mt5_scenarios_by_pair(scenario_ranking)
        if not rows:
            return DashboardMT5HeuristicResearchViewModel(
                rows=[],
                scenario_ranking=scenario_ranking,
                best_scenarios_by_market=best_scenarios,
                status="SEM_DADOS",
                timeframe=str(getattr(forex, "timeframe", "M1")),
                source="MT5_RESEARCH_SNAPSHOT",
                message=(
                    "Nenhum snapshot MT5 carregado para calibracao. Execute "
                    "Pesquisa MT5 no Research Lab."
                ),
            )
        ranked = [
            row
            for row in rows
            if row.status == "APROVADO" and row.recommended_heuristic != "WAIT_NO_EDGE"
        ]
        if not ranked:
            return DashboardMT5HeuristicResearchViewModel(
                rows=rows,
                scenario_ranking=scenario_ranking,
                best_scenarios_by_market=best_scenarios,
                status="SEM_HEURISTICA_APROVADA",
                timeframe=str(getattr(forex, "timeframe", "M1")),
                candles_loaded=sum(
                    int(getattr(row, "received_candles", 0) or 0)
                    for row in list(getattr(forex, "pairs", []) or [])
                ),
                source="MT5_RESEARCH_SNAPSHOT",
                message=(
                    "Nenhuma heuristica MT5 passou nos criterios minimos "
                    "da calibracao sob demanda."
                ),
            )
        best = max(
            ranked,
            key=self._mt5_research_row_rank,
        )
        best_scenario = next(
            (
                scenario
                for scenario in best_scenarios
                if scenario.pair == best.pair
                and scenario.timeframe == best.timeframe
                and scenario.model == best.recommended_heuristic
                and scenario.decision == best.decision
                and str(scenario.parameters.get("alpha", "")).upper()
                == str(best.final_configuration.get("alpha", "")).upper()
            ),
            None,
        )
        source_row = self._find_mt5_forex_row(forex, best.pair)
        return DashboardMT5HeuristicResearchViewModel(
            rows=rows,
            scenario_ranking=scenario_ranking,
            best_scenarios_by_market=best_scenarios,
            best_scenario=best_scenario,
            best_pair=best.pair,
            best_heuristic=best.recommended_heuristic,
            best_score=best.score,
            best_decision=best.decision,
            best_confidence=best.confidence,
            winner_configuration=self._winner_model_configuration(
                configuration,
                best.recommended_heuristic,
            ),
            winner_score_breakdown=dict(best.score_breakdown),
            winner_diagnostics=list(best.diagnostics),
            winner_research_configuration=self._winner_research_configuration(
                configuration,
                source_row,
                best,
                best_scenario,
            ),
            status="RESEARCH_ONLY",
            timeframe=str(getattr(forex, "timeframe", "M1")),
            candles_loaded=sum(
                int(getattr(row, "received_candles", 0) or 0)
                for row in list(getattr(forex, "pairs", []) or [])
            ),
            source="MT5_RESEARCH_SNAPSHOT",
            message=(
                "Calibracao MT5 somente leitura. O resultado gera constantes "
                "para a heuristica online e nao autoriza operacao real."
            ),
        )

    def _mt5_research_timeframes(
        self,
        configuration: ConfigurationData,
        selected_timeframe: str,
    ) -> tuple[str, ...]:
        if str(selected_timeframe or "").upper() == "MULTI":
            configured_multi = tuple(
                str(item).upper()
                for item in getattr(configuration, "timeframe_optimizer_timeframes", ())
                if str(item).strip()
            )
            return configured_multi or ("M1",)
        if (
            os.getenv("TRADERIA_MT5_RESEARCH_HISTORY_ALL_TIMEFRAMES", "0").strip()
            != "1"
        ):
            return (str(selected_timeframe or "M1").upper(),)
        configured = tuple(
            str(item).upper()
            for item in getattr(configuration, "timeframe_optimizer_timeframes", ())
            if str(item).strip()
        )
        values = (str(selected_timeframe or "M1").upper(), *configured)
        return tuple(dict.fromkeys(values))

    def _mt5_research_snapshot_path(self) -> Path:
        return Path(".traderia") / "mt5_research_snapshot.json"

    def _mt5_research_history_snapshot_path(self) -> Path:
        return Path(".traderia") / "mt5_research_history_snapshot.json"

    def mt5_research_history_database_path(self) -> Path:
        """Banco local do historico MT5 usado pelo Lab."""
        return Path(".traderia") / "traderia_mt5_history.sqlite"

    def get_mt5_research_history_database_path(self) -> str:
        """Retorna o caminho absoluto do banco local do historico MT5."""
        return str(self.mt5_research_history_database_path().resolve())

    def get_mt5_research_history_candle_count(self) -> int:
        """Retorna quantas velas o historico MT5 do Lab deve buscar."""
        configuration = self.configuration_service.get_configuration_data()
        return self._mt5_research_history_candle_count(configuration)

    def _mt5_research_history_candle_count(
        self,
        configuration: ConfigurationData,
    ) -> int:
        try:
            configured = int(
                os.getenv(
                    "TRADERIA_MT5_RESEARCH_HISTORY_CANDLES",
                    "500",
                )
            )
        except ValueError:
            configured = 500
        configured = max(1, configured)
        return min(
            configured,
            int(
                getattr(
                    configuration,
                    "quantitative_score_candles_loaded",
                    500,
                )
                or 500
            ),
        )

    def get_mt5_research_history_last_update(self) -> str:
        """Retorna a data da ultima atualizacao do historico bruto MT5."""
        target = self._mt5_research_history_snapshot_path()
        if not target.exists():
            return "N/D"
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "N/D"
        return str(
            payload.get("last_update")
            or payload.get("last_mt5_read")
            or payload.get("last_research_update")
            or "N/D"
        )

    def update_mt5_research_history(
        self,
        timeframe: str = "M1",
    ) -> MT5ForexSignalDashboard:
        """Atualiza somente o historico bruto MT5 usado pelo Research Lab."""
        return self._update_mt5_research_history(timeframe=timeframe)

    def _update_mt5_research_history(
        self,
        timeframe: str = "M1",
        progress_callback: object | None = None,
    ) -> MT5ForexSignalDashboard:
        """Atualiza o historico MT5 com notificacao opcional de progresso."""
        configuration = self.configuration_service.get_configuration_data()
        timeframes = self._mt5_research_timeframes(configuration, timeframe)
        snapshots = []
        total_timeframes = len(timeframes)
        for index, candidate_timeframe in enumerate(timeframes, start=1):
            if callable(progress_callback):
                progress_callback(
                    {
                        "phase": "history_timeframe_started",
                        "index": index,
                        "total": total_timeframes,
                        "timeframe": candidate_timeframe,
                    }
                )
            snapshot = self.mt5_market_data_service.load_forex_research_snapshot(
                timeframe=candidate_timeframe,
                count=self._mt5_research_history_candle_count(configuration),
            )
            snapshots.append(snapshot)
            if callable(progress_callback):
                progress_callback(
                    {
                        "phase": "history_timeframe_finished",
                        "index": index,
                        "total": total_timeframes,
                        "timeframe": candidate_timeframe,
                        "received_candles": sum(
                            int(getattr(row, "received_candles", 0) or 0)
                            for row in list(getattr(snapshot, "pairs", []) or [])
                        ),
                        "status": str(
                            getattr(snapshot, "safe_mode_status", "")
                            or getattr(snapshot, "connection_status", "N/D")
                        ),
                    }
                )
        if callable(progress_callback):
            progress_callback(
                {
                    "phase": "history_snapshot_saving",
                    "index": total_timeframes,
                    "total": total_timeframes,
                    "timeframe": "MULTI",
                }
            )
        all_pairs = [
            row
            for snapshot in snapshots
            for row in list(getattr(snapshot, "pairs", []) or [])
        ]
        history = MT5ForexSignalDashboard(
            connection_status=self._combined_mt5_connection_status(snapshots),
            server=self._first_non_empty_attr(snapshots, "server", "N/D"),
            account=self._first_non_empty_attr(snapshots, "account", "N/D"),
            account_type=self._first_non_empty_attr(
                snapshots,
                "account_type",
                "N/D",
            ),
            timeframe="MULTI",
            pairs=all_pairs,
            available_pairs=sorted(
                {
                    str(pair or "")
                    for snapshot in snapshots
                    for pair in list(getattr(snapshot, "available_pairs", []) or [])
                    if str(pair or "")
                }
            ),
            unavailable_pairs=sorted(
                {
                    str(pair or "")
                    for snapshot in snapshots
                    for pair in list(getattr(snapshot, "unavailable_pairs", []) or [])
                    if str(pair or "")
                }
            ),
            message="Historico MT5 de pesquisa atualizado em modo read-only.",
            connection_health=self._first_non_empty_attr(
                snapshots,
                "connection_health",
                "OFFLINE",
            ),
            connection_health_icon=self._first_non_empty_attr(
                snapshots,
                "connection_health_icon",
                "OFFLINE",
            ),
            last_update=datetime.now(timezone.utc).isoformat(),
            last_mt5_read=self._first_non_empty_attr(snapshots, "last_mt5_read", ""),
            last_candle_time=self._first_non_empty_attr(
                snapshots,
                "last_candle_time",
                "N/D",
            ),
            last_research_update=datetime.now(timezone.utc).isoformat(),
            research_cache_status="RESEARCH_HISTORY_SNAPSHOT",
            research_refresh_duration_ms=sum(
                float(getattr(snapshot, "research_refresh_duration_ms", 0.0) or 0.0)
                for snapshot in snapshots
            ),
            latency_breakdown={
                "provider_read_ms": sum(
                    float(
                        (getattr(snapshot, "latency_breakdown", {}) or {}).get(
                            "provider_read_ms",
                            0.0,
                        )
                    )
                    for snapshot in snapshots
                ),
                "features_ms": sum(
                    float(
                        (getattr(snapshot, "latency_breakdown", {}) or {}).get(
                            "features_ms",
                            0.0,
                        )
                    )
                    for snapshot in snapshots
                ),
            },
            mt5_safe_mode=True,
            safe_mode_message=(
                "Historico MT5 bruto salvo para calculos posteriores do Lab."
            ),
            safe_mode_source="MT5_RESEARCH_HISTORY",
            safe_mode_status=self._combined_mt5_connection_status(snapshots),
            safe_mode_received_candles=sum(
                int(getattr(row, "received_candles", 0) or 0)
                for row in all_pairs
            ),
            safe_mode_last_price=self._latest_mt5_history_price(all_pairs),
            safe_mode_error="; ".join(
                str(getattr(snapshot, "safe_mode_error", "") or "")
                for snapshot in snapshots
                if str(getattr(snapshot, "safe_mode_error", "") or "")
            ),
        )
        if int(getattr(history, "safe_mode_received_candles", 0) or 0) <= 0:
            stored_history = self._load_mt5_research_history_snapshot()
            if (
                stored_history is not None
                and int(getattr(stored_history, "safe_mode_received_candles", 0) or 0)
                > 0
            ):
                return replace(
                    stored_history,
                    message=(
                        "MT5 nao retornou candles nesta tentativa; ultimo "
                        "historico valido foi preservado."
                    ),
                )
        self._save_mt5_research_history_snapshot(history)
        return history

    def update_mt5_research_calculations(
        self,
        timeframe: str = "M1",
    ) -> DashboardMT5HeuristicResearchViewModel:
        """Recalcula o Lab usando o historico bruto salvo quando disponivel."""
        return self._update_mt5_research_calculations(timeframe=timeframe)

    def _update_mt5_research_calculations(
        self,
        timeframe: str = "M1",
        progress_callback: object | None = None,
    ) -> DashboardMT5HeuristicResearchViewModel:
        """Recalcula o Lab com notificacao opcional de progresso."""
        history = self._load_mt5_research_history_snapshot()
        if history is None or not list(getattr(history, "pairs", []) or []):
            return self._mt5_local_research_snapshot_or_empty(
                "Historico local do Lab indisponivel; usando ultimo resultado local."
            )
        if (
            not self._mt5_research_history_has_candle_cache(history)
            and not self._mt5_research_history_has_usable_rows(history)
        ):
            if os.getenv("TRADERIA_MT5_LAB_ALLOW_LIVE_RECALC", "0").strip() == "1":
                return self.run_mt5_research_calibration(timeframe=timeframe)
            return self._mt5_local_research_snapshot_or_empty(
                "Historico local sem cache de candles; usando ultimo resultado local."
            )
        return self._run_mt5_research_calibration_from_history(
            history,
            timeframe=timeframe,
            source="MT5_RESEARCH_CALCULATED_FROM_HISTORY_SNAPSHOT",
            progress_callback=progress_callback,
        )

    def _mt5_local_research_snapshot_or_empty(
        self,
        message: str,
    ) -> DashboardMT5HeuristicResearchViewModel:
        research = self._load_mt5_research_snapshot()
        if research is None:
            return replace(
                self.mt5_research_constants,
                status="SEM_CALIBRACAO_LOCAL",
                message=message,
                source="TRADERIANOVO_LOCAL_LAB",
            )
        research = replace(
            research,
            message=message,
            source="TRADERIANOVO_LOCAL_LAB",
        )
        object.__setattr__(self, "mt5_research_constants", research)
        return research

    def _run_mt5_research_calibration_from_history(
        self,
        history: MT5ForexSignalDashboard,
        timeframe: str = "M1",
        source: str = "MT5_RESEARCH_CALCULATED_FROM_HISTORY_SNAPSHOT",
        progress_callback: object | None = None,
    ) -> DashboardMT5HeuristicResearchViewModel:
        configuration = self.configuration_service.get_configuration_data()
        all_pairs = list(getattr(history, "pairs", []) or [])
        rows_by_timeframe: dict[str, list[MT5ForexSignalRow]] = {}
        for row in all_pairs:
            row_timeframe = str(getattr(row, "timeframe", timeframe) or timeframe)
            rows_by_timeframe.setdefault(row_timeframe, []).append(row)
        snapshots = [
            MT5ForexSignalDashboard(
                connection_status=getattr(history, "connection_status", "CONNECTED"),
                timeframe=row_timeframe,
                pairs=rows,
                available_pairs=[
                    str(getattr(row, "pair", "") or "")
                    for row in rows
                    if str(getattr(row, "pair", "") or "")
                ],
                message="Historico MT5 bruto reutilizado para recalculo do Lab.",
                last_update=str(getattr(history, "last_update", "") or ""),
                last_mt5_read=str(getattr(history, "last_mt5_read", "") or ""),
                research_cache_status="RESEARCH_HISTORY_SNAPSHOT",
            )
            for row_timeframe, rows in rows_by_timeframe.items()
        ]
        base_data = self.get_dashboard_data()
        ordered_pairs = self._ordered_mt5_research_pairs(all_pairs)
        pair_calibrations = []
        total_pairs = len(ordered_pairs)
        for index, pair in enumerate(ordered_pairs, start=1):
            if callable(progress_callback):
                progress_callback(
                    {
                        "phase": "calculation_pair_started",
                        "index": index,
                        "total": total_pairs,
                        "pair": pair,
                    }
                )
            pair_calibrations.append(
                self._run_mt5_research_for_pair(
                pair,
                snapshots,
                base_data,
                configuration,
            )
            )
            if callable(progress_callback):
                progress_callback(
                    {
                        "phase": "calculation_pair_finished",
                        "index": index,
                        "total": total_pairs,
                        "pair": pair,
                    }
                )
        calibration = self._combine_mt5_pair_research_calibrations(
            pair_calibrations,
            history,
            configuration,
        )
        total_candles = sum(
            int(getattr(row, "received_candles", 0) or 0)
            for row in all_pairs
        )
        calibration = replace(
            calibration,
            last_update=datetime.now(timezone.utc).isoformat(),
            candles_loaded=total_candles,
            timeframe=timeframe,
            source=source,
            message=(
                "Calculos do Research Lab atualizados a partir do historico "
                "MT5 bruto salvo."
            ),
        )
        object.__setattr__(self, "mt5_research_constants", calibration)
        self._save_mt5_research_snapshot(calibration)
        return calibration

    def _save_mt5_research_history_snapshot(
        self,
        history: MT5ForexSignalDashboard,
    ) -> None:
        target = self._mt5_research_history_snapshot_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(history)
        payload["candles_by_market"] = self._mt5_research_history_candles_payload(
            list(getattr(history, "pairs", []) or [])
        )
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._save_mt5_research_history_database(payload)

    def _save_mt5_research_history_database(self, payload: dict[str, Any]) -> None:
        database_path = self.mt5_research_history_database_path()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        updated_at = str(
            payload.get("last_update") or datetime.now(timezone.utc).isoformat()
        )
        pairs = [
            item
            for item in payload.get("pairs", []) or []
            if isinstance(item, dict)
        ]
        candles_by_market = payload.get("candles_by_market", {})
        if not isinstance(candles_by_market, dict):
            candles_by_market = {}

        with sqlite3.connect(database_path) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mt5_history_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mt5_history_pairs (
                    pair TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    status TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    last_price REAL,
                    received_candles INTEGER NOT NULL,
                    last_candle_time TEXT,
                    last_update TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (pair, timeframe)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mt5_history_candles (
                    pair TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    candle_time TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (pair, timeframe, candle_time)
                )
                """
            )
            connection.execute("DELETE FROM mt5_history_metadata")
            connection.execute("DELETE FROM mt5_history_pairs")
            connection.execute("DELETE FROM mt5_history_candles")
            metadata = {
                "connection_status": payload.get("connection_status", "N/D"),
                "server": payload.get("server", "N/D"),
                "account": payload.get("account", "N/D"),
                "timeframe": payload.get("timeframe", "N/D"),
                "last_update": payload.get("last_update", "N/D"),
                "snapshot_path": str(
                    self._mt5_research_history_snapshot_path().resolve()
                ),
            }
            for key, value in metadata.items():
                connection.execute(
                    """
                    INSERT INTO mt5_history_metadata (key, value, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (key, str(value), updated_at),
                )
            for row in pairs:
                pair = str(row.get("pair", "") or "").upper()
                timeframe = str(row.get("timeframe", "") or "").upper()
                if not pair or not timeframe:
                    continue
                connection.execute(
                    """
                    INSERT INTO mt5_history_pairs (
                        pair, timeframe, status, decision, last_price,
                        received_candles, last_candle_time, last_update,
                        payload_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pair,
                        timeframe,
                        str(row.get("status", "N/D")),
                        str(row.get("decision", "WAIT")),
                        self._optional_float(row.get("last_price")),
                        int(row.get("received_candles", 0) or 0),
                        str(row.get("last_candle_time", "") or ""),
                        str(row.get("last_update", "") or ""),
                        json.dumps(row, ensure_ascii=False),
                        updated_at,
                    ),
                )
            for key, candles in candles_by_market.items():
                if (
                    not isinstance(key, str)
                    or "|" not in key
                    or not isinstance(candles, list)
                ):
                    continue
                pair, timeframe = [part.upper() for part in key.split("|", 1)]
                for candle in candles:
                    if not isinstance(candle, dict):
                        continue
                    candle_time = str(candle.get("data", "") or "")
                    if not candle_time:
                        continue
                    connection.execute(
                        """
                        INSERT INTO mt5_history_candles (
                            pair, timeframe, candle_time, open, high, low,
                            close, volume, payload_json, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            pair,
                            timeframe,
                            candle_time,
                            float(candle.get("abertura", 0.0) or 0.0),
                            float(candle.get("maxima", 0.0) or 0.0),
                            float(candle.get("minima", 0.0) or 0.0),
                            float(candle.get("fechamento", 0.0) or 0.0),
                            int(candle.get("volume", 0) or 0),
                            json.dumps(candle, ensure_ascii=False),
                            updated_at,
                        ),
                    )
            connection.commit()

    def _load_mt5_research_history_snapshot(
        self,
    ) -> MT5ForexSignalDashboard | None:
        target = self._mt5_research_history_snapshot_path()
        if not target.exists():
            return None
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        rows = [
            MT5ForexSignalRow(**row)
            for row in list(payload.get("pairs", []) or [])
            if isinstance(row, dict)
        ]
        self._restore_mt5_research_history_candles(
            payload.get("candles_by_market", {})
        )
        data = {
            key: value
            for key, value in payload.items()
            if key not in {"pairs", "connection_diagnostic", "candles_by_market"}
        }
        diagnostic_payload = payload.get("connection_diagnostic")
        if isinstance(diagnostic_payload, dict):
            data["connection_diagnostic"] = MT5ConnectionDiagnostic(
                **{
                    key: value
                    for key, value in diagnostic_payload.items()
                    if key != "steps"
                }
            )
        return MT5ForexSignalDashboard(pairs=rows, **data)

    def _mt5_research_history_candles_payload(
        self,
        rows: list[MT5ForexSignalRow],
    ) -> dict[str, list[dict[str, object]]]:
        payload: dict[str, list[dict[str, object]]] = {}
        for row in rows:
            pair = str(getattr(row, "pair", "") or "").upper()
            timeframe = str(getattr(row, "timeframe", "") or "").upper()
            if not pair or not timeframe:
                continue
            candles = self._latest_mt5_forex_candles(pair, timeframe)
            if not candles:
                continue
            payload[f"{pair}|{timeframe}"] = [asdict(candle) for candle in candles]
        return payload

    def _restore_mt5_research_history_candles(
        self,
        payload: object,
    ) -> None:
        if not isinstance(payload, dict):
            return
        for key, items in payload.items():
            if not isinstance(key, str) or "|" not in key or not isinstance(items, list):
                continue
            pair, timeframe = key.split("|", 1)
            candles = [
                Candle(
                    data=str(item.get("data", "")),
                    abertura=float(item.get("abertura", 0.0) or 0.0),
                    maxima=float(item.get("maxima", 0.0) or 0.0),
                    minima=float(item.get("minima", 0.0) or 0.0),
                    fechamento=float(item.get("fechamento", 0.0) or 0.0),
                    volume=int(item.get("volume", 0) or 0),
                )
                for item in items
                if isinstance(item, dict)
            ]
            if candles:
                self.mt5_market_data_service.latest_forex_candles[
                    (pair.upper(), timeframe.upper())
                ] = candles

    def _combined_mt5_connection_status(
        self,
        snapshots: list[MT5ForexSignalDashboard],
    ) -> str:
        if any(str(getattr(snapshot, "connection_status", "")).upper() == "CONNECTED" for snapshot in snapshots):
            return "CONNECTED"
        return "DISCONNECTED"

    def _first_non_empty_attr(
        self,
        snapshots: list[MT5ForexSignalDashboard],
        name: str,
        default: str,
    ) -> str:
        for snapshot in snapshots:
            value = str(getattr(snapshot, name, "") or "")
            if value and value != "N/D":
                return value
        return default

    def _latest_mt5_history_price(self, rows: list[MT5ForexSignalRow]) -> float | None:
        for row in reversed(rows):
            price = getattr(row, "last_price", None)
            if price is not None:
                return float(price)
        return None

    def _mt5_research_history_has_candle_cache(
        self,
        history: MT5ForexSignalDashboard,
    ) -> bool:
        rows = list(getattr(history, "pairs", []) or [])
        if not rows:
            return False
        return all(
            bool(
                self._latest_mt5_forex_candles(
                    str(getattr(row, "pair", "") or ""),
                    str(getattr(row, "timeframe", "") or ""),
                )
            )
            for row in rows
            if str(getattr(row, "pair", "") or "")
            and str(getattr(row, "timeframe", "") or "")
        )

    def _mt5_research_history_has_usable_rows(
        self,
        history: MT5ForexSignalDashboard,
    ) -> bool:
        """Permite recalcular pelo resumo multi-TF salvo mesmo sem candles brutos."""
        return any(
            str(getattr(row, "status", "") or "").upper() == "OK"
            and int(getattr(row, "received_candles", 0) or 0) > 0
            for row in list(getattr(history, "pairs", []) or [])
        )

    def _should_preload_mt5_research_snapshot(self) -> bool:
        """Evita travar a abertura carregando snapshot historico grande."""
        target = self._mt5_research_snapshot_path()
        if not target.exists():
            return False
        try:
            max_bytes = int(
                os.getenv("TRADERIA_MT5_RESEARCH_PRELOAD_MAX_BYTES", "5242880")
            )
            return target.stat().st_size <= max_bytes
        except (OSError, ValueError):
            return False

    def _save_mt5_research_snapshot(
        self,
        research: DashboardMT5HeuristicResearchViewModel,
    ) -> None:
        object.__setattr__(self, "mt5_research_snapshot_cache", research)
        target = self._mt5_research_snapshot_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(asdict(research), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_mt5_research_snapshot(
        self,
    ) -> DashboardMT5HeuristicResearchViewModel | None:
        if (
            self.mt5_research_snapshot_cache is not None
            and str(getattr(self.mt5_research_snapshot_cache, "source", ""))
            != "MT5_RESEARCH_SNAPSHOT_ROWS"
            and str(getattr(self.mt5_research_snapshot_cache, "status", ""))
            != "SNAPSHOT_ROWS_ONLY"
        ):
            return self.mt5_research_snapshot_cache
        target = self._mt5_research_snapshot_path()
        if not target.exists():
            return None
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        rows = [
            DashboardMT5HeuristicResearchRowViewModel(**row)
            for row in list(payload.get("rows", []) or [])
            if isinstance(row, dict)
        ]
        scenario_ranking = [
            DashboardMT5ScenarioViewModel(**row)
            for row in list(payload.get("scenario_ranking", []) or [])
            if isinstance(row, dict)
        ]
        best_scenarios_by_market = [
            DashboardMT5ScenarioViewModel(**row)
            for row in list(payload.get("best_scenarios_by_market", []) or [])
            if isinstance(row, dict)
        ]
        best_scenario_payload = payload.get("best_scenario")
        best_scenario = (
            DashboardMT5ScenarioViewModel(**best_scenario_payload)
            if isinstance(best_scenario_payload, dict)
            else None
        )
        if self._is_legacy_mt5_research_snapshot(scenario_ranking):
            return None
        fields = {
            "best_pair",
            "best_heuristic",
            "best_score",
            "best_decision",
            "best_confidence",
            "winner_configuration",
            "winner_score_breakdown",
            "winner_diagnostics",
            "winner_research_configuration",
            "status",
            "message",
            "is_research_only",
            "last_update",
            "candles_loaded",
            "timeframe",
            "source",
        }
        data = {key: payload[key] for key in fields if key in payload}
        snapshot = DashboardMT5HeuristicResearchViewModel(
            rows=rows,
            scenario_ranking=scenario_ranking,
            best_scenarios_by_market=best_scenarios_by_market,
            best_scenario=best_scenario,
            **data,
        )
        snapshot = self._normalize_mt5_research_snapshot(snapshot)
        object.__setattr__(self, "mt5_research_snapshot_cache", snapshot)
        return snapshot

    def _mt5_research_rows_snapshot(
        self,
    ) -> DashboardMT5HeuristicResearchViewModel | None:
        """Carrega somente rows do snapshot grande do Research Lab."""
        if (
            self.mt5_research_snapshot_cache is not None
            and list(getattr(self.mt5_research_snapshot_cache, "rows", []) or [])
            and str(getattr(self.mt5_research_snapshot_cache, "source", ""))
            != "MT5_RESEARCH_SNAPSHOT_ROWS"
            and str(getattr(self.mt5_research_snapshot_cache, "status", ""))
            != "SNAPSHOT_ROWS_ONLY"
        ):
            return self.mt5_research_snapshot_cache
        target = self._mt5_research_snapshot_path()
        if not target.exists():
            return None
        try:
            rows_payload = self._read_json_top_level_array(target, "rows")
        except (OSError, ValueError, json.JSONDecodeError):
            return None
        rows = [
            DashboardMT5HeuristicResearchRowViewModel(**row)
            for row in rows_payload
            if isinstance(row, dict)
        ]
        if not rows:
            return None
        research = DashboardMT5HeuristicResearchViewModel(
            rows=rows,
            status="SNAPSHOT_ROWS_ONLY",
            source="MT5_RESEARCH_SNAPSHOT_ROWS",
            message="Constantes do Lab carregadas de forma leve pelo bloco rows.",
        )
        return research

    def _read_json_top_level_array(self, path: Path, key: str) -> list[object]:
        """Le um array top-level sem carregar o JSON inteiro em memoria."""
        marker = f'"{key}"'
        buffer = path.read_text(encoding="utf-8")
        marker_index = buffer.index(marker)
        colon_index = buffer.index(":", marker_index)
        array_start = buffer.index("[", colon_index)
        depth = 0
        in_string = False
        escaped = False
        for index in range(array_start, len(buffer)):
            char = buffer[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            else:
                if char == '"':
                    in_string = True
                elif char == "[":
                    depth += 1
                elif char == "]":
                    depth -= 1
                    if depth == 0:
                        parsed = json.loads(buffer[array_start : index + 1])
                        if not isinstance(parsed, list):
                            raise ValueError(f"Campo {key} nao e lista.")
                        return parsed
        raise ValueError(f"Array {key} incompleto.")

    def _normalize_mt5_research_snapshot(
        self,
        snapshot: DashboardMT5HeuristicResearchViewModel,
    ) -> DashboardMT5HeuristicResearchViewModel:
        """Reconstroi campos derivados para snapshots salvos antes do contrato atual."""
        scenarios = list(getattr(snapshot, "scenario_ranking", []) or [])
        if not scenarios:
            return snapshot
        best_scenarios = self._best_mt5_scenarios_by_pair(scenarios)
        candidates = best_scenarios or scenarios
        best = max(candidates, key=self._mt5_lab_target_rank)
        winner_configuration = self._mt5_research_configuration_with_scenario_evidence(
            dict(getattr(snapshot, "winner_research_configuration", {}) or {}),
            best,
        )
        return replace(
            snapshot,
            best_scenarios_by_market=best_scenarios,
            best_scenario=best,
            best_pair=best.pair,
            best_heuristic=best.model,
            best_score=best.score,
            best_decision=best.decision,
            best_confidence=best.lab_confidence,
            winner_research_configuration=winner_configuration,
        )

    def _is_legacy_mt5_research_snapshot(
        self,
        scenarios: list[DashboardMT5ScenarioViewModel],
    ) -> bool:
        return any(
            float(getattr(scenario, "lab_confidence", 0.0) or 0.0) > 0.0
            and int(getattr(scenario, "lab_confidence_sample_size", 0) or 0) == 0
            and str(
                getattr(
                    scenario,
                    "lab_confidence_source",
                    "SCENARIO_HISTORICAL_EVIDENCE",
                )
            )
            == "SCENARIO_HISTORICAL_EVIDENCE"
            for scenario in scenarios
        )

    def export_mt5_visual_signals(
        self,
        output_path: object | None = None,
    ) -> MT5VisualSignalExportResult:
        """Exporta sinais visuais read-only para indicador MT5."""
        target = self._mt5_visual_signals_output_path(output_path)
        view_model = self.get_dashboard_view_model()
        result = self.mt5_visual_signal_exporter.export(
            view_model.mt5_forex_signals,
            target,
        )
        if output_path is None:
            self._apply_mt5_demo_stop_management(target)
        return result

    def _apply_mt5_demo_stop_management(self, visual_path: Path) -> None:
        """Aplica gestao de stop demo sem alterar score, Lab ou decisao."""
        if not self._mt5_demo_execution_enabled():
            return
        self._enable_mt5_demo_provider()
        provider = getattr(self.demo_robot_execution_service, "provider", None)
        apply_management = getattr(
            provider,
            "apply_stop_management_from_signals",
            None,
        )
        if not callable(apply_management):
            return
        try:
            payload = json.loads(visual_path.read_text(encoding="utf-8"))
            signals = payload.get("signals", [])
            if isinstance(signals, list):
                apply_management(signals)
        except (OSError, ValueError, RuntimeError, TypeError):
            return

    def _mt5_visual_signals_output_path(self, output_path: object | None) -> Path:
        if output_path is not None:
            return Path(output_path)
        configured = os.getenv("TRADERIA_MT5_VISUAL_SIGNALS_PATH", "").strip()
        if configured:
            return Path(configured)
        detected = self._detect_mt5_visual_signals_path()
        if detected is not None:
            return detected
        return Path(".traderia") / "traderia_signals.json"

    def recalculate_mt5_research(
        self,
        timeframe: str = "M1",
    ) -> MT5ForexSignalDashboard:
        """Compatibilidade: executa calibracao MT5 sob demanda."""
        self.run_mt5_research_calibration(timeframe=timeframe)
        data = self.get_mt5_forex_signals()
        self._auto_export_mt5_visual_signals()
        return data

    def _auto_export_mt5_visual_signals(self) -> MT5VisualSignalExportResult | None:
        """Sincroniza o JSON visual automaticamente sem impactar o fluxo MT5."""
        if os.getenv("TRADERIA_MT5_VISUAL_SIGNALS_ENABLED", "1").strip() != "1":
            try:
                target = self._mt5_visual_signals_output_path(None)
                self.mt5_visual_signal_exporter.clear(target)
                return None
            except (OSError, ValueError, RuntimeError):
                return None
        try:
            target = self._mt5_visual_signals_output_path(None)
            view_model = self.get_light_dashboard_view_model()
            result = self.mt5_visual_signal_exporter.export(
                view_model.mt5_forex_signals,
                target,
            )
            self._apply_mt5_demo_stop_management(target)
            return result
        except (OSError, ValueError, RuntimeError):
            return None

    def _append_demo_robot_visual_signal(
        self,
        robot: DashboardDemoRobotViewModel,
    ) -> None:
        """Registra a ultima ordem demo no historico visual consumido pelo MT5."""
        if robot.entry_price is None or robot.decision not in {"BUY", "SELL"}:
            return

        target = self._mt5_visual_signals_output_path(None)
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {
                "schema_version": "traderia.mt5.visual_signals.v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": "TraderIA",
                "mode": "VISUAL_ONLY",
                "read_only": True,
                "order_execution": "NOT_ALLOWED_BY_INDICATOR",
                "signals": [],
                "signal_history": [],
            }

        signal = {
            "symbol": robot.selected_pair,
            "timeframe": robot.timeframe,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "last_candle_time": datetime.now(timezone.utc).isoformat(),
            "decision": robot.decision,
            "entry": robot.entry_price,
            "stop": robot.stop,
            "target": robot.target,
            "rr": self._visual_risk_reward(robot),
            "model": robot.model,
            "score": 0.0,
            "confidence": 0.0,
            "lab_alpha_id": str(
                dict(robot.lab_configuration).get("alpha", "ALPHA001")
            ),
            "lab_timeframe": str(
                dict(robot.lab_configuration).get("timeframe", robot.timeframe)
            ),
            "lab_configuration_source": str(
                dict(robot.lab_configuration).get("source", "RESEARCH_LAB")
            ),
            "lab_configuration": dict(robot.lab_configuration),
            "market_indicators": dict(robot.market_indicators),
            "active_indicators": list(robot.active_indicators),
            "plan_status": "PLANO_VALIDO",
            "reason": robot.result_message or robot.message,
            "reason_codes": [robot.status, robot.result_status],
            "theoretical_entry_status": "ORDEM_DEMO",
            "theoretical_entry_direction": robot.decision,
            "trigger_candle": datetime.now(timezone.utc).isoformat(),
            "exit_model": "MT5_DEMO_EXECUTION",
            "robot_status": (
                "ORDEM_ENVIADA_DEMO"
                if robot.result_status == "ACCEPTED"
                else robot.status
            ),
            "visual_only": True,
        }

        history = payload.get("signal_history", [])
        if not isinstance(history, list):
            history = []
        history.append(signal)
        payload["signal_history"] = history[
            -self.mt5_visual_signal_exporter.MAX_HISTORY_SIGNALS :
        ]
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        payload["read_only"] = True
        payload["order_execution"] = "NOT_ALLOWED_BY_INDICATOR"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def _visual_risk_reward(self, robot: DashboardDemoRobotViewModel) -> float:
        if robot.stop is None or robot.target is None or robot.entry_price is None:
            return 0.0
        risk = abs(robot.entry_price - robot.stop)
        reward = abs(robot.target - robot.entry_price)
        if risk <= 0.0:
            return 0.0
        return reward / risk

    def _detect_mt5_visual_signals_path(self) -> Path | None:
        return self.mt5_visual_signal_path_resolver.detect()

    def test_mt5_connection(
        self,
        symbol: str = "EURUSD",
        timeframe: str = "H1",
    ) -> MT5ConnectionDiagnostic:
        """Executa diagnostico MT5 read-only pela fachada do dashboard."""
        return self.mt5_market_data_service.diagnose_mt5_connection(
            symbol=symbol,
            timeframe=timeframe,
        )

    def prepare_demo_execution_order(
        self,
        strategy_signal: StrategySignal,
        market_snapshot: MarketSnapshot,
        risk_decision: RiskDecision,
        entry_price: float,
        stop_points: float,
        target_points: float,
    ) -> tuple[DecisionContext, ExecutionOrder | None]:
        """Prepara ordem demo sem enviar ao provider externo."""
        return self.demo_execution_service.prepare_order(
            strategy_signal=strategy_signal,
            market_snapshot=market_snapshot,
            risk_decision=risk_decision,
            entry_price=entry_price,
            stop_points=stop_points,
            target_points=target_points,
        )

    def submit_demo_execution_order(
        self,
        decision_context: DecisionContext,
        order: ExecutionOrder | None,
        paper_validated: bool,
    ) -> ExecutionResult:
        """Submete ordem demo pelo fluxo separado de execucao."""
        return self.demo_execution_service.submit_demo_order(
            decision_context=decision_context,
            order=order,
            paper_validated=paper_validated,
        )

    def list_demo_execution_audit_log(self) -> list[DemoExecutionAuditRecord]:
        """Lista tentativas de execucao demo registradas pela fachada."""
        return self.demo_execution_service.list_audit_log()

    def get_mt5_trade_audit_report(self) -> DashboardMT5TradeAuditViewModel:
        """Confronta ordens originadas no TraderIA com historico read-only do MT5."""
        local_records = self._read_mt5_demo_execution_jsonl()
        accepted_records = [
            record for record in local_records if bool(record.get("accepted"))
        ]
        mt5_history, mt5_status, mt5_message = self._load_mt5_trade_history()
        rows = [
            self._mt5_trade_audit_row(record, mt5_history)
            for record in accepted_records
        ]
        rows.sort(key=lambda row: str(row.timestamp), reverse=True)
        total_matched = sum(1 for row in rows if row.audit_status == "CONFERE")
        total_mismatched = sum(
            1 for row in rows if row.audit_status not in {"CONFERE", "PENDENTE"}
        )
        return DashboardMT5TradeAuditViewModel(
            rows=rows,
            total_local_records=len(local_records),
            total_accepted_local=len(accepted_records),
            total_audited=len(rows),
            total_matched=total_matched,
            total_mismatched=total_mismatched,
            mt5_connection_status=mt5_status,
            mt5_account_balance=self._load_mt5_account_balance(),
            equity_curve_default_start_date="2026-07-01",
            last_update=datetime.now(timezone.utc).isoformat(),
            message=mt5_message,
        )

    def _load_mt5_account_balance(self) -> float:
        try:
            mt5 = _import_mt5_module()
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
        probe_ok, _probe_message = _probe_mt5_before_inline_initialize()
        if not probe_ok:
            return 0.0
        initialize = getattr(mt5, "initialize", None)
        if callable(initialize) and not bool(initialize()):
            return 0.0
        account_info = getattr(mt5, "account_info", None)
        if not callable(account_info):
            return 0.0
        account = account_info()
        return float(getattr(account, "balance", 0.0) or 0.0)

    def _read_mt5_demo_execution_jsonl(self) -> list[dict[str, Any]]:
        path = Path(".traderia") / "mt5_demo_execution.jsonl"
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
        return records

    def _load_mt5_trade_history(self) -> tuple[dict[int, dict[str, Any]], str, str]:
        try:
            mt5 = _import_mt5_module()
        except ImportError:
            return {}, "INDISPONIVEL", "Biblioteca MetaTrader5 indisponivel."
        except Exception as exc:
            return {}, "INDISPONIVEL", f"Falha ao carregar MetaTrader5: {exc}"
        probe_ok, probe_message = _probe_mt5_before_inline_initialize()
        if not probe_ok:
            return {}, "OFFLINE", f"Sonda MT5 falhou antes do historico: {probe_message}"
        initialize = getattr(mt5, "initialize", None)
        if callable(initialize) and not bool(initialize()):
            error = getattr(mt5, "last_error", lambda: ("N/D", "N/D"))()
            return {}, "OFFLINE", f"MT5 initialize() falhou: {error}"
        start, end = self._mt5_trade_history_query_window()
        current_trades: dict[int, dict[str, Any]] = {}
        self._merge_mt5_current_positions(mt5, current_trades)
        self._merge_mt5_current_orders(mt5, current_trades)
        current_tickets = set(current_trades)

        cache = dict(self.mt5_trade_history_cache)
        accepted_tickets = self._accepted_mt5_local_tickets()
        refresh_history = self._should_refresh_mt5_trade_history(
            accepted_tickets=accepted_tickets,
            current_tickets=current_tickets,
            cached_history=cache,
        )

        if refresh_history:
            cache = {}
            self._merge_mt5_history_orders(mt5, start, end, cache)
            self._merge_mt5_history_deals(mt5, start, end, cache)
            object.__setattr__(self, "mt5_trade_history_cache", cache)
            object.__setattr__(self, "mt5_trade_history_cache_status", "ATUALIZADO")
            object.__setattr__(
                self,
                "mt5_trade_history_cache_message",
                "Historico MT5 atualizado por nova transicao ou cache ausente.",
            )
        else:
            object.__setattr__(self, "mt5_trade_history_cache_status", "CACHE")
            object.__setattr__(
                self,
                "mt5_trade_history_cache_message",
                "Historico MT5 mantido em cache; negociacoes abertas atualizadas.",
            )

        object.__setattr__(self, "mt5_trade_open_ticket_cache", current_tickets)

        history = dict(cache)
        for ticket, payload in current_trades.items():
            history[ticket] = {
                **history.get(ticket, {}),
                **payload,
            }

        if not history:
            return history, "SEM_HISTORICO", "MT5 conectado, mas sem historico retornado."
        return (
            history,
            "CONNECTED",
            self.mt5_trade_history_cache_message,
        )

    def _mt5_trade_history_query_window(self) -> tuple[datetime, datetime]:
        return datetime(2000, 1, 1), datetime.now() + timedelta(days=1)

    def _accepted_mt5_local_tickets(self) -> set[int]:
        tickets: set[int] = set()
        for record in self._read_mt5_demo_execution_jsonl():
            if not bool(record.get("accepted")):
                continue
            ticket = self._int_or_none(record.get("ticket"))
            if ticket is not None:
                tickets.add(ticket)
        return tickets

    def _should_refresh_mt5_trade_history(
        self,
        *,
        accepted_tickets: set[int],
        current_tickets: set[int],
        cached_history: dict[int, dict[str, Any]],
    ) -> bool:
        if not cached_history:
            return True
        previously_open = set(self.mt5_trade_open_ticket_cache)
        if previously_open - current_tickets:
            return True
        unresolved_tickets = accepted_tickets - current_tickets - set(cached_history)
        return bool(unresolved_tickets)

    def _merge_mt5_current_positions(
        self,
        mt5: object,
        history: dict[int, dict[str, Any]],
    ) -> None:
        positions_get = getattr(mt5, "positions_get", None)
        if not callable(positions_get):
            return
        positions = positions_get() or []
        for position in positions:
            data = self._mt5_namedtuple_dict(position)
            ticket = self._int_or_none(data.get("ticket"))
            if ticket is None:
                continue
            self._merge_mt5_trade_payload(
                history,
                ticket,
                self._mt5_history_payload(data, ticket, source="POSITION"),
            )

    def _merge_mt5_current_orders(
        self,
        mt5: object,
        history: dict[int, dict[str, Any]],
    ) -> None:
        orders_get = getattr(mt5, "orders_get", None)
        if not callable(orders_get):
            return
        orders = orders_get() or []
        for order in orders:
            data = self._mt5_namedtuple_dict(order)
            ticket = self._int_or_none(data.get("ticket"))
            if ticket is None:
                continue
            self._merge_mt5_trade_payload(
                history,
                ticket,
                self._mt5_history_payload(data, ticket, source="ORDER_OPEN"),
            )

    def _merge_mt5_history_orders(
        self,
        mt5: object,
        start: datetime,
        end: datetime,
        history: dict[int, dict[str, Any]],
    ) -> None:
        orders_get = getattr(mt5, "history_orders_get", None)
        if not callable(orders_get):
            return
        orders = orders_get(start, end) or []
        for order in orders:
            data = self._mt5_namedtuple_dict(order)
            ticket = self._int_or_none(data.get("ticket"))
            if ticket is None:
                continue
            self._merge_mt5_trade_payload(
                history,
                ticket,
                self._mt5_history_payload(data, ticket, source="ORDER"),
            )

    def _merge_mt5_history_deals(
        self,
        mt5: object,
        start: datetime,
        end: datetime,
        history: dict[int, dict[str, Any]],
    ) -> None:
        deals_get = getattr(mt5, "history_deals_get", None)
        if not callable(deals_get):
            return
        deals = deals_get(start, end) or []
        for deal in deals:
            data = self._mt5_namedtuple_dict(deal)
            deal_ticket = self._int_or_none(data.get("ticket"))
            order_ticket = self._int_or_none(data.get("order"))
            payload = self._mt5_history_payload(
                data,
                deal_ticket,
                source="DEAL",
            )
            if deal_ticket is not None:
                self._merge_mt5_trade_payload(history, deal_ticket, payload)
            if order_ticket is not None:
                self._merge_mt5_trade_payload(history, order_ticket, payload)
            position_ticket = self._int_or_none(data.get("position_id"))
            if position_ticket is not None:
                self._merge_mt5_trade_payload(
                    history,
                    position_ticket,
                    payload,
                    aggregate_profit=True,
                )

    def _merge_mt5_trade_payload(
        self,
        history: dict[int, dict[str, Any]],
        ticket: int,
        payload: dict[str, Any],
        aggregate_profit: bool = False,
    ) -> None:
        existing = history.get(ticket, {})
        existing_profit = float(existing.get("profit") or 0.0)
        payload_profit = float(payload.get("profit") or 0.0)
        merged = {**existing, **payload}
        if existing.get("source") in {"POSITION", "ORDER_OPEN"}:
            merged["source"] = existing.get("source")
            merged["profit"] = existing.get("profit", merged.get("profit", 0.0))
            merged["time"] = existing.get("time", merged.get("time", "N/D"))
        elif aggregate_profit:
            merged["source"] = "DEAL"
            merged["profit"] = existing_profit + payload_profit
            for key in ("symbol", "side", "volume", "price"):
                current = existing.get(key)
                if current not in (None, "", "N/D", 0, 0.0):
                    merged[key] = current
        history[ticket] = merged

    def _mt5_namedtuple_dict(self, item: object) -> dict[str, Any]:
        as_dict = getattr(item, "_asdict", None)
        if callable(as_dict):
            return dict(as_dict())
        return {
            key: getattr(item, key)
            for key in dir(item)
            if not key.startswith("_") and not callable(getattr(item, key))
        }

    def _mt5_history_payload(
        self,
        data: dict[str, Any],
        ticket: int | None,
        source: str,
    ) -> dict[str, Any]:
        side = self._mt5_side_from_type(data.get("type"))
        timestamp = data.get("time_done") or data.get("time")
        return {
            "ticket": ticket,
            "source": source,
            "symbol": str(data.get("symbol") or "N/D"),
            "side": side,
            "volume": float(
                data.get("volume_initial")
                or data.get("volume")
                or data.get("volume_current")
                or 0
            ),
            "price": float(
                data.get("price_open")
                or data.get("price")
                or data.get("price_current")
                or 0
            ),
            "profit": float(data.get("profit") or 0),
            "time": self._mt5_history_time(timestamp),
            "position_id": self._int_or_none(data.get("position_id")),
            "order": self._int_or_none(data.get("order")),
            "entry": self._int_or_none(data.get("entry")),
        }

    def _mt5_trade_audit_row(
        self,
        record: dict[str, Any],
        mt5_history: dict[int, dict[str, Any]],
    ) -> DashboardMT5TradeAuditRowViewModel:
        local_ticket = self._int_or_none(record.get("ticket"))
        mt5_record = mt5_history.get(local_ticket or -1)
        if mt5_record is None:
            return DashboardMT5TradeAuditRowViewModel(
                timestamp=str(record.get("timestamp") or "N/D"),
                symbol=str(record.get("symbol") or "N/D"),
                side=str(record.get("side") or "N/D"),
                quantity=float(record.get("quantity") or 0),
                entry_price=float(record.get("entry_price") or 0),
                stop=self._float_or_none(record.get("stop")),
                target=self._float_or_none(record.get("target")),
                projected_profit=self._projected_profit_from_local_record(record),
                projected_loss=self._projected_loss_from_local_record(record),
                local_status=str(record.get("status") or "N/D"),
                local_message=str(record.get("message") or "N/D"),
                local_ticket=local_ticket,
                mt5_source="N/D",
                operation_status="NAO_ENCONTRADA",
                audit_status="NAO_ENCONTRADO_MT5",
                audit_message="Ticket local aceito nao encontrado no historico MT5.",
                dynamic_exit_policy=str(
                    record.get("dynamic_exit_policy") or record.get("stop_management") or "N/D"
                ),
                dynamic_exit_action=str(
                    record.get("dynamic_exit_action") or "N/D"
                ),
                dynamic_exit_reason=str(
                    record.get("dynamic_exit_reason") or "N/D"
                ),
                dynamic_exit_confidence=self._float_or_none(
                    record.get("dynamic_exit_confidence")
                )
                or 0.0,
                dynamic_exit_market_state=str(
                    record.get("dynamic_exit_market_state") or "NO_POSITION"
                ),
                dynamic_exit_r_multiple=self._float_or_none(
                    record.get("dynamic_exit_r_multiple")
                )
                or 0.0,
                dynamic_exit_candidate_stop=self._float_or_none(
                    record.get("dynamic_exit_candidate_stop")
                ),
                dynamic_exit_allowed_to_execute_demo=bool(
                    record.get("dynamic_exit_allowed_to_execute_demo") is True
                ),
                dynamic_exit_executed_action=str(
                    record.get("dynamic_exit_executed_action") or "NONE"
                ),
                dynamic_exit_final_result="NAO_ENCONTRADO_MT5",
            )
        checks = self._mt5_trade_checks(record, mt5_record)
        status = "CONFERE" if all(checks.values()) else "DIVERGENTE"
        message = (
            "Registro local confere com historico MT5."
            if status == "CONFERE"
            else "Divergencia: "
            + ", ".join(key for key, value in checks.items() if not value)
        )
        return DashboardMT5TradeAuditRowViewModel(
            timestamp=str(record.get("timestamp") or "N/D"),
            symbol=str(record.get("symbol") or "N/D"),
            side=str(record.get("side") or "N/D"),
            quantity=float(record.get("quantity") or 0),
            entry_price=float(record.get("entry_price") or 0),
            stop=self._float_or_none(record.get("stop")),
            target=self._float_or_none(record.get("target")),
            projected_profit=self._projected_profit_from_local_record(record),
            projected_loss=self._projected_loss_from_local_record(record),
            local_status=str(record.get("status") or "N/D"),
            local_message=str(record.get("message") or "N/D"),
            local_ticket=local_ticket,
            mt5_found=True,
            mt5_ticket=self._int_or_none(mt5_record.get("ticket")),
            mt5_source=str(mt5_record.get("source") or "N/D"),
            operation_status=self._mt5_operation_status(mt5_record),
            mt5_symbol=str(mt5_record.get("symbol") or "N/D"),
            mt5_side=str(mt5_record.get("side") or "N/D"),
            mt5_volume=float(mt5_record.get("volume") or 0),
            mt5_price=float(mt5_record.get("price") or 0),
            mt5_realized_profit=float(mt5_record.get("profit") or 0),
            mt5_time=str(mt5_record.get("time") or "N/D"),
            audit_status=status,
            audit_message=message,
            dynamic_exit_policy=str(
                record.get("dynamic_exit_policy") or record.get("stop_management") or "N/D"
            ),
            dynamic_exit_action=str(record.get("dynamic_exit_action") or "N/D"),
            dynamic_exit_reason=str(record.get("dynamic_exit_reason") or "N/D"),
            dynamic_exit_confidence=self._float_or_none(
                record.get("dynamic_exit_confidence")
            )
            or 0.0,
            dynamic_exit_market_state=str(
                record.get("dynamic_exit_market_state") or "NO_POSITION"
            ),
            dynamic_exit_r_multiple=self._float_or_none(
                record.get("dynamic_exit_r_multiple")
            )
            or 0.0,
            dynamic_exit_candidate_stop=self._float_or_none(
                record.get("dynamic_exit_candidate_stop")
            ),
            dynamic_exit_allowed_to_execute_demo=bool(
                record.get("dynamic_exit_allowed_to_execute_demo") is True
            ),
            dynamic_exit_executed_action=str(
                record.get("dynamic_exit_executed_action") or "NONE"
            ),
            dynamic_exit_final_result=self._dynamic_exit_final_result(status, mt5_record),
        )

    def _dynamic_exit_final_result(
        self,
        audit_status: str,
        mt5_record: dict[str, Any],
    ) -> str:
        operation_status = self._mt5_operation_status(mt5_record)
        if operation_status == "ABERTA":
            return "POSICAO_ABERTA"
        if operation_status == "ORDEM_ABERTA":
            return "ORDEM_ABERTA"
        if operation_status == "FECHADA/HISTORICO":
            profit = float(mt5_record.get("profit") or 0.0)
            if profit > 0:
                return "FECHADA_LUCRO"
            if profit < 0:
                return "FECHADA_PREJUIZO"
            return "FECHADA_ZERO"
        return audit_status

    def _mt5_operation_status(self, mt5_record: dict[str, Any]) -> str:
        source = str(mt5_record.get("source") or "").upper()
        if source == "POSITION":
            return "ABERTA"
        if source == "ORDER_OPEN":
            return "ORDEM_ABERTA"
        if source in {"ORDER", "DEAL"}:
            return "FECHADA/HISTORICO"
        return "NAO_ENCONTRADA"

    def _projected_profit_from_local_record(self, record: dict[str, Any]) -> float:
        side = str(record.get("side") or "").upper()
        entry = self._float_or_none(record.get("entry_price"))
        target = self._float_or_none(record.get("target"))
        if entry is None or target is None:
            return 0.0
        if side == "BUY":
            return max(0.0, self._mt5_projected_money(record, entry, target))
        if side == "SELL":
            return max(0.0, self._mt5_projected_money(record, target, entry))
        return 0.0

    def _projected_loss_from_local_record(self, record: dict[str, Any]) -> float:
        side = str(record.get("side") or "").upper()
        entry = self._float_or_none(record.get("entry_price"))
        stop = self._float_or_none(record.get("stop"))
        if entry is None or stop is None:
            return 0.0
        if side == "BUY":
            return -max(0.0, self._mt5_projected_money(record, stop, entry))
        if side == "SELL":
            return -max(0.0, self._mt5_projected_money(record, entry, stop))
        return 0.0

    def _mt5_projected_money(
        self,
        record: dict[str, Any],
        lower_price: float,
        higher_price: float,
    ) -> float:
        quantity = float(record.get("quantity") or 0)
        if quantity <= 0:
            return 0.0
        symbol = str(record.get("symbol") or "").upper()
        contract_size = float(record.get("contract_size") or 100000)
        gross = max(0.0, higher_price - lower_price) * quantity * contract_size
        quote_currency = symbol[-3:] if len(symbol) >= 6 else "USD"
        if quote_currency != "USD":
            conversion_price = higher_price or lower_price
            if conversion_price > 0:
                return gross / conversion_price
        return gross

    def _mt5_trade_checks(
        self,
        record: dict[str, Any],
        mt5_record: dict[str, Any],
    ) -> dict[str, bool]:
        return {
            "symbol": str(record.get("symbol")).upper()
            == str(mt5_record.get("symbol")).upper(),
            "side": str(record.get("side")).upper()
            == str(mt5_record.get("side")).upper(),
            "volume": math.isclose(
                float(record.get("quantity") or 0),
                float(mt5_record.get("volume") or 0),
                rel_tol=1e-6,
                abs_tol=1e-6,
            ),
        }

    def _mt5_side_from_type(self, value: object) -> str:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return "N/D"
        if numeric == 0:
            return "BUY"
        if numeric == 1:
            return "SELL"
        return "N/D"

    def _mt5_history_time(self, value: object) -> str:
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            return "N/D"

    def _int_or_none(self, value: object) -> int | None:
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def _float_or_none(self, value: object) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def get_demo_robot_status(self) -> DashboardDemoRobotViewModel:
        """Retorna estado atual do robo MT5 demo."""
        return self.last_demo_robot_status

    def arm_demo_robot(
        self,
        pair: str = "TODOS",
        timeframe: str = "H1",
    ) -> DashboardDemoRobotViewModel:
        """Arma o robo demo temporal sem executar ordem imediatamente."""
        if not self._mt5_demo_execution_enabled():
            self.mt5_demo_robot_service.enabled = False
            object.__setattr__(
                self,
                "last_demo_robot_status",
                DashboardDemoRobotViewModel(
                    status="DISABLED",
                    message=(
                        "Robo demo nao armado. Defina "
                        "TRADERIA_DEMO_EXECUTION_ENABLED=1 para permitir "
                        "execucao somente em conta MT5 Demo."
                    ),
                    selected_pair=pair,
                    timeframe=timeframe,
                    model="TEMPORAL_DEMO_ROBOT",
                    decision="WAIT",
                    result_status="DISABLED",
                    result_message="Nenhuma ordem foi enviada ao MT5.",
                    provider="MT5_DEMO_DISABLED",
                    mt5_order_send_enabled=False,
                    audit_log=self._demo_robot_audit_rows(),
                ),
            )
            return self.last_demo_robot_status

        self.mt5_demo_robot_service.enabled = True
        object.__setattr__(
            self,
            "last_demo_robot_status",
            DashboardDemoRobotViewModel(
                status="ARMED",
                message=(
                    "Robo demo armado. Aguardando candle novo com gatilho "
                    "WAIT -> BUY/SELL e plano valido do Research Lab."
                ),
                selected_pair=pair,
                timeframe=timeframe,
                model="TEMPORAL_DEMO_ROBOT",
                decision="WAIT",
                result_status="ARMED_WAITING",
                result_message="Nenhuma ordem foi enviada ao MT5.",
                provider="MT5_DEMO",
                real_order_enabled=False,
                mt5_order_send_enabled=True,
                audit_log=self._demo_robot_audit_rows(),
            ),
        )
        return self.last_demo_robot_status

    def disarm_demo_robot(
        self,
        pair: str = "TODOS",
        timeframe: str = "H1",
    ) -> DashboardDemoRobotViewModel:
        """Desarma o robo demo temporal."""
        self.mt5_demo_robot_service.enabled = False
        object.__setattr__(
            self,
            "last_demo_robot_status",
            DashboardDemoRobotViewModel(
                status="DISARMED",
                message="Robo demo desarmado. Nenhuma avaliacao automatica ativa.",
                selected_pair=pair,
                timeframe=timeframe,
                model="TEMPORAL_DEMO_ROBOT",
                decision="WAIT",
                result_status="DISARMED",
                result_message="Nenhuma ordem foi enviada ao MT5.",
                provider="MT5_DEMO_DISABLED",
                mt5_order_send_enabled=False,
                audit_log=self._demo_robot_audit_rows(),
            ),
        )
        return self.last_demo_robot_status

    def evaluate_armed_demo_robot_once(
        self,
        pair: str = "TODOS",
        timeframe: str = "H1",
    ) -> DashboardDemoRobotViewModel:
        """Avalia uma vez o robo armado e executa no maximo um gatilho valido."""
        if not self.mt5_demo_robot_service.enabled:
            object.__setattr__(
                self,
                "last_demo_robot_status",
                DashboardDemoRobotViewModel(
                    status="NOT_ARMED",
                    message="Arme o robo demo antes de avaliar entradas.",
                    selected_pair=pair,
                    timeframe=timeframe,
                    model="TEMPORAL_DEMO_ROBOT",
                    decision="WAIT",
                    result_status="NOT_ARMED",
                    result_message="Nenhuma ordem foi enviada ao MT5.",
                    provider="MT5_DEMO_DISABLED",
                    mt5_order_send_enabled=False,
                    audit_log=self._demo_robot_audit_rows(),
                ),
            )
            return self.last_demo_robot_status
        if not self._mt5_demo_execution_enabled():
            self.mt5_demo_robot_service.enabled = False
            return self.arm_demo_robot(pair=pair, timeframe=timeframe)

        forex = self.get_mt5_forex_signals()
        rows = self._candidate_rows_for_demo_robot(forex, pair)
        if not rows:
            object.__setattr__(
                self,
                "last_demo_robot_status",
                DashboardDemoRobotViewModel(
                    status="NO_SIGNAL",
                    message="Nenhum par MT5 disponivel para o robo demo avaliar.",
                    selected_pair=pair,
                    timeframe=timeframe,
                    model="TEMPORAL_DEMO_ROBOT",
                    decision="WAIT",
                    result_status="NO_SIGNAL",
                    result_message="Nenhuma ordem foi enviada ao MT5.",
                    provider="MT5_DEMO",
                    mt5_order_send_enabled=True,
                    audit_log=self._demo_robot_audit_rows(),
                ),
            )
            return self.last_demo_robot_status

        research = self._mt5_research_source_for_reports()
        active_models = self._active_mt5_research_models_by_market(research)
        active_research_rows = self._active_mt5_research_rows_by_market(research)
        self._enable_mt5_demo_provider()
        self.mt5_demo_robot_service.execution_service = (
            self.demo_robot_execution_service
        )

        last_waiting: DashboardDemoRobotViewModel | None = None
        for source_row in rows:
            active_model = self._active_mt5_research_model_for_row(
                source_row,
                active_models,
                research,
            )
            row = self._to_view_model_mt5_forex_signal_row(
                source_row,
                active_model,
                self._active_mt5_research_row_for_source_row(
                    source_row,
                    active_research_rows,
                ),
            )
            plan = self._mt5_research_trade_plan_for_view_row(row)
            if plan.status != "PLANO_VALIDO":
                last_waiting = self._demo_robot_view_model(
                    row=row,
                    status="AGUARDANDO_PLANO",
                    message=(
                        "Sinal direcional sem plano executavel do Research Lab. "
                        "Robo continua monitorando os demais pares."
                    ),
                    result_status=plan.status,
                    result_message=plan.reason,
                    entry_price=None,
                    stop=None,
                    target=None,
                    provider="MT5_DEMO",
                    mt5_order_send_enabled=True,
                    rejection_tree=self._demo_robot_rejection_tree(
                        row,
                        plan,
                        enabled=self.mt5_demo_robot_service.enabled,
                        mt5_order_send_enabled=True,
                    ),
                )
                continue
            time_context = self.forex_time_layer.classify(
                row.pair,
                str(getattr(source_row, "last_candle_time", "")),
            )
            signal = self._mt5_demo_signal_from_view_row(
                row,
                candle_time=str(getattr(source_row, "last_candle_time", "")),
                time_context=time_context,
            )
            robot_plan = self._to_mt5_demo_trade_plan(row, plan)
            result = self.mt5_demo_robot_service.evaluate_once(signal, robot_plan)
            if result.status in {"EXECUTED", "REJECTED"}:
                object.__setattr__(
                    self,
                    "last_demo_robot_status",
                    self._demo_robot_view_model(
                        row=row,
                        status=result.status,
                        message=result.message,
                        result_status=(
                            result.execution_result.status
                            if result.execution_result is not None
                            else result.status
                        ),
                        result_message=(
                            result.execution_result.message
                            if result.execution_result is not None
                            else result.message
                        ),
                        entry_price=plan.entry_price,
                        stop=plan.stop,
                        target=plan.target,
                        provider="MT5_DEMO",
                        mt5_order_send_enabled=True,
                        rejection_tree=self._demo_robot_rejection_tree(
                            row,
                            plan,
                            enabled=self.mt5_demo_robot_service.enabled,
                            mt5_order_send_enabled=True,
                            time_context=time_context,
                            result_status=(
                                result.execution_result.status
                                if result.execution_result is not None
                                else result.status
                            ),
                            result_message=(
                                result.execution_result.message
                                if result.execution_result is not None
                                else result.message
                            ),
                        ),
                    ),
                )
                self._append_demo_robot_visual_signal(self.last_demo_robot_status)
                return self.last_demo_robot_status
            last_waiting = self._demo_robot_view_model(
                row=row,
                status="ARMED_WAITING",
                message=(
                    "Robo demo armado e aguardando novo gatilho valido do "
                    "Research Lab."
                ),
                result_status=result.status,
                result_message=result.message,
                entry_price=plan.entry_price,
                stop=plan.stop,
                target=plan.target,
                provider="MT5_DEMO",
                mt5_order_send_enabled=True,
                rejection_tree=self._demo_robot_rejection_tree(
                    row,
                    plan,
                    enabled=self.mt5_demo_robot_service.enabled,
                    mt5_order_send_enabled=True,
                    time_context=time_context,
                    result_status=result.status,
                    result_message=result.message,
                ),
            )

        object.__setattr__(
            self,
            "last_demo_robot_status",
            last_waiting
            or DashboardDemoRobotViewModel(
                status="ARMED_WAITING",
                message="Robo demo armado e sem gatilho valido no momento.",
                selected_pair=pair,
                timeframe=timeframe,
                model="TEMPORAL_DEMO_ROBOT",
                decision="WAIT",
                result_status="ARMED_WAITING",
                result_message="Nenhuma ordem foi enviada ao MT5.",
                provider="MT5_DEMO",
                mt5_order_send_enabled=True,
                audit_log=self._demo_robot_audit_rows(),
            ),
        )
        return self.last_demo_robot_status

    def _mt5_demo_signal_from_view_row(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
        *,
        candle_time: str,
        time_context: object,
    ) -> MT5DemoRobotSignal:
        configuration = self.configuration_service.get_configuration_data()
        session_filter_enabled = bool(
            getattr(configuration, "forex_session_filter_enabled", True)
        )
        temporal_blocked = bool(getattr(time_context, "temporal_blocked", False))
        temporal_blocking_enabled = bool(
            session_filter_enabled and temporal_blocked
        )
        return MT5DemoRobotSignal(
            symbol=row.pair,
            timeframe=row.timeframe,
            candle_time=candle_time,
            decision=row.decision,
            confidence=row.confidence,
            active_model=row.active_model,
            reason=row.reason,
            alpha_id=row.lab_alpha_id,
            alpha_version=str(row.lab_parameters.get("alpha_version", "1.0")),
            technical_score=row.confidence,
            historical_confirmation=row.lab_confidence,
            temporal_blocked=bool(session_filter_enabled and temporal_blocked),
            temporal_status=str(getattr(time_context, "temporal_status", "N/D")),
            temporal_reason=str(getattr(time_context, "temporal_reason", "")),
            session_filter_enabled=session_filter_enabled,
            session_filter_result=(
                "BLOCKED"
                if session_filter_enabled and temporal_blocked
                else ("ALLOWED" if session_filter_enabled else "IGNORED")
            ),
            session_filter_reason=str(getattr(time_context, "temporal_reason", "")),
            forex_session=str(getattr(time_context, "session_label", "N/D")),
            forex_session_open=not bool(session_filter_enabled and temporal_blocked),
            timestamp_utc=str(getattr(time_context, "timestamp_utc", "N/D")),
            timestamp_brt=str(getattr(time_context, "timestamp_brt", "N/D")),
            weekday=str(getattr(time_context, "weekday", "N/D")),
            is_rollover=bool(getattr(time_context, "is_rollover_window", False)),
            is_london_ny_overlap=bool(
                getattr(time_context, "is_london_ny_overlap", False)
            ),
            is_sunday_open=bool(getattr(time_context, "is_sunday_open", False)),
            is_friday_late=bool(getattr(time_context, "is_friday_late", False)),
            macro_event_blocked=False,
            macro_event_reason="Calendario macroeconomico nao configurado.",
            last_price=row.last_price,
            trend=row.trend,
            momentum=row.momentum,
            volatility=row.volatility,
            rsi=row.rsi,
            short_average=row.short_average,
            long_average=row.long_average,
            mid_average=row.mid_average,
            ema_fast=row.ema_fast,
            ema_mid=row.ema_mid,
            ema_slow=row.ema_slow,
            atr=row.atr,
            support=row.support,
            resistance=row.resistance,
            swing_high=row.swing_high,
            swing_low=row.swing_low,
        )

    def run_online_demo_robot_cycle(
        self,
        pair: str = "TODOS",
        timeframe: str = "H1",
    ) -> DashboardDemoRobotViewModel:
        """Atualiza MT5 e avalia o robo armado em um ciclo online."""
        if self.mt5_demo_robot_service.enabled and self._mt5_demo_execution_enabled():
            self.load_mt5_forex_signals(timeframe=timeframe)
        return self.evaluate_armed_demo_robot_once(pair=pair, timeframe=timeframe)

    def run_demo_robot_once(
        self,
        pair: str,
        timeframe: str = "H1",
    ) -> DashboardDemoRobotViewModel:
        """Executa um ciclo real na conta MT5 demo, quando habilitado por env."""
        if not self._mt5_demo_execution_enabled():
            return self.arm_demo_robot(pair=pair, timeframe=timeframe)
        self.mt5_demo_robot_service.enabled = True
        return self.evaluate_armed_demo_robot_once(pair=pair, timeframe=timeframe)

    def run_demo_robot_for_all(
        self,
        pairs: list[str] | None = None,
        timeframe: str = "H1",
    ) -> DashboardDemoRobotViewModel:
        """Executa um ciclo demo para todos os pares MT5 informados."""
        forex = self.get_mt5_forex_signals()
        available_pairs = [
            str(getattr(row, "pair", "")).strip()
            for row in forex.pairs
            if str(getattr(row, "pair", "")).strip()
            and str(getattr(row, "status", "")).upper() == "OK"
        ]
        requested_pairs = [pair for pair in (pairs or available_pairs) if pair]
        if not requested_pairs:
            object.__setattr__(
                self,
                "last_demo_robot_status",
                DashboardDemoRobotViewModel(
                    status="NO_SIGNAL",
                    message="Nenhum ativo MT5 disponivel para ciclo demo.",
                    selected_pair="TODOS",
                    timeframe=timeframe,
                ),
            )
            return self.last_demo_robot_status

        if not self._mt5_demo_execution_enabled():
            object.__setattr__(
                self,
                "last_demo_robot_status",
                DashboardDemoRobotViewModel(
                    status="DISABLED",
                    message=(
                        "Execucao MT5 Demo para todos os ativos bloqueada. "
                        "Defina TRADERIA_DEMO_EXECUTION_ENABLED=1."
                    ),
                    selected_pair="TODOS",
                    timeframe=timeframe,
                    model="MULTI_ASSET",
                    decision="MULTI_ASSET",
                    result_status="DISABLED",
                    result_message="Nenhuma ordem foi enviada ao MT5.",
                    provider="MT5_DEMO_DISABLED",
                    mt5_order_send_enabled=False,
                    audit_log=self._demo_robot_audit_rows(),
                ),
            )
            return self.last_demo_robot_status

        results = [
            self.run_demo_robot_once(pair=pair, timeframe=timeframe)
            for pair in requested_pairs
        ]
        accepted = sum(1 for result in results if result.result_status == "ACCEPTED")
        rejected = sum(1 for result in results if result.status == "REJECTED")
        no_order = sum(
            1
            for result in results
            if result.status in {
                "NO_ORDER",
                "NO_SIGNAL",
                "AGUARDANDO_PLANO",
                "ARMED_WAITING",
            }
        )
        disabled = sum(1 for result in results if result.status == "DISABLED")
        message = (
            "Ciclo MT5 Demo para todos os ativos concluido: "
            f"{accepted} aceita(s), {rejected} rejeitada(s), "
            f"{no_order} sem ordem, {disabled} desabilitada(s)."
        )
        object.__setattr__(
            self,
            "last_demo_robot_status",
            DashboardDemoRobotViewModel(
                status="BATCH_COMPLETED",
                message=message,
                selected_pair="TODOS",
                timeframe=timeframe,
                model="MULTI_ASSET",
                decision="MULTI_ASSET",
                result_status="BATCH_COMPLETED",
                result_message=message,
                provider="MT5_DEMO",
                real_order_enabled=False,
                mt5_order_send_enabled=True,
                audit_log=self._demo_robot_audit_rows(),
            ),
        )
        return self.last_demo_robot_status

    def _candidate_rows_for_demo_robot(
        self,
        forex: MT5ForexSignalDashboard,
        pair: str,
    ) -> list[object]:
        requested = str(pair or "TODOS").upper()
        rows = [
            row
            for row in list(getattr(forex, "pairs", []) or [])
            if str(getattr(row, "status", "")).upper() == "OK"
        ]
        if requested in {"TODOS", "ALL"}:
            return rows
        return [
            row
            for row in rows
            if str(getattr(row, "pair", "")).upper() == requested
        ]

    def _to_mt5_demo_trade_plan(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
        plan: MT5ResearchTradePlan,
    ) -> MT5DemoTradePlan:
        if (
            plan.status != "PLANO_VALIDO"
            or plan.entry_price is None
            or plan.stop is None
            or plan.target is None
        ):
            raise ValueError("Plano MT5 Demo exige PLANO_VALIDO do Research Lab.")
        return MT5DemoTradePlan(
            symbol=row.pair,
            timeframe=row.timeframe,
            entry_price=float(plan.entry_price),
            stop=float(plan.stop),
            target=float(plan.target),
            risk_reward=float(plan.risk_reward),
            source=plan.source,
            status=plan.status,
            stop_reason=plan.stop_reason,
            target_reason=plan.target_reason,
            exit_model=plan.exit_model,
        )

    def _mt5_demo_execution_enabled(self) -> bool:
        return os.environ.get("TRADERIA_DEMO_EXECUTION_ENABLED") == "1"

    def _enable_mt5_demo_provider(self) -> None:
        current_provider = getattr(self.demo_robot_execution_service, "provider", None)
        if current_provider.__class__.__name__ == "MT5DemoExecutionProvider":
            object.__setattr__(
                self,
                "demo_robot_execution_service",
                DemoExecutionService(
                    provider=current_provider,
                    policy=self._mt5_demo_execution_policy_from_env(),
                    daily_operations=self.demo_robot_execution_service.daily_operations,
                    daily_result=self.demo_robot_execution_service.daily_result,
                    audit_log=self.demo_robot_execution_service.audit_log,
                ),
            )
            return
        provider_module = importlib.import_module(
            "infrastructure.execution.mt5_demo_execution_provider"
        )
        provider_class = getattr(provider_module, "MT5DemoExecutionProvider")
        object.__setattr__(
            self,
            "demo_robot_execution_service",
            DemoExecutionService(
                provider=provider_class(),
                policy=self._mt5_demo_execution_policy_from_env(),
            ),
        )

    def _mt5_demo_execution_policy_from_env(self) -> DemoExecutionPolicy:
        return DemoExecutionPolicy(
            max_daily_operations=int(os.environ.get("TRADERIA_DEMO_MAX_TRADES", "8")),
            max_daily_loss=float(os.environ.get("TRADERIA_DEMO_MAX_DAILY_LOSS", "500")),
            allowed_start=os.environ.get(
                "TRADERIA_DEMO_ALLOWED_START",
                "00:00",
            ),
            allowed_end=os.environ.get("TRADERIA_DEMO_ALLOWED_END", "23:59"),
        )

    def _demo_robot_view_model(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
        status: str,
        message: str,
        result_status: str,
        result_message: str,
        entry_price: float | None = None,
        stop: float | None = None,
        target: float | None = None,
        provider: str = "MT5_DEMO_DISABLED",
        mt5_order_send_enabled: bool = False,
        rejection_tree: list[DashboardDemoRobotRejectionStepViewModel] | None = None,
    ) -> DashboardDemoRobotViewModel:
        return DashboardDemoRobotViewModel(
            status=status,
            message=message,
            selected_pair=row.pair,
            timeframe=row.timeframe,
            model=row.active_model,
            decision=row.decision,
            entry_price=entry_price
            if entry_price is not None
            else row.last_price
            if row.decision in {"BUY", "SELL"}
            and status in {"EXECUTED", "REJECTED"}
            else None,
            stop=stop,
            target=target,
            result_status=result_status,
            result_message=result_message,
            provider=provider,
            real_order_enabled=False,
            mt5_order_send_enabled=mt5_order_send_enabled,
            lab_configuration=self.mt5_visual_signal_exporter._lab_configuration(row),
            market_indicators=self.mt5_visual_signal_exporter._market_indicators(row),
            active_indicators=tuple(row.active_model_indicators),
            rejection_tree=rejection_tree or [],
            audit_log=self._demo_robot_audit_rows(),
        )

    def _demo_robot_rejection_tree(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
        plan: MT5ResearchTradePlan | None,
        *,
        enabled: bool,
        mt5_order_send_enabled: bool,
        time_context: object | None = None,
        result_status: str = "",
        result_message: str = "",
    ) -> list[DashboardDemoRobotRejectionStepViewModel]:
        steps: list[DashboardDemoRobotRejectionStepViewModel] = []

        def add(stage: str, passed: bool, reason: str, detail: str = "") -> None:
            steps.append(
                DashboardDemoRobotRejectionStepViewModel(
                    order=len(steps) + 1,
                    symbol=row.pair,
                    timeframe=row.timeframe,
                    stage=stage,
                    status="APROVADO" if passed else "BLOQUEADO",
                    reason=reason,
                    detail=detail,
                )
            )

        add(
            "Kill switch demo",
            enabled,
            "Robo demo armado." if enabled else "Robo demo desarmado.",
        )
        add(
            "Envio MT5 Demo habilitado",
            mt5_order_send_enabled,
            (
                "TRADERIA_DEMO_EXECUTION_ENABLED=1."
                if mt5_order_send_enabled
                else "Variavel TRADERIA_DEMO_EXECUTION_ENABLED nao habilitada."
            ),
        )
        has_research = row.lab_configuration_source == "RESEARCH_LAB"
        add(
            "Research Constants",
            has_research,
            (
                "Configuracao veio do Research Lab."
                if has_research
                else "Sem constantes certificadas do Research Lab."
            ),
            str(row.lab_configuration_source),
        )
        add(
            "ICT informativo",
            True,
            (
                f"ICT {row.lab_ict_score:.2f} classe {row.lab_ict_grade} registrado."
                if row.lab_ict_demo_allowed
                else f"ICT {row.lab_ict_score:.2f} classe {row.lab_ict_grade} nao bloqueia Demo."
            ),
            " | ".join(row.lab_ict_rejection_reasons) or row.lab_ict_status,
        )
        signal_ok = row.decision in {"BUY", "SELL"}
        add(
            "Sinal direcional",
            signal_ok,
            (
                f"Decisao {row.decision}."
                if signal_ok
                else "Decisao WAIT; sem BUY/SELL."
            ),
        )
        entry_ok = row.theoretical_entry_status == "SINAL_TEORICO"
        add(
            "Gatilho novo",
            entry_ok,
            (
                "Transicao WAIT -> BUY/SELL detectada."
                if entry_ok
                else row.theoretical_entry_status
            ),
            row.theoretical_entry_reason,
        )
        plan_ok = plan is not None and plan.status == "PLANO_VALIDO"
        add(
            "Trade Plan",
            plan_ok,
            (
                "Plano do Research Lab esta PLANO_VALIDO."
                if plan_ok
                else f"Plano bloqueado: {getattr(plan, 'status', 'SEM_PLANO')}."
            ),
            getattr(plan, "reason", "") if plan is not None else "",
        )
        if time_context is not None:
            temporal_blocked = bool(getattr(time_context, "temporal_blocked", False))
            add(
                "Tempo",
                not temporal_blocked,
                (
                    "Sem bloqueio temporal."
                    if not temporal_blocked
                    else str(getattr(time_context, "temporal_status", "BLOQUEADO"))
                ),
                str(getattr(time_context, "temporal_reason", "")),
            )
        else:
            add("Tempo", True, "Nao avaliado ainda; depende de plano valido.")
        add(
            "Evento macro",
            True,
            "Calendario macroeconomico nao configurado; sem bloqueio ativo.",
        )
        if result_status:
            add(
                "Decision/Risk/Execution",
                result_status in {"EXECUTED", "ACCEPTED"},
                result_status,
                result_message,
            )
        return steps

    def _demo_robot_audit_rows(self) -> list[DashboardDemoRobotAuditViewModel]:
        return [
            DashboardDemoRobotAuditViewModel(
                timestamp=format_dashboard_timestamp(row.timestamp),
                symbol=row.symbol,
                side=row.side,
                quantity=row.quantity,
                accepted=row.accepted,
                status=row.status,
                message=row.message,
                ticket=row.ticket,
                alpha_id=row.alpha_id,
                alpha_version=row.alpha_version,
                technical_score=row.technical_score,
                historical_confirmation=row.historical_confirmation,
                entry_price=row.entry_price,
                stop=row.stop,
                target=row.target,
                risk_reward=row.risk_reward,
                candle_time=row.candle_time,
                mt5_position=row.mt5_position,
            )
            for row in self.demo_robot_execution_service.list_audit_log()
        ]

    def get_timeframe_optimization_results(
        self,
    ) -> list[TimeframeOptimizationResult]:
        """Retorna ranking de timeframes pela fachada do dashboard."""
        return self.mt5_market_data_service.get_timeframe_optimization_results()

    def load_timeframe_optimization_results(
        self,
        count: int | None = None,
    ) -> list[TimeframeOptimizationResult]:
        """Executa Timeframe Optimizer em modo pesquisa read-only."""
        return self.mt5_market_data_service.load_timeframe_optimization_results(
            count=count,
        )

    def get_live_research_data(self) -> LiveResearchDashboardData:
        """Retorna ultimo estado live read-only pela fachada do dashboard."""
        return self._to_live_research_dashboard_data(
            self.live_research_service.get_latest_data()
        )

    def list_live_research_history(self) -> list[LiveResearchHistoryRow]:
        """Lista historico live read-only pela fachada do dashboard."""
        return self._to_live_research_history_rows(
            self.live_research_service.list_snapshot_history()
        )

    def get_live_research_session_summary(
        self,
    ) -> LiveResearchSessionSummaryData:
        """Retorna resumo estatistico live read-only pela fachada."""
        return self._to_live_research_session_summary_data(
            self.live_research_service.get_session_summary()
        )

    def list_live_research_signal_quality(
        self,
    ) -> list[LiveResearchSignalQualityRow]:
        """Lista qualidade dos sinais live pela fachada do dashboard."""
        return self._to_live_research_signal_quality_rows(
            self.live_research_service.list_signal_quality()
        )

    def list_live_experiment_signals(self) -> list[LiveExperimentSignalData]:
        """Lista sinais do experimento live via Research Lab."""
        return self.research_lab_service.list_live_experiment_signals()

    def get_live_experiment_summary(self) -> LiveExperimentSummaryData:
        """Retorna resumo do experimento live via Research Lab."""
        return self.research_lab_service.live_experiment_summary()

    def _to_view_model_system_status(
        self,
        data: DashboardData,
    ) -> DashboardSystemStatusViewModel:
        status = data.system_status
        return DashboardSystemStatusViewModel(
            status=str(getattr(status, "status", "N/D")),
            active_symbol=str(getattr(status, "active_symbol", "N/D")),
            version=str(getattr(status, "version", "N/D")),
            event_count=int(getattr(status, "event_count", 0) or 0),
            loaded_strategies_count=int(
                getattr(status, "loaded_strategies_count", 0) or 0
            ),
        )

    def _to_view_model_replay_status(
        self,
        data: DashboardData,
    ) -> DashboardReplayStatusViewModel:
        replay = data.replay_data
        signal = getattr(replay, "strategy_signal", None)
        return DashboardReplayStatusViewModel(
            status=str(getattr(replay, "status", "N/D")),
            total_candles=int(getattr(replay, "total_candles", 0) or 0),
            current_index=int(getattr(replay, "current_index", -1) or -1),
            active_strategy_name=str(
                getattr(replay, "active_strategy_name", "N/D")
            ),
            active_strategy_label=str(
                getattr(replay, "active_strategy_label", "N/D")
            ),
            last_decision=str(getattr(signal, "decision", "N/D")),
            is_running=bool(getattr(replay, "is_running", False)),
        )

    def _to_view_model_live_status(
        self,
        data: DashboardData,
    ) -> DashboardLiveResearchStatusViewModel:
        live = data.live_research_data
        return DashboardLiveResearchStatusViewModel(
            symbol=live.symbol,
            timeframe=live.timeframe,
            candles_ingested=live.candles_ingested,
            strategies_evaluated=live.strategies_evaluated,
            strategy_signals=live.strategy_signals,
            decision_contexts=live.decision_contexts,
            last_decision=live.last_decision,
            last_confidence=live.last_confidence,
            read_only=live.safety_status == "READ ONLY",
            has_data=live.has_data,
        )

    def _to_view_model_live_summary(
        self,
        data: DashboardData,
    ) -> DashboardLiveSessionSummaryViewModel:
        summary = data.live_research_data.session_summary
        return DashboardLiveSessionSummaryViewModel(
            total_snapshots=summary.total_snapshots,
            buy_count=summary.buy_count,
            sell_count=summary.sell_count,
            wait_count=summary.wait_count,
            average_confidence=summary.average_confidence,
            highest_confidence=summary.highest_confidence,
            lowest_confidence=summary.lowest_confidence,
            last_decision=summary.last_decision,
            last_timestamp=summary.last_timestamp,
        )

    def _to_view_model_signal_quality(
        self,
        data: DashboardData,
    ) -> list[DashboardLiveSignalQualityViewModel]:
        return [
            DashboardLiveSignalQualityViewModel(
                strategy_name=row.strategy_name,
                signal_count=row.signal_count,
                buy_count=row.buy_count,
                sell_count=row.sell_count,
                wait_count=row.wait_count,
                average_confidence=row.average_confidence,
                last_decision=row.last_decision,
            )
            for row in data.live_research_data.signal_quality
        ]

    def _to_view_model_live_history(
        self,
        data: DashboardData,
    ) -> list[DashboardLiveHistoryViewModel]:
        return [
            DashboardLiveHistoryViewModel(
                timestamp=row.timestamp,
                symbol=row.symbol,
                timeframe=row.timeframe,
                decision=row.decision,
                confidence=row.confidence,
                strategy_signals=row.strategy_signals,
                decision_contexts=row.decision_contexts,
            )
            for row in data.live_research_data.history
        ]

    def _to_view_model_research_status(
        self,
        data: DashboardData,
    ) -> DashboardResearchStatusViewModel:
        last = data.last_research_experiment
        return DashboardResearchStatusViewModel(
            experiments_count=len(data.research_lab_experiments),
            benchmarks_count=len(data.research_benchmarks),
            validations_count=len(data.benchmark_validations),
            last_experiment_name=str(
                getattr(last, "experiment_name", "N/D")
                if last is not None
                else "N/D"
            ),
            live_signals_count=data.live_experiment_summary.total_signals,
        )

    def _to_view_model_safety_status(
        self,
        data: DashboardData,
    ) -> DashboardSafetyStatusViewModel:
        alpha_status = data.alpha001_status
        return DashboardSafetyStatusViewModel(
            status="READ ONLY",
            read_only=True,
            real_trading_authorized=bool(
                getattr(alpha_status, "real_trading_authorized", False)
            ),
            broker_integrated=bool(
                getattr(alpha_status, "broker_mt5_integrated", False)
            ),
            order_execution_enabled=False,
        )

    def _to_view_model_mt5_market_data(
        self,
        data: DashboardData,
    ) -> DashboardMT5MarketDataViewModel:
        mt5_data = data.mt5_market_data
        return DashboardMT5MarketDataViewModel(
            connection_status=mt5_data.connection_status,
            server=mt5_data.server,
            account=mt5_data.account,
            account_type=mt5_data.account_type,
            available_symbols=list(mt5_data.available_symbols),
            supported_symbols=list(mt5_data.supported_symbols),
            selected_symbol=mt5_data.selected_symbol,
            supported_timeframes=list(mt5_data.supported_timeframes),
            selected_timeframe=mt5_data.selected_timeframe,
            candles_loaded=mt5_data.candles_loaded,
            last_candle=self._to_view_model_mt5_candle(mt5_data.last_candle),
            candles=[
                self._to_view_model_mt5_candle(candle)
                for candle in mt5_data.candles
                if self._to_view_model_mt5_candle(candle) is not None
            ],
            message=mt5_data.message,
            read_only_status=mt5_data.read_only_status,
            real_operation_authorized=mt5_data.real_operation_authorized,
        )

    def _to_view_model_mt5_candle(
        self,
        candle: object | None,
    ) -> DashboardMT5CandleViewModel | None:
        if candle is None:
            return None
        return DashboardMT5CandleViewModel(
            timestamp=format_dashboard_timestamp(getattr(candle, "timestamp", "N/D")),
            open=float(getattr(candle, "open", 0.0)),
            high=float(getattr(candle, "high", 0.0)),
            low=float(getattr(candle, "low", 0.0)),
            close=float(getattr(candle, "close", 0.0)),
            volume=int(getattr(candle, "volume", 0) or 0),
        )

    def _to_view_model_mt5_forex_signals(
        self,
        data: DashboardData,
        research: DashboardMT5HeuristicResearchViewModel | None = None,
    ) -> DashboardMT5ForexSignalViewModel:
        forex = (
            data.mt5_forex_signals
            if hasattr(data, "mt5_forex_signals")
            else data
        )
        active_models = self._active_mt5_research_models_by_market(research)
        active_research_rows = self._active_mt5_research_rows_by_market(research)
        return DashboardMT5ForexSignalViewModel(
            connection_status=forex.connection_status,
            server=forex.server,
            account=forex.account,
            account_type=forex.account_type,
            timeframe=forex.timeframe,
            pairs=[
                self._to_view_model_mt5_forex_signal_row(
                    row,
                    self._active_mt5_research_model_for_row(
                        row,
                        active_models,
                        research,
                    ),
                    self._active_mt5_research_row_for_source_row(
                        row,
                        active_research_rows,
                    ),
                )
                for row in forex.pairs
            ],
            available_pairs=list(forex.available_pairs),
            unavailable_pairs=list(forex.unavailable_pairs),
            message=forex.message,
            read_only_status=forex.read_only_status,
            real_operation_authorized=forex.real_operation_authorized,
            connection_health=forex.connection_health,
            connection_health_icon=forex.connection_health_icon,
            last_update=format_dashboard_timestamp(forex.last_update),
            last_mt5_read=format_dashboard_timestamp(forex.last_mt5_read),
            last_candle_time=format_dashboard_timestamp(forex.last_candle_time),
            refresh_id=forex.refresh_id,
            seconds_since_update=forex.seconds_since_update,
            health_message=forex.health_message,
            last_research_update=forex.last_research_update,
            research_cache_status=forex.research_cache_status,
            fast_refresh_duration_ms=forex.fast_refresh_duration_ms,
            research_refresh_duration_ms=forex.research_refresh_duration_ms,
            latency_breakdown=dict(forex.latency_breakdown),
            connection_diagnostic=self._to_view_model_mt5_connection_diagnostic(
                forex.connection_diagnostic
            ),
            mt5_safe_mode=bool(getattr(forex, "mt5_safe_mode", True)),
            safe_mode_message=str(getattr(forex, "safe_mode_message", "")),
            safe_mode_source=str(
                getattr(forex, "safe_mode_source", "MT5_SAFE_MODE")
            ),
            safe_mode_status=str(getattr(forex, "safe_mode_status", "OFFLINE")),
            safe_mode_received_candles=int(
                getattr(forex, "safe_mode_received_candles", 0) or 0
            ),
            safe_mode_last_price=getattr(forex, "safe_mode_last_price", None),
            safe_mode_error=str(getattr(forex, "safe_mode_error", "")),
        )

    def _to_view_model_mt5_forex_signal_row(
        self,
        row: object,
        active_model: str,
        active_research_row: object | None = None,
    ) -> DashboardMT5ForexSignalRowViewModel:
        lab_parameters = self._lab_parameters_from_research_row(active_research_row)
        lab_ict_score = float(getattr(active_research_row, "ict_score", 0.0) or 0.0)
        lab_ict_grade = str(getattr(active_research_row, "ict_grade", "E") or "E")
        lab_ict_status = str(
            getattr(active_research_row, "ict_status", "REJEITADA") or "REJEITADA"
        )
        lab_ict_usage = str(
            getattr(active_research_row, "ict_usage", "Rejeitada.") or "Rejeitada."
        )
        lab_ict_demo_allowed = bool(
            getattr(active_research_row, "ict_demo_allowed", False)
        )
        lab_ict_rejection_reasons = tuple(
            getattr(active_research_row, "ict_rejection_reasons", ()) or ()
        )
        lab_timeframe = str(
            getattr(
                active_research_row,
                "ideal_timeframe",
                getattr(active_research_row, "timeframe", getattr(row, "timeframe", "M1")),
            )
            or getattr(row, "timeframe", "M1")
        )
        execution_timeframe = lab_timeframe or str(getattr(row, "timeframe", "M1"))
        analysis_row = self._latest_mt5_forex_row_for_timeframe(
            row,
            execution_timeframe,
        )
        candidate = self._active_model_candidate(
            analysis_row,
            active_model,
            lab_parameters,
        )
        decision = str(candidate["decision"])
        confidence = float(candidate["score"])
        reason = f"{active_model}: {candidate['reason']}"
        theoretical_entry = self._theoretical_entry_for_row(
            analysis_row,
            active_model,
            lab_parameters,
        )
        research_plan = self._mt5_research_trade_plan_for_data(
            symbol=str(getattr(row, "pair", "N/D")),
            timeframe=execution_timeframe,
            decision=decision,
            active_model=active_model,
            entry_status=str(theoretical_entry["status"]),
            entry_price=theoretical_entry["price"],
            atr=getattr(analysis_row, "atr", None),
            reason=reason,
            lab_parameters=lab_parameters,
            certification_demo_allowed=lab_ict_demo_allowed,
            certification_score=lab_ict_score,
            certification_grade=lab_ict_grade,
            certification_status=lab_ict_status,
            certification_usage=lab_ict_usage,
            certification_rejection_reasons=lab_ict_rejection_reasons,
        )
        dynamic_exit = self._mt5_dynamic_exit_recommendation(
            analysis_row,
            research_plan,
        )
        return DashboardMT5ForexSignalRowViewModel(
            pair=row.pair,
            status=analysis_row.status,
            last_price=analysis_row.last_price,
            last_candle_time=format_dashboard_timestamp(analysis_row.last_candle_time),
            trend=analysis_row.trend,
            momentum=analysis_row.momentum,
            volatility=analysis_row.volatility,
            rsi=analysis_row.rsi,
            short_average=analysis_row.short_average,
            long_average=analysis_row.long_average,
            active_model=active_model,
            active_model_score=confidence,
            active_model_indicators=self._active_model_indicators(
                analysis_row,
                active_model,
                lab_parameters,
            ),
            lab_alpha_id=str(lab_parameters.get("alpha", "ALPHA001")),
            lab_timeframe=lab_timeframe,
            lab_parameters=lab_parameters,
            lab_configuration_source=(
                "RESEARCH_LAB"
                if active_research_row is not None and lab_parameters
                else "DEFAULT"
            ),
            decision=decision,
            confidence=confidence,
            lab_confidence=float(getattr(active_research_row, "confidence", 0.0) or 0.0),
            lab_ict_score=lab_ict_score,
            lab_ict_grade=lab_ict_grade,
            lab_ict_status=lab_ict_status,
            lab_ict_usage=lab_ict_usage,
            lab_ict_demo_allowed=lab_ict_demo_allowed,
            lab_ict_rejection_reasons=lab_ict_rejection_reasons,
            reason=reason,
            mid_average=getattr(analysis_row, "mid_average", None),
            ema_fast=getattr(analysis_row, "ema_fast", None),
            ema_mid=getattr(analysis_row, "ema_mid", None),
            ema_slow=getattr(analysis_row, "ema_slow", None),
            adx=getattr(analysis_row, "adx", None),
            macd=getattr(analysis_row, "macd", None),
            macd_signal=getattr(analysis_row, "macd_signal", None),
            atr=getattr(analysis_row, "atr", None),
            atr_average=getattr(analysis_row, "atr_average", None),
            bollinger_upper=getattr(analysis_row, "bollinger_upper", None),
            bollinger_lower=getattr(analysis_row, "bollinger_lower", None),
            tick_volume=getattr(analysis_row, "tick_volume", None),
            tick_volume_average=getattr(analysis_row, "tick_volume_average", None),
            day_high=getattr(analysis_row, "day_high", None),
            day_low=getattr(analysis_row, "day_low", None),
            donchian_high=getattr(analysis_row, "donchian_high", None),
            donchian_low=getattr(analysis_row, "donchian_low", None),
            pivot=getattr(analysis_row, "pivot", None),
            vwap=getattr(analysis_row, "vwap", None),
            z_score=getattr(analysis_row, "z_score", None),
            support=getattr(analysis_row, "support", None),
            resistance=getattr(analysis_row, "resistance", None),
            swing_high=getattr(analysis_row, "swing_high", None),
            swing_low=getattr(analysis_row, "swing_low", None),
            spread=getattr(analysis_row, "spread", None),
            spread_average=getattr(analysis_row, "spread_average", None),
            slippage_estimate=getattr(analysis_row, "slippage_estimate", None),
            price_speed=getattr(analysis_row, "price_speed", None),
            candles_loaded=analysis_row.candles_loaded,
            sample_size=analysis_row.sample_size,
            win_rate=analysis_row.win_rate,
            avg_return=analysis_row.avg_return,
            profit_factor=analysis_row.profit_factor,
            max_drawdown=analysis_row.max_drawdown,
            matched_context_count=analysis_row.matched_context_count,
            rejected_reason=analysis_row.rejected_reason,
            volatility_bucket=analysis_row.volatility_bucket,
            rsi_bucket=analysis_row.rsi_bucket,
            momentum_sign=analysis_row.momentum_sign,
            ma_distance_bucket=analysis_row.ma_distance_bucket,
            confidence_penalties=tuple(analysis_row.confidence_penalties),
            confidence_drivers=tuple(analysis_row.confidence_drivers),
            timeframe=analysis_row.timeframe,
            configured_candles=analysis_row.configured_candles,
            requested_candles=analysis_row.requested_candles,
            received_candles=analysis_row.received_candles,
            research_candles_used=analysis_row.research_candles_used,
            last_update=format_dashboard_timestamp(analysis_row.last_update),
            diagnostics_status=analysis_row.diagnostics_status,
            diagnostics_log=analysis_row.diagnostics_log,
            theoretical_entry_status=theoretical_entry["status"],
            theoretical_entry_candle=format_dashboard_timestamp(
                theoretical_entry["candle"]
            ),
            theoretical_entry_price=theoretical_entry["price"],
            theoretical_entry_direction=theoretical_entry["direction"],
            theoretical_entry_reason=theoretical_entry["reason"],
            research_plan_status=research_plan.status,
            research_plan_source=research_plan.source,
            research_plan_entry_price=research_plan.entry_price,
            research_plan_stop=research_plan.stop,
            research_plan_target=research_plan.target,
            research_plan_risk_reward=research_plan.risk_reward,
            research_plan_stop_multiplier=research_plan.stop_multiplier,
            research_plan_exit_model=research_plan.exit_model,
            research_plan_exit_score=research_plan.exit_score,
            research_plan_exit_candidates=research_plan.exit_candidates,
            research_plan_risk_pips=research_plan.risk_pips,
            research_plan_reward_pips=research_plan.reward_pips,
            research_plan_risk_percent=research_plan.risk_percent,
            research_plan_reward_percent=research_plan.reward_percent,
            research_plan_stop_reason=research_plan.stop_reason,
            research_plan_target_reason=research_plan.target_reason,
            research_plan_stop_management=research_plan.stop_management,
            research_plan_stop_management_parameters=dict(
                research_plan.stop_management_parameters
            ),
            research_plan_stop_management_reason=research_plan.stop_management_reason,
            dynamic_exit_policy=dynamic_exit.policy,
            dynamic_exit_action=dynamic_exit.action,
            dynamic_exit_reason=dynamic_exit.reason,
            dynamic_exit_confidence=dynamic_exit.confidence,
            dynamic_exit_market_state=dynamic_exit.market_state,
            dynamic_exit_r_multiple=dynamic_exit.r_multiple,
            dynamic_exit_candidate_stop=dynamic_exit.candidate_stop,
            dynamic_exit_allowed_to_execute_demo=(
                dynamic_exit.allowed_to_execute_demo
            ),
            dynamic_exit_source=dynamic_exit.source,
            research_plan_reason=research_plan.reason,
            research_plan_invalid_reason=research_plan.invalid_reason,
            research_plan_invalid_fields=research_plan.invalid_fields,
            research_plan_next_retry=research_plan.next_retry,
            research_plan_expected_trigger=research_plan.expected_trigger,
            research_plan_rr_current=research_plan.rr_current,
            research_plan_rr_minimum=research_plan.rr_minimum,
            research_plan_diagnostics=research_plan.diagnostics,
        )

    def _mt5_dynamic_exit_recommendation(
        self,
        row: object,
        research_plan: object,
    ) -> DynamicExitRecommendation:
        """Cria recomendacao de saida dinamica sem autorizar execucao demo."""
        policy = str(getattr(research_plan, "stop_management", "FIXED_STOP") or "FIXED_STOP")
        status = str(getattr(research_plan, "status", "SEM_PLANO") or "SEM_PLANO")
        side = str(getattr(row, "decision", "WAIT") or "WAIT").upper()
        reading = _DYNAMIC_EXIT_MARKET_STATE_CLASSIFIER.classify(
            DynamicExitMarketReading(
                symbol=str(getattr(row, "pair", "N/D") or "N/D"),
                side=side,
                is_positioned=status == "PLANO_VALIDO" and side in {"BUY", "SELL"},
                current_price=self._optional_float(getattr(row, "last_price", None)),
                entry_price=self._optional_float(
                    getattr(research_plan, "entry_price", None)
                ),
                stop_price=self._optional_float(getattr(research_plan, "stop", None)),
                target_price=self._optional_float(
                    getattr(research_plan, "target", None)
                ),
                atr=self._optional_float(getattr(row, "atr", None)),
                volatility=self._optional_float(getattr(row, "volatility", None)),
                momentum=self._optional_float(getattr(row, "momentum", None)),
                spread=self._optional_float(getattr(row, "spread", None)),
            )
        )
        if status != "PLANO_VALIDO":
            reading = DynamicExitMarketReading(
                symbol=reading.symbol,
                side=reading.side,
                is_positioned=reading.is_positioned,
                current_price=reading.current_price,
                entry_price=reading.entry_price,
                stop_price=reading.stop_price,
                target_price=reading.target_price,
                atr=reading.atr,
                volatility=reading.volatility,
                momentum=reading.momentum,
                spread=reading.spread,
                time_in_position_minutes=reading.time_in_position_minutes,
                state="BAD_EXECUTION_CONTEXT",
                r_multiple=reading.r_multiple,
                reason="Plano invalido ou ausente; saida dinamica mantida apenas em auditoria.",
                candidate_stop=reading.candidate_stop,
            )
        return _DYNAMIC_EXIT_RECOMMENDATION_ENGINE.recommend(
            reading,
            policy=policy,
            plan_status=status,
        )

    def _latest_mt5_forex_row_for_timeframe(
        self,
        row: object,
        timeframe: str,
    ) -> object:
        """Recalcula a linha Forex no timeframe do Lab, buscando se o cache faltar."""
        symbol = str(getattr(row, "pair", ""))
        normalized_timeframe = str(timeframe or getattr(row, "timeframe", "M1"))
        candles = self._latest_mt5_forex_candles(symbol, normalized_timeframe)
        if not candles:
            candles = self._load_mt5_forex_candles_for_view_row(
                symbol,
                normalized_timeframe,
                row,
            )
        if not candles:
            return row
        configuration = self.mt5_market_data_service._mt5_safe_mode_configuration(
            self.configuration_service.get_configuration_data()
        )
        uses_external_process = bool(
            self.mt5_market_data_service._provider_uses_external_mt5_process()
        )
        return self.mt5_market_data_service._analyze_pair(
            symbol,
            candles,
            configuration,
            microstructure=(
                {}
                if uses_external_process
                else self.mt5_market_data_service._symbol_microstructure(symbol)
            ),
            timeframe=normalized_timeframe,
            configured_candles=int(getattr(row, "configured_candles", 0) or 0),
            requested_candles=int(getattr(row, "requested_candles", 0) or 0),
            last_update=str(getattr(row, "last_update", "")),
            recalculate_research=False,
        )

    def _load_mt5_forex_candles_for_view_row(
        self,
        symbol: str,
        timeframe: str,
        row: object,
    ) -> list[object]:
        """Preenche cache ausente para evitar linha M1 exibida como timeframe do Lab."""
        if not symbol:
            return []
        try:
            timeframe_value = self.mt5_market_data_service._timeframe_value(timeframe)
            configuration = self.mt5_market_data_service._mt5_safe_mode_configuration(
                self.configuration_service.get_configuration_data()
            )
            requested = int(getattr(row, "requested_candles", 0) or 0)
            count = requested if requested > 0 else int(configuration.candles_loaded)
            count = max(configuration.slow_ma_period + 1, count)
            candles = list(
                self.mt5_market_data_service.provider.get_candles(
                    symbol,
                    timeframe_value,
                    count,
                )
            )
        except Exception:  # noqa: BLE001 - fallback visual nao deve quebrar dashboard
            return []
        self.mt5_market_data_service.latest_forex_candles[(symbol, timeframe)] = candles
        return candles

    def _mt5_research_trade_plan_for_view_row(
        self,
        row: DashboardMT5ForexSignalRowViewModel,
    ) -> MT5ResearchTradePlan:
        return self._mt5_research_trade_plan_for_data(
            symbol=row.pair,
            timeframe=row.lab_timeframe or row.timeframe,
            decision=row.decision,
            active_model=row.active_model,
            entry_status=row.theoretical_entry_status,
            entry_price=row.theoretical_entry_price,
            atr=row.atr,
            reason=row.theoretical_entry_reason,
            lab_parameters=row.lab_parameters,
            certification_demo_allowed=row.lab_ict_demo_allowed,
            certification_score=row.lab_ict_score,
            certification_grade=row.lab_ict_grade,
            certification_status=row.lab_ict_status,
            certification_usage=row.lab_ict_usage,
            certification_rejection_reasons=row.lab_ict_rejection_reasons,
        )

    def _mt5_research_trade_plan_for_data(
        self,
        *,
        symbol: str,
        timeframe: str,
        decision: str,
        active_model: str,
        entry_status: str,
        entry_price: object,
        atr: object,
        reason: str,
        lab_parameters: dict[str, str] | None = None,
        certification_demo_allowed: bool = True,
        certification_score: float = 100.0,
        certification_grade: str = "A+",
        certification_status: str = "CERTIFICADA_A_PLUS",
        certification_usage: str = "Operacao automatica Demo liberada.",
        certification_rejection_reasons: tuple[str, ...] = (),
    ) -> MT5ResearchTradePlan:
        return self.mt5_research_trade_plan_engine.build_plan(
            MT5ResearchTradePlanInput(
                symbol=symbol,
                timeframe=timeframe,
                decision=decision,
                entry_signal_status=entry_status,
                entry_price=self._optional_float(entry_price),
                atr=self._optional_float(atr),
                active_model=active_model,
                reason=reason,
                atr_stop_factor=self._optional_float(
                    (lab_parameters or {}).get("atr_stop_factor")
                ),
                research_risk_reward=self._optional_float(
                    (lab_parameters or {}).get("rr")
                ),
                stop_management=str(
                    (lab_parameters or {}).get("stop_management", "FIXED_STOP")
                ),
                stop_management_parameters=dict(lab_parameters or {}),
                certification_demo_allowed=certification_demo_allowed,
                certification_score=certification_score,
                certification_grade=certification_grade,
                certification_status=certification_status,
                certification_usage=certification_usage,
                certification_rejection_reasons=certification_rejection_reasons,
            )
        )

    def _active_mt5_research_model(
        self,
        research: DashboardMT5HeuristicResearchViewModel | None,
    ) -> str:
        if research is None:
            return "TREND_MOMENTUM"
        model = str(getattr(research, "best_heuristic", "") or "")
        if model in self._mt5_supported_research_models():
            return model
        return "TREND_MOMENTUM"

    def _active_mt5_research_models_by_market(
        self,
        research: DashboardMT5HeuristicResearchViewModel | None,
    ) -> dict[tuple[str, str], str]:
        if research is None:
            return {}
        models: dict[tuple[str, str], str] = {}
        for row in list(getattr(research, "rows", []) or []):
            pair = str(getattr(row, "pair", "") or "").upper()
            timeframe = self._research_row_winner_timeframe(row)
            model = str(getattr(row, "recommended_heuristic", "") or "")
            if not pair or model not in self._mt5_supported_research_models():
                continue
            models[(pair, timeframe)] = model
            models.setdefault((pair, ""), model)
        return models

    def _active_mt5_research_rows_by_market(
        self,
        research: DashboardMT5HeuristicResearchViewModel | None,
    ) -> dict[tuple[str, str], object]:
        if research is None:
            return {}
        rows: dict[tuple[str, str], object] = {}
        for row in list(getattr(research, "rows", []) or []):
            pair = str(getattr(row, "pair", "") or "").upper()
            timeframe = self._research_row_winner_timeframe(row)
            model = str(getattr(row, "recommended_heuristic", "") or "")
            if not pair or model not in self._mt5_supported_research_models():
                continue
            rows[(pair, timeframe)] = row
            rows.setdefault((pair, ""), row)
        return rows

    def _research_row_winner_timeframe(self, row: object) -> str:
        """Retorna o timeframe vencedor definido pelo Lab para uma linha."""
        configuration = dict(getattr(row, "final_configuration", {}) or {})
        return str(
            configuration.get(
                "timeframe",
                getattr(row, "ideal_timeframe", getattr(row, "timeframe", "")),
            )
            or ""
        ).upper()

    def _active_mt5_research_row_for_source_row(
        self,
        row: object,
        active_rows: dict[tuple[str, str], object],
    ) -> object | None:
        pair = str(getattr(row, "pair", "") or "").upper()
        timeframe = str(getattr(row, "timeframe", "") or "").upper()
        return active_rows.get((pair, timeframe)) or active_rows.get((pair, ""))

    def _active_mt5_research_model_for_row(
        self,
        row: object,
        active_models: dict[tuple[str, str], str],
        research: DashboardMT5HeuristicResearchViewModel | None,
    ) -> str:
        pair = str(getattr(row, "pair", "") or "").upper()
        timeframe = str(getattr(row, "timeframe", "") or "").upper()
        return (
            active_models.get((pair, timeframe))
            or active_models.get((pair, ""))
            or self._active_mt5_research_model(research)
        )

    def _active_model_candidate(
        self,
        row: object,
        active_model: str,
        parameters: dict[str, str] | None = None,
    ) -> dict[str, object]:
        if str(getattr(row, "status", "")).upper() != "OK":
            return {
                "heuristic": active_model,
                "decision": "WAIT",
                "score": 0.0,
                "reason": str(getattr(row, "reason", "Par sem dados MT5.")),
            }
        if parameters:
            return self._mt5_parameterized_candidate(row, active_model, parameters)
        if active_model == "MA_RSI_FILTER":
            return self._ma_rsi_candidate(row)
        if active_model == "RSI_REVERSAL":
            return self._rsi_reversal_candidate(row)
        return self._trend_momentum_candidate(row)

    def _active_model_indicators(
        self,
        row: object,
        active_model: str,
        parameters: dict[str, str] | None = None,
    ) -> tuple[str, ...]:
        if parameters:
            return tuple(
                f"{key}={value}"
                for key, value in parameters.items()
                if key not in {"alpha", "modelo", "timeframe"}
            )
        if active_model == "MA_RSI_FILTER":
            return (
                f"Media curta={self._format_optional_float(getattr(row, 'short_average', None))}",
                f"Media longa={self._format_optional_float(getattr(row, 'long_average', None))}",
                f"RSI={self._format_optional_float(getattr(row, 'rsi', None), 2)}",
            )
        if active_model == "RSI_REVERSAL":
            return (
                f"RSI={self._format_optional_float(getattr(row, 'rsi', None), 2)}",
            )
        return (
            f"Tendencia={getattr(row, 'trend', 'N/D')}",
            f"Momentum={self._format_optional_percent(getattr(row, 'momentum', None))}",
            f"Volatilidade={self._format_optional_percent(getattr(row, 'volatility', None))}",
        )

    def _lab_parameters_from_research_row(
        self,
        active_research_row: object | None,
    ) -> dict[str, str]:
        if active_research_row is None:
            return {}
        parameters = dict(getattr(active_research_row, "final_configuration", {}) or {})
        model = str(
            parameters.get(
                "modelo",
                getattr(active_research_row, "recommended_heuristic", ""),
            )
            or ""
        )
        if model:
            parameters["modelo"] = model
        timeframe = str(
            parameters.get(
                "timeframe",
                getattr(active_research_row, "ideal_timeframe", ""),
            )
            or ""
        )
        if timeframe:
            parameters["timeframe"] = timeframe
        if (
            "stop_management" not in parameters
            and str(parameters.get("atr_stop_factor", "")).strip()
        ):
            parameters["stop_management"] = "ATR_TRAILING_STOP"
            parameters.setdefault(
                "atr_trailing_factor",
                str(parameters.get("atr_stop_factor", "2.0")),
            )
            parameters.setdefault("atr_trailing_activation_rr", "1.0")
        return {str(key): str(value) for key, value in parameters.items()}

    def _mt5_supported_research_models(self) -> set[str]:
        return {
            "TREND_MOMENTUM",
            "MA_RSI_FILTER",
            "RSI_REVERSAL",
            "TREND_PULLBACK",
            "BREAKOUT_CONSOLIDATION",
            "DONCHIAN_BREAKOUT",
            "ADX_TREND_STRENGTH",
            "MACD_MOMENTUM_SHIFT",
            "BOLLINGER_VOLATILITY_EXPANSION",
            "ATR_VOLATILITY_REGIME",
            "DONCHIAN_STRUCTURE_BREAKOUT",
            "PIVOT_REJECTION",
            "VWAP_MEAN_REVERSION",
            "SUPPORT_RESISTANCE_REACTION",
            "MULTI_TIMEFRAME_ALIGNMENT",
            "LIQUIDITY_SPREAD_FILTER",
        }

    def _theoretical_entry_for_row(
        self,
        row: object,
        active_model: str,
        parameters: dict[str, str] | None = None,
    ) -> dict[str, object]:
        pair = str(getattr(row, "pair", "") or "")
        timeframe = str(getattr(row, "timeframe", "") or "")
        candles = self._latest_mt5_forex_candles(pair, timeframe)
        if not candles:
            return {
                "status": "SEM_DADOS",
                "candle": "N/D",
                "price": None,
                "direction": "WAIT",
                "reason": "Candles MT5 nao disponiveis em memoria.",
            }
        trigger = self._current_zone_entry_trigger(
            row,
            candles,
            active_model,
            parameters,
        )
        if trigger is None:
            return {
                "status": "FORA_DA_ZONA_DE_INTERESSE",
                "candle": "N/D",
                "price": None,
                "direction": "WAIT",
                "reason": (
                    "Modelo ativo sem entrada autorizada na zona de interesse. "
                    f"Zona atual: {self._mt5_zone_context(row)}."
                ),
            }
        return trigger

    def _current_zone_entry_trigger(
        self,
        row: object,
        candles: list[object],
        active_model: str,
        parameters: dict[str, str] | None = None,
    ) -> dict[str, object] | None:
        candidate = self._active_model_candidate(row, active_model, parameters)
        decision = str(candidate.get("decision", "WAIT")).upper()
        if decision not in {"BUY", "SELL"}:
            return None
        zone_label = self._mt5_zone_label_for_direction(row, decision)
        if not self._mt5_zone_allows_direction(zone_label, decision):
            return None
        candle = candles[-1]
        price = self._optional_float(getattr(row, "last_price", None))
        if price is None or price <= 0:
            price = self._optional_float(getattr(candle, "fechamento", None))
        if price is None or price <= 0:
            return None
        return {
            "status": "SINAL_TEORICO",
            "candle": str(getattr(candle, "data", "N/D")),
            "price": price,
            "direction": decision,
            "reason": (
                f"{active_model}: entrada {decision} na zona de interesse "
                f"{zone_label}. {candidate.get('reason', '')}"
            ),
        }

    def _mt5_zone_allows_direction(self, zone_label: str, decision: str) -> bool:
        zone = str(zone_label or "").upper()
        direction = str(decision or "").upper()
        if zone in {"PIVO", "ZONA DE VALOR"} and direction in {"BUY", "SELL"}:
            return True
        if direction == "BUY":
            return zone == "SUPORTE"
        if direction == "SELL":
            return zone == "RESISTENCIA"
        return False

    def _mt5_zone_label_for_direction(self, row: object, decision: str) -> str:
        direction = str(decision or "").upper()
        price = self._optional_float(getattr(row, "last_price", None))
        support = self._optional_float(getattr(row, "support", None))
        resistance = self._optional_float(getattr(row, "resistance", None))
        pivot = self._optional_float(getattr(row, "pivot", None))
        atr = self._optional_float(getattr(row, "atr", None)) or 0.0
        if price is None or price <= 0:
            return "SEM PRECO"
        tolerance = max(atr * 1.5, abs(price) * 0.003)
        near_support = support is not None and abs(price - support) <= tolerance
        near_resistance = (
            resistance is not None and abs(price - resistance) <= tolerance
        )
        if direction == "BUY" and near_support:
            return "SUPORTE"
        if direction == "SELL" and near_resistance:
            return "RESISTENCIA"
        if pivot is not None and abs(price - pivot) <= tolerance:
            return "PIVO"
        if near_support:
            return "SUPORTE"
        if near_resistance:
            return "RESISTENCIA"
        return self._mt5_zone_label(row)

    def _mt5_zone_label(self, row: object) -> str:
        price = self._optional_float(getattr(row, "last_price", None))
        support = self._optional_float(getattr(row, "support", None))
        resistance = self._optional_float(getattr(row, "resistance", None))
        pivot = self._optional_float(getattr(row, "pivot", None))
        atr = self._optional_float(getattr(row, "atr", None)) or 0.0
        ema_mid = self._optional_float(getattr(row, "ema_mid", None))
        mid_average = self._optional_float(getattr(row, "mid_average", None))
        if price is None or price <= 0:
            return "SEM PRECO"
        tolerance = max(atr * 1.5, abs(price) * 0.003)
        if support is not None and abs(price - support) <= tolerance:
            return "SUPORTE"
        if resistance is not None and abs(price - resistance) <= tolerance:
            return "RESISTENCIA"
        if pivot is not None and abs(price - pivot) <= tolerance:
            return "PIVO"
        anchor = ema_mid if ema_mid is not None else mid_average
        value_tolerance = max(atr * 5.0, abs(price) * 0.02)
        if anchor is not None and abs(price - anchor) <= value_tolerance:
            return "ZONA DE VALOR"
        if support is not None and resistance is not None and support < price < resistance:
            return "MEIO DO RANGE"
        return "FORA DA ZONA"

    def _mt5_zone_context(self, row: object) -> str:
        label = self._mt5_zone_label(row)
        support = self._optional_float(getattr(row, "support", None))
        resistance = self._optional_float(getattr(row, "resistance", None))
        pivot = self._optional_float(getattr(row, "pivot", None))
        return (
            f"{label} | suporte={self._format_optional_float(support)} "
            f"resistencia={self._format_optional_float(resistance)} "
            f"pivot={self._format_optional_float(pivot)}"
        )

    def _latest_mt5_forex_candles(
        self,
        pair: str,
        timeframe: str,
    ) -> list[object]:
        candles_by_market = getattr(
            self.mt5_market_data_service,
            "latest_forex_candles",
            {},
        )
        if not isinstance(candles_by_market, dict):
            return []
        normalized_pair = pair.upper()
        normalized_timeframe = timeframe.upper()
        return list(
            candles_by_market.get((normalized_pair, normalized_timeframe))
            or candles_by_market.get((normalized_pair, ""))
            or []
        )

    def _find_theoretical_entry_trigger(
        self,
        source_row: object,
        candles: list[object],
        active_model: str,
        parameters: dict[str, str] | None = None,
    ) -> dict[str, object] | None:
        minimum = self._theoretical_entry_minimum_candles(active_model)
        if len(candles) < minimum + 1:
            return None
        previous_decision = "WAIT"
        latest_trigger: dict[str, object] | None = None
        for index in range(minimum - 1, len(candles)):
            snapshot = self._theoretical_entry_snapshot(
                source_row,
                candles[: index + 1],
            )
            candidate = self._active_model_candidate(snapshot, active_model, parameters)
            decision = str(candidate.get("decision", "WAIT"))
            if previous_decision == "WAIT" and decision in {"BUY", "SELL"}:
                candle = candles[index]
                latest_trigger = {
                    "status": "SINAL_TEORICO",
                    "candle": str(getattr(candle, "data", "N/D")),
                    "price": float(getattr(candle, "fechamento", 0.0) or 0.0),
                    "direction": decision,
                    "reason": f"{active_model}: {candidate.get('reason', '')}",
                }
            previous_decision = decision
        if latest_trigger is None:
            return None
        current = self._active_model_candidate(
            self._theoretical_entry_snapshot(source_row, candles),
            active_model,
            parameters,
        )
        previous = self._active_model_candidate(
            self._theoretical_entry_snapshot(source_row, candles[:-1]),
            active_model,
            parameters,
        )
        current_decision = str(current.get("decision", "WAIT"))
        previous_decision = str(previous.get("decision", "WAIT"))
        if previous_decision == "WAIT" and current_decision in {"BUY", "SELL"}:
            return latest_trigger
        return None

    def _theoretical_entry_minimum_candles(self, active_model: str) -> int:
        configuration = self.configuration_service.get_configuration_data()
        slow_ma = int(getattr(configuration, "quantitative_score_slow_ma_period", 21))
        feature_lookback = int(
            getattr(configuration, "quantitative_score_feature_lookback", 10)
        )
        rsi_period = int(getattr(configuration, "quantitative_score_rsi_period", 14))
        if active_model == "RSI_REVERSAL":
            return rsi_period + 1
        if active_model == "MA_RSI_FILTER":
            return max(slow_ma, rsi_period) + 1
        return max(slow_ma, feature_lookback) + 1

    def _theoretical_entry_snapshot(
        self,
        source_row: object,
        candles: list[object],
    ) -> object:
        from types import SimpleNamespace

        closes = [float(getattr(candle, "fechamento", 0.0) or 0.0) for candle in candles]
        configuration = self.configuration_service.get_configuration_data()
        fast_ma = int(getattr(configuration, "quantitative_score_fast_ma_period", 9))
        slow_ma = int(getattr(configuration, "quantitative_score_slow_ma_period", 21))
        feature_lookback = int(
            getattr(configuration, "quantitative_score_feature_lookback", 10)
        )
        volatility_period = int(
            getattr(configuration, "quantitative_score_atr_period", 14)
        )
        rsi_period = int(getattr(configuration, "quantitative_score_rsi_period", 14))
        short_average = self._mean_last(closes, fast_ma)
        long_average = self._mean_last(closes, slow_ma)
        momentum = self._momentum_last(closes, feature_lookback)
        volatility = self._volatility_last(closes, volatility_period)
        rsi = self._rsi_last(closes, rsi_period)
        market_structure = self._theoretical_entry_market_structure(candles)
        return SimpleNamespace(
            pair=getattr(source_row, "pair", "N/D"),
            timeframe=getattr(source_row, "timeframe", "H1"),
            status=getattr(source_row, "status", "OK"),
            last_price=closes[-1] if closes else getattr(source_row, "last_price", None),
            trend=self._trend_from_averages(short_average, long_average),
            momentum=momentum,
            volatility=volatility,
            rsi=rsi,
            short_average=short_average,
            long_average=long_average,
            mid_average=getattr(source_row, "mid_average", None),
            ema_fast=getattr(source_row, "ema_fast", short_average),
            ema_mid=getattr(source_row, "ema_mid", None),
            ema_slow=getattr(source_row, "ema_slow", long_average),
            adx=getattr(source_row, "adx", None),
            macd=getattr(source_row, "macd", None),
            macd_signal=getattr(source_row, "macd_signal", None),
            atr=market_structure["atr"],
            atr_average=getattr(source_row, "atr_average", None),
            bollinger_upper=getattr(source_row, "bollinger_upper", None),
            bollinger_lower=getattr(source_row, "bollinger_lower", None),
            tick_volume=getattr(source_row, "tick_volume", None),
            tick_volume_average=getattr(source_row, "tick_volume_average", None),
            day_high=market_structure["day_high"],
            day_low=market_structure["day_low"],
            donchian_high=market_structure["donchian_high"],
            donchian_low=market_structure["donchian_low"],
            pivot=market_structure["pivot"],
            vwap=market_structure["vwap"],
            z_score=market_structure["z_score"],
            support=market_structure["support"],
            resistance=market_structure["resistance"],
            swing_high=market_structure["swing_high"],
            swing_low=market_structure["swing_low"],
            spread=getattr(source_row, "spread", None),
            spread_average=getattr(source_row, "spread_average", None),
            confidence=getattr(source_row, "confidence", 0.55),
            reason=getattr(source_row, "reason", ""),
        )

    def _theoretical_entry_market_structure(
        self,
        candles: list[object],
    ) -> dict[str, float | None]:
        structure: dict[str, float | None] = {
            "atr": None,
            "day_high": None,
            "day_low": None,
            "donchian_high": None,
            "donchian_low": None,
            "pivot": None,
            "vwap": None,
            "z_score": None,
            "support": None,
            "resistance": None,
            "swing_high": None,
            "swing_low": None,
        }
        if not candles:
            return structure
        closes = [float(getattr(candle, "fechamento", 0.0) or 0.0) for candle in candles]
        try:
            structure["atr"] = self.mt5_market_data_service._atr(
                candles,
                min(14, max(1, len(candles))),
            )
            structure["day_high"], structure["day_low"] = (
                self.mt5_market_data_service._session_high_low(candles)
            )
            structure["donchian_high"], structure["donchian_low"] = (
                self.mt5_market_data_service._donchian(candles, min(20, len(candles)))
            )
            structure["pivot"] = self.mt5_market_data_service._pivot(candles)
            structure["vwap"] = self.mt5_market_data_service._vwap(candles)
            structure["z_score"] = self.mt5_market_data_service._z_score(
                closes,
                min(20, len(closes)),
            )
            structure["support"], structure["resistance"] = (
                self.mt5_market_data_service._support_resistance(
                    candles,
                    min(20, len(candles)),
                )
            )
            structure["swing_high"], structure["swing_low"] = (
                self.mt5_market_data_service._swing_high_low(
                    candles,
                    min(5, len(candles)),
                )
            )
        except Exception:  # noqa: BLE001 - estrutura auxiliar nao deve quebrar painel
            return structure
        return structure

    def _mean_last(self, values: list[float], period: int) -> float:
        if not values:
            return 0.0
        return sum(values[-period:]) / len(values[-period:])

    def _momentum_last(self, values: list[float], period: int) -> float:
        if len(values) <= period or values[-period - 1] == 0:
            return 0.0
        return (values[-1] - values[-period - 1]) / values[-period - 1]

    def _volatility_last(self, values: list[float], period: int) -> float:
        if len(values) < 2:
            return 0.0
        returns = []
        selected = values[-(period + 1):]
        for previous, current in zip(selected[:-1], selected[1:]):
            if previous:
                returns.append((current - previous) / previous)
        if not returns:
            return 0.0
        average = sum(returns) / len(returns)
        variance = sum((item - average) ** 2 for item in returns) / len(returns)
        return math.sqrt(variance)

    def _rsi_last(self, values: list[float], period: int) -> float:
        if len(values) <= period:
            return 50.0
        gains = []
        losses = []
        selected = values[-(period + 1):]
        for previous, current in zip(selected[:-1], selected[1:]):
            change = current - previous
            gains.append(max(change, 0.0))
            losses.append(abs(min(change, 0.0)))
        average_gain = sum(gains) / period
        average_loss = sum(losses) / period
        if average_loss == 0:
            return 100.0
        relative_strength = average_gain / average_loss
        return 100.0 - (100.0 / (1.0 + relative_strength))

    def _trend_from_averages(self, short_average: float, long_average: float) -> str:
        if short_average > long_average:
            return "ALTA"
        if short_average < long_average:
            return "BAIXA"
        return "INDEFINIDA"

    def _optional_float(self, value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _format_optional_float(
        self,
        value: object,
        decimals: int = 5,
    ) -> str:
        if value is None:
            return "N/D"
        return f"{float(value):.{decimals}f}"

    def _format_optional_percent(self, value: object) -> str:
        if value is None:
            return "N/D"
        return f"{float(value):.2%}"

    def _to_view_model_mt5_connection_diagnostic(
        self,
        diagnostic: object,
    ) -> DashboardMT5ConnectionDiagnosticViewModel:
        return DashboardMT5ConnectionDiagnosticViewModel(
            connection_status=str(getattr(diagnostic, "connection_status", "OFFLINE")),
            steps=[
                DashboardMT5DiagnosticStepViewModel(
                    name=str(getattr(step, "name", "N/D")),
                    status=str(getattr(step, "status", "FALHOU")),
                    message=str(getattr(step, "message", "")),
                    last_error_code=getattr(step, "last_error_code", None),
                    last_error_message=str(
                        getattr(step, "last_error_message", "")
                    ),
                )
                for step in getattr(diagnostic, "steps", ()) or ()
            ],
            last_error_code=getattr(diagnostic, "last_error_code", None),
            last_error_message=str(getattr(diagnostic, "last_error_message", "")),
            terminal_path=str(getattr(diagnostic, "terminal_path", "N/D")),
            build=str(getattr(diagnostic, "build", "N/D")),
            server=str(getattr(diagnostic, "server", "N/D")),
            account=str(getattr(diagnostic, "account", "N/D")),
            connected=bool(getattr(diagnostic, "connected", False)),
            trade_allowed=bool(getattr(diagnostic, "trade_allowed", False)),
            community_connection=bool(
                getattr(diagnostic, "community_connection", False)
            ),
            failed_call=str(getattr(diagnostic, "failed_call", "")),
            diagnostic_message=str(
                getattr(diagnostic, "diagnostic_message", "")
            ),
            executed_at=format_dashboard_timestamp(
                getattr(diagnostic, "executed_at", "")
            ),
        )

    def _to_view_model_mt5_heuristic_research(
        self,
        data: DashboardData,
    ) -> DashboardMT5HeuristicResearchViewModel:
        forex = data.mt5_forex_signals
        source_rows = list(getattr(forex, "pairs", []) or [])
        scenario_ranking = self._mt5_research_scenario_ranking(
            source_rows,
            data.configuration_data,
        )
        best_scenarios = self._best_mt5_scenarios_by_pair(scenario_ranking)
        scenario_by_market = {
            str(scenario.pair).upper(): scenario
            for scenario in best_scenarios
        }
        rows = []
        for pair in self._ordered_mt5_research_pairs(source_rows):
            scenario = scenario_by_market.get(pair)
            if scenario is None:
                source_row = self._find_mt5_forex_row(forex, pair)
                if source_row is not None:
                    rows.append(self._mt5_heuristic_research_row(source_row))
            else:
                rows.append(
                    self._mt5_heuristic_research_row_from_scenario(
                        scenario,
                        scenario_ranking,
                    )
                )
        ranked = [
            row
            for row in rows
            if row.status == "APROVADO" and row.recommended_heuristic != "WAIT_NO_EDGE"
        ]
        if not rows:
            return DashboardMT5HeuristicResearchViewModel(
                rows=[],
                status="SEM_DADOS",
                timeframe=str(getattr(forex, "timeframe", "M1")),
                source="MT5_RESEARCH_SNAPSHOT",
                message=(
                    "Nenhum snapshot MT5 carregado para calibracao. Execute "
                    "Pesquisa MT5 no Research Lab."
                ),
            )
        if not ranked:
            return DashboardMT5HeuristicResearchViewModel(
                rows=rows,
                scenario_ranking=scenario_ranking,
                best_scenarios_by_market=best_scenarios,
                status="SEM_HEURISTICA_APROVADA",
                timeframe=str(getattr(forex, "timeframe", "M1")),
                candles_loaded=sum(
                    int(getattr(row, "received_candles", 0) or 0)
                    for row in list(getattr(forex, "pairs", []) or [])
                ),
                source="MT5_RESEARCH_SNAPSHOT",
                message=(
                    "Nenhuma heuristica MT5 passou nos criterios minimos "
                    "da calibracao sob demanda."
                ),
            )
        best = max(
            ranked,
            key=self._mt5_research_row_rank,
        )
        best_scenario = next(
            (
                scenario
                for scenario in best_scenarios
                if scenario.pair == best.pair
                and scenario.timeframe == best.timeframe
                and scenario.model == best.recommended_heuristic
                and scenario.decision == best.decision
                and str(scenario.parameters.get("alpha", "")).upper()
                == str(best.final_configuration.get("alpha", "")).upper()
            ),
            None,
        )
        source_row = self._find_mt5_forex_row(forex, best.pair)
        return DashboardMT5HeuristicResearchViewModel(
            rows=rows,
            scenario_ranking=scenario_ranking,
            best_scenarios_by_market=best_scenarios,
            best_scenario=best_scenario,
            best_pair=best.pair,
            best_heuristic=best.recommended_heuristic,
            best_score=best.score,
            best_decision=best.decision,
            best_confidence=best.confidence,
            winner_configuration=self._winner_model_configuration(
                data.configuration_data,
                best.recommended_heuristic,
            ),
            winner_score_breakdown=dict(best.score_breakdown),
            winner_diagnostics=list(best.diagnostics),
            winner_research_configuration=self._winner_research_configuration(
                data.configuration_data,
                source_row,
                best,
                best_scenario,
            ),
            status="RESEARCH_ONLY",
            timeframe=str(getattr(forex, "timeframe", "M1")),
            candles_loaded=sum(
                int(getattr(row, "received_candles", 0) or 0)
                for row in list(getattr(forex, "pairs", []) or [])
            ),
            source="MT5_RESEARCH_SNAPSHOT",
            message=(
                "Calibracao MT5 somente leitura. O resultado gera constantes "
                "para a heuristica online e nao autoriza operacao real."
            ),
        )

    def _mt5_research_scenario_ranking(
        self,
        rows: list[object],
        configuration: ConfigurationData | None,
    ) -> list[DashboardMT5ScenarioViewModel]:
        scenarios: list[DashboardMT5ScenarioViewModel] = []
        for row in rows:
            scenarios.extend(self._mt5_research_scenarios_for_row(row, configuration))
        return sorted(
            scenarios,
            key=lambda scenario: (
                -float(scenario.score),
                str(scenario.pair),
                str(scenario.timeframe),
                str(scenario.model),
            ),
        )

    def _best_mt5_scenarios_by_pair(
        self,
        scenarios: list[DashboardMT5ScenarioViewModel],
    ) -> list[DashboardMT5ScenarioViewModel]:
        best_by_market: dict[str, DashboardMT5ScenarioViewModel] = {}
        for scenario in scenarios:
            key = scenario.pair.upper()
            current = best_by_market.get(key)
            if current is None or self._mt5_lab_target_rank(
                scenario,
            ) > self._mt5_lab_target_rank(current):
                best_by_market[key] = scenario
        return sorted(
            best_by_market.values(),
            key=lambda scenario: str(scenario.pair),
        )

    def _mt5_lab_target_rank(
        self,
        scenario: DashboardMT5ScenarioViewModel,
    ) -> tuple[bool, float, float, float, float]:
        lab_confidence = float(getattr(scenario, "lab_confidence", 0.0) or 0.0)
        score = float(getattr(scenario, "score", 0.0) or 0.0)
        composite = (score * 0.65) + (lab_confidence * 0.35)
        meets_target = lab_confidence >= MT5_LAB_TARGET_CONFIDENCE
        return (
            str(getattr(scenario, "status", "")) == "APROVADO",
            composite,
            score,
            lab_confidence,
            meets_target,
        )

    def _mt5_research_row_rank(
        self,
        row: object,
    ) -> tuple[bool, float, float, float, str]:
        score = float(getattr(row, "score", 0.0) or 0.0)
        confidence = float(getattr(row, "confidence", 0.0) or 0.0)
        composite = (score * 0.65) + (confidence * 0.35)
        return (
            str(getattr(row, "status", "")) == "APROVADO",
            composite,
            score,
            confidence,
            str(getattr(row, "timeframe", "") or ""),
        )

    def _ordered_mt5_research_pairs(self, rows: list[object]) -> list[str]:
        return sorted(
            {
                str(getattr(row, "pair", "") or "").upper()
                for row in rows
                if str(getattr(row, "pair", "") or "").strip()
            }
        )

    def _mt5_research_scenarios_for_row(
        self,
        row: object,
        configuration: ConfigurationData | None,
    ) -> list[DashboardMT5ScenarioViewModel]:
        if str(getattr(row, "status", "")).upper() != "OK":
            return []
        session_filter_enabled = bool(
            getattr(configuration, "forex_session_filter_enabled", True)
        )
        entry_scenarios: list[DashboardMT5ScenarioViewModel] = []
        for parameters in self._mt5_scenario_parameter_grid(
            configuration,
            expand_exits=False,
        ):
            model = parameters["modelo"]
            scenario = self._mt5_scenario_for_parameters(
                row,
                model,
                parameters,
                session_filter_enabled=session_filter_enabled,
            )
            entry_scenarios.append(scenario)

        ranked_entry_scenarios = sorted(
            entry_scenarios,
            key=self._mt5_lab_target_rank,
            reverse=True,
        )
        finalists = self._mt5_research_entry_finalists(ranked_entry_scenarios)
        scenarios: list[DashboardMT5ScenarioViewModel] = []
        for scenario in finalists:
            base_parameters = {
                key: value
                for key, value in dict(scenario.parameters).items()
                if key != "stop_management"
            }
            base_parameters["modelo"] = scenario.model
            for parameters in self._mt5_expand_stop_management_grid([base_parameters]):
                scenarios.append(
                    self._mt5_scenario_for_parameters(
                        row,
                        parameters["modelo"],
                        parameters,
                        session_filter_enabled=session_filter_enabled,
                    )
                )
        return scenarios

    def _mt5_research_entry_finalists(
        self,
        ranked_scenarios: list[DashboardMT5ScenarioViewModel],
    ) -> list[DashboardMT5ScenarioViewModel]:
        """Preserva diversidade de Alphas antes de testar gestao de saida."""
        selected: list[DashboardMT5ScenarioViewModel] = list(ranked_scenarios[:20])
        selected_keys = {
            (
                str(scenario.alpha_id),
                str(scenario.model),
                str(scenario.timeframe),
                tuple(sorted(dict(scenario.parameters).items())),
            )
            for scenario in selected
        }
        alpha_counts: dict[str, int] = {}
        for scenario in selected:
            alpha_counts[str(scenario.alpha_id).upper()] = (
                alpha_counts.get(str(scenario.alpha_id).upper(), 0) + 1
            )
        for scenario in ranked_scenarios:
            alpha_id = str(scenario.alpha_id).upper()
            if alpha_counts.get(alpha_id, 0) >= 2:
                continue
            key = (
                str(scenario.alpha_id),
                str(scenario.model),
                str(scenario.timeframe),
                tuple(sorted(dict(scenario.parameters).items())),
            )
            if key in selected_keys:
                continue
            selected.append(scenario)
            selected_keys.add(key)
            alpha_counts[alpha_id] = alpha_counts.get(alpha_id, 0) + 1
        return sorted(selected, key=self._mt5_lab_target_rank, reverse=True)

    def _mt5_scenario_parameter_grid(
        self,
        configuration: ConfigurationData | None,
        *,
        expand_exits: bool = True,
    ) -> list[dict[str, object]]:
        vol_low = float(
            getattr(configuration, "quantitative_score_volatility_low_threshold", 0.0001)
            or 0.0001
        )
        vol_high = float(
            getattr(
                configuration,
                "quantitative_score_volatility_high_threshold",
                0.0003,
            )
            or 0.0003
        )
        ema_pairs = (
            (9, 21),
            (20, 50),
            (50, 200),
            (20, 100),
        )
        rsi_pairs = ((30.0, 70.0), (35.0, 65.0), (40.0, 60.0))
        atr_values = (1.5, 2.0, 2.5)
        rr_values = (1.5, 2.0, 2.5, 3.0)
        momentum_values = (0.0, 0.0005)
        volatility_values = self._unique_floats((vol_low, vol_high))
        grid: list[dict[str, object]] = []
        for ema_short, ema_long in ema_pairs:
            for atr_stop_factor in atr_values:
                for rr in rr_values:
                    for momentum_threshold in momentum_values:
                        for volatility_threshold in volatility_values:
                            grid.append(
                                self._mt5_grid_parameters(
                                    "ALPHA001",
                                    "TREND_MOMENTUM",
                                    ema_short,
                                    ema_long,
                                    30.0,
                                    70.0,
                                    atr_stop_factor,
                                    rr,
                                    momentum_threshold,
                                    volatility_threshold,
                                )
                            )
        for ema_short, ema_long in ema_pairs:
            for atr_stop_factor in atr_values:
                for rr in rr_values:
                    for pullback_tolerance in (0.0005, 0.0015):
                        for adx_min in (20.0, 25.0):
                            grid.append(
                                self._mt5_grid_parameters(
                                    "ALPHA002",
                                    "TREND_PULLBACK",
                                    ema_short,
                                    ema_long,
                                    35.0,
                                    65.0,
                                    atr_stop_factor,
                                    rr,
                                    0.0,
                                    vol_low,
                                    pullback_tolerance=pullback_tolerance,
                                    adx_min=adx_min,
                                )
                            )
        for atr_stop_factor in atr_values:
            for rr in rr_values:
                for breakout_momentum in (0.0003, 0.0006):
                    for consolidation_volatility in volatility_values:
                        grid.append(
                            self._mt5_grid_parameters(
                                "ALPHA003",
                                "BREAKOUT_CONSOLIDATION",
                                20,
                                50,
                                30.0,
                                70.0,
                                atr_stop_factor,
                                rr,
                                breakout_momentum,
                                consolidation_volatility,
                            )
                        )
        for rsi_oversold, rsi_overbought in ((20.0, 80.0), (25.0, 75.0), (30.0, 70.0)):
            for atr_stop_factor in atr_values:
                for rr in rr_values:
                    grid.append(
                        self._mt5_grid_parameters(
                            "ALPHA004",
                            "RSI_REVERSAL",
                            9,
                            21,
                            rsi_oversold,
                            rsi_overbought,
                            atr_stop_factor,
                            rr,
                            0.0,
                            vol_low,
                        )
                    )
        for donchian_period in (20, 40, 55):
            for atr_stop_factor in atr_values:
                for rr in rr_values:
                    for momentum_threshold in momentum_values:
                        for breakout_buffer in (0.0001, 0.0003):
                            grid.append(
                                self._mt5_grid_parameters(
                                    "ALPHA005",
                                    "DONCHIAN_BREAKOUT",
                                    20,
                                    donchian_period,
                                    30.0,
                                    70.0,
                                    atr_stop_factor,
                                    rr,
                                    momentum_threshold,
                                    vol_low,
                                    breakout_buffer=breakout_buffer,
                                    donchian_period=donchian_period,
                                )
                            )
        for ema_short, ema_long in ema_pairs:
            for adx_min in (20.0, 25.0, 30.0):
                for atr_stop_factor in atr_values:
                    for momentum_threshold in momentum_values:
                        grid.append(
                            self._mt5_grid_parameters(
                                "ALPHA006",
                                "ADX_TREND_STRENGTH",
                                ema_short,
                                ema_long,
                                30.0,
                                70.0,
                                atr_stop_factor,
                                2.0,
                                momentum_threshold,
                                vol_low,
                                adx_min=adx_min,
                            )
                        )
        for ema_short, ema_long in ((9, 21), (20, 50)):
            for atr_stop_factor in atr_values:
                for rr in rr_values:
                    grid.append(
                        self._mt5_grid_parameters(
                            "ALPHA007",
                            "MACD_MOMENTUM_SHIFT",
                            ema_short,
                            ema_long,
                            30.0,
                            70.0,
                            atr_stop_factor,
                            rr,
                            0.0,
                            vol_low,
                        )
                    )
        for atr_stop_factor in atr_values:
            for rr in rr_values:
                for bollinger_width_threshold in (0.0004, 0.0008):
                    grid.append(
                        self._mt5_grid_parameters(
                            "ALPHA008",
                            "BOLLINGER_VOLATILITY_EXPANSION",
                            20,
                            50,
                            30.0,
                            70.0,
                            atr_stop_factor,
                            rr,
                            0.0003,
                            vol_low,
                            bollinger_width_threshold=bollinger_width_threshold,
                        )
                    )
        for ema_short, ema_long in ema_pairs:
            for atr_regime in ("LOW", "MEDIUM", "HIGH"):
                for atr_stop_factor in atr_values:
                    grid.append(
                        self._mt5_grid_parameters(
                            "ALPHA009",
                            "ATR_VOLATILITY_REGIME",
                            ema_short,
                            ema_long,
                            30.0,
                            70.0,
                            atr_stop_factor,
                            2.0,
                            0.0,
                            vol_low,
                            atr_regime=atr_regime,
                        )
                    )
        for donchian_period in (20, 40, 55):
            for atr_stop_factor in atr_values:
                for rr in rr_values:
                    grid.append(
                        self._mt5_grid_parameters(
                            "ALPHA010",
                            "DONCHIAN_STRUCTURE_BREAKOUT",
                            20,
                            donchian_period,
                            30.0,
                            70.0,
                            atr_stop_factor,
                            rr,
                            0.0003,
                            vol_low,
                            donchian_period=donchian_period,
                        )
                    )
        for rsi_oversold, rsi_overbought in rsi_pairs:
            for atr_stop_factor in atr_values:
                grid.append(
                    self._mt5_grid_parameters(
                        "ALPHA011",
                        "PIVOT_REJECTION",
                        20,
                        50,
                        rsi_oversold,
                        rsi_overbought,
                        atr_stop_factor,
                        2.0,
                        0.0,
                        vol_low,
                    )
                )
        for rsi_oversold, rsi_overbought in ((25.0, 75.0), (30.0, 70.0)):
            for z_threshold in (1.0, 1.5, 2.0):
                grid.append(
                    self._mt5_grid_parameters(
                        "ALPHA012",
                        "VWAP_MEAN_REVERSION",
                        20,
                        50,
                        rsi_oversold,
                        rsi_overbought,
                        2.0,
                        2.0,
                        0.0,
                        vol_low,
                        z_threshold=z_threshold,
                    )
                )
        for rsi_oversold, rsi_overbought in rsi_pairs:
            for atr_stop_factor in atr_values:
                grid.append(
                    self._mt5_grid_parameters(
                        "ALPHA013",
                        "SUPPORT_RESISTANCE_REACTION",
                        20,
                        50,
                        rsi_oversold,
                        rsi_overbought,
                        atr_stop_factor,
                        2.0,
                        0.0,
                        vol_low,
                    )
                )
        for ema_short, ema_long in ema_pairs:
            for momentum_threshold in momentum_values:
                grid.append(
                    self._mt5_grid_parameters(
                        "ALPHA014",
                        "MULTI_TIMEFRAME_ALIGNMENT",
                        ema_short,
                        ema_long,
                        30.0,
                        70.0,
                        2.0,
                        2.0,
                        momentum_threshold,
                        vol_low,
                    )
                )
        for volume_factor in (0.8, 1.0, 1.2):
            grid.append(
                self._mt5_grid_parameters(
                    "ALPHA015",
                    "LIQUIDITY_SPREAD_FILTER",
                    20,
                    50,
                    30.0,
                    70.0,
                    2.0,
                    2.0,
                    0.0,
                    vol_low,
                    volume_factor=volume_factor,
                )
            )
        if expand_exits:
            return self._mt5_expand_stop_management_grid(grid)
        return grid

    def _mt5_expand_stop_management_grid(
        self,
        base_grid: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        expanded: list[dict[str, object]] = []
        for parameters in base_grid:
            atr_factor = str(parameters.get("atr_stop_factor", "2.0"))
            ema_long = str(parameters.get("ema_longa", "50"))
            for exit_parameters in self._mt5_exit_management_variants(
                atr_factor,
                ema_long,
            ):
                candidate = dict(parameters)
                candidate.update(exit_parameters)
                expanded.append(candidate)
        return expanded

    def _mt5_exit_management_variants(
        self,
        atr_factor: str,
        ema_long: str,
    ) -> tuple[dict[str, object], ...]:
        return (
            {"stop_management": "FIXED_STOP"},
            {
                "stop_management": "ATR_TRAILING_STOP",
                "atr_trailing_factor": atr_factor,
                "atr_trailing_activation_rr": "1.0",
            },
            {
                "stop_management": "BREAK_EVEN",
                "break_even_trigger_rr": "1.0",
                "break_even_offset_pips": "0.0",
            },
            {
                "stop_management": "CHANDELIER_EXIT",
                "chandelier_period": "22",
                "chandelier_atr_factor": atr_factor,
            },
            {
                "stop_management": "PARABOLIC_SAR",
                "sar_step": "0.02",
                "sar_max_step": "0.20",
            },
            {
                "stop_management": "DONCHIAN_CHANNEL_STOP",
                "donchian_stop_period": "20",
            },
            {
                "stop_management": "MOVING_AVERAGE_EXIT",
                "exit_ma_period": ema_long,
                "exit_ma_type": "EMA",
            },
            {
                "stop_management": "TIME_STOP",
                "max_bars_in_trade": "12",
                "max_minutes_in_trade": "720",
            },
            {
                "stop_management": "VOLATILITY_STOP",
                "volatility_window": "20",
                "volatility_multiplier": atr_factor,
            },
        )

    def _mt5_grid_parameters(
        self,
        alpha_id: str,
        model: str,
        ema_short: int,
        ema_long: int,
        rsi_oversold: float,
        rsi_overbought: float,
        atr_stop_factor: float,
        rr: float,
        momentum_threshold: float,
        volatility_threshold: float,
        **extras: object,
    ) -> dict[str, object]:
        parameters: dict[str, object] = {
            "alpha": alpha_id,
            "modelo": model,
            "ema_curta": ema_short,
            "ema_longa": ema_long,
            "rsi_sobrevenda": rsi_oversold,
            "rsi_sobrecompra": rsi_overbought,
            "atr_stop_factor": atr_stop_factor,
            "rr": rr,
            "momentum_threshold": momentum_threshold,
            "volatility_threshold": volatility_threshold,
            "exit_model": "SCENARIO_EXIT_RESEARCH_SELECTION",
        }
        parameters.update(extras)
        return parameters

    def _mt5_alpha_library(self) -> dict[str, str]:
        return {
            "ALPHA001": "Trend Momentum",
            "ALPHA002": "Trend Pullback",
            "ALPHA003": "Breakout de Consolidacao",
            "ALPHA004": "RSI Reversal",
            "ALPHA005": "Donchian Breakout",
            "ALPHA006": "ADX Trend Strength",
            "ALPHA007": "MACD Momentum Shift",
            "ALPHA008": "Bollinger Volatility Expansion",
            "ALPHA009": "ATR Volatility Regime",
            "ALPHA010": "Donchian Structure Breakout",
            "ALPHA011": "Pivot Rejection",
            "ALPHA012": "VWAP Mean Reversion",
            "ALPHA013": "Support Resistance Reaction",
            "ALPHA014": "Multi-Timeframe Alignment",
            "ALPHA015": "Liquidity Spread Filter",
        }

    def _mt5_alpha_definitions(self) -> dict[str, dict[str, object]]:
        return {
            "ALPHA001": {
                "hypothesis": "Continuidade em tendencia com momentum e volatilidade suficientes.",
                "indicators": ("EMA", "RSI", "ATR stop", "Momentum", "Volatilidade", "RR"),
            },
            "ALPHA002": {
                "hypothesis": "Pullback em tendencia estabelecida pode continuar o movimento.",
                "indicators": ("EMA", "ADX", "RSI", "ATR stop", "RR"),
            },
            "ALPHA003": {
                "hypothesis": "Consolidacao com momentum pode iniciar rompimento.",
                "indicators": ("ATR", "Momentum", "Volatilidade", "RR"),
            },
            "ALPHA004": {
                "hypothesis": "RSI extremo pode antecipar reversao curta.",
                "indicators": ("RSI", "ATR stop", "RR"),
            },
            "ALPHA005": {
                "hypothesis": "Rompimento de canal Donchian pode gerar continuacao.",
                "indicators": ("Donchian", "Momentum", "ATR stop", "RR"),
            },
            "ALPHA006": {
                "hypothesis": "Tendencias com ADX alto tem maior chance de continuacao.",
                "indicators": ("EMA", "ADX", "ATR", "Momentum"),
            },
            "ALPHA007": {
                "hypothesis": "Mudanca de momentum via MACD pode antecipar continuacao ou reversao curta.",
                "indicators": ("MACD", "MACD Signal", "EMA", "ATR"),
            },
            "ALPHA008": {
                "hypothesis": "Compressao de Bollinger seguida de expansao gera rompimentos.",
                "indicators": ("Bollinger Bands", "ATR", "Momentum", "Tick Volume"),
            },
            "ALPHA009": {
                "hypothesis": "Certas estrategias funcionam melhor em regimes de ATR alto, medio ou baixo.",
                "indicators": ("ATR real", "ATR medio", "Volatilidade", "EMA"),
            },
            "ALPHA010": {
                "hypothesis": "Rompimento de maxima/minima estrutural relevante gera continuacao.",
                "indicators": ("Donchian", "Swing High", "Swing Low", "ATR", "Momentum"),
            },
            "ALPHA011": {
                "hypothesis": "Rejeicoes em pivos podem gerar reversao ou continuacao.",
                "indicators": ("Pivot", "RSI", "ATR", "Candle structure"),
            },
            "ALPHA012": {
                "hypothesis": "Distancia excessiva da VWAP pode gerar reversao a media.",
                "indicators": ("VWAP", "Z-Score", "RSI", "ATR"),
            },
            "ALPHA013": {
                "hypothesis": "Preco perto de suporte/resistencia relevante altera a probabilidade de entrada.",
                "indicators": ("Suporte", "Resistencia", "Swing High", "Swing Low", "RSI", "ATR"),
            },
            "ALPHA014": {
                "hypothesis": "Sinais alinhados em multiplos timeframes tem maior qualidade.",
                "indicators": ("EMA", "Trend", "Momentum", "Timeframe ativo"),
            },
            "ALPHA015": {
                "hypothesis": "Sinais com spread baixo e tick volume suficiente tem execucao mais confiavel.",
                "indicators": ("Spread", "Spread medio", "Tick Volume", "Tick Volume medio"),
            },
        }

    def _mt5_alpha_name(self, alpha_id: str) -> str:
        return self._mt5_alpha_library().get(str(alpha_id).upper(), "N/D")

    def _mt5_alpha_hypothesis(self, alpha_id: str) -> str:
        definition = self._mt5_alpha_definitions().get(str(alpha_id).upper(), {})
        return str(definition.get("hypothesis", "N/D"))

    def _mt5_alpha_used_indicators(self, alpha_id: str) -> tuple[str, ...]:
        definition = self._mt5_alpha_definitions().get(str(alpha_id).upper(), {})
        return tuple(str(item) for item in definition.get("indicators", ()))

    def _unique_numbers(self, values: tuple[int, ...]) -> tuple[int, ...]:
        return tuple(dict.fromkeys(int(value) for value in values))

    def _unique_floats(self, values: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(dict.fromkeys(float(value) for value in values))

    def _mt5_scenario_for_parameters(
        self,
        row: object,
        model: str,
        parameters: dict[str, object],
        *,
        session_filter_enabled: bool | None = None,
    ) -> DashboardMT5ScenarioViewModel:
        candidate = self._mt5_parameterized_candidate(row, model, parameters)
        time_context = self.forex_time_layer.classify(
            str(getattr(row, "pair", "N/D")),
            getattr(row, "last_candle_time", "N/D"),
        )
        if session_filter_enabled is None:
            configuration = self.configuration_service.get_configuration_data()
            session_filter_enabled = bool(
                getattr(configuration, "forex_session_filter_enabled", True)
            )
        temporal_blocked = bool(getattr(time_context, "temporal_blocked", False))
        temporal_blocking_enabled = bool(
            temporal_blocked and session_filter_enabled
        )
        raw_score = min(
            1.0,
            float(candidate["score"])
            + self._exit_management_score_adjustment(row, parameters),
        )
        score = self._time_adjusted_scenario_score(
            raw_score,
            time_context,
            session_filter_enabled=session_filter_enabled,
        )
        status = (
            "REJEITADO"
            if temporal_blocking_enabled
            else "APROVADO"
            if score >= 0.55
            else "REJEITADO"
        )
        decision = "WAIT" if temporal_blocking_enabled else str(candidate["decision"])
        reason = str(candidate["reason"])
        if time_context.temporal_reason:
            reason = f"{reason} | Tempo: {time_context.temporal_reason}"
        if not session_filter_enabled and bool(
            getattr(time_context, "temporal_blocked", False)
        ):
            reason = f"{reason} | Filtro de sessao ignorado pela configuracao."
        evidence = self._mt5_scenario_historical_evidence(
            row,
            model,
            parameters,
            decision,
        )
        lab_confidence = evidence.win_rate
        certification = self._mt5_research_certification_from_evidence(evidence)
        return DashboardMT5ScenarioViewModel(
            alpha_id=str(parameters.get("alpha", "ALPHA001")).upper(),
            pair=str(getattr(row, "pair", "N/D")),
            timeframe=str(getattr(row, "timeframe", "M1")),
            temporal_session=time_context.session,
            temporal_session_label=time_context.session_label,
            temporal_window_brt=time_context.brt_window,
            temporal_hour_utc=time_context.hour_utc,
            temporal_hour_brt=time_context.hour_brt,
            temporal_weekday=time_context.weekday,
            temporal_is_london_session=time_context.is_london_session,
            temporal_is_new_york_session=time_context.is_new_york_session,
            temporal_is_asia_session=time_context.is_asia_session,
            temporal_is_overlap=time_context.is_london_new_york_overlap,
            temporal_is_rollover=time_context.is_rollover_window,
            temporal_is_friday_late=time_context.is_friday_late,
            temporal_is_sunday_open=time_context.is_sunday_open,
            temporal_is_off_hours=time_context.is_off_hours,
            temporal_status=time_context.temporal_status,
            temporal_blocked=temporal_blocking_enabled,
            temporal_score_adjustment=time_context.temporal_score_adjustment,
            temporal_reason=time_context.temporal_reason,
            temporal_preferred_sessions=time_context.preferred_sessions,
            temporal_financial_centers=time_context.financial_centers,
            temporal_quality_note=time_context.quality_note,
            model=model,
            parameters={
                str(key): str(value)
                for key, value in parameters.items()
                if key != "modelo"
            },
            score=score,
            lab_confidence=lab_confidence,
            lab_confidence_sample_size=evidence.sample_size,
            lab_confidence_profit_factor=evidence.profit_factor,
            lab_confidence_expectancy=evidence.avg_return,
            lab_confidence_max_drawdown=evidence.max_drawdown,
            lab_confidence_source=evidence.source,
            ict_score=certification.ict_score,
            ict_grade=certification.grade,
            ict_status=certification.status,
            ict_usage=certification.usage,
            ict_demo_allowed=certification.demo_allowed,
            ict_minimum_filters_passed=certification.minimum_filters_passed,
            ict_rejection_reasons=certification.rejection_reasons,
            ict_component_scores=certification.component_scores,
            status=status,
            decision=decision,
            reason=reason,
        )

    def _exit_management_score_adjustment(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> float:
        policy = str(parameters.get("stop_management", "FIXED_STOP")).upper()
        volatility = abs(float(getattr(row, "volatility", 0.0) or 0.0))
        trend = str(getattr(row, "trend", "INDEFINIDA")).upper()
        momentum = abs(float(getattr(row, "momentum", 0.0) or 0.0))
        trending = trend in {"ALTA", "BAIXA"} and momentum > 0.0
        if policy == "ATR_TRAILING_STOP":
            return 0.035 if volatility >= 0.0003 else 0.025
        if policy == "CHANDELIER_EXIT":
            return 0.035 if trending else 0.015
        if policy == "PARABOLIC_SAR":
            return 0.030 if trending and volatility >= 0.0003 else 0.010
        if policy == "DONCHIAN_CHANNEL_STOP":
            return 0.030 if trending else 0.012
        if policy == "BREAK_EVEN":
            return 0.030 if volatility <= 0.0003 else 0.018
        if policy == "VOLATILITY_STOP":
            return 0.030 if volatility >= 0.0004 else 0.012
        if policy == "MOVING_AVERAGE_EXIT":
            return 0.022 if trending else 0.010
        if policy == "TIME_STOP":
            return 0.018
        return 0.0

    def _time_adjusted_scenario_score(
        self,
        score: float,
        time_context: object,
        *,
        session_filter_enabled: bool = True,
    ) -> float:
        if session_filter_enabled and bool(getattr(time_context, "temporal_blocked", False)):
            return 0.0
        if score <= 0.0:
            return 0.0
        if not session_filter_enabled and bool(
            getattr(time_context, "temporal_blocked", False)
        ):
            return max(0.0, min(score, 1.0))
        adjustment = float(getattr(time_context, "temporal_score_adjustment", 0.0) or 0.0)
        return max(0.0, min(score + adjustment, 1.0))

    def _mt5_row_lab_confidence(self, row: object) -> float:
        sample_size = int(getattr(row, "sample_size", 0) or 0)
        if sample_size <= 0:
            return 0.0
        return max(0.0, min(float(getattr(row, "win_rate", 0.0) or 0.0), 1.0))

    def _mt5_scenario_historical_evidence(
        self,
        row: object,
        model: str,
        parameters: dict[str, object],
        current_decision: str,
    ) -> MT5ScenarioHistoricalEvidence:
        decision = str(current_decision or "WAIT").upper()
        if decision not in {"BUY", "SELL"}:
            return MT5ScenarioHistoricalEvidence(source="SCENARIO_WAIT_NO_EXPOSURE")
        candles = self._latest_mt5_forex_candles(
            str(getattr(row, "pair", "")),
            str(getattr(row, "timeframe", "")),
        )
        if not candles:
            return MT5ScenarioHistoricalEvidence(source="SCENARIO_NO_CANDLES")
        configuration = self.configuration_service.get_configuration_data()
        forward = max(
            int(getattr(configuration, "quantitative_score_forward_return_candles", 1) or 1),
            1,
        )
        minimum = self._scenario_evidence_minimum_candles(model, parameters)
        end_index = len(candles) - forward
        if end_index <= minimum:
            return MT5ScenarioHistoricalEvidence(source="SCENARIO_INSUFFICIENT_CANDLES")
        indexes = self._scenario_evidence_indexes(minimum, end_index)
        returns: list[float] = []
        for index in indexes:
            snapshot = self._theoretical_entry_snapshot(row, candles[: index + 1])
            candidate = self._mt5_parameterized_candidate(snapshot, model, parameters)
            candidate_decision = str(candidate.get("decision", "WAIT")).upper()
            if candidate_decision not in {"BUY", "SELL"}:
                continue
            current_close = float(getattr(candles[index], "fechamento", 0.0) or 0.0)
            future_close = float(
                getattr(candles[index + forward], "fechamento", 0.0) or 0.0
            )
            if current_close <= 0.0:
                continue
            forward_return = (future_close / current_close) - 1.0
            directional_return = (
                forward_return if candidate_decision == "BUY" else -forward_return
            )
            returns.append(
                self._exit_adjusted_scenario_return(
                    directional_return,
                    parameters,
                )
            )
        return self._mt5_scenario_evidence_from_returns(returns)

    def _exit_adjusted_scenario_return(
        self,
        directional_return: float,
        parameters: dict[str, object],
    ) -> float:
        policy = str(parameters.get("stop_management", "FIXED_STOP")).upper()
        if directional_return == 0.0:
            return 0.0
        if directional_return > 0.0:
            capture = {
                "FIXED_STOP": 1.00,
                "ATR_TRAILING_STOP": 0.92,
                "BREAK_EVEN": 0.70,
                "CHANDELIER_EXIT": 0.88,
                "PARABOLIC_SAR": 0.78,
                "DONCHIAN_CHANNEL_STOP": 0.84,
                "MOVING_AVERAGE_EXIT": 0.82,
                "TIME_STOP": 0.76,
                "VOLATILITY_STOP": 0.90,
            }.get(policy, 1.0)
            return directional_return * capture

        loss_factor = {
            "FIXED_STOP": 1.00,
            "ATR_TRAILING_STOP": 0.74,
            "BREAK_EVEN": 0.48,
            "CHANDELIER_EXIT": 0.70,
            "PARABOLIC_SAR": 0.66,
            "DONCHIAN_CHANNEL_STOP": 0.82,
            "MOVING_AVERAGE_EXIT": 0.86,
            "TIME_STOP": 0.94,
            "VOLATILITY_STOP": 0.72,
        }.get(policy, 1.0)
        return directional_return * loss_factor

    def _scenario_evidence_minimum_candles(
        self,
        model: str,
        parameters: dict[str, object],
    ) -> int:
        base = self._theoretical_entry_minimum_candles(model)
        numeric_values = []
        for key in ("ema_curta", "ema_longa", "donchian_period"):
            try:
                numeric_values.append(int(float(parameters.get(key, 0) or 0)))
            except (TypeError, ValueError):
                continue
        return max([base, *numeric_values, 2])

    def _scenario_evidence_indexes(
        self,
        minimum: int,
        end_index: int,
        max_points: int = 6,
    ) -> list[int]:
        indexes = list(range(max(minimum - 1, 0), max(end_index, 0)))
        if len(indexes) <= max_points:
            return indexes
        stride = max(len(indexes) // max_points, 1)
        sampled = indexes[::stride]
        return sampled[-max_points:]

    def _mt5_scenario_evidence_from_returns(
        self,
        returns: list[float],
    ) -> MT5ScenarioHistoricalEvidence:
        sample_size = len(returns)
        if sample_size <= 0:
            return MT5ScenarioHistoricalEvidence(source="SCENARIO_NO_HISTORICAL_MATCH")
        wins = [item for item in returns if item > 0.0]
        losses = [item for item in returns if item < 0.0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        if gross_loss == 0.0 and gross_profit > 0.0:
            profit_factor = float("inf")
        elif gross_loss == 0.0:
            profit_factor = 0.0
        else:
            profit_factor = gross_profit / gross_loss
        return MT5ScenarioHistoricalEvidence(
            sample_size=sample_size,
            win_rate=len(wins) / sample_size,
            avg_return=sum(returns) / sample_size,
            profit_factor=profit_factor,
            max_drawdown=self._scenario_max_drawdown(returns),
            source="SCENARIO_ALPHA_BACKTEST_SAMPLE",
        )

    def _scenario_max_drawdown(self, returns: list[float]) -> float:
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for item in returns:
            equity += item
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        return max_drawdown

    def _mt5_research_certification(
        self,
        row: object,
    ) -> TraderIACertificationResult:
        return self.traderia_certification_engine.from_research_metrics(
            win_rate=float(getattr(row, "win_rate", 0.0) or 0.0),
            profit_factor=float(getattr(row, "profit_factor", 0.0) or 0.0),
            avg_return=float(getattr(row, "avg_return", 0.0) or 0.0),
            max_drawdown=float(getattr(row, "max_drawdown", 0.0) or 0.0),
            sample_size=int(getattr(row, "sample_size", 0) or 0),
        )

    def _mt5_research_certification_from_evidence(
        self,
        evidence: MT5ScenarioHistoricalEvidence,
    ) -> TraderIACertificationResult:
        return self.traderia_certification_engine.from_research_metrics(
            win_rate=evidence.win_rate,
            profit_factor=evidence.profit_factor,
            avg_return=evidence.avg_return,
            max_drawdown=evidence.max_drawdown,
            sample_size=evidence.sample_size,
        )

    def _mt5_parameterized_candidate(
        self,
        row: object,
        model: str,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        alpha_id = str(parameters.get("alpha", "ALPHA001")).upper()
        if alpha_id == "ALPHA002":
            return self._trend_pullback_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA003":
            return self._breakout_consolidation_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA004":
            return self._rsi_reversal_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA005":
            return self._donchian_breakout_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA006":
            return self._adx_trend_strength_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA007":
            return self._macd_momentum_shift_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA008":
            return self._bollinger_volatility_expansion_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA009":
            return self._atr_volatility_regime_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA010":
            return self._donchian_structure_breakout_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA011":
            return self._pivot_rejection_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA012":
            return self._vwap_mean_reversion_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA013":
            return self._support_resistance_reaction_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA014":
            return self._multi_timeframe_alignment_parameterized_candidate(row, parameters)
        if alpha_id == "ALPHA015":
            return self._liquidity_spread_filter_parameterized_candidate(row, parameters)
        if model == "MA_RSI_FILTER":
            return self._ma_rsi_parameterized_candidate(row, parameters)
        if model == "RSI_REVERSAL":
            return self._rsi_reversal_parameterized_candidate(row, parameters)
        return self._trend_momentum_parameterized_candidate(row, parameters)

    def _indicator_unavailable_candidate(self, *indicators: str) -> dict[str, object]:
        missing = ", ".join(indicators)
        return {
            "decision": "WAIT",
            "score": 0.0,
            "reason": f"INDICADOR_INDISPONIVEL: {missing}.",
        }

    def _missing_indicators(self, row: object, *names: str) -> tuple[str, ...]:
        missing: list[str] = []
        for name in names:
            value = getattr(row, name, None)
            if value in (None, ""):
                missing.append(name)
        return tuple(missing)

    def _trend_momentum_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        trend = str(getattr(row, "trend", "INDEFINIDA")).upper()
        momentum = float(getattr(row, "momentum", 0.0) or 0.0)
        volatility = abs(float(getattr(row, "volatility", 0.0) or 0.0))
        confidence = float(getattr(row, "confidence", 0.0) or 0.0)
        momentum_threshold = float(parameters["momentum_threshold"])
        volatility_threshold = float(parameters["volatility_threshold"])
        rr = float(parameters["rr"])
        atr_stop_factor = float(parameters["atr_stop_factor"])
        parameter_fit = self._mt5_parameter_fit(row, parameters)
        aligned_buy = trend == "ALTA" and momentum > momentum_threshold
        aligned_sell = trend == "BAIXA" and momentum < -momentum_threshold
        aligned = aligned_buy or aligned_sell
        decision = "BUY" if aligned_buy else "SELL" if aligned_sell else "WAIT"
        score = 0.0
        if aligned and volatility >= volatility_threshold:
            score = confidence + 0.20
            score += min(volatility * 25.0, 0.15)
            score += self._rr_score_adjustment(rr)
            score += self._atr_score_adjustment(volatility, atr_stop_factor)
            score += parameter_fit
        return {
            "decision": decision,
            "score": min(score, 1.0),
            "reason": (
                "Tendencia, momentum e volatilidade atendem o cenario."
                if score > 0
                else "Cenario nao confirmou tendencia/momentum/volatilidade."
            ),
        }

    def _ma_rsi_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        short_average = float(getattr(row, "short_average", 0.0) or 0.0)
        long_average = float(getattr(row, "long_average", 0.0) or 0.0)
        rsi = float(getattr(row, "rsi", 50.0) or 50.0)
        confidence = float(getattr(row, "confidence", 0.0) or 0.0)
        rsi_oversold = float(parameters["rsi_sobrevenda"])
        rsi_overbought = float(parameters["rsi_sobrecompra"])
        rr = float(parameters["rr"])
        if long_average <= 0:
            return {"decision": "WAIT", "score": 0.0, "reason": "Medias indisponiveis."}
        ma_distance = abs((short_average - long_average) / long_average)
        buy = short_average > long_average and rsi < rsi_overbought
        sell = short_average < long_average and rsi > rsi_oversold
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0
        if decision != "WAIT":
            score = confidence + min(ma_distance * 20.0, 0.20)
            score += self._rsi_band_score_adjustment(
                rsi,
                rsi_oversold,
                rsi_overbought,
            )
            score += self._rr_score_adjustment(rr)
            score += self._mt5_parameter_fit(row, parameters)
        return {
            "decision": decision,
            "score": min(score, 1.0),
            "reason": (
                "Medias e RSI atendem o cenario parametrizado."
                if decision != "WAIT"
                else "Medias e RSI nao validaram o cenario."
            ),
        }

    def _rsi_reversal_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        rsi = float(getattr(row, "rsi", 50.0) or 50.0)
        confidence = float(getattr(row, "confidence", 0.0) or 0.0)
        rsi_oversold = float(parameters["rsi_sobrevenda"])
        rsi_overbought = float(parameters["rsi_sobrecompra"])
        rr = float(parameters["rr"])
        if rsi <= rsi_oversold:
            decision = "BUY"
        elif rsi >= rsi_overbought:
            decision = "SELL"
        else:
            decision = "WAIT"
        score = 0.0
        if decision != "WAIT":
            score = confidence + 0.12 + self._rr_score_adjustment(rr)
            score += self._rsi_extreme_score_adjustment(
                rsi,
                rsi_oversold,
                rsi_overbought,
            )
            score += self._atr_score_adjustment(
                abs(float(getattr(row, "volatility", 0.0) or 0.0)),
                float(parameters["atr_stop_factor"]),
            )
        return {
            "decision": decision,
            "score": min(score, 1.0),
            "reason": (
                "RSI extremo validou reversao parametrizada."
                if decision != "WAIT"
                else "RSI sem extremo para o cenario de reversao."
            ),
        }

    def _trend_pullback_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        missing = self._missing_indicators(row, "last_price", "short_average", "long_average", "rsi", "adx")
        if missing:
            return self._indicator_unavailable_candidate(*missing)
        trend = str(getattr(row, "trend", "INDEFINIDA")).upper()
        price = float(getattr(row, "last_price", 0.0) or 0.0)
        short_average = float(getattr(row, "short_average", 0.0) or 0.0)
        long_average = float(getattr(row, "long_average", 0.0) or 0.0)
        rsi = float(getattr(row, "rsi", 50.0) or 50.0)
        confidence = float(getattr(row, "confidence", 0.0) or 0.0)
        tolerance = float(parameters.get("pullback_tolerance", 0.001) or 0.001)
        adx = float(getattr(row, "adx") or 0.0)
        adx_min = float(parameters.get("adx_min", 20.0) or 20.0)
        rr = float(parameters["rr"])
        atr_stop_factor = float(parameters["atr_stop_factor"])
        if price <= 0 or short_average <= 0 or long_average <= 0 or adx < adx_min:
            return {"decision": "WAIT", "score": 0.0, "reason": "Pullback sem tendencia/medias/ADX validos."}
        buy = trend == "ALTA" and long_average < price <= short_average * (1.0 + tolerance)
        sell = trend == "BAIXA" and short_average * (1.0 - tolerance) <= price < long_average
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0
        if decision != "WAIT":
            score = confidence + 0.14
            score += self._rsi_band_score_adjustment(rsi, 35.0, 65.0)
            score += self._rr_score_adjustment(rr)
            score += self._atr_score_adjustment(abs(float(getattr(row, "volatility", 0.0) or 0.0)), atr_stop_factor)
        return {
            "decision": decision,
            "score": min(score, 1.0),
            "reason": (
                "Pullback em tendencia validado perto da media."
                if decision != "WAIT"
                else "Preco nao esta em pullback valido na tendencia."
            ),
        }

    def _breakout_consolidation_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        momentum = float(getattr(row, "momentum", 0.0) or 0.0)
        volatility = abs(float(getattr(row, "volatility", 0.0) or 0.0))
        confidence = float(getattr(row, "confidence", 0.0) or 0.0)
        breakout_momentum = float(parameters["momentum_threshold"])
        consolidation_volatility = float(parameters["volatility_threshold"])
        rr = float(parameters["rr"])
        atr_stop_factor = float(parameters["atr_stop_factor"])
        buy = volatility <= consolidation_volatility and momentum >= breakout_momentum
        sell = volatility <= consolidation_volatility and momentum <= -breakout_momentum
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0
        if decision != "WAIT":
            score = confidence + 0.16 + self._rr_score_adjustment(rr)
            score += self._atr_score_adjustment(volatility, atr_stop_factor)
        return {
            "decision": decision,
            "score": min(score, 1.0),
            "reason": (
                "Consolidacao com momentum de rompimento validado."
                if decision != "WAIT"
                else "Sem consolidacao/rompimento suficiente."
            ),
        }

    def _donchian_breakout_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        price = float(getattr(row, "last_price", 0.0) or 0.0)
        day_high = float(getattr(row, "day_high", 0.0) or 0.0)
        day_low = float(getattr(row, "day_low", 0.0) or 0.0)
        momentum = float(getattr(row, "momentum", 0.0) or 0.0)
        confidence = float(getattr(row, "confidence", 0.0) or 0.0)
        buffer = float(parameters.get("breakout_buffer", 0.0001) or 0.0001)
        momentum_threshold = float(parameters["momentum_threshold"])
        rr = float(parameters["rr"])
        atr_stop_factor = float(parameters["atr_stop_factor"])
        if price <= 0 or day_high <= 0 or day_low <= 0:
            return {"decision": "WAIT", "score": 0.0, "reason": "Canal Donchian indisponivel."}
        buy = price >= day_high * (1.0 - buffer) and momentum >= momentum_threshold
        sell = price <= day_low * (1.0 + buffer) and momentum <= -momentum_threshold
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0
        if decision != "WAIT":
            score = confidence + 0.18 + self._rr_score_adjustment(rr)
            score += self._atr_score_adjustment(abs(float(getattr(row, "volatility", 0.0) or 0.0)), atr_stop_factor)
        return {
            "decision": decision,
            "score": min(score, 1.0),
            "reason": (
                "Rompimento Donchian validado com momentum."
                if decision != "WAIT"
                else "Preco nao rompeu canal Donchian com momentum."
            ),
        }

    def _adx_trend_strength_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        missing = self._missing_indicators(row, "ema_fast", "ema_slow", "adx", "atr", "momentum")
        if missing:
            return self._indicator_unavailable_candidate(*missing)
        ema_fast = float(getattr(row, "ema_fast") or 0.0)
        ema_slow = float(getattr(row, "ema_slow") or 0.0)
        adx = float(getattr(row, "adx") or 0.0)
        atr = float(getattr(row, "atr") or 0.0)
        momentum = float(getattr(row, "momentum") or 0.0)
        adx_min = float(parameters.get("adx_min", 25.0) or 25.0)
        if adx < adx_min or atr <= 0.0:
            return {"decision": "WAIT", "score": 0.0, "reason": "ADX/ATR nao confirmou tendencia forte."}
        buy = ema_fast > ema_slow and momentum > float(parameters["momentum_threshold"])
        sell = ema_fast < ema_slow and momentum < -float(parameters["momentum_threshold"])
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0
        if decision != "WAIT":
            score = min(1.0, 0.35 + min(adx / 100.0, 0.35) + self._atr_score_adjustment(abs(float(getattr(row, "volatility", 0.0) or 0.0)), float(parameters["atr_stop_factor"])))
        return {
            "decision": decision,
            "score": score,
            "reason": "ADX alto com medias e momentum alinhados." if decision != "WAIT" else "Tendencia forte sem alinhamento direcional.",
        }

    def _macd_momentum_shift_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        missing = self._missing_indicators(row, "macd", "macd_signal", "ema_fast", "ema_slow", "atr")
        if missing:
            return self._indicator_unavailable_candidate(*missing)
        macd = float(getattr(row, "macd") or 0.0)
        signal = float(getattr(row, "macd_signal") or 0.0)
        ema_fast = float(getattr(row, "ema_fast") or 0.0)
        ema_slow = float(getattr(row, "ema_slow") or 0.0)
        atr = float(getattr(row, "atr") or 0.0)
        if atr <= 0.0:
            return self._indicator_unavailable_candidate("atr")
        buy = macd > signal and ema_fast >= ema_slow
        sell = macd < signal and ema_fast <= ema_slow
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0
        if decision != "WAIT":
            spread = abs(macd - signal)
            score = min(1.0, 0.38 + min(spread * 1000.0, 0.20) + self._rr_score_adjustment(float(parameters["rr"])))
        return {
            "decision": decision,
            "score": score,
            "reason": "MACD e sinal indicam mudanca de momentum." if decision != "WAIT" else "MACD sem cruzamento alinhado.",
        }

    def _bollinger_volatility_expansion_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        missing = self._missing_indicators(row, "bollinger_upper", "bollinger_lower", "atr", "momentum", "tick_volume", "tick_volume_average")
        if missing:
            return self._indicator_unavailable_candidate(*missing)
        price = float(getattr(row, "last_price", 0.0) or 0.0)
        upper = float(getattr(row, "bollinger_upper") or 0.0)
        lower = float(getattr(row, "bollinger_lower") or 0.0)
        atr = float(getattr(row, "atr") or 0.0)
        momentum = float(getattr(row, "momentum") or 0.0)
        volume = float(getattr(row, "tick_volume") or 0.0)
        volume_average = float(getattr(row, "tick_volume_average") or 0.0)
        width = max(upper - lower, 0.0)
        threshold = float(parameters.get("bollinger_width_threshold", 0.0008) or 0.0008)
        if atr <= 0.0 or volume_average <= 0.0 or width > threshold:
            return {"decision": "WAIT", "score": 0.0, "reason": "Sem compressao/volume suficiente para expansao Bollinger."}
        buy = price >= upper and momentum > 0 and volume >= volume_average
        sell = price <= lower and momentum < 0 and volume >= volume_average
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0
        if decision != "WAIT":
            score = min(1.0, 0.40 + self._rr_score_adjustment(float(parameters["rr"])) + min(volume / volume_average - 1.0, 0.20))
        return {
            "decision": decision,
            "score": score,
            "reason": "Bollinger comprimida com rompimento e tick volume." if decision != "WAIT" else "Sem rompimento Bollinger valido.",
        }

    def _atr_volatility_regime_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        missing = self._missing_indicators(row, "atr", "atr_average", "volatility", "ema_fast", "ema_slow")
        if missing:
            return self._indicator_unavailable_candidate(*missing)
        atr = float(getattr(row, "atr") or 0.0)
        atr_average = float(getattr(row, "atr_average") or 0.0)
        ema_fast = float(getattr(row, "ema_fast") or 0.0)
        ema_slow = float(getattr(row, "ema_slow") or 0.0)
        if atr <= 0.0 or atr_average <= 0.0:
            return self._indicator_unavailable_candidate("atr", "atr_average")
        ratio = atr / atr_average
        regime = str(parameters.get("atr_regime", "MEDIUM")).upper()
        current = "HIGH" if ratio >= 1.2 else "LOW" if ratio <= 0.8 else "MEDIUM"
        if current != regime:
            return {"decision": "WAIT", "score": 0.0, "reason": f"Regime ATR atual {current} diferente do pesquisado {regime}."}
        decision = "BUY" if ema_fast > ema_slow else "SELL" if ema_fast < ema_slow else "WAIT"
        score = 0.0 if decision == "WAIT" else min(1.0, 0.42 + min(abs(ratio - 1.0), 0.25))
        return {
            "decision": decision,
            "score": score,
            "reason": f"Regime ATR {current} com medias direcionais." if decision != "WAIT" else "Regime ATR sem direcao por medias.",
        }

    def _donchian_structure_breakout_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        missing = self._missing_indicators(row, "donchian_high", "donchian_low", "swing_high", "swing_low", "atr", "momentum")
        if missing:
            return self._indicator_unavailable_candidate(*missing)
        price = float(getattr(row, "last_price", 0.0) or 0.0)
        high = max(float(getattr(row, "donchian_high") or 0.0), float(getattr(row, "swing_high") or 0.0))
        low = min(float(getattr(row, "donchian_low") or 0.0), float(getattr(row, "swing_low") or 0.0))
        momentum = float(getattr(row, "momentum") or 0.0)
        threshold = float(parameters["momentum_threshold"])
        buy = price >= high and momentum >= threshold
        sell = price <= low and momentum <= -threshold
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0 if decision == "WAIT" else min(1.0, 0.44 + self._rr_score_adjustment(float(parameters["rr"])))
        return {
            "decision": decision,
            "score": score,
            "reason": "Rompimento estrutural Donchian/Swing confirmado." if decision != "WAIT" else "Sem rompimento estrutural relevante.",
        }

    def _pivot_rejection_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        missing = self._missing_indicators(row, "pivot", "rsi", "atr")
        if missing:
            return self._indicator_unavailable_candidate(*missing)
        price = float(getattr(row, "last_price", 0.0) or 0.0)
        pivot = float(getattr(row, "pivot") or 0.0)
        rsi = float(getattr(row, "rsi") or 50.0)
        atr = float(getattr(row, "atr") or 0.0)
        if pivot <= 0.0 or atr <= 0.0:
            return self._indicator_unavailable_candidate("pivot", "atr")
        near_pivot = abs(price - pivot) <= atr
        buy = near_pivot and price > pivot and rsi <= float(parameters["rsi_sobrecompra"])
        sell = near_pivot and price < pivot and rsi >= float(parameters["rsi_sobrevenda"])
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0 if decision == "WAIT" else min(1.0, 0.43 + self._rsi_band_score_adjustment(rsi, float(parameters["rsi_sobrevenda"]), float(parameters["rsi_sobrecompra"])))
        return {
            "decision": decision,
            "score": score,
            "reason": "Rejeicao em pivot com RSI compativel." if decision != "WAIT" else "Sem rejeicao objetiva em pivot.",
        }

    def _vwap_mean_reversion_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        missing = self._missing_indicators(row, "vwap", "z_score", "rsi", "atr")
        if missing:
            return self._indicator_unavailable_candidate(*missing)
        price = float(getattr(row, "last_price", 0.0) or 0.0)
        vwap = float(getattr(row, "vwap") or 0.0)
        z_score = float(getattr(row, "z_score") or 0.0)
        rsi = float(getattr(row, "rsi") or 50.0)
        threshold = float(parameters.get("z_threshold", 1.5) or 1.5)
        if vwap <= 0.0:
            return self._indicator_unavailable_candidate("vwap")
        buy = price < vwap and z_score <= -threshold and rsi <= float(parameters["rsi_sobrevenda"])
        sell = price > vwap and z_score >= threshold and rsi >= float(parameters["rsi_sobrecompra"])
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0 if decision == "WAIT" else min(1.0, 0.45 + min(abs(z_score) / 10.0, 0.20))
        return {
            "decision": decision,
            "score": score,
            "reason": "Distancia extrema da VWAP sugere reversao a media." if decision != "WAIT" else "VWAP/Z-Score sem extremo suficiente.",
        }

    def _support_resistance_reaction_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        missing = self._missing_indicators(row, "support", "resistance", "swing_high", "swing_low", "rsi", "atr")
        if missing:
            return self._indicator_unavailable_candidate(*missing)
        price = float(getattr(row, "last_price", 0.0) or 0.0)
        support = min(float(getattr(row, "support") or 0.0), float(getattr(row, "swing_low") or 0.0))
        resistance = max(float(getattr(row, "resistance") or 0.0), float(getattr(row, "swing_high") or 0.0))
        atr = float(getattr(row, "atr") or 0.0)
        rsi = float(getattr(row, "rsi") or 50.0)
        if atr <= 0.0:
            return self._indicator_unavailable_candidate("atr")
        near_support = abs(price - support) <= atr
        near_resistance = abs(price - resistance) <= atr
        buy = near_support and rsi <= float(parameters["rsi_sobrecompra"])
        sell = near_resistance and rsi >= float(parameters["rsi_sobrevenda"])
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0 if decision == "WAIT" else min(1.0, 0.44 + self._atr_score_adjustment(abs(float(getattr(row, "volatility", 0.0) or 0.0)), float(parameters["atr_stop_factor"])))
        return {
            "decision": decision,
            "score": score,
            "reason": "Reacao em suporte/resistencia relevante." if decision != "WAIT" else "Preco distante de suporte/resistencia relevante.",
        }

    def _multi_timeframe_alignment_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        missing = self._missing_indicators(row, "ema_fast", "ema_slow", "momentum")
        if missing:
            return self._indicator_unavailable_candidate(*missing)
        # Nesta fase, o alinhamento usa o timeframe vencedor do Lab e nao consulta
        # outros timeframes no refresh Forex online.
        ema_fast = float(getattr(row, "ema_fast") or 0.0)
        ema_slow = float(getattr(row, "ema_slow") or 0.0)
        momentum = float(getattr(row, "momentum") or 0.0)
        buy = ema_fast > ema_slow and momentum > float(parameters["momentum_threshold"])
        sell = ema_fast < ema_slow and momentum < -float(parameters["momentum_threshold"])
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = 0.0 if decision == "WAIT" else min(1.0, 0.40 + self._mt5_parameter_fit(row, parameters))
        return {
            "decision": decision,
            "score": score,
            "reason": "Timeframe ativo alinhado por EMA e momentum; MTF completo pendente." if decision != "WAIT" else "Sem alinhamento direcional no timeframe ativo.",
        }

    def _liquidity_spread_filter_parameterized_candidate(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        missing = self._missing_indicators(row, "spread", "spread_average", "tick_volume", "tick_volume_average")
        if missing:
            return self._indicator_unavailable_candidate(*missing)
        spread = float(getattr(row, "spread") or 0.0)
        spread_average = float(getattr(row, "spread_average") or 0.0)
        volume = float(getattr(row, "tick_volume") or 0.0)
        volume_average = float(getattr(row, "tick_volume_average") or 0.0)
        if spread_average <= 0.0 or volume_average <= 0.0:
            return self._indicator_unavailable_candidate("spread_average", "tick_volume_average")
        volume_factor = float(parameters.get("volume_factor", 1.0) or 1.0)
        allowed = spread <= spread_average and volume >= volume_average * volume_factor
        return {
            "decision": "WAIT",
            "score": 0.35 if allowed else 0.0,
            "reason": "Liquidez/spread aceitos como filtro; nao gera direcao sozinho." if allowed else "Spread alto ou tick volume insuficiente.",
        }

    def _mt5_parameter_fit(
        self,
        row: object,
        parameters: dict[str, object],
    ) -> float:
        volatility = abs(float(getattr(row, "volatility", 0.0) or 0.0))
        momentum = abs(float(getattr(row, "momentum", 0.0) or 0.0))
        ema_short = int(parameters["ema_curta"])
        ema_long = int(parameters["ema_longa"])
        ema_span = max(1, ema_long - ema_short)
        if volatility >= 0.0005 or momentum >= 0.0006:
            preferred_span = 30
        elif volatility <= 0.00015 and momentum <= 0.0003:
            preferred_span = 150
        else:
            preferred_span = 80
        distance = abs(ema_span - preferred_span) / max(preferred_span, ema_span)
        return max(0.0, 0.08 * (1.0 - distance))

    def _rr_score_adjustment(self, rr: float) -> float:
        if rr >= 3.0:
            return 0.06
        if rr >= 2.5:
            return 0.05
        if rr >= 2.0:
            return 0.04
        return 0.02

    def _atr_score_adjustment(self, volatility: float, atr_stop_factor: float) -> float:
        if volatility >= 0.0005:
            preferred = 2.5
        elif volatility <= 0.00015:
            preferred = 1.5
        else:
            preferred = 2.0
        return max(0.0, 0.04 - abs(atr_stop_factor - preferred) * 0.02)

    def _rsi_band_score_adjustment(
        self,
        rsi: float,
        rsi_oversold: float,
        rsi_overbought: float,
    ) -> float:
        if rsi_oversold + 5.0 <= rsi <= rsi_overbought - 5.0:
            return 0.10
        if rsi_oversold <= rsi <= rsi_overbought:
            return 0.05
        return 0.0

    def _rsi_extreme_score_adjustment(
        self,
        rsi: float,
        rsi_oversold: float,
        rsi_overbought: float,
    ) -> float:
        if rsi <= rsi_oversold:
            return min((rsi_oversold - rsi) / 100.0, 0.05)
        if rsi >= rsi_overbought:
            return min((rsi - rsi_overbought) / 100.0, 0.05)
        return 0.0

    def _mt5_heuristic_research_row_from_scenario(
        self,
        scenario: DashboardMT5ScenarioViewModel,
        scenario_ranking: list[DashboardMT5ScenarioViewModel],
    ) -> DashboardMT5HeuristicResearchRowViewModel:
        buy_scenario = self._best_directional_scenario(
            scenario.pair,
            "BUY",
            scenario_ranking,
        )
        sell_scenario = self._best_directional_scenario(
            scenario.pair,
            "SELL",
            scenario_ranking,
        )
        return DashboardMT5HeuristicResearchRowViewModel(
            pair=scenario.pair,
            timeframe=scenario.timeframe,
            recommended_heuristic=scenario.model,
            decision=scenario.decision,
            score=scenario.score,
            confidence=scenario.lab_confidence,
            ict_score=scenario.ict_score,
            ict_grade=scenario.ict_grade,
            ict_status=scenario.ict_status,
            ict_usage=scenario.ict_usage,
            ict_demo_allowed=scenario.ict_demo_allowed,
            ict_rejection_reasons=scenario.ict_rejection_reasons,
            status=scenario.status,
            reason=scenario.reason,
            ideal_timeframe=scenario.timeframe,
            final_configuration={
                "modelo": scenario.model,
                "timeframe": scenario.timeframe,
                **scenario.parameters,
            },
            buy_scenario=self._scenario_summary(buy_scenario),
            sell_scenario=self._scenario_summary(sell_scenario),
            buy_score=float(getattr(buy_scenario, "score", 0.0) or 0.0),
            sell_score=float(getattr(sell_scenario, "score", 0.0) or 0.0),
            score_breakdown={
                "Modelo": scenario.model,
                "Score": f"{scenario.score * 100:.0f} / 100",
                "ICT": f"{scenario.ict_score:.2f}",
                "Classe ICT": scenario.ict_grade,
                "Uso ICT": scenario.ict_usage,
                "Status": scenario.status,
                **scenario.parameters,
            },
            diagnostics=[
                f"Cenario vencedor por par/timeframe: {scenario.model}",
                f"Decisao: {scenario.decision}",
                f"ICT: {scenario.ict_score:.2f} ({scenario.ict_grade})",
                f"Motivo: {scenario.reason}",
            ],
        )

    def _best_directional_scenario(
        self,
        pair: str,
        decision: str,
        scenario_ranking: list[DashboardMT5ScenarioViewModel],
    ) -> DashboardMT5ScenarioViewModel | None:
        pair_key = str(pair).upper()
        candidates = [
            scenario
            for scenario in scenario_ranking
            if scenario.pair.upper() == pair_key and scenario.decision == decision
        ]
        if not candidates:
            return None
        return max(candidates, key=self._mt5_lab_target_rank)

    def _scenario_summary(
        self,
        scenario: DashboardMT5ScenarioViewModel | None,
    ) -> dict[str, str]:
        if scenario is None:
            return {}
        return {
            "timeframe": scenario.timeframe,
            "modelo": scenario.model,
            "score": f"{scenario.score:.4f}",
            "confianca_lab": f"{scenario.lab_confidence:.4f}",
            "status": scenario.status,
            **scenario.parameters,
        }

    def _mt5_heuristic_research_row(
        self,
        row: object,
    ) -> DashboardMT5HeuristicResearchRowViewModel:
        if str(getattr(row, "status", "")).upper() != "OK":
            return DashboardMT5HeuristicResearchRowViewModel(
                pair=str(getattr(row, "pair", "N/D")),
                timeframe=str(getattr(row, "timeframe", "H1")),
                status="REJEITADO",
                reason=str(getattr(row, "reason", "Par sem dados MT5.")),
            )

        candidates = [
            self._trend_momentum_candidate(row),
            self._ma_rsi_candidate(row),
            self._rsi_reversal_candidate(row),
        ]
        best = max(candidates, key=lambda item: item["score"])
        status = "APROVADO" if best["score"] >= 0.55 else "REJEITADO"
        certification = self._mt5_research_certification(row)
        return DashboardMT5HeuristicResearchRowViewModel(
            pair=str(getattr(row, "pair", "N/D")),
            timeframe=str(getattr(row, "timeframe", "H1")),
            recommended_heuristic=str(best["heuristic"]),
            decision=str(best["decision"]),
            score=float(best["score"]),
            confidence=self._mt5_row_lab_confidence(row),
            ict_score=certification.ict_score,
            ict_grade=certification.grade,
            ict_status=certification.status,
            ict_usage=certification.usage,
            ict_demo_allowed=certification.demo_allowed,
            ict_rejection_reasons=certification.rejection_reasons,
            status=status,
            reason=str(best["reason"]),
            score_breakdown={
                str(key): str(value)
                for key, value in dict(best.get("breakdown", {})).items()
            },
            diagnostics=[
                str(item) for item in list(best.get("diagnostics", []) or [])
            ],
        )

    def _trend_momentum_candidate(self, row: object) -> dict[str, object]:
        trend = str(getattr(row, "trend", "INDEFINIDA")).upper()
        momentum = float(getattr(row, "momentum", 0.0) or 0.0)
        volatility = abs(float(getattr(row, "volatility", 0.0) or 0.0))
        confidence = float(getattr(row, "confidence", 0.0) or 0.0)
        aligned_buy = trend == "ALTA" and momentum > 0
        aligned_sell = trend == "BAIXA" and momentum < 0
        aligned = aligned_buy or aligned_sell
        decision = "BUY" if aligned_buy else "SELL" if aligned_sell else "WAIT"
        score = confidence
        if aligned:
            score += 0.20
        if volatility > 0:
            score += min(volatility * 25.0, 0.15)
        return {
            "heuristic": "TREND_MOMENTUM",
            "decision": decision,
            "score": min(score if aligned else 0.0, 1.0),
            "reason": (
                "Tendencia e momentum alinhados."
                if aligned
                else "Tendencia e momentum nao estao alinhados."
            ),
            "breakdown": {
                "Trend Alignment": "30 / 30" if aligned else "0 / 30",
                "Momentum": "20 / 20" if momentum != 0 else "0 / 20",
                "Volatilidade": (
                    f"{min(volatility * 25.0, 0.15) * 100:.0f} / 15"
                    if volatility > 0
                    else "0 / 15"
                ),
                "Confianca base": f"{confidence * 100:.0f} / 100",
                "Total": f"{min(score if aligned else 0.0, 1.0) * 100:.0f} / 100",
            },
            "diagnostics": [
                f"Tendencia: {trend}",
                f"Momentum: {momentum:.4%}",
                f"Volatilidade: {volatility:.4%}",
                (
                    "Resultado: tendencia e momentum alinhados"
                    if aligned
                    else "Resultado: tendencia e momentum nao alinhados"
                ),
                f"Decisao: {decision}",
            ],
        }

    def _ma_rsi_candidate(self, row: object) -> dict[str, object]:
        short_average = float(getattr(row, "short_average", 0.0) or 0.0)
        long_average = float(getattr(row, "long_average", 0.0) or 0.0)
        rsi = float(getattr(row, "rsi", 50.0) or 50.0)
        confidence = float(getattr(row, "confidence", 0.0) or 0.0)
        if long_average <= 0:
            return {
                "heuristic": "MA_RSI_FILTER",
                "decision": "WAIT",
                "score": 0.0,
                "reason": "Medias indisponiveis.",
            }
        ma_distance = abs((short_average - long_average) / long_average)
        buy = short_average > long_average and rsi < 70.0
        sell = short_average < long_average and rsi > 30.0
        decision = "BUY" if buy else "SELL" if sell else "WAIT"
        score = confidence + min(ma_distance * 20.0, 0.20)
        if 35.0 <= rsi <= 65.0:
            score += 0.10
        return {
            "heuristic": "MA_RSI_FILTER",
            "decision": decision,
            "score": min(score if decision != "WAIT" else 0.0, 1.0),
            "reason": (
                "Cruzamento de medias com RSI em zona operacional."
                if decision != "WAIT"
                else "Medias e RSI nao formam contexto suficiente."
            ),
            "breakdown": {
                "Media Alignment": "30 / 30" if decision != "WAIT" else "0 / 30",
                "RSI": "20 / 20" if 35.0 <= rsi <= 65.0 else "10 / 20",
                "Distancia medias": f"{min(ma_distance * 20.0, 0.20) * 100:.0f} / 20",
                "Confianca base": f"{confidence * 100:.0f} / 100",
                "Total": f"{min(score if decision != 'WAIT' else 0.0, 1.0) * 100:.0f} / 100",
            },
            "diagnostics": [
                f"Media curta: {short_average:.5f}",
                f"Media longa: {long_average:.5f}",
                f"RSI: {rsi:.2f}",
                (
                    "Resultado: medias e RSI em zona operacional"
                    if decision != "WAIT"
                    else "Resultado: medias e RSI sem contexto suficiente"
                ),
                f"Decisao: {decision}",
            ],
        }

    def _rsi_reversal_candidate(self, row: object) -> dict[str, object]:
        rsi = float(getattr(row, "rsi", 50.0) or 50.0)
        confidence = float(getattr(row, "confidence", 0.0) or 0.0)
        if rsi <= 30.0:
            decision = "BUY"
            score = confidence + 0.12
            reason = "RSI em sobrevenda; leitura de reversao compradora."
        elif rsi >= 70.0:
            decision = "SELL"
            score = confidence + 0.12
            reason = "RSI em sobrecompra; leitura de reversao vendedora."
        else:
            decision = "WAIT"
            score = 0.0
            reason = "RSI sem extremo suficiente para reversao."
        return {
            "heuristic": "RSI_REVERSAL",
            "decision": decision,
            "score": min(score, 1.0),
            "reason": reason,
            "breakdown": {
                "RSI extremo": "30 / 30" if decision != "WAIT" else "0 / 30",
                "Confianca base": f"{confidence * 100:.0f} / 100",
                "Bonus reversao": "12 / 12" if decision != "WAIT" else "0 / 12",
                "Total": f"{min(score, 1.0) * 100:.0f} / 100",
            },
            "diagnostics": [
                f"RSI: {rsi:.2f}",
                reason,
                f"Decisao: {decision}",
            ],
        }

    def _find_mt5_forex_row(self, forex: object, pair: str) -> object | None:
        for row in list(getattr(forex, "pairs", []) or []):
            if str(getattr(row, "pair", "")) == pair:
                return row
        return None

    def _winner_model_configuration(
        self,
        configuration: ConfigurationData | None,
        model: str,
    ) -> dict[str, str]:
        if configuration is None:
            return {"Modelo": model, "Preset": "Default MT5"}
        return {
            "Modelo": model,
            "Preset": "Default MT5",
            "Media curta": str(configuration.mt5_safe_mode_fast_ma_period),
            "Media longa": str(configuration.mt5_safe_mode_slow_ma_period),
            "Momentum": str(configuration.mt5_safe_mode_momentum_period),
            "Volatilidade": str(configuration.mt5_safe_mode_volatility_period),
            "Volatilidade minima": str(
                configuration.mt5_safe_mode_volatility_low_threshold
            ),
            "RSI": str(configuration.mt5_safe_mode_rsi_period),
            "RSI sobrevenda": "30",
            "RSI sobrecompra": "70",
            "Candles": str(configuration.mt5_safe_mode_candles_loaded),
        }

    def _winner_research_configuration(
        self,
        configuration: ConfigurationData | None,
        source_row: object | None,
        best: DashboardMT5HeuristicResearchRowViewModel,
        best_scenario: DashboardMT5ScenarioViewModel | None = None,
    ) -> dict[str, str]:
        values = {
            "Modelo": best.recommended_heuristic,
            "Preset": "Default MT5",
            "Timeframe": str(getattr(source_row, "timeframe", best.timeframe)),
            "Candles": str(
                getattr(
                    source_row,
                    "configured_candles",
                    getattr(configuration, "mt5_safe_mode_candles_loaded", 0),
                )
                or 0
            ),
            "Simbolo": best.pair,
            "Ultima atualizacao": str(getattr(source_row, "last_update", "")),
            "Fonte": "MT5_SAFE_MODE",
            "Read only": "SIM",
        }
        if best_scenario is not None:
            values["Fonte"] = "MT5_RESEARCH_SCENARIO_RUNNER"
            values["Scenario status"] = best_scenario.status
            values["Scenario score"] = f"{best_scenario.score:.4f}"
            values = self._mt5_research_configuration_with_scenario_evidence(
                values,
                best_scenario,
            )
            for key, value in best_scenario.parameters.items():
                values[key] = str(value)
        return values

    def _mt5_research_configuration_with_scenario_evidence(
        self,
        values: dict[str, str],
        scenario: DashboardMT5ScenarioViewModel,
    ) -> dict[str, str]:
        enriched = dict(values)
        enriched["Confirmacao Historica"] = f"{scenario.lab_confidence:.4f}"
        enriched["Amostra Historica"] = str(scenario.lab_confidence_sample_size)
        enriched["Profit Factor Historico"] = (
            f"{scenario.lab_confidence_profit_factor:.4f}"
        )
        enriched["Expectancy Historica"] = (
            f"{scenario.lab_confidence_expectancy:.4f}"
        )
        enriched["Drawdown Historico"] = (
            f"{scenario.lab_confidence_max_drawdown:.4f}"
        )
        enriched["Fonte Confirmacao"] = scenario.lab_confidence_source
        enriched["ICT"] = f"{scenario.ict_score:.2f}"
        enriched["Classe ICT"] = scenario.ict_grade
        enriched["Uso ICT"] = scenario.ict_usage
        return enriched

    def _to_view_model_timeframe_optimizer(
        self,
        data: DashboardData,
    ) -> list[DashboardTimeframeOptimizationViewModel]:
        return [
            DashboardTimeframeOptimizationViewModel(
                symbol=result.symbol,
                best_timeframe=result.best_timeframe,
                selected_reason=result.selected_reason,
                candidates=[
                    self._to_view_model_timeframe_candidate(candidate)
                    for candidate in result.candidates
                ],
                rejected_candidates=[
                    self._to_view_model_timeframe_candidate(candidate)
                    for candidate in result.rejected_candidates
                ],
                is_research_only=result.is_research_only,
            )
            for result in data.timeframe_optimizer
        ]

    def _to_view_model_timeframe_candidate(
        self,
        candidate: object,
    ) -> DashboardTimeframeCandidateViewModel:
        return DashboardTimeframeCandidateViewModel(
            symbol=str(getattr(candidate, "symbol", "N/D")),
            timeframe=str(getattr(candidate, "timeframe", "N/D")),
            sample_size=int(getattr(candidate, "sample_size", 0) or 0),
            win_rate=float(getattr(candidate, "win_rate", 0.0) or 0.0),
            avg_return=float(getattr(candidate, "avg_return", 0.0) or 0.0),
            profit_factor=float(getattr(candidate, "profit_factor", 0.0) or 0.0),
            max_drawdown=float(getattr(candidate, "max_drawdown", 0.0) or 0.0),
            calibrated_confidence=float(
                getattr(candidate, "calibrated_confidence", 0.0) or 0.0
            ),
            rank_score=float(getattr(candidate, "rank_score", 0.0) or 0.0),
            rejection_reason=str(getattr(candidate, "rejection_reason", "")),
        )

    def _research_lab_dashboard_fields(self) -> dict[str, object]:
        """Monta campos do Research Lab para o DashboardData."""
        return {
            "research_lab_experiments": (
                self.research_lab_service.list_experiments()
            ),
            "last_research_experiment": (
                self.research_lab_service.last_experiment()
            ),
            "research_benchmarks": self.research_lab_service.list_benchmarks(),
            "benchmark_comparison": self.research_lab_service.last_comparison(),
            "parameter_grid_results": (
                self.research_lab_service.list_parameter_grid_results()
            ),
            "best_parameter_grid_result": (
                self.research_lab_service.best_parameter_grid_result()
            ),
            "benchmark_validations": self.research_lab_service.list_validations(),
            "last_benchmark_validation": (
                self.research_lab_service.last_validation()
            ),
            "available_research_strategies": (
                self.replay_service.list_available_strategies()
            ),
            "alpha001_status": self.get_alpha001_status(),
            "alpha001_research_report": self.get_alpha001_research_report(),
            "alpha001_dashboard_research": (
                self.research_lab_service.alpha001_dashboard_research_metrics()
            ),
            "alpha001_parameter_ranking": (
                self.research_lab_service.list_alpha001_parameter_ranking()
            ),
            "alpha001_research_summary": self.get_alpha001_research_summary(),
            "alpha001_robustness": self.get_alpha001_robustness(),
            "research_report": self.get_research_report(),
            "alpha001_paper_status": self.get_alpha001_paper_status(),
            "alpha001_paper_report": self.get_alpha001_paper_report(),
        }

    def _to_live_research_dashboard_data(
        self,
        live_data: LiveResearchData | None,
    ) -> LiveResearchDashboardData:
        if live_data is None:
            return LiveResearchDashboardData(
                history=self.list_live_research_history(),
                session_summary=self.get_live_research_session_summary(),
                signal_quality=self.list_live_research_signal_quality(),
            )

        strategy_results = list(live_data.strategy_results)
        last_result = strategy_results[-1] if strategy_results else None
        last_signal = (
            last_result.strategy_signal
            if last_result is not None
            else None
        )
        ingestion = live_data.ingestion_summary
        candles_ingested = (
            ingestion.inserted_candles
            if ingestion is not None
            else 1
        )
        return LiveResearchDashboardData(
            symbol=live_data.symbol,
            timeframe=live_data.timeframe,
            candles_ingested=candles_ingested,
            strategies_evaluated=len(strategy_results),
            strategy_signals=len(strategy_results),
            decision_contexts=len(
                [result.decision_context for result in strategy_results]
            ),
            last_decision=(
                getattr(last_signal, "decision", "N/D")
                if last_signal is not None
                else "N/D"
            ),
            last_confidence=(
                float(getattr(last_signal, "confidence", 0.0))
                if last_signal is not None
                else 0.0
            ),
            safety_status="READ ONLY",
            has_data=True,
            history=self.list_live_research_history(),
            session_summary=self.get_live_research_session_summary(),
            signal_quality=self.list_live_research_signal_quality(),
        )

    def _to_live_research_history_rows(
        self,
        records: list[LiveResearchSnapshotRecord],
    ) -> list[LiveResearchHistoryRow]:
        return [
            LiveResearchHistoryRow(
                timestamp=record.timestamp,
                symbol=record.symbol,
                timeframe=record.timeframe,
                decision=record.decision,
                confidence=record.confidence,
                strategy_signals=record.strategy_signals,
                decision_contexts=record.decision_contexts,
            )
            for record in records
        ]

    def _to_live_research_session_summary_data(
        self,
        summary: LiveResearchSessionSummary,
    ) -> LiveResearchSessionSummaryData:
        return LiveResearchSessionSummaryData(
            total_snapshots=summary.total_snapshots,
            buy_count=summary.buy_count,
            sell_count=summary.sell_count,
            wait_count=summary.wait_count,
            average_confidence=summary.average_confidence,
            highest_confidence=summary.highest_confidence,
            lowest_confidence=summary.lowest_confidence,
            last_decision=summary.last_decision,
            last_timestamp=summary.last_timestamp,
        )

    def _to_live_research_signal_quality_rows(
        self,
        rows: list[LiveResearchSignalQuality],
    ) -> list[LiveResearchSignalQualityRow]:
        return [
            LiveResearchSignalQualityRow(
                strategy_name=row.strategy_name,
                signal_count=row.signal_count,
                buy_count=row.buy_count,
                sell_count=row.sell_count,
                wait_count=row.wait_count,
                average_confidence=row.average_confidence,
                last_decision=row.last_decision,
            )
            for row in rows
        ]

    def update_configuration(self, **kwargs: object) -> ConfigurationData:
        """Atualiza configuracoes por meio da camada de aplicacao."""
        return self.configuration_service.update_configuration(**kwargs)

    def save_configuration_preset(self, name: str) -> None:
        """Salva preset de configuracao."""
        self.configuration_service.save_preset(name)

    def load_configuration_preset(self, name: str) -> ConfigurationData:
        """Carrega preset de configuracao."""
        return self.configuration_service.load_preset(name)

    def list_configuration_presets(self) -> list[str]:
        """Lista presets de configuracao."""
        return self.configuration_service.list_presets()

    def delete_configuration_preset(self, name: str) -> None:
        """Exclui preset de configuracao."""
        self.configuration_service.delete_preset(name)

    def load_demo_replay_candles(self) -> ReplayData:
        """Carrega candles demonstrativos para replay."""
        return self.replay_service.load_demo_candles()

    def load_historical_replay_csv(self, path: object) -> ReplayData:
        """Carrega dataset historico de replay pela fachada."""
        if self._is_uploaded_csv(path):
            return self._load_uploaded_replay_csv(path)
        return self.replay_service.load_historical_csv(path)

    def list_historical_datasets(self) -> list[HistoricalDatasetMetadata]:
        """Lista datasets historicos disponiveis pela fachada."""
        catalog = getattr(self, "historical_dataset_catalog", None)
        datasets: list[HistoricalDatasetMetadata] = []
        if catalog is None:
            catalog = getattr(self, "_historical_dataset_catalog", None)
        if catalog is not None and hasattr(catalog, "list_datasets"):
            datasets.extend(list(catalog.list_datasets()))
        datasets.extend(self._provider_historical_dataset_metadata())
        by_id = {dataset.dataset_id: dataset for dataset in datasets}
        return sorted(by_id.values(), key=lambda dataset: dataset.dataset_id)

    def _list_dataset_dashboard_data(self) -> list[ActiveDatasetDashboardData]:
        """Lista datasets disponiveis para observabilidade do dashboard."""
        records = self._provider_dataset_records()
        if not records:
            return []

        active_id = self._active_provider_dataset_id(records)
        datasets: list[ActiveDatasetDashboardData] = []
        for record in records:
            metadata = self._provider_metadata(record)
            datasets.append(
                self._active_dataset_data(
                    record=record,
                    metadata=metadata,
                    selected=self._dataset_id(metadata, record) == active_id,
                )
            )
        return datasets

    def _get_active_dataset_dashboard_data(
        self,
    ) -> ActiveDatasetDashboardData | None:
        """Retorna o dataset historico ativo exibido pelo dashboard."""
        datasets = self._list_dataset_dashboard_data()
        for dataset in datasets:
            if dataset.selected:
                return dataset
        return datasets[0] if datasets else None

    def _get_dataset_profile_data(self) -> DatasetProfileData | None:
        """Retorna perfil quantitativo do dataset historico ativo."""
        metadata = self._active_historical_dataset_metadata()
        if metadata is None:
            return None
        try:
            dataset = self._load_historical_dataset_by_metadata(metadata)
        except ValueError:
            return None
        if dataset.is_empty or len(dataset.candles) < 2:
            return None
        return self._dataset_profile_from_dataset(metadata, dataset)

    def _active_historical_dataset_metadata(
        self,
    ) -> HistoricalDatasetMetadata | None:
        active = self._get_active_dataset_dashboard_data()
        if active is None:
            return None
        for dataset in self.list_historical_datasets():
            if dataset.dataset_id == active.dataset_id:
                return dataset
        return None

    def _load_historical_dataset_by_metadata(
        self,
        metadata: HistoricalDatasetMetadata,
    ) -> HistoricalDataset:
        source = self._selected_historical_dataset_source(metadata)
        dataset = self.historical_data_provider.load(
            source,
            symbol=metadata.ativo,
            timeframe=metadata.timeframe,
        )
        if dataset.is_empty:
            raise ValueError(self._historical_dataset_load_error())
        return dataset

    def _dataset_profile_from_dataset(
        self,
        metadata: HistoricalDatasetMetadata,
        dataset: HistoricalDataset,
    ) -> DatasetProfileData:
        candles = list(dataset.candles)
        closes = [float(candle.fechamento) for candle in candles]
        volumes = [int(candle.volume) for candle in candles]
        returns = self._daily_returns(candles)
        cumulative_returns = self._cumulative_returns(closes)
        max_drawdown = self._max_dataset_drawdown(closes)
        best_index, best_return = self._best_return(returns)
        worst_index, worst_return = self._worst_return(returns)
        quality_status = self._dataset_quality_label(metadata)

        return DatasetProfileData(
            asset=metadata.ativo,
            timeframe=metadata.timeframe,
            period=f"{dataset.start_date} -> {dataset.end_date}",
            candles=dataset.total_candles,
            initial_price=closes[0],
            final_price=closes[-1],
            accumulated_return=cumulative_returns[-1],
            annualized_return=self._annualized_return(closes, returns),
            annualized_volatility=self._annualized_volatility(returns),
            max_drawdown=max_drawdown,
            best_day=self._return_day_label(candles, best_index),
            best_day_return=best_return,
            worst_day=self._return_day_label(candles, worst_index),
            worst_day_return=worst_return,
            positive_days=len([value for value in returns if value > 0]),
            negative_days=len([value for value in returns if value < 0]),
            average_volume=sum(volumes) / len(volumes),
            max_volume=max(volumes),
            quality_status=quality_status,
            price_curve=[
                DatasetProfilePoint(label=candle.data, value=float(candle.fechamento))
                for candle in candles
            ],
            accumulated_return_curve=[
                DatasetProfilePoint(label=candle.data, value=value)
                for candle, value in zip(candles, cumulative_returns)
            ],
            daily_return_histogram=self._return_histogram(returns),
            volume_curve=[
                DatasetProfilePoint(label=candle.data, value=float(candle.volume))
                for candle in candles
            ],
        )

    def _daily_returns(self, candles: list[object]) -> list[float]:
        returns: list[float] = []
        for previous, current in zip(candles, candles[1:]):
            previous_close = float(getattr(previous, "fechamento", 0.0))
            current_close = float(getattr(current, "fechamento", 0.0))
            if previous_close <= 0:
                returns.append(0.0)
            else:
                returns.append((current_close / previous_close) - 1.0)
        return returns

    def _cumulative_returns(self, closes: list[float]) -> list[float]:
        initial_price = closes[0]
        if initial_price <= 0:
            return [0.0 for _ in closes]
        return [(close / initial_price) - 1.0 for close in closes]

    def _max_dataset_drawdown(self, closes: list[float]) -> float:
        max_drawdown = 0.0
        peak = closes[0]
        for close in closes:
            peak = max(peak, close)
            if peak <= 0:
                continue
            drawdown = (close / peak) - 1.0
            max_drawdown = min(max_drawdown, drawdown)
        return abs(max_drawdown)

    def _annualized_return(self, closes: list[float], returns: list[float]) -> float:
        initial_price = closes[0]
        final_price = closes[-1]
        periods = len(returns)
        if initial_price <= 0 or final_price <= 0 or periods <= 0:
            return 0.0
        return (final_price / initial_price) ** (252 / periods) - 1.0

    def _annualized_volatility(self, returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        average = sum(returns) / len(returns)
        variance = sum((value - average) ** 2 for value in returns)
        variance = variance / (len(returns) - 1)
        return math.sqrt(variance) * math.sqrt(252)

    def _best_return(self, returns: list[float]) -> tuple[int, float]:
        if not returns:
            return 0, 0.0
        index, value = max(enumerate(returns), key=lambda item: item[1])
        return index + 1, value

    def _worst_return(self, returns: list[float]) -> tuple[int, float]:
        if not returns:
            return 0, 0.0
        index, value = min(enumerate(returns), key=lambda item: item[1])
        return index + 1, value

    def _return_day_label(self, candles: list[object], index: int) -> str:
        if not candles:
            return "N/D"
        safe_index = max(0, min(index, len(candles) - 1))
        return str(getattr(candles[safe_index], "data", "N/D"))

    def _return_histogram(
        self,
        returns: list[float],
        buckets: int = 12,
    ) -> list[DatasetProfilePoint]:
        if not returns:
            return []
        minimum = min(returns)
        maximum = max(returns)
        if minimum == maximum:
            return [DatasetProfilePoint(label=self._percent_label(minimum), value=len(returns))]
        width = (maximum - minimum) / buckets
        counts = [0 for _ in range(buckets)]
        for value in returns:
            index = min(int((value - minimum) / width), buckets - 1)
            counts[index] += 1
        points: list[DatasetProfilePoint] = []
        for index, count in enumerate(counts):
            start = minimum + index * width
            end = start + width
            label = f"{self._percent_label(start)} a {self._percent_label(end)}"
            points.append(DatasetProfilePoint(label=label, value=float(count)))
        return points

    def _percent_label(self, value: float) -> str:
        return f"{value * 100:.2f}%"

    def _dataset_quality_label(self, metadata: HistoricalDatasetMetadata) -> str:
        status = self._historical_dataset_quality_status_or_provider(metadata)
        if status is None:
            return "N/D"
        return status.quality_status

    def _provider_dataset_records(self) -> list[object]:
        provider = getattr(self, "historical_data_provider", None)
        list_datasets = getattr(provider, "list_datasets", None)
        if not callable(list_datasets):
            return []
        try:
            return list(list_datasets())
        except (OSError, ValueError, TypeError):
            return []

    def _provider_metadata(self, record: object) -> dict[str, Any]:
        provider = getattr(self, "historical_data_provider", None)
        get_metadata = getattr(provider, "get_metadata", None)
        if not callable(get_metadata):
            return {}
        try:
            metadata = get_metadata(
                getattr(record, "symbol", ""),
                getattr(record, "timeframe", ""),
                getattr(record, "period", ""),
            )
        except (OSError, ValueError, TypeError):
            return {}
        return metadata if isinstance(metadata, dict) else {}

    def _provider_historical_dataset_metadata(
        self,
    ) -> list[HistoricalDatasetMetadata]:
        datasets: list[HistoricalDatasetMetadata] = []
        for record in self._provider_dataset_records():
            metadata = self._provider_metadata(record)
            dataset = HistoricalDatasetMetadata(
                dataset_id=self._dataset_id(metadata, record),
                ativo=self._asset_from_metadata(metadata),
                timeframe=self._metadata_text(metadata, "timeframe")
                or str(getattr(record, "timeframe", "N/D")),
                start_date=(
                    self._metadata_text(metadata, "first_date")
                    or self._metadata_text(metadata, "first_timestamp")
                    or "N/D"
                ),
                end_date=(
                    self._metadata_text(metadata, "last_date")
                    or self._metadata_text(metadata, "last_timestamp")
                    or "N/D"
                ),
                estimated_candles=self._candle_count(metadata) or 0,
                provider="HistoricalDataProvider",
            )
            datasets.append(dataset)
        return datasets

    def _historical_dataset_quality_status_or_provider(
        self,
        dataset: HistoricalDatasetMetadata,
    ) -> HistoricalDatasetQualityStatus | None:
        status = self.historical_dataset_quality_repository.get(
            dataset.dataset_id
        )
        if status is not None:
            return status
        for record in self._provider_dataset_records():
            metadata = self._provider_metadata(record)
            if self._dataset_id(metadata, record) != dataset.dataset_id:
                continue
            if not self._dataset_status(metadata).upper().startswith("CERTIFIED"):
                return None
            return HistoricalDatasetQualityStatus(
                dataset_id=dataset.dataset_id,
                ativo=dataset.ativo,
                timeframe=dataset.timeframe,
                provider=dataset.provider,
                start_date=dataset.start_date,
                end_date=dataset.end_date,
                total_candles=dataset.estimated_candles,
                quality_status="APPROVED",
                errors=[],
                last_validated_at=(
                    self._metadata_text(metadata, "imported_at")
                    or self._metadata_text(metadata, "updated_at")
                    or None
                ),
            )
        return None

    def _active_provider_dataset_id(self, records: list[object]) -> str | None:
        selected_id = self.selected_historical_dataset_id
        ranked: list[tuple[int, str]] = []
        for record in records:
            metadata = self._provider_metadata(record)
            dataset_id = self._dataset_id(metadata, record)
            if selected_id and selected_id == dataset_id:
                return dataset_id
            ranked.append((self._dataset_priority(metadata), dataset_id))
        if not ranked:
            return None
        return max(ranked, key=lambda item: item[0])[1]

    def _dataset_priority(self, metadata: dict[str, Any]) -> int:
        status = self._metadata_text(metadata, "quality_status").upper()
        readiness = self._metadata_text(metadata, "readiness_status").upper()
        asset = self._asset_from_metadata(metadata).upper()
        candles = self._candle_count(metadata) or 0
        priority = min(candles, 999_999)
        if readiness.startswith("VALIDATED"):
            priority += 1_000_000
        if status.startswith("CERTIFIED"):
            priority += 2_000_000
        if asset == "PETR4" and status.startswith("CERTIFIED"):
            priority += 3_000_000
        return priority

    def _active_dataset_data(
        self,
        record: object,
        metadata: dict[str, Any],
        selected: bool,
    ) -> ActiveDatasetDashboardData:
        status = self._dataset_status(metadata)
        certification = self._dataset_certification(metadata)
        return ActiveDatasetDashboardData(
            asset=self._asset_from_metadata(metadata),
            timeframe=self._metadata_text(metadata, "timeframe")
            or str(getattr(record, "timeframe", "N/D")),
            source=self._source_label(metadata),
            provider="HistoricalDataProvider",
            dataset_id=self._dataset_id(metadata, record),
            status=status,
            period=self._period_from_metadata(metadata),
            candles=self._candle_count(metadata),
            last_update=self._metadata_text(metadata, "imported_at")
            or self._metadata_text(metadata, "updated_at")
            or "N/D",
            checksum=self._checksum_from_metadata_or_file(metadata, record),
            metadata_version=self._metadata_text(metadata, "metadata_version")
            or self._metadata_text(metadata, "version")
            or "N/D",
            dataset_certification=certification,
            replay_status=self._readiness_status(certification, "Replay"),
            research_status=self._readiness_status(certification, "Research Lab"),
            architecture_status="OK",
            selected=selected,
        )

    def _dataset_id(self, metadata: dict[str, Any], record: object) -> str:
        dataset_id = self._metadata_text(metadata, "dataset_id")
        if dataset_id:
            return dataset_id
        return "_".join(
            str(getattr(record, name, "unknown"))
            for name in ("symbol", "timeframe", "period")
        )

    def _asset_from_metadata(self, metadata: dict[str, Any]) -> str:
        asset = self._metadata_text(metadata, "asset")
        if asset:
            return asset
        symbol = self._metadata_text(metadata, "symbol")
        if symbol:
            return symbol.split(".")[0]
        return "N/D"

    def _source_label(self, metadata: dict[str, Any]) -> str:
        source = self._metadata_text(metadata, "source")
        labels = {
            "YAHOO_FINANCE_CHART_API": "Yahoo Finance",
        }
        return labels.get(source, source or "N/D")

    def _dataset_status(self, metadata: dict[str, Any]) -> str:
        return (
            self._metadata_text(metadata, "quality_status")
            or self._metadata_text(metadata, "readiness_status")
            or "N/D"
        )

    def _dataset_certification(self, metadata: dict[str, Any]) -> str:
        status = self._metadata_text(metadata, "quality_status").upper()
        asset = self._asset_from_metadata(metadata).upper()
        if asset == "PETR4" and status.startswith("CERTIFIED"):
            return "PETR4_DATASET_CERTIFIED_FOR_QUANTITATIVE_RESEARCH"
        if status.startswith("CERTIFIED"):
            return "CERTIFIED_FOR_QUANTITATIVE_RESEARCH"
        return self._metadata_text(metadata, "readiness_status") or "N/D"

    def _period_from_metadata(self, metadata: dict[str, Any]) -> str:
        start = (
            self._metadata_text(metadata, "first_date")
            or self._metadata_text(metadata, "first_timestamp")
            or "N/D"
        )
        end = (
            self._metadata_text(metadata, "last_date")
            or self._metadata_text(metadata, "last_timestamp")
            or "N/D"
        )
        return f"{start} -> {end}"

    def _candle_count(self, metadata: dict[str, Any]) -> int | None:
        value = (
            metadata.get("record_count")
            if metadata.get("record_count") is not None
            else metadata.get("candle_count")
        )
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    def _checksum_from_metadata_or_file(
        self,
        metadata: dict[str, Any],
        record: object,
    ) -> str:
        checksum = self._metadata_text(metadata, "dataset_hash")
        if checksum:
            return checksum
        checksum_path = Path(str(getattr(record, "path", ""))) / "checksum.sha256"
        try:
            first_line = checksum_path.read_text(encoding="utf-8").splitlines()[0]
        except (OSError, IndexError):
            return "N/D"
        return first_line.split()[0] if first_line.strip() else "N/D"

    def _readiness_status(self, certification: str, target: str) -> str:
        if "CERTIFIED" in certification or "VALIDATED" in certification:
            return f"Pronto para {target}"
        return "N/D"

    def _metadata_text(self, metadata: dict[str, Any], key: str) -> str:
        value = metadata.get(key)
        return "" if value is None else str(value)

    def select_historical_dataset(
        self,
        dataset_id: str,
    ) -> HistoricalDatasetMetadata:
        """Seleciona um dataset historico sem executar fluxos."""
        metadata = self._get_historical_dataset_metadata(dataset_id)
        if metadata is None:
            raise ValueError(f"Dataset historico nao encontrado: {dataset_id}")
        object.__setattr__(self, "selected_historical_dataset_id", dataset_id)
        return metadata

    def get_selected_historical_dataset_id(self) -> str | None:
        """Retorna o identificador do dataset historico selecionado."""
        return self.selected_historical_dataset_id or self._default_dataset_id()

    def get_selected_historical_dataset(
        self,
    ) -> HistoricalDatasetMetadata | None:
        """Retorna metadados do dataset historico selecionado."""
        dataset_id = self.get_selected_historical_dataset_id()
        if dataset_id is None:
            return None
        return self._get_historical_dataset_metadata(dataset_id)

    def _default_dataset_id(self) -> str | None:
        active = self._get_active_dataset_dashboard_data()
        return None if active is None else active.dataset_id

    def _get_historical_dataset_metadata(
        self,
        dataset_id: str,
    ) -> HistoricalDatasetMetadata | None:
        for metadata in self.list_historical_datasets():
            if metadata.dataset_id == dataset_id:
                return metadata
        return None

    def get_selected_historical_dataset_quality_status(
        self,
    ) -> HistoricalDatasetQualityStatus | None:
        """Consulta ultimo status de qualidade conhecido do dataset ativo."""
        metadata = self.get_selected_historical_dataset()
        if metadata is None:
            return None
        return self.historical_dataset_quality_repository.get(
            metadata.dataset_id,
        )

    def list_historical_dataset_quality_validations(
        self,
        dataset_id: str,
    ) -> list[HistoricalDatasetQualityValidationRecord]:
        """Consulta historico de validacoes de qualidade por dataset."""
        return self.historical_dataset_quality_repository.list_validations(
            dataset_id,
        )

    def get_historical_dataset_health_summary(
        self,
    ) -> HistoricalDatasetHealthSummary:
        """Consolida saude geral dos datasets historicos catalogados."""
        datasets = self.list_historical_datasets()
        statuses = [
            self._historical_dataset_quality_status_or_provider(dataset)
            for dataset in datasets
        ]
        known_statuses = [status for status in statuses if status is not None]
        approved = [
            status
            for status in known_statuses
            if status.quality_status == "APPROVED"
        ]
        rejected = [
            status
            for status in known_statuses
            if status.quality_status == "REJECTED"
        ]
        return HistoricalDatasetHealthSummary(
            total_datasets=len(datasets),
            total_validated=len(known_statuses),
            total_approved=len(approved),
            total_rejected=len(rejected),
            total_unvalidated=len(datasets) - len(known_statuses),
            last_validation_at=self._last_validation_at(known_statuses),
        )

    def list_data_readiness_gate_logs(self) -> list[DataReadinessGateLog]:
        """Lista auditoria das avaliacoes do Data Readiness Gate."""
        return self.data_readiness_gate_logger.list_logs()

    def get_data_readiness_gate_metrics(self) -> DataReadinessGateMetrics:
        """Consolida metricas de auditoria do Data Readiness Gate."""
        logs = self.list_data_readiness_gate_logs()
        blocked_logs = [log for log in logs if log.decision == "BLOCKED"]
        last_blocked = self._last_gate_log(blocked_logs)
        return DataReadinessGateMetrics(
            total_evaluations=len(logs),
            total_allowed=len([log for log in logs if log.decision == "ALLOWED"]),
            total_blocked=len(blocked_logs),
            total_replay_evaluations=len(
                [log for log in logs if log.requested_action == "REPLAY"]
            ),
            total_research_evaluations=len(
                [log for log in logs if log.requested_action == "RESEARCH"]
            ),
            last_blocked_dataset_id=(
                None if last_blocked is None else last_blocked.dataset_id
            ),
            last_block_reason=(
                None if last_blocked is None
                else self._gate_log_reason(last_blocked)
            ),
            last_evaluation_at=self._last_gate_evaluation_at(logs),
        )

    def get_historical_provider_metrics(
        self,
    ) -> dict[str, dict[str, object]]:
        """Consolida saude e auditoria de datasets por provider historico."""
        empty_metrics = self._empty_historical_provider_metrics()

        provider_metrics_service = getattr(
            self,
            "historical_provider_metrics_service",
            None,
        )
        if provider_metrics_service is None:
            provider_metrics_service = getattr(
                self,
                "_historical_provider_metrics_service",
                None,
            )
        if provider_metrics_service is not None and hasattr(
            provider_metrics_service,
            "get_metrics",
        ):
            return provider_metrics_service.get_metrics()

        try:
            datasets = self.list_historical_datasets()
            statuses = [
                self._historical_dataset_quality_status_or_provider(dataset)
                for dataset in datasets
            ]
            known_statuses = [
                status for status in statuses if status is not None
            ]
            logs = self.list_data_readiness_gate_logs()
            providers = self._historical_provider_names(
                datasets,
                known_statuses,
                logs,
            )
            return {
                provider: self._historical_provider_metrics_dict(
                    self._historical_provider_metrics(
                        provider,
                        datasets,
                        known_statuses,
                        logs,
                    )
                )
                for provider in providers
            }
        except AttributeError:
            return {
                "csv": dict(empty_metrics),
                "parquet": dict(empty_metrics),
                "duckdb": dict(empty_metrics),
            }

    def get_selected_historical_dataset_readiness(
        self,
    ) -> HistoricalDatasetReadiness:
        """Classifica prontidao do dataset selecionado."""
        metadata = self.get_selected_historical_dataset()
        if metadata is None:
            raise ValueError("Nenhum dataset historico selecionado.")
        try:
            status = self.historical_dataset_quality_repository.get(
                metadata.dataset_id,
            )
            validations = (
                self.historical_dataset_quality_repository.list_validations(
                    metadata.dataset_id,
                )
            )
        except OSError as exc:
            return HistoricalDatasetReadiness(
                dataset_id=metadata.dataset_id,
                readiness="READINESS_UNAVAILABLE",
                reasons=[
                    "Arquivo de qualidade historica indisponivel para leitura.",
                    str(exc),
                ],
            )
        latest_validation = self._latest_validation(validations)
        if status is None and latest_validation is None:
            provider_readiness = self._readiness_from_provider_metadata(
                metadata.dataset_id
            )
            if provider_readiness is not None:
                return provider_readiness
        if status is None and latest_validation is None:
            return HistoricalDatasetReadiness(
                dataset_id=metadata.dataset_id,
                readiness="NOT_VALIDATED",
                reasons=["Dataset historico ainda nao validado."],
            )
        if latest_validation is None:
            return self._readiness_from_status(metadata.dataset_id, status)
        return self._readiness_from_validation(latest_validation)

    def load_selected_historical_dataset_to_replay(self) -> ReplayData:
        """Carrega Replay com o dataset historico selecionado."""
        self._ensure_selected_dataset_readiness(
            allowed={"READY_FOR_REPLAY", "READY_FOR_REPLAY_AND_RESEARCH"},
            action="REPLAY",
            workflow="Replay",
        )
        metadata = self.get_selected_historical_dataset()
        dataset = self._load_selected_historical_dataset()
        report = self._quality_report(metadata, dataset)
        self._persist_historical_dataset_quality(metadata, report)
        self._validate_historical_dataset_quality(report)
        return self.replay_service.load_historical_dataset(dataset)

    def list_available_replay_strategies(self) -> list[str]:
        """Lista estrategias registradas disponiveis para o Replay."""
        return self.replay_service.list_available_strategies()

    def get_active_replay_strategy_name(self) -> str:
        """Retorna a estrategia realmente executada pelo Replay."""
        return self.replay_service.get_active_strategy_name()

    def select_replay_strategy(self, strategy_name: str) -> ReplayData:
        """Seleciona a estrategia executada pelo Replay pela fachada."""
        return self.replay_service.select_strategy(strategy_name)

    def run_selected_historical_dataset_research_experiment(
        self,
        strategy_name: str = "alpha001_iorb",
        stop_points: float = 50.0,
        target_points: float = 100.0,
    ) -> ResearchExperimentData:
        """Executa Research Lab com o dataset historico selecionado."""
        self._ensure_selected_dataset_readiness(
            allowed={"READY_FOR_RESEARCH", "READY_FOR_REPLAY_AND_RESEARCH"},
            action="RESEARCH",
            workflow="Research Lab",
        )
        metadata = self.get_selected_historical_dataset()
        if metadata is None:
            raise ValueError("Nenhum dataset historico selecionado.")
        dataset = self._load_selected_historical_dataset()
        report = self._quality_report(metadata, dataset)
        self._persist_historical_dataset_quality(metadata, report)
        self._validate_historical_dataset_quality(report)
        source = self._selected_historical_dataset_source(metadata)
        return self.research_lab_service.run_historical_data_experiment(
            source=source,
            experiment_name=metadata.dataset_id,
            strategy_name=strategy_name,
            stop_points=stop_points,
            target_points=target_points,
            symbol=metadata.ativo,
            timeframe=metadata.timeframe,
        )

    def analyze_selected_historical_dataset_quality(
        self,
    ) -> HistoricalDatasetQualityReport:
        """Analisa qualidade do dataset historico selecionado."""
        metadata = self.get_selected_historical_dataset()
        dataset = self._load_selected_historical_dataset()
        report = self._quality_report(metadata, dataset)
        self._persist_historical_dataset_quality(metadata, report)
        return report

    def _quality_report(
        self,
        metadata: HistoricalDatasetMetadata | None,
        dataset: HistoricalDataset,
    ) -> HistoricalDatasetQualityReport:
        """Monta relatorio de qualidade a partir do dataset resolvido."""
        if metadata is None:
            raise ValueError("Nenhum dataset historico selecionado.")
        if dataset.is_empty:
            raise ValueError(self._historical_dataset_load_error())
        return HistoricalDatasetQualityReport(
            dataset_id=metadata.dataset_id,
            total_candles=dataset.total_candles,
            start_datetime=dataset.start_date,
            end_datetime=dataset.end_date,
            invalid_ohlc_candles=self._invalid_ohlc_candles(dataset.candles),
            invalid_volume_candles=self._invalid_volume_candles(dataset.candles),
            temporal_gaps=self._temporal_gaps(
                dataset.candles,
                metadata.timeframe,
            ),
            duplicate_timestamps=self._duplicate_timestamps(dataset.candles),
        )

    def _validate_historical_dataset_quality(
        self,
        report: HistoricalDatasetQualityReport,
    ) -> None:
        """Bloqueia execucao quando a qualidade minima nao for atendida."""
        issues = self._quality_blocking_errors(report)
        if not issues:
            return
        gap_notice = ""
        if report.temporal_gaps > 0:
            gap_notice = (
                f" Gaps temporais reportados: {report.temporal_gaps}."
            )
        raise ValueError(
            "Dataset historico reprovado no gate de qualidade: "
            + "; ".join(issues)
            + "."
            + gap_notice
        )

    def _persist_historical_dataset_quality(
        self,
        metadata: HistoricalDatasetMetadata | None,
        report: HistoricalDatasetQualityReport,
    ) -> None:
        """Persiste ultimo status conhecido sem armazenar candles."""
        if metadata is None:
            return
        status = HistoricalDatasetQualityStatus(
            dataset_id=metadata.dataset_id,
            ativo=metadata.ativo,
            timeframe=metadata.timeframe,
            provider=metadata.provider,
            start_date=report.start_datetime,
            end_date=report.end_datetime,
            total_candles=report.total_candles,
            quality_status=self._quality_status(report),
            errors=self._quality_findings(report),
            last_validated_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.historical_dataset_quality_repository.save(status)
        self.historical_dataset_quality_repository.append_validation(
            HistoricalDatasetQualityValidationRecord(
                dataset_id=metadata.dataset_id,
                validated_at=status.last_validated_at,
                quality_status=status.quality_status,
                total_candles=report.total_candles,
                invalid_ohlc_candles=report.invalid_ohlc_candles,
                invalid_volume_candles=report.invalid_volume_candles,
                temporal_gaps=report.temporal_gaps,
                duplicate_timestamps=report.duplicate_timestamps,
                messages=status.errors,
            )
        )

    def _quality_status(self, report: HistoricalDatasetQualityReport) -> str:
        if self._quality_blocking_errors(report):
            return "REJECTED"
        return "APPROVED"

    def _latest_validation(
        self,
        validations: list[HistoricalDatasetQualityValidationRecord],
    ) -> HistoricalDatasetQualityValidationRecord | None:
        if not validations:
            return None
        return max(validations, key=lambda record: record.validated_at)

    def _ensure_selected_dataset_readiness(
        self,
        allowed: set[str],
        action: str,
        workflow: str,
    ) -> None:
        readiness = self.get_selected_historical_dataset_readiness()
        decision = "ALLOWED" if readiness.readiness in allowed else "BLOCKED"
        self._log_data_readiness_gate(readiness, action, decision)
        if readiness.readiness in allowed:
            return
        reasons = "; ".join(readiness.reasons) or "sem motivo detalhado"
        raise ValueError(
            f"Dataset historico bloqueado para {workflow}: "
            f"{readiness.readiness}. Motivos: {reasons}"
        )

    def _log_data_readiness_gate(
        self,
        readiness: HistoricalDatasetReadiness,
        action: str,
        decision: str,
    ) -> None:
        metadata = self.get_selected_historical_dataset()
        provider = "unknown" if metadata is None else metadata.provider
        self.data_readiness_gate_logger.log(
            DataReadinessGateLog(
                dataset_id=readiness.dataset_id,
                evaluated_at=datetime.now().isoformat(timespec="seconds"),
                requested_action=action,
                readiness_status=readiness.readiness,
                decision=decision,
                provider=provider,
                reasons=list(readiness.reasons),
            )
        )

    def _last_gate_log(
        self,
        logs: list[DataReadinessGateLog],
    ) -> DataReadinessGateLog | None:
        if not logs:
            return None
        return max(logs, key=lambda log: log.evaluated_at)

    def _last_gate_evaluation_at(
        self,
        logs: list[DataReadinessGateLog],
    ) -> str | None:
        last_log = self._last_gate_log(logs)
        if last_log is None:
            return None
        return last_log.evaluated_at

    def _historical_provider_names(
        self,
        datasets: list[HistoricalDatasetMetadata],
        statuses: list[HistoricalDatasetQualityStatus],
        logs: list[DataReadinessGateLog],
    ) -> list[str]:
        default_providers = ["csv", "parquet", "duckdb"]
        providers = set(default_providers)
        providers.update(
            self._normalize_provider(dataset.provider) for dataset in datasets
        )
        providers.update(
            self._normalize_provider(status.provider) for status in statuses
        )
        providers.update(self._normalize_provider(log.provider) for log in logs)
        providers.discard("")
        providers.discard("unknown")
        extra_providers = sorted(
            provider
            for provider in providers
            if provider not in default_providers
        )
        return [
            provider
            for provider in default_providers
            if provider in providers
        ] + extra_providers

    def _historical_provider_metrics(
        self,
        provider: str,
        datasets: list[HistoricalDatasetMetadata],
        statuses: list[HistoricalDatasetQualityStatus],
        logs: list[DataReadinessGateLog],
    ) -> HistoricalProviderMetrics:
        provider_datasets = [
            dataset
            for dataset in datasets
            if self._normalize_provider(dataset.provider) == provider
        ]
        dataset_ids = {dataset.dataset_id for dataset in provider_datasets}
        provider_statuses = [
            status
            for status in statuses
            if status.dataset_id in dataset_ids
            and self._normalize_provider(status.provider) == provider
        ]
        provider_logs = [
            log
            for log in logs
            if self._normalize_provider(log.provider) == provider
        ]
        approved_statuses = [
            status
            for status in provider_statuses
            if status.quality_status == "APPROVED"
        ]
        rejected_statuses = [
            status
            for status in provider_statuses
            if status.quality_status == "REJECTED"
        ]
        allowed_logs = [log for log in provider_logs if log.decision == "ALLOWED"]
        blocked_logs = [log for log in provider_logs if log.decision == "BLOCKED"]
        return HistoricalProviderMetrics(
            provider=provider,
            total_datasets=len(provider_datasets),
            total_validated=len(provider_statuses),
            total_approved=len(approved_statuses),
            total_rejected=len(rejected_statuses),
            total_unvalidated=len(provider_datasets) - len(provider_statuses),
            total_gate_evaluations=len(provider_logs),
            total_allowed=len(allowed_logs),
            total_blocked=len(blocked_logs),
            last_validation_at=self._last_validation_at(provider_statuses),
            last_gate_evaluation_at=self._last_gate_evaluation_at(provider_logs),
        )

    def _historical_provider_metrics_dict(
        self,
        metric: HistoricalProviderMetrics,
    ) -> dict[str, object]:
        return {
            "total_datasets": metric.total_datasets,
            "validated_datasets": metric.total_validated,
            "approved_datasets": metric.total_approved,
            "rejected_datasets": metric.total_rejected,
            "not_validated_datasets": metric.total_unvalidated,
            "gate_evaluations": metric.total_gate_evaluations,
            "allowed": metric.total_allowed,
            "blocked": metric.total_blocked,
            "last_validation_at": metric.last_validation_at,
            "last_gate_evaluation_at": metric.last_gate_evaluation_at,
        }

    def _empty_historical_provider_metrics(self) -> dict[str, object]:
        return {
            "total_datasets": 0,
            "validated_datasets": 0,
            "approved_datasets": 0,
            "rejected_datasets": 0,
            "not_validated_datasets": 0,
            "gate_evaluations": 0,
            "allowed": 0,
            "blocked": 0,
            "last_validation_at": None,
            "last_gate_evaluation_at": None,
        }

    def _normalize_provider(self, provider: str | None) -> str:
        if provider is None:
            return ""
        return provider.strip().lower()

    def _gate_log_reason(self, log: DataReadinessGateLog) -> str | None:
        if not log.reasons:
            return None
        return "; ".join(log.reasons)

    def _readiness_from_status(
        self,
        dataset_id: str,
        status: HistoricalDatasetQualityStatus | None,
    ) -> HistoricalDatasetReadiness:
        if status is None:
            return HistoricalDatasetReadiness(
                dataset_id=dataset_id,
                readiness="NOT_VALIDATED",
                reasons=["Dataset historico ainda nao validado."],
            )
        if status.quality_status == "REJECTED" or status.errors:
            return HistoricalDatasetReadiness(
                dataset_id=dataset_id,
                readiness="NOT_READY",
                reasons=list(status.errors),
            )
        if status.total_candles <= 0:
            return HistoricalDatasetReadiness(
                dataset_id=dataset_id,
                readiness="NOT_READY",
                reasons=["Dataset historico sem candles suficientes."],
            )
        if status.total_candles == 1:
            return HistoricalDatasetReadiness(
                dataset_id=dataset_id,
                readiness="READY_FOR_REPLAY",
                reasons=["Amostra insuficiente para Research Lab."],
            )
        return HistoricalDatasetReadiness(
            dataset_id=dataset_id,
            readiness="READY_FOR_REPLAY_AND_RESEARCH",
            reasons=[],
        )

    def _readiness_from_validation(
        self,
        validation: HistoricalDatasetQualityValidationRecord,
    ) -> HistoricalDatasetReadiness:
        critical_errors = self._readiness_critical_errors(validation)
        if critical_errors:
            return HistoricalDatasetReadiness(
                dataset_id=validation.dataset_id,
                readiness="NOT_READY",
                reasons=critical_errors,
            )
        if validation.total_candles == 1:
            return HistoricalDatasetReadiness(
                dataset_id=validation.dataset_id,
                readiness="READY_FOR_REPLAY",
                reasons=["Amostra insuficiente para Research Lab."],
            )
        if validation.temporal_gaps > 0:
            return HistoricalDatasetReadiness(
                dataset_id=validation.dataset_id,
                readiness="READY_FOR_RESEARCH",
                reasons=[
                    f"{validation.temporal_gaps} gap(s) temporal(is) reportado(s)."
                ],
            )
        return HistoricalDatasetReadiness(
            dataset_id=validation.dataset_id,
            readiness="READY_FOR_REPLAY_AND_RESEARCH",
            reasons=[],
        )

    def _readiness_critical_errors(
        self,
        validation: HistoricalDatasetQualityValidationRecord,
    ) -> list[str]:
        issues = []
        if validation.quality_status == "REJECTED":
            issues.extend(validation.messages)
        if validation.total_candles <= 0:
            issues.append("Dataset historico sem candles suficientes.")
        if validation.invalid_ohlc_candles > 0:
            issues.append(
                f"{validation.invalid_ohlc_candles} candle(s) com OHLC invalido."
            )
        if validation.invalid_volume_candles > 0:
            issues.append(
                f"{validation.invalid_volume_candles} candle(s) com volume invalido."
            )
        if validation.duplicate_timestamps > 0:
            issues.append(
                f"{validation.duplicate_timestamps} timestamp(s) duplicado(s)."
            )
        return list(dict.fromkeys(issues))

    def _last_validation_at(
        self,
        statuses: list[HistoricalDatasetQualityStatus],
    ) -> str | None:
        values = [
            status.last_validated_at
            for status in statuses
            if status.last_validated_at
        ]
        if not values:
            return None
        return max(values)

    def _quality_findings(
        self,
        report: HistoricalDatasetQualityReport,
    ) -> list[str]:
        findings = self._quality_blocking_errors(report)
        if report.temporal_gaps > 0:
            findings.append(
                f"{report.temporal_gaps} gap(s) temporal(is) detectado(s)"
            )
        return findings

    def _quality_blocking_errors(
        self,
        report: HistoricalDatasetQualityReport,
    ) -> list[str]:
        issues = []
        if report.total_candles <= 0:
            issues.append("total de candles igual a zero")
        if report.duplicate_timestamps > 0:
            issues.append(
                f"{report.duplicate_timestamps} timestamp(s) duplicado(s)"
            )
        if report.invalid_ohlc_candles > 0:
            issues.append(
                f"{report.invalid_ohlc_candles} candle(s) com OHLC invalido"
            )
        if report.invalid_volume_candles > 0:
            issues.append(
                f"{report.invalid_volume_candles} candle(s) com volume invalido"
            )
        return issues

    def start_replay(self) -> ReplayData:
        """Inicia o replay por meio da fachada."""
        return self.replay_service.start()

    def stop_replay(self) -> ReplayData:
        """Para o replay por meio da fachada."""
        return self.replay_service.stop()

    def reset_replay(self) -> ReplayData:
        """Reinicia o replay por meio da fachada."""
        return self.replay_service.reset()

    def next_replay_candle(self) -> ReplayData:
        """Avanca o replay por meio da fachada."""
        return self.replay_service.next_candle()

    def enable_replay_auto_run(self, speed_seconds: float) -> ReplayData:
        """Ativa auto replay por meio da fachada."""
        return self.replay_service.enable_auto_run(speed_seconds)

    def disable_replay_auto_run(self) -> ReplayData:
        """Desativa auto replay por meio da fachada."""
        return self.replay_service.disable_auto_run()

    def is_replay_auto_run_enabled(self) -> bool:
        """Consulta auto replay por meio da fachada."""
        return self.replay_service.is_auto_run_enabled()

    def run_demo_research_experiment(self) -> ResearchExperimentData:
        """Executa experimento demo do Research Lab pela fachada."""
        return self.research_lab_service.run_demo_experiment()

    def run_demo_alpha001_experiment(self) -> ResearchExperimentData:
        """Executa Alpha001Experiment demo pela fachada."""
        return self.research_lab_service.run_demo_alpha001_experiment()

    def list_research_experiments(self) -> list[ResearchExperimentData]:
        """Lista experimentos do Research Lab pela fachada."""
        return self.research_lab_service.list_experiments()

    def last_research_experiment(self) -> ResearchExperimentData | None:
        """Retorna ultimo experimento do Research Lab pela fachada."""
        return self.research_lab_service.last_experiment()

    def clear_research_experiments(self) -> None:
        """Limpa experimentos do Research Lab pela fachada."""
        self.research_lab_service.clear()

    def run_demo_research_benchmarks(self) -> list[BenchmarkData]:
        """Executa benchmarks demo pela fachada."""
        return self.research_lab_service.run_demo_benchmarks()

    def compare_research_benchmarks(self) -> BenchmarkComparisonData:
        """Compara benchmarks do Research Lab pela fachada."""
        return self.research_lab_service.compare_benchmarks()

    def last_benchmark_comparison(self) -> BenchmarkComparisonData | None:
        """Retorna ultima comparacao de benchmarks pela fachada."""
        return self.research_lab_service.last_comparison()

    def list_research_benchmarks(self) -> list[BenchmarkData]:
        """Lista benchmarks do Research Lab pela fachada."""
        return self.research_lab_service.list_benchmarks()

    def list_available_research_strategies(self) -> list[str]:
        """Lista estrategias disponiveis para Research Lab pela fachada."""
        return self.research_lab_service.list_available_strategies()

    def get_alpha001_status(self) -> Alpha001StatusData:
        """Retorna status da Alpha 001 para exibicao no dashboard."""
        return Alpha001StatusData()

    def get_alpha001_paper_status(self) -> Alpha001PaperStatusData:
        """Retorna estado paper Alpha001 pela fachada do dashboard."""
        position = self._paper_position_data(
            self.paper_trading_engine.current_position,
        )
        trades = [
            self._paper_trade_data(trade)
            for trade in self.paper_trading_engine.trades_history
        ]
        equity_curve = list(self.paper_trading_engine.equity_curve)
        return Alpha001PaperStatusData(
            position=position,
            trades_history=trades,
            equity_curve=equity_curve,
            accumulated_result_points=equity_curve[-1],
            total_trades=len(trades),
        )

    def get_alpha001_paper_report(self) -> Alpha001PaperReportData:
        """Retorna relatorio paper Alpha001 pela fachada do dashboard."""
        return self._paper_report_data(
            self.paper_trading_service.generate_report(),
        )

    def process_alpha001_paper_signal(
        self,
        strategy_signal: StrategySignal,
        market_snapshot: MarketSnapshot,
    ) -> Alpha001PaperStatusData:
        """Processa sinal paper Alpha001 sem expor o engine ao dashboard."""
        result = self.paper_trading_engine.process(
            strategy_signal,
            market_snapshot,
        )
        return self._paper_status_from_result(result)

    def get_alpha001_research_report(self) -> Alpha001ResearchReportData:
        """Retorna relatorio de pesquisa da Alpha 001 pela fachada."""
        return self.research_lab_service.alpha001_research_report()

    def run_alpha001_parameter_ranking(
        self,
    ) -> list[Alpha001ParameterRankingData]:
        """Executa ranking Alpha 001 pela fachada."""
        return self.research_lab_service.run_alpha001_parameter_ranking()

    def list_alpha001_parameter_ranking(
        self,
    ) -> list[Alpha001ParameterRankingData]:
        """Lista ranking Alpha 001 pela fachada."""
        return self.research_lab_service.list_alpha001_parameter_ranking()

    def get_alpha001_research_summary(self) -> Alpha001ResearchSummaryData:
        """Retorna resumo estatistico Alpha 001 pela fachada."""
        return self.research_lab_service.get_alpha001_research_summary()

    def get_alpha001_robustness(self) -> Alpha001RobustnessData:
        """Retorna analise de robustez Alpha 001 pela fachada."""
        return self.research_lab_service.get_alpha001_robustness()

    def get_research_report(self) -> ResearchReportData:
        """Retorna relatorio consolidado de experimento pela fachada."""
        return self.research_lab_service.research_report()

    def filter_alpha001_parameter_ranking(
        self,
        validation_status: str,
    ) -> list[Alpha001ParameterRankingData]:
        """Filtra ranking Alpha 001 ja existente por status."""
        ranking = self.list_alpha001_parameter_ranking()
        normalized = validation_status.upper()
        if normalized == "ALL":
            return ranking
        if normalized == "REJECTED":
            return [
                result for result in ranking
                if result.validation_status != "APPROVED"
            ]
        return [
            result for result in ranking
            if result.validation_status == normalized
        ]

    def export_alpha001_results_to_csv(self, output_path: object) -> object:
        """Exporta resultados Alpha 001 para CSV pela fachada."""
        return self.research_lab_service.export_alpha001_results_to_csv(
            output_path,
        )

    def run_demo_parameter_grid(self) -> list[ParameterGridData]:
        """Executa grade demo de parametros pela fachada."""
        return self.research_lab_service.run_demo_parameter_grid()

    def list_parameter_grid_results(self) -> list[ParameterGridData]:
        """Lista resultados da grade pela fachada."""
        return self.research_lab_service.list_parameter_grid_results()

    def best_parameter_grid_result(self) -> ParameterGridData | None:
        """Retorna melhor combinacao da grade pela fachada."""
        return self.research_lab_service.best_parameter_grid_result()

    def validate_research_benchmarks(self) -> list[ExperimentValidationData]:
        """Valida benchmarks do Research Lab pela fachada."""
        return self.research_lab_service.validate_all_benchmarks()

    def list_benchmark_validations(self) -> list[ExperimentValidationData]:
        """Lista validacoes estatisticas pela fachada."""
        return self.research_lab_service.list_validations()

    def last_benchmark_validation(self) -> ExperimentValidationData | None:
        """Retorna ultima validacao estatistica pela fachada."""
        return self.research_lab_service.last_validation()

    def _to_regime(self, snapshot: MarketSnapshot | None) -> RegimeData | None:
        if snapshot is None:
            return None
        return self.regime_service.analyze(snapshot)

    def _load_selected_historical_dataset(self) -> HistoricalDataset:
        metadata = self.get_selected_historical_dataset()
        if metadata is None:
            raise ValueError("Nenhum dataset historico selecionado.")
        source = self._selected_historical_dataset_source(metadata)
        return self.historical_data_provider.load(
            source,
            symbol=metadata.ativo,
            timeframe=metadata.timeframe,
        )

    def _selected_historical_dataset_source(
        self,
        metadata: HistoricalDatasetMetadata,
    ) -> object:
        source = self.historical_dataset_catalog.get_dataset_source(
            metadata.dataset_id
        )
        if source is not None:
            return source
        provider_source = self._provider_dataset_source(metadata.dataset_id)
        if provider_source is not None:
            return provider_source
        return metadata.dataset_id

    def _provider_dataset_source(self, dataset_id: str) -> str | None:
        for record in self._provider_dataset_records():
            metadata = self._provider_metadata(record)
            if self._dataset_id(metadata, record) != dataset_id:
                continue
            file_name = metadata.get("file_path") or metadata.get("data_file")
            if isinstance(file_name, str) and file_name.strip():
                return f"{getattr(record, 'path', '')}/{file_name}"
        return None

    def _readiness_from_provider_metadata(
        self,
        dataset_id: str,
    ) -> HistoricalDatasetReadiness | None:
        for record in self._provider_dataset_records():
            metadata = self._provider_metadata(record)
            if self._dataset_id(metadata, record) != dataset_id:
                continue
            status = self._dataset_status(metadata).upper()
            if status.startswith("CERTIFIED"):
                return HistoricalDatasetReadiness(
                    dataset_id=dataset_id,
                    readiness="READY_FOR_REPLAY_AND_RESEARCH",
                    reasons=[],
                )
            readiness = self._metadata_text(metadata, "readiness_status").upper()
            if readiness.startswith("VALIDATED"):
                return HistoricalDatasetReadiness(
                    dataset_id=dataset_id,
                    readiness="READY_FOR_REPLAY_AND_RESEARCH",
                    reasons=[],
                )
            return None
        return None

    def _historical_dataset_load_error(self) -> str:
        errors = getattr(self.historical_data_provider, "errors", [])
        if errors:
            return "; ".join(errors)
        return "Dataset historico selecionado sem candles."

    def _invalid_ohlc_candles(self, candles: list[object]) -> int:
        return len([candle for candle in candles if not self._ohlc_is_valid(candle)])

    def _ohlc_is_valid(self, candle: object) -> bool:
        abertura = getattr(candle, "abertura", None)
        maxima = getattr(candle, "maxima", None)
        minima = getattr(candle, "minima", None)
        fechamento = getattr(candle, "fechamento", None)
        if None in {abertura, maxima, minima, fechamento}:
            return False
        return (
            maxima >= minima
            and maxima >= abertura
            and maxima >= fechamento
            and minima <= abertura
            and minima <= fechamento
        )

    def _invalid_volume_candles(self, candles: list[object]) -> int:
        return len(
            [
                candle
                for candle in candles
                if not self._volume_is_valid(getattr(candle, "volume", None))
            ]
        )

    def _volume_is_valid(self, volume: object | None) -> bool:
        if volume is None:
            return False
        try:
            return float(volume) >= 0
        except (TypeError, ValueError):
            return False

    def _duplicate_timestamps(self, candles: list[object]) -> int:
        timestamps = [getattr(candle, "data", None) for candle in candles]
        seen = set()
        duplicates = 0
        for timestamp in timestamps:
            if timestamp in seen:
                duplicates += 1
            seen.add(timestamp)
        return duplicates

    def _temporal_gaps(self, candles: list[object], timeframe: str) -> int:
        expected_minutes = self._timeframe_minutes(timeframe)
        if expected_minutes is None:
            return 0
        datetimes = [
            self._parse_candle_datetime(getattr(candle, "data", ""))
            for candle in candles
        ]
        valid_datetimes = [value for value in datetimes if value is not None]
        gaps = 0
        for previous, current in zip(valid_datetimes, valid_datetimes[1:]):
            delta_minutes = (current - previous).total_seconds() / 60
            if delta_minutes > expected_minutes:
                gaps += 1
        return gaps

    def _timeframe_minutes(self, timeframe: str) -> int | None:
        normalized = timeframe.strip().lower()
        if not normalized.endswith("m"):
            return None
        try:
            return int(normalized[:-1])
        except ValueError:
            return None

    def _parse_candle_datetime(self, value: str) -> datetime | None:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                return datetime.strptime(value, fmt)
            except (TypeError, ValueError):
                continue
        return None

    def _is_uploaded_csv(self, value: object) -> bool:
        return hasattr(value, "getvalue") or hasattr(value, "read")

    def _load_uploaded_replay_csv(self, uploaded_file: object) -> ReplayData:
        temp_path = self._write_uploaded_csv(uploaded_file)
        try:
            return self.replay_service.load_historical_csv(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def _write_uploaded_csv(self, uploaded_file: object) -> Path:
        suffix = self._uploaded_suffix(uploaded_file)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(self._uploaded_bytes(uploaded_file))
            return Path(handle.name)

    def _uploaded_suffix(self, uploaded_file: object) -> str:
        name = str(getattr(uploaded_file, "name", "historical.csv"))
        suffix = Path(name).suffix
        if suffix.lower() == ".csv":
            return suffix
        return ".csv"

    def _uploaded_bytes(self, uploaded_file: object) -> bytes:
        if hasattr(uploaded_file, "getvalue"):
            content = uploaded_file.getvalue()
        else:
            content = uploaded_file.read()
        if isinstance(content, str):
            return content.encode("utf-8")
        return bytes(content)

    def _paper_status_from_result(
        self,
        result: PaperTradingResult,
    ) -> Alpha001PaperStatusData:
        trades = [self._paper_trade_data(trade) for trade in result.trades_history]
        return Alpha001PaperStatusData(
            position=self._paper_position_data(result.position),
            trades_history=trades,
            equity_curve=list(result.equity_curve),
            accumulated_result_points=result.equity_curve[-1],
            total_trades=len(trades),
        )

    def _paper_report_data(
        self,
        report: PaperTradingReport,
    ) -> Alpha001PaperReportData:
        return Alpha001PaperReportData(
            status=report.status,
            total_operations=report.total_operations,
            paper_win_rate=float(report.paper_win_rate),
            accumulated_result_points=float(report.accumulated_result_points),
            max_drawdown_points=float(report.max_drawdown_points),
            max_loss_sequence=report.max_loss_sequence,
            current_position=self._paper_position_data(
                report.current_position,
            ),
        )

    def _paper_position_data(
        self,
        position: object | None,
    ) -> Alpha001PaperPositionData | None:
        if position is None:
            return None
        return Alpha001PaperPositionData(
            side=position.side,
            quantity=position.quantity,
            entry_price=float(position.entry_price),
            stop=float(position.stop),
            target=float(position.target),
            status=getattr(position, "status", "OPEN"),
            exit_price=getattr(position, "exit_price", None),
            result_points=float(getattr(position, "result_points", 0.0)),
            close_reason=getattr(position, "close_reason", None),
        )

    def _paper_trade_data(self, trade: object) -> Alpha001PaperTradeData:
        return Alpha001PaperTradeData(
            side=trade.side,
            quantity=trade.quantity,
            entry_price=float(trade.entry_price),
            exit_price=float(trade.exit_price),
            result_points=float(trade.result_points),
            close_reason=trade.close_reason,
        )

    def _to_research(
        self,
        snapshot: MarketSnapshot | None,
    ) -> ResearchData | None:
        if snapshot is None and not self._has_research_inputs():
            return None
        return self.research_service.analyze(
            self._research_feature_snapshot(snapshot),
            self._research_regime_analysis(snapshot),
            self._research_market_memory(),
        )

    def _has_research_inputs(self) -> bool:
        return (
            self.feature_snapshot is not None
            and self.regime_analysis is not None
            and self.market_memory is not None
        )

    def _research_feature_snapshot(
        self,
        snapshot: MarketSnapshot | None,
    ) -> FeatureSnapshot:
        if self.feature_snapshot is not None:
            return self.feature_snapshot
        return FeatureSnapshot(
            momentum=self._demo_momentum(snapshot),
            average_range=self._demo_average_range(snapshot),
            highest_high=None,
            lowest_low=None,
            direction=self._demo_direction(snapshot),
            candles_count=20,
            trend_strength=self._demo_trend_strength(snapshot),
            volatility_level=self._demo_volatility_level(snapshot),
        )

    def _research_regime_analysis(
        self,
        snapshot: MarketSnapshot | None,
    ) -> RegimeAnalysis:
        if self.regime_analysis is not None:
            return self.regime_analysis
        return RegimeAnalysis(
            regime=self._demo_regime(snapshot),
            confidence=0.70,
            description="Pesquisa quantitativa demonstrativa.",
        )

    def _research_market_memory(self) -> MarketMemory:
        if self.market_memory is not None:
            return self.market_memory
        return build_demo_market_memory()

    def _demo_direction(self, snapshot: MarketSnapshot | None) -> str:
        if snapshot and snapshot.regime.upper() == "BAIXA":
            return "DOWN"
        if snapshot and snapshot.regime.upper() == "ALTA":
            return "UP"
        return "SIDEWAYS"

    def _demo_momentum(self, snapshot: MarketSnapshot | None) -> float:
        direction = self._demo_direction(snapshot)
        if direction == "UP":
            return 10.0
        if direction == "DOWN":
            return -10.0
        return 0.0

    def _demo_average_range(self, snapshot: MarketSnapshot | None) -> float:
        if snapshot is None:
            return 10.0
        return snapshot.volatility

    def _demo_trend_strength(self, snapshot: MarketSnapshot | None) -> float:
        if snapshot is None:
            return 0.90
        return snapshot.trend_strength

    def _demo_volatility_level(self, snapshot: MarketSnapshot | None) -> str:
        if snapshot is None:
            return "MEDIUM"
        if snapshot.volatility < 10:
            return "LOW"
        if snapshot.volatility < 30:
            return "MEDIUM"
        return "HIGH"

    def _demo_regime(self, snapshot: MarketSnapshot | None) -> MarketRegime:
        if snapshot is None:
            return MarketRegime.TREND
        if snapshot.trend_strength >= 0.70:
            return MarketRegime.TREND
        if snapshot.volatility >= 80:
            return MarketRegime.HIGH_VOLATILITY
        if snapshot.volatility <= 15:
            return MarketRegime.LOW_VOLATILITY
        if snapshot.regime.upper() == "RANGE":
            return MarketRegime.RANGE
        return MarketRegime.UNKNOWN

    def _to_signal(
        self,
        snapshot: MarketSnapshot | None,
    ) -> StrategySignal | None:
        if snapshot is None:
            return None

        score = int(snapshot.market_dna_score)
        return StrategySignal(
            decision="WAIT",
            score=score,
            confidence=0.0,
            reasons=["Dashboard snapshot"],
        )
