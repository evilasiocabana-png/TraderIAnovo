# M29 historical restoration and fixed defense

Authorized on 2026-09-23, using global-chart operation 5400 as reference.
M29 retains sources M1/M2/M5/M7/M8/M10/M18/M20; M21/M22 remain excluded.
M8/M10/M18/M20 copies return to NORMAL at 0.10, without operational channels.
M7 returns to the historical sequence policy: four equal outcomes or either
four-outcome alternating prefix followed by PP (mirror) or GG (normal).
M7 mirror uses 0.20, RR1 and its existing matched-entry synchronization.
Other source channels remain available for research, not order-mode decisions.

The new defense applies only to new NORMAL M29 copies executed by M23,
XAUUSD, origins M8/M10/M18/M20, volume 0.10. It preserves entry and TP.
At submission, broker order_calc_profit on a USD account prices an SL with
at most USD200 gross modeled loss from the request entry. A closer structural
SL is preserved. Missing/invalid calculation rejects the order; the ordinary
broker order_check still runs after the defense. Original and applied SL are
logged. Existing positions, pending orders already accepted and M7 mirrors
are not modified. This is not a target or trailing stop. Gaps, fill slippage,
commissions and swap may make realized loss exceed USD200.

Normal sources no longer require the additional per-source channel pairing
introduced on September 21. Source identity matching remains for historical
positions; unknown copies must not accidentally release the M7 pair.
Cached mirrors from sources other than M7 are rejected rather than relabeled.

The reference is reconstructed from historical order plans and the persisted
legacy sequence implementation, not a complete runtime snapshot at index5400.
Therefore this is not a promise to reproduce every historical fill or profit.
Real remains disabled. No manual order or forced closure is part of deployment.
