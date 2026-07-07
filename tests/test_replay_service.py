"""Testes do servico de replay."""

import unittest

from application.replay_service import PaperMetrics, ReplayData, ReplayService
from application.replay_service import PaperPosition, ReplayStatus
from application.research_service import ResearchData
from core.events import (
    DECISION_CREATED,
    FEATURE_SNAPSHOT_CREATED,
    NEW_CANDLE,
    ORDER_CLOSED,
    ORDER_CREATED,
    REGIME_ANALYSIS_CREATED,
    RESEARCH_ANALYSIS_CREATED,
    STRATEGY_SIGNAL_CREATED,
)
from domain.candle import Candle
from domain.contracts.decision_context import DecisionContext
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.strategy_signal import StrategySignal
from market.regime_engine import RegimeAnalysis


class StaticStrategy:
    """Estrategia fixa para testes de preview de ordem."""

    nome = "static"

    def __init__(self, decision: str) -> None:
        self.decision = decision

    def analisar(self, estado: object) -> StrategySignal:
        """Retorna sempre a decisao configurada."""
        return StrategySignal(
            decision=self.decision,
            score=80,
            confidence=0.8,
            reasons=["Sinal estatico de teste"],
        )


def build_candle(
    maxima: float,
    minima: float,
    fechamento: float,
) -> Candle:
    """Cria candle simples para testes de replay."""
    return Candle(
        data="2026-06-26 09:00",
        abertura=fechamento,
        maxima=maxima,
        minima=minima,
        fechamento=fechamento,
        volume=1000,
    )


def load_test_candles(
    service: ReplayService,
    candles: list[Candle],
) -> None:
    """Carrega candles controlados no ReplayService."""
    service.replay_engine.load_candles(candles)
    service.status = ReplayStatus.READY


