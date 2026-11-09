import re
from pathlib import Path


def test_recovery_keeps_same_authorized_demo_as_launcher():
    def value(path, key):
        text=Path(path).read_text()
        match=re.search(key + r"\s*=\s*['\"]([^'\"]+)['\"]", text)
        assert match, key
        return match.group(1)
    for key in ['TRADERIA_DEMO_ACCOUNT_LOGIN', 'TRADERIA_DEMO_ACCOUNT_SERVER']:
        assert value('scripts/traderianovo_ram_guard.ps1', key)==value('scripts/abrir_traderianovo.ps1', key)
    assert value('scripts/traderianovo_ram_guard.ps1', 'TRADERIA_REAL_EXECUTION_ENABLED')=='0'
