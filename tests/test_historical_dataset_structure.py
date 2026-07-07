"""Valida a estrutura documental de datasets historicos."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_DATA_DIR = ROOT / "historical_data"
DATASETS_DIR = HISTORICAL_DATA_DIR / "datasets"


class HistoricalDatasetStructureTest(unittest.TestCase):
    """Garante que a fundacao historica nao presume datasets reais."""

    def test_diretorios_oficiais_existem(self) -> None:
        self.assertTrue(HISTORICAL_DATA_DIR.is_dir())
        self.assertTrue(DATASETS_DIR.is_dir())

    def test_readmes_existem(self) -> None:
        self.assertTrue((HISTORICAL_DATA_DIR / "README.md").is_file())
        self.assertTrue((DATASETS_DIR / "README.md").is_file())

    def test_readme_documenta_padrao_de_estrutura(self) -> None:
        content = (HISTORICAL_DATA_DIR / "README.md").read_text(encoding="utf-8")

        self.assertIn("historical_data/datasets/<symbol>/<timeframe>/<year>/", content)
        self.assertIn("WDO", content)
        self.assertIn("1m", content)
        self.assertIn("metadata.json", content)

    def test_readme_documenta_metadados_minimos(self) -> None:
        content = (HISTORICAL_DATA_DIR / "README.md").read_text(encoding="utf-8")
        required_fields = [
            "symbol",
            "timeframe",
            "exchange",
            "timezone",
            "first_timestamp",
            "last_timestamp",
            "candle_count",
            "source",
            "version",
        ]

        for field in required_fields:
            with self.subTest(field=field):
                self.assertRegex(content, rf"\b{re.escape(field)}\b")

    def test_datasets_locais_sao_opcionais_e_estruturados(self) -> None:
        entries = [
            path
            for path in DATASETS_DIR.iterdir()
            if path.name != "README.md"
        ]

        for symbol_path in entries:
            with self.subTest(symbol=symbol_path.name):
                self.assertTrue(symbol_path.is_dir())
                for timeframe_path in symbol_path.iterdir():
                    self.assertTrue(timeframe_path.is_dir())
                    for period_path in timeframe_path.iterdir():
                        self.assertTrue(period_path.is_dir())
                        self.assertTrue((period_path / "metadata.json").is_file())

    def test_nenhum_arquivo_real_e_exigido(self) -> None:
        datasets_readme = (DATASETS_DIR / "README.md").read_text(encoding="utf-8").lower()

        self.assertIn("nenhum dataset real e obrigatorio", datasets_readme)
        self.assertIn("nao exigir arquivos reais", datasets_readme)

    def test_leitura_continua_restrita_ao_historical_data_provider(self) -> None:
        content = (HISTORICAL_DATA_DIR / "README.md").read_text(encoding="utf-8")

        self.assertIn("HistoricalDataProvider", content)
        self.assertIn("nao autoriza leitura direta", content)


if __name__ == "__main__":
    unittest.main()
