from __future__ import annotations

import unittest

from application.cost_manager import CostManager


class FakeCostProvider:
    def __init__(self, data: dict[str, object] | None = None) -> None:
        self.data = data or {}

    def get_symbol_cost_data(self, symbol: str) -> dict[str, object]:
        return {"symbol": symbol, **self.data}

    def get_trade_cost_records(
        self,
        *,
        position_id: int | None,
        ticket: int | None,
    ) -> list[dict[str, object]]:
        return [
            {
                "ticket": ticket or 10,
                "profit": 12.0,
                "commission": -1.2,
                "swap": -0.3,
                "fee": -0.1,
            },
            {
                "ticket": 11,
                "profit": -2.0,
                "commission": -0.8,
                "swap": 0.1,
                "fee": 0.0,
            },
        ]


class CostManagerTest(unittest.TestCase):
    def test_symbol_snapshot_completo_calcula_spread_em_dinheiro(self) -> None:
        manager = CostManager(
            FakeCostProvider(
                {
                    "bid": 1.10000,
                    "ask": 1.10012,
                    "spread_points": 12,
                    "swap_long": -3.5,
                    "swap_short": 1.2,
                    "tick_value": 1.0,
                    "tick_size": 0.00001,
                    "contract_size": 100000,
                    "digits": 5,
                    "point": 0.00001,
                }
            )
        )

        snapshot = manager.get_symbol_cost_snapshot("eurusd")

        self.assertEqual(snapshot.symbol, "EURUSD")
        self.assertAlmostEqual(snapshot.spread_price or 0.0, 0.00012)
        self.assertAlmostEqual(snapshot.spread_money_estimate or 0.0, 12.0)
        self.assertEqual(snapshot.swap_long, -3.5)
        self.assertEqual(snapshot.swap_short, 1.2)
        self.assertEqual(snapshot.warnings, ())

    def test_symbol_snapshot_tolera_campos_ausentes(self) -> None:
        snapshot = CostManager(FakeCostProvider({})).get_symbol_cost_snapshot("GBPUSD")

        self.assertEqual(snapshot.symbol, "GBPUSD")
        self.assertIsNone(snapshot.spread_money_estimate)
        self.assertIn("bid indisponivel no MT5", snapshot.warnings)
        self.assertIn("tick_value indisponivel no MT5", snapshot.warnings)

    def test_estimativa_buy_usa_swap_long_sem_comissao_hardcoded(self) -> None:
        manager = CostManager(
            FakeCostProvider(
                {
                    "bid": 1.2,
                    "ask": 1.20010,
                    "tick_value": 1.0,
                    "tick_size": 0.00001,
                    "swap_long": -2.0,
                    "swap_short": 0.5,
                }
            )
        )

        estimate = manager.estimate_trade_cost("EURUSD", 0.1, "BUY")

        self.assertAlmostEqual(estimate.spread_cost or 0.0, 1.0)
        self.assertAlmostEqual(estimate.swap_expected or 0.0, -0.2)
        self.assertIsNone(estimate.commission)
        self.assertIn("commission", estimate.unknown)
        self.assertAlmostEqual(estimate.total_estimated_cost or 0.0, 0.8)

    def test_estimativa_sell_usa_swap_short(self) -> None:
        manager = CostManager(
            FakeCostProvider(
                {
                    "bid": 1.2,
                    "ask": 1.20010,
                    "tick_value": 1.0,
                    "tick_size": 0.00001,
                    "swap_long": -2.0,
                    "swap_short": 0.5,
                }
            )
        )

        estimate = manager.estimate_trade_cost("EURUSD", 0.2, "SELL")

        self.assertAlmostEqual(estimate.swap_expected or 0.0, 0.1)

    def test_custo_real_agrega_profit_comissao_swap_fee(self) -> None:
        cost = CostManager(FakeCostProvider()).get_real_trade_cost(ticket=99)

        self.assertAlmostEqual(cost.profit, 10.0)
        self.assertAlmostEqual(cost.commission, -2.0)
        self.assertAlmostEqual(cost.swap, -0.2)
        self.assertAlmostEqual(cost.fee, -0.1)
        self.assertAlmostEqual(cost.net_profit, 7.7)
        self.assertEqual(cost.deals_count, 2)
        self.assertEqual(cost.tickets, (99, 11))

    def test_custo_real_sem_historico_retorna_zero(self) -> None:
        manager = CostManager(provider=object())

        cost = manager.get_real_trade_cost(ticket=1)

        self.assertEqual(cost.deals_count, 0)
        self.assertEqual(cost.net_profit, 0.0)


if __name__ == "__main__":
    unittest.main()
