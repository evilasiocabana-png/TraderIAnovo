# M30 independent source execution and original M23/M7 channel

Authorized 2026-09-29. Supersedes new-order cloning in
OPERATIONAL_MODEL_30_LEARNING.md. Existing paired positions and reports remain
legacy records; no positions or pending orders are migrated or forcibly closed.

M30 receives the canonical original M1/M2/M5/M7/M8/M10/M18/M20 signals in the
regular Demo cycle, independently of M23 acceptance, pairing and basket gates.
M29-derived copies are not additional M30 sources. M23 and M29 routes remain
unchanged. M30 retains its own enable/round/risk gates, Demo hedging restriction,
source SL/TP and exit metadata, source volume, and broker-priced USD200 initial
loss defense previously inherited from direct M23 contracts. No Real activation
or manual order is part of deployment. Gaps, costs and slippage remain possible.

## M7 mode

Reference: broker-confirmed, fully closed ORIGINAL M7 positions executed by M23,
per account and symbol, net of fees. M29, M23/S29, M30, partial and open results
are excluded. Duplicate deals and positions do not increase the reference count.
Failed reads, wrong account, incomplete prior history or costs block admission.
The earlier draft based on M30's own equity was cancelled before installation.

Use confirmed equity pivots with sensitivity 1 (rolling median absolute result,
last 20 nonzero results). Two rising tops AND bottoms confirm Alta; two falling
pairs confirm Baixa. No future pivot is used. Compare a closure with the channel
known before that closure; newly confirmed geometry applies prospectively.

* Alta: below projected floor -> ESPELHADO; at/above floor -> NORMAL.
  Returning into the rising channel normalizes. Above its roof also remains normal.
* Baixa confirmed -> ESPELHADO; closing above its roof -> NORMAL.
* Remaining below the rising floor holds ESPELHADO, it does not toggle repeatedly.
* Without confirmed channel -> NORMAL. Reconstruct on restart; polling does not
  add results or events. Current reference reconstructed NORMAL on deployment.

Only subsequent M7 entries change direction. Mirror uses symmetric stop around
entry and the original structural stop as TP (RR1 before financial defense),
with source volume unchanged. Other sources stay normal. All sources still need
their own valid signal, candle, execution gates and broker acceptance: receiving
the same sources does not guarantee simultaneous fills with M23.

## Persistence and safeguards

Independent attempts use a separate local ledger keyed by account, source,
symbol, source candle and setup, independent of mode. SENDING precedes execution;
uncertain sends block the same source until reconciled. Duplicate requests never
send twice, including after restart. Native M23/M7 history is rechecked before
submission; a changed reference requires a freshly calculated plan. Open own
positions or pending orders in the same symbol/source block another entry.
Legacy m30_pairs remains available for historical comparisons; new attempts are
shown separately with policy and mode. Old candidate admission remains checked;
manual channel research is not relabeled as evidence for this policy.

Validation uses fake broker orders only. Targeted integration covers M18/M20
original source routing, independent cycle while M23 closes, channel break and
reentry, downward channel, causal prefixes, costs/history/account isolation,
uncertain sends, deduplication and unchanged M23/M29 synchronization.
