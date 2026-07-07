"""Quality gate local para validacao antes de entregas do Codex."""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "quality_gate_summary.json"


@dataclass(frozen=True)
class QualityGateStep:
    """Uma etapa executavel do quality gate local."""

    key: str
    name: str
    command: tuple[str, ...]


QUALITY_GATE_STEPS: tuple[QualityGateStep, ...] = (
    QualityGateStep(
        key="static_analysis",
        name="Analise estatica",
        command=(sys.executable, "scripts/run_static_analysis.py"),
    ),
    QualityGateStep(
        key="app_py",
        name="Execucao principal",
        command=(sys.executable, "app.py"),
    ),
    QualityGateStep(
        key="test_suite",
        name="Testes automatizados",
        command=(sys.executable, "-m", "unittest", "discover", "-s", "tests"),
    ),
    QualityGateStep(
        key="architecture_audit",
        name="Auditoria arquitetural",
        command=(
            sys.executable,
            "scripts/architecture_audit.py",
        ),
    ),
)


@dataclass(frozen=True)
class QualityGateStepResult:
    """Resultado consolidado de uma etapa do quality gate."""

    step: QualityGateStep
    status: str
    duration_seconds: float
    exit_code: int | None
    message: str


def _format_command(command: tuple[str, ...]) -> str:
    return " ".join(command)


def run_step(step: QualityGateStep) -> QualityGateStepResult:
    """Executa uma etapa e propaga o codigo de saida sem mascarar erros."""

    print("=" * 72, flush=True)
    print(f"[QUALITY GATE] {step.name}", flush=True)
    print(f"[QUALITY GATE] Comando: {_format_command(step.command)}", flush=True)

    started_at = time.perf_counter()
    result = subprocess.run(step.command, cwd=ROOT, check=False)
    duration_seconds = round(time.perf_counter() - started_at, 3)

    if result.returncode == 0:
        print(f"[QUALITY GATE] OK: {step.name}", flush=True)
        status = "PASSED"
        message = f"{step.name} concluida com sucesso."
    else:
        print(
            f"[QUALITY GATE] FALHA: {step.name} "
            f"(exit code {result.returncode})",
            flush=True,
        )
        status = "FAILED"
        message = f"{step.name} falhou com exit code {result.returncode}."

    return QualityGateStepResult(
        step=step,
        status=status,
        duration_seconds=duration_seconds,
        exit_code=result.returncode,
        message=message,
    )


def _pending_result(step: QualityGateStep) -> QualityGateStepResult:
    return QualityGateStepResult(
        step=step,
        status="NOT_RUN",
        duration_seconds=0.0,
        exit_code=None,
        message="Etapa nao executada porque uma etapa obrigatoria anterior falhou.",
    )


def build_summary(
    results: list[QualityGateStepResult],
    *,
    executed_at: str | None = None,
) -> dict[str, object]:
    """Monta o relatorio informativo consolidado do quality gate."""

    by_key = {result.step.key: result for result in results}
    ordered_results = [
        by_key.get(step.key, _pending_result(step)) for step in QUALITY_GATE_STEPS
    ]
    overall_status = (
        "PASSED"
        if all(result.status == "PASSED" for result in ordered_results)
        else "FAILED"
    )

    return {
        "executed_at": executed_at or datetime.now().astimezone().isoformat(),
        "overall_status": overall_status,
        "total_duration_seconds": round(
            sum(result.duration_seconds for result in ordered_results),
            3,
        ),
        "steps": {
            result.step.key: {
                "name": result.step.name,
                "command": _format_command(result.step.command),
                "status": result.status,
                "duration_seconds": result.duration_seconds,
                "exit_code": result.exit_code,
                "message": result.message,
            }
            for result in ordered_results
        },
    }


def write_summary(summary: dict[str, object], path: Path | None = None) -> None:
    """Grava o relatorio consolidado sem interferir nos codigos de saida."""

    target_path = path or REPORT_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(summary, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_summary_for_results(results: list[QualityGateStepResult]) -> None:
    write_summary(build_summary(results))
    print(
        f"[QUALITY GATE] Relatorio consolidado: {REPORT_PATH}",
        flush=True,
    )
    _register_history()


def _register_history() -> None:
    """Registra historico informativo sem alterar o resultado do gate."""

    try:
        try:
            from scripts.quality_gate_history import register_quality_gate_execution
        except ModuleNotFoundError:
            from quality_gate_history import register_quality_gate_execution

        register_quality_gate_execution()
        print("[QUALITY GATE] Historico atualizado.", flush=True)
    except Exception as exc:  # pragma: no cover - protecao informativa
        print(
            f"[QUALITY GATE] Aviso: historico nao atualizado ({exc}).",
            flush=True,
        )


def main() -> int:
    """Executa todas as etapas do quality gate local."""

    print("[QUALITY GATE] Iniciando validacao local do TraderIA_WDO", flush=True)

    results: list[QualityGateStepResult] = []
    for step in QUALITY_GATE_STEPS:
        result = run_step(step)
        results.append(result)
        if result.exit_code != 0:
            print("[QUALITY GATE] Validacao interrompida por falha.", flush=True)
            _write_summary_for_results(results)
            return int(result.exit_code)

    print("=" * 72, flush=True)
    print("[QUALITY GATE] Todas as etapas passaram.", flush=True)
    _write_summary_for_results(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
