"""Contrato canônico e versionado do setup operacional M24.

Este módulo é a fonte única para parâmetros estruturais e textos públicos do
M24. O executor, a interface e as guardas de documentação devem consumir este
contrato em vez de manter cópias independentes da regra.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class Model24SetupContract:
    version: str
    model_id: str
    runtime_source: str
    symbol: str
    timeframe: str
    raw_candles: int
    closed_candles: int
    sma_fast_period: int
    sma_slow_period: int
    rsi_period: int
    rsi_level: float
    atr_period: int
    distance_atr_min: float
    distance_atr_filter_enabled: bool
    pip_size: float
    initial_volume: float
    reentry_volume: float
    continuation_volume: float
    lateralization_volume: float
    lateralization_enabled: bool
    lateralization_risk_reward: float
    lateralization_target_source: str
    initial_requires_rsi_cross: bool
    initial_crosses_may_be_asynchronous: bool
    initial_requires_micro_pivot: bool
    initial_stop_source: str
    initial_trailing_source: str
    initial_individual_target: bool
    initial_target_source: str
    initial_target_fibonacci_projection: float
    initial_target_distance: float
    reentry_correction_lookback: int
    reentry_micro_pivot_maximum_age: int
    reentry_buy_rsi_min: float
    reentry_buy_rsi_max: float
    reentry_sell_rsi_min: float
    reentry_sell_rsi_max: float
    reentry_stop_source: str
    reentry_target_source: str
    reentry_target_required: bool
    continuation_enabled: bool
    continuation_requires_reentry_target_exit: bool
    continuation_buy_rsi_min: float
    continuation_sell_rsi_max: float
    continuation_stop_source: str
    continuation_individual_target: bool
    continuation_target_distance: float
    rsi50_exit_initial: bool
    initial_rsi50_exit_wait_closed_candles: int
    rsi50_exit_reentry: bool
    rsi50_exit_continuation: bool
    rsi_extreme_exit: bool
    sma20_sma50_exit: bool
    skip_first_reentry_after_extreme: bool
    basket_full_exit_usd: float
    max_open_initial: int
    max_open_reentry: int
    max_open_continuation: int

    def payload(self) -> dict[str, object]:
        return asdict(self)

    @property
    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.payload(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    @property
    def document_marker(self) -> str:
        return f"M24_CONTRACT={self.version}; SHA256={self.fingerprint}"


MODEL_24_SETUP = Model24SetupContract(
    version="M24_SETUP_V19_20260823",
    model_id="MODELO_24_XAU_RSI50_BASKET",
    runtime_source="M24_PROPRIO",
    symbol="XAUUSD",
    timeframe="M5",
    raw_candles=201,
    closed_candles=200,
    sma_fast_period=20,
    sma_slow_period=50,
    rsi_period=14,
    rsi_level=50.0,
    atr_period=14,
    distance_atr_min=0.25,
    distance_atr_filter_enabled=False,
    pip_size=0.01,
    initial_volume=0.10,
    reentry_volume=0.10,
    continuation_volume=0.10,
    lateralization_volume=0.10,
    lateralization_enabled=True,
    lateralization_risk_reward=3.0,
    lateralization_target_source=(
        "FAILED_FIBONACCI_REENTRY_THEN_PREVIOUS_FAVORABLE_MICRO_PIVOT_CLOSE"
    ),
    initial_requires_rsi_cross=True,
    initial_crosses_may_be_asynchronous=True,
    initial_requires_micro_pivot=False,
    initial_stop_source="PRICE_SMA20_CROSS_CANDLE_EXTREME_PLUS_1_PIP",
    initial_trailing_source=(
        "BREAK_PREVIOUS_MICRO_EXTREME_THEN_LATEST_OPPOSITE_PIVOT_1X1_PLUS_1_PIP_ONLY_FORWARD"
    ),
    initial_individual_target=True,
    initial_target_source=(
        "PREVIOUS_COMPLETED_STRUCTURAL_LEG_FIBONACCI_100_PROJECTED_FROM_ENTRY"
    ),
    initial_target_fibonacci_projection=1.0,
    initial_target_distance=0.0,
    reentry_correction_lookback=5,
    reentry_micro_pivot_maximum_age=5,
    reentry_buy_rsi_min=50.0,
    reentry_buy_rsi_max=70.0,
    reentry_sell_rsi_min=30.0,
    reentry_sell_rsi_max=50.0,
    reentry_stop_source="LATEST_MICRO_PIVOT_1X1_PLUS_1_PIP",
    reentry_target_source=(
        "PREVIOUS_COMPLETED_STRUCTURAL_LEG_FIBONACCI_100_PROJECTED_FROM_ENTRY"
    ),
    reentry_target_required=True,
    continuation_enabled=True,
    continuation_requires_reentry_target_exit=False,
    continuation_buy_rsi_min=70.0,
    continuation_sell_rsi_max=30.0,
    continuation_stop_source="PREVIOUS_CLOSED_CANDLE_EXTREME_TRAILING_ONLY_FORWARD",
    continuation_individual_target=False,
    continuation_target_distance=0.0,
    rsi50_exit_initial=True,
    initial_rsi50_exit_wait_closed_candles=2,
    rsi50_exit_reentry=True,
    rsi50_exit_continuation=False,
    rsi_extreme_exit=True,
    sma20_sma50_exit=False,
    skip_first_reentry_after_extreme=False,
    basket_full_exit_usd=1000.0,
    max_open_initial=1,
    max_open_reentry=1,
    max_open_continuation=1,
)

MODEL_24_SETUP_CONTRACT_VERSION = MODEL_24_SETUP.version
MODEL_24_SETUP_CONTRACT_FINGERPRINT = MODEL_24_SETUP.fingerprint


def model24_public_setup_fields() -> dict[str, str]:
    """Retorna os textos públicos derivados do contrato executável."""
    setup = MODEL_24_SETUP
    return {
        "Contrato": f"{setup.version} | {setup.fingerprint[:12]}",
        "Entrada inicial": (
            "preco cruza SMA20 e RSI14 cruza 50 na mesma direcao; os eventos "
            "podem ocorrer em M5 diferentes, mas ambos devem existir e "
            "permanecer validos"
        ),
        "Confirmacao inicial": (
            "ultimo M5 fechado confirma preco e RSI; o candle que cruzou a "
            "SMA20 fornece a extremidade do SL; |SMA20-SMA50| / ATR14 e "
            "apenas informativo e nao bloqueia"
        ),
        "SL inicial": (
            "BUY 1 pip abaixo da minima do candle que cruzou a SMA20; "
            "SELL 1 pip acima da maxima do candle que cruzou a SMA20; depois da entrada, "
            "BUY so move o SL abaixo do novo microfundo quando romper o topo "
            "anterior, e SELL faz o inverso ao romper o fundo anterior"
        ),
        "TP inicial": (
            "projecao Fibonacci de 100% da ultima perna estrutural completa "
            "na direcao da entrada, projetada a partir do preco de entrada; "
            "sem alvo fixo de 7,50"
        ),
        "Reentrada": (
            "retorno do preco a SMA20 e retomada: BUY rompe a maxima do ultimo "
            "M5 fechado, SELL rompe a minima; se o preco vivo ja ultrapassou o "
            "gatilho entra a mercado, caso contrario usa ordem Stop; sem "
            "descarte da primeira reentrada valida"
        ),
        "Ordem reentrada": (
            "BUY_STOP na maxima ou SELL_STOP na minima do ultimo M5 fechado; "
            "se o preco vivo ja rompeu o gatilho, entrada imediata a mercado"
        ),
        "SL reentrada": (
            "1 pip alem do micro-pivo 1+1 confirmado mais recente, com idade "
            "maxima de 5 M5; move somente a favor"
        ),
        "TP individual": (
            "INITIAL usa Fibonacci 100% da perna estrutural anterior; ao atingir "
            "RSI70 no BUY ou RSI30 no SELL, remove o TP e aguarda o retorno do "
            "RSI para Full Exit; reentrada usa Fibonacci 100% da perna "
            "estrutural anterior; CONTINUATION nao usa TP"
        ),
        "Continuacao": (
            "depois do aceite da INITIAL, arma uma unica ordem Stop por lado "
            "um pip alem do TP Fibonacci inicial para garantir que o alvo seja "
            "concluido primeiro; sem TP proprio, com SL no fundo/topo do ultimo "
            "M5 fechado e trailing pelo mesmo extremo a cada novo candle"
        ),
        "Lateralizacao": (
            "nao abre nova ordem: uma REENTRY ainda aberta que falhou o TP "
            "Fibonacci e retornou ao range reposiciona o TP no fechamento do "
            "microtopo anterior no BUY ou microfundo anterior no SELL; SL usa "
            "RR 3:1 e nunca afrouxa uma protecao existente"
        ),
        "Saida individual": (
            "INITIAL libera a inversao RSI50 somente depois de esperar 2 M5 "
            "fechados apos a entrada; REENTRY mantem sua regra RSI; "
            "CONTINUATION BUY faz Full Exit ao RSI14 atingir 70 e SELL ao "
            "atingir 30; nenhuma posicao "
            "sai por inversao SMA20/SMA50"
        ),
        "Volumes": (
            "INITIAL 0,10 | REENTRY 0,10 | CONTINUATION 0,10 | "
            "LATERALIZATION 0,10 apenas como classificacao; a rota reaproveita "
            "a REENTRY 0,10 aberta e nao adiciona volume"
        ),
        "Limite": (
            "por lado: maximo 1 INITIAL e 1 CONTINUATION; REENTRY e "
            "LATERALIZATION podem repetir em rodadas, mantendo apenas uma "
            "ordem/posicao de cada papel por vez"
        ),
        "Cesta": "somente M24; Full Exit liquido em +US$1.000",
    }
