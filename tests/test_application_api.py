"""Freeze da API publica da camada application."""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
import unittest

from core.operation_session import OperationSession
from tests.architecture_test_utils import imports_from


EXPECTED_PUBLIC_API: dict[str, dict[str, object]] = {'Alpha001ResearchService': {'module': 'application.alpha001_research_service',
                             'methods': {'run': '(self, experiment_result: '
                                                'research.alpha001_experiment.Alpha001ExperimentResult) -> '
                                                'research.alpha001_research_report.Alpha001ResearchResult'}},
 'ConfigurationService': {'module': 'application.configuration_service',
                          'methods': {'delete_preset': '(self, name: str) -> None',
                                      'get_configuration_data': '(self) -> '
                                                                'application.configuration_service.ConfigurationData',
                                      'list_presets': '(self) -> list[str]',
                                      'load_preset': '(self, name: str) -> '
                                                     'application.configuration_service.ConfigurationData',
                                      'save_preset': '(self, name: str) -> None',
                                      'update_configuration': '(self, **kwargs: Any) -> '
                                                              'application.configuration_service.ConfigurationData'}},
 'DashboardService': {'module': 'application.dashboard_service',
                      'methods': {'analyze_selected_historical_dataset_quality': '(self) -> '
                                                                                 'application.dashboard_service.HistoricalDatasetQualityReport',
                                  'arm_demo_robot': "(self, pair: str = 'TODOS', timeframe: str = 'H1') -> "
                                                    'application.dashboard_view_model.DashboardDemoRobotViewModel',
                                  'best_parameter_grid_result': '(self) -> '
                                                                'application.research_lab_service.ParameterGridData | '
                                                                'None',
                                  'clear_research_experiments': '(self) -> None',
                                  'compare_research_benchmarks': '(self) -> '
                                                                 'application.research_lab_service.BenchmarkComparisonData',
                                  'delete_configuration_preset': '(self, name: str) -> None',
                                  'disable_replay_auto_run': '(self) -> application.replay_service.ReplayData',
                                  'disarm_demo_robot': "(self, pair: str = 'TODOS', timeframe: str = 'H1') -> "
                                                       'application.dashboard_view_model.DashboardDemoRobotViewModel',
                                  'enable_replay_auto_run': '(self, speed_seconds: float) -> '
                                                            'application.replay_service.ReplayData',
                                  'evaluate_armed_demo_robot_once': "(self, pair: str = 'TODOS', timeframe: str = "
                                                                    "'H1') -> "
                                                                    'application.dashboard_view_model.DashboardDemoRobotViewModel',
                                  'export_alpha001_results_to_csv': '(self, output_path: object) -> object',
                                  'export_mt5_visual_signals': '(self, output_path: object | None = None) -> '
                                                               'application.mt5_visual_signal_exporter.MT5VisualSignalExportResult',
                                  'filter_alpha001_parameter_ranking': '(self, validation_status: str) -> '
                                                                       'list[application.research_lab_service.Alpha001ParameterRankingData]',
                                  'get_active_replay_strategy_name': '(self) -> str',
                                  'get_alpha001_paper_report': '(self) -> '
                                                               'application.dashboard_service.Alpha001PaperReportData',
                                  'get_alpha001_paper_status': '(self) -> '
                                                               'application.dashboard_service.Alpha001PaperStatusData',
                                  'get_alpha001_research_report': '(self) -> '
                                                                  'application.research_lab_service.Alpha001ResearchReportData',
                                  'get_alpha001_research_summary': '(self) -> '
                                                                   'application.research_lab_service.Alpha001ResearchSummaryData',
                                  'get_alpha001_robustness': '(self) -> '
                                                             'application.research_lab_service.Alpha001RobustnessData',
                                  'get_alpha001_status': '(self) -> application.dashboard_service.Alpha001StatusData',
                                  'get_dashboard_contract_version': '(self) -> str',
                                  'get_dashboard_data': '(self) -> application.dashboard_service.DashboardData',
                                  'get_dashboard_view_model': '(self) -> '
                                                              'application.dashboard_view_model.DashboardViewModel',
                                  'get_data_readiness_gate_metrics': '(self) -> '
                                                                     'application.dashboard_service.DataReadinessGateMetrics',
                                  'get_demo_robot_status': '(self) -> '
                                                           'application.dashboard_view_model.DashboardDemoRobotViewModel',
                                  'get_fast_mt5_forex_snapshot': '(self) -> '
                                                                 'application.dashboard_view_model.DashboardMT5ForexSignalViewModel '
                                                                 '| None',
                                  'get_historical_dataset_health_summary': '(self) -> '
                                                                           'application.dashboard_service.HistoricalDatasetHealthSummary',
                                  'get_historical_provider_metrics': '(self) -> dict[str, dict[str, object]]',
                                  'get_light_dashboard_view_model': '(self) -> '
                                                                    'application.dashboard_view_model.DashboardViewModel',
                                  'get_live_experiment_summary': '(self) -> '
                                                                 'application.research_lab_service.LiveExperimentSummaryData',
                                  'get_live_research_data': '(self) -> '
                                                            'application.dashboard_service.LiveResearchDashboardData',
                                  'get_live_research_session_summary': '(self) -> '
                                                                       'application.dashboard_service.LiveResearchSessionSummaryData',
                                  'get_mt5_alpha_research_ranking': '(self, target_confidence: float = 0.7) -> '
                                                                    'list[application.dashboard_view_model.DashboardMT5AlphaResearchReportViewModel]',
                                  'get_mt5_alpha_research_report': "(self, alpha_id: str = 'ALPHA001', "
                                                                   'target_confidence: float = 0.7) -> '
                                                                   'application.dashboard_view_model.DashboardMT5AlphaResearchReportViewModel',
                                  'get_mt5_forex_signals': '(self) -> '
                                                           'application.mt5_market_data_service.MT5ForexSignalDashboard',
                                  'get_mt5_market_data': '(self) -> '
                                                         'application.mt5_market_data_service.MT5DashboardMarketData',
                                  'get_mt5_research_constants': '(self) -> '
                                                                'application.dashboard_view_model.DashboardMT5HeuristicResearchViewModel',
                                  'get_mt5_research_history_candle_count': '(self) -> int',
                                  'get_mt5_research_history_database_path': '(self) -> str',
                                  'get_mt5_research_history_last_update': '(self) -> str',
                                  'get_mt5_research_report_snapshot': '(self) -> '
                                                                      'application.dashboard_view_model.DashboardMT5HeuristicResearchViewModel',
                                  'get_mt5_trade_audit_report': '(self) -> '
                                                                'application.dashboard_view_model.DashboardMT5TradeAuditViewModel',
                                  'get_research_layer_definitions': '(self) -> list[dict[str, object]]',
                                  'get_research_report': '(self) -> '
                                                         'application.research_lab_service.ResearchReportData',
                                  'get_selected_historical_dataset': '(self) -> '
                                                                     'market_data.historical_dataset_catalog.HistoricalDatasetMetadata '
                                                                     '| None',
                                  'get_selected_historical_dataset_id': '(self) -> str | None',
                                  'get_selected_historical_dataset_quality_status': '(self) -> '
                                                                                    'market_data.historical_dataset_quality_repository.HistoricalDatasetQualityStatus '
                                                                                    '| None',
                                  'get_selected_historical_dataset_readiness': '(self) -> '
                                                                               'application.dashboard_service.HistoricalDatasetReadiness',
                                  'get_timeframe_optimization_results': '(self) -> '
                                                                        'list[research.timeframe_optimizer.TimeframeOptimizationResult]',
                                  'is_replay_auto_run_enabled': '(self) -> bool',
                                  'last_benchmark_comparison': '(self) -> '
                                                               'application.research_lab_service.BenchmarkComparisonData '
                                                               '| None',
                                  'last_benchmark_validation': '(self) -> '
                                                               'application.research_lab_service.ExperimentValidationData '
                                                               '| None',
                                  'last_research_experiment': '(self) -> '
                                                              'application.research_lab_service.ResearchExperimentData '
                                                              '| None',
                                  'list_alpha001_parameter_ranking': '(self) -> '
                                                                     'list[application.research_lab_service.Alpha001ParameterRankingData]',
                                  'list_available_replay_strategies': '(self) -> list[str]',
                                  'list_available_research_strategies': '(self) -> list[str]',
                                  'list_benchmark_validations': '(self) -> '
                                                                'list[application.research_lab_service.ExperimentValidationData]',
                                  'list_configuration_presets': '(self) -> list[str]',
                                  'list_data_readiness_gate_logs': '(self) -> '
                                                                   'list[application.data_readiness_gate_log.DataReadinessGateLog]',
                                  'list_demo_execution_audit_log': '(self) -> '
                                                                   'list[application.demo_execution_service.DemoExecutionAuditRecord]',
                                  'list_historical_dataset_quality_validations': '(self, dataset_id: str) -> '
                                                                                 'list[market_data.historical_dataset_quality_repository.HistoricalDatasetQualityValidationRecord]',
                                  'list_historical_datasets': '(self) -> '
                                                              'list[market_data.historical_dataset_catalog.HistoricalDatasetMetadata]',
                                  'list_live_experiment_signals': '(self) -> '
                                                                  'list[application.research_lab_service.LiveExperimentSignalData]',
                                  'list_live_research_history': '(self) -> '
                                                                'list[application.dashboard_service.LiveResearchHistoryRow]',
                                  'list_live_research_signal_quality': '(self) -> '
                                                                       'list[application.dashboard_service.LiveResearchSignalQualityRow]',
                                  'list_parameter_grid_results': '(self) -> '
                                                                 'list[application.research_lab_service.ParameterGridData]',
                                  'list_research_benchmarks': '(self) -> '
                                                              'list[application.research_lab_service.BenchmarkData]',
                                  'list_research_experiments': '(self) -> '
                                                               'list[application.research_lab_service.ResearchExperimentData]',
                                  'load_configuration_preset': '(self, name: str) -> '
                                                               'application.configuration_service.ConfigurationData',
                                  'load_demo_replay_candles': '(self) -> application.replay_service.ReplayData',
                                  'load_historical_replay_csv': '(self, path: object) -> '
                                                                'application.replay_service.ReplayData',
                                  'load_mt5_forex_signals': "(self, timeframe: str = 'M1') -> "
                                                            'application.mt5_market_data_service.MT5ForexSignalDashboard',
                                  'load_mt5_market_data': "(self, symbol: str = 'EURUSD', timeframe: str = 'M1', "
                                                          'count: int | None = None) -> '
                                                          'application.mt5_market_data_service.MT5DashboardMarketData',
                                  'load_selected_historical_dataset_to_replay': '(self) -> '
                                                                                'application.replay_service.ReplayData',
                                  'load_timeframe_optimization_results': '(self, count: int | None = None) -> '
                                                                         'list[research.timeframe_optimizer.TimeframeOptimizationResult]',
                                  'mt5_research_history_database_path': '(self) -> pathlib.Path',
                                  'next_replay_candle': '(self) -> application.replay_service.ReplayData',
                                  'prepare_demo_execution_order': '(self, strategy_signal: '
                                                                  'domain.contracts.strategy_signal.StrategySignal, '
                                                                  'market_snapshot: '
                                                                  'domain.contracts.market_snapshot.MarketSnapshot, '
                                                                  'risk_decision: '
                                                                  'domain.contracts.risk_decision.RiskDecision, '
                                                                  'entry_price: float, stop_points: float, '
                                                                  'target_points: float) -> '
                                                                  'tuple[domain.contracts.decision_context.DecisionContext, '
                                                                  'domain.contracts.execution_order.ExecutionOrder | '
                                                                  'None]',
                                  'process_alpha001_paper_signal': '(self, strategy_signal: '
                                                                   'domain.contracts.strategy_signal.StrategySignal, '
                                                                   'market_snapshot: '
                                                                   'domain.contracts.market_snapshot.MarketSnapshot) '
                                                                   '-> '
                                                                   'application.dashboard_service.Alpha001PaperStatusData',
                                  'recalculate_mt5_research': "(self, timeframe: str = 'M1') -> "
                                                              'application.mt5_market_data_service.MT5ForexSignalDashboard',
                                  'reset_replay': '(self) -> application.replay_service.ReplayData',
                                  'run_alpha001_parameter_ranking': '(self) -> '
                                                                    'list[application.research_lab_service.Alpha001ParameterRankingData]',
                                  'run_demo_alpha001_experiment': '(self) -> '
                                                                  'application.research_lab_service.ResearchExperimentData',
                                  'run_demo_parameter_grid': '(self) -> '
                                                             'list[application.research_lab_service.ParameterGridData]',
                                  'run_demo_research_benchmarks': '(self) -> '
                                                                  'list[application.research_lab_service.BenchmarkData]',
                                  'run_demo_research_experiment': '(self) -> '
                                                                  'application.research_lab_service.ResearchExperimentData',
                                  'run_demo_robot_for_all': '(self, pairs: list[str] | None = None, timeframe: str = '
                                                            "'H1') -> "
                                                            'application.dashboard_view_model.DashboardDemoRobotViewModel',
                                  'run_demo_robot_once': "(self, pair: str, timeframe: str = 'H1') -> "
                                                         'application.dashboard_view_model.DashboardDemoRobotViewModel',
                                  'run_mt5_research_calibration': "(self, timeframe: str = 'M1') -> "
                                                                  'application.dashboard_view_model.DashboardMT5HeuristicResearchViewModel',
                                  'run_mt5_research_calibration_for_pair': "(self, pair: str, timeframe: str = 'M1') "
                                                                           '-> '
                                                                           'application.dashboard_view_model.DashboardMT5HeuristicResearchViewModel',
                                  'run_online_demo_robot_cycle': "(self, pair: str = 'TODOS', timeframe: str = 'H1') "
                                                                 '-> '
                                                                 'application.dashboard_view_model.DashboardDemoRobotViewModel',
                                  'run_selected_historical_dataset_research_experiment': '(self, strategy_name: str = '
                                                                                         "'alpha001_iorb', "
                                                                                         'stop_points: float = 50.0, '
                                                                                         'target_points: float = '
                                                                                         '100.0) -> '
                                                                                         'application.research_lab_service.ResearchExperimentData',
                                  'save_configuration_preset': '(self, name: str) -> None',
                                  'select_historical_dataset': '(self, dataset_id: str) -> '
                                                               'market_data.historical_dataset_catalog.HistoricalDatasetMetadata',
                                  'select_replay_strategy': '(self, strategy_name: str) -> '
                                                            'application.replay_service.ReplayData',
                                  'start_replay': '(self) -> application.replay_service.ReplayData',
                                  'stop_replay': '(self) -> application.replay_service.ReplayData',
                                  'submit_demo_execution_order': '(self, decision_context: '
                                                                 'domain.contracts.decision_context.DecisionContext, '
                                                                 'order: '
                                                                 'domain.contracts.execution_order.ExecutionOrder | '
                                                                 'None, paper_validated: bool) -> '
                                                                 'domain.contracts.execution_result.ExecutionResult',
                                  'suggest_mt5_lab_setups': '(self, target_confidence: float = 0.7) -> '
                                                            'list[application.dashboard_view_model.DashboardMT5SetupSuggestionViewModel]',
                                  'test_mt5_connection': "(self, symbol: str = 'EURUSD', timeframe: str = 'H1') -> "
                                                         'application.mt5_market_data_service.MT5ConnectionDiagnostic',
                                  'update_configuration': '(self, **kwargs: object) -> '
                                                          'application.configuration_service.ConfigurationData',
                                  'update_mt5_research_calculations': "(self, timeframe: str = 'M1') -> "
                                                                      'application.dashboard_view_model.DashboardMT5HeuristicResearchViewModel',
                                  'update_mt5_research_history': "(self, timeframe: str = 'M1') -> "
                                                                 'application.mt5_market_data_service.MT5ForexSignalDashboard',
                                  'validate_research_benchmarks': '(self) -> '
                                                                  'list[application.research_lab_service.ExperimentValidationData]'}},
 'DemoExecutionService': {'module': 'application.demo_execution_service',
                          'methods': {'list_audit_log': "(self) -> 'list[DemoExecutionAuditRecord]'",
                                      'prepare_order': "(self, strategy_signal: 'StrategySignal', market_snapshot: "
                                                       "'MarketSnapshot', risk_decision: 'RiskDecision', entry_price: "
                                                       "'float', stop_points: 'float', target_points: 'float') -> "
                                                       "'tuple[DecisionContext, ExecutionOrder | None]'",
                                      'register_daily_result': "(self, result_points: 'float') -> 'None'",
                                      'submit_demo_order': "(self, decision_context: 'DecisionContext', order: "
                                                           "'ExecutionOrder | None', paper_validated: 'bool') -> "
                                                           "'ExecutionResult'"}},
 'ForexMT5Service': {'module': 'application.forex_mt5_service',
                     'methods': {'get_open_positions': "(self) -> 'list[dict[str, object]]'",
                                 'get_signals': "(self, timeframe: 'str' = 'M1') -> 'list[ForexSignal]'",
                                 'get_status': "(self) -> 'MT5Status'"}},
 'LabService': {'module': 'application.lab_service', 'methods': {'get_latest_result': "(self) -> 'LabResult'"}},
 'LiveResearchService': {'module': 'application.live_research_service',
                         'methods': {'get_latest_data': "(self) -> 'LiveResearchData | None'",
                                     'get_session_summary': "(self) -> 'LiveResearchSessionSummary'",
                                     'ingest_from_mt5': "(self, symbol: 'str', timeframe: 'Any', count: 'int' = 10) -> "
                                                        "'LiveResearchData | None'",
                                     'list_signal_quality': "(self) -> 'list[LiveResearchSignalQuality]'",
                                     'list_snapshot_history': "(self) -> 'list[LiveResearchSnapshotRecord]'",
                                     'process_candle': "(self, candle: 'Candle', symbol: 'str' = 'UNKNOWN', timeframe: "
                                                       "'str' = 'UNKNOWN', ingestion_summary: 'MT5IngestionSummary | "
                                                       "None' = None, publish_new_candle: 'bool' = True) -> "
                                                       "'LiveResearchData'",
                                     'set_snapshot_history_limit': "(self, limit: 'int') -> 'None'"}},
 'MT5DemoRobotService': {'module': 'application.mt5_demo_robot_service',
                         'methods': {'evaluate_once': "(self, signal: 'MT5DemoRobotSignal', trade_plan: "
                                                      "'MT5DemoTradePlan') -> 'MT5DemoRobotResult'"}},
 'MT5MarketDataService': {'module': 'application.mt5_market_data_service',
                          'methods': {'diagnose_mt5_connection': "(self, symbol: 'str' = 'EURUSD', timeframe: 'str' = "
                                                                 "'M1') -> 'MT5ConnectionDiagnostic'",
                                      'get_dashboard_market_data': "(self) -> 'MT5DashboardMarketData'",
                                      'get_forex_signal_dashboard': "(self) -> 'MT5ForexSignalDashboard'",
                                      'get_timeframe_optimization_results': '(self) -> '
                                                                            "'list[TimeframeOptimizationResult]'",
                                      'ingest_candles': "(self, symbol: 'str', timeframe: 'Any', count: 'int' = 10) -> "
                                                        "'MT5IngestionSummary'",
                                      'load_dashboard_market_data': "(self, symbol: 'str' = 'EURUSD', timeframe: 'str' "
                                                                    "= 'M1', count: 'int | None' = None) -> "
                                                                    "'MT5DashboardMarketData'",
                                      'load_forex_research_snapshot': "(self, timeframe: 'str' = 'M1', count: 'int | "
                                                                      "None' = None) -> 'MT5ForexSignalDashboard'",
                                      'load_forex_signal_dashboard': "(self, timeframe: 'str' = 'M1', "
                                                                     "recalculate_research: 'bool | None' = None) -> "
                                                                     "'MT5ForexSignalDashboard'",
                                      'load_forex_signal_dashboard_for_timeframes': '(self, timeframes_by_pair: '
                                                                                    "'dict[str, str]', "
                                                                                    "fallback_timeframe: 'str' = 'M1') "
                                                                                    "-> 'MT5ForexSignalDashboard'",
                                      'load_timeframe_optimization_results': "(self, count: 'int | None' = None) -> "
                                                                             "'list[TimeframeOptimizationResult]'"}},
 'MT5TradeAuditService': {'module': 'application.mt5_trade_audit_service',
                          'methods': {'build_report': "(self, *, signals: 'list[ForexSignal]', lab: 'LabResult', "
                                                      "positions: 'list[dict[str, object]] | None' = None) -> "
                                                      "'TradeAuditReport'"}},
 'MarketService': {'module': 'application.market_service',
                   'methods': {'get_latest_market_dna': '(self) -> domain.contracts.market_snapshot.MarketSnapshot | '
                                                        'None',
                               'get_liquidity': '(self) -> float | None',
                               'get_regime': '(self) -> str',
                               'get_score': '(self) -> float | None',
                               'get_volatility': '(self) -> float | None'}},
 'PaperTradingService': {'module': 'application.paper_trading_service',
                         'methods': {'alpha001_strategy': '(self) -> '
                                                          'strategies.alpha001_iorb_strategy.Alpha001IORBStrategy',
                                     'clear_history': '(self) -> None',
                                     'generate_report': '(self) -> '
                                                        'application.paper_trading_service.PaperTradingReport',
                                     'list_paper_history': '(self) -> '
                                                           'list[domain.contracts.execution_order.ExecutionOrder]',
                                     'process_signal': '(self, strategy_signal: '
                                                       'domain.contracts.strategy_signal.StrategySignal, '
                                                       'market_snapshot: '
                                                       'domain.contracts.market_snapshot.MarketSnapshot, entry_price: '
                                                       'float) -> '
                                                       'application.paper_trading_service.PaperTradingResult'}},
 'RegimeService': {'module': 'application.regime_service',
                   'methods': {'analyze': '(self, market_snapshot: domain.contracts.market_snapshot.MarketSnapshot) -> '
                                          'application.regime_service.RegimeData'}},
 'ReplayService': {'module': 'application.replay_service',
                   'methods': {'disable_auto_run': '(self) -> application.replay_service.ReplayData',
                               'enable_auto_run': '(self, speed_seconds: float) -> '
                                                  'application.replay_service.ReplayData',
                               'get_active_strategy_name': '(self) -> str',
                               'get_replay_data': '(self) -> application.replay_service.ReplayData',
                               'is_auto_run_enabled': '(self) -> bool',
                               'list_available_strategies': '(self) -> list[str]',
                               'load_candles': '(self, candles: list[domain.candle.Candle]) -> '
                                               'application.replay_service.ReplayData',
                               'load_demo_candles': '(self) -> application.replay_service.ReplayData',
                               'load_historical_csv': '(self, path: object) -> application.replay_service.ReplayData',
                               'load_historical_data': '(self, source: object) -> '
                                                       'application.replay_service.ReplayData',
                               'load_historical_dataset': '(self, dataset: '
                                                          'market_data.historical_dataset.HistoricalDataset) -> '
                                                          'application.replay_service.ReplayData',
                               'load_real_historical_dataset': "(self, symbol: str = 'WDO', timeframe: str = '1m', "
                                                               "period: str = '2025') -> "
                                                               'application.replay_service.ReplayData',
                               'next_candle': '(self) -> application.replay_service.ReplayData',
                               'reset': '(self) -> application.replay_service.ReplayData',
                               'select_strategy': '(self, strategy_name: str) -> application.replay_service.ReplayData',
                               'start': '(self) -> application.replay_service.ReplayData',
                               'stop': '(self) -> application.replay_service.ReplayData'}},
 'ReportService': {'module': 'application.report_service',
                   'methods': {'build_rows': "(self, forex: 'MT5Status', lab: 'LabResult') -> 'list[ReportRow]'",
                               'build_summary': "(self, forex: 'MT5Status', lab: 'LabResult', audit: "
                                                "'TradeAuditReport') -> 'dict[str, object]'"}},
 'ResearchLabService': {'module': 'application.research_lab_service',
                        'methods': {'alpha001_dashboard_research_metrics': '(self) -> '
                                                                           'application.research_lab_service.Alpha001DashboardResearchData',
                                    'alpha001_research_report': '(self) -> '
                                                                'application.research_lab_service.Alpha001ResearchReportData',
                                    'best_parameter_grid_result': '(self) -> '
                                                                  'application.research_lab_service.ParameterGridData '
                                                                  '| None',
                                    'clear': '(self) -> None',
                                    'compare_benchmarks': '(self) -> '
                                                          'application.research_lab_service.BenchmarkComparisonData',
                                    'export_alpha001_results_to_csv': '(self, output_path: str | pathlib.Path) -> '
                                                                      'pathlib.Path',
                                    'get_alpha001_research_summary': '(self) -> '
                                                                     'application.research_lab_service.Alpha001ResearchSummaryData',
                                    'get_alpha001_robustness': '(self) -> '
                                                               'application.research_lab_service.Alpha001RobustnessData',
                                    'last_comparison': '(self) -> '
                                                       'application.research_lab_service.BenchmarkComparisonData | '
                                                       'None',
                                    'last_experiment': '(self) -> '
                                                       'application.research_lab_service.ResearchExperimentData | None',
                                    'last_validation': '(self) -> '
                                                       'application.research_lab_service.ExperimentValidationData | '
                                                       'None',
                                    'list_alpha001_parameter_ranking': '(self) -> '
                                                                       'list[application.research_lab_service.Alpha001ParameterRankingData]',
                                    'list_available_strategies': '(self) -> list[str]',
                                    'list_benchmarks': '(self) -> list[application.research_lab_service.BenchmarkData]',
                                    'list_experiments': '(self) -> '
                                                        'list[application.research_lab_service.ResearchExperimentData]',
                                    'list_live_experiment_signals': '(self) -> '
                                                                    'list[application.research_lab_service.LiveExperimentSignalData]',
                                    'list_parameter_grid_results': '(self) -> '
                                                                   'list[application.research_lab_service.ParameterGridData]',
                                    'list_validations': '(self) -> '
                                                        'list[application.research_lab_service.ExperimentValidationData]',
                                    'live_experiment_summary': '(self) -> '
                                                               'application.research_lab_service.LiveExperimentSummaryData',
                                    'research_report': '(self) -> application.research_lab_service.ResearchReportData',
                                    'run_alpha001_parameter_ranking': '(self) -> '
                                                                      'list[application.research_lab_service.Alpha001ParameterRankingData]',
                                    'run_alpha001_research': '(self, candles: list[domain.candle.Candle], config: '
                                                             'alpha.alpha001_config.Alpha001Config | None = None, '
                                                             "experiment_name: str = 'Alpha001 Research') -> "
                                                             'research.alpha001_research_report.Alpha001ResearchResult',
                                    'run_demo_alpha001_experiment': '(self) -> '
                                                                    'application.research_lab_service.ResearchExperimentData',
                                    'run_demo_benchmarks': '(self) -> '
                                                           'list[application.research_lab_service.BenchmarkData]',
                                    'run_demo_experiment': '(self) -> '
                                                           'application.research_lab_service.ResearchExperimentData',
                                    'run_demo_parameter_grid': '(self) -> '
                                                               'list[application.research_lab_service.ParameterGridData]',
                                    'run_historical_csv_experiment': '(self, path: str | pathlib.Path, '
                                                                     "experiment_name: str = 'Historical WDO "
                                                                     "Research', strategy_name: str = 'alpha001_iorb', "
                                                                     'stop_points: float = 50.0, target_points: float '
                                                                     '= 100.0) -> '
                                                                     'application.research_lab_service.ResearchExperimentData',
                                    'run_historical_data_experiment': '(self, source: object, experiment_name: str = '
                                                                      "'Historical WDO Research', strategy_name: str = "
                                                                      "'alpha001_iorb', stop_points: float = 50.0, "
                                                                      'target_points: float = 100.0, symbol: str = '
                                                                      "'WDO', timeframe: str = 'UNKNOWN') -> "
                                                                      'application.research_lab_service.ResearchExperimentData',
                                    'run_historical_experiment': '(self, candles: list[domain.candle.Candle], '
                                                                 "experiment_name: str = 'Historical WDO Research', "
                                                                 "strategy_name: str = 'alpha001_iorb', stop_points: "
                                                                 'float = 50.0, target_points: float = 100.0) -> '
                                                                 'application.research_lab_service.ResearchExperimentData',
                                    'run_real_data_benchmarks': "(self, symbol: str = 'WDO', timeframe: str = '1m', "
                                                                "period: str = '2025') -> "
                                                                'list[application.research_lab_service.BenchmarkData]',
                                    'run_real_data_research': "(self, symbol: str = 'WDO', timeframe: str = '1m', "
                                                              "period: str = '2025') -> "
                                                              'application.research_lab_service.RealDataResearchData',
                                    'validate_all_benchmarks': '(self) -> '
                                                               'list[application.research_lab_service.ExperimentValidationData]'}},
 'ResearchService': {'module': 'application.research_service',
                     'methods': {'analyze': '(self, feature_snapshot: market.feature_engine.FeatureSnapshot, '
                                            'regime_analysis: market.regime_engine.RegimeAnalysis, market_memory: '
                                            'market.market_memory.MarketMemory) -> '
                                            'application.research_service.ResearchData'}},
 'SessionService': {'module': 'application.session_service',
                    'methods': {'get_session_snapshot': '(self) -> application.session_service.SessionSnapshot'}},
 'SystemService': {'module': 'application.system_service',
                   'methods': {'get_status': '(self) -> application.system_service.SystemStatus'}}}


