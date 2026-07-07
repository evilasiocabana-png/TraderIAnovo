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

## Ultima Missao Inbox Executada

Missao:

```text
MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY
```

Status:

```text
completed
```

Commits:

```text
b0a9e8d Execute MISSION_TIA-006 dynamic exit read-only contract
```

## Arquivos Que Confirmam a Execucao

Relatorio da missao:

```text
codex/completed/MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY/EXECUTION_REPORT.md
```

Auditoria principal:

```text
docs/DYNAMIC_EXIT_READ_ONLY_CONTRACT.md
```

Rastreabilidade:

```text
governance/traceability/DYNAMIC_EXIT_CONTRACT_TRACEABILITY.md
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

O `codex/inbox` fica vazio depois que a missao termina. Isso e esperado. Missoes
concluidas devem ser procuradas em:

```text
codex/completed/
```
