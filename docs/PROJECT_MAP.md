# Project Map

## Runtime

- `dashboard_app.py`: Streamlit entrypoint with the tabs Forex MT5, Lab, and Relatório.
- `application/dashboard_service.py`: single facade consumed by the dashboard.
- `application/forex_mt5_service.py`: read-only Forex MT5 view model.
- `application/lab_service.py`: theoretical Lab result view model.
- `application/report_service.py`: consolidated report view model.
- `application/mt5_visual_signal_exporter.py`: read-only JSON payload for the MT5 visual indicator.
- `application/mt5_trade_audit_service.py`: read-only trade audit baseline for Relatório.

## Contracts

- `domain/contracts/market_candle.py`
- `domain/contracts/forex_signal.py`
- `domain/contracts/lab_result.py`
- `domain/contracts/report_row.py`
- `domain/contracts/mt5_status.py`
- `domain/contracts/visual_signal.py`
- `domain/contracts/trade_audit.py`

## Infrastructure

- `infrastructure/mt5/mt5_readonly_provider.py`: placeholder for MT5 read-only reads.
- `infrastructure/mt5/mt5_connection_probe.py`: connection probe boundary.
- `infrastructure/mt5/mt5_symbol_mapper.py`: symbol normalization boundary.
- `infrastructure/mt5/mt5_visual_signal_path_resolver.py`: resolves the MT5 visual JSON path.

## MT5 Visual Assets

- `mt5/indicators/TraderIAVisualSignals.mq5`: source indicator used as reference for visual signals.
- `mt5/templates/TraderIAVisualSignals.tpl`: MT5 chart template reference.

## Imported TraderIA References

- `TRADERIA_GPT_INSTRUCTIONS.md`
- `TRADERIA_GPT_KNOWLEDGE_FILES.md`
- `TRADERIA_ARCHITECTURE_BIBLE.md`
- `ARCHITECTURE_RULES.md`
- `docs/PROJECT_MAP_TRADERIA_ATUAL.md`
- `docs/MT5_VISUAL_SIGNAL_CONTRACT.md`
- `docs/MT5_RESEARCH_OPERATION_RUNBOOK.md`

## Governance

- `codex/inbox/`: authorized missions waiting for execution.
- `codex/processing/`: one mission in progress.
- `codex/completed/`: completed missions and reports.
- `codex/failed/`: failed missions and error reports.
- `governance/execution/`: current state, blockers, logs, and next mission.
- `governance/programs/`, `tracks/`, `missions/`, `adr/`, `reports/`: planning and audit records.
