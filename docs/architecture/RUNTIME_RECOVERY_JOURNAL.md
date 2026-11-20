# Recovery 01/11/2026

Authorized automatic recovery with persistent replay protection. Background runtime opt-in supervisor restarts terminated Demo scheduler/market/robot routines; it never creates a second live thread. A stuck thread is not killed automatically. Demo submissions hold an interprocess journal lock. A prior accepted plan is blocked on replay; an ATTEMPT without RESULT blocks that source/symbol pending MT5 reconciliation, including exceptions after submission. Real execution is unchanged.

The existing launcher, hourly Windows recovery and minute RAM guard initialize an internal Streamlit session if the cycle has not updated for 180 seconds. Health HTTP takes precedence over failed listener enumeration to avoid duplicate launches. Confirmation requires the cycle state to advance after session initiation. No new trading process or visible browser is required. The weekly schedule remains Sunday 18:05 to Friday 17:30. This does not operate while Windows is asleep/off, and does not prove the original outage cause.

Backups: local TEMP/traderia_recovery_nov01. 40 targeted tests passed, including accepted replay, unresolved outcome, corrupted journal, singleton and restart. No test orders sent. Existing AUDUSD weekend position was not manually changed. Historical blockers remain pending, not silently reset.
