# M23 Pattern Filter

## Objective

Measure which causal market contexts improve or damage the signals copied by
Model 23 without adding heavy work to the ten-second operational cycle.

## Boundary

The source model still decides entry, direction, SL, TP and native exit. M23
still copies that complete contract and adds only its basket exit. The Pattern
Filter is an execution gate and does not recalculate or distort the source
setup.

## Offline Replay

The Replay tab reads the local MT5 audit snapshot and keeps only closed M23
trades whose `source_operational_model` belongs to the current M23 contract.
Legacy or retired source contracts are counted separately and never mixed with
the active sample.

For every eligible trade it locates the last closed M5 `EventRecord` at or
before entry. The frozen context contains:

- trend and structure alignment with the order direction;
- RSI zone;
- ADX zone;
- ATR regime;
- market session;
- last major causal event in the preceding twelve candles.

The sample is split chronologically into 60% discovery, 20% validation and 20%
out-of-sample. To avoid sparse combinations, the miner evaluates causal pattern
families independently by source model and direction: trend, structure, RSI,
ADX, ATR regime, session, major-event family and trend/structure alignment.

A rule needs at least 20 occurrences, at least three observations in every
split and the same expectancy sign in discovery, validation and OOS before it
can be classified as `APPROVE` or `BLOCK`. Otherwise it remains
`NO_EVIDENCE`. Conflicting live evidence always falls back to `NO_EVIDENCE`.

## Runtime

The heavy calculation writes `.traderia/research/m23_pattern_filter/report.json`.
At runtime the M23 contract reads only this small artifact and reuses the M5
causal record already produced by the shared Model 28 market pass. It performs
no Lab run, backtest, MT5 history query or indicator recalculation.

Every copied M23 plan records:

- `m23_pattern_filter_mode`;
- `m23_pattern_filter_decision`;
- `m23_pattern_filter_rule_id`;
- `m23_pattern_filter_pattern_id`;
- sample count and validation/OOS expectancy;
- `m23_pattern_filter_blocks_execution`.

The operational mode is `ACTIVE_BLOCK_ONLY`. A confirmed `BLOCK` changes the
new M23 candidate to `WAIT` before the provider is called. `APPROVE` does not
force an entry, and `NO_EVIDENCE` preserves the source signal.

The portfolio-wide RSI family is also evaluated by direction. The current
validated defensive rule blocks an M23 `SELL` from any source when the causal
closed-candle RSI is below 30. A portfolio `BLOCK` has precedence over an
`APPROVE` from an individual source because it is an explicit basket-risk
guardrail.

This rule is versioned as a promoted drawdown guardrail. Automatic recalculation
continues updating its sample and metrics, but cannot silently remove the
operational block. Changing or retiring it requires an explicit audited change.
Its objective is reducing drawdown, so it is evaluated separately from filters
whose sole objective is maximizing net expectancy.

## Safety Rules

- Only closed candles at or before the signal may be read.
- Active and legacy source contracts must never share one sample.
- Missing context or missing evidence means `NO_EVIDENCE`, never an implicit
  block.
- For allowed signals, the filter cannot change entry, volume, SL, TP or basket
  management.
- A discovered rule needs stable discovery, validation and OOS sign to prevent
  a new M23 entry. A promoted drawdown guardrail is the documented exception and
  can only be added or removed explicitly.
