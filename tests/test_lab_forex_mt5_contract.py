"""Testes de contrato do fluxo Lab -> Forex -> MT5."""

from __future__ import annotations

from pathlib import Path
import unittest

from application.dashboard_service import DashboardData, DashboardService
from application.dashboard_view_model import (
    DashboardMT5ForexSignalRowViewModel,
    DashboardMT5ForexSignalViewModel,
    DashboardMT5HeuristicResearchRowViewModel,
    DashboardMT5HeuristicResearchViewModel,
)
from application.mt5_market_data_service import MT5ForexSignalDashboard, MT5ForexSignalRow
from application.mt5_visual_signal_exporter import MT5VisualSignalExporter
from research.mt5_research_trade_plan import (
    STOP_MANAGEMENT_PARAMETER_KEYS,
    SUPPORTED_STOP_MANAGEMENT_POLICIES,
    MT5ResearchTradePlanEngine,
    MT5ResearchTradePlanInput,
)


class LabForexMT5ContractTest(unittest.TestCase):
    """Protege contratos de decisao do Lab e visualizacao no MT5."""

    def test_regra_de_ouro_lab_alimenta_forex_e_forex_alimenta_mt5(self) -> None:
        service = DashboardService()
        object.__setattr__(
            service,
            "mt5_research_constants",
            DashboardMT5HeuristicResearchViewModel(
                rows=[
                    self._lab_row(
                        pair="EURUSD",
                        timeframe="M15",
                        alpha="ALPHA003",
                        model="BREAKOUT_CONSOLIDATION",
                    ),
                    self._lab_row(
                        pair="NZDUSD",
                        timeframe="H1",
                        alpha="ALPHA001",
                        model="TREND_MOMENTUM",
                    ),
                ]
            ),
        )
        service.mt5_market_data_service.latest_forex_candles[("EURUSD", "M15")] = (
            self._candles()
        )
        service.mt5_market_data_service.latest_forex_candles[("NZDUSD", "H1")] = (
            self._candles()
        )

        data = DashboardData(
            system_status=service.system_service.get_status(),
            market_snapshot=None,
            strategy_signal=None,
            mt5_forex_signals=MT5ForexSignalDashboard(
                timeframe="M1",
                pairs=[
                    self._forex_row("EURUSD", "M1"),
                    self._forex_row("NZDUSD", "M1"),
                ],
            ),
        )
        forex = service._to_view_model_mt5_forex_signals(
            data,
            service.get_mt5_research_constants(),
        )
        rows_by_pair = {row.pair: row for row in forex.pairs}

        self.assertEqual(rows_by_pair["EURUSD"].lab_configuration_source, "RESEARCH_LAB")
        self.assertEqual(rows_by_pair["EURUSD"].lab_timeframe, "M15")
        self.assertEqual(rows_by_pair["EURUSD"].timeframe, "M15")
        self.assertEqual(rows_by_pair["EURUSD"].lab_alpha_id, "ALPHA003")
        self.assertEqual(rows_by_pair["NZDUSD"].lab_configuration_source, "RESEARCH_LAB")
        self.assertEqual(rows_by_pair["NZDUSD"].lab_timeframe, "H1")
        self.assertEqual(rows_by_pair["NZDUSD"].timeframe, "H1")
        self.assertEqual(rows_by_pair["NZDUSD"].lab_alpha_id, "ALPHA001")

        payload = _NoLivePositionsExporter().build_payload(forex)
        signals_by_symbol = {signal["symbol"]: signal for signal in payload["signals"]}

        self.assertEqual(signals_by_symbol["EURUSD"]["timeframe"], "M15")
        self.assertEqual(
            signals_by_symbol["EURUSD"]["lab_configuration_source"],
            "RESEARCH_LAB",
        )
        self.assertEqual(signals_by_symbol["EURUSD"]["lab_timeframe"], "M15")
        self.assertEqual(signals_by_symbol["NZDUSD"]["timeframe"], "H1")
        self.assertEqual(
            signals_by_symbol["NZDUSD"]["lab_configuration_source"],
            "RESEARCH_LAB",
        )
        self.assertEqual(signals_by_symbol["NZDUSD"]["lab_timeframe"], "H1")

    def test_lab_preserva_todos_os_tipos_de_stop_management_suportados(self) -> None:
        engine = MT5ResearchTradePlanEngine()

        for policy in sorted(SUPPORTED_STOP_MANAGEMENT_POLICIES):
            with self.subTest(policy=policy):
                parameters = {
                    key: self._parameter_value(key)
                    for key in STOP_MANAGEMENT_PARAMETER_KEYS.get(policy, ())
                }
                parameters["unused"] = "nao_deve_vazar"

                plan = engine.build_plan(
                    MT5ResearchTradePlanInput(
                        symbol="EURUSD",
                        timeframe="H1",
                        decision="BUY",
                        entry_signal_status="SINAL_TEORICO",
                        entry_price=1.1000,
                        atr=0.0010,
                        atr_stop_factor=2.0,
                        research_risk_reward=2.0,
                        active_model="TREND_MOMENTUM",
                        reason="contrato lab forex mt5",
                        stop_management=policy,
                        stop_management_parameters=parameters,
                    )
                )

                self.assertEqual(plan.status, "PLANO_VALIDO")
                self.assertEqual(plan.stop_management, policy)
                expected_parameters = {
                    key: parameters[key]
                    for key in STOP_MANAGEMENT_PARAMETER_KEYS.get(policy, ())
                }
                self.assertEqual(plan.stop_management_parameters, expected_parameters)
                self.assertNotIn("unused", plan.stop_management_parameters)
                self.assertIn(policy, plan.stop_management_reason)

    def test_json_visual_marca_ativo_posicionado_e_candle_de_entrada(self) -> None:
        exporter = MT5VisualSignalExporter()
        exporter._open_positions_by_symbol = lambda: {  # type: ignore[method-assign]
            "EURUSD": {
                "side": "BUY",
                "entry": 1.14181,
                "stop": 1.14067,
                "target": 1.14524,
                "opened_at": "2026.07.06 18:04:04",
                "ticket": 335443769,
                "volume": 0.1,
            }
        }

        payload = exporter.build_payload(
            DashboardMT5ForexSignalViewModel(
                timeframe="H1",
                pairs=[
                    self._row(
                        pair="EURUSD",
                        lab_timeframe="H1",
                        decision="BUY",
                        stop_management="BREAK_EVEN",
                    )
                ],
            )
        )

        signal = payload["signals"][0]
        self.assertEqual(payload["schema_version"], "traderia.mt5.visual_signals.v1")
        self.assertEqual(signal["symbol"], "EURUSD")
        self.assertTrue(signal["is_positioned"])
        self.assertEqual(signal["timestamp"], "2026.07.06 18:04:04")
        self.assertEqual(signal["position_open_time"], "2026.07.06 18:04:04")
        self.assertEqual(signal["position_ticket"], 335443769)
        self.assertEqual(signal["position_volume"], 0.1)
        self.assertEqual(signal["entry"], 1.14181)
        self.assertEqual(signal["stop"], 1.14067)
        self.assertEqual(signal["target"], 1.14524)
        self.assertEqual(signal["stop_management"], "BREAK_EVEN")

    def test_json_visual_identifica_ativo_sem_posicao_para_grafico_limpo(self) -> None:
        exporter = MT5VisualSignalExporter()
        exporter._open_positions_by_symbol = lambda: {}  # type: ignore[method-assign]

        payload = exporter.build_payload(
            DashboardMT5ForexSignalViewModel(
                timeframe="H1",
                pairs=[
                    self._row(
                        pair="GBPUSD",
                        lab_timeframe="M15",
                        decision="SELL",
                        stop_management="ATR_TRAILING_STOP",
                    )
                ],
            )
        )

        signal = payload["signals"][0]
        self.assertFalse(signal["is_positioned"])
        self.assertIsNone(signal["position_open_time"])
        self.assertIsNone(signal["position_ticket"])
        self.assertEqual(signal["timeframe"], "M15")
        self.assertEqual(signal["mt5_source_timeframe"], "H1")
        self.assertEqual(signal["decision"], "SELL")
        self.assertEqual(signal["stop_management"], "ATR_TRAILING_STOP")

    def test_indicador_mt5_so_desenha_grafico_com_posicao_aberta(self) -> None:
        indicator_source = Path("mt5/indicators/TraderIAVisualSignals.mq5").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'ExtractJsonString(block, "robot_status") == "POSICAO_ABERTA_MT5"',
            indicator_source,
        )
        self.assertIn(
            "if(IsPositionedTradeBlock(block))\n"
            "         {\n"
            "            DrawStatusLabel(block, 0);\n"
            "            DrawSignalBlock(block, 0);\n"
            "            return;\n"
            "         }",
            indicator_source,
        )
        self.assertIn(
            "if(signal_timeframe == chart_timeframe)\n"
            "         {\n"
            "            matched_timeframe = true;\n"
            "            return;\n"
            "         }",
            indicator_source,
        )

    def _row(
        self,
        *,
        pair: str,
        lab_timeframe: str,
        decision: str,
        stop_management: str,
    ) -> DashboardMT5ForexSignalRowViewModel:
        return DashboardMT5ForexSignalRowViewModel(
            pair=pair,
            timeframe="H1",
            last_candle_time="2026.07.06 18:00:00",
            decision=decision,
            active_model="TREND_MOMENTUM",
            lab_alpha_id="ALPHA001",
            lab_timeframe=lab_timeframe,
            lab_configuration_source="RESEARCH_LAB",
            lab_parameters={
                "timeframe": lab_timeframe,
                "stop_management": stop_management,
            },
            theoretical_entry_status="SINAL_TEORICO",
            theoretical_entry_candle="2026.07.06 18:00:00",
            theoretical_entry_price=1.1000,
            theoretical_entry_direction=decision,
            research_plan_status="PLANO_VALIDO",
            research_plan_entry_price=1.1000,
            research_plan_stop=1.0980,
            research_plan_target=1.1040,
            research_plan_risk_reward=2.0,
            research_plan_stop_management=stop_management,
            research_plan_stop_management_parameters={},
            research_plan_stop_management_reason="Gestao definida pelo Lab.",
            research_plan_reason="Contrato visual.",
        )

    def _lab_row(
        self,
        *,
        pair: str,
        timeframe: str,
        alpha: str,
        model: str,
    ) -> DashboardMT5HeuristicResearchRowViewModel:
        return DashboardMT5HeuristicResearchRowViewModel(
            pair=pair,
            timeframe=timeframe,
            ideal_timeframe=timeframe,
            recommended_heuristic=model,
            decision="BUY",
            score=0.80,
            confidence=0.70,
            status="APROVADO",
            final_configuration={
                "alpha": alpha,
                "modelo": model,
                "timeframe": timeframe,
                "ema_curta": "20",
                "ema_longa": "50",
                "atr_stop_factor": "2.0",
                "rr": "2.0",
                "stop_management": "FIXED_STOP",
                "momentum_threshold": "0.0",
                "volatility_threshold": "0.0001",
            },
        )

    def _forex_row(self, pair: str, timeframe: str) -> MT5ForexSignalRow:
        return MT5ForexSignalRow(
            pair=pair,
            status="OK",
            last_price=1.1000,
            last_candle_time="2026-07-06T18:00:00+00:00",
            trend="ALTA",
            momentum=0.001,
            volatility=0.001,
            rsi=55.0,
            short_average=1.101,
            long_average=1.100,
            decision="WAIT",
            confidence=0.0,
            reason="Contrato.",
            timeframe=timeframe,
            atr=0.001,
            received_candles=3,
        )

    def _candles(self):
        from domain.candle import Candle

        return [
            Candle("2026-07-06T17:58:00+00:00", 1.0980, 1.0990, 1.0975, 1.0985, 100),
            Candle("2026-07-06T17:59:00+00:00", 1.0985, 1.1000, 1.0980, 1.0995, 120),
            Candle("2026-07-06T18:00:00+00:00", 1.0995, 1.1010, 1.0990, 1.1005, 140),
        ]

    def _parameter_value(self, key: str) -> str:
        if key == "exit_ma_type":
            return "EMA"
        if "period" in key or "bars" in key or "minutes" in key or "window" in key:
            return "14"
        return "2.0"


class _NoLivePositionsExporter(MT5VisualSignalExporter):
    def _open_positions_by_symbol(self) -> dict[str, dict[str, object]]:
        return {}


if __name__ == "__main__":
    unittest.main()
