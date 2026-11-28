from types import SimpleNamespace
from core.real_account_sizing import basket_target, volume_error
from application.source_channel_gate import entry_volume, POLICY
from application.model23_basket_accumulator import Model23BasketManager
from application.model29_basket_accumulator import Model29BasketManager
from application.mt5_demo_robot_service import MT5DemoRobotService


def test_demo_unchanged(monkeypatch):
    monkeypatch.setenv("TRADERIA_EXECUTION_ACCOUNT_MODE", "DEMO")
    assert basket_target() == 1000
    assert entry_volume({"reinforcement_policy": POLICY}, "EURUSD", 0.1) == 0.2
    assert Model23BasketManager(None).full_exit_usd == 1000
    assert Model29BasketManager(None).full_exit_usd == 1000


def test_real_sizes_and_targets(monkeypatch):
    monkeypatch.setenv("TRADERIA_EXECUTION_ACCOUNT_MODE", "REAL")
    assert basket_target() == 100
    assert Model23BasketManager(None).full_exit_usd == 100
    assert Model29BasketManager(None).full_exit_usd == 100
    assert entry_volume({"reinforcement_policy": POLICY}, "EURUSD", 0.1) == 0.02
    for model, expected in [("MODELO_23_BASKET_ACCUMULATOR_SOURCE_M8", 0.01), ("MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29", 0.02), ("MODELO_29_BASKET_ACCUMULATOR", 0.02)]:
        plan = SimpleNamespace(operational_model=model, stop_management_parameters={})
        assert MT5DemoRobotService._execution_volume(None, plan, plan) == expected
        assert volume_error(SimpleNamespace(quantity=expected, operational_model=model), "REAL") is None
        assert volume_error(SimpleNamespace(quantity=expected*10, operational_model=model), "REAL")
        assert volume_error(SimpleNamespace(quantity=expected*10, operational_model=model), "DEMO") is None


def test_real_basket_threshold(monkeypatch):
    monkeypatch.setenv("TRADERIA_EXECUTION_ACCOUNT_MODE", "REAL")
    for cls in (Model23BasketManager, Model29BasketManager):
        manager = cls(None)
        assert not manager._exit_reason(99.99)
        assert manager._exit_reason(100)
    monkeypatch.setenv("TRADERIA_EXECUTION_ACCOUNT_MODE", "DEMO")
    for cls in (Model23BasketManager, Model29BasketManager):
        assert not cls(None)._exit_reason(100)
        assert cls(None)._exit_reason(1000)
