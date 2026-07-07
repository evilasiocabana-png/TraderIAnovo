"""Testes do contrato oficial de benchmark entre Alphas."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaBenchmarkProfileTest(unittest.TestCase):
    """Valida contrato puro para benchmarks entre Alphas."""

    def test_profile_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaBenchmarkProfile))
        self.assertTrue(AlphaBenchmarkProfile.__dataclass_params__.frozen)

    def test_profile_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(AlphaBenchmarkProfile)]

        self.assertEqual(
            field_names,
            [
                "benchmark_id",
                "alpha_a",
                "alpha_b",
                "experiment_ids",
                "campaign_ids",
                "comparison_period",
                "metrics",
                "created_at",
                "metadata",
            ],
        )

    def test_profile_possui_type_hints_explicitos(self) -> None:
        annotations = AlphaBenchmarkProfile.__annotations__

        self.assertEqual(annotations["benchmark_id"], "str")
        self.assertEqual(annotations["alpha_a"], "str")
        self.assertEqual(annotations["alpha_b"], "str")
        self.assertEqual(annotations["experiment_ids"], "tuple[str, ...]")
        self.assertEqual(annotations["campaign_ids"], "tuple[str, ...]")
        self.assertEqual(annotations["comparison_period"], "str")
        self.assertEqual(annotations["metrics"], "tuple[str, ...]")
        self.assertEqual(annotations["created_at"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_profile_representa_benchmark_entre_duas_alphas(self) -> None:
        profile = self._profile()

        self.assertEqual(profile.benchmark_id, "benchmark-alpha001-alpha301")
        self.assertEqual(profile.alpha_a, "Alpha001")
        self.assertEqual(profile.alpha_b, "Alpha301")
        self.assertEqual(profile.experiment_ids, ("exp-001", "exp-301"))
        self.assertEqual(profile.campaign_ids, ("campaign-001", "campaign-301"))
        self.assertEqual(profile.comparison_period, "2026-01")
        self.assertEqual(profile.metrics, ("net_profit", "drawdown", "win_rate"))
        self.assertEqual(profile.created_at, "2026-06-28T05:05:00-03:00")
        self.assertEqual(profile.metadata["source"], "unit-test")

    def test_profile_preserva_metadata_recebido(self) -> None:
        metadata = {"source": "unit-test"}

        profile = AlphaBenchmarkProfile(
            benchmark_id="benchmark-alpha001-alpha301",
            alpha_a="Alpha001",
            alpha_b="Alpha301",
            experiment_ids=("exp-001", "exp-301"),
            campaign_ids=("campaign-001", "campaign-301"),
            comparison_period="2026-01",
            metrics=("net_profit", "drawdown", "win_rate"),
            created_at="2026-06-28T05:05:00-03:00",
            metadata=metadata,
        )

        self.assertIs(profile.metadata, metadata)

    def test_profile_e_imutavel(self) -> None:
        profile = self._profile()

        with self.assertRaises(FrozenInstanceError):
            profile.alpha_a = "Alpha002"

    def test_profile_nao_executa_comparacoes_ou_metricas(self) -> None:
        source = read_source(Path("research/benchmark/alpha_benchmark_profile.py"))
        forbidden_fragments = (
            "def ",
            "sum(",
            "max(",
            "min(",
            "round(",
            "ResearchPipeline",
            "PortfolioResearch",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".calculate(",
            ".compare(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_profile_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/benchmark/alpha_benchmark_profile.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.portfolio",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "database",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "calculate",
            "compare",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _profile(self) -> AlphaBenchmarkProfile:
        return AlphaBenchmarkProfile(
            benchmark_id="benchmark-alpha001-alpha301",
            alpha_a="Alpha001",
            alpha_b="Alpha301",
            experiment_ids=("exp-001", "exp-301"),
            campaign_ids=("campaign-001", "campaign-301"),
            comparison_period="2026-01",
            metrics=("net_profit", "drawdown", "win_rate"),
            created_at="2026-06-28T05:05:00-03:00",
            metadata={"source": "unit-test"},
        )


if __name__ == "__main__":
    unittest.main()
