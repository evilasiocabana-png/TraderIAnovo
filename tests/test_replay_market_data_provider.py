"""Testes da integracao do ReplayService com MarketDataProvider."""

import ast
import unittest
from pathlib import Path

from application.replay_service import ReplayService, ReplayStatus
from domain.candle import Candle
from market_data import HistoricalDataset, MarketDataProvider


class FakeMarketDataProvider(MarketDataProvider):
    """Provider controlado para validar a fronteira do ReplayService."""

    def __init__(self, dataset: HistoricalDataset) -> None:
        self.dataset = dataset
        self.loaded_path: object | None = None

    def load(self, *args: object, **kwargs: object) -> HistoricalDataset:
        """Registra a chamada e retorna o dataset configurado."""
        self.loaded_path = args[0] if args else None
        return self.dataset

    def symbols(self) -> list[str]:
        """Lista simbolos disponiveis no provider fake."""
        return [self.dataset.symbol]

    def available_periods(self) -> list[str]:
        """Lista timeframes disponiveis no provider fake."""
        return [self.dataset.timeframe]


class SpyReplayEngine:
    """ReplayEngine minimo para verificar o contrato recebido."""

    def __init__(self) -> None:
        self.candles: list[Candle] = []
        self.current_index = -1
        self.current_candle: Candle | None = None
        self.is_running = False
        self.is_finished = False
        self.received_candles: object | None = None
        self.event_bus = None

    def load_candles(self, candles: list[Candle]) -> None:
        """Captura exatamente o objeto entregue pelo ReplayService."""
        self.received_candles = candles
        self.candles = list(candles)

    def get_state(self) -> object:
        """Retorna estado compativel com ReplayService."""
        return self

    @property
    def total_candles(self) -> int:
        """Total de candles carregados no spy."""
        return len(self.candles)


class ReplayMarketDataProviderTest(unittest.TestCase):
    """Valida que o replay usa a camada oficial de market data."""

    def test_replay_service_carrega_dataset_via_market_data_provider(self) -> None:
        """ReplayService deve delegar carga historica ao provider."""
        provider = FakeMarketDataProvider(self._dataset(3))
        service = ReplayService(market_data_provider=provider)

        data = service.load_historical_data("fonte_historica")

        self.assertEqual(provider.loaded_path, "fonte_historica")
        self.assertEqual(data.status, ReplayStatus.READY)
        self.assertEqual(data.total_candles, 3)
        self.assertEqual(data.candles_loaded[0].data, "2026-06-26 09:00")

    def test_replay_engine_recebe_apenas_lista_de_candles(self) -> None:
        """ReplayEngine nao deve receber HistoricalDataset."""
        engine = SpyReplayEngine()
        service = ReplayService(
            replay_engine=engine,
            market_data_provider=FakeMarketDataProvider(self._dataset(2)),
        )

        service.load_historical_data("fonte_historica")

        self.assertIsInstance(engine.received_candles, list)
        self.assertTrue(
            all(isinstance(candle, Candle) for candle in engine.received_candles)
        )

    def test_dataset_vazio_mantem_replay_empty(self) -> None:
        """Dataset vazio deve deixar replay em estado seguro."""
        service = ReplayService(
            market_data_provider=FakeMarketDataProvider(self._empty_dataset()),
        )

        data = service.load_historical_data("fonte_invalida")

        self.assertEqual(data.status, ReplayStatus.EMPTY)
        self.assertEqual(data.total_candles, 0)
        self.assertEqual(data.candles_loaded, [])

    def test_market_snapshot_usa_simbolo_do_dataset_carregado(self) -> None:
        """Replay deve alinhar Market DNA ao ativo real do dataset."""
        service = ReplayService()
        service.load_historical_dataset(self._dataset(1, symbol="PETR4", timeframe="1d"))

        data = service.next_candle()

        self.assertIsNotNone(data.decision_context)
        self.assertEqual(data.decision_context.market_snapshot.symbol, "PETR4")

    def test_replay_service_nao_importa_loader_historico_diretamente(self) -> None:
        """ReplayService deve depender da abstracao de market data."""
        imports = self._imports(Path("application") / "replay_service.py")

        self.assertIn("market_data", imports)
        self.assertNotIn("data.historical_data_loader", imports)

    def test_replay_nao_importa_infraestrutura_de_arquivo_ou_csv(self) -> None:
        """Replay nao deve depender de CSV, Path, open ou pandas."""
        forbidden_imports = {"csv", "pathlib", "pandas", "data.historical_data_loader"}
        for path in self._replay_boundary_files():
            imports = self._imports(path)
            self.assertEqual(imports.intersection(forbidden_imports), set(), str(path))

    def test_replay_nao_chama_leitura_direta_de_arquivo(self) -> None:
        """Replay deve obter historico somente via MarketDataProvider."""
        forbidden_calls = {"open", "read_csv"}
        for path in self._replay_boundary_files():
            calls = self._calls(path)
            self.assertEqual(calls.intersection(forbidden_calls), set(), str(path))

    def _dataset(
        self,
        quantity: int,
        symbol: str = "WDO",
        timeframe: str = "1m",
    ) -> HistoricalDataset:
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
            symbol=symbol,
            timeframe=timeframe,
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

    def _calls(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                if isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        return calls

    def _replay_boundary_files(self) -> list[Path]:
        return [
            Path("replay") / "replay_engine.py",
            Path("application") / "replay_service.py",
        ]


if __name__ == "__main__":
    unittest.main()
