"""Servico de aplicacao para ingestao read-only de candles MT5."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from statistics import pstdev
from time import perf_counter
from typing import Any, Protocol

from core.configuration_manager import ConfigurationManager
from core.event_bus import EventBus
from core.events import NEW_CANDLE
from domain.candle import Candle
from market.candle_history import CandleHistory
from research.quantitative_score_engine import (
    QuantitativeScoreConfiguration,
    QuantitativeScoreContext,
    QuantitativeScoreEngine,
    QuantitativeScoreObservation,
    QuantitativeScoreResult,
)
from research.timeframe_optimizer import (
    TimeframeCandidate,
    TimeframeOptimizationResult,
    TimeframeOptimizer,
    TimeframeOptimizerConfiguration,
)


class ReadOnlyCandleProvider(Protocol):
    """Contrato minimo esperado de um provider read-only de candles."""

    def connect(self) -> bool:
        """Conecta a fonte externa em modo somente leitura."""

    def select_symbol(self, symbol: str) -> bool:
        """Seleciona um simbolo na fonte externa."""

    def get_candles(self, symbol: str, timeframe: Any, count: int) -> list[Candle]:
        """Retorna candles de dominio."""

    def list_symbols(self) -> list[str]:
        """Lista simbolos disponiveis para leitura."""


    def symbol_exists(self, symbol: str) -> bool:
        """Verifica disponibilidade do simbolo em modo read-only."""


@dataclass(frozen=True)
class MT5IngestionSummary:
    """Resumo simples da ingestao read-only de candles MT5."""

    symbol: str
    timeframe: str
    requested_candles: int
    received_candles: int
    inserted_candles: int
    connected: bool
    symbol_selected: bool
    last_candle: Candle | None = None
    message: str = ""


@dataclass(frozen=True)
class MT5CandleDashboardRow:
    """Candle MT5 normalizado para visualizacao read-only."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class MT5DashboardMarketData:
    """Snapshot MT5 pronto para consumo do DashboardService."""

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
    last_candle: MT5CandleDashboardRow | None = None
    candles: list[MT5CandleDashboardRow] = field(default_factory=list)
    message: str = "MT5 nao conectado."
    read_only_status: str = "SOMENTE MARKET DATA"
    real_operation_authorized: bool = False


@dataclass(frozen=True)
class MT5DiagnosticStep:
    """Etapa individual do diagnostico MT5 read-only."""

    name: str
    status: str
    message: str = ""
    last_error_code: int | None = None
    last_error_message: str = ""


