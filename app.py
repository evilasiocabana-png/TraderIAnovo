"""Ponto de entrada da aplicacao TraderIA_WDO."""

from analytics.dashboard import DashboardBuilder
from core.broker import SimulatedBroker
from core.configuration_manager import ConfigurationManager, SystemConfiguration
from core.decision_pipeline import DecisionPipeline
from core.engine import TradingEngine
from core.event_bus import EventBus
from core.event_logger import EventLogger
from core.events import (
    DECISION_CREATED,
    MARKET_DNA_UPDATED,
    ORDER_CREATED,
    STRATEGY_SIGNAL_CREATED,
    SYSTEM_STARTED,
)
from core.order_manager import OrderManager
from core.position_manager import PositionManager
from database.sqlite import SQLiteOperacaoRepository
from domain.candle import Candle
from domain.market_state import MarketState
from market.market_dna import MarketDNA
from risk.risk_engine import RiskEngine
from strategies.breakout import BreakoutStrategy
from strategies.pullback import PullbackStrategy
from strategies.score_contexto import ScoreContextoStrategy
from strategies.smart_money import SmartMoneyStrategy


def criar_estado_demo() -> MarketState:
    """Cria um estado de mercado demonstrativo."""
    candle = Candle("2026-06-25 09:23", 5500, 5530, 5480, 5522, 1500)
    return MarketState(candle, vwap=5516, atr=51, pullback_pontos=13, horario=9)


def criar_engine(
    configuration: SystemConfiguration,
    event_bus: EventBus | None = None,
) -> TradingEngine:
    """Monta o motor com suas dependencias."""
    bus = event_bus or EventBus()
    return TradingEngine(
        strategies=[
            ScoreContextoStrategy(),
            BreakoutStrategy(),
            PullbackStrategy(),
            SmartMoneyStrategy(),
        ],
        risk_engine=RiskEngine(
            configuration.max_daily_loss,
            configuration.max_daily_operations,
            configuration.minimum_score,
        ),
        order_manager=OrderManager(
            configuration.stop_points,
            configuration.target_points,
        ),
        broker=SimulatedBroker(),
        positions=PositionManager(),
        event_bus=bus,
        decision_pipeline=DecisionPipeline(),
    )


def inscrever_logger(event_bus: EventBus, logger: EventLogger) -> None:
    """Inscreve logger nos eventos principais."""
    for event_name in _eventos_principais():
        event_bus.subscribe(
            event_name,
            lambda payload, name=event_name: logger.handle_event(name, payload),
        )


def _eventos_principais() -> tuple[str, ...]:
    return (
        SYSTEM_STARTED,
        MARKET_DNA_UPDATED,
        STRATEGY_SIGNAL_CREATED,
        DECISION_CREATED,
        ORDER_CREATED,
    )


def main() -> None:
    """Executa uma demonstracao ponta a ponta."""
    configuration = ConfigurationManager.get_configuration()
    event_bus = EventBus()
    event_logger = EventLogger()
    inscrever_logger(event_bus, event_logger)
    event_bus.publish(SYSTEM_STARTED, {"ativo": configuration.symbol})

    estado = criar_estado_demo()
    engine = criar_engine(configuration, event_bus)
    operacao = engine.processar(estado)

    dna = MarketDNA()
    pattern = dna.criar_pattern(estado)
    similares = dna.comparar(pattern)
    caminho_dna = dna.salvar(pattern)
    event_bus.publish(MARKET_DNA_UPDATED, pattern)
    caminho_dashboard = DashboardBuilder().gerar(dna.carregar())

    if operacao is not None:
        SQLiteOperacaoRepository().salvar(operacao)

    print(f"Ativo: {configuration.symbol}")
    print(f"Operacao: {operacao}")
    print(f"Padroes similares: {len(similares)}")
    print(f"MARKET DNA salvo em: {caminho_dna.resolve()}")
    print(f"Dashboard salvo em: {caminho_dashboard.resolve()}")
    print(f"Eventos registrados: {len(event_logger.get_events())}")


if __name__ == "__main__":
    main()
