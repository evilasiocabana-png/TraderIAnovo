"""Testes de seguranca do script manual MT5 read-only."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


SCRIPT_PATH = Path("scripts/validate_mt5_read_only_connection.py")


class ValidateMT5ReadOnlyConnectionScriptTest(unittest.TestCase):
    def test_script_nao_declara_capacidades_operacionais(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        forbidden_calls = {
            "order" + "_send",
            "orders" + "_get",
            "positions" + "_get",
            "positions" + "_total",
        }

        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_script_le_credenciais_por_variaveis_de_ambiente(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn('os.getenv("MT5_LOGIN")', source)
        self.assertIn('os.getenv("MT5_PASSWORD")', source)
        self.assertIn('os.getenv("MT5_SERVER")', source)


if __name__ == "__main__":
    unittest.main()
