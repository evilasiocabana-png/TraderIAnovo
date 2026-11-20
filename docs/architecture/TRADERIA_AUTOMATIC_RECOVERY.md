# Automatic recovery

Authorized 2026-09-23. Existing Windows task TraderIANovo Local App now runs
scripts/ensure_traderianovo.ps1 at user logon and every hour.
Interval reduced at user request to lower auxiliary application checks;
the existing minute-based RAM guard remains responsible for panel recovery.
Interactive user principal is preserved; no credentials or automatic login.
Runs on battery, catches missed starts, ignores overlapping task instances.
Task timeout is four minutes with three one-minute retries on failure.

Recovery checks panel health, RAM guard and Demo terminal. If unhealthy or
missing, it invokes the official launcher with NoBrowser. The desktop shortcut
still opens the browser normally. Recovery does not change model selection,
armed state, weekly schedule or Real authorization. No positions are closed.
An unrelated listener on port 8532 is not terminated by the launcher.

Limit: recovery requires Windows to be running and the user to be logged in;
it cannot trade while the PC is powered off or asleep. It does not bypass
manual disarming, the weekend schedule or disabled Real authorization.

Validated PowerShell syntax and actual scheduled run with result zero,
local health ok, both triggers enabled, Real DISABLED. No intentional crash
or OS restart test performed. Previous task XML is backed up locally in
.traderia/runtime/local_app_task_before_recovery_20260923.xml, not versioned.
