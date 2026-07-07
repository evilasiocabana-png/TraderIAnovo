# TraderIA Codex Inbox

Este diretorio define o fluxo oficial de execucao por inbox do TraderIA.

Objetivo: permitir que missoes tecnicas sejam colocadas em `codex/inbox/` e
executadas pelo Codex com controle de estado, relatorio, testes, commit e push.

## Resultado do Ultimo Inbox

Para responder perguntas como "traga o ultimo resultado no inbox", leia:

```text
codex/inbox/RESULTADO_DO_ULTIMO_INBOX.md
```

Esse arquivo e apenas ponteiro de leitura e nao deve ser movido para
`processing`.

## Fluxo Oficial

```text
CTO / GPT
-> gera missao em Markdown
-> pacote entra em codex/inbox/
-> Architecture Validation
-> Dependency Validation
-> Codex le governanca e pacote
-> move pacote para codex/processing/
-> executa somente a missao autorizada
-> Tests
-> Quality Gate
-> gera EXECUTION_REPORT.md ou ERROR_REPORT.md
-> move pacote para codex/completed/ ou codex/failed/
-> atualiza governance/execution/
-> Git Review
-> commita e envia ao GitHub
```

## Pastas

- `inbox/`: novas missoes aguardando execucao.
- `processing/`: missao em execucao. Deve ficar vazia ao final de cada ciclo.
- `completed/`: missoes concluidas com sucesso.
- `failed/`: missoes encerradas com erro ou bloqueio.
- `templates/`: modelos oficiais para novas missoes e relatorios.

## Template Oficial para GPT

Quando uma melhoria for planejada no GPT, use:

```text
codex/templates/GPT_IMPROVEMENT_MISSION_TEMPLATE.md
```

Guia de uso:

```text
docs/GPT_MISSION_AUTHORING_GUIDE.md
```

Regra: o GPT deve entregar pacote de missao completo para `codex/inbox`, nao uma
instrucao solta de implementacao.

## Formatos Aceitos

Missao em pasta:

```text
codex/inbox/MISSION_001/
  README.md
  MISSION.md
  CODEX.md
  ACCEPTANCE.md
```

Missao em arquivo unico:

```text
codex/inbox/MISSION_001.md
```

## Ordem de Leitura

Para pacote em pasta, ler nesta ordem:

1. `README.md`
2. `MISSION.md`
3. `CODEX.md`
4. `ACCEPTANCE.md`

Para arquivo unico `.md`, ler o arquivo inteiro.

## Regras Absolutas

- Nao enviar ordens reais.
- Nao criar broker sem missao explicita.
- Nao usar `order_send()`.
- Nao ler posicoes reais sem autorizacao explicita.
- Nao alterar `RiskEngine` sem missao especifica.
- Nao alterar `DecisionPipeline` sem missao especifica.
- Nao alterar estrategias sem missao especifica.
- Integracoes MT5 permanecem read-only salvo decisao formal.
- Dashboard deve consumir apenas `application/DashboardService`.
- UI nao deve acessar `infrastructure` diretamente.
- Nao criar logica quantitativa no frontend.

## Convencoes de Nomenclatura

- Missao em pasta: `MISSION_0001_nome-curto/`.
- Missao em arquivo unico: `MISSION_0001_nome-curto.md`.
- Relatorio de sucesso: `EXECUTION_REPORT.md`.
- Relatorio de falha: `ERROR_REPORT.md`.
- IDs devem ser estaveis e crescentes quando possivel.

## Politica de Execucao

Antes de executar qualquer missao, o Codex deve:

1. Ler `governance/execution/EXECUTION_STATE.json`.
2. Ler `PROJECT_EXECUTION_CONTEXT.md`, `PROJECT_STATUS.md`, `NEXT_MISSION.md`,
   `NEXT_BLOCK.md`, `BLOCKED_ITEMS.md` e `MISSION_INDEX.md`.
3. Confirmar que nao ha blocker aplicavel.
4. Confirmar que o escopo nao altera camadas proibidas.
5. Mover a missao para `codex/processing/`.
6. Executar testes e quality gates disponiveis.
7. Registrar inicio, termino, duracao, status, commit, branch, responsavel e
   missao nos arquivos de governanca.

`codex/processing/` deve ficar vazio ao final de cada ciclo.

## Comando de Uso

Depois de colocar uma missao em `codex/inbox/`, use:

```text
Leia codex/inbox e execute a proxima missao autorizada.
```

ou:

```text
Inbox.
```
