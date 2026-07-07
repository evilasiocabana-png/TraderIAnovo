"""Resolver tecnico para localizar o arquivo visual do MT5."""

from __future__ import annotations

import os
from pathlib import Path


class MT5VisualSignalPathResolver:
    """Localiza o destino do JSON lido pelo indicador visual do MT5."""

    FILE_NAME = "traderia_visual_signals.json"
    LEGACY_FILE_NAME = "traderia_signals.json"

    def detect(self) -> Path | None:
        appdata = os.getenv("APPDATA", "").strip()
        if not appdata:
            return None

        terminal_root = Path(appdata) / "MetaQuotes" / "Terminal"
        if not terminal_root.exists():
            return None

        existing_files = sorted(
            self._iter_terminal_paths(
                terminal_root,
                ("MQL5", "Files", self.FILE_NAME),
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if existing_files:
            return existing_files[0]

        indicator_files = sorted(
            self._iter_terminal_paths(
                terminal_root,
                ("MQL5", "Indicators", "TraderIAVisualSignals.ex5"),
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if indicator_files:
            return indicator_files[0].parents[1] / "Files" / self.FILE_NAME

        legacy_files = sorted(
            self._iter_terminal_paths(
                terminal_root,
                ("MQL5", "Files", self.LEGACY_FILE_NAME),
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if legacy_files:
            return legacy_files[0]

        return None

    def _iter_terminal_paths(
        self,
        terminal_root: Path,
        relative_parts: tuple[str, ...],
    ) -> list[Path]:
        paths: list[Path] = []
        try:
            terminal_dirs = [path for path in terminal_root.iterdir() if path.is_dir()]
        except OSError:
            return paths

        for terminal_dir in terminal_dirs:
            candidate = terminal_dir.joinpath(*relative_parts)
            if candidate.exists():
                paths.append(candidate)
        return paths
