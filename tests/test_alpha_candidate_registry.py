"""Testes do registro de candidatas a Alpha."""

from dataclasses import dataclass
from pathlib import Path
import unittest

from research.alpha_factory.alpha_candidate_registry import AlphaCandidateRegistry
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AlphaCandidateRegistryTest(unittest.TestCase):
    """Valida registro em memoria de candidatas declarativas."""

    def test_register_e_get_por_candidate_id(self) -> None:
        registry = AlphaCandidateRegistry()
        candidate = _Candidate(
            candidate_id="cand-001",
            name="Alpha Candidate",
            status="DRAFT",
        )

        saved = registry.register(candidate)

        self.assertIs(saved, candidate)
        self.assertIs(registry.get("cand-001"), candidate)

    def test_register_aceita_dict_com_candidate_id(self) -> None:
        registry = AlphaCandidateRegistry()
        candidate = {"candidate_id": "cand-001", "status": "DRAFT"}

        registry.register(candidate)

        self.assertIs(registry.get("cand-001"), candidate)

    def test_register_aceita_id_como_identificador_alternativo(self) -> None:
        registry = AlphaCandidateRegistry()
        candidate = _LegacyCandidate(id="legacy-001", status="DRAFT")

        registry.register(candidate)

        self.assertIs(registry.get("legacy-001"), candidate)

    def test_unregister_remove_candidata_existente(self) -> None:
        registry = AlphaCandidateRegistry()
        registry.register(_Candidate("cand-001", "Alpha", "DRAFT"))

        removed = registry.unregister("cand-001")

        self.assertTrue(removed)
        self.assertIsNone(registry.get("cand-001"))

    def test_unregister_retorna_false_para_candidata_inexistente(self) -> None:
        self.assertFalse(AlphaCandidateRegistry().unregister("missing"))

    def test_list_retorna_candidatas_registradas(self) -> None:
        registry = AlphaCandidateRegistry()
        first = _Candidate("cand-001", "A", "DRAFT")
        second = _Candidate("cand-002", "B", "DRAFT")

        registry.register(first)
        registry.register(second)

        self.assertEqual(registry.list(), (first, second))

    def test_approve_for_research_atualiza_status_sem_mutar_dataclass(self) -> None:
        registry = AlphaCandidateRegistry()
        candidate = _Candidate("cand-001", "Alpha", "DRAFT")
        registry.register(candidate)

        approved = registry.approve_for_research("cand-001")

        self.assertIsNot(approved, candidate)
        self.assertEqual(candidate.status, "DRAFT")
        self.assertEqual(approved.status, "APPROVED_FOR_RESEARCH")
        self.assertIs(registry.get("cand-001"), approved)

    def test_reject_atualiza_status_de_dict_em_copia(self) -> None:
        registry = AlphaCandidateRegistry()
        candidate = {"candidate_id": "cand-001", "status": "DRAFT"}
        registry.register(candidate)

        rejected = registry.reject("cand-001")

        self.assertIsNot(rejected, candidate)
        self.assertEqual(candidate["status"], "DRAFT")
        self.assertEqual(rejected["status"], "REJECTED")
        self.assertIs(registry.get("cand-001"), rejected)

    def test_aprovacao_ou_rejeicao_retorna_none_quando_nao_existe(self) -> None:
        registry = AlphaCandidateRegistry()

        self.assertIsNone(registry.approve_for_research("missing"))
        self.assertIsNone(registry.reject("missing"))

    def test_register_rejeita_candidata_sem_identificador(self) -> None:
        with self.assertRaises(ValueError):
            AlphaCandidateRegistry().register(object())

    def test_registry_nao_executa_experimentos_ou_cria_estrategias(self) -> None:
        source = read_source(
            Path("research/alpha_factory/alpha_candidate_registry.py")
        )
        forbidden_fragments = (
            "Alpha001Experiment",
            "Alpha001IORBStrategy(",
            "Strategy(",
            ".run(",
            ".calculate(",
            ".compare(",
            ".validate(",
            "generate_signal",
            "AlphaRegistry",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_registry_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha_factory/alpha_candidate_registry.py")
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
            "research.portfolio.alpha_registry",
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


@dataclass(frozen=True)
class _Candidate:
    """Candidata declarativa de teste."""

    candidate_id: str
    name: str
    status: str


@dataclass(frozen=True)
class _LegacyCandidate:
    """Candidata com identificador alternativo."""

    id: str
    status: str


if __name__ == "__main__":
    unittest.main()