class ApplicationApiFreezeTest(unittest.TestCase):
    """Protege assinaturas publicas dos servicos de application."""

    def test_imports_de_servicos_publicos_funcionam(self) -> None:
        for service_name, contract in EXPECTED_PUBLIC_API.items():
            with self.subTest(service=service_name):
                module = importlib.import_module(str(contract["module"]))
                self.assertTrue(hasattr(module, service_name))

    def test_todos_servicos_publicos_instanciam_sem_excecao(self) -> None:
        for service_name in EXPECTED_PUBLIC_API:
            with self.subTest(service=service_name):
                service = self._instantiate(service_name)
                self.assertEqual(service.__class__.__name__, service_name)

    def test_descoberta_automatica_de_servicos_publicos_esta_congelada(self) -> None:
        discovered = self._discover_public_services()

        self.assertEqual(
            sorted(discovered),
            sorted(EXPECTED_PUBLIC_API),
            "Servico publico em application foi adicionado/removido sem atualizar "
            "o contrato congelado.",
        )

    def test_metodos_publicos_e_assinaturas_estao_congelados(self) -> None:
        discovered = self._discover_public_services()

        for service_name, contract in EXPECTED_PUBLIC_API.items():
            with self.subTest(service=service_name):
                current_methods = self._public_method_signatures(
                    discovered[service_name]
                )
                self.assertEqual(current_methods, contract["methods"])

    def test_assinaturas_nao_expoem_infraestrutura_interna(self) -> None:
        forbidden_fragments = (
            "Adapter",
            "Provider",
            "Registry",
            "ConfigurationManager",
            "OperationSession",
            "CsvHistoricalDataSource",
            "ParquetHistoricalDataAdapter",
            "DuckDBHistoricalDataAdapter",
            "JsonHistoricalDatasetQualityRepository",
            "HistoricalDatasetQualityRepository",
        )

        for service_name, contract in EXPECTED_PUBLIC_API.items():
            for method_name, signature in contract["methods"].items():
                with self.subTest(service=service_name, method=method_name):
                    leaked = [
                        fragment
                        for fragment in forbidden_fragments
                        if fragment in str(signature)
                    ]
                    self.assertEqual(
                        leaked,
                        [],
                        f"{service_name}.{method_name} expoe infraestrutura: {leaked}",
                    )

    def test_dashboard_service_permanece_fachada_principal_do_dashboard(self) -> None:
        imports = self._imports(Path("dashboard_app.py"))

        self.assertIn("application.dashboard_service", imports)
        forbidden_application_services = {
            "application.configuration_service",
            "application.market_service",
            "application.paper_trading_service",
            "application.regime_service",
            "application.replay_service",
            "application.research_lab_service",
            "application.research_service",
            "application.session_service",
            "application.system_service",
        }
        self.assertTrue(
            forbidden_application_services.isdisjoint(imports),
            "dashboard_app.py deve consumir somente DashboardService como fachada: "
            f"{sorted(forbidden_application_services & imports)}",
        )

    def test_retornos_publicos_minimos_sao_tipos_seguros(self) -> None:
        dashboard_service = self._instantiate("DashboardService")
        replay_service = self._instantiate("ReplayService")
        research_lab_service = self._instantiate("ResearchLabService")
        configuration_service = self._instantiate("ConfigurationService")
        session_service = self._instantiate("SessionService")

        self.assertIsInstance(dashboard_service.list_historical_datasets(), list)
        self.assertIsInstance(dashboard_service.get_historical_provider_metrics(), dict)
        self.assertIsInstance(dashboard_service.get_research_layer_definitions(), list)
        self.assertIsNotNone(dashboard_service.get_dashboard_data())
        self.assertIsNotNone(replay_service.get_replay_data())
        self.assertIsInstance(research_lab_service.list_experiments(), list)
        self.assertIsInstance(research_lab_service.list_available_strategies(), list)
        self.assertIsInstance(configuration_service.list_presets(), list)
        self.assertIsNotNone(configuration_service.get_configuration_data())
        self.assertIsNotNone(session_service.get_session_snapshot())

    def test_docstrings_publicas_existentes_continuam_acessiveis(self) -> None:
        for service_name, contract in EXPECTED_PUBLIC_API.items():
            with self.subTest(service=service_name):
                module = importlib.import_module(str(contract["module"]))
                cls = getattr(module, service_name)
                if cls.__doc__:
                    self.assertIsInstance(inspect.getdoc(cls), str)

    def _discover_public_services(self) -> dict[str, type]:
        services: dict[str, type] = {}
        for path in sorted(Path("application").glob("*_service.py")):
            module_name = "application." + path.stem
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == module_name and name.endswith("Service"):
                    services[name] = obj
        return services

    def _public_method_signatures(self, cls: type) -> dict[str, str]:
        methods: dict[str, str] = {}
        for method_name, method in inspect.getmembers(cls, inspect.isfunction):
            if method_name.startswith("_"):
                continue
            signature = inspect.signature(method)
            parameter_names = list(signature.parameters)
            if not parameter_names or parameter_names[0] != "self":
                continue
            methods[method_name] = str(signature)
        return dict(sorted(methods.items()))

    def _instantiate(self, service_name: str) -> object:
        contract = EXPECTED_PUBLIC_API[service_name]
        module = importlib.import_module(str(contract["module"]))
        cls = getattr(module, service_name)
        if service_name == "SessionService":
            return cls(OperationSession("N/D", "09:00", "18:00"))
        return cls()

    def _imports(self, path: Path) -> set[str]:
        return imports_from(path)


if __name__ == "__main__":
    unittest.main()
