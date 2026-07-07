"""Testes do validador de regime da Alpha 001."""

import unittest

from alpha.regime_validator import RegimeResult, RegimeValidator
from domain.contracts.market_snapshot import MarketSnapshot


class RegimeValidatorTest(unittest.TestCase):
    """Valida permissao por regime de mercado."""

    def test_aprova_regime_trend(self) -> None:
        """Regime TREND deve ser aprovado."""
        result = RegimeValidator().validate(self._snapshot("TREND"))

        self.assertTrue(result.approved)
        self.assertEqual(result.regime, "TREND")

    def test_aprova_regime_breakout(self) -> None:
        """Regime BREAKOUT deve ser aprovado."""
        result = RegimeValidator().validate(self._snapshot("BREAKOUT"))

        self.assertTrue(result.approved)
        self.assertEqual(result.regime, "BREAKOUT")

    def test_rejeita_regime_range(self) -> None:
        """Regime RANGE deve ser rejeitado."""
        result = RegimeValidator().validate(self._snapshot("RANGE"))

        self.assertFalse(result.approved)
        self.assertEqual(result.regime, "RANGE")
        self.assertEqual(result.reason, "regime desfavoravel")

    def test_rejeita_regime_inexistente(self) -> None:
        """Regime ausente deve ser tratado como UNKNOWN."""
        result = RegimeValidator().validate(self._snapshot(""))

        self.assertFalse(result.approved)
        self.assertEqual(result.regime, "UNKNOWN")
        self.assertEqual(result.reason, "regime indisponivel")

    def test_valida_reason(self) -> None:
        """Reason deve explicar aprovacao ou rejeicao."""
        validator = RegimeValidator()

        self.assertEqual(
            validator.validate(self._snapshot("TREND")).reason,
            "regime favoravel",
        )
        self.assertEqual(
            validator.validate(self._snapshot("RANGE")).reason,
            "regime desfavoravel",
        )
        self.assertEqual(
            validator.validate(self._snapshot("")).reason,
            "regime indisponivel",
        )

    def test_valida_retorno_do_tipo_regime_result(self) -> None:
        """Validator deve retornar RegimeResult."""
        result = RegimeValidator().validate(self._snapshot("TREND"))

        self.assertIsInstance(result, RegimeResult)

    def _snapshot(self, regime: str) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-26 09:16",
            regime=regime,
            volatility=30.0,
            liquidity=1000.0,
            trend_strength=0.8,
            market_dna_score=70.0,
        )


if __name__ == "__main__":
    unittest.main()
