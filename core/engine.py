"""Motor principal de decisao do TraderIA_WDO."""

from dataclasses import dataclass

from core.broker import SimulatedBroker
from core.configuration_manager import ConfigurationManager
from core.decision_pipeline import DecisionPipeline
from core.event_bus import EventBus
from core.events import DECISION_CREATED, ORDER_CREATED, STRATEGY_SIGNAL_CREATED
from core.order_manager import OrderManager
from core.position_manager import PositionManager
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision as RiskDecisionContract
from domain.market_state import MarketState
from domain.operacao import Operacao
from risk.risk_engine import RiskEngine
from risk.risk_engine import RiskDecision as EngineRiskDecision
from strategies.base import Strategy, StrategySignal


@dataclass
class TradingEngine:
    """Orquestra estrategia, risco, ordens e posicoes."""

    strategies: list[Strategy]
    risk_engine: RiskEngine
    order_manager: OrderManager
    broker: SimulatedBroker
    positions: PositionManager
    event_bus: EventBus
    decision_pipeline: DecisionPipeline

    def processar(self, estado: MarketState) -> Operacao | None:
        """Processa um estado de mercado e tenta abrir operacao."""
        signal = self._melhor_sinal(estado)
        risk = self.risk_engine.avaliar(signal)
        context = self.decision_pipeline.processar(
            signal,
            self._criar_snapshot(estado),
            self._criar_risk_contract(risk),
        )

        self.event_bus.publish(STRATEGY_SIGNAL_CREATED, signal)
        self.event_bus.publish(DECISION_CREATED, context)

        if not context.approved or self.positions.tem_posicao():
            return None

        operacao = self.order_manager.criar_operacao(context.strategy_signal, estado)
        return self._executar(operacao)

    def _melhor_sinal(self, estado: MarketState) -> StrategySignal:
        sinais = [strategy.analisar(estado) for strategy in self.strategies]
        return max(sinais, key=lambda signal: signal.score)

    def _executar(self, operacao: Operacao | None) -> Operacao | None:
        if operacao is None:
            return None

        executada = self.broker.enviar_ordem(operacao)
        self.positions.abrir(executada)
        self.event_bus.publish(ORDER_CREATED, executada)
        return executada

    def _criar_snapshot(self, estado: MarketState) -> MarketSnapshot:
        return MarketSnapshot(
            symbol=ConfigurationManager.get_configuration().symbol,
            datetime=estado.candle.data,
            regime=estado.direcao,
            volatility=estado.atr,
            liquidity=float(estado.candle.volume),
            trend_strength=estado.posicao_no_dia,
            market_dna_score=0.0,
        )

    def _criar_risk_contract(
        self,
        risk: EngineRiskDecision,
    ) -> RiskDecisionContract:
        return RiskDecisionContract(
            allowed=risk.aprovado,
            reason=risk.motivo,
            max_contracts=1 if risk.aprovado else 0,
            risk_multiplier=1.0 if risk.aprovado else 0.0,
        )
