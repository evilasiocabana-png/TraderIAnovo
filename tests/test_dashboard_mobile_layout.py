from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_preserves_responsive_mobile_contract() -> None:
    source = (ROOT / "dashboard_app.py").read_text(encoding="utf-8")

    assert "@media (max-width: 768px)" in source
    assert "@media (max-width: 430px)" in source
    assert "flex-wrap: wrap" in source
    assert "-webkit-overflow-scrolling: touch" in source
    assert '.traderia-stable-table th:first-child' in source
