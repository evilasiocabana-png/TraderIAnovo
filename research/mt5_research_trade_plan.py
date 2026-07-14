"""Plano read-only de entrada, stop e alvo produzido pelo Research Lab MT5."""

from __future__ import annotations

from dataclasses import dataclass, field


SUPPORTED_STOP_MANAGEMENT_POLICIES = frozenset(
    (
        "DYNAMIC_POSITION_MANAGER",
        "FIXED_STOP",
        "ATR_TRAILING_STOP",
        "BREAK_EVEN",
        "CHANDELIER_EXIT",
        "PARABOLIC_SAR",
        "DONCHIAN_CHANNEL_STOP",
        "MOVING_AVERAGE_EXIT",
        "TIME_STOP",
        "VOLATILITY_STOP",
    )
)

DEFAULT_BETA_ID = "BETA001"
DEFAULT_BETA_VERSION = "BETA v1"

STOP_MANAGEMENT_PARAMETER_KEYS = {
    "DYNAMIC_POSITION_MANAGER": (
        "atr_trailing_factor",
        "atr_trailing_activation_rr",
        "break_even_trigger_rr",
        "break_even_offset_pips",
        "volatility_stop_factor",
        "chandelier_period",
        "chandelier_atr_factor",
        "donchian_stop_period",
        "exit_ma_period",
        "exit_ma_type",
        "max_bars_in_trade",
        "max_minutes_in_trade",
        "volatility_window",
        "volatility_multiplier",
    ),
    "FIXED_STOP": (),
    "ATR_TRAILING_STOP": ("atr_trailing_factor", "atr_trailing_activation_rr"),
    "BREAK_EVEN": ("break_even_trigger_rr", "break_even_offset_pips"),
    "CHANDELIER_EXIT": ("chandelier_period", "chandelier_atr_factor"),
    "PARABOLIC_SAR": ("sar_step", "sar_max_step"),
    "DONCHIAN_CHANNEL_STOP": ("donchian_stop_period",),
    "MOVING_AVERAGE_EXIT": ("exit_ma_period", "exit_ma_type"),
    "TIME_STOP": ("max_bars_in_trade", "max_minutes_in_trade"),
    "VOLATILITY_STOP": ("volatility_window", "volatility_multiplier"),
}


@dataclass(frozen=True)
class MT5ResearchTradePlanConfiguration:
    """Parametros explicitos do plano de trade MT5 de pesquisa."""

    exit_candidates: tuple[tuple[float, float], ...] = (
        (1.5, 1.5),
        (2.0, 2.0),
        (2.5, 2.0),
        (2.0, 3.0),
    )
    minimum_distance_percent: float = 0.001
    minimum_risk_reward: float = 1.5
    default_stop_multiplier: float = 2.0
    default_risk_reward: float = 2.0


@dataclass(frozen=True)
class MT5ResearchTradePlanInput:
    """Entrada do plano baseada no sinal teorico ja calculado."""

    symbol: str
    timeframe: str
    decision: str
    entry_signal_status: str
    entry_price: float | None
    atr: float | None
    active_model: str
    reason: str
    atr_stop_factor: float | None = None
    research_risk_reward: float | None = None
    stop_management: str = "DYNAMIC_POSITION_MANAGER"
    stop_management_parameters: dict[str, str] = field(default_factory=dict)
    alpha_id: str = "ALPHA001"
    alpha_version: str = "v1"
    beta_id: str = DEFAULT_BETA_ID
    beta_version: str = DEFAULT_BETA_VERSION
    beta_mode: str = "PROTECT_ONLY"
    certification_demo_allowed: bool = True
    certification_score: float = 100.0
    certification_grade: str = "A+"
    certification_status: str = "CERTIFICADA_A_PLUS"
    certification_usage: str = "Operacao automatica Demo liberada."
    certification_rejection_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class MT5ResearchTradePlan:
    """Plano de trade institucional, sem execucao operacional."""

    symbol: str
    timeframe: str
    direction: str
    entry_price: float | None
    stop: float | None
    target: float | None
    risk_reward: float
    stop_multiplier: float
    exit_model: str
    exit_score: float
    exit_candidates: int
    status: str
    risk_pips: float = 0.0
    reward_pips: float = 0.0
    risk_percent: float = 0.0
    reward_percent: float = 0.0
    stop_reason: str = ""
    target_reason: str = ""
    stop_management: str = "FIXED_STOP"
    stop_management_parameters: dict[str, str] = field(default_factory=dict)
    stop_management_reason: str = "Saida dinamica decidida pelo Position Manager."
    alpha_id: str = "ALPHA001"
    alpha_version: str = "v1"
    beta_id: str = DEFAULT_BETA_ID
    beta_version: str = DEFAULT_BETA_VERSION
    beta_mode: str = "PROTECT_ONLY"
    beta_reason: str = "Position Manager administra a saida apos a entrada."
    source: str = "RESEARCH_LAB"
    reason: str = ""
    invalid_reason: str = ""
    invalid_fields: tuple[str, ...] = ()
    next_retry: str = ""
    expected_trigger: str = ""
    rr_current: float = 0.0
    rr_minimum: float = 1.5
    diagnostics: tuple[str, ...] = ()
    certification_score: float = 0.0
    certification_grade: str = "E"
    certification_status: str = "REJEITADA"
    certification_usage: str = "Rejeitada."
    certification_demo_allowed: bool = False
    certification_rejection_reasons: tuple[str, ...] = ()


