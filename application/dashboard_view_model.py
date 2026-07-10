"""Contrato unico de ViewModel para o Dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo


DASHBOARD_VIEW_MODEL_CONTRACT_VERSION = "1.0"


def format_dashboard_timestamp(value: object) -> str:
    """Converte timestamp tecnico UTC em horario amigavel do dashboard."""
    text = str(value or "").strip()
    if not text or text == "N/D":
        return "N/D"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%d/%m/%Y %H:%M")
        except ValueError:
            return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    try:
        local_tz = ZoneInfo("America/Sao_Paulo")
    except Exception:
        local_tz = timezone(timedelta(hours=-3), name="BRT")
    local_time = parsed.astimezone(local_tz)
    return local_time.strftime("%d/%m/%Y %H:%M")


@dataclass(frozen=True)
class DashboardSystemStatusViewModel:
    """Estado geral do sistema para exibicao."""

    status: str = "N/D"
    active_symbol: str = "N/D"
    version: str = "N/D"
    event_count: int = 0
    loaded_strategies_count: int = 0


@dataclass(frozen=True)
class DashboardReplayStatusViewModel:
    """Estado do Replay para exibicao."""

    status: str = "N/D"
    total_candles: int = 0
    current_index: int = -1
    active_strategy_name: str = "N/D"
    active_strategy_label: str = "N/D"
    last_decision: str = "N/D"
    is_running: bool = False


@dataclass(frozen=True)
class DashboardLiveResearchStatusViewModel:
    """Estado live read-only para exibicao."""

    symbol: str = "N/D"
    timeframe: str = "N/D"
    candles_ingested: int = 0
    strategies_evaluated: int = 0
    strategy_signals: int = 0
    decision_contexts: int = 0
    last_decision: str = "N/D"
    last_confidence: float = 0.0
    read_only: bool = True
    has_data: bool = False


@dataclass(frozen=True)
class DashboardLiveSessionSummaryViewModel:
    """Resumo da sessao live para exibicao."""

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
class DashboardLiveSignalQualityViewModel:
    """Linha de qualidade de sinal por estrategia."""

    strategy_name: str = "N/D"
    signal_count: int = 0
    buy_count: int = 0
    sell_count: int = 0
    wait_count: int = 0
    average_confidence: float = 0.0
    last_decision: str = "N/D"


@dataclass(frozen=True)
class DashboardLiveHistoryViewModel:
    """Linha de historico live para exibicao."""

    timestamp: str = "N/D"
    symbol: str = "N/D"
    timeframe: str = "N/D"
    decision: str = "N/D"
    confidence: float = 0.0
    strategy_signals: int = 0
    decision_contexts: int = 0


@dataclass(frozen=True)
class DashboardResearchStatusViewModel:
    """Estado do Research Lab para exibicao."""

    experiments_count: int = 0
    benchmarks_count: int = 0
    validations_count: int = 0
    last_experiment_name: str = "N/D"
    live_signals_count: int = 0


@dataclass(frozen=True)
class DashboardSafetyStatusViewModel:
    """Estado de seguranca operacional para exibicao."""

    status: str = "READ ONLY"
    read_only: bool = True
    real_trading_authorized: bool = False
    broker_integrated: bool = False
    order_execution_enabled: bool = False


@dataclass(frozen=True)
class DashboardMT5CandleViewModel:
    """Candle MT5 read-only para exibicao."""

    timestamp: str = "N/D"
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0


@dataclass(frozen=True)
class DashboardMT5MarketDataViewModel:
    """Estado read-only da conexao MT5 para exibicao."""

    connection_status: str = "DISCONNECTED"
    server: str = "N/D"
    account: str = "N/D"
    account_type: str = "N/D"
    available_symbols: list[str] = field(default_factory=list)
    supported_symbols: list[str] = field(default_factory=list)
    selected_symbol: str = "EURUSD"
    supported_timeframes: list[str] = field(default_factory=list)
    selected_timeframe: str = "M1"
    candles_loaded: int = 0
    last_candle: DashboardMT5CandleViewModel | None = None
    candles: list[DashboardMT5CandleViewModel] = field(default_factory=list)
    message: str = "MT5 nao conectado."
    read_only_status: str = "SOMENTE MARKET DATA"
    real_operation_authorized: bool = False


@dataclass(frozen=True)
class DashboardMT5DiagnosticStepViewModel:
    """Etapa do diagnostico de conexao MT5 para exibicao."""

    name: str = "N/D"
    status: str = "FALHOU"
    message: str = ""
    last_error_code: int | None = None
    last_error_message: str = ""


@dataclass(frozen=True)
class DashboardMT5ConnectionDiagnosticViewModel:
    """Diagnostico detalhado da conexao MT5."""

    connection_status: str = "OFFLINE"
    steps: list[DashboardMT5DiagnosticStepViewModel] = field(default_factory=list)
    last_error_code: int | None = None
    last_error_message: str = ""
    terminal_path: str = "N/D"
    build: str = "N/D"
    server: str = "N/D"
    account: str = "N/D"
    connected: bool = False
    trade_allowed: bool = False
    community_connection: bool = False
    failed_call: str = ""
    diagnostic_message: str = "Diagnostico MT5 nao executado."
    executed_at: str = ""


@dataclass(frozen=True)
class DashboardMT5ForexSignalRowViewModel:
    """Linha Forex MT5 com decisao read-only."""

    pair: str = "N/D"
    status: str = "N/D"
    last_price: float | None = None
    last_candle_time: str = "N/D"
    trend: str = "INDEFINIDA"
    momentum: float | None = None
    volatility: float | None = None
    rsi: float | None = None
    short_average: float | None = None
    long_average: float | None = None
    active_model: str = "TREND_MOMENTUM"
    active_model_score: float = 0.0
    active_model_indicators: tuple[str, ...] = ()
    lab_alpha_id: str = "ALPHA001"
    lab_timeframe: str = "M1"
    lab_parameters: dict[str, str] = field(default_factory=dict)
    lab_configuration_source: str = "DEFAULT"
    decision: str = "WAIT"
    confidence: float = 0.0
    lab_confidence: float = 0.0
    lab_ict_score: float = 0.0
    lab_ict_grade: str = "E"
    lab_ict_status: str = "REJEITADA"
    lab_ict_usage: str = "Rejeitada."
    lab_ict_demo_allowed: bool = False
    lab_ict_rejection_reasons: tuple[str, ...] = ()
    reason: str = "Aguardando dados MT5."
    mid_average: float | None = None
    ema_fast: float | None = None
    ema_mid: float | None = None
    ema_slow: float | None = None
    adx: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    atr: float | None = None
    atr_average: float | None = None
    bollinger_upper: float | None = None
    bollinger_lower: float | None = None
    tick_volume: int | None = None
    tick_volume_average: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    donchian_high: float | None = None
    donchian_low: float | None = None
    pivot: float | None = None
    vwap: float | None = None
    z_score: float | None = None
    support: float | None = None
    resistance: float | None = None
    swing_high: float | None = None
    swing_low: float | None = None
    spread: float | None = None
    spread_average: float | None = None
    slippage_estimate: float | None = None
    price_speed: float | None = None
    candles_loaded: int = 0
    sample_size: int = 0
    win_rate: float = 0.0
    avg_return: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    matched_context_count: int = 0
    rejected_reason: str = ""
    volatility_bucket: str = "UNKNOWN"
    rsi_bucket: str = "UNKNOWN"
    momentum_sign: str = "ZERO"
    ma_distance_bucket: str = "FLAT"
    confidence_penalties: tuple[str, ...] = ()
    confidence_drivers: tuple[str, ...] = ()
    timeframe: str = "M1"
    configured_candles: int = 0
    requested_candles: int = 0
    received_candles: int = 0
    research_candles_used: int = 0
    last_update: str = ""
    diagnostics_status: str = "ERRO"
    diagnostics_log: str = ""
    theoretical_entry_status: str = "SEM_GATILHO"
    theoretical_entry_candle: str = "N/D"
    theoretical_entry_price: float | None = None
    theoretical_entry_direction: str = "WAIT"
    theoretical_entry_reason: str = "Nenhum gatilho teorico detectado."
    research_plan_status: str = "SEM_PLANO"
    research_plan_source: str = "RESEARCH_LAB"
    research_plan_entry_price: float | None = None
    research_plan_stop: float | None = None
    research_plan_target: float | None = None
    research_plan_risk_reward: float = 0.0
    research_plan_stop_multiplier: float = 0.0
    research_plan_exit_model: str = "NONE"
    research_plan_exit_score: float = 0.0
    research_plan_exit_candidates: int = 0
    research_plan_risk_pips: float = 0.0
    research_plan_reward_pips: float = 0.0
    research_plan_risk_percent: float = 0.0
    research_plan_reward_percent: float = 0.0
    research_plan_stop_reason: str = ""
    research_plan_target_reason: str = ""
    research_plan_stop_management: str = "FIXED_STOP"
    research_plan_stop_management_parameters: dict[str, str] = field(
        default_factory=dict
    )
    research_plan_stop_management_reason: str = "Gestao fixa por compatibilidade."
    dynamic_exit_policy: str = "FIXED_STOP"
    dynamic_exit_action: str = "KEEP_ORIGINAL_PLAN"
    dynamic_exit_reason: str = "Saida dinamica read-only ainda sem ajuste operacional."
    dynamic_exit_confidence: float = 0.0
    dynamic_exit_market_state: str = "NO_POSITION"
    dynamic_exit_r_multiple: float = 0.0
    dynamic_exit_candidate_stop: float | None = None
    dynamic_exit_allowed_to_execute_demo: bool = False
    dynamic_exit_source: str = "DYNAMIC_EXIT_READ_ONLY"
    dynamic_exit_simulation_enabled: bool = True
    dynamic_exit_simulation_allowed: bool = False
    dynamic_exit_simulation_current_stop: float | None = None
    dynamic_exit_simulation_candidate_stop: float | None = None
    dynamic_exit_simulation_approved_stop: float | None = None
    dynamic_exit_simulation_rejection_reasons: tuple[str, ...] = ()
    dynamic_exit_simulation_created_at: str = "N/D"
    dynamic_exit_demo_sl_assisted_enabled: bool = False
    dynamic_exit_demo_sl_assisted_gate: str = "REJEITADO"
    dynamic_exit_demo_sl_assisted_message: str = "Modo assistido desligado."
    research_plan_reason: str = "Research Lab ainda nao produziu plano."
    research_plan_invalid_reason: str = ""
    research_plan_invalid_fields: tuple[str, ...] = ()
    research_plan_next_retry: str = ""
    research_plan_expected_trigger: str = ""
    research_plan_rr_current: float = 0.0
    research_plan_rr_minimum: float = 1.5
    research_plan_diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class DashboardMT5ForexSignalViewModel:
    """Painel Forex MT5 principal do dashboard."""

    connection_status: str = "DISCONNECTED"
    server: str = "N/D"
    account: str = "N/D"
    account_type: str = "N/D"
    timeframe: str = "M1"
    pairs: list[DashboardMT5ForexSignalRowViewModel] = field(default_factory=list)
    available_pairs: list[str] = field(default_factory=list)
    unavailable_pairs: list[str] = field(default_factory=list)
    message: str = "MT5 nao conectado."
    read_only_status: str = "SOMENTE ANALISE DE MERCADO"
    real_operation_authorized: bool = False
    connection_health: str = "OFFLINE"
    connection_health_icon: str = "🔴"
    last_update: str = ""
    last_mt5_read: str = ""
    last_candle_time: str = "N/D"
    refresh_id: int = 0
    seconds_since_update: float = 0.0
    health_message: str = "MT5 nao conectado."
    last_research_update: str = ""
    research_cache_status: str = "NO_RESEARCH_CACHE"
    fast_refresh_duration_ms: float = 0.0
    research_refresh_duration_ms: float = 0.0
    latency_breakdown: dict[str, float] = field(default_factory=dict)
    connection_diagnostic: DashboardMT5ConnectionDiagnosticViewModel = field(
        default_factory=DashboardMT5ConnectionDiagnosticViewModel
    )
    mt5_safe_mode: bool = True
    safe_mode_message: str = (
        "MT5 Safe Mode ativo: usando leitura simples e heuristica. "
        "Research Quantitativo temporariamente desativado."
    )
    safe_mode_source: str = "MT5_SAFE_MODE"
    safe_mode_status: str = "OFFLINE"
    safe_mode_received_candles: int = 0
    safe_mode_last_price: float | None = None
    safe_mode_error: str = ""


@dataclass(frozen=True)
class DashboardTimeframeCandidateViewModel:
    """Linha de candidato do Timeframe Optimizer."""

    symbol: str = "N/D"
    timeframe: str = "N/D"
    sample_size: int = 0
    win_rate: float = 0.0
    avg_return: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    calibrated_confidence: float = 0.0
    rank_score: float = 0.0
    rejection_reason: str = ""


@dataclass(frozen=True)
class DashboardTimeframeOptimizationViewModel:
    """Resultado read-only do Timeframe Optimizer por par."""

    symbol: str = "N/D"
    best_timeframe: str = "NONE"
    selected_reason: str = "Nenhuma otimizacao executada."
    candidates: list[DashboardTimeframeCandidateViewModel] = field(
        default_factory=list
    )
    rejected_candidates: list[DashboardTimeframeCandidateViewModel] = field(
        default_factory=list
    )
    is_research_only: bool = True


@dataclass(frozen=True)
class DashboardMT5HeuristicResearchRowViewModel:
    """Resultado read-only de avaliacao heuristica MT5 por par."""

    pair: str = "N/D"
    timeframe: str = "M1"
    recommended_heuristic: str = "WAIT_NO_EDGE"
    decision: str = "WAIT"
    score: float = 0.0
    confidence: float = 0.0
    ict_score: float = 0.0
    ict_grade: str = "E"
    ict_status: str = "REJEITADA"
    ict_usage: str = "Rejeitada."
    ict_demo_allowed: bool = False
    ict_rejection_reasons: tuple[str, ...] = ()
    status: str = "SEM_DADOS"
    reason: str = "Aguardando candles MT5."
    ideal_timeframe: str = "M1"
    final_configuration: dict[str, str] = field(default_factory=dict)
    buy_scenario: dict[str, str] = field(default_factory=dict)
    sell_scenario: dict[str, str] = field(default_factory=dict)
    buy_score: float = 0.0
    sell_score: float = 0.0
    score_breakdown: dict[str, str] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DashboardMT5ScenarioViewModel:
    """Cenario parametrizado avaliado pelo Research Lab MT5."""

    alpha_id: str = "ALPHA001"
    pair: str = "N/D"
    timeframe: str = "M1"
    temporal_session: str = "UNKNOWN"
    temporal_session_label: str = "Sem horario valido"
    temporal_window_brt: str = "N/D"
    temporal_hour_utc: int | None = None
    temporal_hour_brt: int | None = None
    temporal_weekday: str = "UNKNOWN"
    temporal_is_london_session: bool = False
    temporal_is_new_york_session: bool = False
    temporal_is_asia_session: bool = False
    temporal_is_overlap: bool = False
    temporal_is_rollover: bool = False
    temporal_is_friday_late: bool = False
    temporal_is_sunday_open: bool = False
    temporal_is_off_hours: bool = False
    temporal_status: str = "FORA_DA_JANELA"
    temporal_blocked: bool = False
    temporal_score_adjustment: float = 0.0
    temporal_reason: str = "Camada Tempo nao avaliada."
    temporal_preferred_sessions: tuple[str, ...] = ()
    temporal_financial_centers: tuple[str, ...] = ()
    temporal_quality_note: str = "Camada Tempo nao avaliada."
    model: str = "WAIT_NO_EDGE"
    parameters: dict[str, str] = field(default_factory=dict)
    score: float = 0.0
    lab_confidence: float = 0.0
    lab_confidence_sample_size: int = 0
    lab_confidence_profit_factor: float = 0.0
    lab_confidence_expectancy: float = 0.0
    lab_confidence_max_drawdown: float = 0.0
    lab_confidence_source: str = "SCENARIO_HISTORICAL_EVIDENCE"
    ict_score: float = 0.0
    ict_grade: str = "E"
    ict_status: str = "REJEITADA"
    ict_usage: str = "Rejeitada."
    ict_demo_allowed: bool = False
    ict_minimum_filters_passed: bool = False
    ict_rejection_reasons: tuple[str, ...] = ()
    ict_component_scores: dict[str, float] = field(default_factory=dict)
    status: str = "REJEITADO"
    decision: str = "WAIT"
    reason: str = "Cenario nao avaliado."


@dataclass(frozen=True)
class DashboardMT5SetupSuggestionViewModel:
    """Sugestao read-only de setup gerada a partir do snapshot do Lab."""

    alpha_id: str = "ALPHA001"
    pair: str = "N/D"
    timeframe: str = "M1"
    model: str = "WAIT_NO_EDGE"
    decision: str = "WAIT"
    parameters: dict[str, str] = field(default_factory=dict)
    exit_model: str = "NONE"
    stop_management: str = "FIXED_STOP"
    stop_management_reason: str = "Saida nao informada pelo snapshot."
    score: float = 0.0
    lab_confidence: float = 0.0
    target_confidence: float = 0.70
    status: str = "SEM_SUGESTAO"
    reason: str = "Nenhum cenario pesquisado."
    source: str = "MT5_RESEARCH_SNAPSHOT"


@dataclass(frozen=True)
class DashboardMT5AlphaResearchReportViewModel:
    """Relatorio tecnico read-only de validacao de Alpha pelo Lab."""

    alpha_id: str = "ALPHA001"
    tested_scenarios: int = 0
    evaluated_pairs: int = 0
    best_pair: str = "NONE"
    best_timeframe: str = "NONE"
    best_model: str = "NONE"
    best_decision: str = "WAIT"
    best_score: float = 0.0
    best_confidence: float = 0.0
    ict_score: float = 0.0
    ict_grade: str = "E"
    ict_status: str = "REJEITADA"
    ict_usage: str = "Rejeitada."
    ict_demo_allowed: bool = False
    target_confidence: float = 0.70
    status: str = "SEM_DADOS"
    alpha_name: str = "N/D"
    hypothesis: str = "N/D"
    used_indicators: tuple[str, ...] = ()
    failure_reasons: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    unavailable_evidence: list[str] = field(default_factory=list)
    source: str = "MT5_RESEARCH_SNAPSHOT"


@dataclass(frozen=True)
class DashboardMT5HeuristicResearchViewModel:
    """Resumo read-only de pesquisa heuristica MT5 para o Dashboard."""

    rows: list[DashboardMT5HeuristicResearchRowViewModel] = field(
        default_factory=list
    )
    scenario_ranking: list[DashboardMT5ScenarioViewModel] = field(
        default_factory=list
    )
    best_scenarios_by_market: list[DashboardMT5ScenarioViewModel] = field(
        default_factory=list
    )
    best_scenario: DashboardMT5ScenarioViewModel | None = None
    best_pair: str = "NONE"
    best_heuristic: str = "NONE"
    best_score: float = 0.0
    best_decision: str = "WAIT"
    best_confidence: float = 0.0
    priority_event_mode: str = "NORMAL_LAB_FLOW"
    priority_event_type: str = "NONE"
    priority_event_context: str = "NO_TRADE"
    priority_event_reason: str = "Nenhum evento prioritario ativo."
    winner_configuration: dict[str, str] = field(default_factory=dict)
    winner_score_breakdown: dict[str, str] = field(default_factory=dict)
    winner_diagnostics: list[str] = field(default_factory=list)
    winner_research_configuration: dict[str, str] = field(default_factory=dict)
    status: str = "SEM_DADOS"
    message: str = "Aguardando leitura MT5."
    is_research_only: bool = True
    last_update: str = "N/D"
    candles_loaded: int = 0
    timeframe: str = "M1"
    source: str = "MT5_RESEARCH_SNAPSHOT"


@dataclass(frozen=True)
class DashboardDemoRobotAuditViewModel:
    """Linha de auditoria do robo demo paper."""

    timestamp: str = "N/D"
    symbol: str = "N/D"
    side: str = "N/D"
    quantity: float = 0.0
    accepted: bool = False
    status: str = "N/D"
    message: str = "N/D"
    ticket: int | None = None
    alpha_id: str = "N/D"
    alpha_version: str = "N/D"
    session_policy_version: str = "N/D"
    execution_pipeline_version: str = "N/D"
    lab_configuration_version: str = "N/D"
    trade_plan_version: str = "N/D"
    execution_engine_version: str = "N/D"
    indicator_bundle_version: str = "N/D"
    microstructure_version: str = "N/D"
    validation_pipeline_version: str = "N/D"
    strategy_definition_version: str = "N/D"
    technical_score: float = 0.0
    historical_confirmation: float = 0.0
    entry_price: float | None = None
    stop: float | None = None
    target: float | None = None
    risk_reward: float = 0.0
    candle_time: str = "N/D"
    mt5_position: str = "N/D"
    forex_session: str = "N/D"
    forex_session_open: bool = False
    session_filter_enabled: bool = True
    session_filter_result: str = "N/D"
    session_reason: str = "N/D"
    timestamp_utc: str = "N/D"
    timestamp_brt: str = "N/D"
    weekday: str = "N/D"
    is_rollover: bool = False
    is_london_ny_overlap: bool = False
    is_sunday_open: bool = False
    is_friday_late: bool = False


@dataclass(frozen=True)
class DashboardDemoRobotRejectionStepViewModel:
    """Etapa diagnosticada na arvore de rejeicao do robo demo."""

    order: int = 0
    symbol: str = "N/D"
    timeframe: str = "N/D"
    stage: str = "N/D"
    status: str = "PENDENTE"
    reason: str = "Nao avaliado."
    detail: str = ""


@dataclass(frozen=True)
class DashboardDemoRobotViewModel:
    """Estado do robo demo MT5 exibido no dashboard."""

    status: str = "DISARMED"
    message: str = "Robo demo desarmado. Clique em Armar robo demo para aguardar entrada."
    selected_pair: str = "N/D"
    timeframe: str = "N/D"
    model: str = "N/D"
    decision: str = "WAIT"
    entry_price: float | None = None
    stop: float | None = None
    target: float | None = None
    result_status: str = "DISARMED"
    result_message: str = "Nenhuma ordem foi enviada ao MT5."
    provider: str = "MT5_DEMO_DISABLED"
    real_order_enabled: bool = False
    mt5_order_send_enabled: bool = False
    lab_configuration: dict[str, object] = field(default_factory=dict)
    market_indicators: dict[str, object] = field(default_factory=dict)
    active_indicators: tuple[str, ...] = ()
    rejection_tree: list[DashboardDemoRobotRejectionStepViewModel] = field(
        default_factory=list
    )
    audit_log: list[DashboardDemoRobotAuditViewModel] = field(default_factory=list)


@dataclass(frozen=True)
class DashboardMT5TradeAuditRowViewModel:
    """Linha de auditoria cruzada TraderIA x historico MT5."""

    timestamp: str = "N/D"
    symbol: str = "N/D"
    side: str = "N/D"
    quantity: float = 0.0
    entry_price: float = 0.0
    stop: float | None = None
    target: float | None = None
    projected_profit: float = 0.0
    projected_loss: float = 0.0
    local_status: str = "N/D"
    local_message: str = "N/D"
    local_ticket: int | None = None
    mt5_found: bool = False
    mt5_ticket: int | None = None
    mt5_source: str = "N/D"
    operation_status: str = "NAO_ENCONTRADA"
    mt5_symbol: str = "N/D"
    mt5_side: str = "N/D"
    mt5_volume: float = 0.0
    mt5_price: float = 0.0
    mt5_stop: float | None = None
    mt5_realized_profit: float = 0.0
    mt5_commission: float = 0.0
    mt5_swap: float = 0.0
    mt5_fee: float = 0.0
    mt5_open_cost: float = 0.0
    mt5_projected_open_cost: float = 0.0
    mt5_time: str = "N/D"
    audit_status: str = "PENDENTE"
    audit_message: str = "Aguardando confronto com historico MT5."
    session_policy_version: str = "N/D"
    execution_pipeline_version: str = "N/D"
    lab_configuration_version: str = "N/D"
    alpha_version: str = "N/D"
    trade_plan_version: str = "N/D"
    execution_engine_version: str = "N/D"
    indicator_bundle_version: str = "N/D"
    microstructure_version: str = "N/D"
    validation_pipeline_version: str = "N/D"
    strategy_definition_version: str = "N/D"
    forex_session: str = "N/D"
    forex_session_open: bool = False
    session_filter_enabled: bool = True
    session_filter_result: str = "N/D"
    session_reason: str = "N/D"
    session_timestamp_utc: str = "N/D"
    session_timestamp_brt: str = "N/D"
    session_weekday: str = "N/D"
    session_is_rollover: bool = False
    session_is_london_ny_overlap: bool = False
    session_is_sunday_open: bool = False
    session_is_friday_late: bool = False
    dynamic_exit_policy: str = "N/D"
    dynamic_exit_action: str = "N/D"
    dynamic_exit_reason: str = "N/D"
    dynamic_exit_confidence: float = 0.0
    dynamic_exit_market_state: str = "NO_POSITION"
    dynamic_exit_r_multiple: float = 0.0
    dynamic_exit_candidate_stop: float | None = None
    dynamic_exit_allowed_to_execute_demo: bool = False
    dynamic_exit_executed_action: str = "NONE"
    dynamic_exit_final_result: str = "N/D"
    final_exit_reason: str = "N/D"
    entry_setup: str = "N/D"
    exit_setup: str = "DYNAMIC_POSITION_MANAGER"
    position_manager_action: str = "N/D"
    position_manager_status: str = "N/D"
    position_manager_message: str = "N/D"
    stop_movel_acionado: bool = False


@dataclass(frozen=True)
class DashboardMT5TradeAuditViewModel:
    """Relatorio de auditoria de negociacoes originadas no TraderIA."""

    rows: list[DashboardMT5TradeAuditRowViewModel] = field(default_factory=list)
    total_local_records: int = 0
    total_accepted_local: int = 0
    total_audited: int = 0
    total_matched: int = 0
    total_mismatched: int = 0
    mt5_connection_status: str = "N/D"
    mt5_account_balance: float = 0.0
    equity_curve_default_start_date: str = "2026-07-01"
    last_update: str = "N/D"
    source: str = ".traderia/mt5_demo_execution.jsonl"
    mt5_source: str = (
        "MetaTrader5 positions_get/orders_get/history_orders_get/history_deals_get"
    )
    message: str = "Aguardando auditoria."


@dataclass(frozen=True)
class DashboardViewModel:
    """Contrato unico entre backend de aplicacao e UI."""

    contract_version: str = DASHBOARD_VIEW_MODEL_CONTRACT_VERSION
    system_status: DashboardSystemStatusViewModel = field(
        default_factory=DashboardSystemStatusViewModel
    )
    replay_status: DashboardReplayStatusViewModel = field(
        default_factory=DashboardReplayStatusViewModel
    )
    live_research_status: DashboardLiveResearchStatusViewModel = field(
        default_factory=DashboardLiveResearchStatusViewModel
    )
    live_session_summary: DashboardLiveSessionSummaryViewModel = field(
        default_factory=DashboardLiveSessionSummaryViewModel
    )
    live_signal_quality: list[DashboardLiveSignalQualityViewModel] = field(
        default_factory=list
    )
    live_history: list[DashboardLiveHistoryViewModel] = field(
        default_factory=list
    )
    research_status: DashboardResearchStatusViewModel = field(
        default_factory=DashboardResearchStatusViewModel
    )
    safety_status: DashboardSafetyStatusViewModel = field(
        default_factory=DashboardSafetyStatusViewModel
    )
    mt5_market_data: DashboardMT5MarketDataViewModel = field(
        default_factory=DashboardMT5MarketDataViewModel
    )
    mt5_forex_signals: DashboardMT5ForexSignalViewModel = field(
        default_factory=DashboardMT5ForexSignalViewModel
    )
    timeframe_optimizer: list[DashboardTimeframeOptimizationViewModel] = field(
        default_factory=list
    )
    mt5_heuristic_research: DashboardMT5HeuristicResearchViewModel = field(
        default_factory=DashboardMT5HeuristicResearchViewModel
    )
    demo_robot: DashboardDemoRobotViewModel = field(
        default_factory=DashboardDemoRobotViewModel
    )
    mt5_trade_audit: DashboardMT5TradeAuditViewModel = field(
        default_factory=DashboardMT5TradeAuditViewModel
    )
    compatibility_data: Any | None = field(
        default=None,
        metadata={"deprecated": "Migrar telas restantes para ViewModels tipados."},
    )

    def __getattr__(self, name: str) -> Any:
        """Fallback deprecated para telas ainda nao migradas."""
        if self.compatibility_data is not None:
            return getattr(self.compatibility_data, name)
        raise AttributeError(name)
