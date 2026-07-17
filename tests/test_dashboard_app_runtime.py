import inspect
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

import dashboard_app
from streamlit.testing.v1 import AppTest


class DashboardAppRuntimeTest(unittest.TestCase):
    """Valida renderizacao real do workbench via Streamlit AppTest."""

    def test_curva_patrimonial_rebaseia_trecho_a_partir_do_indice(self) -> None:
        curve = [0.0, 10.0, 5.0, 25.0]

        rebased = dashboard_app._mt5_equity_curve_rebased_from_index(curve, 2)

        self.assertEqual(rebased, [0.0, 20.0])

    def test_historico_mt5_exporta_csv_com_bom_para_excel(self) -> None:
        payload = dashboard_app._table_rows_to_csv_bytes(
            [{"Par": "EURUSD", "Lucro realizado MT5": "1.25"}],
        )

        self.assertTrue(payload.startswith(b"\xef\xbb\xbf"))
        self.assertIn("EURUSD", payload.decode("utf-8-sig"))

    def test_historico_mt5_csv_expande_snapshot_do_plano(self) -> None:
        row = SimpleNamespace(
            symbol="EURUSD",
            mt5_realized_profit=1.25,
            projected_profit=2.0,
            projected_loss=-1.0,
            side="BUY",
            quantity=0.1,
            entry_price=1.1,
            risk_reward=2.0,
            plan_snapshot={
                "alpha_id": "ALPHA123",
                "entry_setup": "ADX_TREND_STRENGTH",
                "entry_price": 1.1,
            },
        )

        output = dashboard_app._mt5_trade_audit_csv_row(row, {})

        self.assertEqual(output["Plano alpha_id"], "ALPHA123")
        self.assertIn("ADX_TREND_STRENGTH", output["Snapshot plano JSON"])

    def test_robo_demo_background_cycle_exige_estado_online_persistido(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous_cwd = os.getcwd()
            previous_flag = os.environ.get("TRADERIA_DEMO_EXECUTION_ENABLED")
            previous_thread_state = dashboard_app.MT5_DEMO_ROBOT_BACKGROUND_THREAD_STARTED
            try:
                os.chdir(temp_dir)
                os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"
                dashboard_app.MT5_DEMO_ROBOT_BACKGROUND_THREAD_STARTED = False

                self.assertFalse(dashboard_app._demo_robot_background_cycle_should_start())
                self.assertFalse(dashboard_app._demo_robot_background_cycle_active())

                state_path = Path(".traderia") / "mt5_demo_robot_online_state.json"
                state_path.parent.mkdir(parents=True, exist_ok=True)
                state_path.write_text(
                    '{"online": true, "pair": "TODOS", "timeframe": "M1"}',
                    encoding="utf-8",
                )

                self.assertTrue(dashboard_app._demo_robot_background_cycle_should_start())
                self.assertFalse(dashboard_app._demo_robot_background_cycle_active())

                dashboard_app.MT5_DEMO_ROBOT_BACKGROUND_THREAD_STARTED = True

                self.assertTrue(dashboard_app._demo_robot_background_cycle_active())
            finally:
                dashboard_app.MT5_DEMO_ROBOT_BACKGROUND_THREAD_STARTED = previous_thread_state
                if previous_flag is None:
                    os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)
                else:
                    os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = previous_flag
                os.chdir(previous_cwd)

    def test_modelo2_visual_inverte_direcao_e_usa_stop_original_como_alvo(
        self,
    ) -> None:
        row = {
            "Par": "EURUSD",
            "Periodo de tempo": "M1",
            "Entrada Teorica": "SINAL_TEORICO",
            "Direcao Teorica": "BUY",
            "Preco Teorico": "1.10000",
            "Stop Research": "1.09500",
            "Alvo Research": "1.11500",
            "Plano Research": "PLANO_VALIDO",
            "Modelo Ativo": "TREND_MOMENTUM",
            "Filtro entrada": "BLOQUEADO",
            "ADX": "19.50",
        }

        model2 = dashboard_app._model2_inverse_entry_row(row)

        self.assertEqual(model2["Direcao Teorica"], "SELL")
        self.assertEqual(model2["Direcao"], "VENDER")
        self.assertEqual(model2["Alvo Research"], "1.095")
        self.assertEqual(model2["Stop Research"], "1.105")
        self.assertEqual(model2["RR Research"], "1.00")
        self.assertIn("MODELO2_ESPELHO_BETA2", model2["Modelo Ativo"])

    def test_modelo2_visual_aguarda_quando_filtro_ruim_ausente(self) -> None:
        row = {
            "Par": "EURUSD",
            "Periodo de tempo": "M1",
            "Entrada Teorica": "SINAL_TEORICO",
            "Direcao Teorica": "BUY",
            "Preco Teorico": "1.10000",
            "Stop Research": "1.09500",
            "Alvo Research": "1.11500",
            "Plano Research": "PLANO_VALIDO",
            "Modelo Ativo": "TREND_MOMENTUM",
            "Filtro entrada": "OK",
            "ADX": "25.00",
            "Zona Operacional": "SUPORTE",
        }

        model2 = dashboard_app._model2_inverse_entry_row(row)

        self.assertEqual(model2["Direcao Teorica"], "WAIT")
        self.assertEqual(model2["Plano Research"], "PLANO_VALIDO")
        self.assertEqual(model2["Codigo Rejeicao"], "N/D")
        self.assertIn("MODELO2_AGUARDA_ADX_BAIXO", model2["Modelo Ativo"])

    def test_modelo2_resumo_trata_filtro_ruim_como_gatilho_de_inversao(self) -> None:
        row = {
            "Par": "EURUSD",
            "Periodo de tempo": "M1",
            "Entrada Teorica": "SINAL_TEORICO",
            "Direcao Teorica": "BUY",
            "Preco Teorico": "1.10000",
            "Ultimo preco": "1.10000",
            "Stop Research": "1.09500",
            "Alvo Research": "1.11500",
            "Plano Research": "PLANO_VALIDO",
            "Modelo Ativo": "TREND_MOMENTUM",
            "Zona Operacional": "SUPORTE",
            "Tendencia": "ALTA",
            "Momentum": "1.00%",
            "RSI": "55.00",
            "Media curta": "1.10100",
            "Media longa": "1.10000",
            "Filtro entrada": "BLOQUEADO",
            "Filtro motivo": "ADX < 20",
            "ADX": "19.50",
        }

        model2 = dashboard_app._model2_inverse_entry_row(row)
        output = dashboard_app._forex_theoretical_entry_row(
            model2,
            robot_online=True,
            mt5_online=True,
            model2_filter_trigger=True,
        )

        self.assertNotIn("BLOQ: Filtro", output["Envio resumo"])
        self.assertIn("gatilho inversao", output["Filtro"])
        self.assertIn("ADX", output["Filtro"])

    def test_entrada_teorica_nao_bloqueia_duplicidade_por_tentativa_rejeitada(
        self,
    ) -> None:
        original_path = dashboard_app.MT5_DEMO_EXECUTION_LOG_PATH
        with tempfile.TemporaryDirectory() as temp_dir:
            dashboard_app.MT5_DEMO_EXECUTION_LOG_PATH = (
                Path(temp_dir) / "mt5_demo_execution.jsonl"
            )
            dashboard_app.MT5_DEMO_EXECUTION_LOG_PATH.write_text(
                (
                    '{"symbol":"EURUSD","side":"BUY","entry_price":1.13837,'
                    '"stop":1.13723163,"target":1.13950837,'
                    '"accepted":false,'
                    '"status":"REJECTED","message":"Plano operacional duplicado",'
                    '"operational_model":"MODELO_2_ESPELHO_BETA2_RR1",'
                    '"plan_identity":"EURUSD|M1|2026-07-14T01:48:00+00:00|'
                    'MODELO2_ESPELHO_BETA2 | PIVOT_REJECTION|TP V5|'
                    'RESEARCH_LAB|PLANO_VALIDO|BETA002|BETA002_ESPELHO_STOP_RR1|'
                    'MODELO_2_ESPELHO_BETA2_RR1"}\n'
                ),
                encoding="utf-8",
            )
            try:
                row = {
                    "Par": "EURUSD",
                    "Periodo de tempo": "M1",
                    "Entrada Teorica": "SINAL_TEORICO",
                    "Direcao Teorica": "BUY",
                    "Preco Teorico": "1.13837",
                    "Ultimo preco": "1.13837",
                    "Stop Research": "1.13723163",
                    "Alvo Research": "1.13950837",
                    "Plano Research": "PLANO_VALIDO",
                    "Modelo Ativo": "MODELO2_ESPELHO_BETA2 | PIVOT_REJECTION",
                    "Candle do Sinal": "2026-07-14T01:48:00+00:00",
                    "Zona Operacional": "SUPORTE",
                    "Tendencia": "ALTA",
                    "Momentum": "1.00%",
                    "RSI": "55.00",
                    "Media curta": "1.10100",
                    "Media longa": "1.10000",
                    "ADX": "25.00",
                }

                output = dashboard_app._forex_theoretical_entry_row(
                    row,
                    robot_online=True,
                    mt5_online=True,
                    model2_filter_trigger=True,
                    operational_model=dashboard_app.MT5_OPERATIONAL_MODEL_2,
                )

                self.assertEqual(output["Duplicidade"], "OK")
                self.assertNotEqual(output["Envio resumo"], "BLOQ: Duplicidade")
            finally:
                dashboard_app.MT5_DEMO_EXECUTION_LOG_PATH = original_path

    def test_entrada_teorica_bloqueia_duplicidade_de_ordem_aceita(self) -> None:
        original_path = dashboard_app.MT5_DEMO_EXECUTION_LOG_PATH
        with tempfile.TemporaryDirectory() as temp_dir:
            dashboard_app.MT5_DEMO_EXECUTION_LOG_PATH = (
                Path(temp_dir) / "mt5_demo_execution.jsonl"
            )
            dashboard_app.MT5_DEMO_EXECUTION_LOG_PATH.write_text(
                (
                    '{"symbol":"EURUSD","side":"BUY","entry_price":1.13837,'
                    '"stop":1.13723163,"target":1.13950837,'
                    '"accepted":true,'
                    '"status":"ACCEPTED","message":"Request executed",'
                    '"operational_model":"MODELO_2_ESPELHO_BETA2_RR1",'
                    '"plan_identity":"EURUSD|M1|2026-07-14T01:48:00+00:00|'
                    'MODELO2_ESPELHO_BETA2 | PIVOT_REJECTION|TP V5|'
                    'RESEARCH_LAB|PLANO_VALIDO|BETA002|BETA002_ESPELHO_STOP_RR1|'
                    'MODELO_2_ESPELHO_BETA2_RR1"}\n'
                ),
                encoding="utf-8",
            )
            try:
                row = {
                    "Par": "EURUSD",
                    "Periodo de tempo": "M1",
                    "Entrada Teorica": "SINAL_TEORICO",
                    "Direcao Teorica": "BUY",
                    "Preco Teorico": "1.13837",
                    "Ultimo preco": "1.13837",
                    "Stop Research": "1.13723163",
                    "Alvo Research": "1.13950837",
                    "Plano Research": "PLANO_VALIDO",
                    "Modelo Ativo": "MODELO2_ESPELHO_BETA2 | PIVOT_REJECTION",
                    "Candle do Sinal": "2026-07-14T01:48:00+00:00",
                    "Zona Operacional": "SUPORTE",
                    "Tendencia": "ALTA",
                    "Momentum": "1.00%",
                    "RSI": "55.00",
                    "Media curta": "1.10100",
                    "Media longa": "1.10000",
                    "ADX": "25.00",
                }

                output = dashboard_app._forex_theoretical_entry_row(
                    row,
                    robot_online=True,
                    mt5_online=True,
                    model2_filter_trigger=True,
                    operational_model=dashboard_app.MT5_OPERATIONAL_MODEL_2,
                )

                self.assertEqual(output["Duplicidade"], "BLOQ: plano ja avaliado")
                self.assertEqual(output["Envio resumo"], "BLOQ: Duplicidade")
            finally:
                dashboard_app.MT5_DEMO_EXECUTION_LOG_PATH = original_path

    def test_modelo2_nao_inverte_com_filtro_bloqueado_sem_adx_baixo(self) -> None:
        row = {
            "Par": "EURUSD",
            "Periodo de tempo": "M1",
            "Entrada Teorica": "SINAL_TEORICO",
            "Direcao Teorica": "BUY",
            "Preco Teorico": "1.10000",
            "Stop Research": "1.09500",
            "Alvo Research": "1.11500",
            "Plano Research": "PLANO_VALIDO",
            "Modelo Ativo": "TREND_MOMENTUM",
            "Filtro entrada": "BLOQUEADO",
            "Filtro motivo": "Momentum contra NV-V +11%",
            "ADX": "25.00",
        }

        model2 = dashboard_app._model2_inverse_entry_row(row)

        self.assertEqual(model2["Direcao Teorica"], "WAIT")
        self.assertEqual(model2["Plano Research"], "PLANO_VALIDO")
        self.assertEqual(model2["Codigo Rejeicao"], "N/D")
        self.assertIn("ADX atual: 25.00", model2["Motivo Entrada"])

    def test_modelo2_resumo_aguarda_filtro_ruim_ausente(self) -> None:
        row = {
            "Par": "EURUSD",
            "Periodo de tempo": "M1",
            "Entrada Teorica": "SINAL_TEORICO",
            "Direcao Teorica": "BUY",
            "Preco Teorico": "1.10000",
            "Stop Research": "1.09500",
            "Alvo Research": "1.11500",
            "Plano Research": "PLANO_VALIDO",
            "Modelo Ativo": "TREND_MOMENTUM",
            "Filtro entrada": "OK",
            "ADX": "25.00",
            "Zona Operacional": "SUPORTE",
        }

        model2 = dashboard_app._model2_inverse_entry_row(row)
        output = dashboard_app._forex_theoretical_entry_row(
            model2,
            robot_online=True,
            mt5_online=True,
            model2_filter_trigger=True,
        )

        self.assertEqual(output["Envio resumo"], "AGUARDA: Filtro")
        self.assertEqual(output["Plano"], "OK")
        self.assertEqual(output["Filtro"], "AGUARDA: ADX 25.00 >= 20")

    def test_chaveamento_operacional_persiste_ultima_escolha(self) -> None:
        original_path = dashboard_app.MT5_OPERATIONAL_MODEL_STATE_PATH
        with tempfile.TemporaryDirectory() as temp_dir:
            dashboard_app.MT5_OPERATIONAL_MODEL_STATE_PATH = (
                Path(temp_dir) / "mt5_operational_model.json"
            )
            try:
                dashboard_app._persist_mt5_operational_model(
                    dashboard_app.MT5_OPERATIONAL_MODEL_ALL,
                )

                loaded = dashboard_app._load_persisted_mt5_operational_model()

                self.assertEqual(loaded, dashboard_app.MT5_OPERATIONAL_MODEL_ALL)
            finally:
                dashboard_app.MT5_OPERATIONAL_MODEL_STATE_PATH = original_path

    def test_workbench_renderiza_layout_profissional_sem_excecoes(self) -> None:
        """Dashboard deve abrir a plataforma de pesquisa quantitativa."""
        app = self._run_app()

        self.assertFalse(app.exception)
        self.assertEqual(
            self._navigation_labels(app),
            [
                "MT5 Forex",
                "Laboratorio de Pesquisa",
                "Replay",
                "Historico MT5",
                "Relatorios",
                "Sistema Forex",
            ],
        )
        self.assertIn("MT5 Forex", self._subheaders(app))
        self.assertIn("Reiniciar", self._buttons(app))
        self.assertIn("MT5 Safe Mode", self._subheaders(app))
        self.assertIn("Replay", self._navigation_labels(app))

    def test_research_lab_exibe_ativos_mt5_e_melhor_heuristica(self) -> None:
        """Research Lab deve focar MT5 e manter Replay legado fora do fluxo."""
        app = self._run_app("Laboratorio de Pesquisa")
        metrics = self._metrics(app)

        self.assertIn("Calibracao Forex MT5", self._subheaders(app))
        self.assertIn("Sugestoes de Setup do Lab", self._subheaders(app))
        self.assertIn(
            "Fluxo correto: MT5 Forex atualiza online sozinho.",
            self._infos(app),
        )
        self.assertIn("Candles historicos", metrics)
        self.assertIn("Melhor constante/modelo", metrics)
        self.assertIn("Pares avaliados", metrics)
        self.assertNotIn("Timeframe Forex", self._selectboxes(app))
        self.assertNotIn("Exportar visual MT5", self._buttons(app))
        self.assertNotIn(
            "Habilitar todos os ativos disponiveis",
            self._checkboxes(app),
        )
        rendered_table = self._markdown(app) + self._dataframe_text(app)
        self.assertIn("EURUSD", rendered_table)
        self.assertIn("GBPUSD", rendered_table)
        self.assertIn("USDCHF", rendered_table)
        self.assertIn("USDJPY", rendered_table)
        self.assertIn("AUDUSD", rendered_table)
        self.assertIn("NZDUSD", rendered_table)
        self.assertIn("EURJPY", rendered_table)
        self.assertIn("USDCAD", rendered_table)
        self.assertIn(self._metrics(app).get("Decisao"), {"BUY", "SELL", "WAIT"})
        self.assertIn("Replay", self._navigation_labels(app))

    def test_workbench_replay_disponivel_na_navegacao_principal(self) -> None:
        """Replay deve estar disponivel para analise Forex par-a-par."""
        app = self._run_app("Replay")

        self.assertFalse(app.exception)
        self.assertIn("Replay", self._navigation_labels(app))
        self.assertIn("Replay Forex", self._subheaders(app))
        self.assertIn("Par Forex do Replay", self._selectboxes(app))
        self.assertIn("Timeframe Forex do Replay", self._selectboxes(app))
        self.assertIn("Carregar par Forex", self._buttons(app))
        self.assertIn("Executar Pesquisa do Par", self._buttons(app))

    def test_sistema_forex_nao_exibe_dataset_legado(self) -> None:
        """Sistema principal deve focar Forex e ocultar PETR4/WDO/Replay."""
        app = self._run_app("Sistema Forex")

        self.assertFalse(app.exception)
        self.assertNotIn("Candles Dataset", self._metrics(app))
        table_text = "\n".join(str(table.value) for table in app.table)
        full_text = "\n".join(
            [
                *self._subheaders(app),
                *self._infos(app),
                table_text,
                self._dataframe_text(app),
            ]
        )
        self.assertIn("Sistema Forex MT5", self._subheaders(app))
        self.assertIn("Configuracao Forex", self._subheaders(app))
        self.assertNotIn("PETR4", full_text)
        self.assertNotIn("WDO", full_text)
        self.assertNotIn("Replay historico", full_text)

    def test_mt5_forex_heuristico_exibe_valores_reais(self) -> None:
        """Painel MT5 deve exibir leitura heuristica, sem Research pesado."""
        row = SimpleNamespace(
            pair="EURUSD",
            status="OK",
            lab_timeframe="M15",
            timeframe="M1",
            last_price=1.12345,
            last_candle_time="2026-07-01T12:00:00+00:00",
            trend="ALTA",
            lab_alpha_id="ALPHA006",
            active_model="ADX_TREND_STRENGTH",
            lab_parameters={
                "ema_curta": 20,
                "ema_longa": 50,
                "rsi_sobrevenda": 30,
                "rsi_sobrecompra": 70,
                "atr_stop_factor": 1.5,
                "rr": 2.0,
            },
            active_model_indicators=("EMA", "ADX", "ATR"),
            momentum=0.01,
            volatility=0.002,
            rsi=55.0,
            short_average=1.12,
            long_average=1.11,
            ema_fast=1.121,
            ema_mid=1.120,
            ema_slow=1.118,
            adx=24.5,
            macd=0.0002,
            macd_signal=0.0001,
            atr=0.0011,
            atr_average=0.0010,
            bollinger_upper=1.13,
            bollinger_lower=1.11,
            tick_volume=1000,
            tick_volume_average=900,
            day_high=1.125,
            day_low=1.119,
            decision="BUY",
            theoretical_entry_status="SINAL_TEORICO",
            theoretical_entry_candle="2026-07-01T12:00:00+00:00",
            theoretical_entry_price=1.1234,
            theoretical_entry_direction="BUY",
            theoretical_entry_reason="Regime autorizado.",
        )
        view_row = dashboard_app._forex_signal_row(row)
        rendered_table = "\n".join([*view_row.keys(), *map(str, view_row.values())])

        for expected in (
            "Ultimo preco",
            "Horario",
            "Tendencia",
            "Alpha Lab",
            "Modelo Ativo",
            "EMA curta Lab",
            "EMA longa Lab",
            "RSI sobrevenda Lab",
            "RSI sobrecompra Lab",
            "ATR stop Lab",
            "RR Lab",
            "Indicadores do modelo",
            "Momentum",
            "Volatilidade",
            "RSI",
            "Media curta",
            "Media longa",
            "EMA rapida",
            "EMA principal",
            "EMA longa",
            "ADX",
            "MACD",
            "MACD signal",
            "ATR",
            "ATR media",
            "Bollinger superior",
            "Bollinger inferior",
            "Tick volume",
            "Tick volume media",
            "Maxima dia",
            "Minima dia",
            "Decisao",
            "Entrada Teorica",
            "Candle do Sinal",
            "Preco Teorico",
            "Direcao Teorica",
            "Motivo Entrada",
            "Candles recebidos",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, rendered_table)
        self.assertNotIn("Confidence calculada", rendered_table)
        for expected in ("EURUSD", "1.12345", "1000"):
            with self.subTest(expected=expected):
                self.assertIn(expected, rendered_table)

    def test_timeframe_optimizer_exibe_none_e_motivo_por_candidato(self) -> None:
        """Tabela deve explicar rejeicoes sem recalcular ranking."""
        candidate = SimpleNamespace(
            symbol="EURUSD",
            timeframe="M5",
            sample_size=10,
            win_rate=0.40,
            profit_factor=0.72,
            max_drawdown=0.03,
            calibrated_confidence=0.24,
            rank_score=0.0,
            rejection_reason="LOW_SAMPLE_SIZE",
        )
        result = SimpleNamespace(
            symbol="EURUSD",
            best_timeframe="NONE",
            selected_reason=(
                "Nenhum timeframe aprovado pelos criterios minimos de pesquisa."
            ),
            candidates=[candidate],
            rejected_candidates=[candidate],
            is_research_only=True,
        )

        summary = dashboard_app._timeframe_optimizer_row(result)
        row = dashboard_app._timeframe_candidate_row(candidate, result)

        self.assertEqual(summary["Melhor timeframe"], "NONE")
        self.assertIn("Nenhum timeframe aprovado", summary["Motivo"])
        self.assertEqual(row["Status"], "REJEITADO")
        self.assertEqual(row["Rejection reason"], "LOW_SAMPLE_SIZE")
        self.assertEqual(row["Selected reason"], result.selected_reason)

    def test_forex_row_exibe_apenas_leitura_heuristica(self) -> None:
        """Tabela Forex deve ficar desconectada do Optimizer."""
        row = SimpleNamespace(
            pair="EURUSD",
            status="OK",
            timeframe="H1",
            last_price=1.12345,
            last_candle_time="29/06/2026 07:00",
            trend="ALTA",
            momentum=0.01,
            volatility=0.002,
            rsi=55.0,
            short_average=1.12,
            long_average=1.11,
            decision="BUY",
            confidence=0.55,
            received_candles=1000,
            last_update="2026-06-29T10:01:00+00:00",
            reason="Heuristica MT5.",
            active_model="TREND_MOMENTUM",
            active_model_indicators=("Tendencia=ALTA", "Momentum=1.00%"),
            ema_fast=1.123,
            ema_mid=1.122,
            ema_slow=1.121,
            adx=26.0,
            macd=0.01,
            macd_signal=0.005,
            atr=0.002,
            atr_average=0.0015,
            bollinger_upper=1.13,
            bollinger_lower=1.11,
            tick_volume=123,
            tick_volume_average=100.0,
            day_high=1.13,
            day_low=1.11,
            theoretical_entry_status="SINAL_TEORICO",
            theoretical_entry_candle="29/06/2026 07:00",
            theoretical_entry_price=1.12345,
            theoretical_entry_direction="BUY",
            theoretical_entry_reason="TREND_MOMENTUM: gatilho teorico.",
            research_plan_status="PLANO_VALIDO",
            research_plan_entry_price=1.12345,
            research_plan_stop=1.12145,
            research_plan_target=1.12745,
            research_plan_risk_reward=2.0,
            research_plan_risk_pips=20.0,
            research_plan_reward_pips=40.0,
            research_plan_risk_percent=0.1780,
            research_plan_reward_percent=0.3560,
            research_plan_exit_model="ATR_RR_RESEARCH_SELECTION",
            research_plan_stop_reason="Stop por ATR.",
            research_plan_target_reason="Alvo por RR.",
            research_plan_stop_management="ATR_TRAILING_STOP",
            research_plan_stop_management_parameters={
                "atr_trailing_factor": "2.0",
                "atr_trailing_activation_rr": "1.0",
            },
            research_plan_stop_management_reason="Gestao definida pelo Lab.",
            research_plan_stop_multiplier=2.0,
            research_plan_exit_score=88.0,
            research_plan_exit_candidates=4,
            research_plan_reason="Research Lab escolheu saida.",
            dynamic_exit_policy="ATR_TRAILING_STOP",
            dynamic_exit_action="TRAIL_BY_ATR",
            dynamic_exit_reason="Read-only: tendencia favorece acompanhamento por ATR.",
            dynamic_exit_confidence=0.65,
            dynamic_exit_market_state="TREND_RUNNER",
            dynamic_exit_r_multiple=1.25,
            dynamic_exit_candidate_stop=1.12200,
            dynamic_exit_allowed_to_execute_demo=False,
            research_plan_invalid_reason="",
            research_plan_invalid_fields=(),
            research_plan_next_retry="Plano pronto.",
            research_plan_expected_trigger="Conta demo habilitada.",
            research_plan_rr_current=2.0,
            research_plan_rr_minimum=1.5,
        )

        view_row = dashboard_app._forex_signal_row(row)

        self.assertEqual(view_row["Periodo de tempo"], "H1")
        self.assertEqual(view_row["Timeframe MT5 lido"], "H1")
        self.assertEqual(view_row["Ultimo preco"], "1.12345")
        self.assertEqual(view_row["Horario"], "29/06/2026 07:00")
        self.assertEqual(view_row["Decisao"], "BUY")
        self.assertEqual(view_row["Modelo Ativo"], "TREND_MOMENTUM")
        self.assertEqual(view_row["Filtro entrada"], "OK_SEM_FILTRO")
        self.assertEqual(view_row["Filtro parametro"], "SEM_FILTRO_ROBUSTO")
        self.assertEqual(view_row["Filtro leitura"], "N/D")
        self.assertIn("Tendencia=ALTA", view_row["Indicadores do modelo"])
        self.assertEqual(view_row["ADX"], "26.00")
        self.assertEqual(view_row["Tick volume"], "123")
        self.assertEqual(view_row["Entrada Teorica"], "SINAL_TEORICO")
        self.assertEqual(view_row["Candle do Sinal"], "29/06/2026 07:00")
        self.assertEqual(view_row["Preco Teorico"], "1.12345")
        self.assertEqual(view_row["Direcao Teorica"], "BUY")
        self.assertEqual(view_row["Plano Research"], "PLANO_VALIDO")
        self.assertEqual(view_row["Stop Research"], "1.12145")
        self.assertEqual(view_row["Alvo Research"], "1.12745")
        self.assertEqual(view_row["RR Research"], "2.00")
        self.assertEqual(view_row["Risco pips"], "20.00")
        self.assertEqual(view_row["Ganho pips"], "40.00")
        self.assertEqual(view_row["Risco %"], "0.1780%")
        self.assertEqual(view_row["Ganho %"], "0.3560%")
        self.assertEqual(view_row["Modelo Saida"], "ATR_RR_RESEARCH_SELECTION")
        self.assertEqual(view_row["Gestao Stop"], "ATR_TRAILING_STOP")
        self.assertEqual(view_row["Politica Saida Lab"], "ATR_TRAILING_STOP")
        self.assertEqual(view_row["Estado Mercado Saida"], "TREND_RUNNER")
        self.assertEqual(view_row["Recomendacao Saida"], "TRAIL_BY_ATR")
        self.assertEqual(view_row["Confianca Saida Dinamica"], "65.00%")
        self.assertEqual(view_row["R Atual Saida"], "1.25")
        self.assertEqual(view_row["Stop Candidato"], "1.12200")
        self.assertIn("atr_trailing_factor=2.0", view_row["Parametros Gestao"])
        self.assertEqual(view_row["Motivo Gestao"], "Gestao definida pelo Lab.")
        self.assertEqual(view_row["Motivo Stop"], "Stop por ATR.")
        self.assertEqual(view_row["Motivo Alvo"], "Alvo por RR.")
        self.assertEqual(view_row["Score Saida"], "88.00")
        self.assertNotIn("Confianca", view_row)
        self.assertNotIn("Melhor timeframe", view_row)
        self.assertNotIn("Rank score", view_row)

        entry_row = dashboard_app._forex_theoretical_entry_row(
            view_row,
            robot_online=True,
            mt5_online=True,
        )

        self.assertEqual(entry_row["Par"], "EURUSD")
        self.assertEqual(entry_row["Sinal"], "OK")
        self.assertEqual(entry_row["Envio resumo"], "PRONTO")
        self.assertEqual(entry_row["Plano"], "OK")
        self.assertEqual(entry_row["Zona gate"], "OK")
        self.assertEqual(entry_row["Robo"], "OK")
        self.assertEqual(entry_row["MT5"], "OK")
        self.assertEqual(entry_row["Filtro"], "OK")
        self.assertEqual(entry_row["Regime"], "OK")
        self.assertEqual(entry_row["Plano vigente"], "OK")
        self.assertEqual(entry_row["Posicao"], "OK")
        columns = list(entry_row)
        self.assertEqual(
            columns[:3],
            ["Par", "Timeframe", "Envio resumo"],
        )
        self.assertEqual(
            columns[
                columns.index("Sinal") : columns.index("Envio") + 1
            ],
            [
                "Sinal",
                "Plano",
                "Zona gate",
                "Robo",
                "MT5",
                "Filtro",
                "Regime",
                "Plano vigente",
                "Posicao",
                "Envio",
            ],
        )
        self.assertEqual(entry_row["Posicao aberta"], "NAO")
        self.assertEqual(entry_row["Direcao posicao"], "N/D")
        self.assertEqual(entry_row["Sinal teorico atual"], "BUY")
        self.assertEqual(entry_row["Confere posicao"], "SEM_POSICAO")
        self.assertEqual(entry_row["Envio"], "PRONTO")
        self.assertEqual(entry_row["Modelo ativo"], "TREND_MOMENTUM")
        self.assertEqual(entry_row["Entrada Teorica"], "SINAL_TEORICO")
        self.assertEqual(entry_row["Candle do Sinal"], "29/06/2026 07:00")
        self.assertEqual(entry_row["Direcao"], "BUY")
        self.assertEqual(entry_row["Plano Research"], "PLANO_VALIDO")
        self.assertEqual(entry_row["RR Minimo"], "1.50")
        self.assertEqual(entry_row["Proxima Tentativa"], "Plano pronto.")
        self.assertEqual(entry_row["Stop Research"], "1.12145")
        self.assertEqual(entry_row["Alvo Research"], "1.12745")

    def test_entrada_teorica_mostra_gate_preco_sl_tp_bloqueado(self) -> None:
        row = {
            "Par": "GBPUSD",
            "Periodo de tempo": "M1",
            "Modelo Ativo": "ADX_TREND_STRENGTH",
            "Zona Operacional": "RESISTENCIA",
            "Entrada Teorica": "SINAL_TEORICO",
            "Ultimo preco": "1.33981",
            "Direcao Teorica": "SELL",
            "Plano Research": "PLANO_VALIDO",
            "Stop Research": "1.33967",
            "Alvo Research": "1.33565",
            "ADX": "25.00",
            "Motivo Entrada": "Gatilho teorico.",
        }

        entry_row = dashboard_app._forex_theoretical_entry_row(
            row,
            robot_online=True,
            mt5_online=True,
        )

        self.assertEqual(entry_row["Sinal"], "OK")
        self.assertEqual(entry_row["Plano"], "OK")
        self.assertEqual(entry_row["Zona gate"], "OK")
        self.assertEqual(
            entry_row["Plano vigente"],
            "BLOQ: preco saiu do plano SELL",
        )
        self.assertEqual(entry_row["Envio"], "BLOQ: Plano vigente")

    def test_entrada_teorica_mostra_filtro_de_liberacao_apos_mt5(self) -> None:
        row = {
            "Par": "AUDUSD",
            "Periodo de tempo": "M1",
            "Modelo Ativo": "ATR_VOLATILITY_REGIME",
            "Zona Operacional": "SUPORTE",
            "Entrada Teorica": "SINAL_TEORICO",
            "Ultimo preco": "0.69570",
            "Direcao Teorica": "BUY",
            "Plano Research": "PLANO_VALIDO",
            "Stop Research": "0.69400",
            "Alvo Research": "0.69900",
            "Filtro entrada": "BLOQUEADO",
            "Filtro motivo": "Filtro NV-V presente: ADX baixo V 10.19% x NV 20.73% | NV-V +10.54% | liberar se ausente",
            "Motivo Entrada": "Gatilho teorico.",
        }

        entry_row = dashboard_app._forex_theoretical_entry_row(
            row,
            robot_online=True,
            mt5_online=True,
        )

        self.assertEqual(entry_row["MT5"], "OK")
        self.assertIn("BLOQ: Filtro NV-V presente", entry_row["Filtro"])
        self.assertEqual(entry_row["Envio"], "BLOQ: Filtro")

    def test_filtro_entrada_usa_nv_menos_v_como_regra_invertida(self) -> None:
        scenario = SimpleNamespace(
            lab_confidence_sample_size=350,
            lab_discrimination_metrics={
                "ADX baixo": {
                    "winner_rate": 0.1019,
                    "loser_rate": 0.2073,
                }
            },
        )

        rules = dashboard_app._mt5_entry_filter_rules_from_scenario(scenario)

        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["source"], "NV-V")
        self.assertFalse(rules[0]["required_present"])
        self.assertEqual(rules[0]["action"], "EXIGIR_AUSENTE")

    def test_filtro_entrada_usa_diferenca_nv_menos_v_acima_de_dois_porcento(
        self,
    ) -> None:
        scenario = SimpleNamespace(
            lab_confidence_sample_size=350,
            lab_discrimination_metrics={
                "ATR subindo": {
                    "winner_rate": 0.4437,
                    "loser_rate": 0.4779,
                },
                "MACD hist divergente": {
                    "winner_rate": 0.0775,
                    "loser_rate": 0.0885,
                },
            },
        )

        rules = dashboard_app._mt5_entry_filter_rules_from_scenario(scenario)

        self.assertEqual([rule["indicator"] for rule in rules], ["ATR subindo"])
        self.assertAlmostEqual(float(rules[0]["entry_edge"]), 0.0342)

    def test_filtro_entrada_ignora_diferenca_nv_menos_v_nao_positiva(self) -> None:
        scenario = SimpleNamespace(
            lab_confidence_sample_size=350,
            lab_discrimination_metrics={
                "ATR subindo": {
                    "winner_rate": 0.5158,
                    "loser_rate": 0.4932,
                },
                "Momentum contra": {
                    "winner_rate": 0.4388,
                    "loser_rate": 0.4388,
                },
            },
        )

        rules = dashboard_app._mt5_entry_filter_rules_from_scenario(scenario)

        self.assertEqual(rules, [])

    def test_entrada_teorica_confere_posicao_aberta_com_sinal_atual(self) -> None:
        row = {
            "Par": "NZDUSD",
            "Periodo de tempo": "M1",
            "Modelo Ativo": "ADX_TREND_STRENGTH",
            "Zona Operacional": "RESISTENCIA",
            "Entrada Teorica": "SINAL_TEORICO",
            "Ultimo preco": "0.57681",
            "Direcao Teorica": "SELL",
            "Plano Research": "PLANO_VALIDO",
            "Stop Research": "0.57760",
            "Alvo Research": "0.57587",
            "ADX": "28.00",
            "Posicao MT5": "SELL",
            "Alpha Lab": "ALPHA006",
            "Motivo Entrada": "Posicao aberta no MT5: SELL",
        }

        entry_row = dashboard_app._forex_theoretical_entry_row(
            row,
            robot_online=True,
            mt5_online=True,
        )

        self.assertEqual(entry_row["Posicao aberta"], "SIM")
        self.assertEqual(entry_row["Direcao posicao"], "SELL")
        self.assertEqual(entry_row["Alpha posicao"], "ALPHA006")
        self.assertEqual(entry_row["Sinal teorico atual"], "SELL")
        self.assertEqual(entry_row["Confere posicao"], "BATE")

    def test_entrada_teorica_mostra_divergencia_da_posicao_aberta(self) -> None:
        row = {
            "Par": "USDJPY",
            "Periodo de tempo": "M1",
            "Modelo Ativo": "MACD_MOMENTUM_SHIFT",
            "Zona Operacional": "SUPORTE",
            "Entrada Teorica": "SINAL_TEORICO",
            "Ultimo preco": "162.365",
            "Direcao Teorica": "BUY",
            "Plano Research": "PLANO_VALIDO",
            "Stop Research": "162.100",
            "Alvo Research": "162.700",
            "ADX": "30.00",
            "Posicao MT5": "SELL",
            "Alpha Lab": "ALPHA007",
            "Motivo Entrada": "Posicao aberta no MT5: SELL",
        }

        entry_row = dashboard_app._forex_theoretical_entry_row(
            row,
            robot_online=True,
            mt5_online=True,
        )

        self.assertEqual(entry_row["Direcao posicao"], "SELL")
        self.assertEqual(entry_row["Sinal teorico atual"], "BUY")
        self.assertEqual(
            entry_row["Confere posicao"],
            "DIVERGIU: posicao SELL x sinal BUY",
        )

    def test_auditoria_mt5_exibe_projecoes_do_app_ao_lado_do_realizado(self) -> None:
        """Lucro/prejuizo projetados devem ficar juntos do lucro realizado MT5."""
        row = SimpleNamespace(
            audit_status="CONFERE",
            operation_status="FECHADA/HISTORICO",
            mt5_source="DEAL",
            timestamp="2026-06-30T21:00:00-03:00",
            symbol="EURUSD",
            side="BUY",
            quantity=0.1,
            projected_profit=10.0,
            projected_loss=-5.0,
            local_ticket=123,
            local_status="ACCEPTED",
            mt5_ticket=123,
            mt5_symbol="EURUSD",
            mt5_side="BUY",
            mt5_volume=0.1,
            mt5_price=1.1,
            mt5_realized_profit=12.34,
            mt5_time="2026-07-01T00:00:00+00:00",
            audit_message="Registro local confere com historico MT5.",
            session_policy_version="v2.1",
            execution_pipeline_version="v3.4",
            lab_configuration_version="v8",
            alpha_id="ALPHA001",
            alpha_version="v1.6",
            trade_plan_version="TP v5",
            execution_engine_version="ExecutionEngine v1",
            indicator_bundle_version="Indicators v9",
            microstructure_version="Micro v2",
            validation_pipeline_version="VAL v4",
            strategy_definition_version="STRAT v3",
            dynamic_exit_policy="ATR_TRAILING_STOP",
            dynamic_exit_action="TRAIL_BY_ATR",
            dynamic_exit_reason="Tendencia forte permite trailing por ATR.",
            dynamic_exit_confidence=0.65,
            dynamic_exit_market_state="TREND_RUNNER",
            dynamic_exit_r_multiple=1.25,
            dynamic_exit_candidate_stop=1.122,
            dynamic_exit_allowed_to_execute_demo=False,
            dynamic_exit_executed_action="NONE",
            dynamic_exit_final_result="POSICAO_ABERTA",
            forex_session="LONDON_NEW_YORK_OVERLAP",
            forex_session_open=True,
            session_filter_result="ALLOWED",
            session_reason="Sessao Londres/NY aberta.",
            operational_model="MODELO_2_ESPELHO_BETA2_RR1",
            entry_setup="PIVOT_REJECTION",
            beta_id="BETA002",
            beta_version="BETA002_ESPELHO_STOP_RR1",
            beta_mode="INVERSE_QUICK_TRADE",
            timeframe="M1",
            risk_reward=1.0,
        )

        view_row = dashboard_app._mt5_trade_audit_row(row)
        columns = list(view_row)

        realized_index = columns.index("Lucro realizado MT5")
        self.assertEqual(
            columns[:7],
            [
                "Confere",
                "Par",
                "Lucro projetado app",
                "Lucro realizado MT5",
                "Prejuizo projetado app",
                "Modelo envio",
                "Parametros",
            ],
        )
        self.assertNotIn("Pontuacao atual", columns)
        self.assertNotIn("Confianca atual", columns)
        self.assertEqual(columns[realized_index - 1], "Lucro projetado app")
        self.assertEqual(columns[realized_index + 1], "Prejuizo projetado app")
        self.assertLess(columns.index("Modelo envio"), columns.index("Mercado aberto"))
        self.assertLess(columns.index("Parametros"), columns.index("Mercado aberto"))
        self.assertLess(realized_index, columns.index("Ticket TraderIA"))
        self.assertEqual(view_row["Lucro realizado MT5"], "12.34")
        self.assertEqual(view_row["Lucro projetado app"], "10.00")
        self.assertEqual(view_row["Prejuizo projetado app"], "-5.00")
        self.assertEqual(view_row["Modelo envio"], "MODELO 2")
        self.assertIn("Alpha ALPHA001 v1.6", view_row["Parametros"])
        self.assertIn("Entrada PIVOT_REJECTION", view_row["Parametros"])
        self.assertIn("Beta BETA002 BETA002_ESPELHO_STOP_RR1", view_row["Parametros"])
        self.assertIn("TF M1", view_row["Parametros"])
        self.assertIn("RR 1.00", view_row["Parametros"])
        self.assertEqual(
            view_row["Mercado aberto"],
            "ABERTO | Sessao: LONDON_NEW_YORK_OVERLAP | ALLOWED | Sessao Londres/NY aberta.",
        )
        self.assertEqual(view_row["Pontuacao Lab"], "N/D")
        self.assertEqual(view_row["Confianca Lab"], "N/D")
        self.assertEqual(view_row["Politica Saida Lab"], "ATR_TRAILING_STOP")
        self.assertEqual(view_row["Recomendacao Saida"], "TRAIL_BY_ATR")
        self.assertEqual(
            view_row["Motivo Saida Dinamica"],
            "Tendencia forte permite trailing por ATR.",
        )
        self.assertEqual(view_row["Confianca Saida Dinamica"], "65.00%")
        self.assertEqual(view_row["Estado Mercado Saida"], "TREND_RUNNER")
        self.assertEqual(view_row["R Atual Saida"], "1.25")
        self.assertEqual(view_row["Stop Candidato"], "1.12200")
        self.assertEqual(view_row["Acao saida executada"], "NONE")
        self.assertEqual(view_row["Resultado saida"], "POSICAO_ABERTA")
        self.assertEqual(view_row["Execucao saida permitida"], "NAO")
        self.assertEqual(view_row["Motor stop ativo"], "POSITION_MANAGER")
        self.assertEqual(view_row["Modo gestao stop"], "READ_ONLY_CANDIDATO")
        self.assertEqual(view_row["Stop movel monitorado"], "SIM")
        self.assertEqual(
            view_row["Mensagem gestao stop"],
            "Stop candidato calculado; execucao demo nao autorizada neste registro.",
        )
        self.assertEqual(view_row["Stop candidato ativo"], "1.12200")
        self.assertNotIn("Simulacao stop", view_row)
        self.assertNotIn("Stop aprovado simulado", view_row)
        self.assertNotIn("Motivo simulacao", view_row)
        self.assertNotIn("SL assistido demo", view_row)
        self.assertNotIn("Mensagem SL assistido", view_row)
        self.assertEqual(view_row["Versao politica sessao"], "v2.1")
        self.assertEqual(view_row["Versao pipeline execucao"], "v3.4")
        self.assertEqual(view_row["Versao config Lab"], "v8")
        self.assertEqual(view_row["Versao Trade Plan"], "TP v5")

    def test_relatorio_resume_position_manager_abaixo_do_historico_mt5(self) -> None:
        rows = [
            SimpleNamespace(
                operation_status="ABERTA",
                dynamic_exit_policy="ATR_TRAILING_STOP",
                dynamic_exit_action="TRAIL_BY_ATR",
                dynamic_exit_candidate_stop=1.122,
                dynamic_exit_allowed_to_execute_demo=False,
                dynamic_exit_final_result="POSICAO_ABERTA",
            )
        ]

        message = dashboard_app._mt5_position_manager_status_message(rows)

        self.assertEqual(
            message,
            (
                "Position Manager: ATIVO monitorando 1 posicao(oes) | "
                "Modo: READ_ONLY_CANDIDATO | "
                "Saida atual: ATR_TRAILING_STOP / TRAIL_BY_ATR | "
                "Stop candidato: 1.12200"
            ),
        )

    def test_relatorio_position_manager_informa_sem_posicao(self) -> None:
        message = dashboard_app._mt5_position_manager_status_message([])

        self.assertEqual(
            message,
            "Position Manager: sem posicao aberta para acompanhar | Saida atual: N/D",
        )

    def test_sugestoes_lab_vazio_mantem_status_estavel(self) -> None:
        message = dashboard_app._mt5_setup_suggestions_status_message(
            [],
            {
                "total": 0,
                "approved": 0,
                "best_confidence": 0.0,
                "best_pair": "N/D",
            },
        )

        self.assertIn("Status Lab: aguardando snapshot", message)
        self.assertEqual(
            list(dashboard_app._mt5_setup_suggestion_empty_row()),
            [
                "Alpha",
                "Beta",
                "Par",
                "TF",
                "Direcao",
                "Setup",
                "Gestao runtime",
                "Plano de risco",
                "Resumo parametros",
                "Encaixe Tecnico",
                "Confirmacao Historica",
                "Janela que confirmou",
                "Status",
            ],
        )

    def test_auditoria_mt5_exibe_pontuacao_e_confianca_lab_por_par(self) -> None:
        row = SimpleNamespace(
            audit_status="CONFERE",
            operation_status="FECHADA/HISTORICO",
            mt5_source="DEAL",
            symbol="EURUSD",
            mt5_realized_profit=12.34,
        )
        metrics = {
            "EURUSD": {
                "score": 0.7519,
                "current_confidence": 0.7519,
                "lab_confidence": 0.55,
            }
        }

        view_row = dashboard_app._mt5_trade_audit_row(row, metrics)

        self.assertEqual(view_row["Pontuacao Lab"], "75.19%")
        self.assertEqual(view_row["Confianca Lab"], "55.00%")

    def test_relatorio_mt5_prefere_pontuacao_fixa_do_lab(self) -> None:
        data = SimpleNamespace(
            mt5_forex_signals=SimpleNamespace(
                pairs=[
                    SimpleNamespace(
                        pair="EURUSD",
                        active_model_score=0.12,
                        confidence=0.34,
                        lab_confidence=0.56,
                    )
                ]
            ),
            mt5_heuristic_research=SimpleNamespace(
                rows=[
                    SimpleNamespace(
                        pair="EURUSD",
                        score=0.7519,
                        confidence=0.55,
                    )
                ]
            ),
        )

        metrics = dashboard_app._mt5_signal_metrics_by_pair(data)

        self.assertEqual(metrics["EURUSD"]["score"], 0.7519)
        self.assertEqual(metrics["EURUSD"]["lab_confidence"], 0.55)

    def test_lab_exibe_confirmacao_historica_sem_confianca_atual(self) -> None:
        row = SimpleNamespace(
            pair="NZDUSD",
            timeframe="M1",
            ideal_timeframe="M5",
            recommended_heuristic="TENDENCIA_MOMENTO",
            final_configuration={"modelo": "TENDENCIA_MOMENTO", "timeframe": "M5"},
            buy_scenario={"timeframe": "M5", "modelo": "TENDENCIA_MOMENTO"},
            buy_score=0.7519,
            sell_scenario={"timeframe": "M15", "modelo": "MA_RSI_FILTER"},
            sell_score=0.6554,
            decision="VENDER",
            score=0.7519,
            confidence=0.55,
            status="APROVADO",
            reason="Historico calibrado.",
        )

        view_row = dashboard_app._mt5_heuristic_research_row(row)

        self.assertEqual(view_row["Confirmacao Historica"], "55.00%")
        self.assertEqual(view_row["Timeframe ideal"], "M5")
        self.assertIn("modelo=TENDENCIA_MOMENTO", view_row["Configuracao usada"])
        self.assertIn("timeframe=M5", view_row["Cenario compra"])
        self.assertIn("timeframe=M15", view_row["Cenario venda"])
        self.assertEqual(view_row["Encaixe compra"], "75.19%")
        self.assertEqual(view_row["Encaixe venda"], "65.54%")
        self.assertNotIn("Confianca atual", view_row)

    def test_lab_melhor_cenario_por_par_usa_um_par_por_linha(self) -> None:
        scenarios = [
            SimpleNamespace(
                alpha_id="ALPHA001",
                pair="EURUSD",
                timeframe="M1",
                model="TREND_MOMENTUM",
                parameters={"rr": "2.0"},
                score=0.82,
                lab_confidence=0.61,
                status="APROVADO",
                decision="BUY",
                reason="Compra aprovada.",
            ),
            SimpleNamespace(
                alpha_id="ALPHA002",
                pair="EURUSD",
                timeframe="M15",
                model="MA_RSI_FILTER",
                parameters={"rr": "1.5"},
                score=0.76,
                lab_confidence=0.70,
                status="APROVADO",
                decision="BUY",
                reason="Compra com confianca alvo.",
            ),
            SimpleNamespace(
                alpha_id="ALPHA003",
                pair="EURUSD",
                timeframe="M5",
                model="MA_RSI_FILTER",
                parameters={"rr": "1.5"},
                score=0.74,
                lab_confidence=0.55,
                status="APROVADO",
                decision="SELL",
                reason="Venda aprovada.",
            ),
            SimpleNamespace(
                alpha_id="ALPHA004",
                pair="EURUSD",
                timeframe="M15",
                model="RSI_REVERSAL",
                parameters={"rr": "1.5"},
                score=0.10,
                lab_confidence=0.30,
                status="REJEITADO",
                decision="WAIT",
                reason="Sem direcao.",
            ),
        ]

        rows = dashboard_app._mt5_best_directional_scenario_rows(scenarios)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Par"], "EURUSD")
        self.assertIn("MA_RSI_FILTER | M15", rows[0]["Compra"])
        self.assertIn("MA_RSI_FILTER | M5", rows[0]["Venda"])
        self.assertIn("RSI_REVERSAL | M15", rows[0]["Lateralidade"])
        self.assertIn("ALPHA002 | MA_RSI_FILTER | M15", rows[0]["Config Compra"])
        self.assertIn("decisao=BUY", rows[0]["Config Compra"])
        self.assertIn("rr=1.5", rows[0]["Config Compra"])
        self.assertIn("ALPHA003 | MA_RSI_FILTER | M5", rows[0]["Config Venda"])
        self.assertIn("decisao=SELL", rows[0]["Config Venda"])
        self.assertIn("ALPHA004 | RSI_REVERSAL | M15", rows[0]["Config Lateral"])
        self.assertIn("decisao=WAIT", rows[0]["Config Lateral"])
        self.assertEqual(rows[0]["Encaixe Compra"], "76.00%")
        self.assertEqual(rows[0]["Encaixe Venda"], "74.00%")
        self.assertEqual(rows[0]["Encaixe Lateral"], "10.00%")
        self.assertEqual(rows[0]["Confirmacao Compra"], "70.00%")
        self.assertEqual(rows[0]["Confirmacao Venda"], "55.00%")
        self.assertEqual(rows[0]["Confirmacao Lateral"], "30.00%")
        self.assertEqual(rows[0]["TF Compra"], "M15")
        self.assertEqual(rows[0]["TF Venda"], "M5")
        self.assertEqual(rows[0]["Alvo de confirmacao"], "70.00%")
        self.assertEqual(rows[0]["Encaixe Alpha001"], "82.00%")
        self.assertEqual(rows[0]["Encaixe Alpha002"], "76.00%")
        self.assertEqual(rows[0]["Encaixe Alpha003"], "74.00%")
        self.assertEqual(rows[0]["Encaixe Alpha004"], "10.00%")
        self.assertEqual(rows[0]["Encaixe Alpha005"], "0.00%")

    def test_evolucao_patrimonial_usa_lucro_realizado_mt5_fechado(self) -> None:
        rows = [
            SimpleNamespace(
                operation_status="ABERTA",
                mt5_found=True,
                mt5_realized_profit=99.0,
                mt5_time="2026-07-01T03:00:00+00:00",
            ),
            SimpleNamespace(
                operation_status="FECHADA/HISTORICO",
                mt5_found=True,
                mt5_realized_profit=-3.4,
                mt5_time="2026-07-01T02:00:00+00:00",
            ),
            SimpleNamespace(
                operation_status="FECHADA/HISTORICO",
                mt5_found=True,
                mt5_realized_profit=2.15,
                mt5_time="2026-07-01T01:00:00+00:00",
            ),
            SimpleNamespace(
                operation_status="NAO_ENCONTRADA",
                mt5_found=False,
                mt5_realized_profit=10.0,
                mt5_time="N/D",
            ),
        ]

        curve = dashboard_app._mt5_realized_equity_curve(rows)

        self.assertEqual(curve, [0.0, 2.15, -1.25])

    def test_resumo_em_negociacao_soma_lucros_das_operacoes_abertas(self) -> None:
        rows = [
            SimpleNamespace(
                operation_status="ABERTA",
                projected_profit=29.91,
                projected_loss=-10.0,
                mt5_realized_profit=7.37,
                mt5_commission=-1.2,
                mt5_swap=-0.3,
                mt5_fee=-0.05,
                mt5_open_cost=-1.55,
                mt5_projected_open_cost=-1.05,
                session_is_rollover=False,
            ),
            SimpleNamespace(
                operation_status="ORDEM_ABERTA",
                projected_profit=34.24,
                projected_loss=-11.41,
                mt5_realized_profit=8.1,
                mt5_commission=-1.0,
                mt5_swap=-0.25,
                mt5_fee=0.0,
                mt5_open_cost=-1.25,
                mt5_projected_open_cost=-0.95,
                session_is_rollover=True,
            ),
        ]

        summary = dashboard_app._mt5_open_profit_summary(rows)

        self.assertEqual(summary["Lucro projetado aberto"], "64.15")
        self.assertEqual(summary["Custo aberto"], "-2.80")
        self.assertEqual(summary["Custo aberto projetado"], "-2.00")
        self.assertEqual(summary["Risco em aberto"], "-21.41")
        self.assertEqual(summary["Lucro MT5 aberto"], "15.47")
        self.assertEqual(summary["Rollover custo"], "COM ROLLOVER")

    def test_auditoria_mt5_mostra_custo_aberto_por_operacao_aberta(self) -> None:
        open_row = SimpleNamespace(
            audit_status="CONFERE",
            operation_status="ABERTA",
            symbol="GBPUSD",
            projected_profit=105.37,
            projected_loss=-42.91,
            mt5_realized_profit=7.6,
            mt5_commission=-1.25,
            mt5_swap=-0.4,
            mt5_fee=-0.05,
            mt5_open_cost=-1.70,
            mt5_projected_open_cost=-0.75,
            session_is_rollover=False,
        )
        closed_row = SimpleNamespace(
            audit_status="CONFERE",
            operation_status="FECHADA/HISTORICO",
            symbol="GBPUSD",
            projected_profit=105.37,
            projected_loss=-42.91,
            mt5_realized_profit=7.6,
            mt5_commission=-1.25,
            mt5_swap=-0.4,
            mt5_fee=-0.05,
            mt5_open_cost=-1.70,
            mt5_projected_open_cost=-0.75,
            session_is_rollover=True,
        )

        open_view = dashboard_app._mt5_trade_audit_row(open_row)
        closed_view = dashboard_app._mt5_trade_audit_row(closed_row)

        self.assertEqual(open_view["Lucro projetado aberto"], "105.37")
        self.assertEqual(open_view["Custo aberto projetado"], "-0.75")
        self.assertEqual(open_view["Custo aberto"], "-1.70")
        self.assertEqual(open_view["Corretagem aberta"], "-1.25")
        self.assertEqual(open_view["Swap aberto"], "-0.40")
        self.assertEqual(open_view["Fee aberta"], "-0.05")
        self.assertEqual(open_view["Risco em aberto"], "-42.91")
        self.assertEqual(open_view["Lucro MT5 aberto"], "7.60")
        self.assertEqual(open_view["Rollover custo"], "SEM ROLLOVER")
        self.assertEqual(closed_view["Lucro projetado aberto"], "N/D")
        self.assertEqual(closed_view["Custo aberto projetado"], "N/D")
        self.assertEqual(closed_view["Custo aberto"], "N/D")
        self.assertEqual(closed_view["Corretagem aberta"], "N/D")
        self.assertEqual(closed_view["Swap aberto"], "N/D")
        self.assertEqual(closed_view["Fee aberta"], "N/D")
        self.assertEqual(closed_view["Risco em aberto"], "N/D")
        self.assertEqual(closed_view["Lucro MT5 aberto"], "N/D")
        self.assertEqual(closed_view["Rollover custo"], "N/D")

    def test_historico_mt5_colore_vencedoras_e_perdedoras(self) -> None:
        pd = __import__("pandas")

        winner_style = dashboard_app._mt5_history_result_row_style(
            pd.Series({"Lucro realizado MT5": "12.34", "Ticket MT5": "1"})
        )
        loser_style = dashboard_app._mt5_history_result_row_style(
            pd.Series({"Lucro realizado MT5": "-5.77", "Ticket MT5": "2"})
        )
        neutral_style = dashboard_app._mt5_history_result_row_style(
            pd.Series({"Lucro realizado MT5": "0.00", "Ticket MT5": "3"})
        )

        self.assertIn("#DDF7E3", winner_style[0])
        self.assertIn("#FDE0E0", loser_style[0])
        self.assertIn("#FFFFFF", neutral_style[0])

    def test_historico_mt5_usa_ordem_visual_do_mt5_por_horario(self) -> None:
        rows = [
            SimpleNamespace(mt5_time="2026-07-01T03:01:59+00:00", timestamp="B"),
            SimpleNamespace(mt5_time="2026-07-01T02:18:28+00:00", timestamp="A"),
            SimpleNamespace(mt5_time="2026-07-01T04:54:12+00:00", timestamp="C"),
        ]

        sorted_rows = dashboard_app._sorted_mt5_rows_like_mt5(rows)

        self.assertEqual(
            [row.mt5_time for row in sorted_rows],
            [
                "2026-07-01T02:18:28+00:00",
                "2026-07-01T03:01:59+00:00",
                "2026-07-01T04:54:12+00:00",
            ],
        )

    def test_em_negociacao_mt5_usa_ordem_visual_do_mt5_por_horario(self) -> None:
        rows = [
            SimpleNamespace(mt5_time="2026-07-01T07:44:25+00:00", symbol="USDCAD"),
            SimpleNamespace(mt5_time="2026-07-01T03:37:42+00:00", symbol="USDJPY"),
            SimpleNamespace(mt5_time="2026-07-01T07:29:16+00:00", symbol="NZDUSD"),
        ]

        sorted_rows = dashboard_app._sorted_mt5_rows_like_mt5(rows)

        self.assertEqual(
            [row.symbol for row in sorted_rows],
            ["USDJPY", "NZDUSD", "USDCAD"],
        )

    def test_historico_mt5_destaca_ultima_negociacao_por_horario_mt5(self) -> None:
        rows = [
            SimpleNamespace(mt5_time="2026-07-01T03:01:59+00:00", symbol="USDCAD"),
            SimpleNamespace(mt5_time="2026-07-01T02:18:28+00:00", symbol="EURJPY"),
            SimpleNamespace(mt5_time="2026-07-01T04:54:12+00:00", symbol="AUDUSD"),
        ]

        latest = dashboard_app._latest_mt5_history_row(rows)

        self.assertEqual(latest.symbol, "AUDUSD")
        self.assertEqual(latest.mt5_time, "2026-07-01T04:54:12+00:00")

    def test_evolucao_patrimonial_usa_saldo_inicial_e_data_inicial(self) -> None:
        rows = [
            SimpleNamespace(
                operation_status="FECHADA/HISTORICO",
                mt5_found=True,
                mt5_realized_profit=10.0,
                mt5_time="2026-06-30T23:59:00+00:00",
            ),
            SimpleNamespace(
                operation_status="FECHADA/HISTORICO",
                mt5_found=True,
                mt5_realized_profit=-3.5,
                mt5_time="2026-07-01T01:00:00+00:00",
            ),
            SimpleNamespace(
                operation_status="FECHADA/HISTORICO",
                mt5_found=True,
                mt5_realized_profit=2.0,
                mt5_time="2026-07-01T02:00:00+00:00",
            ),
        ]

        curve = dashboard_app._mt5_realized_equity_curve(
            rows,
            initial_balance=50000.0,
            start_date=dashboard_app.date(2026, 7, 1),
        )

        self.assertEqual(curve, [50000.0, 49996.5, 49998.5])

    def test_evolucao_patrimonial_filtra_por_modelo_operacional(self) -> None:
        rows = [
            SimpleNamespace(operational_model="MODELO_1_ALPHA_ATUAL"),
            SimpleNamespace(operational_model="MODELO_2_ESPELHO_BETA2_RR1"),
            SimpleNamespace(operational_model="MODELO_3_RR3"),
            SimpleNamespace(operational_model="MODELO_4_ESPELHO_M1"),
            SimpleNamespace(operational_model="MODELO_5_PRICE_ACTION"),
            SimpleNamespace(operational_model="N/D"),
            SimpleNamespace(
                operational_model="N/D",
                plan_snapshot={"operational_model": "MODELO_2_ESPELHO_BETA2_RR1"},
            ),
        ]

        model0 = dashboard_app._mt5_rows_for_equity_model_filter(rows, "MODELO 0")
        model1 = dashboard_app._mt5_rows_for_equity_model_filter(rows, "MODELO 1")
        model2 = dashboard_app._mt5_rows_for_equity_model_filter(rows, "MODELO 2")
        model3 = dashboard_app._mt5_rows_for_equity_model_filter(rows, "MODELO 3")
        model4 = dashboard_app._mt5_rows_for_equity_model_filter(rows, "MODELO 4")
        model5 = dashboard_app._mt5_rows_for_equity_model_filter(rows, "MODELO 5")

        self.assertEqual(model0, [rows[5]])
        self.assertEqual(model1, [rows[0]])
        self.assertEqual(model2, [rows[1], rows[6]])
        self.assertEqual(model3, [rows[2]])
        self.assertEqual(model4, [rows[3]])
        self.assertEqual(model5, [rows[4]])

    def test_saldo_inicial_mt5_default_visual_e_zero(self) -> None:
        source = inspect.getsource(dashboard_app._exibir_evolucao_patrimonial_mt5)

        self.assertIn("default_balance = 0.0", source)
        self.assertNotIn('default_balance = float(getattr(report, "mt5_account_balance"', source)

    def test_forex_row_style_colore_linha_por_decisao(self) -> None:
        """BUY deve ficar verde, SELL vermelho e WAIT branco."""
        buy_style = dashboard_app._forex_decision_row_style({"Decisao": "BUY"})
        sell_style = dashboard_app._forex_decision_row_style({"Decisao": "SELL"})
        wait_style = dashboard_app._forex_decision_row_style({"Decisao": "WAIT"})

        self.assertIn("#DDF7E3", buy_style[0])
        self.assertIn("#FDE0E0", sell_style[0])
        self.assertIn("#FFFFFF", wait_style[0])

    def test_forex_row_style_destaca_indicadores_do_modelo_ativo(self) -> None:
        """Somente indicadores do modelo ativo devem ficar azuis."""
        pd = __import__("pandas")
        row = pd.Series(
            {
                "Modelo Ativo": "MA_RSI_FILTER",
                "Tendencia": "ALTA",
                "Momentum": "1.00%",
                "Volatilidade": "0.20%",
                "RSI": "55.00",
                "Media curta": "1.12000",
                "Media longa": "1.11000",
                "Decisao": "BUY",
            }
        )

        styles = dict(zip(row.index, dashboard_app._forex_decision_row_style(row)))

        self.assertIn("#DBEAFE", styles["RSI"])
        self.assertIn("#DBEAFE", styles["Media curta"])
        self.assertIn("#DBEAFE", styles["Media longa"])
        self.assertIn("#DDF7E3", styles["Tendencia"])
        self.assertIn("#DDF7E3", styles["Decisao"])

    def test_forex_decision_counts_usa_mesma_base_da_tabela(self) -> None:
        """Cards BUY/SELL/WAIT devem contar exatamente as linhas exibidas."""
        rows = [
            {"Decisao": "BUY"},
            {"Decisao": " buy "},
            {"Decisao": "SELL"},
            {"Decisao": "WAIT"},
            {"Decisao": "N/D"},
        ]

        counts = dashboard_app._forex_decision_counts(rows)

        self.assertEqual(counts["BUY"], 2)
        self.assertEqual(counts["SELL"], 1)
        self.assertEqual(counts["WAIT"], 2)

    def test_robo_demo_monitor_row_eh_compacto_e_usa_timeframe_ativo(self) -> None:
        """Monitor do robo deve mostrar todos os pares sem tabela larga demais."""
        row = {
            "Par": "EURUSD",
            "Timeframe": "H1",
            "Modelo Ativo": "TREND_MOMENTUM",
            "Decisao": "BUY",
            "Entrada Teorica": "SEM_GATILHO_NOVO",
            "Plano Research": "SEM_GATILHO_VALIDO",
            "Stop Research": "N/D",
            "Alvo Research": "N/D",
            "RR Research": "0.00",
            "RR Minimo": "1.50",
            "Codigo Rejeicao": "NO_THEORETICAL_TRIGGER",
            "Gatilho Esperado": "Regime de mercado deve autorizar BUY ou SELL.",
        }

        monitor_row = dashboard_app._demo_robot_monitor_row(row)

        self.assertEqual(monitor_row["TF ativo"], "H1")
        self.assertEqual(monitor_row["Decisao"], "BUY")
        self.assertEqual(monitor_row["Entrada"], "NAO")
        self.assertEqual(monitor_row["Plano"], "NAO")
        self.assertEqual(monitor_row["Stop/Alvo"], "N/D")
        self.assertEqual(monitor_row["RR min"], "1.50")
        self.assertEqual(monitor_row["Status robo"], "AGUARDANDO")
        self.assertEqual(monitor_row["Bloqueio"], "NO_THEORETICAL_TRIGGER")
        self.assertIn("Regime de mercado", monitor_row["Proximo"])
        self.assertNotIn("Motivo", monitor_row)
        self.assertNotIn("Timeframe", monitor_row)

    def test_saida_teorica_mt5_mostra_beta002_para_posicao_aberta(self) -> None:
        """Saida teorica deve resumir BETA002 sem depender de historico fechado."""
        row = SimpleNamespace(
            symbol="EURUSD",
            side="BUY",
            mt5_side="BUY",
            position_manager_action="FULL_EXIT",
            position_manager_status="POSITION_HELD",
            position_manager_message="BETA002 EXIT_CANDIDATE: acao FULL_EXIT.",
            final_exit_reason="BETA002_EXIT_CANDIDATE",
            dynamic_exit_r_multiple=-0.35,
            dynamic_exit_candidate_stop=None,
            dynamic_exit_allowed_to_execute_demo=False,
            beta_strength_score=-0.72,
            beta_confirmation_count=4,
            beta_state_duration=4,
            beta_ema14_value=1.10123,
            beta_ema14_slope=-0.25,
            beta_momentum_14=-0.31,
            beta_atr_14=0.0012,
            beta_atr_relative_change=-0.12,
            beta_structure_signal="AGAINST",
            beta_evaluated_at="2026-07-13T10:00:00",
            beta_closed_candle_time="2026-07-13T09:59:00",
            mt5_price=1.1001,
            entry_price=1.1020,
            stop=1.0990,
            mt5_stop=1.0990,
            target=1.1060,
            beta_id="BETA002",
            alpha_id="ALPHA006",
            entry_setup="ADX_TREND_STRENGTH",
            exit_setup="ATR_TRAILING_STOP",
            operational_model="MODELO_2_ESPELHO_BETA2_RR1",
        )
        signal_by_pair = {
            "EURUSD": {
                "Periodo de tempo": "M1",
                "Alpha Lab": "ALPHA006",
                "Beta Lab": "BETA002",
            }
        }

        output = dashboard_app._mt5_theoretical_exit_row(row, signal_by_pair)

        self.assertEqual(output["Lado"], "COMPRAR")
        self.assertEqual(output["Cenario BETA002"], "TARGET_STOP_ORIGINAL_RR1")
        self.assertEqual(output["TF Entrada Lab"], "M1")
        self.assertEqual(output["TF Saida Beta"], "M1")
        self.assertEqual(output["Modelo entrada"], "ADX_TREND_STRENGTH")
        self.assertEqual(output["Modelo saida"], "BETA002_ESPELHO_STOP_RR1")
        self.assertEqual(output["Beta"], "BETA002")
        self.assertNotEqual(output["Ultimo candle fechado"], "N/D")
        self.assertEqual(output["Gestao stop"], "FIXO_STOP_ORIGINAL_RR1")
        self.assertEqual(output["Movimento SL"], "FIXO")
        self.assertEqual(output["Modelo envio"], "MODELO 2")
        self.assertIn("FULL_EXIT", output["Leitura programada"])
        self.assertEqual(
            dashboard_app._mt5_theoretical_exit_cell_class(output, "Momentum14"),
            "",
        )
        self.assertEqual(
            dashboard_app._mt5_theoretical_exit_cell_class(output, "Estrutura"),
            "",
        )

    def test_saida_teorica_modelo2_nao_herda_beta_do_modelo1(self) -> None:
        row = SimpleNamespace(
            symbol="EURUSD",
            side="BUY",
            mt5_side="BUY",
            stop=1.0900,
            mt5_stop=1.0900,
            target=1.1300,
            beta_id="BETA004",
            alpha_id="ALPHA011",
            entry_setup="PIVOT_REJECTION",
            exit_setup="BREAK_EVEN",
            operational_model="N/D",
        )
        signal_by_pair = {
            "EURUSD": {
                "Periodo de tempo": "M1",
                "Alpha Lab": "ALPHA011",
                "Beta Lab": "BETA004",
                "Modelo Ativo": "PIVOT_REJECTION",
                "Direcao Teorica": "BUY",
                "Direcao": "COMPRAR",
                "Preco Teorico": "1.10000",
                "Stop Research": "1.09000",
                "Alvo Research": "1.12000",
                "Plano Research": "PLANO_VALIDO",
            }
        }

        output = dashboard_app._mt5_theoretical_exit_row(
            row,
            signal_by_pair,
            display_model=dashboard_app.MT5_OPERATIONAL_MODEL_2,
        )

        self.assertEqual(output["Lado"], "COMPRAR")
        self.assertEqual(output["Beta"], "BETA002")
        self.assertEqual(output["Modelo saida"], "BETA002_ESPELHO_STOP_RR1")
        self.assertEqual(output["Cenario BETA002"], "TARGET_STOP_ORIGINAL_RR1")
        self.assertEqual(output["Gestao stop"], "FIXO_STOP_ORIGINAL_RR1")
        self.assertEqual(output["Movimento SL"], "FIXO")
        self.assertEqual(output["Modelo envio"], "MODELO 2")
        self.assertEqual(output["Stop inicial"], "1.11000")
        self.assertEqual(output["Alvo"], "1.09000")

    def test_saida_teorica_modelo4_mostra_espelho_do_m1(self) -> None:
        row = SimpleNamespace(
            symbol="EURUSD",
            side="SELL",
            mt5_side="SELL",
            stop=1.1200,
            mt5_stop=1.1200,
            target=1.0900,
            beta_id="BETA004",
            alpha_id="ALPHA011",
            entry_setup="PIVOT_REJECTION",
            exit_setup="BETA004_ESPELHO_M1",
            operational_model="MODELO_4_ESPELHO_M1",
        )
        signal_by_pair = {
            "EURUSD": {
                "Periodo de tempo": "M1",
                "Alpha Lab": "ALPHA011",
                "Beta Lab": "BETA004",
                "Modelo Ativo": "PIVOT_REJECTION",
                "Direcao Teorica": "BUY",
                "Direcao": "COMPRAR",
                "Preco Teorico": "1.10000",
                "Stop Research": "1.09000",
                "Alvo Research": "1.12000",
                "Plano Research": "PLANO_VALIDO",
            }
        }

        output = dashboard_app._mt5_theoretical_exit_row(
            row,
            signal_by_pair,
            display_model=dashboard_app.MT5_OPERATIONAL_MODEL_1,
        )

        self.assertEqual(output["Lado"], "VENDER")
        self.assertEqual(output["Beta"], "BETA004")
        self.assertEqual(output["Modelo saida"], "BETA004_ESPELHO_M1")
        self.assertEqual(output["Cenario BETA002"], "ESPELHO_M1_STOP_ALVO_TROCADOS")
        self.assertEqual(output["Gestao stop"], "FIXO_ESPELHO_M1")
        self.assertEqual(output["Movimento SL"], "FIXO")
        self.assertEqual(output["Modelo envio"], "MODELO 4")
        self.assertEqual(output["Stop inicial"], "1.12000")
        self.assertEqual(output["Alvo"], "1.09000")

    def test_saida_teorica_m3_usa_plano_da_ordem_aberta(self) -> None:
        row = SimpleNamespace(
            symbol="EURJPY",
            side="BUY",
            mt5_side="BUY",
            operational_model=dashboard_app.MT5_OPERATIONAL_MODEL_3,
            timeframe="M15",
            alpha_id="ALPHA007",
            beta_id="BETA006",
            beta_version="CHANDELIER_STOP_MANAGER",
            entry_setup="MODELO3_RR3 | MACD_MOMENTUM_SHIFT",
            exit_setup="CHANDELIER_EXIT",
            stop=185.417,
            mt5_stop=185.417,
            target=186.159,
            entry_price=185.611,
            mt5_price=185.780,
            plan_snapshot={
                "timeframe": "M15",
                "alpha_id": "ALPHA007",
                "beta_id": "BETA006",
                "entry_setup": "MODELO3_RR3 | MACD_MOMENTUM_SHIFT",
                "exit_setup": "CHANDELIER_EXIT",
                "initial_stop": 185.417,
                "target": 186.159,
            },
        )
        signal_by_pair = {
            "EURJPY": {
                "Periodo de tempo": "M1",
                "Alpha Lab": "ALPHA009",
                "Beta Lab": "BETA004",
                "Modelo Ativo": "ATR_VOLATILITY_REGIME",
                "Modelo Saida": "BREAK_EVEN",
                "Stop Research": "185.76000",
                "Alvo Research": "185.20200",
            }
        }

        output = dashboard_app._mt5_theoretical_exit_row(row, signal_by_pair)

        self.assertEqual(output["Modelo"], "MODELO 3")
        self.assertEqual(output["TF Entrada Lab"], "M15")
        self.assertEqual(output["TF Saida Beta"], "M15")
        self.assertEqual(output["Alpha"], "ALPHA007")
        self.assertEqual(output["Beta"], "BETA006")
        self.assertEqual(output["Modelo entrada"], "MODELO3_RR3 | MACD_MOMENTUM_SHIFT")
        self.assertEqual(output["Modelo saida"], "CHANDELIER_EXIT")
        self.assertEqual(output["Stop inicial"], "185.41700")
        self.assertEqual(output["Alvo"], "186.15900")

    def test_saida_teorica_usa_modelo_gravado_na_ordem_antes_do_chaveamento(self) -> None:
        row = SimpleNamespace(
            symbol="EURUSD",
            operational_model="MODELO_1_ALPHA_ATUAL",
        )

        effective_model = dashboard_app._mt5_theoretical_exit_effective_model(
            row,
            dashboard_app.MT5_OPERATIONAL_MODEL_2,
        )

        self.assertEqual(effective_model, dashboard_app.MT5_OPERATIONAL_MODEL_1)

    def test_saida_teorica_legada_usa_chaveamento_como_fallback(self) -> None:
        row = SimpleNamespace(symbol="EURUSD", operational_model="N/D")

        effective_model = dashboard_app._mt5_theoretical_exit_effective_model(
            row,
            dashboard_app.MT5_OPERATIONAL_MODEL_2,
        )

        self.assertEqual(effective_model, dashboard_app.MT5_OPERATIONAL_MODEL_2)

    def test_saida_teorica_mt5_diferencia_hold_e_protect(self) -> None:
        """Cenarios operacionais devem ficar limitados a HOLD, PROTECT e FULL_EXIT."""
        hold = SimpleNamespace(
            position_manager_action="HOLD_POSITION",
            position_manager_status="POSITION_HELD",
            final_exit_reason="N/D",
            dynamic_exit_candidate_stop=None,
        )
        protect = SimpleNamespace(
            position_manager_action="STOP_MOVED",
            position_manager_status="STOP_MOVED",
            final_exit_reason="N/D",
            dynamic_exit_candidate_stop=1.2345,
        )

        self.assertEqual(dashboard_app._mt5_theoretical_exit_scenario(hold), "HOLD")
        self.assertEqual(
            dashboard_app._mt5_theoretical_exit_scenario(protect),
            "PROTECT",
        )

    def test_saida_teorica_mt5_ignora_linha_sem_simbolo_real(self) -> None:
        """Saida teorica nao deve exibir saldo/linhas N/D apos reiniciar navegador."""
        invalid = SimpleNamespace(
            symbol="N/D",
            mt5_symbol="N/D",
            local_ticket=None,
            mt5_ticket=None,
        )
        valid = SimpleNamespace(
            symbol="EURUSD",
            mt5_symbol="EURUSD",
            local_ticket=123,
            mt5_ticket=123,
        )

        self.assertFalse(dashboard_app._is_valid_mt5_theoretical_exit_row(invalid))
        self.assertTrue(dashboard_app._is_valid_mt5_theoretical_exit_row(valid))

    def test_saida_teorica_mt5_separa_tf_entrada_do_tf_saida_beta2(self) -> None:
        """Entrada pode ser H1, mas BETA002 deve declarar saida em M1."""
        row = SimpleNamespace(
            symbol="EURUSD",
            side="SELL",
            mt5_side="SELL",
            position_manager_action="HOLD_POSITION",
            position_manager_status="POSITION_HELD",
            position_manager_message="BETA002 HEALTHY: acao HOLD_POSITION.",
            final_exit_reason="N/D",
            dynamic_exit_r_multiple=0.10,
            dynamic_exit_candidate_stop=None,
            dynamic_exit_allowed_to_execute_demo=False,
            beta_strength_score=0.55,
            beta_confirmation_count=1,
            beta_state_duration=1,
            beta_ema14_value=1.10123,
            beta_ema14_slope=0.25,
            beta_momentum_14=0.31,
            beta_atr_14=0.0012,
            beta_atr_relative_change=0.02,
            beta_structure_signal="FAVORABLE",
            beta_evaluated_at="2026-07-13T10:00:00",
            mt5_price=1.1001,
            entry_price=1.1020,
            stop=1.1030,
            mt5_stop=1.1030,
            target=1.0960,
            beta_id="BETA002",
            beta_version="M1_EMA14_MOMENTUM_VOLATILITY",
            alpha_id="ALPHA006",
            operational_model="MODELO_1_ALPHA_ATUAL",
        )

        output = dashboard_app._mt5_theoretical_exit_row(
            row,
            {"EURUSD": {"Periodo de tempo": "H1"}},
        )

        self.assertEqual(output["TF Entrada Lab"], "H1")
        self.assertEqual(output["TF Saida Beta"], "M1")
        self.assertEqual(output["Modelo envio"], "MODELO 1")

    def test_saida_teorica_modelo1_usa_tf_do_lab_quando_beta_nao_tem_tf_proprio(self) -> None:
        row = SimpleNamespace(
            symbol="EURUSD",
            side="BUY",
            mt5_side="BUY",
            entry_price=1.1000,
            stop=1.0980,
            mt5_stop=1.0980,
            target=1.1060,
            beta_id="BETA004",
            beta_version="BREAK_EVEN",
            alpha_id="ALPHA011",
            entry_setup="PIVOT_REJECTION",
            operational_model="MODELO_1_ALPHA_ATUAL",
        )

        output = dashboard_app._mt5_theoretical_exit_row(
            row,
            {"EURUSD": {"Periodo de tempo": "H1"}},
        )

        self.assertEqual(output["TF Entrada Lab"], "H1")
        self.assertEqual(output["TF Saida Beta"], "H1")
        self.assertEqual(output["Modelo envio"], "MODELO 1")

    def test_saida_teorica_colore_modelo_envio_por_modelo(self) -> None:
        self.assertEqual(
            dashboard_app._mt5_theoretical_exit_cell_class(
                {"Modelo envio": "MODELO 1"},
                "Modelo envio",
            ),
            "traderia-cell-model1",
        )
        self.assertEqual(
            dashboard_app._mt5_theoretical_exit_cell_class(
                {"Modelo envio": "MODELO 2"},
                "Modelo envio",
            ),
            "traderia-cell-model2",
        )

    def test_saida_teorica_mt5_detecta_stop_movel_real(self) -> None:
        """Stop atual diferente do inicial deve aparecer como movel."""
        row = SimpleNamespace(
            symbol="EURUSD",
            side="BUY",
            mt5_side="BUY",
            position_manager_action="STOP_MOVED",
            position_manager_status="STOP_MOVED",
            position_manager_message="SL movido para ponto mais protetivo.",
            final_exit_reason="N/D",
            dynamic_exit_r_multiple=1.20,
            dynamic_exit_candidate_stop=1.1010,
            dynamic_exit_allowed_to_execute_demo=True,
            stop_movel_acionado=True,
            beta_strength_score=-0.20,
            beta_confirmation_count=3,
            beta_state_duration=3,
            beta_ema14_value=1.10200,
            beta_ema14_slope=-0.12,
            beta_momentum_14=-0.08,
            beta_atr_14=0.0010,
            beta_atr_relative_change=-0.02,
            beta_structure_signal="NEUTRAL",
            beta_evaluated_at="2026-07-13T10:00:00",
            mt5_price=1.1040,
            entry_price=1.1000,
            stop=1.0980,
            mt5_stop=1.1010,
            target=1.1060,
            beta_id="BETA002",
            beta_version="M1_EMA14_MOMENTUM_VOLATILITY",
            alpha_id="ALPHA006",
        )

        output = dashboard_app._mt5_theoretical_exit_row(
            row,
            {"EURUSD": {"Periodo de tempo": "M1"}},
        )

        self.assertEqual(output["Gestao stop"], "SL MOVIDO")
        self.assertEqual(output["Movimento SL"], "JA_MOVEU")
        self.assertEqual(
            dashboard_app._mt5_theoretical_exit_cell_class(output, "Gestao stop"),
            "",
        )

    def test_saida_teorica_mt5_nao_marca_movido_quando_sl_mt5_igual_inicial(self) -> None:
        """Flag historico nao deve sobrepor a leitura real do SL no MT5."""
        row = SimpleNamespace(
            symbol="EURUSD",
            side="SELL",
            mt5_side="SELL",
            position_manager_action="STOP_MAINTAINED",
            position_manager_status="MODIFY_REJECTED",
            position_manager_message="MT5 retornou resposta vazia.",
            final_exit_reason="N/D",
            dynamic_exit_r_multiple=0.10,
            dynamic_exit_candidate_stop=None,
            dynamic_exit_allowed_to_execute_demo=True,
            stop_movel_acionado=True,
            beta_strength_score=-0.20,
            beta_confirmation_count=3,
            beta_state_duration=3,
            beta_ema14_value=1.10200,
            beta_ema14_slope=-0.12,
            beta_momentum_14=-0.08,
            beta_atr_14=0.0010,
            beta_atr_relative_change=-0.02,
            beta_structure_signal="NEUTRAL",
            beta_evaluated_at="2026-07-13T10:00:00",
            mt5_price=1.1010,
            entry_price=1.1000,
            stop=1.14220375,
            mt5_stop=1.14220,
            target=1.0900,
            beta_id="BETA002",
            beta_version="M1_EMA14_MOMENTUM_VOLATILITY",
            alpha_id="ALPHA006",
        )

        output = dashboard_app._mt5_theoretical_exit_row(
            row,
            {"EURUSD": {"Periodo de tempo": "M1"}},
        )

        self.assertEqual(output["Gestao stop"], "MONITORANDO")
        self.assertEqual(output["Movimento SL"], "NAO_MOVEU")

    def test_robo_demo_rejection_step_row_mostra_etapa_e_motivo(self) -> None:
        """Arvore de rejeicao deve mostrar exatamente onde o candidato parou."""
        step = SimpleNamespace(
            order=4,
            symbol="EURUSD",
            timeframe="H1",
            stage="Trade Plan",
            status="BLOQUEADO",
            reason="Plano bloqueado: SEM_GATILHO_VALIDO.",
            detail="Regime indefinido.",
        )

        row = dashboard_app._demo_robot_rejection_step_row(step)

        self.assertEqual(row["Ordem"], 4)
        self.assertEqual(row["Par"], "EURUSD")
        self.assertEqual(row["TF"], "H1")
        self.assertEqual(row["Etapa"], "Trade Plan")
        self.assertEqual(row["Status"], "BLOQUEADO")
        self.assertIn("SEM_GATILHO_VALIDO", row["Motivo"])
        self.assertIn("Regime", row["Detalhe"])

    def test_robo_demo_online_so_fica_ativo_quando_backend_permite(self) -> None:
        """Session state antigo nao pode mostrar robo online se o backend bloqueou."""
        disabled = SimpleNamespace(
            status="DISABLED",
            provider="MT5_DEMO_DISABLED",
            mt5_order_send_enabled=False,
        )
        not_armed = SimpleNamespace(
            status="NOT_ARMED",
            provider="MT5_DEMO_DISABLED",
            mt5_order_send_enabled=False,
        )
        armed = SimpleNamespace(
            status="ARMED_WAITING",
            provider="MT5_DEMO",
            mt5_order_send_enabled=True,
        )

        self.assertFalse(dashboard_app._demo_robot_online_allowed(disabled))
        self.assertFalse(dashboard_app._demo_robot_online_allowed(not_armed))
        self.assertTrue(dashboard_app._demo_robot_online_allowed(armed))

    def test_relatorios_exibe_ponto_de_status_do_robo_demo(self) -> None:
        online_dot = dashboard_app._demo_robot_status_dot_html(True)
        offline_dot = dashboard_app._demo_robot_status_dot_html(False)

        self.assertIn("#16A34A", online_dot)
        self.assertIn("Robo demo ligado", online_dot)
        self.assertIn("#DC2626", offline_dot)
        self.assertIn("Robo demo desligado", offline_dot)

    def test_robo_demo_nao_apaga_online_por_leitura_backend_transitoria(self) -> None:
        class FakeSessionState(dict):
            pass

        previous_session_state = dashboard_app.st.session_state
        try:
            dashboard_app.st.session_state = FakeSessionState(
                {dashboard_app.MT5_DEMO_ROBOT_ONLINE_KEY: True}
            )
            data = SimpleNamespace(
                demo_robot=SimpleNamespace(
                    status="DISARMED",
                    provider="MT5_DEMO_DISABLED",
                    mt5_order_send_enabled=False,
                )
            )

            self.assertTrue(dashboard_app._demo_robot_online_status(data))
            self.assertTrue(
                dashboard_app.st.session_state[
                    dashboard_app.MT5_DEMO_ROBOT_ONLINE_KEY
                ]
            )
        finally:
            dashboard_app.st.session_state = previous_session_state

    def test_robo_demo_snapshot_estavel_usa_ultimo_plano_visivel(self) -> None:
        class FakeSessionState(dict):
            pass

        previous_session_state = dashboard_app.st.session_state
        valid = SimpleNamespace(
            status="EXECUTED",
            result_status="ACCEPTED",
            selected_pair="USDCAD",
            entry_price=1.42076,
            stop=1.41934,
            target=1.42360,
        )
        empty = SimpleNamespace(
            status="DISARMED",
            result_status="DISARMED",
            selected_pair="N/D",
            entry_price=None,
            stop=None,
            target=None,
        )
        try:
            dashboard_app.st.session_state = FakeSessionState()

            first = dashboard_app._stable_demo_robot_snapshot(valid)
            second = dashboard_app._stable_demo_robot_snapshot(empty)

            self.assertIs(first, valid)
            self.assertIs(second, valid)
        finally:
            dashboard_app.st.session_state = previous_session_state

    def test_relatorios_arma_todos_pela_fachada_do_dashboard(self) -> None:
        class FakeSessionState(dict):
            pass

        class FakeService:
            def __init__(self):
                self.calls = []

            def arm_demo_robot(self, pair: str, timeframe: str):
                self.calls.append((pair, timeframe))
                return SimpleNamespace(
                    status="ARMED_WAITING",
                    provider="MT5_DEMO",
                    mt5_order_send_enabled=True,
                )

        previous_session_state = dashboard_app.st.session_state
        previous_env = os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)
        fake_service = FakeService()
        data = SimpleNamespace(mt5_forex_signals=SimpleNamespace(timeframe="H1"))
        try:
            dashboard_app.st.session_state = FakeSessionState()

            robot = dashboard_app._arm_all_demo_robot_from_reports(fake_service, data)

            self.assertEqual(fake_service.calls, [("TODOS", "H1")])
            self.assertEqual(robot.status, "ARMED_WAITING")
            self.assertTrue(
                dashboard_app.st.session_state[dashboard_app.MT5_DEMO_ROBOT_ONLINE_KEY]
            )
            self.assertEqual(os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"], "1")
        finally:
            dashboard_app.st.session_state = previous_session_state
            if previous_env is None:
                os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)
            else:
                os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = previous_env

    def test_armar_robo_persiste_online_mesmo_se_backend_bloquear_no_clique(
        self,
    ) -> None:
        class FakeSessionState(dict):
            pass

        class FakeService:
            def arm_demo_robot(self, pair: str, timeframe: str):
                return SimpleNamespace(
                    status="DISARMED",
                    provider="MT5_DEMO_DISABLED",
                    mt5_order_send_enabled=False,
                    message="backend ainda indisponivel",
                )

        persisted: list[dict[str, object]] = []

        def fake_persist(**kwargs):
            persisted.append(dict(kwargs))

        previous_session_state = dashboard_app.st.session_state
        previous_persist = dashboard_app._persist_demo_robot_online_state
        previous_env = os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)
        data = SimpleNamespace(mt5_forex_signals=SimpleNamespace(timeframe="M1"))
        try:
            dashboard_app.st.session_state = FakeSessionState()
            dashboard_app._persist_demo_robot_online_state = fake_persist

            robot = dashboard_app._arm_all_demo_robot_from_reports(
                FakeService(),
                data,
            )

            self.assertEqual(robot.status, "DISARMED")
            self.assertTrue(
                dashboard_app.st.session_state[
                    dashboard_app.MT5_DEMO_ROBOT_ONLINE_KEY
                ]
            )
            self.assertTrue(persisted)
            self.assertTrue(persisted[-1]["online"])
        finally:
            dashboard_app.st.session_state = previous_session_state
            dashboard_app._persist_demo_robot_online_state = previous_persist
            if previous_env is None:
                os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)
            else:
                os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = previous_env

    def test_arming_robo_demo_habilita_execucao_demo_na_sessao(self) -> None:
        """Botao de armar precisa habilitar a flag demo no processo Streamlit."""
        previous = os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)
        try:
            dashboard_app._enable_mt5_demo_execution_for_session()

            self.assertEqual(os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"], "1")
        finally:
            if previous is None:
                os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)
            else:
                os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = previous

    def test_runtime_cleanup_remove_apenas_estado_temporario(self) -> None:
        class FakeSessionState(dict):
            pass

        class FakeCache:
            def __init__(self) -> None:
                self.cleared = False

            def clear(self) -> None:
                self.cleared = True

        previous_session_state = dashboard_app.st.session_state
        previous_cache_data = dashboard_app.st.cache_data
        previous_cache_resource = dashboard_app.st.cache_resource
        cache_data = FakeCache()
        cache_resource = FakeCache()
        try:
            dashboard_app.st.session_state = FakeSessionState(
                {
                    dashboard_app.MT5_FOREX_MANUAL_DIAGNOSTIC_KEY: object(),
                    dashboard_app.MT5_FOREX_LAST_AUTO_LOAD_KEY: 123.0,
                    dashboard_app.REPLAY_PENDING_ACTION_KEY: "load",
                    "mt5_trade_audit_report_10": object(),
                    "runtime_temp_grid": object(),
                    dashboard_app.MT5_FOREX_LAST_VALID_SNAPSHOT_KEY: object(),
                    "dashboard_selected_tab": "Sistema Forex",
                    "lab_parameter_profile": "PERSISTE",
                    "configuration_data": object(),
                }
            )
            dashboard_app.st.cache_data = cache_data
            dashboard_app.st.cache_resource = cache_resource

            removed = dashboard_app._clear_runtime_queues_and_temporary_caches()

            self.assertIn(dashboard_app.MT5_FOREX_MANUAL_DIAGNOSTIC_KEY, removed)
            self.assertIn("mt5_trade_audit_report_10", removed)
            self.assertIn("runtime_temp_grid", removed)
            self.assertNotIn(
                dashboard_app.MT5_FOREX_MANUAL_DIAGNOSTIC_KEY,
                dashboard_app.st.session_state,
            )
            self.assertNotIn("mt5_trade_audit_report_10", dashboard_app.st.session_state)
            self.assertIn(
                dashboard_app.MT5_FOREX_LAST_VALID_SNAPSHOT_KEY,
                dashboard_app.st.session_state,
            )
            self.assertEqual(
                dashboard_app.st.session_state["lab_parameter_profile"],
                "PERSISTE",
            )
            self.assertIn("configuration_data", dashboard_app.st.session_state)
            self.assertTrue(cache_data.cleared)
            self.assertTrue(cache_resource.cleared)
        finally:
            dashboard_app.st.session_state = previous_session_state
            dashboard_app.st.cache_data = previous_cache_data
            dashboard_app.st.cache_resource = previous_cache_resource

    def test_runtime_repair_scanner_mapeia_sintomas_conhecidos(self) -> None:
        snapshot = {
            "auto_cycle_enabled": True,
            "cycle_lock_busy": True,
            "dashboard_service_cached": True,
            "initial_load_error": True,
            "manual_diagnostic_message": False,
            "legacy_guard_pending": False,
            "slow_tabs": ["MT5 Forex"],
            "temporary_key_count": 2,
        }

        plan = dashboard_app._runtime_repair_plan_from_snapshot(snapshot)

        self.assertIn("ciclo automatico MT5 Forex ativo", plan["symptoms"])
        self.assertIn("pause_auto_cycle", plan["actions"])
        self.assertIn("clear_cycle_timestamps", plan["actions"])
        self.assertIn("recreate_dashboard_service", plan["actions"])
        self.assertIn("clear_runtime_errors", plan["actions"])
        self.assertIn("clear_temporary_caches", plan["actions"])
        self.assertIn("clear_render_metrics", plan["actions"])
        self.assertNotIn("maintenance_required", plan["actions"])

    def test_runtime_repair_scanner_indica_manutencao_para_caso_novo(self) -> None:
        snapshot = {
            "auto_cycle_enabled": False,
            "cycle_lock_busy": False,
            "dashboard_service_cached": False,
            "initial_load_error": False,
            "manual_diagnostic_message": False,
            "legacy_guard_pending": False,
            "slow_tabs": [],
            "temporary_key_count": 0,
        }

        plan = dashboard_app._runtime_repair_plan_from_snapshot(snapshot)

        self.assertEqual(
            plan["symptoms"],
            ["nenhum sintoma conhecido detectado pelo scanner"],
        )
        self.assertEqual(plan["actions"], ["maintenance_required"])

    def test_runtime_repair_aplica_remedios_sem_apagar_estado_operacional(self) -> None:
        class FakeSessionState(dict):
            pass

        class FakeCache:
            def __init__(self) -> None:
                self.cleared = False

            def clear(self) -> None:
                self.cleared = True

        previous_session_state = dashboard_app.st.session_state
        previous_cache_data = dashboard_app.st.cache_data
        previous_cache_resource = dashboard_app.st.cache_resource
        cache_data = FakeCache()
        cache_resource = FakeCache()
        try:
            dashboard_app.st.session_state = FakeSessionState(
                {
                    "dashboard_service": object(),
                    dashboard_app.MT5_FOREX_AUTO_CYCLE_UI_KEY: True,
                    dashboard_app.MT5_FOREX_INITIAL_LOAD_ERROR_KEY: "erro",
                    dashboard_app.MT5_FOREX_LAST_AUTO_LOAD_KEY: 123.0,
                    dashboard_app.RUNTIME_RENDER_DURATIONS_KEY: {"MT5 Forex": 4000},
                    "runtime_temp_probe": object(),
                    dashboard_app.MT5_FOREX_LAST_VALID_SNAPSHOT_KEY: object(),
                    "lab_parameter_profile": "PERSISTE",
                }
            )
            dashboard_app.st.cache_data = cache_data
            dashboard_app.st.cache_resource = cache_resource
            plan = {
                "actions": [
                    "clear_temporary_caches",
                    "clear_cycle_timestamps",
                    "clear_runtime_errors",
                    "clear_render_metrics",
                    "recreate_dashboard_service",
                    "pause_auto_cycle",
                ]
            }

            removed = dashboard_app._apply_runtime_repair_plan(plan)

            self.assertIn("dashboard_service", removed)
            self.assertIn(dashboard_app.MT5_FOREX_INITIAL_LOAD_ERROR_KEY, removed)
            self.assertIn(dashboard_app.MT5_FOREX_LAST_AUTO_LOAD_KEY, removed)
            self.assertIn("runtime_temp_probe", removed)
            self.assertFalse(
                dashboard_app.st.session_state[
                    dashboard_app.MT5_FOREX_AUTO_CYCLE_UI_KEY
                ]
            )
            self.assertNotIn("dashboard_service", dashboard_app.st.session_state)
            self.assertIn(
                dashboard_app.MT5_FOREX_LAST_VALID_SNAPSHOT_KEY,
                dashboard_app.st.session_state,
            )
            self.assertEqual(
                dashboard_app.st.session_state["lab_parameter_profile"],
                "PERSISTE",
            )
            self.assertTrue(cache_data.cleared)
            self.assertTrue(cache_resource.cleared)
        finally:
            dashboard_app.st.session_state = previous_session_state
            dashboard_app.st.cache_data = previous_cache_data
            dashboard_app.st.cache_resource = previous_cache_resource

    def test_lab_confirmation_audit_agrupa_alpha_por_par_e_ordena(self) -> None:
        scenarios = [
            SimpleNamespace(
                pair="EURUSD",
                alpha_id="ALPHA001",
                lab_confidence=0.55,
                lab_confidence_sample_size=80,
                score=0.9,
                timeframe="M1",
                decision="BUY",
                model="A1_OLD",
                parameters={
                    "ema_curta": "9",
                    "ema_longa": "21",
                    "atr_stop_factor": "1.5",
                    "rr": "2.0",
                },
                lab_discrimination_summary="RSI divergente: V 10% x NV 40% (mais nos nao vencedores)",
                status="REJEITADO",
            ),
            SimpleNamespace(
                pair="EURUSD",
                alpha_id="ALPHA001",
                lab_confidence=0.61,
                lab_confidence_sample_size=120,
                score=0.7,
                timeframe="M15",
                decision="SELL",
                model="A1_BEST",
                parameters={
                    "ema_curta": "20",
                    "ema_longa": "50",
                    "atr_stop_factor": "2.0",
                    "rr": "3.0",
                },
                lab_discrimination_summary="MACD hist divergente: V 15% x NV 45% (mais nos nao vencedores)",
                lab_discrimination_metrics={
                    "RSI divergente": {
                        "winner_rate": 0.10,
                        "loser_rate": 0.40,
                        "difference": 0.30,
                    },
                    "MACD hist divergente": {
                        "winner_rate": 0.15,
                        "loser_rate": 0.45,
                        "difference": 0.30,
                    },
                    "ADX baixo": {
                        "winner_rate": 0.20,
                        "loser_rate": 0.50,
                        "difference": 0.30,
                    },
                    "ADX caindo": {
                        "winner_rate": 0.12,
                        "loser_rate": 0.42,
                        "difference": 0.30,
                    },
                    "ADX indisponivel": {
                        "winner_rate": 0.00,
                        "loser_rate": 0.00,
                        "difference": 0.00,
                    },
                    "ATR em queda": {
                        "winner_rate": 0.25,
                        "loser_rate": 0.55,
                        "difference": 0.30,
                    },
                    "ATR subindo": {
                        "winner_rate": 0.75,
                        "loser_rate": 0.45,
                        "difference": -0.30,
                    },
                    "Momentum contra": {
                        "winner_rate": 0.05,
                        "loser_rate": 0.35,
                        "difference": 0.30,
                    },
                    "Momentum enfraquecendo": {
                        "winner_rate": 0.18,
                        "loser_rate": 0.48,
                        "difference": 0.30,
                    },
                },
                status="APROVADO",
            ),
            SimpleNamespace(
                pair="EURUSD",
                alpha_id="ALPHA002",
                lab_confidence=0.72,
                lab_confidence_sample_size=50,
                score=0.8,
                timeframe="M5",
                decision="BUY",
                model="A2_BEST",
                parameters={
                    "ema_curta": "20",
                    "ema_longa": "50",
                    "atr_stop_factor": "2.0",
                    "rr": "3.0",
                },
                status="APROVADO",
            ),
            SimpleNamespace(
                pair="GBPUSD",
                alpha_id="ALPHA001",
                lab_confidence=0.44,
                lab_confidence_sample_size=200,
                score=0.6,
                timeframe="H1",
                decision="WAIT",
                model="GBP_A1",
                status="REJEITADO",
            ),
            SimpleNamespace(
                pair="GBPUSD",
                alpha_id="ALPHA002",
                lab_confidence=0.66,
                lab_confidence_sample_size=180,
                score=0.7,
                timeframe="M15",
                decision="BUY",
                model="GBP_A2_BETA3",
                parameters={
                    "atr_stop_factor": "2.5",
                    "rr": "3.0",
                    "stop_management": "ATR_TRAILING_STOP",
                    "atr_trailing_factor": "2.5",
                    "atr_trailing_activation_rr": "1.0",
                    "beta_id": "BETA005",
                    "beta_version": "ATR_TRAILING_STOP_MANAGER",
                    "beta_mode": "ATR_TRAILING_ONLY",
                },
                status="APROVADO",
            ),
        ]

        rows = dashboard_app._lab_historical_confirmation_audit_rows(scenarios)

        eurusd_rows = [row for row in rows if row["Par"] == "EURUSD"]
        gbpusd_rows = [row for row in rows if row["Par"] == "GBPUSD"]

        self.assertEqual(len(eurusd_rows), 16)
        self.assertEqual(len(gbpusd_rows), 16)
        self.assertEqual(
            [
                (row["Alpha de entrada"], row["Confirmacao Historica"])
                for row in eurusd_rows[:3]
            ],
            [
                ("ALPHA002", "72.00%"),
                ("ALPHA001", "61.00%"),
                ("ALPHA003", "0.00%"),
            ],
        )
        self.assertEqual(eurusd_rows[1]["Trades observados"], 120)
        self.assertEqual(eurusd_rows[1]["Confirmados"], 73)
        self.assertEqual(eurusd_rows[1]["Nao confirmados"], 47)
        self.assertEqual(eurusd_rows[1]["% Nao confirmado"], "39.00%")
        self.assertEqual(eurusd_rows[1]["Setup de entrada"], "A1_BEST")
        self.assertIn("ema_curta=20", eurusd_rows[1]["Parametros da entrada"])
        self.assertIn("rr=3.0", eurusd_rows[1]["Iguais ao melhor do par"])
        self.assertIn("Direcao: SELL != BUY", eurusd_rows[1]["Diferentes do melhor do par"])
        self.assertIn("Confirmacao equilibrada", eurusd_rows[1]["Padrao observado"])
        self.assertEqual(
            eurusd_rows[0]["Filtro de liberacao"],
            "RSI divergente | NV 40.00% x V 10.00% | Dif +30%",
        )
        self.assertEqual(
            eurusd_rows[1]["Filtro de liberacao"],
            "RSI divergente | NV 40.00% x V 10.00% | Dif +30%",
        )
        self.assertIn("Entrada da Alpha so deve ser liberada", eurusd_rows[1]["Regra de liberacao"])
        self.assertIn("Ainda nao altera execucao", eurusd_rows[1]["Regra de liberacao"])
        self.assertIn(
            "MACD hist divergente",
            eurusd_rows[1]["Indicadores que diferenciam"],
        )
        self.assertEqual(eurusd_rows[1]["RSI divergente"], "V 10.00% | NV 40.00% | Dif +30%")
        self.assertEqual(
            eurusd_rows[1]["MACD hist divergente"],
            "V 15.00% | NV 45.00% | Dif +30%",
        )
        self.assertEqual(eurusd_rows[1]["ADX baixo"], "V 20.00% | NV 50.00% | Dif +30%")
        self.assertEqual(eurusd_rows[1]["ADX caindo"], "V 12.00% | NV 42.00% | Dif +30%")
        self.assertEqual(eurusd_rows[1]["ADX indisponivel"], "V 0.00% | NV 0.00% | Dif +0%")
        self.assertEqual(eurusd_rows[1]["ATR em queda"], "V 25.00% | NV 55.00% | Dif +30%")
        self.assertEqual(eurusd_rows[1]["ATR subindo"], "V 75.00% | NV 45.00% | Dif -30%")
        self.assertEqual(eurusd_rows[1]["Momentum contra"], "V 5.00% | NV 35.00% | Dif +30%")
        self.assertEqual(
            eurusd_rows[1]["Momentum enfraquecendo"],
            "V 18.00% | NV 48.00% | Dif +30%",
        )
        self.assertEqual(eurusd_rows[-1]["Alpha de entrada"], "ALPHA016")
        self.assertEqual(eurusd_rows[-1]["Trades observados"], 0)
        self.assertEqual(eurusd_rows[-1]["RSI divergente"], "N/D")
        self.assertEqual(gbpusd_rows[0]["Beta Stop"], "BETA005 | ATR_TRAILING_ONLY | ATR_TRAILING_STOP_MANAGER")
        self.assertEqual(
            gbpusd_rows[0]["Stop inicial em R"],
            "1R = stop inicial 2.5 ATR | alvo planejado 3R",
        )
        self.assertIn("sem FULL_EXIT", gbpusd_rows[0]["Plano Position Manager"])
        self.assertIn("trailing por ATR x2.5", gbpusd_rows[0]["Plano Position Manager"])

    def test_lab_confirmation_preview_usa_colunas_da_auditoria(self) -> None:
        columns = dashboard_app._lab_historical_confirmation_audit_columns()
        preview = dashboard_app._lab_historical_confirmation_preview_row()

        self.assertEqual(list(preview.keys()), columns)
        self.assertEqual(preview["Status"], "PREVIA")
        self.assertEqual(preview["Alpha de entrada"], "ALPHA001")
        self.assertIn("ema_curta", preview["Parametros da entrada"])

    def test_lab_audit_deriva_beta_stop_da_politica_mesmo_em_snapshot_beta2(
        self,
    ) -> None:
        scenario = SimpleNamespace(
            pair="GBPUSD",
            alpha_id="ALPHA002",
            lab_confidence=0.66,
            lab_confidence_sample_size=180,
            score=0.7,
            timeframe="M15",
            decision="BUY",
            model="GBP_A2_BETA2_COMPAT",
            parameters={
                "atr_stop_factor": "2.5",
                "rr": "3.0",
                "stop_management": "ATR_TRAILING_STOP",
                "atr_trailing_factor": "2.5",
                "atr_trailing_activation_rr": "1.0",
                "beta_id": "BETA002",
                "beta_version": "M1_EMA14_MOMENTUM_VOLATILITY",
                "beta_mode": "ADAPTIVE_FULL_EXIT",
            },
            status="APROVADO",
        )

        row = dashboard_app._lab_historical_confirmation_audit_row(
            scenario,
            reference=scenario,
        )

        self.assertEqual(
            row["Beta Stop"],
            "BETA005 | ATR_TRAILING_ONLY | ATR_TRAILING_STOP_MANAGER",
        )
        self.assertIn("BETA005 sem FULL_EXIT", row["Plano Position Manager"])
        self.assertIn("trailing por ATR x2.5", row["Plano Position Manager"])

    def test_research_lab_display_usa_snapshot_calculado_para_planilha(self) -> None:
        class FakeSessionState(dict):
            pass

        class FakeService:
            def __init__(self) -> None:
                self.constants_called = False

            def get_mt5_research_constants(self) -> object:
                self.constants_called = True
                return SimpleNamespace(source="DISK")

            def get_mt5_research_report_snapshot(self) -> object:
                return SimpleNamespace(source="REPORT")

        previous_session_state = dashboard_app.st.session_state
        calculated = SimpleNamespace(source="CALCULATED")
        service = FakeService()
        try:
            dashboard_app.st.session_state = FakeSessionState(
                {dashboard_app.MT5_LAB_CALCULATION_SNAPSHOT_KEY: calculated}
            )

            selected = dashboard_app._research_lab_snapshot_for_display(service)

            self.assertIs(selected, calculated)
            self.assertFalse(service.constants_called)
        finally:
            dashboard_app.st.session_state = previous_session_state

    def test_research_lab_display_descarta_snapshot_calculado_sem_evidencia(
        self,
    ) -> None:
        class FakeSessionState(dict):
            pass

        persisted = SimpleNamespace(
            source="PERSISTED",
            scenario_ranking=[
                SimpleNamespace(lab_confidence_sample_size=564),
            ],
        )
        stale_calculated = SimpleNamespace(
            source="STALE",
            scenario_ranking=[
                SimpleNamespace(lab_confidence_sample_size=0),
            ],
        )

        class FakeService:
            def get_mt5_research_constants(self) -> object:
                return SimpleNamespace(source="CONSTANTS")

            def get_mt5_research_report_snapshot(self) -> object:
                return persisted

        previous_session_state = dashboard_app.st.session_state
        try:
            dashboard_app.st.session_state = FakeSessionState(
                {dashboard_app.MT5_LAB_CALCULATION_SNAPSHOT_KEY: stale_calculated}
            )

            selected = dashboard_app._research_lab_snapshot_for_display(
                FakeService(),
                include_full_audit=True,
            )

            self.assertIs(selected, persisted)
            self.assertIs(
                dashboard_app.st.session_state[
                    dashboard_app.MT5_LAB_CALCULATION_SNAPSHOT_KEY
                ],
                persisted,
            )
        finally:
            dashboard_app.st.session_state = previous_session_state

    def test_research_lab_display_prefere_snapshot_persistido_ao_runtime_index(
        self,
    ) -> None:
        class FakeSessionState(dict):
            pass

        runtime_index = SimpleNamespace(
            source="MT5_RESEARCH_RUNTIME_INDEX",
            scenario_ranking=[],
            rows=[SimpleNamespace(sample_size=0)],
        )
        persisted = SimpleNamespace(
            source="MT5_RESEARCH_CALCULATED_FROM_HISTORY_SNAPSHOT",
            scenario_ranking=[SimpleNamespace(lab_confidence_sample_size=564)],
            rows=[],
        )

        class FakeService:
            def get_mt5_research_constants(self) -> object:
                return runtime_index

            def get_mt5_research_report_snapshot(self) -> object:
                return persisted

        previous_session_state = dashboard_app.st.session_state
        try:
            dashboard_app.st.session_state = FakeSessionState()

            selected = dashboard_app._research_lab_snapshot_for_display(FakeService())

            self.assertIs(selected, persisted)
        finally:
            dashboard_app.st.session_state = previous_session_state

    def test_robo_demo_nao_exibe_entrada_parcial_sem_plano_executavel(self) -> None:
        """Card do robo nao pode mostrar preco se stop/alvo ainda sao invalidos."""
        robot = SimpleNamespace(
            status="AGUARDANDO_PLANO",
            result_status="SEM_GATILHO_VALIDO",
            entry_price=1.41949,
            stop=None,
            target=None,
        )

        entry, stop, target = dashboard_app._demo_robot_trade_prices(robot)

        self.assertIsNone(entry)
        self.assertIsNone(stop)
        self.assertIsNone(target)

    def test_robo_demo_exibe_precos_quando_plano_foi_executado(self) -> None:
        """Card do robo pode mostrar precos somente para ordem avaliada."""
        robot = SimpleNamespace(
            status="EXECUTED",
            result_status="ACCEPTED",
            entry_price=1.1,
            stop=1.0,
            target=1.3,
        )

        self.assertEqual(
            dashboard_app._demo_robot_trade_prices(robot),
            (1.1, 1.0, 1.3),
        )

    def test_robo_demo_auditoria_exibe_metadados_do_research_lab(self) -> None:
        """Auditoria visual deve mostrar Alpha, score e plano executado."""
        row = SimpleNamespace(
            timestamp="2026-07-02T10:00:00-03:00",
            symbol="EURUSD",
            side="BUY",
            quantity=0.1,
            alpha_id="ALPHA006",
            alpha_version="v1.6",
            session_policy_version="v2.1",
            execution_pipeline_version="v3.4",
            lab_configuration_version="v8",
            trade_plan_version="TP v5",
            execution_engine_version="ExecutionEngine v1",
            indicator_bundle_version="Indicators v9",
            microstructure_version="Micro v2",
            validation_pipeline_version="VAL v4",
            strategy_definition_version="STRAT v3",
            technical_score=0.72,
            historical_confirmation=0.68,
            entry_price=1.1,
            stop=1.09,
            target=1.12,
            risk_reward=2.0,
            candle_time="2026-07-02T13:00:00+00:00",
            accepted=True,
            status="ACCEPTED",
            message="demo",
            ticket=123,
            mt5_position="OPEN",
            forex_session="LONDON",
            forex_session_open=True,
            session_filter_enabled=True,
            session_filter_result="ALLOWED",
            session_reason="London Session",
            timestamp_utc="2026-07-02T13:00:00+00:00",
            timestamp_brt="2026-07-02T10:00:00-03:00",
            weekday="THURSDAY",
            is_rollover=False,
            is_london_ny_overlap=False,
            is_sunday_open=False,
            is_friday_late=False,
        )

        audit = dashboard_app._demo_robot_audit_row(row)

        self.assertEqual(audit["Alpha"], "ALPHA006")
        self.assertEqual(audit["Versao politica sessao"], "v2.1")
        self.assertEqual(audit["Versao pipeline execucao"], "v3.4")
        self.assertEqual(audit["Versao config Lab"], "v8")
        self.assertEqual(audit["Versao Trade Plan"], "TP v5")
        self.assertEqual(audit["Versao motor execucao"], "ExecutionEngine v1")
        self.assertEqual(audit["Versao indicadores"], "Indicators v9")
        self.assertEqual(audit["Versao microestrutura"], "Micro v2")
        self.assertEqual(audit["Versao validacao"], "VAL v4")
        self.assertEqual(audit["Versao estrategia"], "STRAT v3")
        self.assertEqual(audit["Score Tecnico"], "72.00%")
        self.assertEqual(audit["Confirmacao Historica"], "68.00%")
        self.assertEqual(audit["Entrada"], "1.10000")
        self.assertEqual(audit["RR"], "2.00")
        self.assertEqual(audit["Ticket"], 123)
        self.assertEqual(audit["Posicao MT5"], "OPEN")
        self.assertEqual(audit["Sessao Forex"], "LONDON")
        self.assertEqual(
            audit["Mercado aberto"],
            "ABERTO | Sessao: LONDON | ALLOWED | London Session",
        )
        self.assertEqual(audit["Resultado sessao"], "ALLOWED")
        self.assertEqual(audit["Motivo sessao"], "London Session")

    def test_historico_mt5_exibe_apenas_fluxo_forex(self) -> None:
        """Historico MT5 deve listar candles Forex sem comparar PETR4/WDO."""
        row = SimpleNamespace(
            pair="EURUSD",
            timeframe="H1",
            received_candles=1000,
            last_candle_time="2026-06-29T23:00:00+00:00",
            last_price=1.12345,
            decision="BUY",
            status="OK",
        )

        history_row = dashboard_app._mt5_history_row(row)

        self.assertEqual(history_row["Par"], "EURUSD")
        self.assertEqual(history_row["Candles recebidos"], 1000)
        self.assertEqual(history_row["Timeframe"], "H1")
        self.assertEqual(history_row["Decisao"], "BUY")
        self.assertNotIn("Ativo Plataforma", history_row)
        self.assertNotIn("Candles Plataforma", history_row)

    def test_mt5_forex_ignora_session_state_antigo_de_candles(self) -> None:
        """Session state antigo nao pode sobrescrever ConfigurationManager."""
        previous_fast_boot = os.environ.get("TRADERIA_FAST_BOOT_ENABLED")
        os.environ["TRADERIA_FAST_BOOT_ENABLED"] = "0"
        app = AppTest.from_file("dashboard_app.py")
        app.session_state["mt5_forex_candles"] = 5000
        try:
            app.run(timeout=30)
            app.segmented_control[0].set_value("Sistema Forex")
            app.run(timeout=30)
        finally:
            if previous_fast_boot is None:
                os.environ.pop("TRADERIA_FAST_BOOT_ENABLED", None)
            else:
                os.environ["TRADERIA_FAST_BOOT_ENABLED"] = previous_fast_boot

        rendered_table = self._markdown(app) + self._dataframe_text(app)
        metrics = self._metrics(app)
        self.assertFalse(app.exception)
        self.assertEqual(metrics.get("Candles online por par"), "1000")
        self.assertIn("Candles recebidos", metrics)
        self.assertNotEqual(metrics.get("Candles online por par"), "5000")

    def test_replay_foca_pares_forex_sem_dataset_legado(self) -> None:
        """Replay usa pares Forex, sem seletor de dataset legado."""
        app = self._run_app("Replay")

        self.assertFalse(app.exception)
        self.assertIn("Replay", self._navigation_labels(app))
        self.assertIn("Par Forex do Replay", "\n".join(self._selectboxes(app)))
        self.assertNotIn("Carregar Dataset Selecionado", self._buttons(app))

    def test_lab_sugestoes_exibem_parametros_compactos(self) -> None:
        row = dashboard_app._mt5_setup_suggestion_compact_row(
            SimpleNamespace(
                pair="EURUSD",
                timeframe="H1",
                decision="BUY",
                model="TREND_MOMENTUM",
                parameters={
                    "ema_curta": "20",
                    "ema_longa": "50",
                    "rsi_sobrevenda": "35.0",
                    "rsi_sobrecompra": "65.0",
                    "atr_stop_factor": "2.0",
                    "rr": "2.5",
                },
                exit_model="INITIAL_RISK_PLAN",
                stop_management="ATR_TRAILING_STOP",
                score=0.82,
                lab_confidence=0.70,
                status="SUGERIDO_70",
            )
        )

        self.assertEqual(
            row["Resumo parametros"],
            "EMA 20x50 | RSI 35.0/65.0 | ATR 2.0 | RR 2.5",
        )
        self.assertEqual(row["Status"], "ATINGIU_70")
        self.assertEqual(row["Gestao runtime"], "POSITION_MANAGER_DINAMICO")
        self.assertEqual(row["Plano de risco"], "INITIAL_RISK_PLAN")

    def test_lab_sugestoes_normalizam_modelo_saida_legado(self) -> None:
        row = dashboard_app._mt5_setup_suggestion_compact_row(
            SimpleNamespace(
                pair="EURUSD",
                timeframe="H1",
                decision="BUY",
                model="TREND_MOMENTUM",
                parameters={},
                exit_model="SCENARIO_EXIT_RESEARCH_SELECTION",
                stop_management="ATR_TRAILING_STOP",
                score=0.82,
                lab_confidence=0.70,
                status="SUGERIDO_70",
            )
        )

        self.assertEqual(row["Gestao runtime"], "POSITION_MANAGER_DINAMICO")
        self.assertEqual(row["Plano de risco"], "INITIAL_RISK_PLAN")

    def test_lab_sugestoes_derivam_beta_stop_da_politica(self) -> None:
        suggestion = SimpleNamespace(
            pair="AUDUSD",
            timeframe="M1",
            decision="BUY",
            model="ATR_VOLATILITY_REGIME",
            beta_id="BETA002",
            beta_mode="SAIDA_COMPLETA_ADAPTAVEL",
            parameters={
                "atr_stop_factor": "1.5",
                "rr": "2.0",
            },
            exit_model="INITIAL_RISK_PLAN",
            stop_management="ATR_TRAILING_STOP",
            score=0.82,
            lab_confidence=0.70,
            status="SUGERIDO_70",
        )

        compact = dashboard_app._mt5_setup_suggestion_compact_row(suggestion)
        detail = dashboard_app._mt5_setup_suggestion_row(suggestion)

        self.assertEqual(compact["Beta"], "BETA005")
        self.assertEqual(detail["Beta"], "BETA005")

    def test_lab_research_report_resume_status_da_alpha(self) -> None:
        row = dashboard_app._mt5_alpha_research_report_row(
            SimpleNamespace(
                alpha_id="ALPHA001",
                status="REPROVADA",
                best_pair="EURUSD",
                best_timeframe="M15",
                best_model="TREND_MOMENTUM",
                best_decision="SELL",
                best_score=0.7124,
                best_confidence=0.5897,
                evaluated_pairs=8,
                source="MT5_RESEARCH_ALPHA001_SEARCH_SPACE_5000",
            )
        )

        self.assertEqual(row["Alpha"], "ALPHA001")
        self.assertEqual(row["Status"], "REPROVADA")
        self.assertEqual(row["Melhor par"], "EURUSD")
        self.assertEqual(row["Confirmacao Historica"], "58.97%")

    def test_dashboard_usa_apenas_fragmentos_de_topo_sem_aninhar_robo(self) -> None:
        """Fragmentos aninhados quebram o frontend Streamlit durante auto-refresh."""
        with open("dashboard_app.py", encoding="utf-8") as file:
            source = file.read()

        self.assertEqual(source.count("@st.fragment"), 3)
        self.assertIn("def _global_demo_robot_cycle_fragment", source)
        self.assertIn("def exibir_mt5_forex_dashboard", source)
        self.assertIn("def exibir_relatorios_dashboard", source)
        self.assertNotIn("@st.fragment\ndef _exibir_robo_demo_mt5", source)

    def test_relatorios_separam_operacoes_abertas_do_historico(self) -> None:
        with open("dashboard_app.py", encoding="utf-8") as file:
            source = file.read()

        self.assertIn('st.markdown("#### Em negociacao")', source)
        self.assertIn('st.markdown("#### Historico")', source)
        self.assertIn("def _is_mt5_open_operation", source)
        self.assertTrue(
            dashboard_app._is_mt5_open_operation(
                SimpleNamespace(operation_status="ABERTA")
            )
        )
        self.assertTrue(
            dashboard_app._is_mt5_open_operation(
                SimpleNamespace(operation_status="ORDEM_ABERTA")
            )
        )
        self.assertFalse(
            dashboard_app._is_mt5_open_operation(
                SimpleNamespace(operation_status="FECHADA/HISTORICO")
            )
        )

    def test_diagnostico_mt5_nao_liga_ciclo_automatico(self) -> None:
        original_st = dashboard_app.st
        original_render_diagnostic = dashboard_app._exibir_mt5_connection_diagnostic
        fake_st = self._fake_streamlit(button_clicked=True)
        light_view_calls = []
        service = SimpleNamespace(
            test_mt5_connection=lambda symbol, timeframe: SimpleNamespace(
                connection_status="ONLINE",
                steps=[],
            ),
            get_light_dashboard_view_model=lambda: light_view_calls.append(True),
        )
        forex = SimpleNamespace(
            pairs=[SimpleNamespace(pair="EURUSD")],
            timeframe="M1",
        )
        dashboard_app.st = fake_st
        dashboard_app._exibir_mt5_connection_diagnostic = lambda diagnostic: None
        try:
            dashboard_app._exibir_mt5_manual_diagnostic_controls(
                service,
                SimpleNamespace(mt5_forex_signals=forex),
                forex,
            )
        finally:
            dashboard_app.st = original_st
            dashboard_app._exibir_mt5_connection_diagnostic = original_render_diagnostic

        self.assertNotIn(
            dashboard_app.MT5_FOREX_AUTO_CYCLE_UI_KEY,
            fake_st.session_state,
        )
        self.assertEqual(light_view_calls, [])
        self.assertIn(
            "Nenhum ciclo automatico foi iniciado",
            fake_st.session_state[
                dashboard_app.MT5_FOREX_MANUAL_DIAGNOSTIC_MESSAGE_KEY
            ],
        )

    def test_robo_demo_online_executa_no_maximo_um_ciclo_por_intervalo(self) -> None:
        class FakeSessionState(dict):
            pass

        class FakeService:
            def __init__(self) -> None:
                self.cycles = 0

            def get_demo_robot_status(self):
                return SimpleNamespace(
                    status="ARMED",
                    result_status="ARMED_WAITING",
                    provider="MT5_DEMO",
                    mt5_order_send_enabled=True,
                )

            def arm_demo_robot(self, pair: str, timeframe: str):
                return self.get_demo_robot_status()

            def run_online_demo_robot_cycle(self, pair: str, timeframe: str):
                self.cycles += 1
                return self.get_demo_robot_status()

            def get_dashboard_view_model(self):
                return SimpleNamespace(demo_robot=self.get_demo_robot_status())

        previous_session_state = dashboard_app.st.session_state
        try:
            dashboard_app.st.session_state = FakeSessionState(
                {dashboard_app.MT5_DEMO_ROBOT_ONLINE_KEY: True}
            )
            service = FakeService()

            first_data, first_online = dashboard_app._run_demo_robot_online_cycle_if_due(
                service,
                SimpleNamespace(),
                selected_pair="TODOS",
                timeframe="M1",
            )
            second_data, second_online = dashboard_app._run_demo_robot_online_cycle_if_due(
                service,
                first_data,
                selected_pair="TODOS",
                timeframe="M1",
            )

            self.assertTrue(first_online)
            self.assertTrue(second_online)
            self.assertIs(second_data, first_data)
            self.assertEqual(service.cycles, 1)
        finally:
            dashboard_app.st.session_state = previous_session_state

    def test_robo_demo_online_global_cycle_roda_em_qualquer_aba(self) -> None:
        class FakeSessionState(dict):
            pass

        class FakeService:
            def __init__(self) -> None:
                self.cycles: list[tuple[str, str]] = []

            def get_demo_robot_status(self):
                return SimpleNamespace(
                    status="ARMED",
                    result_status="ARMED_WAITING",
                    provider="MT5_DEMO",
                    mt5_order_send_enabled=True,
                )

            def arm_demo_robot(self, pair: str, timeframe: str):
                return self.get_demo_robot_status()

            def run_online_demo_robot_cycle(self, pair: str, timeframe: str):
                self.cycles.append((pair, timeframe))
                return self.get_demo_robot_status()

            def get_dashboard_view_model(self):
                return SimpleNamespace(demo_robot=self.get_demo_robot_status())

        previous_session_state = dashboard_app.st.session_state
        try:
            dashboard_app.st.session_state = FakeSessionState(
                {dashboard_app.MT5_DEMO_ROBOT_ONLINE_KEY: True}
            )
            service = FakeService()
            data = SimpleNamespace(
                mt5_forex_signals=SimpleNamespace(timeframe="M15"),
            )

            dashboard_app._maybe_run_demo_robot_global_cycle(service, data)

            self.assertEqual(service.cycles, [("TODOS", "M15")])
        finally:
            dashboard_app.st.session_state = previous_session_state

    def test_robo_demo_online_rearma_backend_transitorio_antes_do_ciclo(self) -> None:
        class FakeSessionState(dict):
            pass

        class FakeService:
            def __init__(self) -> None:
                self.arm_calls = 0
                self.cycles = 0

            def get_demo_robot_status(self):
                return SimpleNamespace(
                    status="DISARMED",
                    result_status="DISARMED",
                    provider="MT5_DEMO_DISABLED",
                    mt5_order_send_enabled=False,
                )

            def arm_demo_robot(self, pair: str, timeframe: str):
                self.arm_calls += 1
                return SimpleNamespace(
                    status="ARMED",
                    result_status="ARMED_WAITING",
                    provider="MT5_DEMO",
                    mt5_order_send_enabled=True,
                )

            def run_online_demo_robot_cycle(self, pair: str, timeframe: str):
                self.cycles += 1
                return self.arm_demo_robot(pair, timeframe)

            def get_dashboard_view_model(self):
                return SimpleNamespace(demo_robot=self.arm_demo_robot("TODOS", "M1"))

        previous_session_state = dashboard_app.st.session_state
        try:
            dashboard_app.st.session_state = FakeSessionState(
                {dashboard_app.MT5_DEMO_ROBOT_ONLINE_KEY: True}
            )
            service = FakeService()

            _, online = dashboard_app._run_demo_robot_online_cycle_if_due(
                service,
                SimpleNamespace(),
                selected_pair="TODOS",
                timeframe="M1",
            )

            self.assertTrue(online)
            self.assertEqual(service.cycles, 1)
            self.assertGreaterEqual(service.arm_calls, 1)
            self.assertTrue(
                dashboard_app.st.session_state[
                    dashboard_app.MT5_DEMO_ROBOT_ONLINE_KEY
                ]
            )
        finally:
            dashboard_app.st.session_state = previous_session_state

    def test_robo_demo_online_nao_desarma_persistido_quando_backend_falha(self) -> None:
        class FakeSessionState(dict):
            pass

        class FakeService:
            def get_demo_robot_status(self):
                return SimpleNamespace(
                    status="DISARMED",
                    result_status="DISARMED",
                    provider="MT5_DEMO_DISABLED",
                    mt5_order_send_enabled=False,
                    message="backend ainda inicializando",
                )

            def arm_demo_robot(self, pair: str, timeframe: str):
                return self.get_demo_robot_status()

        persisted: list[dict[str, object]] = []

        def fake_persist(**kwargs):
            persisted.append(dict(kwargs))

        previous_session_state = dashboard_app.st.session_state
        previous_persist = dashboard_app._persist_demo_robot_online_state
        try:
            dashboard_app.st.session_state = FakeSessionState(
                {dashboard_app.MT5_DEMO_ROBOT_ONLINE_KEY: True}
            )
            dashboard_app._persist_demo_robot_online_state = fake_persist

            _, online = dashboard_app._run_demo_robot_online_cycle_if_due(
                FakeService(),
                SimpleNamespace(),
                selected_pair="TODOS",
                timeframe="M1",
            )

            self.assertTrue(online)
            self.assertTrue(
                dashboard_app.st.session_state[
                    dashboard_app.MT5_DEMO_ROBOT_ONLINE_KEY
                ]
            )
            self.assertTrue(persisted)
            self.assertTrue(persisted[-1]["online"])
            self.assertIn("ultimo comando", str(persisted[-1]["message"]))
        finally:
            dashboard_app.st.session_state = previous_session_state
            dashboard_app._persist_demo_robot_online_state = previous_persist

    def test_auto_refresh_nao_recarrega_pagina_inteira_por_padrao(self) -> None:
        original_st = dashboard_app.st
        original_components = dashboard_app.components
        original_forex_enabled = dashboard_app._mt5_forex_auto_cycle_enabled
        original_report_enabled = dashboard_app._mt5_report_auto_refresh_enabled
        previous_flag = os.environ.pop("TRADERIA_UI_FULL_PAGE_RELOAD_ENABLED", None)
        fake_st = self._fake_streamlit(button_clicked=False)
        html_calls = []
        dashboard_app.st = fake_st
        dashboard_app.components = SimpleNamespace(
            html=lambda body, **kwargs: html_calls.append(body)
        )
        dashboard_app._mt5_forex_auto_cycle_enabled = lambda: True
        dashboard_app._mt5_report_auto_refresh_enabled = lambda: False
        try:
            dashboard_app._inject_mt5_forex_auto_refresh()
        finally:
            dashboard_app.st = original_st
            dashboard_app.components = original_components
            dashboard_app._mt5_forex_auto_cycle_enabled = original_forex_enabled
            dashboard_app._mt5_report_auto_refresh_enabled = original_report_enabled
            if previous_flag is not None:
                os.environ["TRADERIA_UI_FULL_PAGE_RELOAD_ENABLED"] = previous_flag

        self.assertEqual(html_calls, [])

    def test_ciclo_leve_preserva_snapshot_forex_quando_refresh_vem_vazio(self) -> None:
        previous = SimpleNamespace(
            mt5_forex_signals=SimpleNamespace(
                pairs=[SimpleNamespace(pair="EURUSD")],
                connection_status="ONLINE",
            )
        )
        refreshed = SimpleNamespace(
            mt5_forex_signals=SimpleNamespace(
                pairs=[],
                connection_status="N/D",
            )
        )

        result = dashboard_app._preserve_mt5_forex_snapshot_if_empty(
            previous,
            refreshed,
        )

        self.assertIs(result, previous)
        self.assertEqual(
            dashboard_app._forex_pairs_count(result.mt5_forex_signals),
            1,
        )

    def test_snapshot_forex_estavel_usa_ultimo_valido_quando_leitura_vem_vazia(self) -> None:
        class FakeSessionState(dict):
            pass

        previous_session_state = dashboard_app.st.session_state
        valid = SimpleNamespace(
            pairs=[SimpleNamespace(pair="EURUSD")],
            connection_status="ONLINE",
        )
        empty = SimpleNamespace(
            pairs=[],
            connection_status="OFFLINE",
        )
        try:
            dashboard_app.st.session_state = FakeSessionState()

            first = dashboard_app._stable_mt5_forex_snapshot(valid)
            second = dashboard_app._stable_mt5_forex_snapshot(empty)

            self.assertIs(first, valid)
            self.assertIs(second, valid)
            self.assertEqual(dashboard_app._forex_pairs_count(second), 1)
        finally:
            dashboard_app.st.session_state = previous_session_state

    def test_sugestoes_lab_estaveis_usam_ultimo_snapshot_valido(self) -> None:
        class FakeSessionState(dict):
            pass

        previous_session_state = dashboard_app.st.session_state
        valid = [
            SimpleNamespace(
                alpha_id="ALPHA006",
                pair="EURJPY",
                timeframe="M1",
            )
        ]
        try:
            dashboard_app.st.session_state = FakeSessionState()

            first = dashboard_app._stable_mt5_lab_setup_suggestions(valid)
            second = dashboard_app._stable_mt5_lab_setup_suggestions([])

            self.assertEqual(first, valid)
            self.assertEqual(second, valid)
        finally:
            dashboard_app.st.session_state = previous_session_state

    def test_auto_refresh_total_exige_flag_explicita(self) -> None:
        original_st = dashboard_app.st
        original_components = dashboard_app.components
        original_forex_enabled = dashboard_app._mt5_forex_auto_cycle_enabled
        original_report_enabled = dashboard_app._mt5_report_auto_refresh_enabled
        previous_flag = os.environ.get("TRADERIA_UI_FULL_PAGE_RELOAD_ENABLED")
        os.environ["TRADERIA_UI_FULL_PAGE_RELOAD_ENABLED"] = "1"
        fake_st = self._fake_streamlit(button_clicked=False)
        html_calls = []
        dashboard_app.st = fake_st
        dashboard_app.components = SimpleNamespace(
            html=lambda body, **kwargs: html_calls.append(body)
        )
        dashboard_app._mt5_forex_auto_cycle_enabled = lambda: True
        dashboard_app._mt5_report_auto_refresh_enabled = lambda: False
        try:
            dashboard_app._inject_mt5_forex_auto_refresh()
        finally:
            dashboard_app.st = original_st
            dashboard_app.components = original_components
            dashboard_app._mt5_forex_auto_cycle_enabled = original_forex_enabled
            dashboard_app._mt5_report_auto_refresh_enabled = original_report_enabled
            if previous_flag is None:
                os.environ.pop("TRADERIA_UI_FULL_PAGE_RELOAD_ENABLED", None)
            else:
                os.environ["TRADERIA_UI_FULL_PAGE_RELOAD_ENABLED"] = previous_flag

        self.assertTrue(html_calls)
        self.assertIn("window.parent.location.reload()", html_calls[0])

    def test_interacao_critica_bloqueia_refresh_pesado(self) -> None:
        original_st = dashboard_app.st
        fake_st = self._fake_streamlit(button_clicked=False)
        previous = os.environ.get("TRADERIA_UI_INTERACTION_GRACE_SECONDS")
        os.environ["TRADERIA_UI_INTERACTION_GRACE_SECONDS"] = "20"
        dashboard_app.st = fake_st
        try:
            dashboard_app._mark_ui_critical_interaction()

            self.assertTrue(dashboard_app._ui_in_critical_interaction_grace())
        finally:
            dashboard_app.st = original_st
            if previous is None:
                os.environ.pop("TRADERIA_UI_INTERACTION_GRACE_SECONDS", None)
            else:
                os.environ["TRADERIA_UI_INTERACTION_GRACE_SECONDS"] = previous

    def test_relatorio_mt5_auto_refresh_e_leve_por_intervalo(self) -> None:
        original_st = dashboard_app.st
        original_loader = dashboard_app._load_mt5_trade_audit_report_locked
        original_enabled = dashboard_app._mt5_report_auto_refresh_enabled
        fake_st = self._fake_streamlit(button_clicked=False)
        calls = []

        def fake_loader(service):
            calls.append(service)
            return SimpleNamespace(total_audited=len(calls))

        dashboard_app.st = fake_st
        dashboard_app._load_mt5_trade_audit_report_locked = fake_loader
        dashboard_app._mt5_report_auto_refresh_enabled = lambda: True
        try:
            first = dashboard_app._maybe_refresh_mt5_trade_audit_report(
                SimpleNamespace(),
                None,
            )
            second = dashboard_app._maybe_refresh_mt5_trade_audit_report(
                SimpleNamespace(),
                first,
            )
        finally:
            dashboard_app.st = original_st
            dashboard_app._load_mt5_trade_audit_report_locked = original_loader
            dashboard_app._mt5_report_auto_refresh_enabled = original_enabled

        self.assertIs(first, second)
        self.assertEqual(len(calls), 1)

    def _run_app(self, selected_tab: str | None = None) -> AppTest:
        previous_fast_boot = os.environ.get("TRADERIA_FAST_BOOT_ENABLED")
        os.environ["TRADERIA_FAST_BOOT_ENABLED"] = "0"
        try:
            app = AppTest.from_file("dashboard_app.py")
            app.run(timeout=30)
            if selected_tab is not None:
                app.segmented_control[0].set_value(selected_tab)
                app.run(timeout=30)
        finally:
            if previous_fast_boot is None:
                os.environ.pop("TRADERIA_FAST_BOOT_ENABLED", None)
            else:
                os.environ["TRADERIA_FAST_BOOT_ENABLED"] = previous_fast_boot
        return app

    def _fake_streamlit(self, *, button_clicked: bool):
        class FakeContext:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def button(self, *args, **kwargs):
                return button_clicked

            def caption(self, *args, **kwargs):
                return None

            def metric(self, *args, **kwargs):
                return None

        class FakeStreamlit:
            def __init__(self):
                self.session_state = {}

            def container(self, *args, **kwargs):
                return FakeContext()

            def columns(self, spec):
                size = spec if isinstance(spec, int) else len(spec)
                return [FakeContext() for _ in range(size)]

            def spinner(self, *args, **kwargs):
                return FakeContext()

            def caption(self, *args, **kwargs):
                return None

        return FakeStreamlit()

    def _button(self, app: AppTest, label: str):
        for button in app.button:
            if button.label == label:
                return button
        raise AssertionError(f"Botao nao encontrado: {label}")

    def _buttons(self, app: AppTest) -> list[str]:
        return [button.label for button in app.button]

    def _navigation_labels(self, app: AppTest) -> list[str]:
        if app.tabs:
            return [tab.label for tab in app.tabs]
        if app.segmented_control:
            return list(getattr(app.segmented_control[0], "options", []) or [])
        return []

    def _subheaders(self, app: AppTest) -> list[str]:
        return [subheader.value for subheader in app.subheader]

    def _captions(self, app: AppTest) -> list[str]:
        return [caption.value for caption in app.caption]

    def _selectboxes(self, app: AppTest) -> list[str]:
        return [selectbox.label for selectbox in app.selectbox]

    def _selectbox(self, app: AppTest, label: str):
        for selectbox in app.selectbox:
            if selectbox.label == label:
                return selectbox
        raise AssertionError(f"Selectbox nao encontrado: {label}")

    def _selectbox_values(self, app: AppTest) -> str:
        return "\n".join(str(selectbox.value) for selectbox in app.selectbox)

    def _checkboxes(self, app: AppTest) -> list[str]:
        return [checkbox.label for checkbox in app.checkbox]

    def _metrics(self, app: AppTest) -> dict[str, str]:
        return {metric.label: metric.value for metric in app.metric}

    def _warnings(self, app: AppTest) -> list[str]:
        return [warning.value for warning in app.warning]

    def _infos(self, app: AppTest) -> str:
        return "\n".join(str(info.value) for info in app.info)

    def _markdown(self, app: AppTest) -> str:
        return "\n".join(str(markdown.value) for markdown in app.markdown)

    def _dataframe_text(self, app: AppTest) -> str:
        return "\n".join(str(dataframe.value) for dataframe in app.dataframe)


if __name__ == "__main__":
    unittest.main()
