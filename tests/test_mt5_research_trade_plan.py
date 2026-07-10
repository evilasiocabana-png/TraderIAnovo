"""Testes do plano de trade MT5 produzido pelo Research Lab."""

import unittest

from research.mt5_research_trade_plan import (
    MT5ResearchTradePlanConfiguration,
    MT5ResearchTradePlanEngine,
    MT5ResearchTradePlanInput,
)


class MT5ResearchTradePlanEngineTest(unittest.TestCase):
    """Valida entrada, stop inicial e alvo sem predefinir saida operacional."""

    def test_cria_plano_buy_sem_saida_predefinida_pelo_research_lab(self) -> None:
        engine = MT5ResearchTradePlanEngine(
            MT5ResearchTradePlanConfiguration(
                exit_candidates=((1.5, 1.5), (2.0, 2.0)),
                minimum_distance_percent=0.001,
            )
        )

        plan = engine.build_plan(
            MT5ResearchTradePlanInput(
                symbol="EURUSD",
                timeframe="H1",
                decision="BUY",
                entry_signal_status="SINAL_TEORICO",
                entry_price=1.1000,
                atr=0.0010,
                active_model="TREND_MOMENTUM",
                reason="gatilho teorico",
            )
        )

        self.assertEqual(plan.status, "PLANO_VALIDO")
        self.assertEqual(plan.source, "RESEARCH_LAB")
        self.assertEqual(plan.exit_model, "INITIAL_RISK_PLAN")
        self.assertEqual(plan.stop_multiplier, 2.0)
        self.assertEqual(plan.risk_reward, 2.0)
        self.assertAlmostEqual(plan.stop or 0.0, 1.0980)
        self.assertAlmostEqual(plan.target or 0.0, 1.1040)
        self.assertEqual(plan.exit_score, 0.0)
        self.assertEqual(plan.exit_candidates, 0)
        self.assertEqual(plan.invalid_reason, "")
        self.assertEqual(plan.rr_current, 2.0)
        self.assertEqual(plan.rr_minimum, 1.5)
        self.assertAlmostEqual(plan.risk_pips, 20.0)
        self.assertAlmostEqual(plan.reward_pips, 40.0)
        self.assertAlmostEqual(plan.risk_percent, 0.1818181818)
        self.assertAlmostEqual(plan.reward_percent, 0.3636363636)
        self.assertIn("2.00x ATR", plan.stop_reason)
        self.assertIn("RR 2.00", plan.target_reason)
        self.assertEqual(plan.exit_model, "INITIAL_RISK_PLAN")
        self.assertEqual(plan.stop_management, "DYNAMIC_POSITION_MANAGER")
        self.assertEqual(plan.beta_id, "LEGACY_CURRENT_EXIT")
        self.assertEqual(plan.beta_mode, "PROTECT_ONLY")
        self.assertIn("Position Manager", plan.stop_management_reason)
        self.assertIn("Position Manager", plan.beta_reason)
        self.assertIn("Entrada teorica valida.", plan.diagnostics)
        self.assertTrue(any("Saida dinamica" in item for item in plan.diagnostics))
        self.assertTrue(any("Risco 20.0 pips" in item for item in plan.diagnostics))
        self.assertTrue(any("Ganho potencial 40.0 pips" in item for item in plan.diagnostics))

    def test_usa_parametros_de_risco_inicial_quando_disponiveis(self) -> None:
        engine = MT5ResearchTradePlanEngine(
            MT5ResearchTradePlanConfiguration(
                exit_candidates=((1.5, 1.5), (2.0, 2.0)),
                minimum_distance_percent=0.001,
            )
        )

        plan = engine.build_plan(
            MT5ResearchTradePlanInput(
                symbol="EURUSD",
                timeframe="H1",
                decision="BUY",
                entry_signal_status="SINAL_TEORICO",
                entry_price=1.1000,
                atr=0.0010,
                atr_stop_factor=2.5,
                research_risk_reward=3.0,
                stop_management="ATR_TRAILING_STOP",
                stop_management_parameters={
                    "atr_trailing_factor": "2.5",
                    "atr_trailing_activation_rr": "1.0",
                    "unused": "ignore",
                },
                active_model="TREND_MOMENTUM",
                reason="cenario vencedor",
            )
        )

        self.assertEqual(plan.status, "PLANO_VALIDO")
        self.assertEqual(plan.stop_multiplier, 2.5)
        self.assertEqual(plan.risk_reward, 3.0)
        self.assertEqual(plan.exit_candidates, 0)
        self.assertAlmostEqual(plan.stop or 0.0, 1.0975)
        self.assertAlmostEqual(plan.target or 0.0, 1.1075)
        self.assertAlmostEqual(plan.risk_pips, 25.0)
        self.assertAlmostEqual(plan.reward_pips, 75.0)
        self.assertEqual(plan.stop_management, "ATR_TRAILING_STOP")
        self.assertEqual(
            plan.stop_management_parameters,
            {
                "atr_trailing_factor": "2.5",
                "atr_trailing_activation_rr": "1.0",
            },
        )
        self.assertIn("Position Manager", plan.stop_management_reason)
        self.assertIn("Hint legado ATR_TRAILING_STOP", plan.stop_management_reason)

    def test_fallback_usa_risco_inicial_padrao_quando_cenario_nao_tem_parametros(self) -> None:
        engine = MT5ResearchTradePlanEngine(
            MT5ResearchTradePlanConfiguration(
                exit_candidates=((1.5, 1.5), (2.0, 2.0)),
                minimum_distance_percent=0.001,
            )
        )

        plan = engine.build_plan(
            MT5ResearchTradePlanInput(
                symbol="EURUSD",
                timeframe="H1",
                decision="BUY",
                entry_signal_status="SINAL_TEORICO",
                entry_price=1.1000,
                atr=0.0010,
                active_model="TREND_MOMENTUM",
                reason="snapshot antigo",
            )
        )

        self.assertEqual(plan.status, "PLANO_VALIDO")
        self.assertEqual(plan.stop_multiplier, 2.0)
        self.assertEqual(plan.risk_reward, 2.0)
        self.assertEqual(plan.exit_candidates, 0)

    def test_cria_plano_sell_com_stop_acima_e_alvo_abaixo(self) -> None:
        plan = MT5ResearchTradePlanEngine().build_plan(
            MT5ResearchTradePlanInput(
                symbol="GBPUSD",
                timeframe="H1",
                decision="SELL",
                entry_signal_status="SINAL_TEORICO",
                entry_price=1.3000,
                atr=0.0020,
                active_model="MA_RSI_FILTER",
                reason="gatilho teorico",
            )
        )

        self.assertEqual(plan.status, "PLANO_VALIDO")
        self.assertLess(plan.target or 0.0, plan.entry_price or 0.0)
        self.assertGreater(plan.stop or 0.0, plan.entry_price or 0.0)

    def test_calcula_pips_de_par_jpy_com_duas_casas(self) -> None:
        plan = MT5ResearchTradePlanEngine(
            MT5ResearchTradePlanConfiguration(
                exit_candidates=((2.0, 2.0),),
                minimum_distance_percent=0.001,
            )
        ).build_plan(
            MT5ResearchTradePlanInput(
                symbol="USDJPY",
                timeframe="M15",
                decision="BUY",
                entry_signal_status="SINAL_TEORICO",
                entry_price=160.00,
                atr=0.10,
                active_model="TREND_MOMENTUM",
                reason="gatilho teorico",
            )
        )

        self.assertAlmostEqual(plan.stop or 0.0, 159.80)
        self.assertAlmostEqual(plan.target or 0.0, 160.40)
        self.assertAlmostEqual(plan.risk_pips, 20.0)
        self.assertAlmostEqual(plan.reward_pips, 40.0)

    def test_nao_cria_plano_sem_gatilho_teorico(self) -> None:
        plan = MT5ResearchTradePlanEngine().build_plan(
            MT5ResearchTradePlanInput(
                symbol="EURUSD",
                timeframe="H1",
                decision="BUY",
                entry_signal_status="SEM_GATILHO_NOVO",
                entry_price=None,
                atr=0.001,
                active_model="TREND_MOMENTUM",
                reason="sem trigger",
            )
        )

        self.assertEqual(plan.status, "SEM_GATILHO_VALIDO")
        self.assertIsNone(plan.stop)
        self.assertIsNone(plan.target)
        self.assertEqual(plan.exit_model, "NONE")
        self.assertEqual(plan.risk_pips, 0.0)
        self.assertEqual(plan.reward_pips, 0.0)
        self.assertEqual(plan.risk_percent, 0.0)
        self.assertEqual(plan.reward_percent, 0.0)
        self.assertIn("Stop ausente", plan.stop_reason)
        self.assertIn("Alvo ausente", plan.target_reason)
        self.assertEqual(plan.invalid_reason, "NO_THEORETICAL_TRIGGER")
        self.assertIn("entry_price", plan.invalid_fields)
        self.assertIn("Regime de mercado", plan.expected_trigger)
        self.assertIn("Aguardar regime de mercado", plan.next_retry)

    def test_ict_nao_bloqueia_plano_demo_quando_gatilho_e_valido(self) -> None:
        plan = MT5ResearchTradePlanEngine().build_plan(
            MT5ResearchTradePlanInput(
                symbol="EURUSD",
                timeframe="H1",
                decision="BUY",
                entry_signal_status="SINAL_TEORICO",
                entry_price=1.1000,
                atr=0.001,
                active_model="TREND_MOMENTUM",
                reason="gatilho teorico",
                certification_demo_allowed=False,
                certification_score=46.0,
                certification_grade="E",
                certification_status="REJEITADA",
                certification_usage="Rejeitada.",
                certification_rejection_reasons=(
                    "Profit Factor abaixo de 1.30.",
                ),
            )
        )

        self.assertEqual(plan.status, "PLANO_VALIDO")
        self.assertEqual(plan.invalid_reason, "")
        self.assertIsNotNone(plan.stop)
        self.assertIsNotNone(plan.target)
        self.assertFalse(plan.certification_demo_allowed)
        self.assertEqual(plan.certification_score, 46.0)
        self.assertEqual(plan.invalid_fields, ())
        self.assertTrue(
            any("nao bloqueia operacao Demo" in item for item in plan.diagnostics)
        )


if __name__ == "__main__":
    unittest.main()
