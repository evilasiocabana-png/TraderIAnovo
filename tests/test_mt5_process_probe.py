import subprocess
import unittest
from unittest.mock import Mock, patch

from core.mt5_process_probe import probe_mt5_initialize


class MT5ProcessProbeTests(unittest.TestCase):
    def test_probe_retorna_ok_quando_subprocesso_responde(self) -> None:
        process = Mock()
        process.communicate.return_value = ("OK (1, 'ok')", "")
        process.returncode = 0

        with patch("core.mt5_process_probe.subprocess.Popen", return_value=process):
            result = probe_mt5_initialize(0.1)

        self.assertTrue(result.ok)
        self.assertIn("OK", result.message)

    def test_probe_limpa_subprocesso_quando_timeout_estoura(self) -> None:
        process = Mock()
        process.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd="probe", timeout=0.1),
            ("", ""),
        ]
        process.returncode = None

        with patch("core.mt5_process_probe.subprocess.Popen", return_value=process):
            with patch("core.mt5_process_probe._terminate_process_tree") as terminate:
                result = probe_mt5_initialize(0.1)

        terminate.assert_called_once_with(process)
        self.assertFalse(result.ok)
        self.assertIn("Timeout na sonda MT5", result.message)

    def test_probe_encaminha_caminho_resolvido_do_terminal(self) -> None:
        process = Mock()
        process.communicate.return_value = ("OK", "")
        process.returncode = 0
        terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"

        with patch(
            "core.mt5_process_probe.resolve_mt5_terminal_path",
            return_value=terminal_path,
        ):
            with patch(
                "core.mt5_process_probe.subprocess.Popen",
                return_value=process,
            ) as popen:
                result = probe_mt5_initialize(0.1)

        self.assertTrue(result.ok)
        self.assertEqual(popen.call_args.args[0][-1], terminal_path)


if __name__ == "__main__":
    unittest.main()
