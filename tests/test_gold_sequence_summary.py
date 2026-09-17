import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("model", [23, 29])
@pytest.mark.parametrize("count", [4, 7, 8])
def test_gold_summary_rolls_last_seven_net_results(tmp_path, monkeypatch, model, count):
    import application.model29_sequence_history as history

    source = Path(__file__).resolve().parents[1] / "dashboard_app.py"
    name = f"_model{model}_sequence_title_suffix"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    namespace = {"Path": Path, "json": json, "os": __import__("os")}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), namespace)
    monkeypatch.chdir(tmp_path)
    values = [999, 10, -2, 3, -4, 5, -6, 7][-count:]
    rows = [dict(model=m, symbol="XAUUSD", net=v) for m in (23, 29) for v in values]
    rows.append(dict(model=model, symbol="BTCUSD", net=9000))
    monkeypatch.setattr(history, "closed_m7_positions", lambda payload: rows)
    identity = "test:1"
    root = tmp_path / ".traderia/model29_sequences"
    root.mkdir(parents=True)
    (root / (hashlib.sha256(identity.encode()).hexdigest() + ".json")).write_text(
        json.dumps({"account": identity, "symbols": {"XAUUSD": {"seed": [-900, -800, -700], "mode": "NORMAL"}}}),
        encoding="utf-8",
    )
    provider = SimpleNamespace(_external_mt5_read=lambda *a, **k: {
        "ok": True, "account": {"login": 1, "server": "test"},
    })
    render = lambda: namespace[name](provider, "DEMO", "test")
    expected = values[-7:]
    letters = "".join("G" if v > 0 else "P" for v in expected)
    if model == 23:
        assert f"Ouro M7 original: {letters} | {len(expected)} operacoes | US$ {sum(expected):+.2f}" in render()
    else:
        assert f"{letters} | Saldo M{model} ({len(expected)} operacoes proprias): US$ {sum(expected):+.2f}" in render()
    assert "Bitcoin" not in render()
    rows.extend(dict(model=m, symbol="XAUUSD", net=-20) for m in (23, 29))
    expected = (values + [-20])[-7:]
    if model == 23:
        letters = "".join("G" if v > 0 else "P" for v in expected)
        assert f"Ouro M7 original: {letters} | {len(expected)} operacoes | US$ {sum(expected):+.2f}" in render()
    else:
        assert f"({len(expected)} operacoes proprias): US$ {sum(expected):+.2f}" in render()
    rows.clear()
    assert ("sem resultados" if model == 29 else "sem encerramentos") in render()
    assert "US$ +0.00" in render()
