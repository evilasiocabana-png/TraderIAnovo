"""Configuracao central de logging."""

import logging
from dataclasses import dataclass


@dataclass(frozen=True)
class LoggerFactory:
    """Cria loggers padronizados para o projeto."""

    level: int = logging.INFO

    def criar(self, nome: str) -> logging.Logger:
        """Retorna logger configurado."""
        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(name)s - %(message)s",
            level=self.level,
        )
        return logging.getLogger(nome)
