"""Resolve o caminho do JSON visual lido pelo indicador MT5."""

from __future__ import annotations

import os
from pathlib import Path


class MT5VisualSignalPathResolver:
    FILE_NAME = "traderia_visual_signals.json"

    def detect(self) -> Path | None:
        appdata = os.getenv("APPDATA", "").strip()
        if not appdata:
            return None

        terminal_root = Path(appdata) / "MetaQuotes" / "Terminal"
        if not terminal_root.exists():
            return None

        terminal_dirs = sorted(
            [path for path in terminal_root.iterdir() if path.is_dir()],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        for terminal_dir in terminal_dirs:
            candidate = terminal_dir / "MQL5" / "Files" / self.FILE_NAME
            if candidate.exists():
                return candidate

        for terminal_dir in terminal_dirs:
            files_dir = terminal_dir / "MQL5" / "Files"
            if files_dir.exists():
                return files_dir / self.FILE_NAME

        return None

    def default_for_terminal(self, terminal_dir: Path) -> Path:
        return terminal_dir / "MQL5" / "Files" / self.FILE_NAME
