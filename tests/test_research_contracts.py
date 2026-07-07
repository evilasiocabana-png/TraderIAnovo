"""Contratos arquiteturais e comportamentais do Research Lab."""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
import unittest

from application.research_lab_service import (
    BenchmarkData,
    ExperimentValidationData,
    ResearchExperimentData,
    ResearchLabService,
)
from domain.candle import Candle
from market_data.historical_dataset import HistoricalDataset
from research.benchmark_comparator import BenchmarkComparator
from research.experiment_validator import ExperimentValidator
from research.research_advisor import ResearchAdvisor
from research.research_engine import ResearchEngine
from research.research_lab import ResearchExperiment, ResearchLab
from research.strategy_benchmark import StrategyBenchmarkResult
from tests.architecture_test_utils import calls_from, imports_from, python_files, read_source


class ResearchContractsTest(unittest.TestCase):
    """Blinda o laboratorio quantitativo contra regressao publica."""

    REQUIRED_RESEARCH_LAB_SERVICE_METHODS = {
        "alpha001_research_report",
        "best_parameter_grid_result",
        "clear",
        "compare_benchmarks",
        "get_alpha001_research_summary",
        "get_alpha001_robustness",
        "last_comparison",
        "last_experiment",
        "last_validation",
        "list_alpha001_parameter_ranking",
        "list_available_strategies",
        "list_benchmarks",
        "list_experiments",
        "list_parameter_grid_results",
        "list_validations",
        "run_alpha001_parameter_ranking",
        "run_demo_benchmarks",
        "run_demo_experiment",
        "run_demo_parameter_grid",
        "run_historical_data_experiment",
        "run_historical_experiment",
        "validate_all_benchmarks",
    }

    RESEARCH_RUNTIME_FILES = (
        Path("research/research_lab.py"),
        Path("research/research_engine.py"),
        Path("research/experiment_validator.py"),
        Path("research/benchmark_comparator.py"),
        Path("research/research_advisor.py"),
        Path("application/research_lab_service.py"),
    )

    def test_componentes_criticos_importam_sem_excecao(self) -> None:
        components = {
            "research.research_lab": "ResearchLab",
            "application.research_lab_service": "ResearchLabService",
            "research.research_engine": "ResearchEngine",
            "research.experiment_validator": "ExperimentValidator",
            "research.benchmark_comparator": "BenchmarkComparator",
            "research.research_advisor": "ResearchAdvisor",
        }

        for module_name, class_name in components.items():
            with self.subTest(component=class_name):
                module = importlib.import_module(module_name)
                self.assertTrue(hasattr(module, class_name))

    def test_componentes_criticos_instanciam_sem_excecao(self) -> None:
        instances = [
            ResearchLab(),
            ResearchLabService(),
            ResearchEngine(),
            ExperimentValidator(),
            BenchmarkComparator(),
            ResearchAdvisor(),
        ]

        self.assertIsInstance(instances[0], ResearchLab)
        self.assertIsInstance(instances[1], ResearchLabService)
        self.assertIsInstance(instances[2], ResearchEngine)
        self.assertIsInstance(instances[3], ExperimentValidator)
        self.assertIsInstance(instances[4], BenchmarkComparator)
        self.assertIsInstance(instances[5], ResearchAdvisor)

    def test_research_lab_service_expoe_api_publica_essencial(self) -> None:
        public_methods = self._public_method_names(ResearchLabService)

        missing = sorted(self.REQUIRED_RESEARCH_LAB_SERVICE_METHODS - public_methods)

        self.assertEqual(
            missing,
            [],
            "ResearchLabService perdeu metodos publicos essenciais: "
            + ", ".join(missing),
        )

    def test_research_lab_expoe_api_publica_essencial(self) -> None:
        public_methods = self._public_method_names(ResearchLab)
        required = {
            "run_experiment",
            "list_experiments",
            "last_experiment",
            "clear",
            "run_strategy_benchmark",
            "list_benchmarks",
            "compare_benchmarks",
            "validate_all_benchmarks",
            "list_validations",
        }

        self.assertTrue(required.issubset(public_methods))

    def test_experimento_minimo_em_memoria_executa_sem_excecao(self) -> None:
        service = ResearchLabService()

        data = service.run_historical_experiment(
            self._candles(3),
            experiment_name="Contrato Research",
        )

        self.assertIsInstance(data, ResearchExperimentData)
        self.assertEqual(data.experiment_name, "Contrato Research")
        self.assertEqual(data.strategy_name, "alpha001_iorb")
        self.assertIn(data, service.list_experiments())

    def test_research_lab_executa_experimento_sem_arquivo_fisico(self) -> None:
        experiment = ResearchExperiment(
            experiment_name="Memoria",
            strategy_name="alpha001_iorb",
            stop_points=50.0,
            target_points=100.0,
            candles=self._candles(2),
        )

        completed = ResearchLab().run_experiment(experiment)

        self.assertEqual(completed.experiment_name, "Memoria")
        self.assertIsNotNone(completed.result)

    def test_metricas_quantitativas_minimas_nao_desaparecem(self) -> None:
        data = ResearchLabService().run_demo_experiment()

        for metric in (
            "total_trades",
            "win_rate",
            "profit_factor",
            "max_drawdown_points",
            "net_profit_points",
        ):
            with self.subTest(metric=metric):
                self.assertTrue(hasattr(data, metric))
                self.assertIsInstance(getattr(data, metric), (int, float))

    def test_benchmarks_validacoes_e_diagnostico_continuam_disponiveis(self) -> None:
        service = ResearchLabService()

        benchmarks = service.run_demo_benchmarks()
        comparison = service.compare_benchmarks()
        validations = service.validate_all_benchmarks()

        self.assertTrue(benchmarks)
        self.assertIsInstance(benchmarks[0], BenchmarkData)
        self.assertTrue(comparison.ranking)
        self.assertTrue(validations)
        self.assertIsInstance(validations[0], ExperimentValidationData)

    def test_baixa_amostra_e_identificada_pelo_contrato_existente(self) -> None:
        benchmark = StrategyBenchmarkResult(
            strategy_name="alpha001_iorb",
            total_trades=2,
            wins=1,
            losses=1,
            net_profit_points=0.0,
            win_rate=0.5,
            profit_factor=1.0,
            max_drawdown_points=10.0,
            equity_curve=[0.0, 10.0, 0.0],
        )

        validation = ExperimentValidator().validate(benchmark)

        self.assertFalse(validation.is_statistically_relevant)
        self.assertIn("Pouca amostra", validation.warnings)

    def test_dados_historicos_sao_resolvidos_por_provider_autorizado(self) -> None:
        provider = _FakeHistoricalProvider(self._candles(2))
        service = ResearchLabService(market_data_provider=provider)

        data = service.run_historical_data_experiment(source="dataset-1")

        self.assertIsInstance(data, ResearchExperimentData)
        self.assertEqual(provider.calls, [("dataset-1", "WDO", "UNKNOWN")])

    def test_research_lab_nao_executa_ordem_real(self) -> None:
        service = ResearchLabService()

        data = service.run_demo_experiment()

        self.assertIsInstance(data, ResearchExperimentData)
        self.assertFalse(hasattr(service, "broker"))
        self.assertFalse(hasattr(service, "mt5"))
        self.assertFalse(hasattr(service, "corretora"))

    def test_componentes_nao_importam_ui_broker_mt5_ou_adapters_fisicos(
        self,
    ) -> None:
        forbidden_imports = {
            "dashboard_app",
            "streamlit",
            "broker",
            "core.broker",
            "corretora",
            "mt5",
            "MetaTrader5",
            "pandas",
            "duckdb",
            "market_data.csv_historical_data_source",
            "market_data.parquet_historical_data_adapter",
            "market_data.duckdb_historical_data_adapter",
        }

        for path in self.RESEARCH_RUNTIME_FILES:
            with self.subTest(path=str(path)):
                imports = imports_from(path)
                self.assertTrue(
                    forbidden_imports.isdisjoint(imports),
                    f"{path} importou acoplamento proibido: "
                    f"{sorted(forbidden_imports & imports)}",
                )

    def test_componentes_nao_chamam_execucao_operacional_real(self) -> None:
        forbidden_calls = {
            "order_send",
            "send_order",
            "place_order",
            "execute_order",
            "executar_ordem",
            "enviar_ordem",
            "connect_mt5",
        }

        for path in self.RESEARCH_RUNTIME_FILES:
            with self.subTest(path=str(path)):
                calls = calls_from(path)
                self.assertTrue(
                    forbidden_calls.isdisjoint(calls),
                    f"{path} chama execucao operacional proibida: "
                    f"{sorted(forbidden_calls & calls)}",
                )

    def test_research_package_nao_acessa_arquivos_fisicos_diretamente(self) -> None:
        forbidden_calls = {"open", "read_csv", "read_parquet", "connect"}
        forbidden_imports = {"pathlib", "pathlib.Path", "csv"}

        for path in self._research_package_files():
            with self.subTest(path=str(path)):
                imports = imports_from(path)
                calls = calls_from(path)
                self.assertTrue(forbidden_imports.isdisjoint(imports))
                self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_exports_csv_explicitos_ficam_restritos_ao_service_de_aplicacao(
        self,
    ) -> None:
        source = read_source(Path("application/research_lab_service.py"))

        self.assertIn("export_alpha001_results_to_csv", source)
        self.assertIn("def _write_csv", source)
        self.assertNotIn("import pandas", source)
        self.assertNotIn("duckdb", source)

    def _public_method_names(self, cls: type) -> set[str]:
        return {
            name
            for name, method in inspect.getmembers(cls, inspect.isfunction)
            if not name.startswith("_")
            and list(inspect.signature(method).parameters)[:1] == ["self"]
        }

    def _research_package_files(self) -> list[Path]:
        return python_files(Path("research"))

    def _candles(self, quantity: int) -> list[Candle]:
        return [self._candle(index) for index in range(quantity)]

    def _candle(self, index: int) -> Candle:
        close = 1000.0 + index * 10
        return Candle(
            data=f"2026-06-26 09:{index:02d}",
            abertura=close - 2,
            maxima=close + 10,
            minima=close - 10,
            fechamento=close,
            volume=1000 + index,
        )


class _FakeHistoricalProvider:
    """Provider fake para validar fronteira autorizada."""

    def __init__(self, candles: list[Candle]) -> None:
        self.candles = candles
        self.calls: list[tuple[object, str, str]] = []

    def load(
        self,
        source: object,
        symbol: str = "WDO",
        timeframe: str = "UNKNOWN",
    ) -> HistoricalDataset:
        self.calls.append((source, symbol, timeframe))
        return HistoricalDataset(
            symbol=symbol,
            timeframe=timeframe,
            start_date=self.candles[0].data if self.candles else None,
            end_date=self.candles[-1].data if self.candles else None,
            candles=list(self.candles),
        )


if __name__ == "__main__":
    unittest.main()
