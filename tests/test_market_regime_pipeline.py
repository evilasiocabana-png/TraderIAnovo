"""Testes do pipeline de autorizacao por regime de mercado."""

import unittest
from types import SimpleNamespace

from application.market_regime_pipeline import MarketRegimePipeline


class MarketRegimePipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = MarketRegimePipeline()

    def test_autoriza_buy_em_tendencia_de_alta_com_retomada(self) -> None:
        result = self.pipeline.evaluate(
            self._signal(
                decision="BUY",
                trend="ALTA",
                last_price=1.1000,
                ema_fast=1.0990,
                ema_mid=1.0985,
                ema_slow=1.0950,
                momentum=0.001,
            )
        )

        self.assertTrue(result.authorized)
        self.assertEqual(result.state, "BUY_AUTORIZADO")
        self.assertEqual(result.direction, "BUY")

    def test_autoriza_sell_em_tendencia_de_baixa_com_retomada(self) -> None:
        result = self.pipeline.evaluate(
            self._signal(
                decision="SELL",
                trend="BAIXA",
                last_price=1.1000,
                ema_fast=1.1010,
                ema_mid=1.1020,
                ema_slow=1.1050,
                momentum=-0.001,
            )
        )

        self.assertTrue(result.authorized)
        self.assertEqual(result.state, "SELL_AUTORIZADO")
        self.assertEqual(result.direction, "SELL")

    def test_bloqueia_movimento_esticado(self) -> None:
        result = self.pipeline.evaluate(
            self._signal(
                decision="BUY",
                trend="ALTA",
                last_price=1.1300,
                ema_fast=1.1000,
                ema_mid=1.1000,
                ema_slow=1.0950,
                atr=0.001,
                momentum=0.001,
            )
        )

        self.assertFalse(result.authorized)
        self.assertEqual(result.block_reason, "MOVIMENTO_ESTICADO")

    def test_autoriza_buy_no_suporte_do_range(self) -> None:
        result = self.pipeline.evaluate(
            self._signal(
                decision="BUY",
                trend="RANGE",
                last_price=1.1005,
                support=1.1000,
                resistance=1.1200,
                momentum=0.001,
            )
        )

        self.assertTrue(result.authorized)
        self.assertEqual(result.state, "BUY_NO_SUPORTE")

    def test_bloqueia_meio_do_range(self) -> None:
        result = self.pipeline.evaluate(
            self._signal(
                decision="BUY",
                trend="RANGE",
                last_price=1.1100,
                support=1.1000,
                resistance=1.1200,
            )
        )

        self.assertFalse(result.authorized)
        self.assertEqual(result.block_reason, "MEIO_DO_RANGE")

    def test_bloqueia_regime_indefinido(self) -> None:
        result = self.pipeline.evaluate(self._signal(decision="BUY"))

        self.assertFalse(result.authorized)
        self.assertEqual(result.regime, "MARKET_UNDEFINED")
        self.assertEqual(result.block_reason, "REGIME_INDEFINIDO")

    def _signal(self, **overrides: object) -> SimpleNamespace:
        data = {
            "decision": "WAIT",
            "trend": "INDEFINIDA",
            "last_price": None,
            "ema_fast": None,
            "ema_mid": None,
            "ema_slow": None,
            "short_average": None,
            "long_average": None,
            "support": None,
            "resistance": None,
            "momentum": None,
            "rsi": None,
            "atr": 0.002,
        }
        data.update(overrides)
        return SimpleNamespace(**data)


if __name__ == "__main__":
    unittest.main()
