"""Testes do painel de status da Alpha 001 no dashboard."""

import ast
import unittest
from pathlib import Path

from application.dashboard_service import DashboardService


class DashboardAlpha001StatusTest(unittest.TestCase):
    """Valida exposicao visual segura do status da Alpha 001."""

    def test_dashboard_service_expoe_status_da_alpha001(self) -> None:
        """DashboardService deve retornar o status da Alpha 001."""
        status = DashboardService().get_alpha001_status()

        self.assertEqual(status.strategy_name, "Alpha 001 - IORB")
        self.assertEqual(status.status, "pesquisa/simulação")
        self.assertTrue(status.research_lab_integrated)
        self.assertTrue(status.benchmark_integrated)

    def test_status_informa_operacao_real_nao_autorizada(self) -> None:
        """Operacao real deve permanecer bloqueada."""
        status = DashboardService().get_alpha001_status()

        self.assertFalse(status.real_trading_authorized)

    def test_status_informa_corretora_mt5_nao_integrado(self) -> None:
        """Corretora e MT5 devem permanecer nao integrados."""
        status = DashboardService().get_alpha001_status()

        self.assertFalse(status.broker_mt5_integrated)

    def test_status_informa_ia_nao_autorizada(self) -> None:
        """IA deve permanecer nao autorizada."""
        status = DashboardService().get_alpha001_status()

        self.assertFalse(status.ai_authorized)

    def test_status_informa_validacao_estatistica_pendente(self) -> None:
        """Status deve apontar dependencia do Research Lab."""
        status = DashboardService().get_alpha001_status()

        self.assertIn("Research Lab", status.statistical_validation_status)

    def test_dashboard_data_inclui_status_da_alpha001(self) -> None:
        """DashboardData deve transportar o status da Alpha 001."""
        data = DashboardService().get_dashboard_data()

        self.assertEqual(data.alpha001_status.strategy_name, "Alpha 001 - IORB")

    def test_dashboard_nao_acessa_strategy_diretamente(self) -> None:
        """Dashboard deve depender apenas de DashboardService."""
        imports = self._dashboard_imports()

        self.assertEqual(
            imports,
            {
                "datetime",
                "inspect",
                "os",
                "time",
                "streamlit",
                "application.dashboard_view_model",
            },
        )

    def _dashboard_imports(self) -> set[str]:
        tree = ast.parse(Path("dashboard_app.py").read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module != "application.dashboard_service":
                    imports.add(node.module)
        return imports


if __name__ == "__main__":
    unittest.main()
