"""Registro em memoria dos instrumentos financeiros suportados."""

from __future__ import annotations

from dataclasses import dataclass, field

from market.instruments.instrument import Instrument


DEFAULT_WDO_INSTRUMENT = Instrument(
    instrument_id="B3:WDO",
    symbol="WDO",
    asset_class="FUTURES",
    exchange="B3",
    currency="BRL",
    tick_size=0.5,
    point_value=10.0,
    contract_size=1.0,
    enabled=True,
    metadata={"status": "supported"},
)

FUTURE_INSTRUMENT_SYMBOLS: tuple[str, ...] = (
    "WIN",
    "PETR4",
    "VALE3",
    "ITUB4",
    "SPY",
    "QQQ",
    "ES",
    "NQ",
    "CL",
    "GC",
    "BTC",
)


@dataclass
class InstrumentRegistry:
    """Gerencia instrumentos suportados em memoria."""

    _instruments: dict[str, Instrument] = field(
        default_factory=dict,
        init=False,
    )

    def __post_init__(self) -> None:
        self.register(DEFAULT_WDO_INSTRUMENT)

    def register(self, instrument: Instrument) -> Instrument:
        """Registra ou substitui um instrumento."""
        self._instruments[instrument.instrument_id] = instrument
        return instrument

    def unregister(self, instrument_id: str) -> bool:
        """Remove um instrumento quando existir."""
        if instrument_id not in self._instruments:
            return False
        del self._instruments[instrument_id]
        return True

    def get(self, instrument_id: str) -> Instrument | None:
        """Retorna um instrumento pelo identificador."""
        return self._instruments.get(instrument_id)

    def list(self) -> tuple[Instrument, ...]:
        """Lista instrumentos registrados."""
        return tuple(self._instruments.values())

    def exists(self, instrument_id: str) -> bool:
        """Indica se um instrumento esta registrado."""
        return instrument_id in self._instruments
