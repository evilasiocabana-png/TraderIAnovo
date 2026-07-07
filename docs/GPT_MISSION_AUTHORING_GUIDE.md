# TraderIA Novo - Guia para GPT Criar Missoes Codex Inbox

Este guia ensina como pedir ao GPT uma melhoria sem colocar em risco a
operacionalidade atual do TraderIA Novo.

## Fluxo recomendado

```text
Usuario descreve melhoria
  |
  v
GPT gera pacote de missao usando template oficial
  |
  v
Usuario coloca pacote em codex/inbox
  |
  v
Codex executa Inbox
  |
  v
Relatorio + commit + push
```

## Prompt oficial para usar no GPT

Copie e cole:

```text
Voce e o TraderIA Mission Architect.

Crie uma missao Codex Inbox para o projeto TraderIA Novo.

Leia e respeite estes documentos de governanca:
- docs/SYSTEM_FLOW.md
- docs/APP_TABS_FLOW.md
- docs/OPERATIONAL_GUARDRAILS.md
- docs/CHANGE_PROTOCOL.md
- docs/ALPHA_TRACEABILITY.md
- docs/SETUP_LOGIC_TRACEABILITY.md

Use o template:
- codex/templates/GPT_IMPROVEMENT_MISSION_TEMPLATE.md

Melhoria desejada:
<descrever aqui>

Regras obrigatorias:
- preservar a operacionalidade atual;
- nao habilitar operacao real;
- nao usar order_send();
- nao recalcular Lab pesado dentro do ciclo leve Forex;
- nao forcar todos os timeframes para M1;
- nao versionar .traderia, logs, bancos, snapshots ou credenciais;
- declarar arquivos permitidos e proibidos;
- declarar testes e rollback;
- atualizar rastreabilidade se tocar Alpha, setup, saida ou MT5.

Entregue uma pasta de missao completa:

codex/inbox/MISSION_TIA-XXX_NOME_CURTO/
  README.md
  MISSION.md
  CODEX.md
  ACCEPTANCE.md
```

## Como avaliar a resposta do GPT

Antes de mandar para o Codex, conferir:

- A missao tem ID `MISSION_TIA-XXX`.
- O objetivo esta claro.
- A area impactada esta marcada.
- Arquivos permitidos estao explicitos.
- Arquivos proibidos incluem runtime local.
- Guardrails estao presentes.
- Existe plano de teste.
- Existe rollback.
- Se tocar Alpha/setup, a rastreabilidade foi preenchida.

## Exemplo de pacote minimo

```text
codex/inbox/MISSION_TIA-010_AJUSTAR_TABELA_SETUP_TF/
  README.md
  MISSION.md
  CODEX.md
  ACCEPTANCE.md
```

## Quando pedir para o GPT refazer

Peca para refazer se a missao:

- nao declara arquivos permitidos;
- mistura muitas areas criticas;
- pede para alterar runtime local;
- ignora Lab/Forex/MT5 contracts;
- nao tem teste;
- nao tem rollback;
- sugere operacao real.

## Frase curta de uso diario

```text
Crie uma missao TraderIA Novo no padrao codex/inbox usando
codex/templates/GPT_IMPROVEMENT_MISSION_TEMPLATE.md e respeitando docs/*.md.
```
