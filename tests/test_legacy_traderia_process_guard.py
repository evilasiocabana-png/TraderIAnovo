"""Testes do guarda de processo legado TraderIA."""

import unittest
from unittest import mock

from core import legacy_traderia_process_guard as guard


class LegacyTraderIAProcessGuardTest(unittest.TestCase):
    def test_identifica_apenas_streamlit_do_traderia_wdo(self) -> None:
        self.assertTrue(
            guard._is_legacy_traderia_command(
                "C:\\Users\\evcab\\OneDrive\\Documentos\\TraderIA_WDO\\Python\\bin\\python.exe "
                "-m streamlit run dashboard_app.py --server.port 8530"
            )
        )
        self.assertFalse(
            guard._is_legacy_traderia_command(
                "C:\\Users\\evcab\\OneDrive\\Documentos\\traderiaianovo\\Python\\bin\\python.exe "
                "-m streamlit run dashboard_app.py --server.port 8532"
            )
        )
        self.assertFalse(guard._is_legacy_traderia_command("python outro_app.py"))

    def test_find_legacy_filtra_resultados_por_command_line(self) -> None:
        rows = [
            {
                "Pid": 10,
                "Port": 8530,
                "CommandLine": (
                    "C:\\Users\\evcab\\OneDrive\\Documentos\\TraderIA_WDO\\Python\\bin\\python.exe "
                    "-m streamlit run dashboard_app.py"
                ),
            },
            {
                "Pid": 11,
                "Port": 8532,
                "CommandLine": (
                    "C:\\Users\\evcab\\OneDrive\\Documentos\\traderiaianovo\\Python\\bin\\python.exe "
                    "-m streamlit run dashboard_app.py"
                ),
            },
        ]

        with mock.patch.object(guard, "_run_powershell_json", return_value=rows):
            processes = guard.find_legacy_traderia_processes((8530, 8532))

        self.assertEqual(len(processes), 1)
        self.assertEqual(processes[0].pid, 10)
        self.assertEqual(processes[0].port, 8530)

    def test_cleanup_respeita_flag_desligada(self) -> None:
        with mock.patch.dict(
            guard.os.environ,
            {"TRADERIA_LEGACY_PROCESS_GUARD_ENABLED": "0"},
        ):
            with mock.patch.object(guard, "find_legacy_traderia_processes") as find:
                self.assertEqual(guard.cleanup_legacy_traderia_processes(), [])

        find.assert_not_called()


if __name__ == "__main__":
    unittest.main()
