"""CTO Agent v1 para gerar missoes TraderIA.

O utilitario le a governanca documental do projeto, recebe um objetivo simples
e grava uma missao estruturada em .traderia/mission.md.
"""

import argparse
import json
import os
from pathlib import Path
import sys
from urllib import request
from urllib.error import HTTPError, URLError

from file_utils import read_text_auto, write_utf8


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MISSION_FILE = PROJECT_ROOT / ".traderia" / "mission.md"
CONTEXT_FILES = (
    "CODEX_PLAYBOOK.md",
    "ARCHITECTURE_RULES.md",
    "TRADERIA_ARCHITECTURE_BIBLE.md",
)
DEFAULT_MODEL = "gpt-5-mini"
RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
MAX_CONTEXT_CHARS_PER_FILE = 12000


def read_project_context() -> str:
    """Le documentos de governanca sem acessar modulos operacionais."""
    sections: list[str] = []
    for file_name in CONTEXT_FILES:
        path = PROJECT_ROOT / file_name
        if path.is_file():
            content = read_text_auto(path)[:MAX_CONTEXT_CHARS_PER_FILE]
        else:
            content = "Documento nao encontrado."
        sections.append(f"## {file_name}\n\n{content}")
    return "\n\n---\n\n".join(sections)


def build_prompt(objective: str, project_context: str) -> list[dict[str, str]]:
    """Monta prompt para gerar uma missao executavel pelo Codex."""
    system_prompt = (
        "Voce e o TraderIA CTO. Transforme um objetivo simples em uma missao "
        "estruturada para o Codex executar. Respeite estritamente a arquitetura "
        "do TraderIA_WDO. Nao proponha operacao real, corretora, MT5, IA "
        "operacional ou mudancas em Domain sem autorizacao explicita. "
        "A resposta deve ser somente o conteudo de .traderia/mission.md, em "
        "Markdown, sem cercas de codigo e sem comentarios externos."
    )
    user_prompt = (
        "Contexto documental do projeto:\n\n"
        f"{project_context}\n\n"
        "Objetivo simples informado pelo usuario:\n\n"
        f"{objective}\n\n"
        "Gere uma missao completa em portugues com esta estrutura minima:\n"
        "# Missao Atual\n\n"
        "## Titulo\n\n"
        "## Status\n\n"
        "PENDENTE\n\n"
        "## Objetivo\n\n"
        "## Contexto\n\n"
        "## Escopo\n\n"
        "## Regras Arquiteturais\n\n"
        "## Nao Alterar\n\n"
        "## Validacao Obrigatoria\n\n"
        "## Criterios de Aceite\n\n"
        "## Entrega Esperada\n\n"
        "A missao deve ser objetiva, implementavel e segura."
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def call_openai(messages: list[dict[str, str]]) -> str:
    """Chama a API da OpenAI usando apenas biblioteca padrao."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY nao configurada.")

    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    endpoint = os.environ.get("OPENAI_RESPONSES_ENDPOINT", RESPONSES_ENDPOINT)
    payload = json.dumps(
        {
            "model": model,
            "input": messages,
        },
    ).encode("utf-8")
    http_request = request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=90) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro HTTP da OpenAI: {exc.code} - {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Falha de conexao com OpenAI: {exc.reason}") from exc

    return extract_text(response_payload)


def extract_text(response_payload: dict[str, object]) -> str:
    """Extrai texto da resposta mantendo compatibilidade defensiva."""
    output_text = response_payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    fragments: list[str] = []
    output = response_payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict):
                    continue
                text = content_item.get("text")
                if isinstance(text, str):
                    fragments.append(text)

    text = "\n".join(fragments).strip()
    if not text:
        raise RuntimeError("Resposta da OpenAI nao contem texto utilizavel.")
    return text


def normalize_mission(content: str) -> str:
    """Garante que o arquivo final comece pela secao oficial de missao."""
    mission = content.strip()
    if not mission.startswith("# Miss"):
        mission = f"# Missao Atual\n\n{mission}"
    return f"{mission}\n"


def write_mission(content: str) -> None:
    """Grava somente .traderia/mission.md."""
    write_utf8(MISSION_FILE, normalize_mission(content))


def parse_args() -> argparse.Namespace:
    """Processa argumentos opcionais de conveniencia."""
    parser = argparse.ArgumentParser(description="TraderIA CTO Agent v1")
    parser.add_argument(
        "--objective",
        help="Objetivo simples da missao. Sem este argumento, sera solicitado.",
    )
    return parser.parse_args()


def main() -> int:
    """Executa o CTO Agent local."""
    args = parse_args()
    objective = args.objective or input("Objetivo da missao: ").strip()
    if not objective:
        print("Objetivo vazio. Nenhuma missao foi criada.")
        return 1

    try:
        project_context = read_project_context()
        mission = call_openai(build_prompt(objective, project_context))
        write_mission(mission)
    except (RuntimeError, UnicodeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    print("Missao criada em .traderia/mission.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
