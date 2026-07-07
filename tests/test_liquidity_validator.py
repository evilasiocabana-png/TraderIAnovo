"""Testes do validador de liquidez da Alpha 001."""

import unittest
from dataclasses import dataclass

from alpha.liquidity_validator import LiquidityResult, LiquidityValidator
from domain.contracts.market_snapshot import MarketSnapshot


class LiquidityValidatorTest(unittest.TestCase):
    """Valida volume minimo a partir do MarketSnapshot."""

    def test_aprova_liquidez_suficiente(self) -> None:
        """Volume igual ou maior que o minimo deve ser aprovado."""
        result = LiquidityValidator().validate(self._snapshot(1500.0), 1000.0)

        self.assertTrue(result.approved)
        self.assertEqual(result.reason, "liquidez suficiente")

    def test_rejeita_liquidez_insuficiente(self) -> None:
        """Volume abaixo do minimo deve ser rejeitado."""
        result = LiquidityValidator().validate(self._snapshot(500.0), 1000.0)

        self.assertFalse(result.approved)
        self.assertEqual(result.reason, "liquidez insuficiente")

    def test_rejeita_volume_inexistente(self) -> None:
        """Snapshot sem liquidez deve rejeitar por volume indisponivel."""
        result = LiquidityValidator().validate(EmptySnapshot(), 1000.0)

        self.assertFalse(result.approved)
        self.assertEqual(result.current_volume, 0.0)
        self.assertEqual(result.reason, "volume indisponivel")

    def test_valida_current_volume(self) -> None:
        """Resultado deve preservar o volume avaliado."""
        result = LiquidityValidator().validate(self._snapshot(1234.5), 1000.0)

        self.assertEqual(result.current_volume, 1234.5)

    def test_valida_minimum_volume(self) -> None:
        """Resultado deve preservar o minimo exigido."""
        result = LiquidityValidator().validate(self._snapshot(1234.5), 900.0)

        self.assertEqual(result.minimum_volume, 900.0)

    def test_valida_reason(self) -> None:
        """Reason deve explicar aprovacao, rejeicao ou ausencia de volume."""
        validator = LiquidityValidator()

        self.assertEqual(
            validator.validate(self._snapshot(1500.0), 1000.0).reason,
            "liquidez suficiente",
        )
        self.assertEqual(
            validator.validate(self._snapshot(500.0), 1000.0).reason,
            "liquidez insuficiente",
        )
        self.assertEqual(
            validator.validate(EmptySnapshot(), 1000.0).reason,
            "volume indisponivel",
        )

    def test_valida_retorno_liquidity_result(self) -> None:
        """Validator deve retornar LiquidityResult."""
        result = LiquidityValidator().validate(self._snapshot(1500.0), 1000.0)

        self.assertIsInstance(result, LiquidityResult)

    def _snapshot(self, liquidity: float) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-26 09:16",
            regime="TREND",
            volatility=30.0,
            liquidity=liquidity,
            trend_strength=0.8,
            market_dna_score=70.0,
        )


@dataclass(frozen=True)
class EmptySnapshot:
    """Objeto sem campo de liquidez para simular volume indisponivel."""

    symbol: str = "WDO"


if __name__ == "__main__":
    unittest.main()
