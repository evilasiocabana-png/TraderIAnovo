"""Servico read-only para a aba Forex MT5."""

from __future__ import annotations

from domain.contracts.forex_signal import ForexSignal
from domain.contracts.mt5_status import MT5Status


class ForexMT5Service:
    """Exibe estado de mercado sem executar ordens."""

    def get_status(self) -> MT5Status:
        return MT5Status(
            status="READ_ONLY_MOCK",
            server="N/D",
            account="N/D",
            timeframe="M1",
        )

    def get_signals(self) -> list[ForexSignal]:
        return [
            ForexSignal(
                pair="EURUSD",
                timeframe="M1",
                decision="WAIT",
                price=1.1000,
                reason="Base inicial read-only sem conexao operacional.",
            ),
            ForexSignal(
                pair="GBPUSD",
                timeframe="M1",
                decision="WAIT",
                price=1.2500,
                reason="Aguardando parametros autorizados pelo Lab.",
            ),
        ]
