import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExecutionStateTest(unittest.TestCase):
    def test_execution_state_is_valid_json(self) -> None:
        path = ROOT / "governance" / "execution" / "EXECUTION_STATE.json"

        state = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(state["project"], "traderiaianovo")
        self.assertEqual(state["workflow"], "codex-inbox")
        self.assertEqual(state["status"], "ready")

    def test_codex_inbox_exists(self) -> None:
        self.assertTrue((ROOT / "codex" / "inbox").is_dir())

    def test_codex_processing_exists_and_starts_empty(self) -> None:
        processing = ROOT / "codex" / "processing"
        contents = [path.name for path in processing.iterdir()]

        self.assertTrue(processing.is_dir())
        self.assertEqual(contents, [".gitkeep"])
