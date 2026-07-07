"""Testes das politicas de governanca arquitetural do CTO."""

from pathlib import Path
import unittest


class CtoGovernanceDocumentationTest(unittest.TestCase):
    """Garante que as regras permanentes estao documentadas."""

    DOCUMENTS = (
        Path("TRADERIA_GPT_INSTRUCTIONS.md"),
        Path("TRADERIA_ARCHITECTURE_BIBLE.md"),
        Path("ARCHITECTURE_RULES.md"),
        Path("README.md"),
    )

    def test_documentacao_contem_politicas_obrigatorias(self) -> None:
        content = self._documentation_text()

        required_terms = [
            "VALIDACAO FUNCIONAL OBRIGATORIA",
            "CORRECAO EM CASCATA",
            "PROIBICAO DE WORKAROUNDS",
            "ANALISE DE IMPACTO OBRIGATORIA",
            "DashboardService",
            "ReplayService",
            "ResearchLabService",
            "AttributeError",
            "ImportError",
            "TypeError",
            "End-to-End Validation",
            "Unit Tests",
            "Integration Tests",
            "Streamlit AppTest",
        ]

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, content)

    def test_quatro_niveis_oficiais_de_validacao_estao_documentados(
        self,
    ) -> None:
        content = self._documentation_text()

        levels = [
            "Unit Tests",
            "Integration Tests",
            "Streamlit AppTest",
            "End-to-End Validation",
        ]

        self.assertTrue(
            all(level in content for level in levels),
            "Os quatro niveis oficiais de validacao devem estar documentados.",
        )

    def test_politica_de_validacao_por_risco_esta_documentada(self) -> None:
        content = self._documentation_text()

        required_terms = [
            "VALIDAÇÃO POR RISCO",
            "BAIXO RISCO",
            "ALTO RISCO",
            "python -m streamlit run dashboard_app.py",
            "Se houver dúvida",
            "análise de impacto",
            "API pública",
            "st.session_state",
        ]

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, content)

    def _documentation_text(self) -> str:
        return "\n".join(
            path.read_text(encoding="utf-8")
            for path in self.DOCUMENTS
        )


if __name__ == "__main__":
    unittest.main()
