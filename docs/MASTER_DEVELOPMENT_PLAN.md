# Master Development Plan

## Direcao Geral

TraderIA Novo deve evoluir como produto local com governanca GitHub. O foco e
estabilizar as tres abas principais antes de qualquer expansao:

1. MT5 Forex
2. Lab
3. Relatorios

## Fase 1 - Estabilizacao Operacional

Objetivo: deixar a copia GitHub local funcionando sem dependencia do TraderIA
antigo.

Entregas:

- app Streamlit em `localhost:8532`;
- nome visual `TraderIA Novo`;
- Lab usando `.traderia/` local;
- Relatorios carregando auditoria local;
- MT5 Forex sem ciclo automatico bloqueante;
- GitHub atualizado.

Status: em execucao.

## Fase 2 - Contratos E Dados Locais

Objetivo: transformar os arquivos locais em contratos claros.

Entregas:

- contrato do snapshot do Lab;
- contrato do banco SQLite local;
- contrato do JSON visual MT5;
- validadores de integridade;
- mensagens de UI claras quando dados locais estiverem ausentes.

## Fase 3 - Performance E Robustez

Objetivo: reduzir travamentos e leituras MT5 longas.

Entregas:

- leitura por snapshot/cache na abertura;
- atualizacoes pesadas somente sob demanda;
- timeout e preservacao do ultimo historico valido;
- telemetria simples de tempo por etapa;
- logs locais organizados em `.traderia/`.

## Fase 4 - Governanca Inbox

Objetivo: permitir desenvolvimento continuo com missoes.

Entregas:

- `codex/inbox`;
- criterios de aceite por missao;
- relatorio de execucao;
- atualizacao de `docs/NEXT_MISSION.md`;
- registro em `docs/EXECUTION_LOG.md`.

## Fase 5 - Expansao Controlada

So deve comecar depois da estabilizacao das abas principais.

Possiveis trilhas:

- indicadores visuais MT5 mais limpos;
- gestao de stop movel por setup/timeframe;
- melhoria do banco local do Lab;
- testes automatizados por contrato;
- dashboard de saude operacional.

## Politica De Branch/Commit

- `main` deve conter estado funcional.
- Commits devem ser pequenos e descritivos.
- Mudancas com risco operacional devem ter ponto de restauracao ou commit claro.
- Artefatos locais nunca entram no Git.

## Validacao Padrao

Minimo:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m py_compile dashboard_app.py application\dashboard_service.py
```

Quando a mudanca tocar Lab, Forex ou Relatorios, rodar teste funcional isolado
pelo respectivo service.

