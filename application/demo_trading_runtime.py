"""Runtime operacional controlado para execucao demo."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import fmean
from typing import Any, Protocol

from application.demo_execution_service import DemoExecutionService
from domain.candle import Candle
from domain.contracts.decision_context import DecisionContext
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal


class DemoRuntimeMarketDataProvider(Protocol):
    """Porta read-only usada pelo runtime para buscar candles."""

    def initialize_market_data(self) -> bool:
        """Conecta o terminal ou fonte externa."""

    def select_symbol(self, symbol: str) -> bool:
        """Seleciona o simbolo para leitura."""

    def get_candles(self, symbol: str, timeframe: Any, count: int) -> list[Candle]:
        """Retorna candles normalizados."""


class DemoRuntimeSignalProvider(Protocol):
    """Porta para estrategias que geram StrategySignal."""

    def generate_signal(
        self,
        candles: list[Candle],
        market_snapshot: MarketSnapshot,
        current_price: float,
    ) -> StrategySignal:
        """Gera sinal a partir de candles e snapshot."""


@dataclass(frozen=True)
class DemoTradingRuntimeConfig:
    """Configuracao operacional do runtime demo."""

    symbol: str = "WDO"
    timeframe: Any = "M1"
    candles_count: int = 120
    quantity: float = 0.1
    stop_points: float = 50.0
    target_points: float = 100.0
    minimum_score: int = 60
    minimum_confidence: float = 0.60
    enabled: bool = False


@dataclass(frozen=True)
class DemoTradingPlan:
    """Plano completo de entrada, stop, alvo e saida operacional."""

    symbol: str
    timeframe: str
    signal: StrategySignal
    entry_price: float | None
    stop: float | None
    target: float | None
    exit_rule: str
    order: ExecutionOrder | None


@dataclass(frozen=True)
class DemoTradingRuntimeResult:
    """Resultado de um ciclo do runtime demo."""

    status: str
    message: str
    market_snapshot: MarketSnapshot | None = None
    plan: DemoTradingPlan | None = None
    decision_context: DecisionContext | None = None
    execution_result: ExecutionResult | None = None


@dataclass
class MovingAverageDemoSignalProvider:
    """Gerador conservador de sinais para operacao demo."""

    short_window: int = 9
    long_window: int = 21

    def generate_signal(
        self,
        candles: list[Candle],
        market_snapshot: MarketSnapshot,
        current_price: float,
    ) -> StrategySignal:
        if len(candles) < self.long_window:
            return StrategySignal("WAIT", 0, 0.0, ["Amostra insuficiente para sinal demo"])

        closes = [float(candle.fechamento) for candle in candles]
        short_average = fmean(closes[-self.short_window :])
        long_average = fmean(closes[-self.long_window :])
        previous_close = closes[-2]
        momentum = current_price - previous_close
        distance = abs(short_average - long_average)
        normalized_distance = distance / max(abs(current_price), 1.0)
        confidence = min(0.95, 0.55 + normalized_distance * 100.0)
        score = int(round(confidence * 100))

        if short_average > long_average and momentum > 0:
            return StrategySignal(
                "BUY",
                score,
                confidence,
                [
                    "Media curta acima da media longa",
                    "Momentum positivo no candle atual",
                ],
            )
        if short_average < long_average and momentum < 0:
            return StrategySignal(
                "SELL",
                score,
                confidence,
                [
                    "Media curta abaixo da media longa",
                    "Momentum negativo no candle atual",
                ],
            )
        return StrategySignal(
            "WAIT",
            0,
            0.0,
            ["Medias e momentum sem alinhamento operacional"],
        )


@dataclass
class DemoTradingRuntime:
    """Executa um ciclo completo de sinal, risco, paper validation e ordem demo."""

    market_data_provider: DemoRuntimeMarketDataProvider
    execution_service: DemoExecutionService = field(default_factory=DemoExecutionService)
    signal_provider: DemoRuntimeSignalProvider = field(
        default_factory=MovingAverageDemoSignalProvider
    )
    config: DemoTradingRuntimeConfig = field(default_factory=DemoTradingRuntimeConfig)

    def run_once(self) -> DemoTradingRuntimeResult:
        """Executa um unico ciclo operacional demo."""
        if not self.config.enabled:
            return DemoTradingRuntimeResult(
                status="DISABLED",
                message="Runtime demo desativado. Nenhuma ordem sera enviada.",
            )

        connection_result = self._initialize_and_select_symbol()
        if connection_result is not None:
            return connection_result

        candles = self.market_data_provider.get_candles(
            self.config.symbol,
            self.config.timeframe,
            self.config.candles_count,
        )
        if not candles:
            return DemoTradingRuntimeResult(
                status="NO_MARKET_DATA",
                message="Nenhum candle retornado pelo provider de market data.",
            )

        snapshot = self._market_snapshot(candles)
        entry_price = float(candles[-1].fechamento)
        signal = self.signal_provider.generate_signal(candles, snapshot, entry_price)
        risk = self._risk_decision(signal)
        decision_context, order = self.execution_service.prepare_order(
            signal,
            snapshot,
            risk,
            entry_price,
            self.config.stop_points,
            self.config.target_points,
        )
        plan = self._plan(signal, entry_price, order)
        if order is None:
            return DemoTradingRuntimeResult(
                status="NO_ORDER",
                message="Sinal nao gerou ordem operacional.",
                market_snapshot=snapshot,
                plan=plan,
                decision_context=decision_context,
            )

        result = self.execution_service.submit_demo_order(
            decision_context,
            order,
            paper_validated=True,
        )
        return DemoTradingRuntimeResult(
            status=result.status,
            message=result.message,
            market_snapshot=snapshot,
            plan=plan,
            decision_context=decision_context,
            execution_result=result,
        )

    def _initialize_and_select_symbol(self) -> DemoTradingRuntimeResult | None:
        if not self.market_data_provider.initialize_market_data():
            return DemoTradingRuntimeResult(
                status="MARKET_DATA_DISCONNECTED",
                message="Provider de market data nao conectou.",
            )
        if not self.market_data_provider.select_symbol(self.config.symbol):
            return DemoTradingRuntimeResult(
                status="SYMBOL_UNAVAILABLE",
                message=f"Simbolo {self.config.symbol} indisponivel no provider.",
            )
        return None

    def _risk_decision(self, signal: StrategySignal) -> RiskDecision:
        if signal.decision not in {"BUY", "SELL"}:
            return RiskDecision(False, "Sinal sem decisao operacional.", 0, 0.0)
        if signal.score < self.config.minimum_score:
            return RiskDecision(False, "Score abaixo do minimo operacional.", 0, 0.0)
        if signal.confidence < self.config.minimum_confidence:
            return RiskDecision(False, "Confianca abaixo do minimo operacional.", 0, 0.0)
        return RiskDecision(True, "Risco aprovado pelo runtime demo.", self.config.quantity, 1.0)

    def _market_snapshot(self, candles: list[Candle]) -> MarketSnapshot:
        last = candles[-1]
        closes = [float(candle.fechamento) for candle in candles]
        recent = closes[-min(len(closes), 20) :]
        volatility = self._average_range(candles[-min(len(candles), 20) :])
        trend_strength = self._trend_strength(recent)
        return MarketSnapshot(
            symbol=self.config.symbol,
            datetime=str(last.data),
            regime=self._regime(trend_strength),
            volatility=volatility,
            liquidity=float(last.volume),
            trend_strength=trend_strength,
            market_dna_score=self._market_dna_score(trend_strength, volatility),
        )

    def _plan(
        self,
        signal: StrategySignal,
        entry_price: float,
        order: ExecutionOrder | None,
    ) -> DemoTradingPlan:
        return DemoTradingPlan(
            symbol=self.config.symbol,
            timeframe=str(self.config.timeframe),
            signal=signal,
            entry_price=entry_price if signal.decision in {"BUY", "SELL"} else None,
            stop=order.stop if order else None,
            target=order.target if order else None,
            exit_rule="Saida automatica por Stop Loss, Take Profit ou bloqueio de nova ordem.",
            order=order,
        )

    def _average_range(self, candles: list[Candle]) -> float:
        if not candles:
            return 0.0
        return float(fmean(float(candle.amplitude) for candle in candles))

    def _trend_strength(self, closes: list[float]) -> float:
        if len(closes) < 2:
            return 0.0
        movement = closes[-1] - closes[0]
        base = max(abs(closes[0]), 1.0)
        return float(movement / base)

    def _regime(self, trend_strength: float) -> str:
        if trend_strength > 0:
            return "TREND_UP"
        if trend_strength < 0:
            return "TREND_DOWN"
        return "RANGE"

    def _market_dna_score(self, trend_strength: float, volatility: float) -> float:
        score = 50.0 + trend_strength * 1000.0
        if volatility <= 0:
            score -= 10.0
        return max(0.0, min(100.0, score))
