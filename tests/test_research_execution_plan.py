"""Testes do plano declarativo do Research Pipeline."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.research_execution_plan import (
    ResearchExecutionPlan,
    ResearchExecutionStep,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchExecutionPlanTest(unittest.TestCase):
    """Valida representacao declarativa da sequencia oficial."""

    def test_contratos_sao_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ResearchExecutionStep))
        self.assertTrue(ResearchExecutionStep.__dataclass_params__.frozen)
        self.assertTrue(is_dataclass(ResearchExecutionPlan))
        self.assertTrue(ResearchExecutionPlan.__dataclass_params__.frozen)

    def test_step_contem_campos_obrigatorios(self) -> None:
        step = ResearchExecutionStep(
            name="Alpha001Experiment",
            order=1,
            description="Executa o experimento.",
            enabled=True,
            required=True,
        )

        self.assertEqual(step.name, "Alpha001Experiment")
        self.assertEqual(step.order, 1)
        self.assertEqual(step.description, "Executa o experimento.")
        self.assertTrue(step.enabled)
        self.assertTrue(step.required)

    def test_plano_representa_sequencia_oficial(self) -> None:
        plan = ResearchExecutionPlan()

        self.assertEqual(
            [step.name for step in plan.steps],
            [
                "Alpha001Experiment",
                "Alpha001MetricsEngine",
                "Alpha001ProfitEngine",
                "Alpha001DrawdownEngine",
                "Alpha001WinRateEngine",
                "Alpha001ProfitFactorEngine",
                "Alpha001ExpectancyEngine",
                "Alpha001BenchmarkComparator",
                "Alpha001ResearchReport",
                "Alpha001ResearchValidator",
                "Alpha001ResearchAdvisor",
            ],
        )
        self.assertEqual(
            [step.order for step in plan.steps],
            list(range(1, 12)),
        )

    def test_todas_as_etapas_padrao_sao_habilitadas_e_obrigatorias(self) -> None:
        plan = ResearchExecutionPlan()

        self.assertTrue(all(step.enabled for step in plan.steps))
        self.assertTrue(all(step.required for step in plan.steps))

    def test_plano_aceita_sequencia_customizada_sem_executar(self) -> None:
        step = ResearchExecutionStep(
            name="CustomStep",
            order=1,
            description="Etapa declarativa customizada.",
            enabled=False,
            required=False,
        )
        plan = ResearchExecutionPlan(steps=(step,))

        self.assertEqual(plan.steps, (step,))

    def test_plano_e_steps_sao_imutaveis(self) -> None:
        step = ResearchExecutionPlan().steps[0]
        plan = ResearchExecutionPlan()

        with self.assertRaises(FrozenInstanceError):
            step.enabled = False
        with self.assertRaises(FrozenInstanceError):
            plan.steps = ()

    def test_plano_nao_executa_etapas_nem_importa_componentes(self) -> None:
        path = Path("research/research_execution_plan.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.alpha001_experiment",
            "research.alpha001_metrics_engine",
            "research.alpha001_profit_engine",
            "research.alpha001_drawdown_engine",
            "research.alpha001_winrate_engine",
            "research.alpha001_profit_factor_engine",
            "research.alpha001_expectancy_engine",
            "research.alpha001_benchmark_comparator",
            "research.alpha001_research_report",
            "research.alpha001_research_validator",
            "research.alpha001_research_advisor",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "compare",
            "validate",
            "recommend",
            "open",
            "write",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_codigo_fonte_nao_realiza_calculos(self) -> None:
        source = read_source(Path("research/research_execution_plan.py"))
        forbidden_fragments = (
            ".run(",
            ".calculate(",
            ".compare(",
            ".validate(",
            ".recommend(",
            "sum(",
            "max(",
            "min(",
            " / ",
            " * ",
            " + ",
            " - ",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])


if __name__ == "__main__":
    unittest.main()
