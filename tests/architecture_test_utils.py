"""Utilitarios compartilhados para testes arquiteturais."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ArchitectureViolation:
    """Representa uma violacao arquitetural detectada por teste."""

    path: Path
    item: str
    reason: str

    def __str__(self) -> str:
        return f"{self.path}:{self.item} ({self.reason})"


@dataclass(frozen=True)
class ExplicitException:
    """Excecao explicita e justificada para uma regra arquitetural."""

    path: Path
    reason: str
    items: set[str] = field(default_factory=set)


def python_files(root: Path) -> list[Path]:
    """Lista arquivos Python abaixo de uma raiz, ignorando caches."""
    if root.is_file():
        return [root]
    return [
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def files_from_roots(roots: tuple[Path, ...]) -> list[Path]:
    """Lista arquivos Python a partir de arquivos ou diretorios."""
    files: list[Path] = []
    for root in roots:
        files.extend(python_files(root))
    return files


def read_source(path: Path) -> str:
    """Le codigo fonte com encoding padrao do projeto."""
    return path.read_text(encoding="utf-8")


def parse_ast(path: Path) -> ast.AST:
    """Parseia AST com contexto de arquivo em caso de erro."""
    try:
        return ast.parse(read_source(path))
    except SyntaxError as exc:
        raise AssertionError(f"Erro de sintaxe ao parsear {path}: {exc}") from exc


def imports_from(path: Path) -> set[str]:
    """Extrai imports e nomes importados de um arquivo Python."""
    imports: set[str] = set()
    for node in ast.walk(parse_ast(path)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
            imports.update(alias.name for alias in node.names)
    return imports


def calls_from(path: Path) -> set[str]:
    """Extrai nomes de chamadas de funcao/metodo de um arquivo Python."""
    calls: set[str] = set()
    for node in ast.walk(parse_ast(path)):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            if isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    return calls


def attributes_from(path: Path) -> set[str]:
    """Extrai nomes de atributos acessados em um arquivo Python."""
    return {
        node.attr
        for node in ast.walk(parse_ast(path))
        if isinstance(node, ast.Attribute)
    }


def imported_roots(path: Path) -> set[str]:
    """Extrai o primeiro segmento dos imports de um arquivo."""
    return {item.split(".", maxsplit=1)[0] for item in imports_from(path)}


def forbidden_imports_in(
    path: Path,
    forbidden: set[str],
    exceptions: tuple[ExplicitException, ...] = (),
) -> set[str]:
    """Retorna imports proibidos, respeitando excecoes explicitas."""
    imports = imports_from(path)
    violations = {
        imported
        for imported in imports
        if imported in forbidden or imported.split(".", maxsplit=1)[0] in forbidden
    }
    return _apply_item_exceptions(path, violations, exceptions)


def forbidden_calls_in(
    path: Path,
    forbidden: set[str],
    exceptions: tuple[ExplicitException, ...] = (),
) -> set[str]:
    """Retorna chamadas proibidas, respeitando excecoes explicitas."""
    return _apply_item_exceptions(path, calls_from(path) & forbidden, exceptions)


def forbidden_text_in(
    path: Path,
    forbidden: tuple[str, ...],
    exceptions: tuple[ExplicitException, ...] = (),
) -> list[str]:
    """Retorna fragmentos proibidos encontrados no fonte."""
    source = read_source(path)
    violations = {
        fragment
        for fragment in forbidden
        if fragment in source
    }
    return sorted(_apply_item_exceptions(path, violations, exceptions))


def collect_forbidden_text_violations(
    paths: list[Path],
    forbidden: tuple[str, ...],
    authorized_paths: set[Path] | None = None,
    exceptions: tuple[ExplicitException, ...] = (),
) -> list[ArchitectureViolation]:
    """Coleta violacoes textuais em multiplos arquivos."""
    authorized = set() if authorized_paths is None else authorized_paths
    violations: list[ArchitectureViolation] = []
    for path in paths:
        if path in authorized:
            continue
        for item in forbidden_text_in(path, forbidden, exceptions):
            violations.append(
                ArchitectureViolation(
                    path=path,
                    item=item,
                    reason="texto proibido",
                )
            )
    return violations


def _apply_item_exceptions(
    path: Path,
    items: set[str],
    exceptions: tuple[ExplicitException, ...],
) -> set[str]:
    remaining = set(items)
    for exception in exceptions:
        if exception.path != path:
            continue
        if not exception.items:
            remaining.clear()
            continue
        remaining -= exception.items
    return remaining
