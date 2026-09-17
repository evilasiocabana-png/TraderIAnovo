"""Explicit account selection; never infer authorization from a terminal login."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class MT5ExecutionAccount:
    mode: str = "DEMO"
    login: str = ""
    server: str = ""
    real_enabled: bool = False
    revision: str = ""
    terminal_path: str = ""

    @classmethod
    def from_env(cls) -> "MT5ExecutionAccount":
        return cls(
            mode=os.environ.get("TRADERIA_EXECUTION_ACCOUNT_MODE", "DEMO").strip().upper(),
            login=os.environ.get("TRADERIA_REAL_ACCOUNT_LOGIN", "").strip(),
            server=os.environ.get("TRADERIA_REAL_ACCOUNT_SERVER", "").strip(),
            real_enabled=os.environ.get("TRADERIA_REAL_EXECUTION_ENABLED") == "1",
            revision=os.environ.get("TRADERIA_EXECUTION_ACCOUNT_REVISION", ""),
            terminal_path=os.environ.get("MT5_PATH", "").strip(),
        )

    @property
    def configured(self) -> bool:
        if self.mode == "DEMO":
            return os.environ.get("TRADERIA_DEMO_EXECUTION_ENABLED") == "1"
        return (
            self.mode == "REAL" and self.real_enabled
            and self.login.isdecimal() and int(self.login) > 0 and bool(self.server)
        )

    def rejection(self, mt5: object, account: object) -> str | None:
        if self.terminal_path:
            try:
                terminal = mt5.terminal_info()
                actual_path = getattr(terminal, "path", "")
                expected_path = os.path.dirname(os.path.abspath(self.terminal_path))
                if not actual_path or os.path.normcase(os.path.abspath(actual_path)) != os.path.normcase(expected_path):
                    return "Terminal MT5 conectado diverge do caminho configurado."
            except Exception:
                return "Identidade do terminal MT5 indisponivel."
        if self.mode not in {"DEMO", "REAL"}:
            return "Modo de conta MT5 invalido."
        expected = getattr(mt5, "ACCOUNT_TRADE_MODE_" + self.mode, None)
        actual = getattr(account, "trade_mode", None)
        if expected is None or actual is None or actual != expected:
            return "Execucao bloqueada: conta MT5 nao e " + self.mode.lower() + "."
        if self.mode == "REAL":
            if not self.configured:
                return "Conta Real exige habilitacao, login e servidor explicitos."
            if str(getattr(account, "login", "")) != self.login or getattr(account, "server", "") != self.server:
                return "Conta ou servidor Real diverge da configuracao autorizada."
            if not getattr(account, "trade_allowed", False) or not getattr(account, "trade_expert", False):
                return "Conta Real nao permite negociacao automatica."
        if self.mode == "DEMO":
            login = os.environ.get("TRADERIA_DEMO_ACCOUNT_LOGIN", "")
            server = os.environ.get("TRADERIA_DEMO_ACCOUNT_SERVER", "")
            if login and str(getattr(account, "login", "")) != login:
                return "Conta Demo diverge da configuracao autorizada."
            if server and getattr(account, "server", "") != server:
                return "Servidor Demo diverge da configuracao autorizada."
        return None


def execution_enabled() -> bool:
    return MT5ExecutionAccount.from_env().configured


def real_execution_enabled() -> bool:
    policy = MT5ExecutionAccount.from_env()
    return policy.mode == "REAL" and policy.configured
