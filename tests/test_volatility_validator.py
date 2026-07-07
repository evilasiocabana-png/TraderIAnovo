"""Testes do validador de volatilidade da Alpha 001."""

import unittest

from alpha.opening_range_engine import OpeningRange
from alpha.volatility_validator import VolatilityResult, VolatilityValidator


class VolatilityValidatorTest(unittest.TestCase):
    """Valida o tamanho minimo da Opening Range."""

    def test_aprova_volatilidade_suficiente(self) -> None:
        """Range igual ou maior que o minimo deve ser aprovado."""
        result = VolatilityValidator().validate(self._opening_range(25.0), 20.0)

        self.assertTrue(result.approved)
        self.assertEqual(result.reason, "volatilidade suficiente")

    def test_rejeita_volatilidade_insuficiente(self) -> None:
        """Range menor que o minimo deve ser rejeitado."""
        result = VolatilityValidator().validate(self._opening_range(15.0), 20.0)

        self.assertFalse(result.approved)
        self.assertEqual(result.reason, "volatilidade insuficiente")

    def test_rejeita_opening_range_incompleta(self) -> None:
        """Faixa incompleta deve rejeitar volatilidade."""
        result = VolatilityValidator().validate(
            self._opening_range(25.0, is_complete=False),
            20.0,
        )

        self.assertFalse(result.approved)
        self.assertEqual(result.range_size, 0.0)
        self.assertEqual(result.reason, "opening range incompleta")

    def test_valida_range_size(self) -> None:
        """Resultado deve preservar o range_size avaliado."""
        result = VolatilityValidator().validate(self._opening_range(30.5), 20.0)

        self.assertEqual(result.range_size, 30.5)

    def test_valida_minimum_required(self) -> None:
        """Resultado deve preservar o minimo exigido."""
        result = VolatilityValidator().validate(self._opening_range(30.5), 22.5)

        self.assertEqual(result.minimum_required, 22.5)

    def test_valida_reason(self) -> None:
        """Reason deve explicar aprovacao, rejeicao ou incompletude."""
        validator = VolatilityValidator()

        self.assertEqual(
            validator.validate(self._opening_range(25.0), 20.0).reason,
            "volatilidade suficiente",
        )
        self.assertEqual(
            validator.validate(self._opening_range(15.0), 20.0).reason,
            "volatilidade insuficiente",
        )
        self.assertEqual(
            validator.validate(self._opening_range(25.0, False), 20.0).reason,
            "opening range incompleta",
        )

    def test_valida_retorno_volatility_result(self) -> None:
        """Validator deve retornar VolatilityResult."""
        result = VolatilityValidator().validate(self._opening_range(25.0), 20.0)

        self.assertIsInstance(result, VolatilityResult)

    def _opening_range(
        self,
        range_size: float,
        is_complete: bool = True,
    ) -> OpeningRange:
        high = 100.0 + range_size
        return OpeningRange(
            start_time="09:00",
            end_time="09:15",
            high=high,
            low=100.0,
            range_size=range_size,
            is_complete=is_complete,
        )


if __name__ == "__main__":
    unittest.main()
