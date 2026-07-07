"""Testes da integracao do ResearchLabService com MarketDataProvider."""

import ast
import unittest
from pathlib import Path

from application.research_lab_service import ResearchLabService
from domain.candle import Candle
from market_data import HistoricalDataset, MarketDataProvider


class FakeMarketDataProvider(MarketDataProvider):
    """Provider controlado para validar a fronteira do ResearchLabService."""

    def __init__(
        self,
        dataset: HistoricalDataset,
        errors: list[str] | None = None,
    ) -> None:
        self.dataset = dataset
        self.errors = list(errors or [])
        self.loaded_path: object | None = None
        self.loaded_symbol: str | None = None
        self.loaded_timeframe: str | None = None

    def load(self, *args: object, **kwargs: object) -> HistoricalDataset:
        """Registra a chamada e retorna o dataset configurado."""
        self.loaded_path = args[0] if args else None
        self.loaded_symbol = kwargs.get("symbol")
        self.loaded_timeframe = kwargs.get("timeframe")
        return self.dataset

    def symbols(self) -> list[str]:
        """Lista simbolos disponiveis no provider fake."""
        return [self.dataset.symbol]

    def available_periods(self) -> list[str]:
        """Lista timeframes disponiveis no provider fake."""
        return [self.dataset.timeframe]


class SpyResearchLab:
    """ResearchLab minimo para verificar candles recebidos."""

    def __init__(self) -> None:
        self.received_candles: object | None = None

    def run_experiment(self, experiment: object) -> object:
        """Captura os candles e devolve o experimento sem executar backtest."""
        self.received_candles = experiment.candles
        return experiment


class ResearchMarketDataProviderTest(unittest.TestCase):
    """Valida que o Research Lab usa a camada oficial de market data."""

    def test_research_lab_service_carrega_dataset_via_provider(self) -> None:
        """ResearchLabService deve delegar carga historica ao provider."""
        provider = FakeMarketDataProvider(self._dataset(4))
        service = ResearchLabService(market_data_provider=provider)

        data = service.run_historical_csv_experiment("historico.csv")

        self.assertEqual(provider.loaded_path, "historico.csv")
        self.assertEqual(data.experiment_name, "Historical WDO Research")
        self.assertEqual(data.strategy_name, "alpha001_iorb")

    def test_research_lab_service_resolve_origem_historica_via_provider(self) -> None:
        """Servico deve aceitar origem opaca sem conhecer formato fisico."""
        provider = FakeMarketDataProvider(self._dataset(3))
        service = ResearchLabService(market_data_provider=provider)

        data = service.run_historical_data_experiment(
            source="origem_opaca",
            experiment_name="wdo_1m_2026",
            symbol="WDO",
            timeframe="1m",
        )

        self.assertEqual(provider.loaded_path, "origem_opaca")
        self.assertEqual(provider.loaded_symbol, "WDO")
        self.assertEqual(provider.loaded_timeframe, "1m")
        self.assertEqual(data.experiment_name, "wdo_1m_2026")

    def test_research_lab_recebe_apenas_lista_de_candles(self) -> None:
        """ResearchLab nao deve receber HistoricalDataset."""
        research_lab = SpyResearchLab()
        service = ResearchLabService(
            research_lab=research_lab,
            market_data_provider=FakeMarketDataProvider(self._dataset(2)),
        )

        service.run_historical_csv_experiment("historico.csv")

        self.assertIsInstance(research_lab.received_candles, list)
        self.assertTrue(
            all(isinstance(candle, Candle) for candle in research_lab.received_candles)
        )

    def test_dataset_vazio_retorna_erro_seguro(self) -> None:
        """Dataset vazio deve ser rejeitado antes do ResearchLab."""
        service = ResearchLabService(
            market_data_provider=FakeMarketDataProvider(
                self._empty_dataset(),
                errors=["CSV com estrutura invalida."],
            ),
        )

        with self.assertRaisesRegex(ValueError, "CSV com estrutura invalida."):
            service.run_historical_csv_experiment("invalido.csv")

    def test_research_lab_service_nao_importa_loader_historico_diretamente(
        self,
    ) -> None:
        """ResearchLabService deve depender da abstracao de market data."""
        imports = self._imports(Path("application") / "research_lab_service.py")

        self.assertIn("market_data", imports)
        self.assertNotIn("data.historical_data_loader", imports)

    def test_experimento_demo_permanece_funcionando(self) -> None:
        """Fluxo atual de experimento demo deve permanecer operacional."""
        data = ResearchLabService().run_demo_experiment()

        self.assertEqual(data.experiment_name, "Demo Research Lab")
        self.assertEqual(data.strategy_name, "alpha001_iorb")

    def _dataset(self, quantity: int) -> HistoricalDataset:
        candles = [
            Candle(
                data=f"2026-06-26 09:{index:02d}",
                abertura=100.0 + index,
                maxima=102.0 + index,
                minima=98.0 + index,
                fechamento=101.0 + index,
                volume=1000,
            )
            for index in range(quantity)
        ]
        return HistoricalDataset(
            symbol="WDO",
            timeframe="1m",
            start_date=candles[0].data,
            end_date=candles[-1].data,
            candles=candles,
        )

    def _empty_dataset(self) -> HistoricalDataset:
        return HistoricalDataset(
            symbol="WDO",
            timeframe="1m",
            start_date=None,
            end_date=None,
            candles=[],
        )

    def _imports(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        return imports


if __name__ == "__main__":
    unittest.main()
