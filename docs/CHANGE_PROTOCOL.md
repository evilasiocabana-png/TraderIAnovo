# TraderIA Novo - Protocolo de Mudanca via GPT e Codex Inbox

Este documento define como transformar uma ideia do GPT em mudanca segura no
TraderIA Novo.

## Principio

O GitHub e a fonte da verdade para codigo, governanca e rastreabilidade. O
Codex executa apenas missoes colocadas em `codex/inbox`, com escopo, aceite,
testes e rollback.

## Formato da missao

```text
codex/inbox/MISSION_TIA-XXX_NOME_CURTO/
  README.md
  MISSION.md
  CODEX.md
  ACCEPTANCE.md
```

## Campos obrigatorios

Toda missao deve informar:

- objetivo;
- motivo;
- area impactada;
- arquivos permitidos;
- arquivos proibidos;
- guardrails aplicaveis;
- criterio de aceite;
- validacao obrigatoria;
- rollback;
- risco operacional;
- documentacao a atualizar.

## Areas impactadas validas

- `GOVERNANCE_ONLY`
- `TAB_FOREX_MT5`
- `TAB_LAB`
- `TAB_RELATORIO`
- `MT5_VISUAL`
- `ALPHA_LIBRARY`
- `SETUP_LOGIC`
- `TRADE_PLAN`
- `DEMO_EXECUTION`
- `REPORT_AUDIT`

## Modelo de prompt para o GPT gerar missao

```text
Crie uma missao Codex Inbox para TraderIA Novo.

Contexto:
- Sistema operacional atual deve ser preservado.
- Ler docs/SYSTEM_FLOW.md, docs/APP_TABS_FLOW.md,
  docs/OPERATIONAL_GUARDRAILS.md, docs/ALPHA_TRACEABILITY.md e
  docs/SETUP_LOGIC_TRACEABILITY.md.

Objetivo:
<descrever melhoria>

Area impactada:
<uma area valida>

Restricoes:
- nao quebrar app local;
- nao recalcular Lab pesado no ciclo Forex;
- nao mudar operacao real;
- nao versionar runtime local;
- manter rollback por commit.

Entregue:
- README.md
- MISSION.md
- CODEX.md
- ACCEPTANCE.md
```

## Checklist antes de executar

- A missao esta em `codex/inbox`.
- `codex/processing` esta vazio.
- A missao declara arquivos permitidos.
- A missao nao viola guardrails.
- O estado Git esta conhecido.
- O risco operacional esta classificado.

## Checklist depois de executar

- Criterios de aceite conferidos.
- Testes proporcionais executados.
- `EXECUTION_REPORT.md` criado.
- Missao movida para `codex/completed` ou `codex/failed`.
- `governance/execution` atualizado.
- Commit e push realizados.

## Quando bloquear

Bloquear a missao se:

- pedir operacao real sem autorizacao formal;
- pedir alteracao sem arquivos permitidos;
- exigir acesso a credenciais;
- conflitar com estado operacional ideal;
- misturar muitas areas criticas sem plano de arquitetura;
- nao houver rollback claro.
