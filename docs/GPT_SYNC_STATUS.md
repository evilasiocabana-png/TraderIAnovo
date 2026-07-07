# TraderIA Novo - Status para GPT

Atualizado em: 2026-07-07

## Leitura Obrigatoria Para Resultado do Inbox

Quando o usuario pedir:

```text
traga o resultado do ultimo inbox
o que foi executado pelo inbox
resultado do inbox
```

leia primeiro:

```text
LATEST_INBOX_RESULT.md
```

Depois, se precisar de detalhes, leia os arquivos listados naquele documento.
Nao use `codex/inbox/` para resumir resultado, porque `codex/inbox/` contem
apenas missoes pendentes.

Repositorio oficial:

```text
https://github.com/evilasiocabana-png/TraderIAnovo
```

Branch oficial:

```text
main
```

## Ultimo Inbox Executado

Entrada:

```text
PROGRAM_TIA_DYNAMIC_EXIT_RUNTIME_FULL_EXECUTION
```

Status:

```text
completed
```

Commits:

```text
8f75a4a Process dynamic exit runtime program inbox
```

## Arquivos Que Confirmam a Execucao

Relatorio:

```text
codex/completed/PROGRAM_TIA_DYNAMIC_EXIT_RUNTIME_FULL_EXECUTION/EXECUTION_REPORT.md
```

Programa registrado:

```text
governance/programs/PROGRAM_TIA_DYNAMIC_EXIT_RUNTIME_FULL_EXECUTION.md
```

Proxima missao criada:

```text
codex/inbox/MISSION_TIA-007_IMPLEMENTAR_MOTOR_DE_LEITURA_DE_MERCADO/MISSION.md
```

Registro de governanca:

```text
governance/execution/MISSION_INDEX.md
governance/execution/EXECUTION_STATE.json
governance/execution/EXECUTION_LOG.md
```

## Observacao para GPT

Se uma busca do GitHub disser que os arquivos nao existem, trate como indice
desatualizado ou consulta no repositorio errado. A fonte de verdade e a branch
`main` do repositorio `evilasiocabana-png/TraderIAnovo`.

O `codex/inbox` pode conter missoes pendentes. Resultado concluido deve ser
procurado em:

```text
codex/completed/
```
