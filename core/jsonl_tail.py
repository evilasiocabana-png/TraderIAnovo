"""Bounded JSONL tail reads for operational logs."""

from __future__ import annotations

from pathlib import Path


def read_last_text_lines(
    path: Path,
    *,
    limit: int,
    block_size: int = 64 * 1024,
) -> list[str]:
    """Read only the final ``limit`` lines instead of loading the whole file."""

    wanted = max(int(limit), 0)
    if wanted == 0 or not path.exists():
        return []
    chunks: list[bytes] = []
    newline_count = 0
    with path.open("rb") as source:
        source.seek(0, 2)
        position = source.tell()
        while position > 0 and newline_count <= wanted:
            size = min(max(int(block_size), 1024), position)
            position -= size
            source.seek(position)
            chunk = source.read(size)
            chunks.append(chunk)
            newline_count += chunk.count(b"\n")
    data = b"".join(reversed(chunks))
    return [
        line.decode("utf-8", errors="ignore")
        for line in data.splitlines()[-wanted:]
    ]
