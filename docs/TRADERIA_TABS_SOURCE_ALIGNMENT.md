# TraderIA Tabs Source Alignment

This audit compared the current local TraderIA project with `TraderIAnovo` for
the three initial tabs: Forex MT5, Lab, and Relatorio.

## Included

### Forex MT5

- `docs/LAB_FOREX_MT5_FLOW.md`
- `docs/LAB_FOREX_MT5_CONTRACT.md`
- `docs/MT5_VISUAL_SIGNAL_CONTRACT.md`
- `docs/MT5_RESEARCH_OPERATION_RUNBOOK.md`
- `application/forex_mt5_service.py`
- `application/mt5_visual_signal_exporter.py`
- `infrastructure/mt5/mt5_readonly_provider.py`
- `infrastructure/mt5/mt5_visual_signal_path_resolver.py`
- `mt5/indicators/TraderIAVisualSignals.mq5`
- `mt5/templates/TraderIAVisualSignals.tpl`

### Lab

- `application/lab_service.py`
- `research/lab_engine.py`
- `research/setup_catalog.py`
- `research/stop_management_catalog.py`
- `domain/contracts/lab_result.py`
- `docs/LAB_FOREX_MT5_CONTRACT.md`

### Relatorio

- `application/report_service.py`
- `application/mt5_trade_audit_service.py`
- `domain/contracts/report_row.py`
- `domain/contracts/trade_audit.py`
- `tests/test_report_service.py`
- `tests/test_mt5_trade_audit_service.py`

### GPT and Architecture References

- `TRADERIA_GPT_INSTRUCTIONS.md`
- `TRADERIA_GPT_KNOWLEDGE_FILES.md`
- `TRADERIA_ARCHITECTURE_BIBLE.md`
- `ARCHITECTURE_RULES.md`
- `docs/PROJECT_MAP_TRADERIA_ATUAL.md`

## Deliberately Excluded

The following local TraderIA areas were not copied into the new repository in
this mission:

- `Python/`
- `.traderia/`
- `logs/`
- generated `reports/`
- local databases
- snapshots and raw operational datasets
- credentials or `.env`
- `infrastructure/execution/`
- any Python code path with operational MT5 order execution

The exclusion is intentional. The baseline repository must preserve read-only
MT5 behavior until a future formal mission designs, tests, and approves any
execution boundary.

## Validation

- `python -m unittest discover -s tests -t .`
- Python source scan for forbidden operational MT5 methods.

Current result: all tests pass and no Python file in `TraderIAnovo` contains
operational MT5 order execution calls.
