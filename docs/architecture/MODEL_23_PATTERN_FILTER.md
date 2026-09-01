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

Each source model and direction receives its own chronological split of 60%
discovery, 20% validation and 20% out-of-sample. To avoid sparse combinations,
the miner evaluates causal pattern families independently by source model and
direction: trend, structure, RSI, ADX, ATR regime, session, major-event family,
trend/structure alignment and the causal RSI combinations with trend,
structure, ADX, ATR, session and event family.

A rule needs at least 20 occurrences, at least three observations in every
split and the same expectancy sign in discovery, validation and OOS before it
can be classified as `APPROVE` or `BLOCK`. Otherwise it remains
`NO_EVIDENCE`.

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

The operational mode is `INDIVIDUAL_BLOCK_ONLY`. A confirmed `BLOCK` from the
same source model changes the new M23 candidate to `WAIT` before the provider
is called. `APPROVE` is informational and does not force an entry, while
`NO_EVIDENCE` preserves the source signal. If different dimensions from the
same source match simultaneously, a validated `BLOCK` has precedence over an
informational `APPROVE`.

There is no portfolio-wide `ALL_SOURCES` rule. This prevents the result from one
source model from blocking another source with a different setup and outcome.

## Safety Rules

- Only closed candles at or before the signal may be read.
- Active and legacy source contracts must never share one sample.
- Missing context or missing evidence means `NO_EVIDENCE`, never an implicit
  block.
- For allowed signals, the filter cannot change entry, volume, SL, TP or basket
  management.
- A discovered rule needs stable discovery, validation and OOS sign to prevent
  a new M23 entry.
