"""Testes de parametrizacao completa da Alpha 001 IORB."""

import unittest

from alpha.alpha001_config import Alpha001Config
from alpha.alpha001_decision_engine import Alpha001DecisionEngine
from domain.candle import Candle
from domain.contracts.market_snapshot import MarketSnapshot
from strategies.alpha001_iorb_strategy import Alpha001IORBStrategy


class Alpha001ParameterizationTest(unittest.TestCase):
    """Valida configuracao da Alpha 001 por injecao de dependencia."""

    def test_config_padrao_mantem_opening_range_do_playbook(self) -> None:
        config = Alpha001Config()

        self.assertEqual(config.opening_range_start_time, "09:00")
        self.assertEqual(config.opening_range_duration_minutes, 15)
        self.assertEqual(config.opening_range_end_time, "09:15")

    def test_config_declara_todos_parametros_minimos_da_missao(self) -> None:
        config = Alpha001Config(
            opening_range_start_time="10:00",
            opening_range_duration_minutes=20,
            initial_stop_points=70.0,
            initial_target_points=140.0,
            minimum_score=80,
            minimum_confidence=0.8,
            minimum_range_size=30.0,
            minimum_volume=2000.0,
            allowed_regimes=("TREND", "BREAKOUT"),
        )

        self.assertEqual(config.opening_range_end_time, "10:20")
        self.assertEqual(config.initial_stop_points, 70.0)
        self.assertEqual(config.initial_target_points, 140.0)
        self.assertEqual(config.minimum_score, 80)
        self.assertEqual(config.minimum_confidence, 0.8)
        self.assertEqual(config.minimum_range_size, 30.0)
        self.assertEqual(config.minimum_volume, 2000.0)
        self.assertEqual(config.normalized_allowed_regimes(), ("TREND", "BREAKOUT"))

    def test_opening_range_horario_e_duracao_sao_injetados(self) -> None:
        config = Alpha001Config(
            opening_range_start_time="10:00",
            opening_range_duration_minutes=10,
            minimum_range_size=20.0,
            minimum_volume=1000.0,
        )

        decision = Alpha001DecisionEngine(config=config).evaluate(
            candles=[
                self._candle("09:00", 100.0, 300.0, 1.0, 1500),
                self._candle("10:00", 100.0, 120.0, 95.0, 1500),
                self._candle("10:10", 105.0, 118.0, 98.0, 1500),
                self._candle("10:11", 126.0, 128.0, 121.0, 1500),
            ],
            market_snapshot=self._snapshot(),
            current_price=126.0,
        )

        self.assertTrue(decision.approved)
        self.assertEqual(decision.decision, "BUY")

    def test_minimos_de_volatilidade_e_liquidez_vem_da_configuracao(self) -> None:
        config = Alpha001Config(minimum_range_size=40.0, minimum_volume=2000.0)

        decision = Alpha001DecisionEngine(config=config).evaluate(
            candles=self._buy_candles(),
            market_snapshot=self._snapshot(liquidity=1500.0),
            current_price=126.0,
        )

        self.assertFalse(decision.approved)
        self.assertIn("volatilidade insuficiente", decision.reasons)
        self.assertIn("liquidez insuficiente", decision.reasons)

    def test_regimes_permitidos_sao_configuraveis(self) -> None:
        config = Alpha001Config(allowed_regimes=("BREAKOUT",))

        decision = Alpha001DecisionEngine(config=config).evaluate(
            candles=self._buy_candles(),
            market_snapshot=self._snapshot(regime="TREND"),
            current_price=126.0,
        )

        self.assertFalse(decision.approved)
        self.assertIn("regime nao permitido", decision.reasons)

    def test_minimum_score_e_confidence_filtram_strategy_signal(self) -> None:
        config = Alpha001Config(minimum_score=100, minimum_confidence=1.0)
        signal = Alpha001IORBStrategy(config=config).generate_signal(
            candles=self._buy_candles(),
            market_snapshot=self._snapshot(regime="RANGE"),
            current_price=126.0,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("score abaixo do minimo", signal.reasons)
        self.assertIn("confidence abaixo do minimo", signal.reasons)

    def test_overrides_legados_ainda_funcionam_por_chamada(self) -> None:
        decision = Alpha001DecisionEngine().evaluate(
            candles=self._buy_candles(),
            market_snapshot=self._snapshot(),
            current_price=126.0,
            minimum_range_size=40.0,
            minimum_volume=2000.0,
        )

        self.assertFalse(decision.approved)
        self.assertIn("volatilidade insuficiente", decision.reasons)
        self.assertIn("liquidez insuficiente", decision.reasons)

    def _buy_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 126.0, 128.0, 121.0, 1500),
        ]

    def _candle(
        self,
        candle_time: str,
        close: float,
        high: float,
        low: float,
        volume: int,
    ) -> Candle:
        return Candle(
            data=f"2026-06-26 {candle_time}",
            abertura=close,
            maxima=high,
            minima=low,
            fechamento=close,
            volume=volume,
        )

    def _snapshot(
        self,
        regime: str = "TREND",
        liquidity: float = 1500.0,
    ) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-26 09:16",
            regime=regime,
            volatility=30.0,
            liquidity=liquidity,
            trend_strength=0.8,
            market_dna_score=70.0,
        )


if __name__ == "__main__":
    unittest.main()
