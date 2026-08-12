"""Operational identity for the M3 winner-per-pair Forex portfolio."""

from __future__ import annotations

from domain.market_universe import MODEL_3_ALL_FOREX_PAIRS


MODEL_3_ID = "MODELO_3_LAB_ALL_FOREX_WINNERS"
MODEL_3_SHORT_NAME = "M3"
MODEL_3_SOURCE = "M1_LAB_WINNER_PER_PAIR_REUSE"
MODEL_3_SCOPE = MODEL_3_ALL_FOREX_PAIRS
MODEL_3_EXIT_POLICY = "RESEARCH_FIXED_SL_TP"
MODEL_3_PROTOCOL_VERSION = "M3_ALL_FOREX_WINNERS_V1"
