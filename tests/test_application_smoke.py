"""Smoke test da aplicacao principal."""

import gc
import io
import unittest
import warnings
from contextlib import redirect_stdout

import app


class ApplicationSmokeTest(unittest.TestCase):
    """Valida inicializacao ponta a ponta da aplicacao."""

    def test_app_main_executa_sem_excecoes(self) -> None:
        """Executa o ponto de entrada principal sem lancar excecoes."""
        output = io.StringIO()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            with redirect_stdout(output):
                app.main()
            gc.collect()

        self.assertIn("Ativo:", output.getvalue())
        self.assertIn("Eventos registrados:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
