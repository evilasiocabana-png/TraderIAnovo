import importlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ArchitectureBoundariesTest(unittest.TestCase):
    def test_dashboard_imports_application_dashboard_service(self) -> None:
        source = (ROOT / "dashboard_app.py").read_text(encoding="utf-8")

        self.assertIn("from application.dashboard_service import DashboardService", source)

    def test_dashboard_does_not_import_infrastructure(self) -> None:
        source = (ROOT / "dashboard_app.py").read_text(encoding="utf-8")

        self.assertNotIn("infrastructure", source)

    def test_no_python_file_uses_forbidden_mt5_sender(self) -> None:
        forbidden = "order" + "_send"

        for path in ROOT.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, source, msg=str(path))

    def test_mt5_readonly_provider_has_no_operational_methods(self) -> None:
        module = importlib.import_module("infrastructure.mt5.mt5_readonly_provider")
        provider = module.MT5ReadonlyProvider()
        forbidden_methods = [
            "order" + "_send",
            "send" + "_order",
            "buy",
            "sell",
            "close" + "_position",
            "modify" + "_order",
        ]

        for method_name in forbidden_methods:
            self.assertFalse(hasattr(provider, method_name), msg=method_name)
