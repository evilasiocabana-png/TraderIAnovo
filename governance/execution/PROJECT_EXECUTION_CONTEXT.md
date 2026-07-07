# TraderIA Project Execution Context

TraderIA e um sistema de pesquisa quantitativa, leitura de mercado, dashboard
Streamlit e integracao read-only com MetaTrader 5.

Este diretorio guarda o estado operacional do fluxo de execucao por inbox. O
repositorio deve carregar o contexto suficiente para que o Codex entenda a
proxima missao sem depender de memoria informal da conversa.

## Integracao com GPT

O GPT TraderIA Architect deve usar tambem `governance/cto/` como base de
governanca. Esse diretorio contem o workspace documental CTO importado para o
repositorio principal, incluindo regras, protocolos, templates e roadmaps.

Arquivos principais para GPT:

- `TRADERIA_GPT_INSTRUCTIONS.md`
- `TRADERIA_GPT_KNOWLEDGE_FILES.md`
- `codex/README.md`
- `governance/execution/PROJECT_EXECUTION_CONTEXT.md`
- `governance/cto/README.md`
- `governance/cto/MANIFEST.md`
- `governance/cto/CTO_RULES.md`
- `governance/cto/EXECUTION_PROTOCOL.md`
- `governance/cto/VALIDATION_PROTOCOL.md`

## Fluxo Oficial

1. Ler `governance/execution/EXECUTION_STATE.json`.
2. Ler `governance/execution/PROJECT_EXECUTION_CONTEXT.md`.
3. Ler `governance/execution/NEXT_MISSION.md`.
4. Ler `governance/execution/NEXT_BLOCK.md`.
5. Verificar `governance/execution/BLOCKED_ITEMS.md`.
6. Ler `governance/execution/MISSION_INDEX.md`.
7. Ler o primeiro pacote autorizado em `codex/inbox/`.
8. Validar arquitetura e dependencias declaradas.
9. Mover para `codex/processing/`.
10. Executar somente o escopo autorizado.
11. Rodar testes e quality gates.
12. Criar `EXECUTION_REPORT.md` ou `ERROR_REPORT.md`.
13. Mover para `codex/completed/` ou `codex/failed/`.
14. Atualizar governanca.
15. Revisar Git, commitar e enviar ao GitHub.

## Guardrails do TraderIA

- Operacao real permanece desabilitada.
- Integracao MT5 e read-only salvo decisao formal.
- Nao usar `order_send()`.
- Nao criar broker operacional sem missao explicita.
- Dashboard consome `application/DashboardService`.
- Frontend nao acessa `infrastructure` diretamente.
- Logica quantitativa deve ficar fora da UI.
- Alteracoes em risco, pipeline de decisao e estrategias exigem missao
  especifica.

## Validacao Padrao

Validacao minima para missoes tecnicas:

```powershell
python scripts\run_critical_ci.py
```

Quando a missao exigir, ampliar para testes especificos ou suite completa.

## Quality Gates Disponiveis

Executar quando existirem e forem compativeis com a missao:

```powershell
python scripts\architecture_health.py
python scripts\architecture_audit.py
python scripts\run_static_analysis.py
python -m unittest discover -s tests -t .
```

Se `pytest` estiver instalado e houver suite pytest declarada, executar tambem:

```powershell
python -m pytest
```

## Registro Obrigatorio

Cada missao deve registrar:

- inicio;
- termino;
- duracao;
- status;
- commit;
- branch;
- responsavel;
- missao.
