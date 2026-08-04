from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from research.multi_ea_trading_lab import (
    MultiEACandle,
    MultiEATradePosition,
    MultiEATradingLabEngine,
    _fit_classification,
    _ranking_sort_key,
)


class MultiEATradingLabEngineTest(unittest.TestCase):
    def test_nao_usa_candle_ainda_aberto_na_entrada(self) -> None:
        start = datetime(2026, 1, 1)
        base = [
            MultiEACandle(
                symbol="EURUSD",
                source_symbol="EURUSD",
                timeframe="H1",
                timestamp=start + timedelta(hours=index),
                open=1.0 + index * 0.001,
                high=1.002 + index * 0.001,
                low=0.998 + index * 0.001,
                close=1.001 + index * 0.001,
                volume=100,
            )
            for index in range(80)
        ]
        entry_time = start + timedelta(hours=60, minutes=30)
        position = self._position(
            "p1",
            "EURUSD",
            "BUY",
            entry_time,
            entry_time + timedelta(hours=2),
        )
        altered = list(base)
        current = altered[60]
        altered[60] = MultiEACandle(
            symbol=current.symbol,
            source_symbol=current.source_symbol,
            timeframe=current.timeframe,
            timestamp=current.timestamp,
            open=current.open,
            high=9.0,
            low=0.1,
            close=8.0,
            volume=current.volume,
        )

        first = MultiEATradingLabEngine().analyze([position], base)
        second = MultiEATradingLabEngine().analyze([position], altered)

        self.assertEqual(first["ranking_global"], second["ranking_global"])
        h1 = next(
            row
            for row in first["coverage"]["by_series"]
            if row["market"] == "EURUSD" and row["timeframe"] == "H1"
        )
        self.assertEqual(h1["eligible_positions"], 1)

    def test_detecta_hedge_concorrencia_e_cluster_sem_afirmar_grade(self) -> None:
        start = datetime(2026, 1, 1, 10)
        positions = [
            self._position(
                "p1",
                "XAUUSD",
                "BUY",
                start,
                start + timedelta(minutes=20),
            ),
            self._position(
                "p2",
                "XAUUSD",
                "SELL",
                start + timedelta(minutes=5),
                start + timedelta(minutes=21),
            ),
            self._position(
                "p3",
                "EURUSD",
                "BUY",
                start + timedelta(minutes=6),
                start + timedelta(minutes=22),
            ),
        ]

        result = MultiEATradingLabEngine().analyze(positions, [])
        behavior = result["behavior"]

        self.assertEqual(behavior["maximum_concurrent_positions"], 3)
        self.assertEqual(behavior["opposite_overlap_positions"], 2)
        self.assertEqual(behavior["same_symbol_close_clusters_120s"], 1)
        self.assertEqual(behavior["positions_in_close_clusters_120s"], 2)
        self.assertIn("nao provam", behavior["interpretation"])

    def test_preserva_perfil_publico_separado_da_amostra(self) -> None:
        result = MultiEATradingLabEngine().analyze([], [])

        profile = result["reported_profile"]
        self.assertEqual(profile["estatistica"]["operacoes"], 346)
        self.assertEqual(profile["estatistica"]["fator_de_lucro"], 2.0)
        self.assertEqual(profile["identificacao"]["alavancagem"], "1:500")
        self.assertEqual(
            sum(profile["distribuicao_publica_operacoes"].values()),
            346,
        )
        self.assertTrue(result["research_only"])
        self.assertFalse(result["operational_eligible"])
        self.assertIn("FUSO_NAO_INFORMADO", " ".join(result["warnings"]))

    def test_ranking_expoe_parametros_e_holdout_sem_claim_de_identificacao(self) -> None:
        start = datetime(2025, 1, 1)
        candles = [
            MultiEACandle(
                symbol="EURUSD",
                source_symbol="EURUSD",
                timeframe="H1",
                timestamp=start + timedelta(hours=index),
                open=1.0 + index * 0.0001,
                high=1.001 + index * 0.0001,
                low=0.999 + index * 0.0001,
                close=1.0005 + index * 0.0001,
                volume=100,
            )
            for index in range(220)
        ]
        positions = [
            self._position(
                f"p{index}",
                "EURUSD",
                "BUY" if index % 3 else "SELL",
                start + timedelta(hours=80 + index * 4, minutes=30),
                start + timedelta(hours=81 + index * 4),
            )
            for index in range(30)
        ]

        result = MultiEATradingLabEngine().analyze(positions, candles)
        best = result["ranking_global"][0]

        self.assertIsInstance(best["parameters"], dict)
        self.assertEqual(best["eligible"], 30)
        self.assertGreater(best["holdout"]["eligible"], 0)
        self.assertIn("selection_score", best)
        self.assertNotEqual(best["classification"], "IDENTIFICADO")
        self.assertFalse(result["methodology"]["lookahead"])

    def test_score_de_regra_aleatoria_com_cobertura_total_tem_baseline_zero(self) -> None:
        events = [
            {
                "observed": "BUY" if index % 2 == 0 else "SELL",
                "signal": "BUY" if index % 4 < 2 else "SELL",
                "exact": index % 4 in {0, 3},
                "opposite": index % 4 in {1, 2},
                "wait": False,
            }
            for index in range(40)
        ]

        metrics = MultiEATradingLabEngine()._event_metrics(events)

        self.assertEqual(metrics["observed_recall"], 1.0)
        self.assertEqual(metrics["direction_accuracy"], 0.5)
        self.assertEqual(metrics["score"], 0.0)

    def test_ordenacao_nao_consulta_score_total_classificacao_ou_holdout(self) -> None:
        preferred_by_train = {
            "selection_score": 0.30,
            "score": 0.0,
            "classification": "INSTAVEL_NO_HOLDOUT",
            "train": {"eligible": 70, "signaled": 30, "observed_recall": 0.4},
            "holdout": {"score": 0.0},
        }
        preferred_only_by_holdout = {
            "selection_score": 0.20,
            "score": 1.0,
            "classification": "HIPOTESE_PLAUSIVEL_NAO_IDENTIFICADA",
            "train": {"eligible": 70, "signaled": 70, "observed_recall": 1.0},
            "holdout": {"score": 1.0},
        }

        ranked = sorted(
            [preferred_only_by_holdout, preferred_by_train],
            key=_ranking_sort_key,
            reverse=True,
        )

        self.assertIs(ranked[0], preferred_by_train)

    def test_regra_sem_um_unico_gatilho_nao_e_suportada_pela_amostra(self) -> None:
        classification = _fit_classification(
            {"eligible": 100, "signaled": 0, "score": 0.0},
            {"eligible": 40, "signaled": 0, "score": 0.0},
        )

        self.assertEqual(classification, "NAO_SUPORTADA_PELA_AMOSTRA")

    def _position(
        self,
        position_id: str,
        symbol: str,
        direction: str,
        open_time: datetime,
        close_time: datetime,
    ) -> MultiEATradePosition:
        return MultiEATradePosition(
            source_symbol=symbol,
            symbol=symbol,
            direction=direction,
            volume=0.01,
            open_time=open_time,
            open_price=1.0,
            close_time=close_time,
            close_price=1.01,
            commission=-0.01,
            swap=0.0,
            profit=1.0,
            source_row=1,
            position_id=position_id,
        )


if __name__ == "__main__":
    unittest.main()
