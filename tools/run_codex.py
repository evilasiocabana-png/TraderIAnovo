"""CodeX Runner v1.

Executa o Codex CLI usando a missao atual de .traderia/mission.md.
Ferramenta de desenvolvimento isolada, sem importar modulos operacionais.
"""

from pathlib import Path
import subprocess
import sys

from file_utils import read_text_auto


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MISSION_FILE = PROJECT_ROOT / ".traderia" / "mission.md"
CODEX_PROMPT = (
    "Execute a missão atual lendo .traderia/mission.md e atualize "
    ".traderia/review.md."
)


def read_mission() -> str:
    """Le a missao atual sem modificar arquivos."""
    if not MISSION_FILE.is_file():
        return ""
    return read_text_auto(MISSION_FILE).strip()


def has_active_mission(mission_content: str) -> bool:
    """Valida se existe missao ativa para enviar ao Codex."""
    normalized = mission_content.strip().lower()
    if not normalized:
        return False
    return (
        "nenhuma missao ativa" not in normalized
        and "nenhuma missão ativa" not in normalized
    )


def run_codex(prompt: str) -> int:
    """Executa codex exec com o prompt oficial e imprime o retorno."""
    try:
        result = subprocess.run(
            ["codex", "exec", prompt],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        print("Erro: Codex CLI nao encontrado no PATH.", file=sys.stderr)
        return 1

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def main() -> int:
    """Valida a missao atual e delega execucao ao Codex CLI."""
    try:
        mission_content = read_mission()
    except UnicodeError as exc:
        print(f"Erro de encoding ao ler mission.md: {exc}", file=sys.stderr)
        return 1

    if not has_active_mission(mission_content):
        print("Nenhuma missao ativa encontrada em .traderia/mission.md.")
        return 1

    print("Executando Codex CLI com a missao atual...")
    return run_codex(CODEX_PROMPT)


if __name__ == "__main__":
    raise SystemExit(main())
