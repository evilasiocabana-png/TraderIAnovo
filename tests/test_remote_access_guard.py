from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.remote_access_guard import (
    configured_remote_hosts,
    is_remote_request,
    request_host,
    verify_password,
)


class RemoteAccessGuardTest(unittest.TestCase):
    def test_localhost_does_not_require_remote_authentication(self) -> None:
        self.assertFalse(is_remote_request({"Host": "localhost:8532"}))
        self.assertFalse(is_remote_request({"Host": "127.0.0.1:8532"}))

    def test_public_hostname_requires_remote_authentication(self) -> None:
        headers = {"X-Forwarded-Host": "traderianovo.psiquiatriaemfoco.com"}
        self.assertTrue(is_remote_request(headers))

    def test_forwarded_host_has_priority_and_ignores_port(self) -> None:
        headers = {
            "Host": "localhost:8532",
            "X-Forwarded-Host": "traderianovo.psiquiatriaemfoco.com:443",
        }
        self.assertEqual(
            request_host(headers),
            "traderianovo.psiquiatriaemfoco.com",
        )

    def test_remote_hosts_can_be_configured(self) -> None:
        with patch.dict(os.environ, {"TRADERIA_REMOTE_ACCESS_HOSTS": "a.test, b.test"}):
            self.assertEqual(configured_remote_hosts(), frozenset({"a.test", "b.test"}))

    def test_password_is_verified_against_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            password_path = Path(directory) / "password.sha256"
            digest = hashlib.sha256(b"segredo-forte").hexdigest()
            password_path.write_text(f"sha256:{digest}", encoding="ascii")
            self.assertTrue(verify_password("segredo-forte", password_path))
            self.assertFalse(verify_password("senha-errada", password_path))

    def test_missing_or_invalid_password_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            password_path = Path(directory) / "missing.sha256"
            self.assertFalse(verify_password("qualquer", password_path))
            password_path.write_text("texto-puro", encoding="ascii")
            self.assertFalse(verify_password("texto-puro", password_path))


if __name__ == "__main__":
    unittest.main()
