from pathlib import Path
from core import dual_mt5 as dual


def test_replacement_identity_matches_manual_launcher():
    launcher = (dual.PROJECT / 'scripts/iniciar_traderianovo_real.ps1').read_text(encoding='utf-8-sig')
    assert dual.REAL_LOGIN == '51618035'
    assert dual.REAL_SERVER == 'PepperstoneBS-MT5-Live01'
    assert dual.REAL_ROOT.name == 'real-51618035'
    assert dual.REAL_LOGIN in launcher
    assert '51517136' not in launcher


def test_previous_authorization_cannot_enable_replacement(tmp_path):
    control = tmp_path / 'control.json'
    dual.write_json(control, dict(enabled=True, authorized=True, login='51517136', server=dual.REAL_SERVER))
    assert not dual.real_control_allows(entry=True, path=control)
    assert not dual.real_control_allows(entry=False, path=control)
    dual.write_json(control, dict(enabled=False, authorized=False, login=dual.REAL_LOGIN, server=dual.REAL_SERVER))
    assert not dual.real_control_allows(entry=True, path=control)
    assert not dual.real_control_allows(entry=False, path=control)


def test_desktop_start_and_panel_use_replacement_identity():
    for name in ['scripts/abrir_traderianovo.ps1', 'scripts/preparar_mt5_demo.ps1']:
        text = (dual.PROJECT / name).read_text(encoding='utf-8-sig')
        assert '/login:' + dual.REAL_LOGIN in text
    panel = (dual.PROJECT / 'dashboard/mt5_account_controls.py').read_text(encoding='utf-8-sig')
    assert '51517136' not in panel
    assert dual.REAL_LOGIN in panel