class MT5ResearchTradePlanEngine:
    """Deriva stop/alvo do Research Lab sem acessar Broker ou MT5."""

    def __init__(
        self,
        configuration: MT5ResearchTradePlanConfiguration | None = None,
    ) -> None:
        self.configuration = configuration or MT5ResearchTradePlanConfiguration()

    def build_plan(
        self,
        payload: MT5ResearchTradePlanInput,
    ) -> MT5ResearchTradePlan:
        """Cria plano apenas quando existe entrada teorica BUY/SELL valida."""
        direction = str(payload.decision or "WAIT").upper()
        if payload.entry_signal_status != "SINAL_TEORICO":
            return self._empty_plan(
                payload,
                "SEM_GATILHO_VALIDO",
                "Research Lab nao recebeu entrada teorica autorizada por regime.",
                invalid_reason="NO_THEORETICAL_TRIGGER",
                invalid_fields=(
                    "entry_signal_status",
                    "entry_price",
                    "stop",
                    "target",
                    "risk_reward",
                ),
                next_retry="Aguardar regime de mercado autorizar BUY ou SELL.",
                expected_trigger="Regime de mercado deve autorizar BUY ou SELL.",
            )
        if direction not in {"BUY", "SELL"}:
            return self._empty_plan(
                payload,
                "SEM_DIRECAO_EXECUTAVEL",
                "Decisao atual nao e BUY/SELL.",
                invalid_reason="NO_EXECUTABLE_DIRECTION",
                invalid_fields=("decision", "stop", "target", "risk_reward"),
                next_retry="Aguardar decisao BUY ou SELL do modelo ativo.",
                expected_trigger="Modelo ativo deve produzir BUY ou SELL.",
            )
        if payload.entry_price is None or float(payload.entry_price) <= 0:
            return self._empty_plan(
                payload,
                "ENTRADA_INVALIDA",
                "Preco teorico de entrada ausente ou invalido.",
                invalid_reason="INVALID_ENTRY_PRICE",
                invalid_fields=("entry_price", "stop", "target", "risk_reward"),
                next_retry="Aguardar candle de gatilho com preco teorico valido.",
                expected_trigger="Entrada teorica positiva no candle de sinal.",
            )
        entry = float(payload.entry_price)
        stop_multiplier, risk_reward, exit_score = self._initial_risk_parameters(
            payload,
        )
        if risk_reward < self.configuration.minimum_risk_reward:
            return self._empty_plan(
                payload,
                "RR_INSUFICIENTE",
                "Research Lab rejeitou plano por RR abaixo do minimo.",
                invalid_reason="LOW_RISK_REWARD",
                invalid_fields=("risk_reward", "target"),
                next_retry="Aguardar novo candle com relacao risco/retorno melhor.",
                expected_trigger=(
                    f"RR >= {self.configuration.minimum_risk_reward:.2f}."
                ),
                rr_current=risk_reward,
            )
        distance = self._stop_distance(entry, payload.atr, stop_multiplier)
        target_distance = distance * risk_reward
        if direction == "BUY":
            stop = entry - distance
            target = entry + target_distance
        else:
            stop = entry + distance
            target = entry - target_distance
        risk_pips = self._pips(payload.symbol, abs(entry - stop))
        reward_pips = self._pips(payload.symbol, abs(target - entry))
        risk_percent = self._percent_distance(entry, stop)
        reward_percent = self._percent_distance(entry, target)
        stop_management = self._normalize_stop_management(payload.stop_management)
        stop_management_parameters = self._stop_management_parameters(
            stop_management,
            payload.stop_management_parameters,
        )
        stop_management_reason = (
            f"Hint legado {stop_management} preservado por compatibilidade. "
            "Entrada aprovada por plano inicial de risco. A saida nao e escolhida "
            "na aprovacao do trade; o Position Manager decidira dinamicamente "
            "apos existir posicao aberta."
        )
        beta_id = self._normalize_beta_id(payload.beta_id)
        beta_version = str(payload.beta_version or DEFAULT_BETA_VERSION)
        beta_mode = self._normalize_beta_mode(payload.beta_mode)
        beta_reason = (
            f"Beta {beta_id}: gestao pos-entrada executada pelo Position Manager. "
            "O Lab define entrada, stop inicial e alvo; o Beta protege/gerencia "
            "somente depois de existir posicao aberta."
        )
        stop_reason = (
            f"Stop definido por {stop_multiplier:.2f}x ATR com distancia minima "
            "institucional."
        )
        target_reason = (
            f"Alvo definido por RR {risk_reward:.2f} sobre o risco calculado."
        )

        return MT5ResearchTradePlan(
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            direction=direction,
            entry_price=entry,
            stop=stop,
            target=target,
            risk_reward=risk_reward,
            stop_multiplier=stop_multiplier,
            exit_model="INITIAL_RISK_PLAN",
            exit_score=exit_score,
            exit_candidates=0,
            risk_pips=risk_pips,
            reward_pips=reward_pips,
            risk_percent=risk_percent,
            reward_percent=reward_percent,
            stop_reason=stop_reason,
            target_reason=target_reason,
            stop_management=stop_management,
            stop_management_parameters=stop_management_parameters,
            stop_management_reason=stop_management_reason,
            alpha_id=str(payload.alpha_id or "ALPHA001"),
            alpha_version=str(payload.alpha_version or "v1"),
            beta_id=beta_id,
            beta_version=beta_version,
            beta_mode=beta_mode,
            beta_reason=beta_reason,
            status="PLANO_VALIDO",
            reason=(
                f"{payload.active_model}: entrada aprovada com stop inicial "
                f"{stop_multiplier:.2f}x ATR e RR inicial {risk_reward:.2f}. "
                f"{payload.reason}"
            ),
            next_retry="Plano pronto para avaliacao do robo demo temporal.",
            expected_trigger="Conta demo habilitada, sem posicao aberta no simbolo.",
            rr_current=risk_reward,
            rr_minimum=self.configuration.minimum_risk_reward,
            diagnostics=(
                "Entrada teorica valida.",
                (
                    f"ICT informativo {payload.certification_score:.2f} "
                    f"({payload.certification_grade}); nao bloqueia operacao Demo."
                ),
                f"Stop calculado com {stop_multiplier:.2f}x ATR/distancia minima.",
                f"RR inicial {risk_reward:.2f}.",
                "Saida dinamica sera decidida pelo Position Manager em tempo de posicao.",
                beta_reason,
                f"Risco {risk_pips:.1f} pips ({risk_percent:.4f}%).",
                f"Ganho potencial {reward_pips:.1f} pips ({reward_percent:.4f}%).",
            ),
            certification_score=payload.certification_score,
            certification_grade=payload.certification_grade,
            certification_status=payload.certification_status,
            certification_usage=payload.certification_usage,
            certification_demo_allowed=payload.certification_demo_allowed,
            certification_rejection_reasons=payload.certification_rejection_reasons,
        )

    def _initial_risk_parameters(
        self,
        payload: MT5ResearchTradePlanInput,
    ) -> tuple[float, float, float]:
        """Define risco inicial sem escolher uma saida operacional."""
        lab_stop_multiplier = self._positive_float(payload.atr_stop_factor)
        lab_risk_reward = self._positive_float(payload.research_risk_reward)
        if lab_stop_multiplier is not None and lab_risk_reward is not None:
            return lab_stop_multiplier, lab_risk_reward, 0.0
        return (
            self.configuration.default_stop_multiplier,
            self.configuration.default_risk_reward,
            0.0,
        )

    def _exit_candidate_count(self, payload: MT5ResearchTradePlanInput) -> int:
        if (
            self._positive_float(payload.atr_stop_factor) is not None
            and self._positive_float(payload.research_risk_reward) is not None
        ):
            return 1
        return 0

    def _positive_float(self, value: float | None) -> float | None:
        if value is None:
            return None
        parsed = float(value)
        if parsed <= 0.0:
            return None
        return parsed

    def _normalize_stop_management(self, value: str | None) -> str:
        normalized = str(value or "DYNAMIC_POSITION_MANAGER").strip().upper()
        if normalized in SUPPORTED_STOP_MANAGEMENT_POLICIES:
            return normalized
        return "DYNAMIC_POSITION_MANAGER"

    def _normalize_beta_id(self, value: str | None) -> str:
        normalized = str(value or DEFAULT_BETA_ID).strip().upper()
        if normalized == "LEGACY_CURRENT_EXIT":
            return DEFAULT_BETA_ID
        return normalized or DEFAULT_BETA_ID

    def _normalize_beta_mode(self, value: str | None) -> str:
        normalized = str(value or "PROTECT_ONLY").strip().upper()
        if normalized in {"ADAPTIVE_FULL_EXIT", "FULL_EXIT_ADAPTATIVO"}:
            return "ADAPTIVE_FULL_EXIT"
        if normalized in {"PROTECT_ONLY", "PROTEGER_SOMENTE"}:
            return "PROTECT_ONLY"
        return normalized or "PROTECT_ONLY"

    def _stop_management_parameters(
        self,
        policy: str,
        parameters: dict[str, str] | None,
    ) -> dict[str, str]:
        raw_parameters = parameters or {}
        allowed_keys = STOP_MANAGEMENT_PARAMETER_KEYS.get(policy, ())
        return {
            key: str(raw_parameters[key])
            for key in allowed_keys
            if key in raw_parameters and str(raw_parameters[key]).strip()
        }

    def _exit_candidate_score(
        self,
        stop_multiplier: float,
        risk_reward: float,
        atr: float,
    ) -> float:
        atr_bonus = 10.0 if atr > 0 else 0.0
        conservative_stop = 20.0 - abs(stop_multiplier - 2.0) * 8.0
        balanced_rr = 30.0 - abs(risk_reward - 2.0) * 6.0
        payoff = min(risk_reward * 12.0, 36.0)
        return max(0.0, atr_bonus + conservative_stop + balanced_rr + payoff)

    def _stop_distance(
        self,
        entry: float,
        atr: float | None,
        stop_multiplier: float,
    ) -> float:
        atr_value = max(float(atr or 0.0), 0.0)
        atr_distance = atr_value * stop_multiplier
        minimum_distance = abs(entry) * self.configuration.minimum_distance_percent
        return max(atr_distance, minimum_distance)

    def _pips(self, symbol: str, distance: float) -> float:
        pip_size = 0.01 if str(symbol).upper().endswith("JPY") else 0.0001
        if pip_size <= 0.0:
            return 0.0
        return distance / pip_size

    def _percent_distance(self, entry: float, price: float | None) -> float:
        if price is None or entry == 0.0:
            return 0.0
        return abs(float(price) - entry) / abs(entry) * 100.0

    def _empty_plan(
        self,
        payload: MT5ResearchTradePlanInput,
        status: str,
        reason: str,
        invalid_reason: str,
        invalid_fields: tuple[str, ...],
        next_retry: str,
        expected_trigger: str,
        rr_current: float = 0.0,
    ) -> MT5ResearchTradePlan:
        return MT5ResearchTradePlan(
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            direction=str(payload.decision or "WAIT").upper(),
            entry_price=payload.entry_price,
            stop=None,
            target=None,
            risk_reward=0.0,
            stop_multiplier=0.0,
            exit_model="NONE",
            exit_score=0.0,
            exit_candidates=len(self.configuration.exit_candidates),
            risk_pips=0.0,
            reward_pips=0.0,
            risk_percent=0.0,
            reward_percent=0.0,
            stop_reason="Stop ausente porque o plano nao esta valido.",
            target_reason="Alvo ausente porque o plano nao esta valido.",
            stop_management=self._normalize_stop_management(payload.stop_management),
            stop_management_parameters=self._stop_management_parameters(
                self._normalize_stop_management(payload.stop_management),
                payload.stop_management_parameters,
            ),
            stop_management_reason=(
                "Saida dinamica registrada, mas sem aplicacao porque o plano nao esta valido."
            ),
            alpha_id=str(payload.alpha_id or "ALPHA001"),
            alpha_version=str(payload.alpha_version or "v1"),
            beta_id=self._normalize_beta_id(payload.beta_id),
            beta_version=str(payload.beta_version or DEFAULT_BETA_VERSION),
            beta_mode=self._normalize_beta_mode(payload.beta_mode),
            beta_reason=(
                "Beta registrado por compatibilidade; sem execucao porque o plano "
                "nao esta valido."
            ),
            status=status,
            reason=reason,
            invalid_reason=invalid_reason,
            invalid_fields=invalid_fields,
            next_retry=next_retry,
            expected_trigger=expected_trigger,
            rr_current=rr_current,
            rr_minimum=self.configuration.minimum_risk_reward,
            diagnostics=(
                f"Status: {status}.",
                f"Motivo: {invalid_reason}.",
                f"Proxima tentativa: {next_retry}",
                f"ICT: {payload.certification_score:.2f} ({payload.certification_grade}).",
            ),
            certification_score=payload.certification_score,
            certification_grade=payload.certification_grade,
            certification_status=payload.certification_status,
            certification_usage=payload.certification_usage,
            certification_demo_allowed=payload.certification_demo_allowed,
            certification_rejection_reasons=payload.certification_rejection_reasons,
        )
