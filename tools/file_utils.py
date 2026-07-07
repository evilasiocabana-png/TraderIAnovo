"""Utilitarios de encoding para ferramentas locais TraderIA."""

from pathlib import Path


SUPPORTED_ENCODINGS = ("utf-8", "utf-8-sig", "utf-16")


def read_text_auto(path: str | Path) -> str:
    """Le texto tentando UTF-8, UTF-8-SIG e UTF-16, nessa ordem."""
    text_path = Path(path)
    errors: list[str] = []
    for encoding in SUPPORTED_ENCODINGS:
        try:
            return text_path.read_text(encoding=encoding)
        except UnicodeError as exc:
            errors.append(f"{encoding}: {exc}")
    details = "; ".join(errors)
    raise UnicodeError(
        f"Nao foi possivel ler {text_path} com os encodings suportados "
        f"({', '.join(SUPPORTED_ENCODINGS)}). Detalhes: {details}"
    )


def write_utf8(path: str | Path, content: str) -> None:
    """Grava texto em UTF-8, criando a pasta pai quando necessario."""
    text_path = Path(path)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(content, encoding="utf-8")
