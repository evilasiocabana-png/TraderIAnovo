# Codex Inbox

O repositorio e a fonte da verdade. O Codex executa apenas missoes colocadas em
`codex/inbox/`.

## Ciclo

```text
codex/inbox/
  -> codex/processing/
  -> executa missao
  -> gera EXECUTION_REPORT.md ou ERROR_REPORT.md
  -> codex/completed/ ou codex/failed/
  -> atualiza governance/execution/
  -> commit + push
```

## Pacote de Missao

```text
codex/inbox/MISSION_ID/
  README.md
  MISSION.md
  CODEX.md
  ACCEPTANCE.md
```

Tambem e aceito arquivo unico `codex/inbox/MISSION_ID.md`.

## Regras

- `processing/` deve ficar vazio ao final.
- Nao executar missao nao autorizada.
- Nao criar funcionalidade operacional sem missao explicita.
- MT5 permanece read-only.
- Nenhuma ordem real pode ser enviada.
