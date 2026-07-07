"""Testes do motor de permissao de mercado da Alpha 001."""

import unittest

from alpha.market_permission_engine import (
    MarketPermission,
    MarketPermissionEngine,
    MarketPermissionResult,
)
from application.research_service import ResearchData
from market.feature_engine import FeatureSnapshot
from market.regime_engine import MarketRegime, RegimeAnalysis


class MarketPermissionEngineTest(unittest.TestCase):
    """Valida filtros iniciais da Alpha 001 IORB."""

    def test_deny_quando_regime_range(self) -> None:
        """Regime RANGE deve bloquear operacao."""
        result = MarketPermissionEngine().evaluate(
            self._feature_snapshot(),
            self._regime(MarketRegime.RANGE),
            self._research_data(),
        )

        self.assertEqual(result.permission, MarketPermission.DENY)
        self.assertIn("Regime RANGE nao permite operacao.", result.reasons)

    def test_deny_quando_volatilidade_low(self) -> None:
        """Volatilidade LOW deve bloquear operacao."""
        result = MarketPermissionEngine().evaluate(
            self._feature_snapshot(volatility_level="LOW"),
            self._regime(),
            self._research_data(),
        )

        self.assertEqual(result.permission, MarketPermission.DENY)
        self.assertIn("Volatilidade LOW nao permite operacao.", result.reasons)

    def test_deny_quando_research_confidence_baixo(self) -> None:
        """Research confidence abaixo de 60 deve bloquear operacao."""
        result = MarketPermissionEngine().evaluate(
            self._feature_snapshot(),
            self._regime(),
            self._research_data(confidence=59.0),
        )

        self.assertEqual(result.permission, MarketPermission.DENY)
        self.assertIn("Research confidence abaixo do minimo.", result.reasons)

    def test_allow_quando_filtros_sao_favoraveis(self) -> None:
        """Mercado favoravel deve permitir avaliacao operacional."""
        result = MarketPermissionEngine().evaluate(
            self._feature_snapshot(),
            self._regime(),
            self._research_data(),
        )

        self.assertIsInstance(result, MarketPermissionResult)
        self.assertEqual(result.permission, MarketPermission.ALLOW)
        self.assertTrue(result.reasons)

    def test_deny_acumula_multiplas_razoes(self) -> None:
        """Multiplos bloqueios devem aparecer no resultado."""
        result = MarketPermissionEngine().evaluate(
            self._feature_snapshot(volatility_level="LOW"),
            self._regime(MarketRegime.RANGE),
            self._research_data(confidence=10.0),
        )

        self.assertEqual(result.permission, MarketPermission.DENY)
        self.assertEqual(len(result.reasons), 3)

    def _feature_snapshot(
        self,
        volatility_level: str = "MEDIUM",
    ) -> FeatureSnapshot:
        return FeatureSnapshot(
            momentum=10.0,
            average_range=20.0,
            highest_high=120.0,
            lowest_low=90.0,
            direction="UP",
            candles_count=3,
            trend_strength=0.8,
            volatility_level=volatility_level,
        )

    def _regime(
        self,
        regime: MarketRegime = MarketRegime.TREND,
    ) -> RegimeAnalysis:
        return RegimeAnalysis(
            regime=regime,
            confidence=0.8,
            description="Mercado favoravel.",
        )

    def _research_data(self, confidence: float = 60.0) -> ResearchData:
        return ResearchData(
            similar_scenarios=60,
            confidence=confidence,
            historical_score=confidence,
            average_momentum=10.0,
            average_trend_strength=0.8,
            history_strength="Historico forte",
            summary="Cenario com historico suficiente.",
        )


if __name__ == "__main__":
    unittest.main()
