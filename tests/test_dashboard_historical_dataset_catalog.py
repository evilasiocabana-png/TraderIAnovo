"""Testes do catalogo historico exposto pelo DashboardService."""

import ast
from types import SimpleNamespace
import unittest
from pathlib import Path

from application.data_readiness_gate_log import (
    DataReadinessGateLog,
    InMemoryDataReadinessGateLogger,
)
from application.dashboard_service import DashboardService
from application.research_lab_service import ResearchLabService
from domain.candle import Candle
from market_data import (
    HistoricalDataset,
    HistoricalDatasetCatalog,
    HistoricalDatasetMetadata,
    HistoricalDatasetQualityRepository,
    HistoricalDatasetQualityStatus,
    HistoricalDatasetQualityValidationRecord,
    MarketDataProvider,
)


class DashboardHistoricalDatasetCatalogTest(unittest.TestCase):
    """Valida listagem de datasets historicos via fachada de dashboard."""

    def test_dashboard_service_lista_datasets_historicos(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata)
        service = DashboardService(historical_dataset_catalog=catalog)

        datasets = service.list_historical_datasets()

        self.assertIn(metadata, datasets)

    def test_dashboard_service_catalogo_default_lista_provider_estrutural(self) -> None:
        datasets = DashboardService().list_historical_datasets()

        self.assertIn("b3_petr4_1d_raw_yahoo_chart_20160628_20260628", [
            dataset.dataset_id for dataset in datasets
        ])

    def test_dashboard_service_sem_catalogo_mantem_provider_estrutural(self) -> None:
        service = DashboardService(historical_dataset_catalog=None)

        datasets = service.list_historical_datasets()

        self.assertGreaterEqual(len(datasets), 1)
        self.assertEqual(datasets[0].provider, "HistoricalDataProvider")

    def test_dashboard_service_retorna_metadados_sem_candles(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata)
        service = DashboardService(historical_dataset_catalog=catalog)

        dataset = [
            item
            for item in service.list_historical_datasets()
            if item.dataset_id == "wdo_1m_2026"
        ][0]

        self.assertEqual(dataset.dataset_id, "wdo_1m_2026")
        self.assertEqual(dataset.ativo, "WDO")
        self.assertEqual(dataset.timeframe, "1m")
        self.assertEqual(dataset.start_date, "2026-06-01")
        self.assertEqual(dataset.end_date, "2026-06-26")
        self.assertEqual(dataset.estimated_candles, 1200)
        self.assertEqual(dataset.provider, "csv")
        self.assertFalse(hasattr(dataset, "candles"))

    def test_dashboard_service_seleciona_dataset_historico_por_id(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata)
        service = DashboardService(historical_dataset_catalog=catalog)

        selected = service.select_historical_dataset("wdo_1m_2026")

        self.assertEqual(selected, metadata)
        self.assertEqual(service.get_selected_historical_dataset_id(), "wdo_1m_2026")

    def test_dashboard_service_consulta_dataset_historico_selecionado(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata)
        service = DashboardService(historical_dataset_catalog=catalog)

        service.select_historical_dataset("wdo_1m_2026")

        self.assertEqual(service.get_selected_historical_dataset(), metadata)

    def test_dashboard_service_sem_dataset_manual_retorna_padrao_certificado(self) -> None:
        service = DashboardService()

        self.assertEqual(
            service.get_selected_historical_dataset_id(),
            "b3_petr4_1d_raw_yahoo_chart_20160628_20260628",
        )
        self.assertEqual(service.get_selected_historical_dataset().ativo, "PETR4")

    def test_dashboard_service_rejeita_dataset_id_invalido(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata)
        service = DashboardService(historical_dataset_catalog=catalog)

        with self.assertRaisesRegex(ValueError, "inexistente"):
            service.select_historical_dataset("inexistente")

        self.assertEqual(
            service.get_selected_historical_dataset_id(),
            "b3_petr4_1d_raw_yahoo_chart_20160628_20260628",
        )

    def test_selecionar_dataset_nao_executa_replay_ou_research_lab(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata)
        service = DashboardService(historical_dataset_catalog=catalog)

        service.select_historical_dataset("wdo_1m_2026")

        replay_data = service.replay_service.get_replay_data()
        self.assertEqual(replay_data.total_candles, 0)
        self.assertEqual(service.research_lab_service.list_experiments(), [])

    def test_dashboard_service_carrega_replay_com_dataset_selecionado(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        provider = FakeMarketDataProvider(self._dataset())
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(self._validation_record(total_candles=2))
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=provider,
            historical_dataset_quality_repository=repository,
        )
        service.select_historical_dataset("wdo_1m_2026")

        replay_data = service.load_selected_historical_dataset_to_replay()

        self.assertEqual(provider.loaded_source, "origem_opaca")
        self.assertEqual(provider.loaded_symbol, "WDO")
        self.assertEqual(provider.loaded_timeframe, "1m")
        self.assertEqual(replay_data.total_candles, 2)
        self.assertEqual(replay_data.current_index, -1)
        self.assertFalse(replay_data.is_running)

    def test_carregar_replay_sem_dataset_manual_usa_padrao_certificado(self) -> None:
        service = DashboardService()

        replay_data = service.load_selected_historical_dataset_to_replay()

        self.assertEqual(replay_data.total_candles, 2491)

    def test_carregar_replay_com_dataset_vazio_retorna_erro_controlado(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(self._validation_record(total_candles=2))
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_dataset_quality_repository=repository,
            historical_data_provider=FakeMarketDataProvider(
                self._empty_dataset(),
                errors=["Dataset vazio."],
            ),
        )
        service.select_historical_dataset("wdo_1m_2026")

        with self.assertRaisesRegex(ValueError, "Dataset vazio."):
            service.load_selected_historical_dataset_to_replay()

    def test_dashboard_service_executa_research_com_dataset_selecionado(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        provider = FakeMarketDataProvider(self._dataset())
        research_service = ResearchLabService(market_data_provider=provider)
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(self._validation_record(total_candles=2))
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=provider,
            historical_dataset_quality_repository=repository,
            research_lab_service=research_service,
        )
        service.select_historical_dataset("wdo_1m_2026")

        experiment = service.run_selected_historical_dataset_research_experiment()

        self.assertEqual(provider.loaded_source, "origem_opaca")
        self.assertEqual(provider.loaded_symbol, "WDO")
        self.assertEqual(provider.loaded_timeframe, "1m")
        self.assertEqual(experiment.experiment_name, "wdo_1m_2026")
        self.assertEqual(experiment.strategy_name, "alpha001_iorb")
        self.assertEqual(len(service.research_lab_service.list_experiments()), 1)

    def test_research_com_dataset_sem_selecao_usa_padrao_certificado(self) -> None:
        service = DashboardService()

        experiment = service.run_selected_historical_dataset_research_experiment()

        self.assertEqual(
            experiment.experiment_name,
            "b3_petr4_1d_raw_yahoo_chart_20160628_20260628",
        )

    def test_research_com_dataset_vazio_retorna_erro_controlado(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        provider = FakeMarketDataProvider(
            self._empty_dataset(),
            errors=["Dataset vazio."],
        )
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(self._validation_record(total_candles=2))
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=provider,
            historical_dataset_quality_repository=repository,
            research_lab_service=ResearchLabService(market_data_provider=provider),
        )
        service.select_historical_dataset("wdo_1m_2026")

        with self.assertRaisesRegex(ValueError, "Dataset vazio."):
            service.run_selected_historical_dataset_research_experiment()

    def test_replay_com_dataset_invalido_e_bloqueado_pelo_gate(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(
            self._validation_record(
                quality_status="REJECTED",
                invalid_ohlc_candles=1,
                invalid_volume_candles=2,
                duplicate_timestamps=1,
                temporal_gaps=1,
                messages=["1 candle(s) com OHLC invalido"],
            )
        )
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=FakeMarketDataProvider(
                self._dataset_with_quality_issues(),
            ),
            historical_dataset_quality_repository=repository,
        )
        service.select_historical_dataset("wdo_1m_2026")

        with self.assertRaisesRegex(ValueError, "bloqueado para Replay"):
            service.load_selected_historical_dataset_to_replay()

        replay_data = service.replay_service.get_replay_data()
        self.assertEqual(replay_data.total_candles, 0)

    def test_research_com_dataset_invalido_e_bloqueado_pelo_gate(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        provider = FakeMarketDataProvider(self._dataset_with_quality_issues())
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(
            self._validation_record(
                quality_status="REJECTED",
                invalid_ohlc_candles=1,
                invalid_volume_candles=2,
                duplicate_timestamps=1,
                temporal_gaps=1,
                messages=["1 candle(s) com OHLC invalido"],
            )
        )
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=provider,
            historical_dataset_quality_repository=repository,
            research_lab_service=ResearchLabService(market_data_provider=provider),
        )
        service.select_historical_dataset("wdo_1m_2026")

        with self.assertRaisesRegex(ValueError, "bloqueado para Research Lab"):
            service.run_selected_historical_dataset_research_experiment()

        self.assertEqual(service.research_lab_service.list_experiments(), [])

    def test_gate_reporta_gaps_temporais_no_bloqueio(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(
            self._validation_record(
                quality_status="REJECTED",
                invalid_ohlc_candles=1,
                temporal_gaps=1,
                messages=["1 candle(s) com OHLC invalido"],
            )
        )
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=FakeMarketDataProvider(
                self._dataset_with_quality_issues(),
            ),
            historical_dataset_quality_repository=repository,
        )
        service.select_historical_dataset("wdo_1m_2026")

        with self.assertRaisesRegex(ValueError, "OHLC invalido"):
            service.load_selected_historical_dataset_to_replay()

    def test_dashboard_service_analisa_qualidade_do_dataset_selecionado(
        self,
    ) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        provider = FakeMarketDataProvider(self._dataset_with_quality_issues())
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=provider,
            historical_dataset_quality_repository=(
                InMemoryHistoricalDatasetQualityRepository()
            ),
        )
        service.select_historical_dataset("wdo_1m_2026")

        report = service.analyze_selected_historical_dataset_quality()

        self.assertEqual(provider.loaded_source, "origem_opaca")
        self.assertEqual(report.dataset_id, "wdo_1m_2026")
        self.assertEqual(report.total_candles, 4)
        self.assertEqual(report.start_datetime, "2026-06-26 09:00")
        self.assertEqual(report.end_datetime, "2026-06-26 09:04")
        self.assertEqual(report.invalid_ohlc_candles, 1)
        self.assertEqual(report.invalid_volume_candles, 2)
        self.assertEqual(report.temporal_gaps, 1)
        self.assertEqual(report.duplicate_timestamps, 1)

    def test_qualidade_sem_dataset_manual_usa_padrao_certificado(self) -> None:
        service = DashboardService()

        report = service.analyze_selected_historical_dataset_quality()

        self.assertEqual(report.dataset_id, "b3_petr4_1d_raw_yahoo_chart_20160628_20260628")
        self.assertEqual(report.total_candles, 2491)

    def test_qualidade_com_dataset_vazio_retorna_erro_controlado(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=FakeMarketDataProvider(
                self._empty_dataset(),
                errors=["Dataset vazio."],
            ),
            historical_dataset_quality_repository=(
                InMemoryHistoricalDatasetQualityRepository()
            ),
        )
        service.select_historical_dataset("wdo_1m_2026")

        with self.assertRaisesRegex(ValueError, "Dataset vazio."):
            service.analyze_selected_historical_dataset_quality()

    def test_dashboard_service_persiste_status_de_qualidade(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        repository = InMemoryHistoricalDatasetQualityRepository()
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=FakeMarketDataProvider(self._dataset()),
            historical_dataset_quality_repository=repository,
        )
        service.select_historical_dataset("wdo_1m_2026")

        service.analyze_selected_historical_dataset_quality()

        status = repository.get("wdo_1m_2026")
        self.assertIsNotNone(status)
        self.assertEqual(status.dataset_id, "wdo_1m_2026")
        self.assertEqual(status.ativo, "WDO")
        self.assertEqual(status.timeframe, "1m")
        self.assertEqual(status.provider, "csv")
        self.assertEqual(status.total_candles, 2)
        self.assertEqual(status.quality_status, "APPROVED")
        self.assertEqual(status.errors, [])
        self.assertNotEqual(status.last_validated_at, "")

    def test_dashboard_service_consulta_ultimo_status_persistido(self) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.save(
            HistoricalDatasetQualityStatus(
                dataset_id="wdo_1m_2026",
                ativo="WDO",
                timeframe="1m",
                provider="csv",
                start_date="2026-06-26 09:00",
                end_date="2026-06-26 09:01",
                total_candles=2,
                quality_status="APPROVED",
                errors=[],
                last_validated_at="2026-06-26T18:00:00",
            )
        )
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_dataset_quality_repository=repository,
        )
        service.select_historical_dataset("wdo_1m_2026")

        status = service.get_selected_historical_dataset_quality_status()

        self.assertIsNotNone(status)
        self.assertEqual(status.quality_status, "APPROVED")

    def test_dashboard_service_persiste_status_rejeitado_antes_do_bloqueio(
        self,
    ) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(self._validation_record(total_candles=2))
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=FakeMarketDataProvider(
                self._dataset_with_quality_issues(),
            ),
            historical_dataset_quality_repository=repository,
        )
        service.select_historical_dataset("wdo_1m_2026")

        with self.assertRaisesRegex(ValueError, "gate de qualidade"):
            service.load_selected_historical_dataset_to_replay()

        status = repository.get("wdo_1m_2026")
        self.assertIsNotNone(status)
        self.assertEqual(status.quality_status, "REJECTED")
        self.assertIn("1 candle(s) com OHLC invalido", status.errors)
        self.assertIn("2 candle(s) com volume invalido", status.errors)
        self.assertIn("1 timestamp(s) duplicado(s)", status.errors)
        self.assertIn("1 gap(s) temporal(is) detectado(s)", status.errors)

    def test_dashboard_service_registra_historico_a_cada_validacao(
        self,
    ) -> None:
        catalog = HistoricalDatasetCatalog()
        metadata = self._metadata()
        catalog.register_dataset(metadata, source="origem_opaca")
        repository = InMemoryHistoricalDatasetQualityRepository()
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=FakeMarketDataProvider(self._dataset()),
            historical_dataset_quality_repository=repository,
        )
        service.select_historical_dataset("wdo_1m_2026")

        service.analyze_selected_historical_dataset_quality()
        service.analyze_selected_historical_dataset_quality()

        history = service.list_historical_dataset_quality_validations(
            "wdo_1m_2026"
        )
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].dataset_id, "wdo_1m_2026")
        self.assertEqual(history[0].quality_status, "APPROVED")
        self.assertEqual(history[0].total_candles, 2)
        self.assertEqual(history[0].invalid_ohlc_candles, 0)
        self.assertEqual(history[0].invalid_volume_candles, 0)
        self.assertEqual(history[0].temporal_gaps, 0)
        self.assertEqual(history[0].duplicate_timestamps, 0)
        self.assertEqual(history[0].messages, [])

    def test_dashboard_service_consulta_historico_por_dataset_id(self) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(
            HistoricalDatasetQualityValidationRecord(
                dataset_id="wdo_1m_2026",
                validated_at="2026-06-26T18:00:00",
                quality_status="APPROVED",
                total_candles=2,
                invalid_ohlc_candles=0,
                invalid_volume_candles=0,
                temporal_gaps=0,
                duplicate_timestamps=0,
                messages=[],
            )
        )
        repository.append_validation(
            HistoricalDatasetQualityValidationRecord(
                dataset_id="outro_dataset",
                validated_at="2026-06-26T18:01:00",
                quality_status="REJECTED",
                total_candles=1,
                invalid_ohlc_candles=1,
                invalid_volume_candles=0,
                temporal_gaps=0,
                duplicate_timestamps=0,
                messages=["1 candle(s) com OHLC invalido"],
            )
        )
        service = DashboardService(
            historical_dataset_quality_repository=repository,
        )

        history = service.list_historical_dataset_quality_validations(
            "wdo_1m_2026"
        )

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].dataset_id, "wdo_1m_2026")

    def test_dashboard_service_resume_saude_com_aprovados_reprovados_e_sem_validacao(
        self,
    ) -> None:
        catalog = HistoricalDatasetCatalog()
        approved_metadata = self._metadata(
            dataset_id="dataset_aprovado",
        )
        rejected_metadata = self._metadata(
            dataset_id="dataset_reprovado",
        )
        unvalidated_metadata = self._metadata(
            dataset_id="dataset_sem_validacao",
        )
        catalog.register_dataset(approved_metadata)
        catalog.register_dataset(rejected_metadata)
        catalog.register_dataset(unvalidated_metadata)
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.save(
            self._quality_status(
                dataset_id="dataset_aprovado",
                quality_status="APPROVED",
                last_validated_at="2026-06-26T18:00:00",
            )
        )
        repository.save(
            self._quality_status(
                dataset_id="dataset_reprovado",
                quality_status="REJECTED",
                last_validated_at="2026-06-26T18:10:00",
            )
        )
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_dataset_quality_repository=repository,
        )

        summary = service.get_historical_dataset_health_summary()

        self.assertEqual(summary.total_datasets, 5)
        self.assertEqual(summary.total_validated, 3)
        self.assertEqual(summary.total_approved, 2)
        self.assertEqual(summary.total_rejected, 1)
        self.assertEqual(summary.total_unvalidated, 2)
        self.assertEqual(summary.last_validation_at, "2026-06-28T00:00:00")

    def test_dashboard_service_resume_saude_sem_datasets(self) -> None:
        service = DashboardService(
            historical_dataset_quality_repository=(
                InMemoryHistoricalDatasetQualityRepository()
            )
        )

        summary = service.get_historical_dataset_health_summary()

        self.assertEqual(summary.total_datasets, 2)
        self.assertEqual(summary.total_validated, 1)
        self.assertEqual(summary.total_approved, 1)
        self.assertEqual(summary.total_rejected, 0)
        self.assertEqual(summary.total_unvalidated, 1)
        self.assertEqual(summary.last_validation_at, "2026-06-28T00:00:00")

    def test_dashboard_service_resume_ignora_status_fora_do_catalogo(
        self,
    ) -> None:
        catalog = HistoricalDatasetCatalog()
        catalog.register_dataset(self._metadata(dataset_id="dataset_catalogado"))
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.save(
            self._quality_status(
                dataset_id="dataset_nao_catalogado",
                quality_status="APPROVED",
            )
        )
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_dataset_quality_repository=repository,
        )

        summary = service.get_historical_dataset_health_summary()

        self.assertEqual(summary.total_datasets, 3)
        self.assertEqual(summary.total_validated, 1)
        self.assertEqual(summary.total_unvalidated, 2)

    def test_readiness_sem_validacao_retorna_not_validated(self) -> None:
        service = self._service_for_readiness()

        readiness = service.get_selected_historical_dataset_readiness()

        self.assertEqual(readiness.dataset_id, "wdo_1m_2026")
        self.assertEqual(readiness.readiness, "NOT_VALIDATED")
        self.assertIn("ainda nao validado", readiness.reasons[0])

    def test_readiness_com_erro_critico_retorna_not_ready(self) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(
            self._validation_record(
                quality_status="REJECTED",
                invalid_ohlc_candles=1,
                messages=["1 candle(s) com OHLC invalido"],
            )
        )
        service = self._service_for_readiness(repository)

        readiness = service.get_selected_historical_dataset_readiness()

        self.assertEqual(readiness.readiness, "NOT_READY")
        self.assertIn("OHLC invalido", "; ".join(readiness.reasons))

    def test_readiness_valido_com_um_candle_retorna_ready_for_replay(self) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(self._validation_record(total_candles=1))
        service = self._service_for_readiness(repository)

        readiness = service.get_selected_historical_dataset_readiness()

        self.assertEqual(readiness.readiness, "READY_FOR_REPLAY")
        self.assertIn("Research Lab", readiness.reasons[0])

    def test_readiness_valido_com_gaps_retorna_ready_for_research(self) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(self._validation_record(temporal_gaps=2))
        service = self._service_for_readiness(repository)

        readiness = service.get_selected_historical_dataset_readiness()

        self.assertEqual(readiness.readiness, "READY_FOR_RESEARCH")
        self.assertIn("gap", readiness.reasons[0])

    def test_readiness_valido_sem_gaps_retorna_ready_for_ambos(self) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.append_validation(self._validation_record(total_candles=2))
        service = self._service_for_readiness(repository)

        readiness = service.get_selected_historical_dataset_readiness()

        self.assertEqual(readiness.readiness, "READY_FOR_REPLAY_AND_RESEARCH")
        self.assertEqual(readiness.reasons, [])

    def test_readiness_sem_dataset_manual_usa_padrao_certificado(
        self,
    ) -> None:
        service = DashboardService(
            historical_dataset_quality_repository=(
                InMemoryHistoricalDatasetQualityRepository()
            )
        )

        readiness = service.get_selected_historical_dataset_readiness()

        self.assertEqual(readiness.readiness, "READY_FOR_REPLAY_AND_RESEARCH")

    def test_gate_readiness_not_validated_bloqueia_replay_e_research(
        self,
    ) -> None:
        logger = InMemoryDataReadinessGateLogger()
        service = self._service_for_dataset_execution(
            InMemoryHistoricalDatasetQualityRepository(),
            logger,
        )

        with self.assertRaisesRegex(ValueError, "NOT_VALIDATED"):
            service.load_selected_historical_dataset_to_replay()
        with self.assertRaisesRegex(ValueError, "NOT_VALIDATED"):
            service.run_selected_historical_dataset_research_experiment()
        logs = service.list_data_readiness_gate_logs()
        self.assertEqual([log.decision for log in logs], ["BLOCKED", "BLOCKED"])
        self.assertEqual([log.requested_action for log in logs], ["REPLAY", "RESEARCH"])
        self.assertEqual(logs[0].readiness_status, "NOT_VALIDATED")

    def test_gate_readiness_not_ready_bloqueia_replay_e_research(self) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        logger = InMemoryDataReadinessGateLogger()
        repository.append_validation(
            self._validation_record(
                quality_status="REJECTED",
                invalid_ohlc_candles=1,
                messages=["1 candle(s) com OHLC invalido"],
            )
        )
        service = self._service_for_dataset_execution(repository, logger)

        with self.assertRaisesRegex(ValueError, "NOT_READY"):
            service.load_selected_historical_dataset_to_replay()
        with self.assertRaisesRegex(ValueError, "NOT_READY"):
            service.run_selected_historical_dataset_research_experiment()
        logs = service.list_data_readiness_gate_logs()
        self.assertEqual([log.decision for log in logs], ["BLOCKED", "BLOCKED"])
        self.assertEqual(logs[0].readiness_status, "NOT_READY")
        self.assertIn("OHLC invalido", "; ".join(logs[0].reasons))

    def test_gate_readiness_ready_for_replay_libera_apenas_replay(self) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        logger = InMemoryDataReadinessGateLogger()
        repository.append_validation(self._validation_record(total_candles=1))
        service = self._service_for_dataset_execution(repository, logger)

        with self.assertRaisesRegex(ValueError, "READY_FOR_REPLAY"):
            service.run_selected_historical_dataset_research_experiment()
        replay_data = service.load_selected_historical_dataset_to_replay()

        self.assertEqual(replay_data.total_candles, 2)
        logs = service.list_data_readiness_gate_logs()
        self.assertEqual([log.decision for log in logs], ["BLOCKED", "ALLOWED"])
        self.assertEqual([log.requested_action for log in logs], ["RESEARCH", "REPLAY"])

    def test_gate_readiness_ready_for_research_libera_apenas_research(self) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        logger = InMemoryDataReadinessGateLogger()
        repository.append_validation(self._validation_record(temporal_gaps=1))
        service = self._service_for_dataset_execution(repository, logger)

        with self.assertRaisesRegex(ValueError, "READY_FOR_RESEARCH"):
            service.load_selected_historical_dataset_to_replay()
        experiment = service.run_selected_historical_dataset_research_experiment()

        self.assertEqual(experiment.experiment_name, "wdo_1m_2026")
        logs = service.list_data_readiness_gate_logs()
        self.assertEqual([log.decision for log in logs], ["BLOCKED", "ALLOWED"])
        self.assertEqual([log.requested_action for log in logs], ["REPLAY", "RESEARCH"])

    def test_gate_readiness_ready_for_ambos_libera_replay_e_research(self) -> None:
        repository = InMemoryHistoricalDatasetQualityRepository()
        logger = InMemoryDataReadinessGateLogger()
        repository.append_validation(self._validation_record(total_candles=2))
        service = self._service_for_dataset_execution(repository, logger)

        replay_data = service.load_selected_historical_dataset_to_replay()
        experiment = service.run_selected_historical_dataset_research_experiment()

        self.assertEqual(replay_data.total_candles, 2)
        self.assertEqual(experiment.experiment_name, "wdo_1m_2026")
        logs = service.list_data_readiness_gate_logs()
        self.assertEqual([log.decision for log in logs], ["ALLOWED", "ALLOWED"])
        self.assertEqual([log.requested_action for log in logs], ["REPLAY", "RESEARCH"])

    def test_metricas_gate_sem_historico_retornam_valores_seguros(self) -> None:
        service = DashboardService(
            data_readiness_gate_logger=InMemoryDataReadinessGateLogger(),
        )

        metrics = service.get_data_readiness_gate_metrics()

        self.assertEqual(metrics.total_evaluations, 0)
        self.assertEqual(metrics.total_allowed, 0)
        self.assertEqual(metrics.total_blocked, 0)
        self.assertEqual(metrics.total_replay_evaluations, 0)
        self.assertEqual(metrics.total_research_evaluations, 0)
        self.assertIsNone(metrics.last_blocked_dataset_id)
        self.assertIsNone(metrics.last_block_reason)
        self.assertIsNone(metrics.last_evaluation_at)

    def test_metricas_gate_com_allowed(self) -> None:
        logger = InMemoryDataReadinessGateLogger()
        logger.log(
            self._gate_log(
                requested_action="REPLAY",
                decision="ALLOWED",
                evaluated_at="2026-06-26T18:00:00",
            )
        )
        service = DashboardService(data_readiness_gate_logger=logger)

        metrics = service.get_data_readiness_gate_metrics()

        self.assertEqual(metrics.total_evaluations, 1)
        self.assertEqual(metrics.total_allowed, 1)
        self.assertEqual(metrics.total_blocked, 0)
        self.assertEqual(metrics.total_replay_evaluations, 1)
        self.assertEqual(metrics.total_research_evaluations, 0)
        self.assertIsNone(metrics.last_blocked_dataset_id)
        self.assertIsNone(metrics.last_block_reason)
        self.assertEqual(metrics.last_evaluation_at, "2026-06-26T18:00:00")

    def test_metricas_gate_com_blocked(self) -> None:
        logger = InMemoryDataReadinessGateLogger()
        logger.log(
            self._gate_log(
                requested_action="RESEARCH",
                decision="BLOCKED",
                evaluated_at="2026-06-26T18:10:00",
                reasons=["Dataset historico ainda nao validado."],
            )
        )
        service = DashboardService(data_readiness_gate_logger=logger)

        metrics = service.get_data_readiness_gate_metrics()

        self.assertEqual(metrics.total_evaluations, 1)
        self.assertEqual(metrics.total_allowed, 0)
        self.assertEqual(metrics.total_blocked, 1)
        self.assertEqual(metrics.total_replay_evaluations, 0)
        self.assertEqual(metrics.total_research_evaluations, 1)
        self.assertEqual(metrics.last_blocked_dataset_id, "wdo_1m_2026")
        self.assertEqual(
            metrics.last_block_reason,
            "Dataset historico ainda nao validado.",
        )
        self.assertEqual(metrics.last_evaluation_at, "2026-06-26T18:10:00")

    def test_metricas_gate_com_historico_misto(self) -> None:
        logger = InMemoryDataReadinessGateLogger()
        logger.log(
            self._gate_log(
                requested_action="REPLAY",
                decision="ALLOWED",
                evaluated_at="2026-06-26T18:00:00",
            )
        )
        logger.log(
            self._gate_log(
                dataset_id="dataset_bloqueado_antigo",
                requested_action="RESEARCH",
                decision="BLOCKED",
                evaluated_at="2026-06-26T18:05:00",
                reasons=["Motivo antigo"],
            )
        )
        logger.log(
            self._gate_log(
                dataset_id="dataset_bloqueado_novo",
                requested_action="REPLAY",
                decision="BLOCKED",
                evaluated_at="2026-06-26T18:15:00",
                reasons=["Motivo novo"],
            )
        )
        service = DashboardService(data_readiness_gate_logger=logger)

        metrics = service.get_data_readiness_gate_metrics()

        self.assertEqual(metrics.total_evaluations, 3)
        self.assertEqual(metrics.total_allowed, 1)
        self.assertEqual(metrics.total_blocked, 2)
        self.assertEqual(metrics.total_replay_evaluations, 2)
        self.assertEqual(metrics.total_research_evaluations, 1)
        self.assertEqual(metrics.last_blocked_dataset_id, "dataset_bloqueado_novo")
        self.assertEqual(metrics.last_block_reason, "Motivo novo")
        self.assertEqual(metrics.last_evaluation_at, "2026-06-26T18:15:00")

    def test_metricas_por_provider_sem_datasets_retornam_valores_seguros(
        self,
    ) -> None:
        service = DashboardService(
            historical_dataset_quality_repository=(
                InMemoryHistoricalDatasetQualityRepository()
            ),
            data_readiness_gate_logger=InMemoryDataReadinessGateLogger(),
        )

        metrics = service.get_historical_provider_metrics()

        self.assertIn("historicaldataprovider", metrics)
        self.assertEqual(metrics["historicaldataprovider"]["total_datasets"], 2)
        self.assertEqual(metrics["historicaldataprovider"]["validated_datasets"], 1)
        self.assertEqual(metrics["historicaldataprovider"]["approved_datasets"], 1)
        self.assertEqual(metrics["historicaldataprovider"]["not_validated_datasets"], 1)
        for provider, metric in metrics.items():
            if provider == "historicaldataprovider":
                continue
            self.assertEqual(metric["total_datasets"], 0)
            self.assertEqual(metric["validated_datasets"], 0)
            self.assertEqual(metric["approved_datasets"], 0)
            self.assertEqual(metric["rejected_datasets"], 0)
            self.assertEqual(metric["not_validated_datasets"], 0)
            self.assertEqual(metric["gate_evaluations"], 0)
            self.assertEqual(metric["allowed"], 0)
            self.assertEqual(metric["blocked"], 0)
            self.assertIsNone(metric["last_validation_at"])
            self.assertIsNone(metric["last_gate_evaluation_at"])

    def test_metricas_por_provider_com_csv_parquet_duckdb_e_historico_misto(
        self,
    ) -> None:
        catalog = HistoricalDatasetCatalog()
        catalog.register_dataset(
            self._metadata(dataset_id="csv_aprovado", provider="csv")
        )
        catalog.register_dataset(
            self._metadata(dataset_id="csv_sem_validacao", provider="csv")
        )
        catalog.register_dataset(
            self._metadata(dataset_id="parquet_reprovado", provider="parquet")
        )
        catalog.register_dataset(
            self._metadata(dataset_id="parquet_sem_validacao", provider="parquet")
        )
        catalog.register_dataset(
            self._metadata(dataset_id="duckdb_aprovado", provider="duckdb")
        )
        catalog.register_dataset(
            self._metadata(dataset_id="duckdb_sem_validacao", provider="duckdb")
        )
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.save(
            self._quality_status(
                dataset_id="csv_aprovado",
                quality_status="APPROVED",
                provider="csv",
                last_validated_at="2026-06-26T18:00:00",
            )
        )
        repository.save(
            self._quality_status(
                dataset_id="parquet_reprovado",
                quality_status="REJECTED",
                provider="parquet",
                last_validated_at="2026-06-26T18:10:00",
            )
        )
        repository.save(
            self._quality_status(
                dataset_id="duckdb_aprovado",
                quality_status="APPROVED",
                provider="duckdb",
                last_validated_at="2026-06-26T18:40:00",
            )
        )
        logger = InMemoryDataReadinessGateLogger()
        logger.log(
            self._gate_log(
                dataset_id="csv_aprovado",
                requested_action="REPLAY",
                decision="ALLOWED",
                evaluated_at="2026-06-26T18:20:00",
                provider="csv",
            )
        )
        logger.log(
            self._gate_log(
                dataset_id="csv_aprovado",
                requested_action="RESEARCH",
                decision="BLOCKED",
                evaluated_at="2026-06-26T18:21:00",
                provider="csv",
            )
        )
        logger.log(
            self._gate_log(
                dataset_id="parquet_reprovado",
                requested_action="REPLAY",
                decision="BLOCKED",
                evaluated_at="2026-06-26T18:30:00",
                provider="parquet",
            )
        )
        logger.log(
            self._gate_log(
                dataset_id="parquet_reprovado",
                requested_action="RESEARCH",
                decision="ALLOWED",
                evaluated_at="2026-06-26T18:31:00",
                provider="parquet",
            )
        )
        logger.log(
            self._gate_log(
                dataset_id="duckdb_aprovado",
                requested_action="REPLAY",
                decision="ALLOWED",
                evaluated_at="2026-06-26T18:50:00",
                provider="duckdb",
            )
        )
        logger.log(
            self._gate_log(
                dataset_id="duckdb_aprovado",
                requested_action="RESEARCH",
                decision="BLOCKED",
                evaluated_at="2026-06-26T18:51:00",
                provider="duckdb",
            )
        )
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_dataset_quality_repository=repository,
            data_readiness_gate_logger=logger,
        )

        metrics = service.get_historical_provider_metrics()

        csv_metrics = metrics["csv"]
        self.assertEqual(csv_metrics["total_datasets"], 2)
        self.assertEqual(csv_metrics["validated_datasets"], 1)
        self.assertEqual(csv_metrics["approved_datasets"], 1)
        self.assertEqual(csv_metrics["rejected_datasets"], 0)
        self.assertEqual(csv_metrics["not_validated_datasets"], 1)
        self.assertEqual(csv_metrics["gate_evaluations"], 2)
        self.assertEqual(csv_metrics["allowed"], 1)
        self.assertEqual(csv_metrics["blocked"], 1)
        self.assertEqual(csv_metrics["last_validation_at"], "2026-06-26T18:00:00")
        self.assertEqual(
            csv_metrics["last_gate_evaluation_at"],
            "2026-06-26T18:21:00",
        )

        parquet_metrics = metrics["parquet"]
        self.assertEqual(parquet_metrics["total_datasets"], 2)
        self.assertEqual(parquet_metrics["validated_datasets"], 1)
        self.assertEqual(parquet_metrics["approved_datasets"], 0)
        self.assertEqual(parquet_metrics["rejected_datasets"], 1)
        self.assertEqual(parquet_metrics["not_validated_datasets"], 1)
        self.assertEqual(parquet_metrics["gate_evaluations"], 2)
        self.assertEqual(parquet_metrics["allowed"], 1)
        self.assertEqual(parquet_metrics["blocked"], 1)
        self.assertEqual(
            parquet_metrics["last_validation_at"],
            "2026-06-26T18:10:00",
        )
        self.assertEqual(
            parquet_metrics["last_gate_evaluation_at"],
            "2026-06-26T18:31:00",
        )

        duckdb_metrics = metrics["duckdb"]
        self.assertEqual(duckdb_metrics["total_datasets"], 2)
        self.assertEqual(duckdb_metrics["validated_datasets"], 1)
        self.assertEqual(duckdb_metrics["approved_datasets"], 1)
        self.assertEqual(duckdb_metrics["rejected_datasets"], 0)
        self.assertEqual(duckdb_metrics["not_validated_datasets"], 1)
        self.assertEqual(duckdb_metrics["gate_evaluations"], 2)
        self.assertEqual(duckdb_metrics["allowed"], 1)
        self.assertEqual(duckdb_metrics["blocked"], 1)
        self.assertEqual(
            duckdb_metrics["last_validation_at"],
            "2026-06-26T18:40:00",
        )
        self.assertEqual(
            duckdb_metrics["last_gate_evaluation_at"],
            "2026-06-26T18:51:00",
        )

    def test_metricas_por_provider_ignoram_status_fora_do_catalogo(
        self,
    ) -> None:
        catalog = HistoricalDatasetCatalog()
        catalog.register_dataset(
            self._metadata(dataset_id="csv_catalogado", provider="csv")
        )
        repository = InMemoryHistoricalDatasetQualityRepository()
        repository.save(
            self._quality_status(
                dataset_id="csv_nao_catalogado",
                quality_status="APPROVED",
                provider="csv",
            )
        )
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_dataset_quality_repository=repository,
        )

        metrics = service.get_historical_provider_metrics()

        self.assertEqual(metrics["csv"]["total_datasets"], 1)
        self.assertEqual(metrics["csv"]["validated_datasets"], 0)
        self.assertEqual(metrics["csv"]["not_validated_datasets"], 1)

    def test_dashboard_app_nao_importa_catalogo_provider_registry_ou_adapter(
        self,
    ) -> None:
        imports = self._imports(Path("dashboard_app.py"))

        self.assertIn("application.dashboard_service", imports)
        self.assertNotIn("market_data", imports)
        self.assertNotIn("market_data.historical_dataset_catalog", imports)
        self.assertNotIn("market_data.historical_data_provider", imports)
        self.assertNotIn("market_data.historical_data_source_registry", imports)
        self.assertNotIn("market_data.csv_historical_data_source", imports)

    def test_dashboard_app_chama_apenas_metodos_existentes_no_dashboard_service(
        self,
    ) -> None:
        source = Path("dashboard_app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        service_calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "service"
        }
        service_methods = {
            name
            for name in dir(DashboardService)
            if not name.startswith("_")
            and callable(getattr(DashboardService, name, None))
        }

        self.assertEqual(service_calls - service_methods, set())

    def test_dashboard_tabela_metricas_provider_exibe_csv_parquet_e_duckdb(
        self,
    ) -> None:
        from dashboard_app import _historical_provider_metrics_table

        metrics = [
            self._provider_metric("csv"),
            self._provider_metric("parquet"),
            self._provider_metric("duckdb"),
        ]

        rows = _historical_provider_metrics_table(metrics)

        self.assertEqual(
            [row["provider"] for row in rows],
            ["csv", "parquet", "duckdb"],
        )
        for row in rows:
            with self.subTest(provider=row["provider"]):
                self.assertIn("datasets_catalogados", row)
                self.assertIn("datasets_validados", row)
                self.assertIn("datasets_aprovados", row)
                self.assertIn("datasets_reprovados", row)
                self.assertIn("datasets_sem_validacao", row)
                self.assertIn("avaliacoes_gate", row)
                self.assertIn("allowed", row)
                self.assertIn("blocked", row)
                self.assertIn("ultima_validacao", row)
                self.assertIn("ultima_avaliacao_gate", row)

    def test_dashboard_tabela_metricas_provider_aceita_dicionario_seguro(
        self,
    ) -> None:
        from dashboard_app import _historical_provider_metrics_table

        metrics = {
            "csv": self._provider_metric_dict(),
            "parquet": self._provider_metric_dict(),
            "duckdb": self._provider_metric_dict(),
        }

        rows = _historical_provider_metrics_table(metrics)

        self.assertEqual(
            [row["provider"] for row in rows],
            ["csv", "parquet", "duckdb"],
        )
        self.assertEqual(rows[0]["datasets_catalogados"], 1)
        self.assertEqual(rows[0]["datasets_validados"], 1)
        self.assertEqual(rows[0]["datasets_aprovados"], 1)
        self.assertEqual(rows[0]["datasets_reprovados"], 0)
        self.assertEqual(rows[0]["datasets_sem_validacao"], 0)
        self.assertEqual(rows[0]["avaliacoes_gate"], 2)
        self.assertEqual(rows[0]["allowed"], 1)
        self.assertEqual(rows[0]["blocked"], 1)

    def test_dashboard_app_exibe_secao_de_dataset_historico_via_service(
        self,
    ) -> None:
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertIn("Datasets historicos", source)
        self.assertIn("Dataset historico", source)
        self.assertIn("Selecionar Dataset Historico", source)
        self.assertIn("Dataset ativo", source)
        self.assertIn("Carregar Replay do Dataset", source)
        self.assertIn("Executar Research do Dataset", source)
        self.assertIn("Analisar Qualidade do Dataset", source)
        self.assertIn("Qualidade do dataset historico", source)
        self.assertIn("Historico de qualidade do dataset", source)
        self.assertIn("Saude geral dos datasets historicos", source)
        self.assertIn("Comparacao de providers historicos", source)
        self.assertIn("Data Readiness Gate", source)
        self.assertIn("Auditoria do Data Readiness Gate", source)
        self.assertIn("Metricas do Data Readiness Gate", source)
        self.assertIn("Readiness", source)
        self.assertIn("Avaliacoes", source)
        self.assertIn("Allowed", source)
        self.assertIn("Blocked", source)
        self.assertIn("Replay", source)
        self.assertIn("Research", source)
        self.assertIn("Ultima avaliacao", source)
        self.assertIn("Ultimo dataset bloqueado", source)
        self.assertIn("Ultimo motivo de bloqueio", source)
        self.assertIn("datasets_catalogados", source)
        self.assertIn("datasets_validados", source)
        self.assertIn("datasets_aprovados", source)
        self.assertIn("datasets_reprovados", source)
        self.assertIn("datasets_sem_validacao", source)
        self.assertIn("avaliacoes_gate", source)
        self.assertIn("ultima_validacao", source)
        self.assertIn("ultima_avaliacao_gate", source)
        self.assertIn("Selecione um dataset historico para ver a prontidao", source)
        self.assertIn("Selecione um dataset historico para ver a auditoria", source)
        self.assertIn("Nenhum motivo restritivo registrado", source)
        self.assertIn("Nenhuma decisao do Data Readiness Gate registrada", source)
        self.assertIn("_historical_dataset_readiness_reasons_table", source)
        self.assertIn("_data_readiness_gate_logs_table(logs)", source)
        self.assertIn('"motivo": reason', source)
        self.assertIn('"dataset_id": log.dataset_id', source)
        self.assertIn('"avaliacao": log.evaluated_at', source)
        self.assertIn('"acao": log.requested_action', source)
        self.assertIn('"readiness": log.readiness_status', source)
        self.assertIn('"decisao": log.decision', source)
        self.assertIn('"motivos": "; ".join(log.reasons)', source)
        self.assertIn("Catalogados", source)
        self.assertIn("Validados", source)
        self.assertIn("Aprovados", source)
        self.assertIn("Reprovados", source)
        self.assertIn("Sem validacao", source)
        self.assertIn("Ultima validacao", source)
        self.assertIn("Selecione um dataset historico", source)
        self.assertIn("Nenhuma validacao de qualidade registrada", source)
        self.assertIn("service.list_historical_datasets()", source)
        self.assertIn("service.select_historical_dataset", source)
        self.assertIn("service.get_selected_historical_dataset()", source)
        self.assertIn("service.get_historical_dataset_health_summary()", source)
        self.assertIn("service.get_selected_historical_dataset_readiness()", source)
        self.assertIn("service.get_data_readiness_gate_metrics()", source)
        self.assertIn("service.get_historical_provider_metrics()", source)
        self.assertIn("service.list_data_readiness_gate_logs()", source)
        self.assertIn("service.load_selected_historical_dataset_to_replay()", source)
        self.assertIn(
            "service.run_selected_historical_dataset_research_experiment()",
            source,
        )
        self.assertIn("service.analyze_selected_historical_dataset_quality()", source)
        self.assertIn(
            "service.list_historical_dataset_quality_validations",
            source,
        )
        self.assertIn("_historical_provider_metrics_table(metrics)", source)
        self.assertIn('"provider": provider', source)
        self.assertIn('"datasets_catalogados": _metric_value(', source)
        self.assertIn('"validated_datasets"', source)
        self.assertIn('"approved_datasets"', source)
        self.assertIn('"rejected_datasets"', source)
        self.assertIn('"not_validated_datasets"', source)
        self.assertIn('"gate_evaluations"', source)
        self.assertIn('"allowed"', source)
        self.assertIn('"blocked"', source)
        self.assertIn("_historical_dataset_quality_history_table(history)", source)
        self.assertIn('"validacao": record.validated_at', source)
        self.assertIn('"status": record.quality_status', source)
        self.assertIn('"total_candles": record.total_candles', source)
        self.assertIn('"ohlc_invalidos": record.invalid_ohlc_candles', source)
        self.assertIn('"volumes_invalidos": record.invalid_volume_candles', source)
        self.assertIn('"gaps": record.temporal_gaps', source)
        self.assertIn(
            '"timestamps_duplicados": record.duplicate_timestamps',
            source,
        )
        self.assertIn('"mensagens": "; ".join(record.messages)', source)
        self.assertIn("except ValueError as exc", source)
        self.assertIn("st.error(str(exc))", source)
        self.assertNotIn("HistoricalDatasetCatalog", source)
        self.assertNotIn("HistoricalDataProvider", source)
        self.assertNotIn("HistoricalDatasetQualityRepository", source)
        self.assertNotIn("JsonHistoricalDatasetQualityRepository", source)
        self.assertNotIn("DataReadinessGateLog", source)
        self.assertNotIn("DataReadinessGateLogger", source)
        self.assertNotIn("maxima >= minima", source)

    def test_dashboard_app_nao_acessa_csv_arquivo_path_ou_pandas(self) -> None:
        imports = self._imports(Path("dashboard_app.py"))
        source = Path("dashboard_app.py").read_text(encoding="utf-8")

        self.assertNotIn("pathlib", imports)
        self.assertNotIn("pandas", imports)
        self.assertNotIn("csv", imports)
        self.assertNotIn("open(", source)
        self.assertNotIn("read_csv", source)
        self.assertNotIn("st.file_uploader", source)

    def _metadata(
        self,
        dataset_id: str = "wdo_1m_2026",
        provider: str = "csv",
    ) -> HistoricalDatasetMetadata:
        return HistoricalDatasetMetadata(
            dataset_id=dataset_id,
            ativo="WDO",
            timeframe="1m",
            start_date="2026-06-01",
            end_date="2026-06-26",
            estimated_candles=1200,
            provider=provider,
        )

    def _quality_status(
        self,
        dataset_id: str,
        quality_status: str,
        provider: str = "csv",
        last_validated_at: str = "2026-06-26T18:00:00",
    ) -> HistoricalDatasetQualityStatus:
        return HistoricalDatasetQualityStatus(
            dataset_id=dataset_id,
            ativo="WDO",
            timeframe="1m",
            provider=provider,
            start_date="2026-06-26 09:00",
            end_date="2026-06-26 09:01",
            total_candles=2,
            quality_status=quality_status,
            errors=[],
            last_validated_at=last_validated_at,
        )

    def _validation_record(
        self,
        dataset_id: str = "wdo_1m_2026",
        quality_status: str = "APPROVED",
        total_candles: int = 2,
        invalid_ohlc_candles: int = 0,
        invalid_volume_candles: int = 0,
        temporal_gaps: int = 0,
        duplicate_timestamps: int = 0,
        messages: list[str] | None = None,
    ) -> HistoricalDatasetQualityValidationRecord:
        return HistoricalDatasetQualityValidationRecord(
            dataset_id=dataset_id,
            validated_at="2026-06-26T18:00:00",
            quality_status=quality_status,
            total_candles=total_candles,
            invalid_ohlc_candles=invalid_ohlc_candles,
            invalid_volume_candles=invalid_volume_candles,
            temporal_gaps=temporal_gaps,
            duplicate_timestamps=duplicate_timestamps,
            messages=list(messages or []),
        )

    def _service_for_readiness(
        self,
        repository: HistoricalDatasetQualityRepository | None = None,
    ) -> DashboardService:
        catalog = HistoricalDatasetCatalog()
        catalog.register_dataset(self._metadata(), source="origem_opaca")
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_dataset_quality_repository=(
                repository or InMemoryHistoricalDatasetQualityRepository()
            ),
        )
        service.select_historical_dataset("wdo_1m_2026")
        return service

    def _service_for_dataset_execution(
        self,
        repository: HistoricalDatasetQualityRepository,
        logger: InMemoryDataReadinessGateLogger | None = None,
    ) -> DashboardService:
        catalog = HistoricalDatasetCatalog()
        catalog.register_dataset(self._metadata(), source="origem_opaca")
        provider = FakeMarketDataProvider(self._dataset())
        service = DashboardService(
            historical_dataset_catalog=catalog,
            historical_data_provider=provider,
            historical_dataset_quality_repository=repository,
            data_readiness_gate_logger=(
                logger or InMemoryDataReadinessGateLogger()
            ),
            research_lab_service=ResearchLabService(market_data_provider=provider),
        )
        service.select_historical_dataset("wdo_1m_2026")
        return service

    def _gate_log(
        self,
        dataset_id: str = "wdo_1m_2026",
        requested_action: str = "REPLAY",
        decision: str = "ALLOWED",
        evaluated_at: str = "2026-06-26T18:00:00",
        provider: str = "csv",
        reasons: list[str] | None = None,
    ) -> DataReadinessGateLog:
        return DataReadinessGateLog(
            dataset_id=dataset_id,
            evaluated_at=evaluated_at,
            requested_action=requested_action,
            readiness_status="READY_FOR_REPLAY_AND_RESEARCH",
            decision=decision,
            provider=provider,
            reasons=list(reasons or []),
        )

    def _provider_metric(self, provider: str) -> object:
        return SimpleNamespace(
            provider=provider,
            total_datasets=1,
            total_validated=1,
            total_approved=1,
            total_rejected=0,
            total_unvalidated=0,
            total_gate_evaluations=2,
            total_allowed=1,
            total_blocked=1,
            last_validation_at="2026-06-26T18:00:00",
            last_gate_evaluation_at="2026-06-26T18:10:00",
        )

    def _provider_metric_dict(self) -> dict[str, object]:
        return {
            "total_datasets": 1,
            "validated_datasets": 1,
            "approved_datasets": 1,
            "rejected_datasets": 0,
            "not_validated_datasets": 0,
            "gate_evaluations": 2,
            "allowed": 1,
            "blocked": 1,
            "last_validation_at": "2026-06-26T18:00:00",
            "last_gate_evaluation_at": "2026-06-26T18:10:00",
        }

    def _dataset(self) -> HistoricalDataset:
        candles = [
            Candle("2026-06-26 09:00", 100.0, 102.0, 98.0, 101.0, 1000),
            Candle("2026-06-26 09:01", 101.0, 103.0, 99.0, 102.0, 1000),
        ]
        return HistoricalDataset(
            symbol="WDO",
            timeframe="1m",
            start_date="2026-06-26 09:00",
            end_date="2026-06-26 09:01",
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

    def _dataset_with_quality_issues(self) -> HistoricalDataset:
        candles = [
            Candle("2026-06-26 09:00", 100.0, 102.0, 98.0, 101.0, 1000),
            Candle("2026-06-26 09:01", 100.0, 99.0, 98.0, 101.0, -1),
            Candle("2026-06-26 09:04", 101.0, 103.0, 99.0, 102.0, 1000),
            Candle("2026-06-26 09:04", 102.0, 104.0, 100.0, 103.0, None),
        ]
        return HistoricalDataset(
            symbol="WDO",
            timeframe="1m",
            start_date="2026-06-26 09:00",
            end_date="2026-06-26 09:04",
            candles=candles,
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


class FakeMarketDataProvider(MarketDataProvider):
    """Provider fake para resolver dataset selecionado sem infraestrutura."""

    def __init__(
        self,
        dataset: HistoricalDataset,
        errors: list[str] | None = None,
    ) -> None:
        self.dataset = dataset
        self.errors = list(errors or [])
        self.loaded_source: object | None = None
        self.loaded_symbol: str | None = None
        self.loaded_timeframe: str | None = None

    def load(
        self,
        source: object,
        symbol: str = "WDO",
        timeframe: str = "UNKNOWN",
    ) -> HistoricalDataset:
        """Registra a origem opaca recebida e retorna dataset controlado."""
        self.loaded_source = source
        self.loaded_symbol = symbol
        self.loaded_timeframe = timeframe
        return self.dataset

    def symbols(self) -> list[str]:
        """Lista simbolos disponiveis no provider fake."""
        return [self.dataset.symbol]

    def available_periods(self) -> list[str]:
        """Lista timeframes disponiveis no provider fake."""
        return [self.dataset.timeframe]


class InMemoryHistoricalDatasetQualityRepository(
    HistoricalDatasetQualityRepository
):
    """Repositorio em memoria para validar a fachada sem infraestrutura."""

    def __init__(self) -> None:
        self.statuses: dict[str, HistoricalDatasetQualityStatus] = {}
        self.validations: list[HistoricalDatasetQualityValidationRecord] = []

    def save(self, status: HistoricalDatasetQualityStatus) -> None:
        """Salva status por dataset_id."""
        self.statuses[status.dataset_id] = status

    def get(self, dataset_id: str) -> HistoricalDatasetQualityStatus | None:
        """Busca status por dataset_id."""
        return self.statuses.get(dataset_id)

    def list_all(self) -> list[HistoricalDatasetQualityStatus]:
        """Lista status em memoria."""
        return sorted(
            self.statuses.values(),
            key=lambda status: status.dataset_id,
        )

    def append_validation(
        self,
        record: HistoricalDatasetQualityValidationRecord,
    ) -> None:
        """Registra validacao historica em memoria."""
        self.validations.append(record)

    def list_validations(
        self,
        dataset_id: str,
    ) -> list[HistoricalDatasetQualityValidationRecord]:
        """Lista validacoes por dataset_id."""
        return [
            record
            for record in self.validations
            if record.dataset_id == dataset_id
        ]


if __name__ == "__main__":
    unittest.main()
