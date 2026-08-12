"""Canonical market scopes for research and Demo execution."""

from __future__ import annotations


MODEL_1_FOREX_PAIRS = (
    "AUDUSD",
    "EURJPY",
    "EURUSD",
    "GBPUSD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "USDJPY",
)

MODEL_6_FOREX_EXPANSION_PAIRS = (
    "AUDCAD",
    "AUDJPY",
    "CADCHF",
    "EURNZD",
    "GBPAUD",
    "GBPCAD",
    "GBPNZD",
    "NZDCAD",
    "NZDJPY",
)

MODEL_3_ALL_FOREX_PAIRS = (
    *MODEL_1_FOREX_PAIRS,
    *MODEL_6_FOREX_EXPANSION_PAIRS,
)

MODEL_7_ALTERNATIVE_MARKETS = (
    "XAUUSD",
    "BTCUSD",
)

MT5_RESEARCH_MARKETS = (
    *MODEL_3_ALL_FOREX_PAIRS,
    *MODEL_7_ALTERNATIVE_MARKETS,
)
