"""Provider MT5 placeholder estritamente read-only."""

from __future__ import annotations

from domain.contracts.mt5_status import MT5Status


class MT5ReadonlyProvider:
    """Fronteira read-only para futura leitura MT5."""

    def get_status(self) -> MT5Status:
        return MT5Status(
            status="READ_ONLY_PLACEHOLDER",
            server="N/D",
            account="N/D",
            timeframe="M1",
        )

    def get_symbols(self) -> list[str]:
        return ["EURUSD", "GBPUSD", "USDJPY"]

    def get_latest_price(self, symbol: str) -> float | None:
        prices = {"EURUSD": 1.1000, "GBPUSD": 1.2500, "USDJPY": 150.0}
        return prices.get(symbol.upper())
