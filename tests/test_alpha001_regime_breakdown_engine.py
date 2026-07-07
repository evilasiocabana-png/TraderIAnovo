"""Testes do breakdown por regime da Alpha 001."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from domain.contracts.strategy_signal import StrategySignal
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_regime_breakdown_engine import (
    Alpha001RegimeBreakdownEngine,
    Alpha001RegimeBreakdownResult,
    Alpha001RegimeMetrics,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha001RegimeBreakdownEngineTest(unittest.TestCase):
    """Valida agrupamento por regime sem alterar a estrategia."""

    def test_resultados_sao_dataclasses_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha001RegimeBreakdownResult))
        self.assertTrue(Alpha001RegimeBreakdownResult.__dataclass_params__.frozen)
        self.assertTrue(is_dataclass(Alpha001RegimeMetrics))
        self.assertTrue(Alpha001RegimeMetrics.__dataclass_params__.frozen)

    def test_agrupa_trades_por_regimes_oficiais(self) -> None:
        result = Alpha001RegimeBreakdownEngine().calculate(
            self._experiment_result(
                [
                    self._signal("BUY", "regime TREND"),
                    self._signal("SELL", "regime RANGE"),
                    self._signal("BUY", "regime VOLATILE"),
                    self._signal("SELL", "regime LOW_LIQUIDITY"),
                    self._signal("WAIT", "regime TREND"),
                ],
            ),
        )

        self.assertEqual(result.regimes["TREND"].total_trades, 1)
        self.assertEqual(result.regimes["RANGE"].total_trades, 1)
        self.assertEqual(result.regimes["VOLATILE"].total_trades, 1)
        self.assertEqual(result.regimes["LOW_LIQUIDITY"].total_trades, 1)

    def test_inclui_regimes_oficiais_mesmo_sem_trades(self) -> None:
        result = Alpha001RegimeBreakdownEngine().calculate(
            self._experiment_result([]),
        )

        self.assertEqual(
            set(result.regimes),
            {"TREND", "RANGE", "VOLATILE", "LOW_LIQUIDITY"},
        )
        self.assertTrue(
            all(metrics.total_trades == 0 for metrics in result.regimes.values())
        )

    def test_sinal_sem_regime_expresso_usa_trend_como_padrao(self) -> None:
        result = Alpha001RegimeBreakdownEngine().calculate(
            self._experiment_result([self._signal("BUY", "sinal aprovado")]),
        )

        self.assertEqual(result.regimes["TREND"].total_trades, 1)

    def test_metricas_financeiras_ficam_neutras_no_contrato_atual(self) -> None:
        result = Alpha001RegimeBreakdownEngine().calculate(
            self._experiment_result([self._signal("BUY", "regime RANGE")]),
        )
        metrics = result.regimes["RANGE"]

        self.assertEqual(metrics.gross_profit, 0.0)
        self.assertEqual(metrics.gross_loss, 0.0)
        self.assertEqual(metrics.net_profit, 0.0)
        self.assertEqual(metrics.win_rate, 0.0)

    def test_resultado_e_imutavel(self) -> None:
        result = Alpha001RegimeBreakdownEngine().calculate(
            self._experiment_result([]),
        )

        with self.assertRaises(FrozenInstanceError):
            result.regimes = {}

    def test_engine_nao_recalcula_metricas_globais_ou_altera_estrategia(
        self,
    ) -> None:
        source = read_source(Path("research/alpha001_regime_breakdown_engine.py"))
        forbidden_fragments = (
            "Alpha001IORBStrategy",
            "Alpha001ResearchResult",
            "Alpha001ProfitEngine",
            "Alpha001DrawdownEngine",
            "Alpha001WinRateEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001ExpectancyEngine",
            "sharpe",
            "sortino",
            ".calculate(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha001_regime_breakdown_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "replay",
            "application.replay_service",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "broker",
            "mt5",
            "MetaTrader5",
            "strategies",
        }
        forbidden_calls = {
            "open",
            "write",
            "run",
            "generate_signal",
            "order_send",
            "execute_order",
            "next_candle",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _experiment_result(
        self,
        signals: list[StrategySignal],
    ) -> Alpha001ExperimentResult:
        return Alpha001ExperimentResult(
            total_candles=len(signals),
            total_signals=len(signals),
            total_buy=len([signal for signal in signals if signal.decision == "BUY"]),
            total_sell=len(
                [signal for signal in signals if signal.decision == "SELL"]
            ),
            total_wait=len(
                [signal for signal in signals if signal.decision == "WAIT"]
            ),
            execution_time_ms=1.0,
            signals=tuple(signals),
        )

    def _signal(self, decision: str, reason: str) -> StrategySignal:
        return StrategySignal(
            decision=decision,
            score=100,
            confidence=1.0,
            reasons=[reason],
        )


if __name__ == "__main__":
    unittest.main()
