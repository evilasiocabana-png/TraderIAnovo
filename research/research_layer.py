"""Camadas oficiais de conhecimento do Research Lab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResearchLayer(Enum):
    """Ordem institucional das camadas de pesquisa quantitativa."""

    MARKET_DATA = "MARKET_DATA"
    INDICATORS = "INDICATORS"
    CONTEXT = "CONTEXT"
    STRUCTURE = "STRUCTURE"
    TIME = "TIME"
    MICROSTRUCTURE = "MICROSTRUCTURE"
    ALPHA = "ALPHA"
    TRADE_PLAN = "TRADE_PLAN"
    VALIDATION = "VALIDATION"


@dataclass(frozen=True)
class ResearchLayerDefinition:
    """Definicao declarativa de uma camada do Research Lab."""

    layer: ResearchLayer
    index: int
    title: str
    question: str
    responsibility: str


OFFICIAL_RESEARCH_LAYERS: tuple[ResearchLayerDefinition, ...] = (
    ResearchLayerDefinition(
        layer=ResearchLayer.MARKET_DATA,
        index=0,
        title="Market Data",
        question="Quais dados estao disponiveis?",
        responsibility="Fornecer candles, bid, ask, tick, spread, volume e timeframe.",
    ),
    ResearchLayerDefinition(
        layer=ResearchLayer.INDICATORS,
        index=1,
        title="Indicadores",
        question="Quais numeros descrevem o mercado?",
        responsibility="Calcular EMA, RSI, ATR, Momentum, ADX, Donchian e indicadores derivados.",
    ),
    ResearchLayerDefinition(
        layer=ResearchLayer.CONTEXT,
        index=2,
        title="Contexto",
        question="Como esta o mercado?",
        responsibility="Classificar tendencia, range, volatilidade, momentum, distancia de medias e RSI extremo.",
    ),
    ResearchLayerDefinition(
        layer=ResearchLayer.STRUCTURE,
        index=3,
        title="Estrutura",
        question="Onde o preco esta?",
        responsibility="Mapear suporte, resistencia, pivots, swings, ranges, rompimentos e distancias estruturais.",
    ),
    ResearchLayerDefinition(
        layer=ResearchLayer.TIME,
        index=4,
        title="Tempo",
        question="Quando essa Alpha funciona?",
        responsibility="Separar sessoes, horarios, janelas operacionais, dias e periodos antes da validacao.",
    ),
    ResearchLayerDefinition(
        layer=ResearchLayer.MICROSTRUCTURE,
        index=5,
        title="Microestrutura",
        question="Vale a pena entrar agora?",
        responsibility="Avaliar spread, tick volume, slippage estimado, velocidade do preco e liquidez por sessao.",
    ),
    ResearchLayerDefinition(
        layer=ResearchLayer.ALPHA,
        index=6,
        title="Alpha",
        question="Qual hipotese estou testando?",
        responsibility="Selecionar a hipotese formal, mercados permitidos, parametros pesquisaveis e criterios de rejeicao.",
    ),
    ResearchLayerDefinition(
        layer=ResearchLayer.TRADE_PLAN,
        index=7,
        title="Trade Plan",
        question="Como operar?",
        responsibility="Definir entrada, stop, alvo, risco, ganho, RR, motivo do stop, motivo do alvo e modelo de saida.",
    ),
    ResearchLayerDefinition(
        layer=ResearchLayer.VALIDATION,
        index=8,
        title="Validacao",
        question="Essa hipotese merece ser certificada?",
        responsibility="Medir trades, win rate, profit factor, expectancy, drawdown, MAE, MFE e robustez.",
    ),
)


OFFICIAL_RESEARCH_LAYER_ORDER: tuple[ResearchLayer, ...] = tuple(
    definition.layer for definition in OFFICIAL_RESEARCH_LAYERS
)
