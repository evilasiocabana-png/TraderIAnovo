"""Servico temporal para robo MT5 Demo sem loop autonomo."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from application.demo_execution_service import DemoExecutionService
from application.lab_operational_model_service import (
    MODEL_3_ID as HISTORICAL_MODEL_3_ID,
    MODEL_8_ID as HISTORICAL_MODEL_8_ID,
    MODEL_9_ID as HISTORICAL_MODEL_9_ID,
    MODEL_10_ID as HISTORICAL_MODEL_10_ID,
)
from application.dynamic_exit_model_family import (
    dynamic_exit_source_model,
)
from application.model3_all_forex_winners import (
    MODEL_3_ID as HISTORICAL_ALL_FOREX_MODEL_3_ID,
)
from application.model3_xau_m5_rsi50_flip import MODEL_3_ID
from application.market_regime_pipeline import MarketRegimePipeline
from application.model6_lab_forex_expansion import MODEL_6_ID
from application.model7_lab_alternative_markets import MODEL_7_ID
from application.model8_xau_m5_sma_rsi_reentry import MODEL_8_ID, MODEL_8_SYMBOL
from application.xau_m5_sma_rsi_model_family import (
    XAU_IMPROVED_REENTRY_MODEL_IDS,
    XAU_ALL_TREND_FILTER_MODEL_IDS as XAU_TREND_FILTER_MODEL_IDS,
    xau_model_requires_target,
)
from application.forex_m5_sma_rsi_model_family import (
    FOREX_SMA_RSI_POSITION_MANAGEMENT_MODEL_IDS as FOREX_SMA_RSI_MODEL_IDS,
)
from application.model15_xau_m5_breakout import MODEL_15_ID
from application.model16_xau_m5_price_ema_breakout import MODEL_16_ID
from application.model23_basket_accumulator import (
    MODEL_23_ENTRY_SOURCE,
    is_model23,
)
from application.model24_xau_basket import (
    MODEL_24_CONTINUATION_VOLUME,
    MODEL_24_ENTRY_SOURCE,
    MODEL_24_INITIAL_VOLUME,
    MODEL_24_REENTRY_VOLUME,
    is_model24,
)
from application.model25_multi_asset_rsi50_basket import (
    MODEL_25_ENTRY_SOURCE,
    MODEL_25_INITIAL_VOLUME,
    MODEL_25_REENTRY_VOLUME,
    MODEL_25_SOURCE_MODEL_IDS,
    MODEL_25_TIMEFRAME,
    is_model25,
)
from application.model26_xau_m5_smart_money import (
    MODEL_26_VOLUME,
    is_model26,
)
from application.model6_original_trend_momentum import (
    MODEL_6_ID as HISTORICAL_MODEL_6_ID,
)
from application.model7_trend_momentum_dynamic import (
    MODEL_7_ID as HISTORICAL_MODEL_7_ID,
)
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from domain.operational_model_policy import is_retired_operational_model
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal


DEFAULT_ALPHA_ID = "ALPHA007"
DEFAULT_ALPHA_VERSION = "v1.6"
SESSION_POLICY_VERSION = "v2.1"
EXECUTION_PIPELINE_VERSION = "v3.4"
LAB_CONFIGURATION_VERSION = "v8"
TRADE_PLAN_VERSION = "TP v5"
EXECUTION_ENGINE_VERSION = "ExecutionEngine v1"
INDICATOR_BUNDLE_VERSION = "Indicators v9"
MICROSTRUCTURE_VERSION = "Micro v2"
VALIDATION_PIPELINE_VERSION = "VAL v4"
STRATEGY_DEFINITION_VERSION = "STRAT v3"
DEFAULT_BETA_ID = "BETA001"
DEFAULT_BETA_VERSION = "BETA v1"
DEFAULT_OPERATIONAL_MODEL = "MODELO_1_ALPHA_ATUAL"
HARD_TEMPORAL_BLOCK_STATUSES = {
    "FIM_DE_SEMANA_BLOQUEADO",
    "DOMINGO_ABERTURA_BLOQUEADO",
    "SEXTA_FINAL_BLOQUEADO",
    "ROLLOVER_BLOQUEADO",
    "ROLLOVER_SERVIDOR_MT5_BLOQUEADO",
}


@dataclass(frozen=True)
class MT5DemoRobotSignal:
    """Sinal avaliado pelo robo temporal a partir do modelo ativo."""

    symbol: str
    timeframe: str
    candle_time: str
    decision: str
    confidence: float
    active_model: str
    reason: str
    alpha_id: str = DEFAULT_ALPHA_ID
    alpha_version: str = DEFAULT_ALPHA_VERSION
    lab_configuration_version: str = LAB_CONFIGURATION_VERSION
    indicator_bundle_version: str = INDICATOR_BUNDLE_VERSION
    microstructure_version: str = MICROSTRUCTURE_VERSION
    validation_pipeline_version: str = VALIDATION_PIPELINE_VERSION
    strategy_definition_version: str = STRATEGY_DEFINITION_VERSION
    technical_score: float = 0.0
    historical_confirmation: float = 0.0
    temporal_blocked: bool = False
    temporal_status: str = "N/D"
    temporal_reason: str = ""
    session_filter_enabled: bool = False
    session_filter_result: str = "ALLOWED"
    session_filter_reason: str = ""
    forex_session: str = "N/D"
    forex_session_open: bool = False
    timestamp_utc: str = "N/D"
    timestamp_brt: str = "N/D"
    weekday: str = "N/D"
    is_rollover: bool = False
    is_london_ny_overlap: bool = False
    is_sunday_open: bool = False
    is_friday_late: bool = False
    macro_event_blocked: bool = False
    macro_event_reason: str = ""
    entry_filter_blocked: bool = False
    entry_filter_status: str = "OK"
    entry_filter_reason: str = "Sem filtro NV-V robusto aplicado."
    entry_filter_parameter: str = "SEM_FILTRO_ROBUSTO"
    entry_filter_reading: str = "N/D"
    operational_model: str = DEFAULT_OPERATIONAL_MODEL
    last_price: float | None = None
    trend: str = "INDEFINIDA"
    momentum: float | None = None
    volatility: float | None = None
    rsi: float | None = None
    short_average: float | None = None
    long_average: float | None = None
    mid_average: float | None = None
    ema_fast: float | None = None
    ema_mid: float | None = None
    ema_slow: float | None = None
    atr: float | None = None
    support: float | None = None
    resistance: float | None = None
    swing_high: float | None = None
    swing_low: float | None = None


@dataclass(frozen=True)
class MT5DemoTradePlan:
    """Plano de trade ja produzido pela camada de pesquisa."""

    symbol: str
    timeframe: str
    entry_price: float
    stop: float
    target: float
    risk_reward: float
    source: str = "RESEARCH_LAB"
    status: str = "PLANO_VALIDO"
    stop_reason: str = ""
    target_reason: str = ""
    exit_model: str = "NONE"
    stop_management: str = "DYNAMIC_POSITION_MANAGER"
    stop_management_parameters: dict[str, object] = field(default_factory=dict)
    alpha_id: str = DEFAULT_ALPHA_ID
    alpha_version: str = DEFAULT_ALPHA_VERSION
    beta_id: str = DEFAULT_BETA_ID
    beta_version: str = DEFAULT_BETA_VERSION
    beta_mode: str = "PROTECT_ONLY"
    operational_model: str = DEFAULT_OPERATIONAL_MODEL
    trade_plan_version: str = TRADE_PLAN_VERSION
    mirror_pair_id: str = ""
    mirror_pair_role: str = ""


@dataclass(frozen=True)
class MT5DemoRobotResult:
    """Resultado de uma avaliacao temporal do robo MT5 Demo."""

    status: str
    message: str
    symbol: str
    timeframe: str
    candle_time: str
    decision: str
    executed: bool = False
    execution_result: ExecutionResult | None = None
    trade_plan: MT5DemoTradePlan | None = None


@dataclass
class MT5DemoRobotService:
    """Executa apenas entradas autorizadas pelo regime em conta MT5 Demo."""

    execution_service: DemoExecutionService = field(default_factory=DemoExecutionService)
    market_regime_pipeline: MarketRegimePipeline = field(
        default_factory=MarketRegimePipeline
    )
    enabled: bool = False
    volume: float = 0.1
    last_candle_by_market: dict[tuple[str, str, str], str] = field(default_factory=dict)
    last_decision_by_market: dict[tuple[str, str, str], str] = field(default_factory=dict)

    def evaluate_once(
        self,
        signal: MT5DemoRobotSignal,
        trade_plan: MT5DemoTradePlan,
    ) -> MT5DemoRobotResult:
        """Avalia um candle novo e executa somente regime autorizado."""
        key = self._execution_key(signal)
        if not self.enabled:
            return self._result(
                "DISABLED",
                "Kill switch demo ativo. Robo temporal nao executou.",
                signal,
                trade_plan,
            )
        if is_retired_operational_model(signal.operational_model):
            return self._result(
                "MODEL_RETIRED",
                "Modelo operacional aposentado nao abre novas ordens.",
                signal,
                trade_plan,
            )
        if self.last_candle_by_market.get(key) == signal.candle_time:
            return self._result(
                "NO_NEW_CANDLE",
                "Candle ja avaliado pelo robo temporal.",
                signal,
                trade_plan,
            )

        current_decision = str(signal.decision).upper()

        if current_decision not in {"BUY", "SELL"}:
            self._mark_candle_evaluated(key, signal.candle_time, current_decision)
            return self._result(
                "NO_SIGNAL",
                "Modelo ativo nao gerou BUY/SELL no candle novo.",
                signal,
                trade_plan,
            )
        regime_signal = self._regime_validation_signal(signal)
        if regime_signal is not None:
            regime_result = self.market_regime_pipeline.evaluate(regime_signal)
            if not regime_result.authorized:
                self._mark_candle_evaluated(key, signal.candle_time, current_decision)
                return self._result(
                    regime_result.block_reason or "REGIME_BLOCKED",
                    regime_result.message or "Regime de mercado nao autorizou entrada.",
                    signal,
                    trade_plan,
                )
            expected_regime_direction = str(regime_signal.decision).upper()
            if regime_result.direction != expected_regime_direction:
                self._mark_candle_evaluated(key, signal.candle_time, current_decision)
                return self._result(
                    "REGIME_DIRECTION_MISMATCH",
                    (
                        "Regime autorizou "
                        f"{regime_result.direction}, mas a origem M1 pede "
                        f"{expected_regime_direction}."
                    ),
                    signal,
                    trade_plan,
                )
        hard_temporal_block = (
            signal.temporal_blocked
            and str(signal.temporal_status or "").upper()
            in HARD_TEMPORAL_BLOCK_STATUSES
        )
        if signal.temporal_blocked and (
            signal.session_filter_enabled or hard_temporal_block
        ):
            self._mark_candle_evaluated(key, signal.candle_time, current_decision)
            return self._result(
                "TEMPORAL_BLOCKED",
                signal.temporal_reason
                or f"Bloqueio temporal do Research Lab: {signal.temporal_status}.",
                signal,
                trade_plan,
            )
        if signal.macro_event_blocked:
            self._mark_candle_evaluated(key, signal.candle_time, current_decision)
            return self._result(
                "MACRO_EVENT_BLOCKED",
                signal.macro_event_reason
                or "Bloqueio por evento macroeconomico ativo.",
                signal,
                trade_plan,
            )
        if signal.entry_filter_blocked:
            self._mark_candle_evaluated(key, signal.candle_time, current_decision)
            return self._result(
                "ENTRY_FILTER_BLOCKED",
                signal.entry_filter_reason
                or "Filtro de entrada NV-V bloqueou a operacao.",
                signal,
                trade_plan,
            )
        validation_message = self._trade_plan_validation(signal, trade_plan)
        if validation_message:
            return self._result(
                "NO_TRADE_PLAN",
                validation_message,
                signal,
                trade_plan,
            )

        order_volume = self._execution_volume(signal, trade_plan)
        context = self.execution_service.decision_pipeline.processar(
            StrategySignal(
                current_decision,
                int(round(float(signal.confidence) * 100)),
                float(signal.confidence),
                [signal.reason],
            ),
            MarketSnapshot(
                symbol=signal.symbol,
                datetime=signal.candle_time,
                regime=signal.active_model,
                volatility=0.0,
                liquidity=0.0,
                trend_strength=0.0,
                market_dna_score=float(signal.confidence) * 100.0,
            ),
            RiskDecision(
                True,
                "Risco aprovado pelo robo demo temporal.",
                order_volume,
                1.0,
            ),
        )
        plan_snapshot = self._trade_plan_snapshot(
            signal,
            trade_plan,
            current_decision,
        )
        plan_snapshot["execution_volume"] = order_volume
        order = ExecutionOrder(
            symbol=trade_plan.symbol,
            side=current_decision,
            quantity=order_volume,
            entry_price=float(trade_plan.entry_price),
            stop=float(trade_plan.stop),
            target=float(trade_plan.target),
            plan_identity=self._trade_plan_identity(signal, trade_plan),
            entry_setup=signal.active_model,
            exit_setup=trade_plan.stop_management,
            exit_policy=trade_plan.stop_management,
            alpha_id=trade_plan.alpha_id or signal.alpha_id,
            alpha_version=trade_plan.alpha_version or signal.alpha_version,
            beta_id=trade_plan.beta_id or DEFAULT_BETA_ID,
            beta_version=trade_plan.beta_version or DEFAULT_BETA_VERSION,
            beta_mode=trade_plan.beta_mode or "PROTECT_ONLY",
            operational_model=signal.operational_model,
            plan_snapshot=plan_snapshot,
        )
        self.execution_service.pending_audit_metadata = {
            "plan_snapshot": order.plan_snapshot,
            "operational_model": signal.operational_model,
            "alpha_id": trade_plan.alpha_id or signal.alpha_id,
            "alpha_version": trade_plan.alpha_version or signal.alpha_version,
            "beta_id": trade_plan.beta_id or DEFAULT_BETA_ID,
            "beta_version": trade_plan.beta_version or DEFAULT_BETA_VERSION,
            "beta_mode": trade_plan.beta_mode or "PROTECT_ONLY",
            "session_policy_version": SESSION_POLICY_VERSION,
            "execution_pipeline_version": EXECUTION_PIPELINE_VERSION,
            "lab_configuration_version": signal.lab_configuration_version,
            "trade_plan_version": trade_plan.trade_plan_version,
            "execution_engine_version": EXECUTION_ENGINE_VERSION,
            "indicator_bundle_version": signal.indicator_bundle_version,
            "microstructure_version": signal.microstructure_version,
            "validation_pipeline_version": signal.validation_pipeline_version,
            "strategy_definition_version": signal.strategy_definition_version,
            "technical_score": signal.technical_score,
            "historical_confirmation": signal.historical_confirmation,
            "entry_filter_status": signal.entry_filter_status,
            "entry_filter_parameter": signal.entry_filter_parameter,
            "entry_filter_reading": signal.entry_filter_reading,
            "entry_filter_reason": signal.entry_filter_reason,
            "risk_reward": trade_plan.risk_reward,
            "candle_time": signal.candle_time,
            "mt5_position": "OPEN" if current_decision in {"BUY", "SELL"} else "N/D",
            "forex_session": signal.forex_session,
            "forex_session_open": signal.forex_session_open,
            "session_filter_enabled": signal.session_filter_enabled,
            "session_filter_result": signal.session_filter_result,
            "session_reason": signal.session_filter_reason
            or signal.temporal_reason
            or signal.temporal_status,
            "timestamp_utc": signal.timestamp_utc,
            "timestamp_brt": signal.timestamp_brt,
            "weekday": signal.weekday,
            "is_rollover": signal.is_rollover,
            "is_london_ny_overlap": signal.is_london_ny_overlap,
            "is_sunday_open": signal.is_sunday_open,
            "is_friday_late": signal.is_friday_late,
        }
        execution = self.execution_service.submit_demo_order(
            context,
            order,
            paper_validated=True,
        )
        if execution.accepted or self._is_terminal_rejection(execution.message):
            self._mark_candle_evaluated(key, signal.candle_time, current_decision)
        return MT5DemoRobotResult(
            status="EXECUTED" if execution.accepted else "REJECTED",
            message=execution.message,
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            candle_time=signal.candle_time,
            decision=current_decision,
            executed=execution.accepted,
            execution_result=execution,
            trade_plan=trade_plan,
        )

    def _is_inverse_operational_model_signal(self, signal: MT5DemoRobotSignal) -> bool:
        model = str(getattr(signal, "operational_model", "") or "").upper()
        return model in {
            "MODELO_2_ESPELHO_BETA2_RR1",
            "MODELO_4_ESPELHO_M1",
            "MODELO_6_ESPELHO_M5",
        }

    def _regime_validation_signal(
        self,
        signal: MT5DemoRobotSignal,
    ) -> MT5DemoRobotSignal | None:
        """Nao sobrepoe regime legado aos modelos com Alpha canonica completa."""
        model = str(getattr(signal, "operational_model", "") or "").upper()
        if is_model23(model) or is_model24(model) or is_model25(model):
            # O M23 recebe somente sinais que ja venceram todos os gates do
            # modelo-fonte. Reaplicar o regime legado aqui distorceria a fonte.
            return None
        dynamic_source = dynamic_exit_source_model(model)
        if dynamic_source is not None:
            # A variante deve repetir todos os gates de entrada da origem. M8
            # herda o regime adicional do M1; M9-M14 preservam o bypass dos
            # modelos canonicos M2-M7, que ja calculam o proprio regime.
            return signal if dynamic_source == DEFAULT_OPERATIONAL_MODEL else None
        if model in {
            "MODELO_2_LAB_ALPHA_SUGERIDA_1_PLUS",
            MODEL_3_ID,
            HISTORICAL_MODEL_3_ID,
            HISTORICAL_ALL_FOREX_MODEL_3_ID,
            "MODELO_4_LAB_CONTEXTUAL_MTF",
            "MODELO_5_LAB_CONSOLIDADO",
            MODEL_6_ID,
            MODEL_7_ID,
            HISTORICAL_MODEL_6_ID,
            HISTORICAL_MODEL_7_ID,
            HISTORICAL_MODEL_8_ID,
            HISTORICAL_MODEL_9_ID,
            HISTORICAL_MODEL_10_ID,
            MODEL_8_ID,
            MODEL_15_ID,
            MODEL_16_ID,
            *XAU_TREND_FILTER_MODEL_IDS,
            *FOREX_SMA_RSI_MODEL_IDS,
        }:
            # Sessao, regime, momentum, volatilidade e demais indicadores ja
            # pertencem ao sinal reproduzido pelo adaptador canonico do Lab.
            return None
        if model == "MODELO_4_ESPELHO_M1":
            original_direction = (
                "BUY" if str(signal.decision).upper() == "SELL" else "SELL"
            )
            return replace(signal, decision=original_direction)
        if self._is_inverse_operational_model_signal(signal):
            return None
        return signal

    def _trade_plan_validation(
        self,
        signal: MT5DemoRobotSignal,
        trade_plan: MT5DemoTradePlan,
    ) -> str:
        if self._market_key(signal.symbol, signal.timeframe) != self._market_key(
            trade_plan.symbol,
            trade_plan.timeframe,
        ):
            return "Plano do Research Lab pertence a outro simbolo/timeframe."
        if trade_plan.source not in {
            "RESEARCH_LAB",
            "PRICE_ACTION_MODEL",
            "M6_ORIGINAL_MARCO_ZERO",
            "M7_DYNAMIC_MARCO_ZERO",
            "MODEL_15_MANUAL_RULE",
            "MODEL_16_MANUAL_RULE",
            "MODEL_3_MANUAL_RULE",
            "MODEL_8_MANUAL_RULE",
            "MODEL_9_MANUAL_RULE",
            "MODEL_10_MANUAL_RULE",
            "MODEL_11_MANUAL_RULE",
            "MODEL_12_MANUAL_RULE",
            "MODEL_18_FROM_M8_REENTRY_TP75",
            "MODEL_19_FROM_M9_REENTRY_TP75",
            "MODEL_20_FROM_M10_REENTRY_TP75",
            "MODEL_21_FROM_M11_REENTRY_TP75",
            "MODEL_22_FROM_M12_REENTRY_TP75",
            "MODEL_18_FROM_M8_REENTRY_STRUCTURAL_TARGET",
            "MODEL_19_FROM_M9_REENTRY_STRUCTURAL_TARGET",
            "MODEL_20_FROM_M10_REENTRY_STRUCTURAL_TARGET",
            "MODEL_21_FROM_M11_REENTRY_STRUCTURAL_TARGET",
            "MODEL_22_FROM_M12_REENTRY_STRUCTURAL_TARGET",
            "MODEL_13_FOREX_MANUAL_RULE",
            "MODEL_14_FOREX_MANUAL_RULE",
            "MODEL_15_FOREX_MANUAL_RULE",
            "MODEL_16_FOREX_MANUAL_RULE",
            "MODEL_17_FOREX_MANUAL_RULE",
            MODEL_23_ENTRY_SOURCE,
            MODEL_24_ENTRY_SOURCE,
            MODEL_25_ENTRY_SOURCE,
        }:
            return "Plano de trade nao veio de fonte operacional autorizada."
        if trade_plan.status != "PLANO_VALIDO":
            return "Plano do Research Lab nao esta com status PLANO_VALIDO."
        parameters = dict(trade_plan.stop_management_parameters or {})
        validation_model = str(signal.operational_model or "").upper()
        validation_is_model24 = is_model24(validation_model)
        validation_is_model25 = is_model25(validation_model)
        source_operational_model = str(
            parameters.get("source_operational_model") or ""
        ).upper()
        validation_is_model25_source = bool(
            validation_is_model25
            and source_operational_model in MODEL_25_SOURCE_MODEL_IDS
        )
        if validation_is_model25 and (
            str(signal.symbol or "").upper() != MODEL_8_SYMBOL
            or str(signal.timeframe or "").upper() != MODEL_25_TIMEFRAME
        ):
            return "M25 opera exclusivamente XAUUSD/M5."
        if (
            is_model23(validation_model)
            or validation_is_model24
            or validation_is_model25_source
        ):
            validation_model = str(
                parameters.get("source_operational_model") or ""
            ).upper()
            if not validation_model:
                return "Plano de cesta sem modelo-fonte para validar SL/TP."
        requires_target = (not validation_is_model24) and (
            not validation_is_model25 or validation_is_model25_source
        ) and xau_model_requires_target(
            validation_model,
            parameters.get("active_entry_order_type"),
        )
        no_target_model = validation_model in {
            MODEL_3_ID,
            MODEL_8_ID,
            MODEL_15_ID,
            MODEL_16_ID,
            *XAU_TREND_FILTER_MODEL_IDS,
            *FOREX_SMA_RSI_MODEL_IDS,
        } and not requires_target
        if validation_is_model24:
            no_target_model = not (
                bool(parameters.get("m24_individual_target_enabled"))
                and float(trade_plan.target or 0.0) > 0.0
            )
        if validation_is_model25 and not validation_is_model25_source:
            no_target_model = not (
                str(parameters.get("m25_entry_role") or "").upper()
                in {"REENTRY", "STRUCTURAL_REENTRY"}
                and bool(parameters.get("m25_individual_target_enabled"))
                and float(trade_plan.target or 0.0) > 0.0
            )
        if trade_plan.risk_reward <= 0 and not no_target_model:
            return "Plano do Research Lab sem RR valido."
        if signal.decision == "BUY" and not (
            trade_plan.stop < trade_plan.entry_price
            and (no_target_model or trade_plan.entry_price < trade_plan.target)
        ):
            return "Plano BUY invalido: stop/entrada/alvo inconsistentes."
        if signal.decision == "SELL" and not (
            trade_plan.entry_price < trade_plan.stop
            and (no_target_model or trade_plan.target < trade_plan.entry_price)
        ):
            return "Plano SELL invalido: alvo/entrada/stop inconsistentes."
        return ""

    def _trade_plan_identity(
        self,
        signal: MT5DemoRobotSignal,
        trade_plan: MT5DemoTradePlan,
    ) -> str:
        """Identifica quando o Lab realmente produziu um novo plano/candle."""
        parts = (
            trade_plan.symbol,
            trade_plan.timeframe,
            signal.candle_time,
            signal.active_model,
            trade_plan.trade_plan_version,
            trade_plan.source,
            trade_plan.status,
            trade_plan.beta_id,
            trade_plan.beta_version,
            trade_plan.operational_model,
        )
        return "|".join(str(part or "N/D").upper() for part in parts)

    def _trade_plan_snapshot(
        self,
        signal: MT5DemoRobotSignal,
        trade_plan: MT5DemoTradePlan,
        direction: str,
    ) -> dict[str, object]:
        """Congela os parametros reais usados no envio, sem recalcular depois."""
        parameters = dict(trade_plan.stop_management_parameters)
        return {
            "schema_version": "1.0",
            "symbol": trade_plan.symbol,
            "timeframe": trade_plan.timeframe,
            "candle_time": signal.candle_time,
            "direction": direction,
            "entry_price": float(trade_plan.entry_price),
            "initial_stop": float(trade_plan.stop),
            "target": float(trade_plan.target),
            "risk_reward": float(trade_plan.risk_reward),
            "source": trade_plan.source,
            "status": trade_plan.status,
            "plan_identity": self._trade_plan_identity(signal, trade_plan),
            "trade_plan_version": trade_plan.trade_plan_version,
            "operational_model": signal.operational_model,
            "entry_setup": signal.active_model,
            "exit_setup": trade_plan.stop_management,
            "exit_model": trade_plan.exit_model,
            "stop_management": trade_plan.stop_management,
            "stop_management_parameters": parameters,
            "indicator_source": parameters.get("indicator_source", "N/D"),
            "indicator_generated_at": parameters.get(
                "indicator_generated_at", "N/D"
            ),
            "indicator_closed_candle_time": parameters.get(
                "indicator_closed_candle_time", "N/D"
            ),
            "stop_reason": trade_plan.stop_reason,
            "target_reason": trade_plan.target_reason,
            "alpha_id": trade_plan.alpha_id or signal.alpha_id,
            "alpha_version": trade_plan.alpha_version or signal.alpha_version,
            "beta_id": trade_plan.beta_id,
            "beta_version": trade_plan.beta_version,
            "beta_mode": trade_plan.beta_mode,
            "mirror_pair_id": trade_plan.mirror_pair_id,
            "mirror_pair_role": trade_plan.mirror_pair_role,
            "lab_configuration_version": signal.lab_configuration_version,
            "indicator_bundle_version": signal.indicator_bundle_version,
            "microstructure_version": signal.microstructure_version,
            "validation_pipeline_version": signal.validation_pipeline_version,
            "strategy_definition_version": signal.strategy_definition_version,
            "technical_score": float(signal.technical_score),
            "historical_confirmation": float(signal.historical_confirmation),
            "entry_filter_status": signal.entry_filter_status,
            "entry_filter_parameter": signal.entry_filter_parameter,
            "entry_filter_reading": signal.entry_filter_reading,
            "entry_filter_reason": signal.entry_filter_reason,
            "last_price": signal.last_price,
            "trend": signal.trend,
            "momentum": signal.momentum,
            "volatility": signal.volatility,
            "rsi": signal.rsi,
            "short_average": signal.short_average,
            "long_average": signal.long_average,
            "mid_average": signal.mid_average,
            "ema_fast": signal.ema_fast,
            "ema_mid": signal.ema_mid,
            "ema_slow": signal.ema_slow,
            "atr": signal.atr,
            "support": signal.support,
            "resistance": signal.resistance,
            "swing_high": signal.swing_high,
            "swing_low": signal.swing_low,
            "forex_session": signal.forex_session,
            "forex_session_open": signal.forex_session_open,
            "timestamp_utc": signal.timestamp_utc,
            "timestamp_brt": signal.timestamp_brt,
            "weekday": signal.weekday,
        }

    def _execution_volume(
        self,
        signal: MT5DemoRobotSignal,
        trade_plan: MT5DemoTradePlan,
    ) -> float:
        """Aplica o lote contratual dos modelos com volume proprio."""
        operational_model = (
            signal.operational_model or trade_plan.operational_model or ""
        )
        if is_model25(operational_model):
            parameters = dict(trade_plan.stop_management_parameters or {})
            role = str(parameters.get("m25_entry_role") or "").upper()
            return (
                MODEL_25_REENTRY_VOLUME
                if role in {"REENTRY", "STRUCTURAL_REENTRY"}
                else MODEL_25_INITIAL_VOLUME
            )
        if is_model26(operational_model):
            return MODEL_26_VOLUME
        if not is_model24(operational_model):
            return float(self.volume)
        parameters = dict(trade_plan.stop_management_parameters or {})
        role = str(parameters.get("m24_entry_role") or "").upper()
        if role == "CONTINUATION":
            return MODEL_24_CONTINUATION_VOLUME
        if role in {"REENTRY", "STRUCTURAL_REENTRY"}:
            return MODEL_24_REENTRY_VOLUME
        return MODEL_24_INITIAL_VOLUME

    def _result(
        self,
        status: str,
        message: str,
        signal: MT5DemoRobotSignal,
        trade_plan: MT5DemoTradePlan | None,
    ) -> MT5DemoRobotResult:
        return MT5DemoRobotResult(
            status=status,
            message=message,
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            candle_time=signal.candle_time,
            decision=signal.decision,
            trade_plan=trade_plan,
        )

    def _market_key(self, symbol: str, timeframe: str) -> tuple[str, str]:
        return (str(symbol).upper(), str(timeframe).upper())

    def _execution_key(self, signal: MT5DemoRobotSignal) -> tuple[str, str, str]:
        return (
            str(signal.symbol).upper(),
            str(signal.timeframe).upper(),
            str(signal.operational_model or DEFAULT_OPERATIONAL_MODEL).upper(),
        )

    def _mark_candle_evaluated(
        self,
        key: tuple[str, str, str],
        candle_time: str,
        decision: str,
    ) -> None:
        self.last_candle_by_market[key] = candle_time
        self.last_decision_by_market[key] = decision

    def _is_terminal_rejection(self, message: str) -> bool:
        """Consome candle apenas para rejeicoes logicas, nao falhas transitorias."""
        normalized = str(message or "").lower()
        transient_markers = (
            "tick indisponivel",
            "preco executavel indisponivel",
            "mt5 retornou resposta vazia",
            "initialize() falhou",
            "autotrading disabled",
            "automated trading is disabled",
            "trading disabled by client",
            "client disabled autotrading",
            "simbolo",
            "nao pode ser selecionado",
        )
        return not any(marker in normalized for marker in transient_markers)
