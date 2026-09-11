"""The original mined contract is not constrained by the 66-trade study."""
from unittest.mock import patch
from types import SimpleNamespace
import application.model28_pattern_miner_shadow as module
from application.model28_pattern_miner_shadow import Model28ShadowRuntime, model28_parameters


def test_default_registry_also_disables_realized_overlay(tmp_path,monkeypatch):
    registry=tmp_path/'patterns.json'
    monkeypatch.setattr(module,'DEFAULT_MODEL_28_REGISTRY_PATH',registry)
    runtime=Model28ShadowRuntime(registry_path=registry,journal_path=tmp_path/'journal.json',
                                auto_activate_replay_contracts=False)
    assert runtime._realized_filter_enabled is False
    assert model28_parameters()['realized_context_filter_enabled'] is False
    selected=SimpleNamespace(symbol='XAUUSD',timeframe='M5',selected_at='2026-09-11T12:00:00+00:00')
    runtime._selections[('XAUUSD','M5')]=selected
    with patch.object(module,'allows_realized_pattern',side_effect=AssertionError('Offline study was consulted'),create=True):
        assert runtime.live_selection('XAUUSD') is selected
        assert runtime.live_selection() is selected


def test_pattern_ranking_is_not_filtered_by_realized_study(tmp_path,monkeypatch):
    # Reuse the established two-pattern ranking scenario, exercising its real tracker.
    from tests.test_model28_pattern_miner_shadow import test_live_adaptive_selector_uses_strongest_validated_pattern
    with patch.object(module,'allows_realized_pattern',side_effect=AssertionError('Offline study was consulted'),create=True):
        test_live_adaptive_selector_uses_strongest_validated_pattern(tmp_path)