@dataclass(frozen=True)
class MT5ConnectionDiagnostic:
    """Diagnostico detalhado da conexao MT5 para observabilidade."""

    connection_status: str = "OFFLINE"
    steps: tuple[MT5DiagnosticStep, ...] = ()
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
class MT5ForexSignalRow:
    """Linha de analise Forex read-only para o dashboard."""

    pair: str
    status: str
    last_price: float | None
    last_candle_time: str
    trend: str
    momentum: float | None
    volatility: float | None
    rsi: float | None
    short_average: float | None
    long_average: float | None
    decision: str
    confidence: float
    reason: str
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
    research_cache_status: str = "NO_RESEARCH_CACHE"
    latency_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class MT5ForexSignalDashboard:
    """Snapshot Forex MT5 com decisoes BUY/SELL/WAIT."""

    connection_status: str = "DISCONNECTED"
    server: str = "N/D"
    account: str = "N/D"
    account_type: str = "N/D"
    timeframe: str = "M1"
    pairs: list[MT5ForexSignalRow] = field(default_factory=list)
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
    connection_diagnostic: MT5ConnectionDiagnostic = field(
        default_factory=MT5ConnectionDiagnostic
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


SUPPORTED_MT5_SYMBOLS = (
    "EURUSD",
    "GBPUSD",
    "USDCHF",
    "USDJPY",
    "EURJPY",
    "AUDUSD",
    "NZDUSD",
    "USDCAD",
)
SUPPORTED_MT5_TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")
@dataclass
class MT5MarketDataService:
    """Ingere candles MT5 em CandleHistory sem expor execucao operacional."""

    provider: ReadOnlyCandleProvider = field(
        default_factory=lambda: _create_default_provider()
    )
    candle_history: CandleHistory = field(default_factory=CandleHistory)
    event_bus: EventBus = field(default_factory=EventBus)
    latest_dashboard_data: MT5DashboardMarketData = field(
        default_factory=lambda: MT5DashboardMarketData(
            supported_symbols=list(SUPPORTED_MT5_SYMBOLS),
            supported_timeframes=list(SUPPORTED_MT5_TIMEFRAMES),
        )
    )
    latest_forex_signal_dashboard: MT5ForexSignalDashboard = field(
        default_factory=MT5ForexSignalDashboard
    )
    latest_timeframe_optimization: list[TimeframeOptimizationResult] = field(
        default_factory=list
    )
    configuration_manager: type[ConfigurationManager] = ConfigurationManager
    quantitative_score_engine: QuantitativeScoreEngine | None = field(
        default=None
    )
    forex_refresh_id: int = 0
    last_forex_candle_times: dict[str, str] = field(default_factory=dict)
    latest_research_rows: dict[str, MT5ForexSignalRow] = field(default_factory=dict)
    latest_forex_candles: dict[tuple[str, str], list[Candle]] = field(
        default_factory=dict
    )
    latest_spread_history: dict[tuple[str, str], list[float]] = field(
        default_factory=dict
    )
    last_research_update: str = ""
    last_research_duration_ms: float = 0.0
    latest_connection_diagnostic: MT5ConnectionDiagnostic = field(
        default_factory=MT5ConnectionDiagnostic
    )

    def __post_init__(self) -> None:
        if hasattr(self.provider, "event_bus"):
            setattr(self.provider, "event_bus", self.event_bus)

    def ingest_candles(
        self,
        symbol: str,
        timeframe: Any,
        count: int = 10,
    ) -> MT5IngestionSummary:
        """Busca candles read-only e insere no CandleHistory."""
        normalized_symbol = symbol.strip()
        timeframe_label = self._timeframe_label(timeframe)
        if not normalized_symbol:
            return self._summary(
                symbol=normalized_symbol,
                timeframe=timeframe_label,
                requested=count,
                connected=False,
                selected=False,
                message="Simbolo vazio.",
            )
        if count <= 0:
            return self._summary(
                symbol=normalized_symbol,
                timeframe=timeframe_label,
                requested=count,
                connected=False,
                selected=False,
                message="Quantidade de candles deve ser positiva.",
            )

        connected = self._provider_connect()
        if not connected:
            return self._summary(
                symbol=normalized_symbol,
                timeframe=timeframe_label,
                requested=count,
                connected=False,
                selected=False,
                message="Fonte MT5 read-only nao conectada.",
            )

        selected = self.provider.select_symbol(normalized_symbol)
        if not selected:
            return self._summary(
                symbol=normalized_symbol,
                timeframe=timeframe_label,
                requested=count,
                connected=True,
                selected=False,
                message="Simbolo indisponivel na fonte MT5.",
            )

        candles = self.provider.get_candles(normalized_symbol, timeframe, count)
        provider_publishes_events = hasattr(self.provider, "event_bus")
        for candle in candles:
            self.candle_history.add_candle(candle)
            if not provider_publishes_events:
                self.event_bus.publish(NEW_CANDLE, candle)

        return MT5IngestionSummary(
            symbol=normalized_symbol,
            timeframe=timeframe_label,
            requested_candles=count,
            received_candles=len(candles),
            inserted_candles=len(candles),
            connected=True,
            symbol_selected=True,
            last_candle=self.candle_history.last(),
            message="Candles MT5 ingeridos em modo read-only.",
        )

    def get_dashboard_market_data(self) -> MT5DashboardMarketData:
        """Retorna o ultimo snapshot MT5 sem acionar conexao externa."""
        return self.latest_dashboard_data

    def get_forex_signal_dashboard(self) -> MT5ForexSignalDashboard:
        """Retorna a ultima analise Forex ou carrega M1 automaticamente."""
        if not self.latest_forex_signal_dashboard.pairs:
            return self.load_forex_signal_dashboard()
        return self.latest_forex_signal_dashboard

    def diagnose_mt5_connection(
        self,
        symbol: str = "EURUSD",
        timeframe: str = "M1",
    ) -> MT5ConnectionDiagnostic:
        """Executa diagnostico read-only sem alimentar replay ou pesquisa."""
        normalized_symbol = self._normalize_symbol(symbol)
        normalized_timeframe = self._normalize_timeframe(timeframe)
        timeframe_value = self._timeframe_value(normalized_timeframe)
        diagnostic_runner = getattr(self.provider, "diagnose_connection", None)
        if callable(diagnostic_runner):
            raw_diagnostic = diagnostic_runner(normalized_symbol, timeframe_value)
            diagnostic = self._to_connection_diagnostic(raw_diagnostic)
        else:
            diagnostic = self._generic_connection_diagnostic(
                normalized_symbol,
                timeframe_value,
            )
        self.latest_connection_diagnostic = diagnostic
        self.latest_forex_signal_dashboard = replace(
            self.latest_forex_signal_dashboard,
            connection_diagnostic=diagnostic,
        )
        return diagnostic

    def load_forex_signal_dashboard(
        self,
        timeframe: str = "M1",
        recalculate_research: bool | None = None,
    ) -> MT5ForexSignalDashboard:
        """Carrega os pares Forex oficiais com leitura MT5 heuristica."""
        total_started = perf_counter()
        provider_read_ms = 0.0
        feature_ms = 0.0
        score_ms = 0.0
        previous_candle_times = dict(self.last_forex_candle_times)
        self.forex_refresh_id += 1
        refresh_id = self.forex_refresh_id
        system_configuration = self.configuration_manager.get_configuration()
        safe_mode_enabled = True
        safe_mode_message = (
            "MT5 Forex heuristico ativo: usando somente candles, medias, RSI, "
            "momentum e volatilidade. Constantes calibradas podem ser "
            "consumidas pela camada DashboardService sem executar Research "
            "durante o refresh online."
        )
        configuration = self._mt5_safe_mode_configuration(system_configuration)
        should_recalculate_research = False
        normalized_timeframe = self._normalize_timeframe(timeframe)
        configured_candles = configuration.candles_loaded
        safe_count = max(configuration.slow_ma_period + 1, configured_candles)
        timeframe_value = self._timeframe_value(normalized_timeframe)
        refresh_time = self._current_update_time()

        connected = self._provider_connect()
        if not connected:
            rows = [
                self._unavailable_pair_row(
                    pair,
                    "MT5 DESCONECTADO",
                    "MT5 nao conectado; decisao WAIT por ausencia de dados.",
                    timeframe=normalized_timeframe,
                    configured_candles=configured_candles,
                    requested_candles=safe_count,
                    last_update=refresh_time,
                )
                for pair in SUPPORTED_MT5_SYMBOLS
            ]
            self.latest_forex_signal_dashboard = MT5ForexSignalDashboard(
                connection_status="DISCONNECTED",
                timeframe=normalized_timeframe,
                pairs=rows,
                unavailable_pairs=list(SUPPORTED_MT5_SYMBOLS),
                message=self._provider_error_message(
                    "Fonte MT5 read-only nao conectada."
                ),
                connection_health="OFFLINE",
                connection_health_icon="🔴",
                last_update=refresh_time,
                last_mt5_read=refresh_time,
                last_candle_time="N/D",
                refresh_id=refresh_id,
                seconds_since_update=0.0,
                health_message=self._provider_error_message(
                    "Terminal MT5 desconectado."
                ),
                last_research_update=self.last_research_update,
                research_cache_status="MT5_OFFLINE",
                fast_refresh_duration_ms=self._elapsed_ms(total_started),
                research_refresh_duration_ms=self.last_research_duration_ms,
                connection_diagnostic=self.latest_connection_diagnostic,
                mt5_safe_mode=safe_mode_enabled,
                safe_mode_message=safe_mode_message,
                safe_mode_source="MT5_SAFE_MODE",
                safe_mode_status="OFFLINE",
                safe_mode_received_candles=0,
                safe_mode_last_price=None,
                safe_mode_error=self._provider_error_message(
                    "Terminal MT5 desconectado."
                ),
            )
            return self.latest_forex_signal_dashboard

        rows: list[MT5ForexSignalRow] = []
        available_pairs: list[str] = []
        unavailable_pairs: list[str] = []
        read_errors: list[str] = []
        for pair in SUPPORTED_MT5_SYMBOLS:
            if not self._symbol_exists(pair):
                unavailable_pairs.append(pair)
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "INDISPONIVEL NO MT5",
                        "Par indisponivel no MT5; decisao WAIT.",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue

            selected = self.provider.select_symbol(pair)
            if not selected:
                unavailable_pairs.append(pair)
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "INDISPONIVEL NO MT5",
                        "MT5 nao habilitou o par para leitura; decisao WAIT.",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue

            try:
                read_started = perf_counter()
                candles = self.provider.get_candles(pair, timeframe_value, safe_count)
                provider_read_ms += self._elapsed_ms(read_started)
                self.latest_forex_candles[(pair, normalized_timeframe)] = list(candles)
            except TimeoutError as exc:
                unavailable_pairs.append(pair)
                read_errors.append(f"{pair}: timeout: {exc}")
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "ERRO MT5",
                        f"Timeout ao consultar provider MT5: {exc}",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue
            except Exception as exc:  # noqa: BLE001 - provider externo read-only
                unavailable_pairs.append(pair)
                read_errors.append(f"{pair}: {exc}")
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "ERRO MT5",
                        f"Erro ao consultar provider MT5: {exc}",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue
            rows.append(
                self._analyze_pair(
                    pair,
                    candles,
                    configuration,
                    microstructure=self._symbol_microstructure(pair),
                    timeframe=normalized_timeframe,
                    configured_candles=configured_candles,
                    requested_candles=safe_count,
                    last_update=refresh_time,
                    recalculate_research=should_recalculate_research,
                )
            )
            feature_ms += rows[-1].latency_breakdown.get("features_ms", 0.0)
            score_ms += rows[-1].latency_breakdown.get("score_ms", 0.0)
            available_pairs.append(pair)

        health = self._forex_connection_health(
            rows=rows,
            previous_candle_times=previous_candle_times,
            read_errors=read_errors,
            refresh_time=refresh_time,
            refresh_id=refresh_id,
        )
        self.last_forex_candle_times = {
            row.pair: row.last_candle_time
            for row in rows
            if row.last_candle_time != "N/D"
        }
        self.latest_forex_signal_dashboard = MT5ForexSignalDashboard(
            connection_status="CONNECTED",
            server=str(getattr(self.provider, "server_name", "N/D")),
            account=str(getattr(self.provider, "account", "N/D")),
            account_type=str(getattr(self.provider, "account_type", "N/D")),
            timeframe=normalized_timeframe,
            pairs=rows,
            available_pairs=available_pairs,
            unavailable_pairs=unavailable_pairs,
            message="Analise Forex MT5 atualizada em modo read-only.",
            connection_health=health["connection_health"],
            connection_health_icon=health["connection_health_icon"],
            last_update=refresh_time,
            last_mt5_read=refresh_time,
            last_candle_time=health["last_candle_time"],
            refresh_id=refresh_id,
            seconds_since_update=health["seconds_since_update"],
            health_message=health["health_message"],
            last_research_update=self.last_research_update,
            research_cache_status=self._research_cache_status(
                rows,
                should_recalculate_research,
            ),
            fast_refresh_duration_ms=self._elapsed_ms(total_started),
            research_refresh_duration_ms=(
                score_ms if should_recalculate_research else self.last_research_duration_ms
            ),
            latency_breakdown={
                "provider_read_ms": provider_read_ms,
                "features_ms": feature_ms,
                "score_ms": score_ms,
                "view_model_source_ms": 0.0,
            },
            connection_diagnostic=self.latest_connection_diagnostic,
            mt5_safe_mode=safe_mode_enabled,
            safe_mode_message=safe_mode_message,
            safe_mode_source="MT5_SAFE_MODE",
            safe_mode_status=(
                "ONLINE" if health["connection_health"].startswith("ONLINE")
                else "OFFLINE"
            ),
            safe_mode_received_candles=sum(row.received_candles for row in rows),
            safe_mode_last_price=self._latest_row_price(rows),
            safe_mode_error="; ".join(read_errors),
        )
        return self.latest_forex_signal_dashboard

    def load_forex_signal_dashboard_for_timeframes(
        self,
        timeframes_by_pair: dict[str, str],
        fallback_timeframe: str = "M1",
    ) -> MT5ForexSignalDashboard:
        """Carrega Forex online leve usando um timeframe autorizado por par."""
        if not timeframes_by_pair:
            return self.load_forex_signal_dashboard(timeframe=fallback_timeframe)

        total_started = perf_counter()
        provider_read_ms = 0.0
        feature_ms = 0.0
        score_ms = 0.0
        previous_candle_times = dict(self.last_forex_candle_times)
        self.forex_refresh_id += 1
        refresh_id = self.forex_refresh_id
        system_configuration = self.configuration_manager.get_configuration()
        configuration = self._mt5_safe_mode_configuration(system_configuration)
        safe_mode_enabled = True
        safe_mode_message = (
            "MT5 Forex heuristico ativo: leitura leve por par usando o "
            "timeframe recomendado pelo Research Lab quando disponivel."
        )
        fallback = self._normalize_timeframe(fallback_timeframe)
        configured_candles = configuration.candles_loaded
        safe_count = max(configuration.slow_ma_period + 1, configured_candles)
        refresh_time = self._current_update_time()
        should_recalculate_research = False

        normalized_map = {
            str(pair).upper(): self._normalize_timeframe(timeframe)
            for pair, timeframe in dict(timeframes_by_pair).items()
            if str(pair).strip()
        }

        connected = self._provider_connect()
        if not connected:
            rows = [
                self._unavailable_pair_row(
                    pair,
                    "MT5 DESCONECTADO",
                    "MT5 nao conectado; decisao WAIT por ausencia de dados.",
                    timeframe=normalized_map.get(pair, fallback),
                    configured_candles=configured_candles,
                    requested_candles=safe_count,
                    last_update=refresh_time,
                )
                for pair in SUPPORTED_MT5_SYMBOLS
            ]
            self.latest_forex_signal_dashboard = MT5ForexSignalDashboard(
                connection_status="DISCONNECTED",
                timeframe=fallback,
                pairs=rows,
                unavailable_pairs=list(SUPPORTED_MT5_SYMBOLS),
                message=self._provider_error_message(
                    "Fonte MT5 read-only nao conectada."
                ),
                connection_health="OFFLINE",
                connection_health_icon="ðŸ”´",
                last_update=refresh_time,
                last_mt5_read=refresh_time,
                last_candle_time="N/D",
                refresh_id=refresh_id,
                seconds_since_update=0.0,
                health_message=self._provider_error_message(
                    "Terminal MT5 desconectado."
                ),
                last_research_update=self.last_research_update,
                research_cache_status="MT5_OFFLINE",
                fast_refresh_duration_ms=self._elapsed_ms(total_started),
                research_refresh_duration_ms=self.last_research_duration_ms,
                connection_diagnostic=self.latest_connection_diagnostic,
                mt5_safe_mode=safe_mode_enabled,
                safe_mode_message=safe_mode_message,
                safe_mode_source="MT5_SAFE_MODE",
                safe_mode_status="OFFLINE",
                safe_mode_received_candles=0,
                safe_mode_last_price=None,
                safe_mode_error=self._provider_error_message(
                    "Terminal MT5 desconectado."
                ),
            )
            return self.latest_forex_signal_dashboard

        rows: list[MT5ForexSignalRow] = []
        available_pairs: list[str] = []
        unavailable_pairs: list[str] = []
        read_errors: list[str] = []
        batch_market_data: dict[str, dict[str, Any]] = {}
        batch_reader = getattr(self.provider, "get_forex_batch", None)
        if (
            callable(batch_reader)
            and os.getenv("TRADERIA_MT5_BATCH_ENABLED", "0").strip() == "1"
        ):
            try:
                batch_market_data = batch_reader(
                    {
                        pair: self._timeframe_value(normalized_map.get(pair, fallback))
                        for pair in SUPPORTED_MT5_SYMBOLS
                    },
                    safe_count,
                )
            except Exception as exc:  # noqa: BLE001 - provider externo read-only
                batch_market_data = {}
                read_errors.append(f"MT5 batch: {exc}")
        for pair in SUPPORTED_MT5_SYMBOLS:
            normalized_timeframe = normalized_map.get(pair, fallback)
            timeframe_value = self._timeframe_value(normalized_timeframe)
            batch_row = batch_market_data.get(pair)
            if batch_market_data:
                symbol_exists = bool(batch_row and batch_row.get("exists"))
            elif self._provider_uses_external_mt5_process():
                symbol_exists = True
            else:
                symbol_exists = self._symbol_exists(pair)
            if not symbol_exists:
                unavailable_pairs.append(pair)
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "INDISPONIVEL NO MT5",
                        "Par indisponivel no MT5; decisao WAIT.",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue

            if batch_market_data:
                selected = bool(batch_row and batch_row.get("selected"))
            elif self._provider_uses_external_mt5_process():
                selected = True
            else:
                selected = self.provider.select_symbol(pair)
            if not selected:
                unavailable_pairs.append(pair)
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "INDISPONIVEL NO MT5",
                        "MT5 nao habilitou o par para leitura; decisao WAIT.",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue

            try:
                read_started = perf_counter()
                if batch_market_data:
                    candles = list(batch_row.get("candles", [])) if batch_row else []
                else:
                    candles = self.provider.get_candles(pair, timeframe_value, safe_count)
                provider_read_ms += self._elapsed_ms(read_started)
                self.latest_forex_candles[(pair, normalized_timeframe)] = list(candles)
            except TimeoutError as exc:
                unavailable_pairs.append(pair)
                read_errors.append(f"{pair}: timeout: {exc}")
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "ERRO MT5",
                        f"Timeout ao consultar provider MT5: {exc}",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue
            except Exception as exc:  # noqa: BLE001 - provider externo read-only
                unavailable_pairs.append(pair)
                read_errors.append(f"{pair}: {exc}")
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "ERRO MT5",
                        f"Erro ao consultar provider MT5: {exc}",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue

            rows.append(
                self._analyze_pair(
                    pair,
                    candles,
                    configuration,
                    microstructure=(
                        dict(batch_row.get("microstructure", {}))
                        if batch_market_data and batch_row
                        else (
                            {}
                            if self._provider_uses_external_mt5_process()
                            else self._symbol_microstructure(pair)
                        )
                    ),
                    timeframe=normalized_timeframe,
                    configured_candles=configured_candles,
                    requested_candles=safe_count,
                    last_update=refresh_time,
                    recalculate_research=should_recalculate_research,
                )
            )
            feature_ms += rows[-1].latency_breakdown.get("features_ms", 0.0)
            score_ms += rows[-1].latency_breakdown.get("score_ms", 0.0)
            available_pairs.append(pair)

        health = self._forex_connection_health(
            rows=rows,
            previous_candle_times=previous_candle_times,
            read_errors=read_errors,
            refresh_time=refresh_time,
            refresh_id=refresh_id,
        )
        self.last_forex_candle_times = {
            row.pair: row.last_candle_time
            for row in rows
            if row.last_candle_time != "N/D"
        }
        self.latest_forex_signal_dashboard = MT5ForexSignalDashboard(
            connection_status="CONNECTED",
            server=str(getattr(self.provider, "server_name", "N/D")),
            account=str(getattr(self.provider, "account", "N/D")),
            account_type=str(getattr(self.provider, "account_type", "N/D")),
            timeframe=fallback,
            pairs=rows,
            available_pairs=available_pairs,
            unavailable_pairs=unavailable_pairs,
            message="Analise Forex MT5 atualizada em modo read-only por timeframe do Lab.",
            connection_health=health["connection_health"],
            connection_health_icon=health["connection_health_icon"],
            last_update=refresh_time,
            last_mt5_read=refresh_time,
            last_candle_time=health["last_candle_time"],
            refresh_id=refresh_id,
            seconds_since_update=health["seconds_since_update"],
            health_message=health["health_message"],
            last_research_update=self.last_research_update,
            research_cache_status=self._research_cache_status(
                rows,
                should_recalculate_research,
            ),
            fast_refresh_duration_ms=self._elapsed_ms(total_started),
            research_refresh_duration_ms=self.last_research_duration_ms,
            latency_breakdown={
                "provider_read_ms": provider_read_ms,
                "features_ms": feature_ms,
                "score_ms": score_ms,
                "view_model_source_ms": 0.0,
            },
            connection_diagnostic=self.latest_connection_diagnostic,
            mt5_safe_mode=safe_mode_enabled,
            safe_mode_message=safe_mode_message,
            safe_mode_source="MT5_SAFE_MODE",
            safe_mode_status=(
                "ONLINE" if health["connection_health"].startswith("ONLINE")
                else "OFFLINE"
            ),
            safe_mode_received_candles=sum(row.received_candles for row in rows),
            safe_mode_last_price=self._latest_row_price(rows),
            safe_mode_error="; ".join(read_errors),
        )
        return self.latest_forex_signal_dashboard

    def load_forex_research_snapshot(
        self,
        timeframe: str = "M1",
        count: int | None = None,
    ) -> MT5ForexSignalDashboard:
        """Carrega snapshot MT5 para calibracao sem alterar o painel online."""
        total_started = perf_counter()
        provider_read_ms = 0.0
        feature_ms = 0.0
        system_configuration = self.configuration_manager.get_configuration()
        online_configuration = self._mt5_safe_mode_configuration(system_configuration)
        research_configuration = self._quantitative_score_configuration()
        normalized_timeframe = self._normalize_timeframe(timeframe)
        configured_candles = (
            research_configuration.candles_loaded if count is None else int(count)
        )
        safe_count = max(online_configuration.slow_ma_period + 1, configured_candles)
        timeframe_value = self._timeframe_value(normalized_timeframe)
        refresh_time = self._current_update_time()
        safe_mode_message = (
            "Snapshot MT5 de pesquisa carregado sob demanda. Este fluxo calibra "
            "constantes e nao participa do refresh online do MT5 Forex."
        )

        connected = self._provider_connect()
        if not connected:
            rows = [
                self._unavailable_pair_row(
                    pair,
                    "MT5 DESCONECTADO",
                    "MT5 nao conectado; calibracao indisponivel.",
                    timeframe=normalized_timeframe,
                    configured_candles=configured_candles,
                    requested_candles=safe_count,
                    last_update=refresh_time,
                )
                for pair in SUPPORTED_MT5_SYMBOLS
            ]
            return MT5ForexSignalDashboard(
                connection_status="DISCONNECTED",
                timeframe=normalized_timeframe,
                pairs=rows,
                unavailable_pairs=list(SUPPORTED_MT5_SYMBOLS),
                message=self._provider_error_message(
                    "Fonte MT5 read-only nao conectada para calibracao."
                ),
                connection_health="OFFLINE",
                connection_health_icon="OFFLINE",
                last_update=refresh_time,
                last_mt5_read=refresh_time,
                last_candle_time="N/D",
                refresh_id=self.forex_refresh_id,
                seconds_since_update=0.0,
                health_message=self._provider_error_message(
                    "Terminal MT5 desconectado."
                ),
                last_research_update=refresh_time,
                research_cache_status="RESEARCH_SNAPSHOT_OFFLINE",
                fast_refresh_duration_ms=0.0,
                research_refresh_duration_ms=self._elapsed_ms(total_started),
                connection_diagnostic=self.latest_connection_diagnostic,
                mt5_safe_mode=True,
                safe_mode_message=safe_mode_message,
                safe_mode_source="MT5_RESEARCH_CALIBRATION",
                safe_mode_status="OFFLINE",
                safe_mode_received_candles=0,
                safe_mode_last_price=None,
                safe_mode_error=self._provider_error_message(
                    "Terminal MT5 desconectado."
                ),
            )

        rows: list[MT5ForexSignalRow] = []
        available_pairs: list[str] = []
        unavailable_pairs: list[str] = []
        read_errors: list[str] = []
        for pair in SUPPORTED_MT5_SYMBOLS:
            if not self._symbol_exists(pair):
                unavailable_pairs.append(pair)
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "INDISPONIVEL NO MT5",
                        "Par indisponivel no MT5; calibracao rejeitada.",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue

            selected = self.provider.select_symbol(pair)
            if not selected:
                unavailable_pairs.append(pair)
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "INDISPONIVEL NO MT5",
                        "MT5 nao habilitou o par para calibracao.",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue

            try:
                read_started = perf_counter()
                candles = self.provider.get_candles(pair, timeframe_value, safe_count)
                provider_read_ms += self._elapsed_ms(read_started)
            except TimeoutError as exc:
                unavailable_pairs.append(pair)
                read_errors.append(f"{pair}: timeout: {exc}")
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "ERRO MT5",
                        f"Timeout ao consultar provider MT5: {exc}",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue
            except Exception as exc:  # noqa: BLE001 - provider externo read-only
                unavailable_pairs.append(pair)
                read_errors.append(f"{pair}: {exc}")
                rows.append(
                    self._unavailable_pair_row(
                        pair,
                        "ERRO MT5",
                        f"Erro ao consultar provider MT5: {exc}",
                        timeframe=normalized_timeframe,
                        configured_candles=configured_candles,
                        requested_candles=safe_count,
                        last_update=refresh_time,
                    )
                )
                continue

            rows.append(
                self._analyze_pair(
                    pair,
                    candles,
                    research_configuration,
                    microstructure=self._symbol_microstructure(pair),
                    timeframe=normalized_timeframe,
                    configured_candles=configured_candles,
                    requested_candles=safe_count,
                    last_update=refresh_time,
                    recalculate_research=True,
                )
            )
            feature_ms += rows[-1].latency_breakdown.get("features_ms", 0.0)
            available_pairs.append(pair)

        health = self._forex_connection_health(
            rows=rows,
            previous_candle_times={},
            read_errors=read_errors,
            refresh_time=refresh_time,
            refresh_id=self.forex_refresh_id,
        )
        return MT5ForexSignalDashboard(
            connection_status="CONNECTED",
            server=str(getattr(self.provider, "server_name", "N/D")),
            account=str(getattr(self.provider, "account", "N/D")),
            account_type=str(getattr(self.provider, "account_type", "N/D")),
            timeframe=normalized_timeframe,
            pairs=rows,
            available_pairs=available_pairs,
            unavailable_pairs=unavailable_pairs,
            message="Snapshot MT5 de pesquisa carregado em modo read-only.",
            connection_health=health["connection_health"],
            connection_health_icon=health["connection_health_icon"],
            last_update=refresh_time,
            last_mt5_read=refresh_time,
            last_candle_time=health["last_candle_time"],
            refresh_id=self.forex_refresh_id,
            seconds_since_update=health["seconds_since_update"],
            health_message=health["health_message"],
            last_research_update=refresh_time,
            research_cache_status="RESEARCH_SNAPSHOT",
            fast_refresh_duration_ms=0.0,
            research_refresh_duration_ms=self._elapsed_ms(total_started),
            latency_breakdown={
                "provider_read_ms": provider_read_ms,
                "features_ms": feature_ms,
                "score_ms": 0.0,
                "view_model_source_ms": 0.0,
            },
            connection_diagnostic=self.latest_connection_diagnostic,
            mt5_safe_mode=True,
            safe_mode_message=safe_mode_message,
            safe_mode_source="MT5_RESEARCH_CALIBRATION",
            safe_mode_status=(
                "ONLINE" if health["connection_health"].startswith("ONLINE")
                else "OFFLINE"
            ),
            safe_mode_received_candles=sum(row.received_candles for row in rows),
            safe_mode_last_price=self._latest_row_price(rows),
            safe_mode_error="; ".join(read_errors),
        )

    def get_timeframe_optimization_results(
        self,
    ) -> list[TimeframeOptimizationResult]:
        """Retorna ultimo ranking de timeframes sem acionar conexao externa."""
        return list(self.latest_timeframe_optimization)

    def load_timeframe_optimization_results(
        self,
        count: int | None = None,
    ) -> list[TimeframeOptimizationResult]:
        """Executa pesquisa read-only de timeframes por par Forex."""
        self.latest_timeframe_optimization = []
        return []
        score_configuration = self._quantitative_score_configuration()
        optimizer_configuration = self._timeframe_optimizer_configuration()
        system_configuration = self.configuration_manager.get_configuration()
        timeframes = tuple(system_configuration.timeframe_optimizer_timeframes)
        requested_count = score_configuration.candles_loaded if count is None else int(count)
        safe_count = max(score_configuration.slow_ma_period + 1, requested_count)
        optimizer = TimeframeOptimizer()

        connected = self._provider_connect()
        if not connected:
            self.latest_timeframe_optimization = [
                optimizer.optimize(
                    symbol=pair,
                    candidates=[
                        TimeframeCandidate(
                            symbol=pair,
                            timeframe=timeframe,
                            sample_size=0,
                            win_rate=0.0,
                            avg_return=0.0,
                            profit_factor=0.0,
                            max_drawdown=0.0,
                            calibrated_confidence=0.0,
                            rejection_reason="MT5_DISCONNECTED",
                        )
                        for timeframe in timeframes
                    ],
                    configuration=optimizer_configuration,
                )
                for pair in SUPPORTED_MT5_SYMBOLS
            ]
            return self.get_timeframe_optimization_results()

        results: list[TimeframeOptimizationResult] = []
        for pair in SUPPORTED_MT5_SYMBOLS:
            candidates: list[TimeframeCandidate] = []
            for timeframe in timeframes:
                normalized_timeframe = self._normalize_timeframe(timeframe)
                if not self._symbol_exists(pair) or not self.provider.select_symbol(pair):
                    candidates.append(
                        TimeframeCandidate(
                            symbol=pair,
                            timeframe=normalized_timeframe,
                            sample_size=0,
                            win_rate=0.0,
                            avg_return=0.0,
                            profit_factor=0.0,
                            max_drawdown=0.0,
                            calibrated_confidence=0.0,
                            rejection_reason="SYMBOL_UNAVAILABLE",
                        )
                    )
                    continue

                candles = self.provider.get_candles(
                    pair,
                    self._timeframe_value(normalized_timeframe),
                    safe_count,
                )
                row = self._analyze_pair(
                    pair,
                    candles,
                    score_configuration,
                    microstructure=self._symbol_microstructure(pair),
                )
                candidates.append(
                    TimeframeCandidate(
                        symbol=pair,
                        timeframe=normalized_timeframe,
                        sample_size=row.sample_size,
                        win_rate=row.win_rate,
                        avg_return=row.avg_return,
                        profit_factor=row.profit_factor,
                        max_drawdown=row.max_drawdown,
                        calibrated_confidence=row.confidence,
                    )
                )

            results.append(
                optimizer.optimize(
                    symbol=pair,
                    candidates=candidates,
                    configuration=optimizer_configuration,
                )
            )

        self.latest_timeframe_optimization = results
        return self.get_timeframe_optimization_results()

    def load_dashboard_market_data(
        self,
        symbol: str = "EURUSD",
        timeframe: str = "M1",
        count: int | None = None,
    ) -> MT5DashboardMarketData:
        """Carrega candles MT5 para exibicao read-only no dashboard."""
        configuration = self._quantitative_score_configuration()
        normalized_symbol = self._normalize_symbol(symbol)
        normalized_timeframe = self._normalize_timeframe(timeframe)
        requested_count = configuration.candles_loaded if count is None else int(count)
        safe_count = max(1, requested_count)
        timeframe_value = self._timeframe_value(normalized_timeframe)
        summary = self.ingest_candles(
            normalized_symbol,
            timeframe_value,
            safe_count,
        )
        candles = self._dashboard_candle_rows(
            self.candle_history.last_n(summary.inserted_candles)
        )
        available_symbols = self._available_symbols()
        connection_status = (
            "CONNECTED" if summary.connected else "DISCONNECTED"
        )
        message = summary.message
        if not summary.connected:
            message = self._provider_error_message(message)
        elif not summary.symbol_selected:
            message = "Simbolo nao disponivel para leitura no MT5."
        elif not candles:
            message = "MT5 conectado, mas nenhum candle foi retornado."

        self.latest_dashboard_data = MT5DashboardMarketData(
            connection_status=connection_status,
            server=str(getattr(self.provider, "server_name", "N/D")),
            account=str(getattr(self.provider, "account", "N/D")),
            account_type=str(getattr(self.provider, "account_type", "N/D")),
            available_symbols=available_symbols,
            supported_symbols=list(SUPPORTED_MT5_SYMBOLS),
            selected_symbol=normalized_symbol,
            supported_timeframes=list(SUPPORTED_MT5_TIMEFRAMES),
            selected_timeframe=normalized_timeframe,
            candles_loaded=len(candles),
            last_candle=candles[-1] if candles else None,
            candles=candles,
            message=message,
        )
        return self.latest_dashboard_data

    def _summary(
        self,
        symbol: str,
        timeframe: str,
        requested: int,
        connected: bool,
        selected: bool,
        message: str,
    ) -> MT5IngestionSummary:
        return MT5IngestionSummary(
            symbol=symbol,
            timeframe=timeframe,
            requested_candles=requested,
            received_candles=0,
            inserted_candles=0,
            connected=connected,
            symbol_selected=selected,
            last_candle=self.candle_history.last(),
            message=message,
        )

    def _timeframe_label(self, timeframe: Any) -> str:
        if isinstance(timeframe, str):
            return timeframe
        return str(timeframe)

    def _provider_connect(self) -> bool:
        connector = getattr(self.provider, "connect")
        return bool(connector())

    def _generic_connection_diagnostic(
        self,
        symbol: str,
        timeframe: Any,
    ) -> MT5ConnectionDiagnostic:
        executed_at = self._current_update_time()
        steps: list[MT5DiagnosticStep] = []
        terminal_ok = self.provider is not None
        steps.append(
            MT5DiagnosticStep(
                name="Terminal encontrado",
                status="OK" if terminal_ok else "FALHOU",
                message="Provider MT5 instanciado." if terminal_ok else "Provider MT5 ausente.",
                last_error_message=self._provider_error_message(""),
            )
        )
        initialized = self._provider_connect() if terminal_ok else False
        steps.append(
            MT5DiagnosticStep(
                name="initialize()",
                status="OK" if initialized else "FALHOU",
                message="Conexao inicializada." if initialized else self._provider_error_message("Falha ao inicializar MT5."),
                last_error_message=self._provider_error_message(""),
            )
        )
        login_ok = initialized
        steps.append(
            MT5DiagnosticStep(
                name="login()",
                status="OK" if login_ok else "FALHOU",
                message="Sessao considerada ativa pelo provider." if login_ok else "Sem sessao ativa.",
                last_error_message=self._provider_error_message(""),
            )
        )
        account = str(getattr(self.provider, "account", "N/D"))
        server = str(getattr(self.provider, "server_name", "N/D"))
        account_ok = initialized and account != "N/D"
        terminal_info_ok = initialized
        steps.append(
            MT5DiagnosticStep(
                name="account_info()",
                status="OK" if account_ok else "FALHOU",
                message="Conta obtida." if account_ok else "account_info indisponivel no provider.",
                last_error_message=self._provider_error_message(""),
            )
        )
        steps.append(
            MT5DiagnosticStep(
                name="terminal_info()",
                status="OK" if terminal_info_ok else "FALHOU",
                message="Terminal acessivel pelo provider." if terminal_info_ok else "terminal_info indisponivel.",
                last_error_message=self._provider_error_message(""),
            )
        )
        selected = bool(self.provider.select_symbol(symbol)) if initialized else False
        steps.append(
            MT5DiagnosticStep(
                name="symbol_select()",
                status="OK" if selected else "FALHOU",
                message=f"Simbolo {symbol} selecionado." if selected else self._provider_error_message("Falha ao selecionar simbolo."),
                last_error_message=self._provider_error_message(""),
            )
        )
        copied = False
        if selected:
            try:
                copied = bool(self.provider.get_candles(symbol, timeframe, 1))
            except Exception as exc:  # noqa: BLE001 - provider externo read-only
                copied = False
                setattr(self.provider, "last_error", f"Falha em copy_rates_from_pos(): {exc}")
        steps.append(
            MT5DiagnosticStep(
                name="copy_rates_from_pos()",
                status="OK" if copied else "FALHOU",
                message="Sonda de 1 candle retornada." if copied else self._provider_error_message("Falha ao ler candle de diagnostico."),
                last_error_message=self._provider_error_message(""),
            )
        )
        failed = next((step.name for step in steps if step.status != "OK"), "")
        return MT5ConnectionDiagnostic(
            connection_status="ONLINE" if not failed else "OFFLINE",
            steps=tuple(steps),
            last_error_message=self._provider_error_message(""),
            terminal_path=str(getattr(self.provider, "terminal_path", "N/D") or "N/D"),
            build=str(getattr(self.provider, "build", "N/D")),
            server=server,
            account=account,
            connected=bool(getattr(self.provider, "connected", initialized)),
            trade_allowed=bool(getattr(self.provider, "trade_allowed", False)),
            community_connection=bool(
                getattr(self.provider, "community_connection", False)
            ),
            failed_call=failed,
            diagnostic_message=(
                "Todas as etapas MT5 read-only responderam com sucesso."
                if not failed
                else f"Falha em {failed}."
            ),
            executed_at=executed_at,
        )

    def _to_connection_diagnostic(
        self,
        raw_diagnostic: Any,
    ) -> MT5ConnectionDiagnostic:
        raw_steps = list(self._raw_value(raw_diagnostic, "steps", []) or [])
        steps = tuple(
            MT5DiagnosticStep(
                name=str(self._raw_value(step, "name", "N/D")),
                status=str(self._raw_value(step, "status", "FALHOU")),
                message=str(self._raw_value(step, "message", "")),
                last_error_code=self._optional_int(
                    self._raw_value(step, "last_error_code", None)
                ),
                last_error_message=str(
                    self._raw_value(step, "last_error_message", "")
                ),
            )
            for step in raw_steps
        )
        return MT5ConnectionDiagnostic(
            connection_status=str(
                self._raw_value(raw_diagnostic, "connection_status", "OFFLINE")
            ),
            steps=steps,
            last_error_code=self._optional_int(
                self._raw_value(raw_diagnostic, "last_error_code", None)
            ),
            last_error_message=str(
                self._raw_value(raw_diagnostic, "last_error_message", "")
            ),
            terminal_path=str(self._raw_value(raw_diagnostic, "terminal_path", "N/D")),
            build=str(self._raw_value(raw_diagnostic, "build", "N/D")),
            server=str(self._raw_value(raw_diagnostic, "server", "N/D")),
            account=str(self._raw_value(raw_diagnostic, "account", "N/D")),
            connected=bool(self._raw_value(raw_diagnostic, "connected", False)),
            trade_allowed=bool(self._raw_value(raw_diagnostic, "trade_allowed", False)),
            community_connection=bool(
                self._raw_value(raw_diagnostic, "community_connection", False)
            ),
            failed_call=str(self._raw_value(raw_diagnostic, "failed_call", "")),
            diagnostic_message=str(
                self._raw_value(
                    raw_diagnostic,
                    "diagnostic_message",
                    "Diagnostico MT5 executado.",
                )
            ),
            executed_at=self._current_update_time(),
        )

    def _raw_value(self, item: Any, name: str, default: Any) -> Any:
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)

    def _optional_int(self, value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _normalize_symbol(self, symbol: str) -> str:
        normalized = str(symbol or "").strip().upper()
        if normalized in SUPPORTED_MT5_SYMBOLS:
            return normalized
        return SUPPORTED_MT5_SYMBOLS[0]

    def _normalize_timeframe(self, timeframe: str) -> str:
        normalized = str(timeframe or "").strip().upper()
        if normalized in SUPPORTED_MT5_TIMEFRAMES:
            return normalized
        return "M1"

    def _timeframe_value(self, timeframe: str) -> Any:
        external_mt5 = getattr(self.provider, "_use_external_mt5_process", None)
        if callable(external_mt5) and external_mt5():
            mt5_timeframes = {
                "M1": 1,
                "M5": 5,
                "M15": 15,
                "M30": 30,
                "H1": 16385,
                "H4": 16388,
                "D1": 16408,
            }
            return mt5_timeframes.get(timeframe, timeframe)

        mt5_module = getattr(self.provider, "_mt5", None)
        if callable(mt5_module):
            try:
                mt5 = mt5_module()
                value = getattr(mt5, f"TIMEFRAME_{timeframe}", None)
                if value is not None:
                    return value
            except (ImportError, ModuleNotFoundError, OSError, RuntimeError):
                return timeframe
        return timeframe

    def _dashboard_candle_rows(
        self,
        candles: list[Candle],
    ) -> list[MT5CandleDashboardRow]:
        return [
            MT5CandleDashboardRow(
                timestamp=candle.data,
                open=float(candle.abertura),
                high=float(candle.maxima),
                low=float(candle.minima),
                close=float(candle.fechamento),
                volume=int(candle.volume),
            )
            for candle in candles
        ]

    def _available_symbols(self) -> list[str]:
        symbols = getattr(self.provider, "list_symbols", None)
        if callable(symbols):
            available = list(symbols())
            if available:
                supported = [
                    symbol
                    for symbol in SUPPORTED_MT5_SYMBOLS
                    if symbol in set(available)
                ]
                return supported or available[:100]
        return list(SUPPORTED_MT5_SYMBOLS)

    def _provider_error_message(self, fallback: str) -> str:
        error = str(getattr(self.provider, "last_error", "") or "").strip()
        if error:
            return error
        return fallback

    def _symbol_exists(self, symbol: str) -> bool:
        checker = getattr(self.provider, "symbol_exists", None)
        if callable(checker):
            return bool(checker(symbol))
        return True

    def _provider_uses_external_mt5_process(self) -> bool:
        external_mt5 = getattr(self.provider, "_use_external_mt5_process", None)
        return bool(callable(external_mt5) and external_mt5())

    def _current_update_time(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _forex_connection_health(
        self,
        rows: list[MT5ForexSignalRow],
        previous_candle_times: dict[str, str],
        read_errors: list[str],
        refresh_time: str,
        refresh_id: int,
    ) -> dict[str, Any]:
        successful_rows = [
            row
            for row in rows
            if row.received_candles > 0
        ]
        last_candle_time = self._latest_row_candle_time(successful_rows)
        if read_errors:
            return {
                "connection_health": "OFFLINE",
                "connection_health_icon": "🔴",
                "last_candle_time": last_candle_time,
                "seconds_since_update": self._seconds_since(refresh_time),
                "health_message": "; ".join(read_errors),
            }
        if not successful_rows:
            return {
                "connection_health": "OFFLINE",
                "connection_health_icon": "🔴",
                "last_candle_time": last_candle_time,
                "seconds_since_update": self._seconds_since(refresh_time),
                "health_message": "MT5 conectado, mas nenhum candle foi recebido.",
            }
        if refresh_id > 1 and not self._has_new_candle(
            successful_rows,
            previous_candle_times,
        ):
            return {
                "connection_health": "ONLINE — Aguardando nova vela",
                "connection_health_icon": "🟡",
                "last_candle_time": last_candle_time,
                "seconds_since_update": self._seconds_since(refresh_time),
                "health_message": "Aguardando fechamento da proxima vela.",
            }
        return {
            "connection_health": "ONLINE",
            "connection_health_icon": "🟢",
            "last_candle_time": last_candle_time,
            "seconds_since_update": self._seconds_since(refresh_time),
            "health_message": "Dados atualizados.",
        }

    def _latest_row_candle_time(self, rows: list[MT5ForexSignalRow]) -> str:
        valid_times = [
            row.last_candle_time
            for row in rows
            if row.last_candle_time != "N/D"
        ]
        if not valid_times:
            return "N/D"
        return max(valid_times)

    def _latest_row_price(self, rows: list[MT5ForexSignalRow]) -> float | None:
        valid_rows = [
            row
            for row in rows
            if row.last_price is not None and row.last_candle_time != "N/D"
        ]
        if not valid_rows:
            return None
        latest = max(valid_rows, key=lambda row: row.last_candle_time)
        return latest.last_price

    def _has_new_candle(
        self,
        rows: list[MT5ForexSignalRow],
        previous_candle_times: dict[str, str],
    ) -> bool:
        if not previous_candle_times:
            return True
        for row in rows:
            previous = previous_candle_times.get(row.pair)
            if previous is None or previous != row.last_candle_time:
                return True
        return False

    def _seconds_since(self, timestamp: str) -> float:
        try:
            parsed = datetime.fromisoformat(timestamp)
        except ValueError:
            return 0.0
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())

    def _elapsed_ms(self, started: float) -> float:
        return max(0.0, (perf_counter() - started) * 1000.0)

    def _research_cache_status(
        self,
        rows: list[MT5ForexSignalRow],
        recalculated: bool,
    ) -> str:
        if recalculated:
            return "RECALCULATED"
        statuses = {
            row.research_cache_status
            for row in rows
            if row.status == "OK"
        }
        if "OK_SAME_CANDLE" in statuses and len(statuses) == 1:
            return "OK_SAME_CANDLE"
        if "USING_LAST_RESEARCH" in statuses:
            return "USING_LAST_RESEARCH"
        if "NO_RESEARCH_CACHE" in statuses:
            return "NO_RESEARCH_CACHE"
        return "NO_MARKET_DATA"

    def _score_from_cached_row(
        self,
        row: MT5ForexSignalRow,
    ) -> QuantitativeScoreResult:
        return QuantitativeScoreResult(
            decision=row.decision,
            calibrated_confidence=row.confidence,
            sample_size=row.sample_size,
            win_rate=row.win_rate,
            avg_return=row.avg_return,
            profit_factor=row.profit_factor,
            max_drawdown=row.max_drawdown,
            reason="Research reutilizado do ultimo calculo.",
            matched_context_count=row.matched_context_count,
            rejected_reason=row.rejected_reason,
            volatility_bucket=row.volatility_bucket,
            rsi_bucket=row.rsi_bucket,
            momentum_sign=row.momentum_sign,
            ma_distance_bucket=row.ma_distance_bucket,
            confidence_penalties=row.confidence_penalties,
            confidence_drivers=row.confidence_drivers,
        )

    def _empty_score(self, decision: str) -> QuantitativeScoreResult:
        return QuantitativeScoreResult(
            decision=decision,
            calibrated_confidence=0.0,
            sample_size=0,
            win_rate=0.0,
            avg_return=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
            reason="Research ainda nao recalculado; exibindo leitura leve.",
            matched_context_count=0,
            rejected_reason="NO_RESEARCH_CACHE",
        )

    def _heuristic_score(
        self,
        decision: str,
        confidence: float,
        reason: str,
    ) -> QuantitativeScoreResult:
        return QuantitativeScoreResult(
            decision=decision,
            calibrated_confidence=confidence,
            sample_size=0,
            win_rate=0.0,
            avg_return=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
            reason=f"Heuristica MT5: {reason}",
            matched_context_count=0,
            rejected_reason="MT5_HEURISTIC_ONLY",
        )

    def _quantitative_score_configuration(self) -> QuantitativeScoreConfiguration:
        configuration = self.configuration_manager.get_configuration()
        return QuantitativeScoreConfiguration(
            candles_loaded=configuration.quantitative_score_candles_loaded,
            feature_lookback=configuration.quantitative_score_feature_lookback,
            forward_return_candles=(
                configuration.quantitative_score_forward_return_candles
            ),
            fast_ma_period=configuration.quantitative_score_fast_ma_period,
            slow_ma_period=configuration.quantitative_score_slow_ma_period,
            rsi_period=configuration.quantitative_score_rsi_period,
            volatility_period=configuration.quantitative_score_atr_period,
            min_sample_size=configuration.quantitative_score_min_sample_size,
            min_profit_factor=configuration.quantitative_score_min_profit_factor,
            min_win_rate=configuration.quantitative_score_min_win_rate,
            confidence_floor=configuration.quantitative_score_confidence_floor,
            confidence_ceiling=configuration.quantitative_score_confidence_ceiling,
            volatility_bucket_method=(
                configuration.quantitative_score_volatility_bucket_method
            ),
            volatility_low_threshold=(
                configuration.quantitative_score_volatility_low_threshold
            ),
            volatility_high_threshold=(
                configuration.quantitative_score_volatility_high_threshold
            ),
            ma_flat_threshold=configuration.quantitative_score_ma_flat_threshold,
            ma_strong_threshold=configuration.quantitative_score_ma_strong_threshold,
            rsi_oversold_threshold=(
                configuration.quantitative_score_rsi_oversold_threshold
            ),
            rsi_overbought_threshold=(
                configuration.quantitative_score_rsi_overbought_threshold
            ),
        )

    def _mt5_safe_mode_configuration(
        self,
        configuration: object,
    ) -> QuantitativeScoreConfiguration:
        candles_loaded = self._positive_int(
            getattr(configuration, "mt5_safe_mode_candles_loaded", 1000),
            1000,
        )
        fast_ma_period = self._positive_int(
            getattr(configuration, "mt5_safe_mode_fast_ma_period", 20),
            20,
        )
        slow_ma_period = self._positive_int(
            getattr(configuration, "mt5_safe_mode_slow_ma_period", 50),
            50,
        )
        return QuantitativeScoreConfiguration(
            candles_loaded=candles_loaded,
            feature_lookback=self._positive_int(
                getattr(configuration, "mt5_safe_mode_momentum_period", 10),
                10,
            ),
            forward_return_candles=1,
            fast_ma_period=fast_ma_period,
            slow_ma_period=max(slow_ma_period, fast_ma_period + 1),
            rsi_period=self._positive_int(
                getattr(configuration, "mt5_safe_mode_rsi_period", 14),
                14,
            ),
            volatility_period=self._positive_int(
                getattr(configuration, "mt5_safe_mode_volatility_period", 20),
                20,
            ),
            min_sample_size=1,
            min_profit_factor=0.0,
            min_win_rate=0.0,
            confidence_floor=0.55,
            confidence_ceiling=1.0,
            volatility_bucket_method="SIMPLE",
            volatility_low_threshold=self._positive_float(
                getattr(configuration, "mt5_safe_mode_volatility_low_threshold", 0.00001),
                0.00001,
            ),
            volatility_high_threshold=1.0,
            ma_flat_threshold=self._positive_float(
                getattr(configuration, "mt5_safe_mode_ma_flat_threshold", 0.00005),
                0.00005,
            ),
            ma_strong_threshold=0.001,
            rsi_oversold_threshold=30.0,
            rsi_overbought_threshold=70.0,
        )

    def _positive_int(self, value: object, fallback: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return fallback
        return parsed if parsed > 0 else fallback

    def _positive_float(self, value: object, fallback: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return fallback
        return parsed if parsed >= 0.0 else fallback

    def _timeframe_optimizer_configuration(self) -> TimeframeOptimizerConfiguration:
        configuration = self.configuration_manager.get_configuration()
        return TimeframeOptimizerConfiguration(
            min_sample_size=configuration.timeframe_optimizer_min_sample_size,
            min_profit_factor=configuration.timeframe_optimizer_min_profit_factor,
            min_win_rate=configuration.timeframe_optimizer_min_win_rate,
            max_allowed_drawdown=(
                configuration.timeframe_optimizer_max_allowed_drawdown
            ),
            min_confidence=configuration.timeframe_optimizer_min_confidence,
        )

    def _quantitative_score_engine(
        self,
        configuration: QuantitativeScoreConfiguration,
    ) -> QuantitativeScoreEngine:
        if self.quantitative_score_engine is not None:
            return self.quantitative_score_engine
        return QuantitativeScoreEngine(configuration)

    def _unavailable_pair_row(
        self,
        pair: str,
        status: str,
        reason: str,
        timeframe: str = "H1",
        configured_candles: int = 0,
        requested_candles: int = 0,
        last_update: str = "",
    ) -> MT5ForexSignalRow:
        diagnostics_status = self._diagnostics_status(
            configured_candles,
            requested_candles,
            "ERRO",
        )
        return MT5ForexSignalRow(
            pair=pair,
            status=status,
            last_price=None,
            last_candle_time="N/D",
            trend="INDEFINIDA",
            momentum=None,
            volatility=None,
            rsi=None,
            short_average=None,
            long_average=None,
            decision="WAIT",
            confidence=0.0,
            reason=reason,
            timeframe=timeframe,
            configured_candles=configured_candles,
            requested_candles=requested_candles,
            received_candles=0,
            research_candles_used=0,
            last_update=last_update,
            diagnostics_status=diagnostics_status,
            diagnostics_log=(
                f"{pair} {timeframe}: {reason} "
                f"configurados={configured_candles}, "
                f"solicitados={requested_candles}, recebidos=0, usados=0."
            ),
        )

    def _analyze_pair(
        self,
        pair: str,
        candles: list[Candle],
        configuration: QuantitativeScoreConfiguration,
        microstructure: dict[str, Any] | None = None,
        timeframe: str = "H1",
        configured_candles: int = 0,
        requested_candles: int = 0,
        last_update: str = "",
        recalculate_research: bool = False,
    ) -> MT5ForexSignalRow:
        feature_started = perf_counter()
        received_candles = len(candles)
        if len(candles) < configuration.slow_ma_period:
            diagnostics_status = self._diagnostics_status(
                configured_candles,
                requested_candles,
                "ERRO",
            )
            return MT5ForexSignalRow(
                pair=pair,
                status="DADOS INSUFICIENTES",
                last_price=self._last_close(candles),
                last_candle_time=self._last_time(candles),
                trend="INDEFINIDA",
                momentum=None,
                volatility=None,
                rsi=None,
                short_average=None,
                long_average=None,
                decision="WAIT",
                confidence=0.0,
                reason=(
                    f"Menos de {configuration.slow_ma_period} candles "
                    "disponiveis; decisao WAIT."
                ),
                candles_loaded=len(candles),
                timeframe=timeframe,
                configured_candles=configured_candles,
                requested_candles=requested_candles,
                received_candles=received_candles,
                research_candles_used=0,
                last_update=last_update,
                diagnostics_status=diagnostics_status,
                diagnostics_log=(
                    f"{pair} {timeframe}: ultimo_candle={self._last_time(candles)}, "
                    f"configurados={configured_candles}, "
                    f"solicitados={requested_candles}, recebidos={received_candles}, "
                    "usados=0."
                ),
                research_cache_status="INSUFFICIENT_DATA",
                latency_breakdown={"features_ms": self._elapsed_ms(feature_started), "score_ms": 0.0},
            )

        closes = [float(candle.fechamento) for candle in candles]
        short_average = self._mean(closes[-configuration.fast_ma_period:])
        long_average = self._mean(closes[-configuration.slow_ma_period:])
        mid_average = self._mean(closes[-min(100, len(closes)):])
        ema_fast = self._ema(closes, configuration.fast_ma_period)
        ema_mid = self._ema(closes, min(50, len(closes)))
        ema_slow = self._ema(closes, configuration.slow_ma_period)
        momentum = self._momentum(closes, configuration.feature_lookback)
        volatility = self._volatility(closes, configuration.volatility_period)
        rsi = self._rsi(closes, configuration.rsi_period)
        atr = self._atr(candles, configuration.volatility_period)
        atr_average = self._atr_average(
            candles,
            configuration.volatility_period,
            min(50, max(1, len(candles))),
        )
        adx = self._adx(candles, configuration.rsi_period)
        macd, macd_signal = self._macd(closes, 12, 26, 9)
        bollinger_upper, bollinger_lower = self._bollinger(closes, 20, 2.0)
        tick_volume = int(candles[-1].volume)
        tick_volume_average = self._volume_average(candles, min(50, len(candles)))
        day_high, day_low = self._session_high_low(candles)
        donchian_high, donchian_low = self._donchian(candles, 20)
        pivot = self._pivot(candles)
        vwap = self._vwap(candles)
        z_score = self._z_score(closes, 20)
        support, resistance = self._support_resistance(candles, 20)
        swing_high, swing_low = self._swing_high_low(candles, 5)
        price_speed = self._price_speed(closes, configuration.feature_lookback)
        spread = self._microstructure_value(microstructure, "spread")
        spread_average = self._spread_average(pair, timeframe, spread)
        slippage_estimate = self._slippage_estimate(
            spread,
            spread_average,
            tick_volume,
            tick_volume_average,
        )
        trend = self._trend(short_average, long_average, configuration)
        candidate_decision, heuristic_confidence, heuristic_reason = self._decision(
            trend,
            momentum,
            volatility,
            rsi,
            configuration,
        )
        moving_average_distance = self._moving_average_distance(
            short_average,
            long_average,
        )
        feature_ms = self._elapsed_ms(feature_started)
        score_ms = 0.0
        score = self._heuristic_score(
            candidate_decision,
            heuristic_confidence,
            heuristic_reason,
        )
        research_cache_status = "HEURISTIC_ONLY"
        reason = score.reason
        research_candles_used = 0
        if recalculate_research:
            score_started = perf_counter()
            observations = self._quantitative_observations(candles, configuration)
            score = self._quantitative_score_engine(configuration).calculate(
                QuantitativeScoreContext(
                    trend=trend,
                    momentum=momentum,
                    volatility=volatility,
                    rsi=rsi,
                    moving_average_distance=moving_average_distance,
                    candidate_decision=candidate_decision,
                ),
                observations,
            )
            score_ms = self._elapsed_ms(score_started)
            research_cache_status = "RECALCULATED"
            reason = score.reason
            research_candles_used = len(observations)
        diagnostics_status = self._diagnostics_status(
            configured_candles,
            requested_candles,
            "OK" if received_candles > 0 else "ERRO",
        )
        return MT5ForexSignalRow(
            pair=pair,
            status="OK",
            last_price=closes[-1],
            last_candle_time=candles[-1].data,
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            rsi=rsi,
            short_average=short_average,
            long_average=long_average,
            mid_average=mid_average,
            ema_fast=ema_fast,
            ema_mid=ema_mid,
            ema_slow=ema_slow,
            adx=adx,
            macd=macd,
            macd_signal=macd_signal,
            atr=atr,
            atr_average=atr_average,
            bollinger_upper=bollinger_upper,
            bollinger_lower=bollinger_lower,
            tick_volume=tick_volume,
            tick_volume_average=tick_volume_average,
            day_high=day_high,
            day_low=day_low,
            donchian_high=donchian_high,
            donchian_low=donchian_low,
            pivot=pivot,
            vwap=vwap,
            z_score=z_score,
            support=support,
            resistance=resistance,
            swing_high=swing_high,
            swing_low=swing_low,
            spread=spread,
            spread_average=spread_average,
            slippage_estimate=slippage_estimate,
            price_speed=price_speed,
            decision=score.decision,
            confidence=score.calibrated_confidence,
            reason=reason,
            candles_loaded=len(candles),
            sample_size=score.sample_size,
            win_rate=score.win_rate,
            avg_return=score.avg_return,
            profit_factor=score.profit_factor,
            max_drawdown=score.max_drawdown,
            matched_context_count=score.matched_context_count,
            rejected_reason=score.rejected_reason,
            volatility_bucket=score.volatility_bucket,
            rsi_bucket=score.rsi_bucket,
            momentum_sign=score.momentum_sign,
            ma_distance_bucket=score.ma_distance_bucket,
            confidence_penalties=score.confidence_penalties,
            confidence_drivers=score.confidence_drivers,
            timeframe=timeframe,
            configured_candles=configured_candles,
            requested_candles=requested_candles,
            received_candles=received_candles,
            research_candles_used=research_candles_used,
            last_update=last_update,
            diagnostics_status=diagnostics_status,
            diagnostics_log=(
                f"{pair} {timeframe}: ultimo_candle={candles[-1].data}, "
                f"configurados={configured_candles}, "
                f"solicitados={requested_candles}, recebidos={received_candles}, "
                f"usados={research_candles_used}."
            ),
            research_cache_status=research_cache_status,
            latency_breakdown={"features_ms": feature_ms, "score_ms": score_ms},
        )

    def _diagnostics_status(
        self,
        configured_candles: int,
        requested_candles: int,
        fallback_status: str,
    ) -> str:
        if configured_candles != requested_candles:
            return "CONFIG_MISMATCH"
        return fallback_status

    def _last_close(self, candles: list[Candle]) -> float | None:
        if not candles:
            return None
        return float(candles[-1].fechamento)

    def _last_time(self, candles: list[Candle]) -> str:
        if not candles:
            return "N/D"
        return candles[-1].data

    def _mean(self, values: list[float]) -> float:
        return sum(values) / len(values)

    def _ema(self, values: list[float], period: int) -> float:
        if not values:
            return 0.0
        if len(values) < period:
            return self._mean(values)
        multiplier = 2.0 / (period + 1.0)
        ema = self._mean(values[:period])
        for value in values[period:]:
            ema = (value * multiplier) + (ema * (1.0 - multiplier))
        return ema

    def _true_ranges(self, candles: list[Candle]) -> list[float]:
        ranges: list[float] = []
        for previous, current in zip(candles[:-1], candles[1:]):
            high = float(current.maxima)
            low = float(current.minima)
            previous_close = float(previous.fechamento)
            ranges.append(
                max(
                    high - low,
                    abs(high - previous_close),
                    abs(low - previous_close),
                )
            )
        return ranges

    def _atr(self, candles: list[Candle], period: int) -> float:
        ranges = self._true_ranges(candles)
        if not ranges:
            return 0.0
        return self._mean(ranges[-period:])

    def _atr_average(
        self,
        candles: list[Candle],
        atr_period: int,
        baseline_period: int,
    ) -> float:
        ranges = self._true_ranges(candles)
        if len(ranges) < atr_period:
            return self._mean(ranges) if ranges else 0.0
        atr_values = [
            self._mean(ranges[index - atr_period : index])
            for index in range(atr_period, len(ranges) + 1)
        ]
        return self._mean(atr_values[-baseline_period:])

    def _adx(self, candles: list[Candle], period: int) -> float:
        if len(candles) <= period:
            return 0.0
        plus_dm: list[float] = []
        minus_dm: list[float] = []
        true_ranges: list[float] = []
        for previous, current in zip(candles[:-1], candles[1:]):
            up_move = float(current.maxima) - float(previous.maxima)
            down_move = float(previous.minima) - float(current.minima)
            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
            minus_dm.append(
                down_move if down_move > up_move and down_move > 0 else 0.0
            )
            high = float(current.maxima)
            low = float(current.minima)
            previous_close = float(previous.fechamento)
            true_ranges.append(
                max(
                    high - low,
                    abs(high - previous_close),
                    abs(low - previous_close),
                )
            )
        dx_values: list[float] = []
        for index in range(period, len(true_ranges) + 1):
            tr_sum = sum(true_ranges[index - period : index])
            if tr_sum == 0.0:
                continue
            plus_di = 100.0 * sum(plus_dm[index - period : index]) / tr_sum
            minus_di = 100.0 * sum(minus_dm[index - period : index]) / tr_sum
            denominator = plus_di + minus_di
            if denominator == 0.0:
                continue
            dx_values.append(100.0 * abs(plus_di - minus_di) / denominator)
        if not dx_values:
            return 0.0
        return self._mean(dx_values[-period:])

    def _macd(
        self,
        closes: list[float],
        fast_period: int,
        slow_period: int,
        signal_period: int,
    ) -> tuple[float, float]:
        if not closes:
            return 0.0, 0.0
        fast_series = self._ema_series(closes, fast_period)
        slow_series = self._ema_series(closes, slow_period)
        macd_series = [
            fast - slow for fast, slow in zip(fast_series, slow_series)
        ]
        macd_value = macd_series[-1]
        signal_value = self._ema(macd_series, signal_period)
        return macd_value, signal_value

    def _ema_series(self, values: list[float], period: int) -> list[float]:
        if not values:
            return []
        multiplier = 2.0 / (period + 1.0)
        ema = values[0]
        series: list[float] = []
        for value in values:
            ema = (value * multiplier) + (ema * (1.0 - multiplier))
            series.append(ema)
        return series

    def _bollinger(
        self,
        closes: list[float],
        period: int,
        standard_deviations: float,
    ) -> tuple[float, float]:
        if not closes:
            return 0.0, 0.0
        window = closes[-period:]
        average = self._mean(window)
        deviation = pstdev(window) if len(window) > 1 else 0.0
        return (
            average + (standard_deviations * deviation),
            average - (standard_deviations * deviation),
        )

    def _volume_average(self, candles: list[Candle], period: int) -> float:
        volumes = [float(candle.volume) for candle in candles[-period:]]
        return self._mean(volumes) if volumes else 0.0

    def _symbol_microstructure(self, symbol: str) -> dict[str, Any]:
        reader = getattr(self.provider, "get_symbol_microstructure", None)
        if not callable(reader):
            return {}
        try:
            microstructure = reader(symbol)
        except (OSError, RuntimeError, ValueError, TypeError):
            return {}
        if not isinstance(microstructure, dict):
            return {}
        return dict(microstructure)

    def _microstructure_value(
        self,
        microstructure: dict[str, Any] | None,
        name: str,
    ) -> float | None:
        if not microstructure:
            return None
        try:
            value = float(microstructure.get(name))
        except (TypeError, ValueError):
            return None
        if value <= 0.0:
            return None
        return value

    def _spread_average(
        self,
        pair: str,
        timeframe: str,
        spread: float | None,
    ) -> float | None:
        if spread is None:
            return None
        key = (pair, timeframe)
        history = list(self.latest_spread_history.get(key, []))
        history.append(float(spread))
        history = history[-50:]
        self.latest_spread_history[key] = history
        return self._mean(history)

    def _slippage_estimate(
        self,
        spread: float | None,
        spread_average: float | None,
        tick_volume: int | None,
        tick_volume_average: float | None,
    ) -> float | None:
        if spread is None and spread_average is None:
            return None
        reference_spread = max(
            float(spread or 0.0),
            float(spread_average or 0.0),
        )
        if reference_spread <= 0.0:
            return None
        relative_volume = 1.0
        if tick_volume and tick_volume_average and tick_volume_average > 0.0:
            relative_volume = max(0.25, min(2.0, tick_volume / tick_volume_average))
        return reference_spread / relative_volume

    def _session_high_low(self, candles: list[Candle]) -> tuple[float, float]:
        if not candles:
            return 0.0, 0.0
        last_date = str(candles[-1].data).replace("T", " ").split(" ")[0]
        session = [
            candle
            for candle in candles
            if str(candle.data).replace("T", " ").split(" ")[0] == last_date
        ]
        if not session:
            session = [candles[-1]]
        return (
            max(float(candle.maxima) for candle in session),
            min(float(candle.minima) for candle in session),
        )

    def _donchian(self, candles: list[Candle], period: int) -> tuple[float, float]:
        window = candles[-period:] if candles else []
        if not window:
            return 0.0, 0.0
        return (
            max(float(candle.maxima) for candle in window),
            min(float(candle.minima) for candle in window),
        )

    def _pivot(self, candles: list[Candle]) -> float:
        if not candles:
            return 0.0
        reference = candles[-2] if len(candles) > 1 else candles[-1]
        return (
            float(reference.maxima)
            + float(reference.minima)
            + float(reference.fechamento)
        ) / 3.0

    def _vwap(self, candles: list[Candle]) -> float:
        if not candles:
            return 0.0
        total_volume = sum(max(float(candle.volume), 0.0) for candle in candles)
        if total_volume == 0.0:
            return 0.0
        total_price_volume = sum(
            (
                (
                    float(candle.maxima)
                    + float(candle.minima)
                    + float(candle.fechamento)
                )
                / 3.0
            )
            * max(float(candle.volume), 0.0)
            for candle in candles
        )
        return total_price_volume / total_volume

    def _z_score(self, values: list[float], period: int) -> float:
        window = values[-period:]
        if len(window) < 2:
            return 0.0
        average = self._mean(window)
        deviation = pstdev(window)
        if deviation == 0.0:
            return 0.0
        return (window[-1] - average) / deviation

    def _support_resistance(
        self,
        candles: list[Candle],
        period: int,
    ) -> tuple[float, float]:
        window = candles[-period:] if candles else []
        if not window:
            return 0.0, 0.0
        return (
            min(float(candle.minima) for candle in window),
            max(float(candle.maxima) for candle in window),
        )

    def _swing_high_low(
        self,
        candles: list[Candle],
        lookback: int,
    ) -> tuple[float, float]:
        if len(candles) < (lookback * 2) + 1:
            return self._support_resistance(candles, min(len(candles), lookback))
        recent = candles[-((lookback * 2) + 1) :]
        center = recent[lookback]
        is_swing_high = all(
            float(center.maxima) >= float(candle.maxima)
            for index, candle in enumerate(recent)
            if index != lookback
        )
        is_swing_low = all(
            float(center.minima) <= float(candle.minima)
            for index, candle in enumerate(recent)
            if index != lookback
        )
        high = float(center.maxima) if is_swing_high else max(
            float(candle.maxima) for candle in recent
        )
        low = float(center.minima) if is_swing_low else min(
            float(candle.minima) for candle in recent
        )
        return high, low

    def _price_speed(self, closes: list[float], period: int) -> float:
        if len(closes) <= period:
            return 0.0
        return (closes[-1] - closes[-period - 1]) / float(period)

    def _momentum(self, closes: list[float], period: int) -> float:
        previous = closes[-period - 1]
        if previous == 0:
            return 0.0
        return (closes[-1] / previous) - 1.0

    def _volatility(self, closes: list[float], period: int) -> float:
        returns = [
            (current / previous) - 1.0
            for previous, current in zip(
                closes[-period - 1 : -1],
                closes[-period:],
            )
            if previous != 0
        ]
        if len(returns) < 2:
            return 0.0
        return pstdev(returns)

    def _rsi(self, closes: list[float], period: int) -> float:
        deltas = [
            current - previous
            for previous, current in zip(
                closes[-period - 1 : -1],
                closes[-period:],
            )
        ]
        gains = [delta for delta in deltas if delta > 0]
        losses = [-delta for delta in deltas if delta < 0]
        average_gain = sum(gains) / period
        average_loss = sum(losses) / period
        if average_loss == 0:
            return 100.0
        relative_strength = average_gain / average_loss
        return 100.0 - (100.0 / (1.0 + relative_strength))

    def _trend(
        self,
        short_average: float,
        long_average: float,
        configuration: QuantitativeScoreConfiguration,
    ) -> str:
        tolerance = abs(long_average) * configuration.ma_flat_threshold
        if short_average > long_average + tolerance:
            return "ALTA"
        if short_average < long_average - tolerance:
            return "BAIXA"
        return "INDEFINIDA"

    def _moving_average_distance(
        self,
        short_average: float,
        long_average: float,
    ) -> float:
        if long_average == 0.0:
            return 0.0
        return (short_average / long_average) - 1.0

    def _quantitative_observations(
        self,
        candles: list[Candle],
        configuration: QuantitativeScoreConfiguration,
    ) -> list[QuantitativeScoreObservation]:
        observations: list[QuantitativeScoreObservation] = []
        closes = [float(candle.fechamento) for candle in candles]
        start_index = max(
            configuration.slow_ma_period,
            configuration.feature_lookback,
            configuration.rsi_period,
            configuration.volatility_period,
        )
        end_index = len(closes) - configuration.forward_return_candles
        for index in range(start_index, end_index):
            window = closes[: index + 1]
            next_close = closes[index + configuration.forward_return_candles]
            current_close = closes[index]
            if current_close == 0.0:
                continue
            short_average = self._mean(window[-configuration.fast_ma_period:])
            long_average = self._mean(window[-configuration.slow_ma_period:])
            momentum = self._momentum(window, configuration.feature_lookback)
            volatility = self._volatility(window, configuration.volatility_period)
            rsi = self._rsi(window, configuration.rsi_period)
            trend = self._trend(short_average, long_average, configuration)
            candidate_decision, _, _ = self._decision(
                trend,
                momentum,
                volatility,
                rsi,
                configuration,
            )
            observations.append(
                QuantitativeScoreObservation(
                    trend=trend,
                    momentum=momentum,
                    volatility=volatility,
                    rsi=rsi,
                    moving_average_distance=self._moving_average_distance(
                        short_average,
                        long_average,
                    ),
                    candidate_decision=candidate_decision,
                    forward_return=(next_close / current_close) - 1.0,
                )
            )
        return observations

    def _decision(
        self,
        trend: str,
        momentum: float,
        volatility: float,
        rsi: float,
        configuration: QuantitativeScoreConfiguration,
    ) -> tuple[str, float, str]:
        sufficient_volatility = (
            volatility >= configuration.volatility_low_threshold
        )
        if not sufficient_volatility:
            return (
                "WAIT",
                configuration.confidence_floor,
                "Volatilidade insuficiente para leitura confiavel.",
            )

        if (
            trend == "ALTA"
            and momentum > 0
            and rsi < configuration.rsi_overbought_threshold
        ):
            return (
                "BUY",
                configuration.confidence_floor,
                "Tendencia positiva, momentum positivo, RSI saudavel e volatilidade suficiente.",
            )
        if (
            trend == "BAIXA"
            and momentum < 0
            and rsi > configuration.rsi_oversold_threshold
        ):
            return (
                "SELL",
                configuration.confidence_floor,
                "Tendencia negativa, momentum negativo, RSI saudavel e volatilidade suficiente.",
            )
        if trend == "INDEFINIDA":
            return (
                "WAIT",
                configuration.confidence_floor,
                "Tendencia indefinida pelas medias curta e longa.",
            )
        return (
            "WAIT",
            configuration.confidence_floor,
            "Sinais conflitantes entre tendencia, momentum, RSI e volatilidade.",
        )


def _create_default_provider() -> ReadOnlyCandleProvider:
    from infrastructure.market_data import MT5MarketDataProvider

    return MT5MarketDataProvider()
