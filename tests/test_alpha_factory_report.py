"""Testes do relatorio consolidado da Alpha Factory."""

from dataclasses import FrozenInstanceError, dataclass, is_dataclass
from datetime import datetime
from pathlib import Path
import unittest

from research.alpha_factory.alpha_candidate_registry import AlphaCandidateRegistry
from research.alpha_factory.alpha_factory_report import AlphaFactoryReport
from research.alpha_factory.alpha_hypothesis import AlphaHypothesis
from research.alpha_factory.alpha_playbook_template import AlphaPlaybookTemplate
from research.alpha_factory.alpha_readiness_validator import AlphaReadinessResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaFactoryReportTest(unittest.TestCase):
    """Valida consolidacao pura de informacoes da Alpha Factory."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AlphaFactoryReport))
        self.assertTrue(AlphaFactoryReport.__dataclass_params__.frozen)

    def test_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.hypothesis, AlphaHypothesis)
        self.assertIsInstance(report.playbook, AlphaPlaybookTemplate)
        self.assertIsInstance(report.readiness_result, AlphaReadinessResult)
        self.assertIsInstance(report.candidate_registry, AlphaCandidateRegistry)

    def test_apresenta_campos_consolidados(self) -> None:
        report = self._report()

        self.assertEqual(report.hypothesis_id, "hyp-001")
        self.assertEqual(report.alpha_name, "Alpha Candidate")
        self.assertEqual(report.version, 1)
        self.assertEqual(report.readiness_status, "APPROVED")
        self.assertEqual(report.validation_messages, ())
        self.assertEqual(report.candidate_status, "APPROVED_FOR_RESEARCH")
        self.assertEqual(report.created_at, datetime(2026, 6, 27, 21, 50, 0))

    def test_preserva_referencias_recebidas(self) -> None:
        hypothesis = self._hypothesis()
        playbook = self._playbook()
        readiness = AlphaReadinessResult(
            approved=True,
            validation_messages=(),
        )
        registry = AlphaCandidateRegistry()

        report = AlphaFactoryReport(
            hypothesis=hypothesis,
            playbook=playbook,
            readiness_result=readiness,
            candidate_registry=registry,
            hypothesis_id="hyp-001",
            alpha_name="Alpha Candidate",
            version=1,
            readiness_status="APPROVED",
            validation_messages=(),
            candidate_status="APPROVED_FOR_RESEARCH",
            created_at=datetime(2026, 6, 27, 21, 50, 0),
        )

        self.assertIs(report.hypothesis, hypothesis)
        self.assertIs(report.playbook, playbook)
        self.assertIs(report.readiness_result, readiness)
        self.assertIs(report.candidate_registry, registry)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.candidate_status = "REJECTED"

    def test_report_nao_realiza_calculos_ou_execucoes(self) -> None:
        source = read_source(
            Path("research/alpha_factory/alpha_factory_report.py")
        )
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
            "AlphaReadinessValidator",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_nao_gera_interfaces_ou_persistencia(self) -> None:
        source = read_source(
            Path("research/alpha_factory/alpha_factory_report.py")
        )
        forbidden_fragments = (
            "dashboard",
            "streamlit",
            "html",
            "pdf",
            "open(",
            "write",
            "json",
            "csv",
            "export",
            "database",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_factory_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
            "alpha.alpha001_config",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "run",
            "calculate",
            "generate_signal",
            "open",
            "write",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> AlphaFactoryReport:
        return AlphaFactoryReport(
            hypothesis=self._hypothesis(),
            playbook=self._playbook(),
            readiness_result=AlphaReadinessResult(
                approved=True,
                validation_messages=(),
            ),
            candidate_registry=self._registry(),
            hypothesis_id="hyp-001",
            alpha_name="Alpha Candidate",
            version=1,
            readiness_status="APPROVED",
            validation_messages=(),
            candidate_status="APPROVED_FOR_RESEARCH",
            created_at=datetime(2026, 6, 27, 21, 50, 0),
        )

    def _hypothesis(self) -> AlphaHypothesis:
        return AlphaHypothesis(
            hypothesis_id="hyp-001",
            alpha_name="Alpha Candidate",
            version=1,
            title="Rompimento controlado",
            description="Hipotese de pesquisa.",
            market="WDO",
            timeframe="1m",
            context="Abertura do mercado.",
            trigger="Rompimento da maxima inicial.",
            expected_behavior="Movimento direcional.",
            risk_assumptions=("Stops limitados.",),
            validation_plan="Validar em pesquisa.",
            author="Research",
            created_at=datetime(2026, 6, 27, 21, 45, 0),
            status="DRAFT",
        )

    def _playbook(self) -> AlphaPlaybookTemplate:
        return AlphaPlaybookTemplate(
            hypothesis="Hipotese quantitativa.",
            objective="Documentar Alpha candidata.",
            allowed_markets=("WDO",),
            forbidden_markets=("WIN",),
            context="Contexto simulado.",
            trigger="Gatilho de entrada.",
            filters=("Filtro de volume.",),
            entry_rules=("Entrada apos confirmacao.",),
            exit_rules=("Saida por regra definida.",),
            risk_management=("Stop obrigatorio.",),
            replay_validation="Validar em ambiente simulado.",
            research_validation="Validar em pesquisa.",
            rejection_criteria=("Amostra insuficiente.",),
            acceptance_criteria=("Robustez estatistica.",),
        )

    def _registry(self) -> AlphaCandidateRegistry:
        registry = AlphaCandidateRegistry()
        registry.register(
            _Candidate(
                candidate_id="hyp-001",
                status="APPROVED_FOR_RESEARCH",
            )
        )
        return registry


@dataclass(frozen=True)
class _Candidate:
    """Candidata declarativa usada nos testes."""

    candidate_id: str
    status: str


if __name__ == "__main__":
    unittest.main()
