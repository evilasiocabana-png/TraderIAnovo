"""Valida conexao real MT5 Pepperstone em modo somente leitura."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from domain.candle import Candle
from infrastructure.market_data.mt5_market_data_provider import MT5MarketDataProvider


DEFAULT_SYMBOL = "EURUSD"
DEFAULT_TIMEFRAME = "H1"
DEFAULT_CANDLE_COUNT = 10
MINIMUM_CANDLES = 5


def main() -> int:
    """Executa validacao manual read-only contra o terminal MT5."""
    try:
        import MetaTrader5 as mt5
    except ModuleNotFoundError:
        print(
            "ERRO: biblioteca MetaTrader5 nao instalada. "
            "Instale as dependencias antes da validacao."
        )
        return 1

    symbol = os.getenv("MT5_SYMBOL", DEFAULT_SYMBOL).strip() or DEFAULT_SYMBOL
    timeframe_name = os.getenv("MT5_TIMEFRAME", DEFAULT_TIMEFRAME).strip().upper()
    candle_count = _candle_count()

    missing_credentials = [
        name
        for name in ("MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER")
        if not os.getenv(name)
    ]
    if missing_credentials:
        print(
            "ERRO: credenciais ausentes nas variaveis de ambiente: "
            + ", ".join(missing_credentials)
        )
        return 1

    provider = MT5MarketDataProvider(
        mt5_module=mt5,
        login=os.getenv("MT5_LOGIN"),
        password=os.getenv("MT5_PASSWORD"),
        server=os.getenv("MT5_SERVER"),
        terminal_path=os.getenv(
            "MT5_PATH",
            r"C:\Program Files\MetaTrader 5\terminal64.exe",
        ),
    )

    try:
        if not provider.connect():
            print(
                "ERRO: nao foi possivel conectar ao MT5. "
                "Verifique se o terminal esta aberto, logado e se as "
                "credenciais Pepperstone estao corretas."
            )
            _print_last_error(mt5)
            return 1

        if not provider.select_symbol(symbol):
            print(
                f"ERRO: simbolo '{symbol}' nao encontrado ou indisponivel no MT5."
            )
            _print_last_error(mt5)
            return 1

        timeframe = _timeframe(mt5, timeframe_name)
        if timeframe is None:
            print(f"ERRO: timeframe MT5 invalido: {timeframe_name}")
            return 1

        candles = provider.get_candles(symbol, timeframe, candle_count)
        if len(candles) < MINIMUM_CANDLES:
            print(
                "ERRO: quantidade insuficiente de candles retornados. "
                f"Esperado >= {MINIMUM_CANDLES}; recebido {len(candles)}."
            )
            _print_last_error(mt5)
            return 1

        _print_summary(symbol, timeframe_name, candles)
        return 0
    finally:
        mt5.shutdown()
        print("Conexao MT5 encerrada com seguranca.")


def _candle_count() -> int:
    raw_count = os.getenv("MT5_CANDLE_COUNT", str(DEFAULT_CANDLE_COUNT))
    try:
        return max(int(raw_count), MINIMUM_CANDLES)
    except ValueError:
        return DEFAULT_CANDLE_COUNT


def _timeframe(mt5: Any, timeframe_name: str) -> Any | None:
    available = {
        "M1": "TIMEFRAME_M1",
        "M5": "TIMEFRAME_M5",
        "M15": "TIMEFRAME_M15",
        "M30": "TIMEFRAME_M30",
        "H1": "TIMEFRAME_H1",
        "H4": "TIMEFRAME_H4",
        "D1": "TIMEFRAME_D1",
    }
    attribute_name = available.get(timeframe_name)
    if attribute_name is None:
        return None
    return getattr(mt5, attribute_name, None)


def _print_summary(symbol: str, timeframe_name: str, candles: list[Candle]) -> None:
    first = candles[0]
    last = candles[-1]

    print("MT5 READ ONLY VALIDATION: OK")
    print(f"Simbolo: {symbol}")
    print(f"Timeframe: {timeframe_name}")
    print(f"Candles convertidos para Candle: {len(candles)}")
    print(
        "Primeiro candle: "
        f"{first.data} O={first.abertura} H={first.maxima} "
        f"L={first.minima} C={first.fechamento} V={first.volume}"
    )
    print(
        "Ultimo candle: "
        f"{last.data} O={last.abertura} H={last.maxima} "
        f"L={last.minima} C={last.fechamento} V={last.volume}"
    )
    print("Modo: somente leitura de candles.")


def _print_last_error(mt5: Any) -> None:
    last_error = getattr(mt5, "last_error", None)
    if callable(last_error):
        print(f"MT5 last_error: {last_error()}")


if __name__ == "__main__":
    sys.exit(main())
