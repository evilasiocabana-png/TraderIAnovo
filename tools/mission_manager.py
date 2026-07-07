"""TraderIA Mission Manager v7.

Utilitario para exibir, criar, editar, arquivar missoes e carregar Sprints.
Nao importa modulos da aplicacao e usa apenas biblioteca padrao do Python.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
import unicodedata

from file_utils import read_text_auto, write_utf8


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRADERIA_DIR = PROJECT_ROOT / ".traderia"
MISSION_FILE = TRADERIA_DIR / "mission.md"
REVIEW_FILE = TRADERIA_DIR / "review.md"
SPRINT_FILE = TRADERIA_DIR / "sprint.md"
HISTORY_DIR = TRADERIA_DIR / "history"
DEFAULT_MISSION_CONTENT = "# Missao Atual\n\nNenhuma missao ativa.\n"


@dataclass(frozen=True)
class SprintMission:
    """Representa uma missao declarada em sprint.md."""

    number: str
    title: str
    status: str


@dataclass(frozen=True)
class SprintSummary:
    """Resumo calculado em memoria a partir de sprint.md."""

    name: str
    objective: str
    missions: tuple[SprintMission, ...]


def normalize_text(value: str) -> str:
    """Remove acentos para comparacoes tolerantes ao texto do Markdown."""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def status_label(path: Path, *, is_dir: bool = False) -> str:
    """Retorna OK quando o caminho esperado existe."""
    exists = path.is_dir() if is_dir else path.is_file()
    return "OK" if exists else "MISSING"


def read_mission() -> str:
    """Le o arquivo de missao sem modificar nenhum artefato."""
    if not MISSION_FILE.is_file():
        return "Missao nao encontrada."
    try:
        return read_text_auto(MISSION_FILE).strip()
    except UnicodeError as exc:
        return f"Erro de encoding ao ler mission.md: {exc}"


def read_sprint() -> str:
    """Le o arquivo da Sprint sem modificar nenhum artefato."""
    if not SPRINT_FILE.is_file():
        return "Sprint nao encontrada."
    try:
        return read_text_auto(SPRINT_FILE).strip()
    except UnicodeError as exc:
        return f"Erro de encoding ao ler sprint.md: {exc}"


def has_active_mission(mission_content: str) -> bool:
    """Indica se existe missao ativa para arquivamento."""
    normalized = normalize_text(mission_content.strip().lower())
    if not normalized:
        return False
    return "nenhuma missao ativa" not in normalized


def archive_mission() -> None:
    """Arquiva a missao atual sem apagar nem alterar mission.md."""
    mission_content = read_mission()
    if mission_content.startswith("Erro de encoding"):
        print(mission_content)
        return
    if not has_active_mission(mission_content):
        print("Nenhuma missao ativa para arquivar.")
        return

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = HISTORY_DIR / f"mission_{timestamp}.md"
    write_utf8(archive_path, f"{mission_content}\n")
    print(f"Missao arquivada em: {archive_path}")


def read_multiline_description() -> str:
    """Le descricao multilinha ate uma linha contendo apenas END."""
    print("Descricao da missao:")
    lines: list[str] = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def build_mission_content(title: str, description: str) -> str:
    """Monta o conteudo canonico de mission.md."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "# Missao Atual\n\n"
        "## Titulo\n\n"
        f"{title}\n\n"
        "## Data\n\n"
        f"{created_at}\n\n"
        "## Status\n\n"
        "PENDENTE\n\n"
        "## Descricao\n\n"
        f"{description}\n"
    )


def create_new_mission(title: str | None = None, description: str | None = None) -> None:
    """Cria ou atualiza mission.md com uma nova missao pendente."""
    mission_title = (
        title.strip() if title is not None else input("Titulo da missao: ").strip()
    )
    mission_description = (
        description.strip()
        if description is not None
        else read_multiline_description()
    )

    write_utf8(MISSION_FILE, build_mission_content(mission_title, mission_description))
    print("Nova missao criada em .traderia/mission.md")


def edit_mission() -> None:
    """Abre mission.md no editor padrao do sistema operacional."""
    if not MISSION_FILE.is_file():
        write_utf8(MISSION_FILE, DEFAULT_MISSION_CONTENT)
    os.startfile(str(MISSION_FILE))
    print("Mission file opened successfully.")


