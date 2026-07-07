"""Persistencia SQLite para operacoes."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from domain.operacao import Operacao


@dataclass(frozen=True)
class SQLiteOperacaoRepository:
    """Repositorio SQLite para salvar operacoes."""

    caminho: Path = Path("data") / "traderia.db"

    def inicializar(self) -> None:
        """Cria a tabela de operacoes quando necessario."""
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.caminho) as conexao:
            conexao.execute(self._schema())

    def salvar(self, operacao: Operacao) -> None:
        """Insere uma operacao no banco."""
        self.inicializar()
        with sqlite3.connect(self.caminho) as conexao:
            conexao.execute(self._insert_sql(), self._valores(operacao))

    def listar(self) -> list[Operacao]:
        """Lista operacoes persistidas."""
        self.inicializar()
        with sqlite3.connect(self.caminho) as conexao:
            linhas = conexao.execute("SELECT * FROM operacoes").fetchall()
        return [self._to_operacao(linha) for linha in linhas]

    def _schema(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS operacoes (
            tipo TEXT, entrada REAL, stop REAL, gain REAL, score INTEGER,
            motivo TEXT, status TEXT, resultado REAL
        )
        """

    def _insert_sql(self) -> str:
        return """
        INSERT INTO operacoes
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

    def _valores(self, operacao: Operacao) -> tuple:
        return (
            operacao.tipo, operacao.entrada, operacao.stop, operacao.gain,
            operacao.score, operacao.motivo, operacao.status, operacao.resultado,
        )

    def _to_operacao(self, linha: tuple) -> Operacao:
        return Operacao(*linha)
