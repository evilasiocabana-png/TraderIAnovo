"""Compatibilidade para configuracoes centrais do TraderIA_WDO."""

from core.configuration_manager import ConfigurationManager, SystemConfiguration


class Settings(SystemConfiguration):
    """Alias de compatibilidade para configuracao do sistema."""

    @property
    def ativo(self) -> str:
        """Compatibilidade com nomenclatura antiga."""
        return self.symbol

    @property
    def capital_inicial(self) -> float:
        """Compatibilidade com nomenclatura antiga."""
        return self.initial_capital

    @property
    def stop_pontos(self) -> float:
        """Compatibilidade com nomenclatura antiga."""
        return self.stop_points

    @property
    def gain_pontos(self) -> float:
        """Compatibilidade com nomenclatura antiga."""
        return self.target_points

    @property
    def perda_maxima_dia(self) -> float:
        """Compatibilidade com nomenclatura antiga."""
        return self.max_daily_loss

    @property
    def limite_operacoes(self) -> int:
        """Compatibilidade com nomenclatura antiga."""
        return self.max_daily_operations

    @property
    def score_minimo(self) -> int:
        """Compatibilidade com nomenclatura antiga."""
        return self.minimum_score


__all__ = ["ConfigurationManager", "Settings", "SystemConfiguration"]