def extract_sprint_name(lines: list[str]) -> str:
    """Extrai o primeiro titulo Markdown como nome da Sprint."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Sprint nao identificada"


def extract_section(lines: list[str], section_name: str) -> str:
    """Extrai o texto de uma secao de nivel 2 do Markdown."""
    target = normalize_text(section_name).lower()
    collecting = False
    section_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        normalized = normalize_text(stripped).lower()
        if stripped.startswith("## "):
            if collecting:
                break
            collecting = normalized == f"## {target}"
            continue
        if collecting:
            section_lines.append(line.rstrip())

    return "\n".join(section_lines).strip() or "Objetivo nao identificado."


def clean_mission_title(line: str) -> str:
    """Remove marcadores de checklist do titulo da missao."""
    title = line.strip()
    title = re.sub(r"^\[[ xX]\]\s*", "", title)
    title = re.sub(r"^[☐☑]\s*", "", title)
    return title.strip()


def parse_sprint_missions(lines: list[str]) -> tuple[SprintMission, ...]:
    """Extrai missoes declaradas no sprint.md."""
    missions: list[SprintMission] = []
    current_number: str | None = None
    current_title = ""
    current_status = "NAO INFORMADO"

    def flush_current() -> None:
        if current_number is None:
            return
        missions.append(
            SprintMission(
                number=current_number,
                title=current_title or "Titulo nao identificado",
                status=current_status,
            )
        )

    for line in lines:
        stripped = line.strip()
        normalized = normalize_text(stripped).lower()
        if stripped.startswith("### ") and "missao" in normalized:
            flush_current()
            match = re.search(r"(\d+)", stripped)
            current_number = match.group(1) if match else "?"
            current_title = ""
            current_status = "NAO INFORMADO"
            continue

        if current_number is None or not stripped:
            continue

        if normalized.startswith("status:"):
            current_status = stripped.split(":", 1)[1].strip().upper()
            continue

        if not current_title and not normalized.startswith(("objetivo:", "depende")):
            current_title = clean_mission_title(stripped)

    flush_current()
    return tuple(missions)


def parse_sprint_summary(sprint_content: str) -> SprintSummary:
    """Cria um resumo em memoria da Sprint."""
    lines = sprint_content.splitlines()
    return SprintSummary(
        name=extract_sprint_name(lines),
        objective=extract_section(lines, "Objetivo"),
        missions=parse_sprint_missions(lines),
    )


def is_mission_done(mission: SprintMission) -> bool:
    """Indica se a missao esta marcada como concluida."""
    status = normalize_text(mission.status).upper()
    return status in {"CONCLUIDA", "CONCLUIDO", "DONE"}


def is_mission_blocked(mission: SprintMission) -> bool:
    """Indica se a missao esta bloqueada."""
    return normalize_text(mission.status).upper() == "BLOQUEADA"


def format_mission_line(mission: SprintMission) -> str:
    """Formata uma missao para exibicao."""
    return f"{mission.number} - {mission.title}"


def show_status() -> None:
    """Exibe o status da infraestrutura de missoes e a missao atual."""
    print("==================================")
    print(" TraderIA Mission Manager v7")
    print("==================================")
    print()
    print(f"Mission file .... {status_label(MISSION_FILE)}")
    print()
    print(f"Review file ..... {status_label(REVIEW_FILE)}")
    print()
    print(f"Sprint file ..... {status_label(SPRINT_FILE)}")
    print()
    print(f"History folder .. {status_label(HISTORY_DIR, is_dir=True)}")
    print()
    print("-------------------------------")
    print()
    print("Conteudo da missao:")
    print()
    print(read_mission())
    print()
    print("-------------------------------")
    print()
    print("Ready.")


def show_sprint() -> None:
    """Carrega e exibe o conteudo completo da Sprint atual."""
    print("==================================")
    print(" TraderIA Mission Manager v7")
    print("==================================")
    print()
    print(f"Sprint file ..... {status_label(SPRINT_FILE)}")
    print()
    print("-------------------------------")
    print()
    print("Conteudo da Sprint:")
    print()
    print(read_sprint())
    print()
    print("-------------------------------")
    print()
    print("Ready.")


def show_sprint_status() -> None:
    """Exibe um resumo executivo da Sprint atual sem alterar arquivos."""
    sprint_content = read_sprint()
    if sprint_content.startswith("Sprint nao encontrada") or sprint_content.startswith(
        "Erro de encoding"
    ):
        print(sprint_content)
        return

    summary = parse_sprint_summary(sprint_content)
    total = len(summary.missions)
    completed = sum(1 for mission in summary.missions if is_mission_done(mission))
    percent = int((completed / total) * 100) if total else 0
    current = next(
        (
            mission
            for mission in summary.missions
            if not is_mission_done(mission) and not is_mission_blocked(mission)
        ),
        None,
    )
    if current is None:
        current = next(
            (mission for mission in summary.missions if not is_mission_done(mission)),
            None,
        )
    blocked = tuple(mission for mission in summary.missions if is_mission_blocked(mission))

    print("========================================")
    print("TraderIA Sprint Manager")
    print("========================================")
    print()
    print("Sprint:")
    print(summary.name)
    print()
    print("Objetivo:")
    print(summary.objective)
    print()
    print("Progresso:")
    print(f"{completed} / {total} ({percent}%)")
    print()
    print("Missao Atual:")
    print(format_mission_line(current) if current else "Nenhuma missao pendente.")
    print()
    print("Proximas:")
    if blocked:
        for mission in blocked:
            print(format_mission_line(mission))
    else:
        print("Nenhuma missao bloqueada.")
    print()
    print("========================================")


def parse_args() -> argparse.Namespace:
    """Processa argumentos de CLI sem dependencias externas."""
    parser = argparse.ArgumentParser(description="TraderIA Mission Manager")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("archive", help="Arquiva a missao atual")
    subparsers.add_parser("edit", help="Abre mission.md no editor padrao")
    subparsers.add_parser("sprint-load", help="Carrega a Sprint atual")
    subparsers.add_parser("status", help="Exibe o status da Sprint atual")

    new_parser = subparsers.add_parser("new", help="Cria uma nova missao")
    new_parser.add_argument("--title", help="Titulo da missao")
    new_parser.add_argument("--description", help="Descricao da missao")

    return parser.parse_args()


def main() -> None:
    """Executa o comando solicitado."""
    args = parse_args()
    if args.command == "archive":
        archive_mission()
        return
    if args.command == "edit":
        edit_mission()
        return
    if args.command == "sprint-load":
        show_sprint()
        return
    if args.command == "status":
        show_sprint_status()
        return
    if args.command == "new":
        create_new_mission(title=args.title, description=args.description)
        return
    show_status()


if __name__ == "__main__":
    main()
