"""Testes da camada de servicos de aplicacao."""

import ast
import tempfile
import unittest
from pathlib import Path

from application.dashboard_service import DashboardData, DashboardService
from application.live_research_service import LiveResearchService
from application.market_service import MarketService
from application.session_service import SessionService
from application.system_service import SystemService
from core.configuration_manager import ConfigurationManager
from core.event_logger import EventLogger
from core.operation_session import OperationSession
from domain.candle import Candle
from market.feature_engine import FeatureSnapshot
from market.market_memory import MarketMemory
from market.market_dna import MarketDNA, MarketPattern
from market.regime_engine import MarketRegime, RegimeAnalysis


class ApplicationServicesTest(unittest.TestCase):
    """Valida as fachadas de aplicacao."""

    def setUp(self) -> None:
        """Restaura configuracao padrao antes de cada teste."""
        ConfigurationManager.reset_configuration()

    def test_market_service_retorna_snapshot_do_ultimo_market_dna(
        self,
    ) -> None:
        """Garante conversao do MARKET DNA para contrato."""
        with tempfile.TemporaryDirectory() as pasta:
            dna = MarketDNA(Path(pasta))
            dna.salvar(self._pattern("2026-06-25"))
            service = MarketService(lambda: dna.carregar()[-1])

            snapshot = service.get_latest_market_dna()

            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.symbol, "WDO")

    def test_dashboard_service_retorna_dashboard_data(self) -> None:
        """Garante que o dashboard recebe dados via fachada."""
        service = DashboardService(
            market_service=MarketService(lambda: self._pattern("2026-06-25")),
            system_service=SystemService(),
            session_service=SessionService(self._session()),
        )

        data = service.get_dashboard_data()

        self.assertIsInstance(data, DashboardData)
        self.assertEqual(data.system_status.active_symbol, "WDO")
        self.assertEqual(data.session_snapshot.session_date, "2026-06-25")
        self.assertEqual(data.configuration_data.symbol, "WDO")
        self.assertIsNotNone(data.regime_data)
        self.assertIsNotNone(data.research_data)
        self.assertIsNotNone(data.replay_data)
        self.assertEqual(data.research_lab_experiments, [])
        self.assertIsNone(data.last_research_experiment)
        self.assertEqual(data.research_benchmarks, [])
        self.assertIsNone(data.benchmark_comparison)
        self.assertEqual(data.parameter_grid_results, [])
        self.assertIsNone(data.best_parameter_grid_result)
        self.assertEqual(data.benchmark_validations, [])
        self.assertIsNone(data.last_benchmark_validation)
        self.assertGreater(data.research_data.similar_scenarios, 0)
        self.assertEqual(data.live_research_data.safety_status, "READ ONLY")

    def test_dashboard_service_expoe_estado_live_read_only(self) -> None:
        """Garante que o Dashboard consome estado live pela fachada."""
        live_service = LiveResearchService()
        live_service.process_candle(self._candle(1), symbol="EURUSD", timeframe="H1")
        service = DashboardService(live_research_service=live_service)

        live_data = service.get_live_research_data()
        dashboard_data = service.get_dashboard_data()

        self.assertTrue(live_data.has_data)
        self.assertEqual(live_data.symbol, "EURUSD")
        self.assertEqual(live_data.timeframe, "H1")
        self.assertEqual(live_data.safety_status, "READ ONLY")
        self.assertEqual(dashboard_data.live_research_data.symbol, "EURUSD")
        self.assertEqual(len(live_data.history), 1)
        self.assertEqual(live_data.history[0].symbol, "EURUSD")
        self.assertEqual(len(service.list_live_research_history()), 1)
        self.assertEqual(live_data.session_summary.total_snapshots, 1)
        self.assertEqual(
            service.get_live_research_session_summary().total_snapshots,
            1,
        )
        self.assertEqual(
            len(live_data.signal_quality),
            live_data.strategies_evaluated,
        )
        self.assertEqual(
            len(service.list_live_research_signal_quality()),
            live_data.strategies_evaluated,
        )
        self.assertEqual(
            len(service.list_live_experiment_signals()),
            live_data.strategies_evaluated,
        )
        self.assertEqual(
            service.get_live_experiment_summary().total_signals,
            live_data.strategies_evaluated,
        )
        self.assertEqual(
            dashboard_data.live_experiment_summary.total_signals,
            live_data.strategies_evaluated,
        )

    def test_dashboard_service_controla_replay(self) -> None:
        """Garante controle de replay via fachada do dashboard."""
        service = DashboardService()

        loaded = service.load_demo_replay_candles()
        started = service.start_replay()
        advanced = service.next_replay_candle()

        self.assertGreater(loaded.total_candles, 0)
        self.assertTrue(started.is_running)
        self.assertEqual(started.current_index, 0)
        self.assertEqual(advanced.current_index, 1)
        self.assertIsNotNone(service.get_dashboard_data().replay_data)

    def test_dashboard_service_preserva_estado_replay(self) -> None:
        """Garante avancos sequenciais no mesmo DashboardService."""
        service = DashboardService()
        service.load_demo_replay_candles()

        first = service.next_replay_candle()
        second = service.next_replay_candle()
        third = service.next_replay_candle()

        self.assertEqual(first.current_index, 0)
        self.assertEqual(second.current_index, 1)
        self.assertEqual(third.current_index, 2)

    def test_dashboard_service_controla_auto_replay(self) -> None:
        """Garante controle de auto replay pela fachada."""
        service = DashboardService()
        service.load_demo_replay_candles()

        enabled = service.enable_replay_auto_run(0.5)
        disabled = service.disable_replay_auto_run()

        self.assertTrue(enabled.auto_run_enabled)
        self.assertEqual(enabled.replay_speed_seconds, 0.5)
        self.assertFalse(disabled.auto_run_enabled)

    def test_dashboard_service_controla_research_lab(self) -> None:
        """Garante controle do Research Lab pela fachada."""
        service = DashboardService()

        experiment = service.run_demo_research_experiment()
        data = service.get_dashboard_data()

        self.assertEqual(service.last_research_experiment(), experiment)
        self.assertEqual(service.list_research_experiments(), [experiment])
        self.assertEqual(data.last_research_experiment, experiment)
        self.assertEqual(data.research_lab_experiments, [experiment])

        service.clear_research_experiments()
        self.assertEqual(service.list_research_experiments(), [])

    def test_dashboard_service_controla_benchmarks_research_lab(self) -> None:
        """Garante benchmarks do Research Lab pela fachada."""
        service = DashboardService()

        benchmarks = service.run_demo_research_benchmarks()
        comparison = service.compare_research_benchmarks()
        data = service.get_dashboard_data()

        self.assertTrue(benchmarks)
        self.assertEqual(service.list_research_benchmarks(), benchmarks)
        self.assertEqual(service.last_benchmark_comparison(), comparison)
        self.assertEqual(data.research_benchmarks, benchmarks)
        self.assertEqual(data.benchmark_comparison, comparison)

    def test_dashboard_service_controla_parameter_grid(self) -> None:
        """Garante grade de parametros pela fachada."""
        service = DashboardService()

        results = service.run_demo_parameter_grid()
        data = service.get_dashboard_data()

        self.assertEqual(len(results), 4)
        self.assertEqual(service.list_parameter_grid_results(), results)
        self.assertEqual(data.parameter_grid_results, results)
        self.assertEqual(
            service.best_parameter_grid_result(),
            data.best_parameter_grid_result,
        )

    def test_dashboard_service_controla_validacoes_benchmarks(self) -> None:
        """Garante validacoes estatisticas pela fachada."""
        service = DashboardService()
        service.run_demo_research_benchmarks()

        validations = service.validate_research_benchmarks()
        data = service.get_dashboard_data()

        self.assertTrue(validations)
        self.assertEqual(service.list_benchmark_validations(), validations)
        self.assertEqual(service.last_benchmark_validation(), validations[-1])
        self.assertEqual(data.benchmark_validations, validations)
        self.assertEqual(data.last_benchmark_validation, validations[-1])

    def test_dashboard_service_expoe_metodos_auto_replay(self) -> None:
        """Garante existencia da fachada de auto replay."""
        service = DashboardService()

        self.assertTrue(hasattr(service, "enable_replay_auto_run"))
        self.assertTrue(hasattr(service, "disable_replay_auto_run"))
        self.assertTrue(hasattr(service, "is_replay_auto_run_enabled"))
        self.assertTrue(hasattr(service, "run_demo_research_experiment"))
        self.assertTrue(hasattr(service, "list_research_experiments"))
        self.assertTrue(hasattr(service, "last_research_experiment"))
        self.assertTrue(hasattr(service, "clear_research_experiments"))
        self.assertTrue(hasattr(service, "run_demo_research_benchmarks"))
        self.assertTrue(hasattr(service, "compare_research_benchmarks"))
        self.assertTrue(hasattr(service, "last_benchmark_comparison"))
        self.assertTrue(hasattr(service, "list_research_benchmarks"))
        self.assertTrue(hasattr(service, "run_demo_parameter_grid"))
        self.assertTrue(hasattr(service, "list_parameter_grid_results"))
        self.assertTrue(hasattr(service, "best_parameter_grid_result"))
        self.assertTrue(hasattr(service, "validate_research_benchmarks"))
        self.assertTrue(hasattr(service, "list_benchmark_validations"))
        self.assertTrue(hasattr(service, "last_benchmark_validation"))

    def test_dashboard_service_expoe_research_data_quando_disponivel(
        self,
    ) -> None:
        """Garante pesquisa quantitativa via fachada do dashboard."""
        memory = MarketMemory()
        feature_snapshot = self._feature_snapshot()
        regime_analysis = self._regime_analysis()
        memory.remember(feature_snapshot, regime_analysis)
        service = DashboardService(
            market_service=MarketService(lambda: self._pattern("2026-06-25")),
            feature_snapshot=feature_snapshot,
            regime_analysis=regime_analysis,
            market_memory=memory,
        )

        data = service.get_dashboard_data()

        self.assertIsNotNone(data.research_data)
        self.assertEqual(data.research_data.similar_scenarios, 1)

    def test_dashboard_service_atualiza_configuracao(self) -> None:
        """Garante atualizacao de configuracao pela fachada."""
        service = DashboardService()

        configuration = service.update_configuration(contracts=3)

        self.assertEqual(configuration.contracts, 3)

    def test_dashboard_service_bloqueia_configuracao_invalida(self) -> None:
        """Garante propagacao da validacao do ConfigurationManager."""
        service = DashboardService()

        with self.assertRaises(ValueError):
            service.update_configuration(stop_points=-10)

    def test_dashboard_service_gerencia_presets(self) -> None:
        """Garante presets pela fachada do dashboard."""
        service = DashboardService()
        service.update_configuration(symbol="WIN")
        service.save_configuration_preset("preset")
        service.update_configuration(symbol="WDO")

        self.assertEqual(service.list_configuration_presets(), ["preset"])
        preset = service.load_configuration_preset("preset")
        self.assertEqual(preset.symbol, "WIN")

        service.delete_configuration_preset("preset")
        self.assertEqual(service.list_configuration_presets(), [])

    def test_system_service_conta_eventos(self) -> None:
        """Garante status de sistema com contagem de eventos."""
        logger = EventLogger()
        logger.handle_event("SYSTEM_STARTED", {})

        status = SystemService(event_logger=logger).get_status()

        self.assertEqual(status.event_count, 1)

    def test_dashboard_app_importa_apenas_dashboard_service(self) -> None:
        """Garante que dashboard nao acessa infraestrutura de dados."""
        imports = self._imports(Path("dashboard_app.py"))

        self.assertIn("application.dashboard_service", imports)
        self.assertNotIn("application.replay_service", imports)
        self.assertNotIn("replay.replay_engine", imports)
        self.assertNotIn("analytics.market_dna_reader", imports)
        self.assertNotIn("market.market_dna", imports)
        self.assertNotIn("sqlite3", imports)

    def test_dashboard_app_preserva_service_em_session_state(self) -> None:
        """Garante persistencia do DashboardService no Streamlit."""
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertIn("st.session_state", source)
        self.assertIn('"dashboard_service"', source)
        self.assertIn("def get_dashboard_service", source)
        self.assertIn("def _dashboard_service_valido", source)
        self.assertIn("disable_replay_auto_run", source)
        self.assertIn("run_demo_research_experiment", source)
        self.assertIn("Research Lab", source)
        self.assertIn("run_demo_research_benchmarks", source)
        self.assertIn("compare_research_benchmarks", source)
        self.assertIn("run_demo_parameter_grid", source)
        self.assertIn("validate_research_benchmarks", source)

    def test_dashboard_app_trata_replay_fields_opcionais(self) -> None:
        """Garante fallback para estados antigos do ReplayData."""
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertIn('getattr(replay_data, "feature_snapshot", None)', source)
        self.assertIn('getattr(replay_data, "regime_analysis", None)', source)

    def test_application_services_nao_importam_streamlit(self) -> None:
        """Garante que servicos de aplicacao nao dependem da UI."""
        for caminho in Path("application").glob("*.py"):
            self.assertNotIn("streamlit", self._imports(caminho), str(caminho))

    def _pattern(self, data: str) -> MarketPattern:
        return MarketPattern(
            data=data,
            horario="09:23",
            preco=5522.0,
            amplitude=50.0,
            volume=1500,
            vwap=5516.0,
            atr=51.0,
            pullback_pontos=13.0,
            direcao="ALTA",
            posicao_no_dia=0.84,
        )

    def _session(self) -> OperationSession:
        return OperationSession("2026-06-25", "09:00", "18:00")

    def _candle(self, index: int) -> Candle:
        return Candle(
            data=f"2026-06-29T0{index}:00:00+00:00",
            abertura=1.10 + index,
            maxima=1.20 + index,
            minima=1.00 + index,
            fechamento=1.15 + index,
            volume=1000 + index,
        )

    def _feature_snapshot(self) -> FeatureSnapshot:
        return FeatureSnapshot(
            momentum=10,
            average_range=10,
            highest_high=120,
            lowest_low=90,
            direction="UP",
            candles_count=2,
            trend_strength=1.0,
            volatility_level="MEDIUM",
        )

    def _regime_analysis(self) -> RegimeAnalysis:
        return RegimeAnalysis(
            regime=MarketRegime.TREND,
            confidence=0.70,
            description="Mercado com predominancia direcional.",
        )

    def _imports(self, caminho: Path) -> set[str]:
        tree = ast.parse(caminho.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
        return imports


if __name__ == "__main__":
    unittest.main()
