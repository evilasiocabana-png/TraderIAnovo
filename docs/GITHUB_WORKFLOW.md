# GitHub Workflow

The repository is the source of truth.

## Normal Flow

1. Add an authorized mission to `codex/inbox/`.
2. Move one mission to `codex/processing/`.
3. Execute the smallest safe implementation.
4. Run tests.
5. Generate an execution or error report.
6. Move the mission to `codex/completed/` or `codex/failed/`.
7. Update `governance/execution/`.
8. Commit and push.

## Branch

Default branch: `main`.

## Do Not Commit

- Local Python runtime directories.
- `.traderia/`
- Logs and generated reports.
- `.env` and credentials.
- Local databases and backups.
- MT5 compiled files.
