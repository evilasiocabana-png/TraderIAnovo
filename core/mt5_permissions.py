"""Read-only, fail-closed permission diagnostics for the connected MT5."""


def read_permissions(mt5: object) -> dict[str, bool | None]:
    def read(name):
        try:
            return getattr(mt5, name)()
        except Exception:
            return None

    terminal, account = read("terminal_info"), read("account_info")
    return {
        "connected": getattr(terminal, "connected", None),
        "algotrading": getattr(terminal, "trade_allowed", None),
        "python_api_disabled": getattr(terminal, "tradeapi_disabled", None),
        "account_trade_allowed": getattr(account, "trade_allowed", None),
        "account_trade_expert": getattr(account, "trade_expert", None),
    }


def permissions_allowed(status: dict) -> bool:
    return all(status.get(key) is True for key in (
        "connected", "algotrading", "account_trade_allowed", "account_trade_expert",
    )) and status.get("python_api_disabled") is False


def permissions_label(status: dict) -> str:
    fields = (
        ("connected", "Conexao", "CONECTADA", "DESCONECTADA"),
        ("algotrading", "Algotrading", "LIGADO", "DESLIGADO"),
        ("python_api_disabled", "API Python", "BLOQUEADA", "PERMITIDA"),
        ("account_trade_allowed", "Negociacao da conta", "PERMITIDA", "BLOQUEADA"),
        ("account_trade_expert", "Robos na conta", "PERMITIDOS", "BLOQUEADOS"),
    )
    return " | ".join(
        f"{label}: {yes if status.get(key) is True else no if status.get(key) is False else 'INDISPONIVEL'}"
        for key, label, yes, no in fields
    )
