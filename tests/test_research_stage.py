"""Testes dos modelos de estagio do Research Pipeline."""

from dataclasses import FrozenInstanceError, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
import unittest

from research.research_stage import ResearchStage, ResearchStageResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchStageTest(unittest.TestCase):
    """Valida estados oficiais e resultado de estagio."""

    def test_research_stage_e_enum(self) -> None:
        self.assertTrue(issubclass(ResearchStage, Enum))

    def test_research_stage_define_estados_oficiais(self) -> None:
        self.assertEqual(
            [stage.value for stage in ResearchStage],
            [
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "SKIPPED",
            ],
        )

    def test_stage_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ResearchStageResult))
        self.assertTrue(ResearchStageResult.__dataclass_params__.frozen)

    def test_stage_result_contem_campos_minimos(self) -> None:
        started_at = datetime(2026, 6, 27, 20, 30, 0)
        finished_at = datetime(2026, 6, 27, 20, 30, 1)
        result = ResearchStageResult(
            stage=ResearchStage.COMPLETED,
            started_at=started_at,
            finished_at=finished_at,
            duration=1.0,
            success=True,
            message="Etapa concluida.",
        )

        self.assertEqual(result.stage, ResearchStage.COMPLETED)
        self.assertEqual(result.started_at, started_at)
        self.assertEqual(result.finished_at, finished_at)
        self.assertEqual(result.duration, 1.0)
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Etapa concluida.")

    def test_stage_result_permite_estado_pendente_sem_datas(self) -> None:
        result = ResearchStageResult(
            stage=ResearchStage.PENDING,
            started_at=None,
            finished_at=None,
            duration=0.0,
            success=False,
            message="Etapa pendente.",
        )

        self.assertIsNone(result.started_at)
        self.assertIsNone(result.finished_at)
        self.assertFalse(result.success)

    def test_stage_result_e_imutavel(self) -> None:
        result = ResearchStageResult(
            stage=ResearchStage.RUNNING,
            started_at=None,
            finished_at=None,
            duration=0.0,
            success=False,
            message="Em execucao.",
        )

        with self.assertRaises(FrozenInstanceError):
            result.stage = ResearchStage.FAILED

    def test_modelo_nao_executa_logica_nem_importa_camadas(self) -> None:
        path = Path("research/research_stage.py")
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
            "broker",
            "mt5",
            "MetaTrader5",
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

    def test_codigo_fonte_nao_realiza_execucao_ou_calculos(self) -> None:
        source = read_source(Path("research/research_stage.py"))
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
