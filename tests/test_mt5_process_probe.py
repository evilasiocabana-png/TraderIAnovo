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


if __name__ == "__main__":
    unittest.main()
