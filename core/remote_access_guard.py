"""Protecao leve para o acesso remoto ao dashboard."""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
from typing import Mapping


DEFAULT_REMOTE_HOST = "traderianovo.psiquiatriaemfoco.com"
REMOTE_HOSTS_ENV = "TRADERIA_REMOTE_ACCESS_HOSTS"
PASSWORD_FILE_ENV = "TRADERIA_REMOTE_ACCESS_PASSWORD_FILE"


def default_password_file() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "TraderIANovo" / "remote-access-password.sha256"
    return Path.home() / ".traderianovo" / "remote-access-password.sha256"


def configured_remote_hosts() -> frozenset[str]:
    raw = os.getenv(REMOTE_HOSTS_ENV, DEFAULT_REMOTE_HOST)
    return frozenset(
        normalized
        for value in raw.split(",")
        if (normalized := _normalize_host(value))
    )


def request_host(headers: Mapping[str, object] | None) -> str:
    if not headers:
        return ""
    normalized_headers = {str(key).lower(): value for key, value in headers.items()}
    forwarded = str(normalized_headers.get("x-forwarded-host", "") or "")
    host = forwarded.split(",", 1)[0] if forwarded else str(
        normalized_headers.get("host", "") or ""
    )
    return _normalize_host(host)


def is_remote_request(headers: Mapping[str, object] | None) -> bool:
    return request_host(headers) in configured_remote_hosts()


def password_file() -> Path:
    configured = os.getenv(PASSWORD_FILE_ENV, "").strip()
    return Path(configured) if configured else default_password_file()


def password_is_configured(path: Path | None = None) -> bool:
    target = path or password_file()
    try:
        return bool(target.read_text(encoding="ascii").strip())
    except OSError:
        return False


def verify_password(candidate: str, path: Path | None = None) -> bool:
    if not candidate:
        return False
    target = path or password_file()
    try:
        stored = target.read_text(encoding="ascii").strip()
    except OSError:
        return False
    if not stored.startswith("sha256:"):
        return False
    candidate_digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    return hmac.compare_digest(stored.removeprefix("sha256:"), candidate_digest)


def _normalize_host(value: object) -> str:
    host = str(value or "").strip().lower().rstrip(".")
    if host.startswith("[") and "]" in host:
        return host[1 : host.index("]")]
    return host.split(":", 1)[0]