class ReplayServiceTest(unittest.TestCase):
    """Valida controle de replay pela camada de aplicacao."""

    def test_load_demo_candles_carrega_candles_ficticios(self) -> None:
        """Garante carga demonstrativa em memoria."""
        data = ReplayService().load_demo_candles()

        self.assertIsInstance(data, ReplayData)
        self.assertGreater(data.total_candles, 0)
        self.assertEqual(data.current_index, -1)
        self.assertEqual(len(data.candles_loaded), data.total_candles)
        self.assertEqual(data.candles_processed, [])
        self.assertEqual(data.status, ReplayStatus.READY)

    def test_start_inicia_replay(self) -> None:
        """Garante inicio do replay."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.start()

        self.assertTrue(data.is_running)
        self.assertEqual(data.current_index, 0)
        self.assertEqual(data.status, ReplayStatus.RUNNING)

    def test_stop_para_replay(self) -> None:
        """Garante parada do replay."""
        service = ReplayService()
        service.load_demo_candles()
        service.start()

        data = service.stop()

        self.assertFalse(data.is_running)
        self.assertEqual(data.status, ReplayStatus.PAUSED)

    def test_next_candle_avanca_e_retorna_estado(self) -> None:
        """Garante avanco candle a candle."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.next_candle()

        self.assertEqual(data.current_index, 0)
        self.assertIsNotNone(data.current_candle)

    def test_next_candle_atualiza_candle_history(self) -> None:
        """Garante que o candle avancado entra no historico."""
        service = ReplayService()
        service.load_demo_candles()

        service.next_candle()

        self.assertEqual(service.candle_history.count(), 1)

    def test_next_candle_gera_feature_snapshot(self) -> None:
        """Garante calculo de features apos avanco."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsNotNone(data.feature_snapshot)
        self.assertEqual(data.feature_snapshot.candles_count, 1)

    def test_next_candle_gera_regime_analysis(self) -> None:
        """Garante analise de regime apos avanco."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsInstance(data.regime_analysis, RegimeAnalysis)
        self.assertTrue(data.regime_analysis.description)

    def test_replay_data_inclui_regime_analysis(self) -> None:
        """Garante exposicao da analise de regime no DTO."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsNotNone(data.regime_analysis)

    def test_next_candle_gera_pesquisa_quantitativa(self) -> None:
        """Garante pesquisa quantitativa apos avanco."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsInstance(data.research_data, ResearchData)
        self.assertEqual(data.research_data.similar_scenarios, 0)

    def test_market_memory_aumenta_apos_avanco(self) -> None:
        """Garante que o cenario atual e lembrado apos pesquisa."""
        service = ReplayService()
        service.load_demo_candles()

        service.next_candle()
        service.next_candle()

        self.assertEqual(service.market_memory.count(), 2)

    def test_replay_data_inclui_research_data(self) -> None:
        """Garante exposicao da pesquisa quantitativa no DTO."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsNotNone(data.research_data)

    def test_next_candle_gera_strategy_signal(self) -> None:
        """Garante geracao de sinal de estrategia no replay."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsInstance(data.strategy_signal, StrategySignal)
        self.assertIn(data.strategy_signal.decision, {"BUY", "SELL", "WAIT"})

    def test_select_strategy_altera_estrategia_executada_no_replay(self) -> None:
        """Seletor de estrategia deve trocar a StrategySignal real do Replay."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.select_strategy("breakout")
        data = service.next_candle()

        self.assertEqual(service.get_active_strategy_name(), "breakout")
        self.assertEqual(data.active_strategy_name, "breakout")
        self.assertEqual(data.active_strategy_label, "Breakout")
        self.assertEqual(service.strategy.nome, "breakout")
        self.assertIsInstance(data.strategy_signal, StrategySignal)
        self.assertIn("rompimento", " ".join(data.strategy_signal.reasons).lower())

    def test_select_strategy_rejeita_estrategia_nao_registrada(self) -> None:
        """Replay deve expor apenas estrategias registradas pela factory."""
        service = ReplayService()

        with self.assertRaises(ValueError):
            service.select_strategy("alpha_inexistente")

    def test_select_strategy_alpha101_altera_alpha_executada(self) -> None:
        """Replay deve aceitar Alpha101 registrada como StrategySignal."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.select_strategy("alpha101")
        data = service.next_candle()

        self.assertEqual(data.active_strategy_name, "alpha101")
        self.assertEqual(
            data.active_strategy_label,
            "Alpha101 Volume Momentum Breakout",
        )
        self.assertIsInstance(data.strategy_signal, StrategySignal)

    def test_alpha001_informa_incompatibilidade_com_petr4_diario(self) -> None:
        """Alpha001 deve avisar quando usada em PETR4 1D."""
        service = ReplayService()
        service.active_symbol = "PETR4"
        service.active_timeframe = "1d"

        data = service.get_replay_data()

        self.assertEqual(
            data.strategy_compatibility_warning,
            "Alpha001 IORB é incompatível com PETR4 1D. Esperado: WDO intraday.",
        )

    def test_replay_data_inclui_strategy_signal(self) -> None:
        """Garante exposicao do sinal de estrategia no DTO."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsNotNone(data.strategy_signal)

    def test_next_candle_gera_decision_context(self) -> None:
        """Garante preview do DecisionPipeline no replay."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsInstance(data.decision_context, DecisionContext)
        self.assertEqual(
            data.decision_context.risk_decision.reason,
            "Replay de pesquisa. Operacao real nao autorizada.",
        )

    def test_replay_data_inclui_decision_context(self) -> None:
        """Garante exposicao do contexto de decisao no DTO."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsNotNone(data.decision_context)

    def test_buy_gera_order_preview_com_stop_e_target_corretos(self) -> None:
        """Garante previa simulada de compra sem envio real de ordem."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        service.load_demo_candles()

        data = service.next_candle()
        configuration = service.configuration_service.get_configuration_data()
        entry_price = data.current_candle.fechamento

        self.assertIsInstance(data.order_preview, ExecutionOrder)
        self.assertEqual(data.order_preview.side, "BUY")
        self.assertEqual(data.order_preview.quantity, 1)
        self.assertEqual(data.order_preview.entry_price, entry_price)
        self.assertEqual(
            data.order_preview.stop,
            entry_price - configuration.stop_points,
        )
        self.assertEqual(
            data.order_preview.target,
            entry_price + configuration.target_points,
        )

    def test_sell_gera_order_preview_com_stop_e_target_corretos(self) -> None:
        """Garante previa simulada de venda sem envio real de ordem."""
        service = ReplayService(strategy=StaticStrategy("SELL"))
        service.load_demo_candles()

        data = service.next_candle()
        configuration = service.configuration_service.get_configuration_data()
        entry_price = data.current_candle.fechamento

        self.assertIsInstance(data.order_preview, ExecutionOrder)
        self.assertEqual(data.order_preview.side, "SELL")
        self.assertEqual(data.order_preview.quantity, 1)
        self.assertEqual(data.order_preview.entry_price, entry_price)
        self.assertEqual(
            data.order_preview.stop,
            entry_price + configuration.stop_points,
        )
        self.assertEqual(
            data.order_preview.target,
            entry_price - configuration.target_points,
        )

    def test_wait_nao_gera_order_preview(self) -> None:
        """Garante que WAIT nao cria previa de ordem."""
        service = ReplayService(strategy=StaticStrategy("WAIT"))
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsNone(data.order_preview)

    def test_abre_paper_position_buy(self) -> None:
        """Garante abertura de posicao simulada de compra."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsInstance(data.paper_position, PaperPosition)
        self.assertEqual(data.paper_position.side, "BUY")
        self.assertEqual(data.paper_position.status, "OPEN")

    def test_fecha_paper_position_buy_no_stop(self) -> None:
        """Garante fechamento de compra simulada por stop."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        entry = 1000.0
        load_test_candles(
            service,
            [
                build_candle(entry + 1.0, entry - 1.0, entry),
                build_candle(entry + 1.0, entry - config.stop_points, entry),
            ],
        )

        service.next_candle()
        data = service.next_candle()

        self.assertEqual(data.paper_position.status, "STOP")
        self.assertEqual(data.paper_position.exit_price, entry - config.stop_points)
        self.assertEqual(data.paper_position.result_points, -config.stop_points)
        self.assertEqual(data.paper_position.close_reason, "STOP")
        self.assertIn(
            ORDER_CLOSED,
            [event.event_name for event in data.recent_events],
        )

    def test_fecha_paper_position_buy_no_target(self) -> None:
        """Garante fechamento de compra simulada por target."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        entry = 1000.0
        load_test_candles(
            service,
            [
                build_candle(entry + 1.0, entry - 1.0, entry),
                build_candle(entry + config.target_points, entry - 1.0, entry),
            ],
        )

        service.next_candle()
        data = service.next_candle()

        self.assertEqual(data.paper_position.status, "TARGET")
        self.assertEqual(
            data.paper_position.exit_price,
            entry + config.target_points,
        )
        self.assertEqual(data.paper_position.result_points, config.target_points)
        self.assertEqual(data.paper_position.close_reason, "TARGET")

    def test_abre_paper_position_sell(self) -> None:
        """Garante abertura de posicao simulada de venda."""
        service = ReplayService(strategy=StaticStrategy("SELL"))
        service.load_demo_candles()

        data = service.next_candle()

        self.assertIsInstance(data.paper_position, PaperPosition)
        self.assertEqual(data.paper_position.side, "SELL")
        self.assertEqual(data.paper_position.status, "OPEN")

    def test_fecha_paper_position_sell_no_stop(self) -> None:
        """Garante fechamento de venda simulada por stop."""
        service = ReplayService(strategy=StaticStrategy("SELL"))
        config = service.configuration_service.get_configuration_data()
        entry = 1000.0
        load_test_candles(
            service,
            [
                build_candle(entry + 1.0, entry - 1.0, entry),
                build_candle(entry + config.stop_points, entry - 1.0, entry),
            ],
        )

        service.next_candle()
        data = service.next_candle()

        self.assertEqual(data.paper_position.status, "STOP")
        self.assertEqual(data.paper_position.exit_price, entry + config.stop_points)
        self.assertEqual(data.paper_position.result_points, -config.stop_points)
        self.assertEqual(data.paper_position.close_reason, "STOP")

    def test_fecha_paper_position_sell_no_target(self) -> None:
        """Garante fechamento de venda simulada por target."""
        service = ReplayService(strategy=StaticStrategy("SELL"))
        config = service.configuration_service.get_configuration_data()
        entry = 1000.0
        load_test_candles(
            service,
            [
                build_candle(entry + 1.0, entry - 1.0, entry),
                build_candle(entry + 1.0, entry - config.target_points, entry),
            ],
        )

        service.next_candle()
        data = service.next_candle()

        self.assertEqual(data.paper_position.status, "TARGET")
        self.assertEqual(
            data.paper_position.exit_price,
            entry - config.target_points,
        )
        self.assertEqual(data.paper_position.result_points, config.target_points)
        self.assertEqual(data.paper_position.close_reason, "TARGET")

    def test_operacao_fechada_entra_no_historico_paper(self) -> None:
        """Garante registro de posicao fechada no historico."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        entry = 1000.0
        load_test_candles(
            service,
            [
                build_candle(entry + 1.0, entry - 1.0, entry),
                build_candle(entry + config.target_points, entry - 1.0, entry),
            ],
        )

        service.next_candle()
        data = service.next_candle()

        self.assertEqual(data.total_paper_trades, 1)
        self.assertEqual(len(data.paper_trades_history), 1)
        self.assertEqual(data.paper_trades_history[0].status, "TARGET")

    def test_resultado_total_paper_soma_corretamente(self) -> None:
        """Garante soma dos pontos das operacoes fechadas."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        load_test_candles(
            service,
            self._two_closed_buy_trades(config.stop_points),
        )

        while not service.get_replay_data().is_finished:
            data = service.next_candle()

        expected = config.target_points - config.stop_points
        self.assertEqual(data.total_paper_trades, 2)
        self.assertEqual(data.total_paper_result_points, expected)

    def test_wins_e_losses_paper_contam_corretamente(self) -> None:
        """Garante contagem de vitorias e derrotas paper."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        load_test_candles(
            service,
            self._two_closed_buy_trades(config.stop_points),
        )

        while not service.get_replay_data().is_finished:
            data = service.next_candle()

        self.assertEqual(data.wins, 1)
        self.assertEqual(data.losses, 1)

    def test_curva_paper_inicia_em_zero(self) -> None:
        """Garante inicio da curva de patrimonio paper."""
        data = ReplayService().get_replay_data()

        self.assertEqual(data.paper_equity_curve, [0.0])
        self.assertEqual(data.current_equity_points, 0.0)
        self.assertEqual(data.max_equity_points, 0.0)
        self.assertEqual(data.min_equity_points, 0.0)

    def test_fechamento_positivo_aumenta_curva_paper(self) -> None:
        """Garante incremento da curva em trade positivo."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        entry = 1000.0
        load_test_candles(
            service,
            [
                build_candle(entry + 1.0, entry - 1.0, entry),
                build_candle(entry + config.target_points, entry - 1.0, entry),
            ],
        )

        service.next_candle()
        data = service.next_candle()

        self.assertEqual(data.paper_equity_curve, [0.0, config.target_points])
        self.assertEqual(data.current_equity_points, config.target_points)

    def test_fechamento_negativo_reduz_curva_paper(self) -> None:
        """Garante reducao da curva em trade negativo."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        entry = 1000.0
        load_test_candles(
            service,
            [
                build_candle(entry + 1.0, entry - 1.0, entry),
                build_candle(entry + 1.0, entry - config.stop_points, entry),
            ],
        )

        service.next_candle()
        data = service.next_candle()

        self.assertEqual(data.paper_equity_curve, [0.0, -config.stop_points])
        self.assertEqual(data.current_equity_points, -config.stop_points)

    def test_max_min_da_curva_paper_sao_calculados(self) -> None:
        """Garante calculo dos extremos da curva paper."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        load_test_candles(
            service,
            self._two_closed_buy_trades(config.stop_points),
        )

        while not service.get_replay_data().is_finished:
            data = service.next_candle()

        expected_current = config.target_points - config.stop_points
        self.assertEqual(
            data.paper_equity_curve,
            [0.0, config.target_points, expected_current],
        )
        self.assertEqual(data.current_equity_points, expected_current)
        self.assertEqual(data.max_equity_points, config.target_points)
        self.assertEqual(data.min_equity_points, 0.0)

    def test_metricas_paper_sem_operacoes(self) -> None:
        """Garante metricas zeradas sem trades fechados."""
        data = ReplayService().get_replay_data()
        metrics = data.paper_metrics

        self.assertIsInstance(metrics, PaperMetrics)
        self.assertEqual(metrics.total_trades, 0)
        self.assertEqual(metrics.wins, 0)
        self.assertEqual(metrics.losses, 0)
        self.assertEqual(metrics.win_rate, 0.0)
        self.assertEqual(metrics.gross_profit_points, 0.0)
        self.assertEqual(metrics.gross_loss_points, 0.0)
        self.assertEqual(metrics.net_profit_points, 0.0)
        self.assertEqual(metrics.average_win_points, 0.0)
        self.assertEqual(metrics.average_loss_points, 0.0)
        self.assertEqual(metrics.profit_factor, 0.0)

    def test_metricas_paper_com_vitoria(self) -> None:
        """Garante metricas de uma operacao vencedora."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        data = self._run_single_buy_target(service, config.target_points)
        metrics = data.paper_metrics

        self.assertEqual(metrics.total_trades, 1)
        self.assertEqual(metrics.wins, 1)
        self.assertEqual(metrics.losses, 0)
        self.assertEqual(metrics.win_rate, 1.0)
        self.assertEqual(metrics.gross_profit_points, config.target_points)
        self.assertEqual(metrics.gross_loss_points, 0.0)
        self.assertEqual(metrics.net_profit_points, config.target_points)
        self.assertEqual(metrics.average_win_points, config.target_points)
        self.assertEqual(metrics.average_loss_points, 0.0)

    def test_metricas_paper_com_perda(self) -> None:
        """Garante metricas de uma operacao perdedora."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        data = self._run_single_buy_stop(service, config.stop_points)
        metrics = data.paper_metrics

        self.assertEqual(metrics.total_trades, 1)
        self.assertEqual(metrics.wins, 0)
        self.assertEqual(metrics.losses, 1)
        self.assertEqual(metrics.win_rate, 0.0)
        self.assertEqual(metrics.gross_profit_points, 0.0)
        self.assertEqual(metrics.gross_loss_points, config.stop_points)
        self.assertEqual(metrics.net_profit_points, -config.stop_points)
        self.assertEqual(metrics.average_win_points, 0.0)
        self.assertEqual(metrics.average_loss_points, -config.stop_points)
        self.assertEqual(metrics.profit_factor, 0.0)

    def test_profit_factor_sem_perdas(self) -> None:
        """Garante profit factor infinito quando ha lucro sem perda."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        data = self._run_single_buy_target(service, config.target_points)

        self.assertEqual(data.paper_metrics.profit_factor, float("inf"))

    def test_drawdown_sem_operacoes_e_zero(self) -> None:
        """Garante drawdown zerado sem trades fechados."""
        metrics = ReplayService().get_replay_data().paper_metrics

        self.assertEqual(metrics.current_drawdown_points, 0.0)
        self.assertEqual(metrics.max_drawdown_points, 0.0)
        self.assertEqual(metrics.peak_equity_points, 0.0)

    def test_drawdown_curva_subindo_e_zero(self) -> None:
        """Garante drawdown zerado em curva apenas positiva."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        data = self._run_single_buy_target(service, config.target_points)
        metrics = data.paper_metrics

        self.assertEqual(metrics.current_drawdown_points, 0.0)
        self.assertEqual(metrics.max_drawdown_points, 0.0)
        self.assertEqual(metrics.peak_equity_points, config.target_points)

    def test_drawdown_calcula_queda_apos_pico(self) -> None:
        """Garante drawdown atual apos queda da curva."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        load_test_candles(
            service,
            self._two_closed_buy_trades(config.stop_points),
        )

        while not service.get_replay_data().is_finished:
            data = service.next_candle()

        metrics = data.paper_metrics
        self.assertEqual(metrics.peak_equity_points, config.target_points)
        self.assertEqual(metrics.current_drawdown_points, config.stop_points)

    def test_max_drawdown_preserva_maior_queda(self) -> None:
        """Garante maior queda historica da curva paper."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        load_test_candles(
            service,
            self._win_loss_win_trades(config.stop_points),
        )

        while not service.get_replay_data().is_finished:
            data = service.next_candle()

        self.assertEqual(
            data.paper_metrics.max_drawdown_points,
            config.stop_points,
        )
        self.assertEqual(data.paper_metrics.current_drawdown_points, 0.0)

    def test_next_candle_registra_eventos_do_replay(self) -> None:
        """Garante registro dos eventos gerados no avanco."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        service.load_demo_candles()

        data = service.next_candle()
        event_names = [event.event_name for event in data.recent_events]

        self.assertEqual(data.event_count, 7)
        self.assertIn(NEW_CANDLE, event_names)
        self.assertIn(DECISION_CREATED, event_names)
        self.assertIn(FEATURE_SNAPSHOT_CREATED, event_names)
        self.assertIn(REGIME_ANALYSIS_CREATED, event_names)
        self.assertIn(RESEARCH_ANALYSIS_CREATED, event_names)
        self.assertIn(STRATEGY_SIGNAL_CREATED, event_names)
        self.assertIn(ORDER_CREATED, event_names)

    def test_replay_data_inclui_eventos_recentes(self) -> None:
        """Garante exposicao dos eventos recentes no DTO."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.next_candle()

        self.assertTrue(data.recent_events)
        self.assertEqual(data.event_count, len(data.recent_events))

    def test_enable_auto_run_ativa_replay_automatico(self) -> None:
        """Garante ativacao do auto replay."""
        service = ReplayService()
        service.load_demo_candles()

        data = service.enable_auto_run(0.5)

        self.assertTrue(data.auto_run_enabled)
        self.assertTrue(service.is_auto_run_enabled())
        self.assertEqual(data.replay_speed_seconds, 0.5)

    def test_disable_auto_run_desativa_replay_automatico(self) -> None:
        """Garante desativacao do auto replay."""
        service = ReplayService()
        service.load_demo_candles()
        service.enable_auto_run(0.5)

        data = service.disable_auto_run()

        self.assertFalse(data.auto_run_enabled)
        self.assertFalse(service.is_auto_run_enabled())

    def test_replay_data_inclui_estado_do_auto_run(self) -> None:
        """Garante exposicao do auto replay no DTO."""
        data = ReplayService().get_replay_data()

        self.assertFalse(data.auto_run_enabled)
        self.assertEqual(data.replay_speed_seconds, 1.0)

    def test_auto_run_desliga_ao_finalizar_replay(self) -> None:
        """Garante desligamento automatico no fim do replay."""
        service = ReplayService()
        service.load_demo_candles()
        service.enable_auto_run(0.5)

        while not service.get_replay_data().is_finished:
            data = service.next_candle()

        self.assertTrue(data.is_finished)
        self.assertFalse(data.auto_run_enabled)

    def test_feature_store_guarda_ultimo_snapshot(self) -> None:
        """Garante armazenamento do ultimo snapshot no FeatureStore."""
        service = ReplayService()
        service.load_demo_candles()

        first = service.next_candle()
        second = service.next_candle()

        self.assertIsNotNone(first.feature_snapshot)
        self.assertEqual(
            service.feature_store.latest(),
            second.feature_snapshot,
        )
        self.assertEqual(second.feature_snapshot.candles_count, 2)

    def test_next_candle_multiplas_vezes_preserva_estado(self) -> None:
        """Garante avancos sequenciais sem recarregar candles."""
        service = ReplayService()
        service.load_demo_candles()

        first = service.next_candle()
        second = service.next_candle()
        third = service.next_candle()

        self.assertEqual(first.current_index, 0)
        self.assertEqual(second.current_index, 1)
        self.assertEqual(third.current_index, 2)

    def test_candles_processed_aumenta_conforme_avanco(self) -> None:
        """Garante lista de candles processados no replay."""
        service = ReplayService()
        service.load_demo_candles()

        first = service.next_candle()
        second = service.next_candle()

        self.assertEqual(len(first.candles_processed), 1)
        self.assertEqual(len(second.candles_processed), 2)

    def test_reset_volta_para_inicio(self) -> None:
        """Garante reset do replay."""
        service = ReplayService()
        service.load_demo_candles()
        service.next_candle()

        data = service.reset()

        self.assertEqual(data.current_index, -1)
        self.assertIsNone(data.current_candle)
        self.assertIsNone(data.feature_snapshot)
        self.assertIsNone(data.regime_analysis)
        self.assertIsNone(data.research_data)
        self.assertIsNone(data.strategy_signal)
        self.assertIsNone(data.decision_context)
        self.assertIsNone(data.order_preview)
        self.assertIsNone(data.paper_position)
        self.assertEqual(data.paper_trades_history, [])
        self.assertEqual(data.total_paper_trades, 0)
        self.assertEqual(data.total_paper_result_points, 0.0)
        self.assertEqual(data.wins, 0)
        self.assertEqual(data.losses, 0)
        self.assertEqual(data.paper_equity_curve, [0.0])
        self.assertEqual(data.current_equity_points, 0.0)
        self.assertEqual(data.max_equity_points, 0.0)
        self.assertEqual(data.min_equity_points, 0.0)
        self.assertEqual(data.paper_metrics, PaperMetrics())
        self.assertEqual(service.candle_history.count(), 0)
        self.assertEqual(service.market_memory.count(), 0)
        self.assertEqual(data.event_count, 0)
        self.assertEqual(data.recent_events, [])
        self.assertEqual(data.candles_processed, [])
        self.assertGreater(len(data.candles_loaded), 0)
        self.assertEqual(data.status, ReplayStatus.READY)

    def test_get_replay_data_retorna_estado_atual(self) -> None:
        """Garante consulta do estado atual."""
        data = ReplayService().get_replay_data()

        self.assertIsInstance(data, ReplayData)
        self.assertEqual(data.total_candles, 0)
        self.assertEqual(data.status, ReplayStatus.EMPTY)

    def test_get_replay_data_inclui_campos_opcionais_com_none(self) -> None:
        """Garante contrato completo antes de qualquer candle."""
        data = ReplayService().get_replay_data()

        self.assertTrue(hasattr(data, "feature_snapshot"))
        self.assertTrue(hasattr(data, "regime_analysis"))
        self.assertTrue(hasattr(data, "research_data"))
        self.assertTrue(hasattr(data, "strategy_signal"))
        self.assertTrue(hasattr(data, "decision_context"))
        self.assertTrue(hasattr(data, "order_preview"))
        self.assertTrue(hasattr(data, "paper_position"))
        self.assertTrue(hasattr(data, "paper_trades_history"))
        self.assertTrue(hasattr(data, "total_paper_trades"))
        self.assertTrue(hasattr(data, "total_paper_result_points"))
        self.assertTrue(hasattr(data, "wins"))
        self.assertTrue(hasattr(data, "losses"))
        self.assertTrue(hasattr(data, "paper_equity_curve"))
        self.assertTrue(hasattr(data, "current_equity_points"))
        self.assertTrue(hasattr(data, "max_equity_points"))
        self.assertTrue(hasattr(data, "min_equity_points"))
        self.assertTrue(hasattr(data, "paper_metrics"))
        self.assertTrue(hasattr(data, "event_count"))
        self.assertTrue(hasattr(data, "recent_events"))
        self.assertTrue(hasattr(data, "candles_loaded"))
        self.assertTrue(hasattr(data, "candles_processed"))
        self.assertTrue(hasattr(data, "auto_run_enabled"))
        self.assertTrue(hasattr(data, "replay_speed_seconds"))
        self.assertTrue(hasattr(data, "status"))
        self.assertIsNone(data.feature_snapshot)
        self.assertIsNone(data.regime_analysis)
        self.assertIsNone(data.research_data)
        self.assertIsNone(data.strategy_signal)
        self.assertIsNone(data.decision_context)
        self.assertIsNone(data.order_preview)
        self.assertIsNone(data.paper_position)
        self.assertEqual(data.paper_trades_history, [])
        self.assertEqual(data.total_paper_trades, 0)
        self.assertEqual(data.total_paper_result_points, 0.0)
        self.assertEqual(data.wins, 0)
        self.assertEqual(data.losses, 0)
        self.assertEqual(data.paper_equity_curve, [0.0])
        self.assertEqual(data.current_equity_points, 0.0)
        self.assertEqual(data.max_equity_points, 0.0)
        self.assertEqual(data.min_equity_points, 0.0)
        self.assertEqual(data.paper_metrics, PaperMetrics())

    def test_reset_limpa_order_preview(self) -> None:
        """Garante que reset remove a previa simulada."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        service.load_demo_candles()
        service.next_candle()

        data = service.reset()

        self.assertIsNone(data.order_preview)

    def test_reset_limpa_paper_position(self) -> None:
        """Garante que reset remove a posicao simulada."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        service.load_demo_candles()
        service.next_candle()

        data = service.reset()

        self.assertIsNone(data.paper_position)

    def test_reset_limpa_historico_paper(self) -> None:
        """Garante que reset remove operacoes paper fechadas."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        entry = 1000.0
        load_test_candles(
            service,
            [
                build_candle(entry + 1.0, entry - 1.0, entry),
                build_candle(entry + config.target_points, entry - 1.0, entry),
            ],
        )
        service.next_candle()
        service.next_candle()

        data = service.reset()

        self.assertEqual(data.paper_trades_history, [])
        self.assertEqual(data.total_paper_trades, 0)
        self.assertEqual(data.total_paper_result_points, 0.0)
        self.assertEqual(data.wins, 0)
        self.assertEqual(data.losses, 0)

    def test_reset_limpa_curva_paper_para_zero(self) -> None:
        """Garante reset da curva de patrimonio paper."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        entry = 1000.0
        load_test_candles(
            service,
            [
                build_candle(entry + 1.0, entry - 1.0, entry),
                build_candle(entry + config.target_points, entry - 1.0, entry),
            ],
        )
        service.next_candle()
        service.next_candle()

        data = service.reset()

        self.assertEqual(data.paper_equity_curve, [0.0])
        self.assertEqual(data.current_equity_points, 0.0)
        self.assertEqual(data.max_equity_points, 0.0)
        self.assertEqual(data.min_equity_points, 0.0)

    def test_reset_limpa_metricas_paper(self) -> None:
        """Garante reset das metricas paper."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        self._run_single_buy_target(service, config.target_points)

        data = service.reset()

        self.assertEqual(data.paper_metrics, PaperMetrics())

    def test_reset_zera_drawdown_paper(self) -> None:
        """Garante reset dos campos de drawdown."""
        service = ReplayService(strategy=StaticStrategy("BUY"))
        config = service.configuration_service.get_configuration_data()
        self._run_single_buy_target(service, config.target_points)

        metrics = service.reset().paper_metrics

        self.assertEqual(metrics.current_drawdown_points, 0.0)
        self.assertEqual(metrics.max_drawdown_points, 0.0)
        self.assertEqual(metrics.peak_equity_points, 0.0)

    def test_start_nao_funciona_em_empty(self) -> None:
        """Impede RUNNING sem candles carregados."""
        data = ReplayService().start()

        self.assertEqual(data.status, ReplayStatus.EMPTY)
        self.assertFalse(data.is_running)
        self.assertEqual(data.total_candles, 0)

    def test_next_candle_nao_funciona_em_empty(self) -> None:
        """Impede avancar candle sem carga."""
        data = ReplayService().next_candle()

        self.assertEqual(data.status, ReplayStatus.EMPTY)
        self.assertEqual(data.current_index, -1)
        self.assertIsNone(data.current_candle)

    def test_auto_run_nao_funciona_em_empty(self) -> None:
        """Impede auto replay sem candles carregados."""
        data = ReplayService().enable_auto_run(0.5)

        self.assertEqual(data.status, ReplayStatus.EMPTY)
        self.assertFalse(data.auto_run_enabled)

    def test_status_finished_ao_processar_ultimo_candle(self) -> None:
        """Garante estado FINISHED no ultimo candle."""
        service = ReplayService()
        service.load_demo_candles()

        while not service.get_replay_data().is_finished:
            data = service.next_candle()

        self.assertEqual(data.status, ReplayStatus.FINISHED)
        self.assertFalse(data.auto_run_enabled)

    def test_nunca_running_com_total_zero_ou_index_menos_um(self) -> None:
        """Garante estados invalidos bloqueados."""
        empty = ReplayService().start()
        service = ReplayService()
        service.load_demo_candles()
        running = service.start()

        self.assertFalse(empty.is_running and empty.total_candles == 0)
        self.assertFalse(running.is_running and running.current_index == -1)

    def _two_closed_buy_trades(self, stop_points: float) -> list[Candle]:
        target_points = (
            self._configuration_target_points()
        )
        return [
            build_candle(1001.0, 999.0, 1000.0),
            build_candle(1000.0 + target_points, 999.0, 1000.0),
            build_candle(2001.0, 1999.0, 2000.0),
            build_candle(2001.0, 2000.0 - stop_points, 2000.0),
        ]

    def _win_loss_win_trades(self, stop_points: float) -> list[Candle]:
        target_points = self._configuration_target_points()
        return [
            build_candle(1001.0, 999.0, 1000.0),
            build_candle(1000.0 + target_points, 999.0, 1000.0),
            build_candle(2001.0, 1999.0, 2000.0),
            build_candle(2001.0, 2000.0 - stop_points, 2000.0),
            build_candle(3001.0, 2999.0, 3000.0),
            build_candle(3000.0 + target_points, 2999.0, 3000.0),
        ]

    def _configuration_target_points(self) -> float:
        service = ReplayService()
        return service.configuration_service.get_configuration_data().target_points

    def _run_single_buy_target(
        self,
        service: ReplayService,
        target_points: float,
    ) -> ReplayData:
        entry = 1000.0
        load_test_candles(
            service,
            [
                build_candle(entry + 1.0, entry - 1.0, entry),
                build_candle(entry + target_points, entry - 1.0, entry),
            ],
        )
        service.next_candle()
        return service.next_candle()

    def _run_single_buy_stop(
        self,
        service: ReplayService,
        stop_points: float,
    ) -> ReplayData:
        entry = 1000.0
        load_test_candles(
            service,
            [
                build_candle(entry + 1.0, entry - 1.0, entry),
                build_candle(entry + 1.0, entry - stop_points, entry),
            ],
        )
        service.next_candle()
        return service.next_candle()


if __name__ == "__main__":
    unittest.main()
