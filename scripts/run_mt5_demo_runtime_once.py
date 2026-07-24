"""Executa um ciclo do runtime demo conectado ao MT5."""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import asdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from application.demo_execution_service import (
    DemoExecutionPolicy,
    DemoExecutionService,
    DisabledDemoExecutionProvider,
)
from application.demo_trading_runtime import (
    DemoTradingRuntime,
    DemoTradingRuntimeConfig,
)
from infrastructure.execution.mt5_demo_execution_provider import MT5DemoExecutionProvider
from infrastructure.market_data.mt5_market_data_provider import MT5MarketDataProvider


class _RuntimeMT5MarketDataProvider:
    """Adapter de composicao para manter application sem chamada direta a connect()."""

    def __init__(self, provider: MT5MarketDataProvider) -> None:
        self.provider = provider

    def initialize_market_data(self) -> bool:
        return self.provider.connect()

    def select_symbol(self, symbol: str) -> bool:
        return self.provider.select_symbol(symbol)

    def get_candles(self, symbol: str, timeframe: object, count: int):
        return self.provider.get_candles(symbol, timeframe, count)


def _mt5_timeframe_value(timeframe: str) -> object:
    """Converte M1/H1/etc. para a constante do MetaTrader5."""
    normalized = str(timeframe or "M1").strip().upper()
    mt5 = importlib.import_module("MetaTrader5")
    return getattr(mt5, f"TIMEFRAME_{normalized}")


def main() -> None:
    """Roda um unico ciclo operacional demo com travas explicitas."""
    enabled = os.environ.get("TRADERIA_DEMO_EXECUTION_ENABLED") == "1"
    symbol = os.environ.get("TRADERIA_DEMO_SYMBOL", "WDO")
    timeframe_label = os.environ.get("TRADERIA_DEMO_TIMEFRAME", "M1")
    quantity = float(os.environ.get("TRADERIA_DEMO_QUANTITY", "0.1"))
    stop_points = float(os.environ.get("TRADERIA_DEMO_STOP_POINTS", "50"))
    target_points = float(os.environ.get("TRADERIA_DEMO_TARGET_POINTS", "100"))
    execution_provider = (
        MT5DemoExecutionProvider() if enabled else DisabledDemoExecutionProvider()
    )
    timeframe = _mt5_timeframe_value(timeframe_label) if enabled else timeframe_label

    runtime = DemoTradingRuntime(
        market_data_provider=_RuntimeMT5MarketDataProvider(MT5MarketDataProvider()),
        execution_service=DemoExecutionService(
            provider=execution_provider,
            policy=DemoExecutionPolicy(
                max_daily_operations=int(os.environ.get("TRADERIA_DEMO_MAX_TRADES", "8")),
                max_daily_loss=float(os.environ.get("TRADERIA_DEMO_MAX_DAILY_LOSS", "500")),
                allowed_start=os.environ.get("TRADERIA_DEMO_ALLOWED_START", "00:00"),
                allowed_end=os.environ.get("TRADERIA_DEMO_ALLOWED_END", "23:59"),
            ),
        ),
        config=DemoTradingRuntimeConfig(
            symbol=symbol,
            timeframe=timeframe,
            quantity=quantity,
            stop_points=stop_points,
            target_points=target_points,
            minimum_score=int(os.environ.get("TRADERIA_DEMO_MIN_SCORE", "60")),
            minimum_confidence=float(os.environ.get("TRADERIA_DEMO_MIN_CONFIDENCE", "0.60")),
            enabled=enabled,
        ),
    )
    result = runtime.run_once()
    print(asdict(result))


if __name__ == "__main__":
    main()
