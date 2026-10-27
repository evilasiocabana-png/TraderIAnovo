"""Account-runtime-scoped execution log location. No broker calls."""
import json
import os
from pathlib import Path


def execution_log_path(root=None):
    root = Path(root) if root is not None else Path.cwd()
    legacy = root / '.traderia' / 'mt5_demo_execution.jsonl'
    marker = root / '.traderia' / 'execution_storage.json'
    if not marker.exists():
        return legacy
    data = json.loads(marker.read_text(encoding='utf-8'))
    if data.get('mode') != os.environ.get('TRADERIA_EXECUTION_ACCOUNT_MODE', 'DEMO').upper():
        return legacy
    path = Path(data['execution_log'])
    if not path.is_absolute() or not path.is_file():
        raise ValueError('Configured execution log is unavailable; do not silently use stale legacy data')
    return path
