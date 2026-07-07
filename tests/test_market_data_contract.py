"""Testes do contrato oficial de dados de mercado."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from market.data.market_data_contract import MarketDataContract
from tests.architecture_test_utils import calls_from, imports_from, read_source


class MarketDataContractTest(unittest.TestCase):
    """Valida o DTO normalizado de candles de mercado."""

    def test_contract_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MarketDataContract))
        self.assertTrue(MarketDataContract.__dataclass_params__.frozen)

    def test_contract_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(MarketDataContract)]

        self.assertEqual(
            field_names,
            [
                "symbol",
                "timeframe",
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "is_valid",
                "metadata",
            ],
        )

    def test_contract_possui_type_hints_explicitos(self) -> None:
        annotations = MarketDataContract.__annotations__

        self.assertEqual(annotations["symbol"], "str")
        self.assertEqual(annotations["timeframe"], "str")
        self.assertEqual(annotations["timestamp"], "str")
        self.assertEqual(annotations["open"], "float")
        self.assertEqual(annotations["high"], "float")
        self.assertEqual(annotations["low"], "float")
        self.assertEqual(annotations["close"], "float")
        self.assertEqual(annotations["volume"], "float")
        self.assertEqual(annotations["is_valid"], "bool")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_contract_representa_candle_normalizado(self) -> None:
        candle = MarketDataContract(
            symbol="WDO",
            timeframe="1m",
            timestamp="2026-06-27T09:00:00-03:00",
            open=1000.0,
            high=1010.0,
            low=990.0,
            close=1005.0,
            volume=1200.0,
            is_valid=True,
            metadata={"source": "fixture"},
        )

        self.assertEqual(candle.symbol, "WDO")
        self.assertEqual(candle.timeframe, "1m")
        self.assertEqual(candle.close, 1005.0)
        self.assertTrue(candle.is_valid)
        self.assertEqual(candle.metadata["source"], "fixture")

    def test_contract_e_imutavel(self) -> None:
        candle = self._contract()

        with self.assertRaises(FrozenInstanceError):
            candle.close = 1001.0

    def test_contract_nao_implementa_calculo_ou_validacao(self) -> None:
        public_methods = [
            name for name in dir(MarketDataContract)
            if not name.startswith("_") and callable(getattr(MarketDataContract, name))
        ]

        self.assertEqual(public_methods, [])

    def test_contract_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("market/data/market_data_contract.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "market.feature_engine",
            "FeatureEngine",
            "alpha",
            "strategies",
            "core.decision_pipeline",
            "DecisionPipeline",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "open",
            "validate",
            "calculate",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_contract_nao_contem_logica_operacional_no_codigo_fonte(self) -> None:
        source = read_source(Path("market/data/market_data_contract.py"))
        forbidden_fragments = (
            "ReplayEngine",
            "FeatureEngine",
            "Alpha001",
            "DecisionPipeline",
            "ResearchPipeline",
            "Broker",
            "MT5",
            "profit",
            "drawdown",
            "win_rate",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def _contract(self) -> MarketDataContract:
        return MarketDataContract(
            symbol="WDO",
            timeframe="1m",
            timestamp="2026-06-27T09:00:00-03:00",
            open=1000.0,
            high=1010.0,
            low=990.0,
            close=1005.0,
            volume=1200.0,
            is_valid=True,
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
