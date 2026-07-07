"""Testes de protecao das regras arquiteturais."""

import ast
import unittest
from pathlib import Path


class ArchitectureRulesTest(unittest.TestCase):
    """Garante que fronteiras arquiteturais nao sejam quebradas."""

    def test_strategies_nao_importam_execucao_ou_risco(self) -> None:
        """Impede estrategias de dependerem de risco, broker ou ordens."""
        proibidos = {
            "risk.risk_engine",
            "core.broker",
            "core.order_manager",
        }

        for caminho in self._python_files(Path("strategies")):
            imports = self._imports(caminho)
            violacoes = imports.intersection(proibidos)
            self.assertEqual(violacoes, set(), str(caminho))

    def test_market_dna_nao_importa_broker(self) -> None:
        """Impede MARKET DNA de depender do broker."""
        caminho = Path("market") / "market_dna.py"
        imports = self._imports(caminho)

        self.assertNotIn("core.broker", imports)

    def test_domain_nao_importa_infraestrutura(self) -> None:
        """Impede dominio de depender de bibliotecas ou infra externas."""
        proibidos = {"streamlit", "sqlite3", "pandas", "MetaTrader5"}

        for caminho in self._python_files(Path("domain")):
            imports = self._imports(caminho)
            violacoes = imports.intersection(proibidos)
            self.assertEqual(violacoes, set(), str(caminho))

    def test_domain_nao_acessa_csv_diretamente(self) -> None:
        """Impede leitura ou escrita direta de CSV no dominio."""
        for caminho in self._python_files(Path("domain")):
            texto = caminho.read_text(encoding="utf-8")
            self.assertNotIn(".csv", texto, str(caminho))

    def test_strategies_nao_retornam_dict_literal(self) -> None:
        """Impede estrategias de retornarem dicionarios como sinal."""
        for caminho in self._python_files(Path("strategies")):
            tree = self._parse(caminho)
            for node in ast.walk(tree):
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
                    self.fail(f"{caminho}:{node.lineno} retorna dict literal")

    def _python_files(self, pasta: Path) -> list[Path]:
        return [
            caminho
            for caminho in pasta.rglob("*.py")
            if "__pycache__" not in caminho.parts
        ]

    def _imports(self, caminho: Path) -> set[str]:
        imports: set[str] = set()
        for node in ast.walk(self._parse(caminho)):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
        return imports

    def _parse(self, caminho: Path) -> ast.AST:
        return ast.parse(caminho.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
