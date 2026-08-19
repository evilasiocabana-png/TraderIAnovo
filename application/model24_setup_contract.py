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
    pip_size: float
    initial_volume: float
    reentry_volume: float
    continuation_volume: float
    initial_requires_rsi_cross: bool
    initial_crosses_may_be_asynchronous: bool
    initial_requires_micro_pivot: bool
    initial_stop_source: str
    initial_trailing_source: str
    initial_individual_target: bool
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
    version="M24_SETUP_V5_20260819",
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
    pip_size=0.01,
    initial_volume=0.30,
    reentry_volume=0.20,
    continuation_volume=0.40,
    initial_requires_rsi_cross=True,
    initial_crosses_may_be_asynchronous=True,
    initial_requires_micro_pivot=False,
    initial_stop_source="PREVIOUS_CLOSED_CANDLE_EXTREME_PLUS_1_PIP",
    initial_trailing_source="SMA20_AFTER_TWO_FAVORABLE_CLOSES",
    initial_individual_target=True,
    initial_target_distance=0.25,
    reentry_correction_lookback=5,
    reentry_micro_pivot_maximum_age=5,
    reentry_buy_rsi_min=50.0,
    reentry_buy_rsi_max=70.0,
    reentry_sell_rsi_min=30.0,
    reentry_sell_rsi_max=50.0,
    reentry_stop_source="LATEST_MICRO_PIVOT_1X1_PLUS_1_PIP",
    reentry_target_source="LATEST_PROFITABLE_MICRO_PIVOT_1X1_CLOSE",
    reentry_target_required=True,
    continuation_enabled=True,
    continuation_requires_reentry_target_exit=True,
    continuation_buy_rsi_min=70.0,
    continuation_sell_rsi_max=30.0,
    continuation_stop_source="PREVIOUS_CLOSED_CANDLE_EXTREME_PLUS_1_PIP",
    continuation_individual_target=True,
    continuation_target_distance=0.13,
    rsi50_exit_initial=True,
    rsi50_exit_reentry=True,
    rsi50_exit_continuation=True,
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
            "ultimo M5 fechado + |SMA20-SMA50| / ATR14 >= 0,25"
        ),
        "SL inicial": (
            "1 pip alem do extremo do M5 fechado imediatamente anterior a "
            "entrada; apos dois "
            "fechamentos favoraveis, SMA20 move o SL somente a favor"
        ),
        "TP inicial": "0,25 no preco a partir da entrada",
        "Reentrada": (
            "correcao nos ultimos 5 M5 + preco alem da SMA20 + RSI14 em "
            "50/70 BUY ou 30/50 SELL"
        ),
        "Ordem reentrada": (
            "BUY_STOP na maxima ou SELL_STOP na minima do ultimo M5 fechado"
        ),
        "SL reentrada": (
            "1 pip alem do micro-pivo 1+1 confirmado mais recente, com idade "
            "maxima de 5 M5; move somente a favor"
        ),
        "TP individual": (
            "INITIAL usa distancia fixa de 0,25; reentrada exige o fechamento "
            "lucrativo do microtopo/microfundo 1+1 mais recente; "
            "CONTINUATION usa distancia fixa de 0,13"
        ),
        "Continuacao": (
            "apos a REENTRY zerar no TP confirmado: BUY a mercado se o preco "
            "continuar acima do alvo e RSI14>70, SELL espelhado com RSI14<30; "
            "SL 1 pip alem do extremo do M5 fechado anterior"
        ),
        "Saida individual": (
            "INITIAL, REENTRY e CONTINUATION saem na inversao RSI50 ou no "
            "retorno RSI 70/30; nenhuma sai por inversao SMA20/SMA50"
        ),
        "Volumes": "INITIAL 0,30 | REENTRY 0,20 | CONTINUATION 0,40",
        "Limite": (
            "maximo 1 INITIAL, 1 REENTRY e 1 CONTINUATION; sem descarte da "
            "primeira reentrada apos saida RSI 70/30"
        ),
        "Cesta": "somente M24; Full Exit liquido em +US$1.000",
    }
