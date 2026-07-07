# Architecture

`traderiaianovo` starts with a small, explicit boundary:

- `dashboard_app.py` renders Streamlit only.
- `application/` exposes the dashboard facade and use-case services.
- `domain/contracts/` keeps stable dataclasses shared by services.
- `infrastructure/mt5/` is read-only and never sends broker commands.
- `research/` hosts Lab-oriented research catalogs and engines.
- `codex/` and `governance/` control mission execution.

The UI must import only:

```python
from application.dashboard_service import DashboardService
```

All future operational behavior requires a formal mission, tests, and an ADR when the architecture boundary changes.
