# Project Map

## Runtime

- `dashboard_app.py`: Streamlit entrypoint with the tabs Forex MT5, Lab, and Relatório.
- `application/dashboard_service.py`: single facade consumed by the dashboard.
- `application/forex_mt5_service.py`: read-only Forex MT5 view model.
- `application/lab_service.py`: theoretical Lab result view model.
- `application/report_service.py`: consolidated report view model.

## Contracts

- `domain/contracts/market_candle.py`
- `domain/contracts/forex_signal.py`
- `domain/contracts/lab_result.py`
- `domain/contracts/report_row.py`
- `domain/contracts/mt5_status.py`

## Infrastructure

- `infrastructure/mt5/mt5_readonly_provider.py`: placeholder for MT5 read-only reads.
- `infrastructure/mt5/mt5_connection_probe.py`: connection probe boundary.
- `infrastructure/mt5/mt5_symbol_mapper.py`: symbol normalization boundary.

## Governance

- `codex/inbox/`: authorized missions waiting for execution.
- `codex/processing/`: one mission in progress.
- `codex/completed/`: completed missions and reports.
- `codex/failed/`: failed missions and error reports.
- `governance/execution/`: current state, blockers, logs, and next mission.
- `governance/programs/`, `tracks/`, `missions/`, `adr/`, `reports/`: planning and audit records.
