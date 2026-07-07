"""Servico de aplicacao para status do sistema."""

from dataclasses import dataclass, field

from core.configuration_manager import ConfigurationManager, SystemConfiguration
from core.event_logger import EventLogger


@dataclass(frozen=True)
class SystemStatus:
    """Dados de status do sistema para apresentacao."""

    status: str
    version: str
    active_symbol: str
    event_count: int
    loaded_strategies_count: int


@dataclass(frozen=True)
class SystemService:
    """Fornece metadados do sistema para camadas de apresentacao."""

    configuration: SystemConfiguration = field(
        default_factory=ConfigurationManager.get_configuration
    )
    event_logger: EventLogger | None = None
    loaded_strategies_count: int = 4

    def get_status(self) -> SystemStatus:
        """Retorna o status consolidado do sistema."""
        status = "Simulação" if self.configuration.simulation_mode else "Real"
        return SystemStatus(
            status=status,
            version=self.configuration.version,
            active_symbol=self.configuration.symbol,
            event_count=self._event_count(),
            loaded_strategies_count=self.loaded_strategies_count,
        )

    def _event_count(self) -> int:
        if self.event_logger is None:
            return 0
        return len(self.event_logger.get_events())
