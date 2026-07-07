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

        for terminal_dir in sorted(terminal_root.iterdir()):
            candidate = terminal_dir / "MQL5" / "Files" / self.FILE_NAME
            if candidate.exists():
                return candidate

        return None

    def default_for_terminal(self, terminal_dir: Path) -> Path:
        return terminal_dir / "MQL5" / "Files" / self.FILE_NAME
