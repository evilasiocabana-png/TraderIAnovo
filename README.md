# TraderIA

TraderIA e um sistema local de pesquisa, leitura de mercado, dashboard Streamlit
e integracao operacional com MetaTrader 5.

Este repositorio foi organizado para documentar e versionar o codigo sem mudar o
local de trabalho atual:

```text
C:\Users\evcab\OneDrive\Documentos\TraderIA_WDO
```

## Documentos principais

- [Leia Primeiro - Ultimo Inbox](000_READ_FIRST_LATEST_INBOX_RESULT.md)
- [Ultimo Resultado do Inbox](LATEST_INBOX_RESULT.md)
- [Status para GPT](docs/GPT_SYNC_STATUS.md)
- [Mapa do Projeto](docs/PROJECT_MAP.md)
- [Runtime e Artefatos Locais](docs/RUNTIME_AND_ARTIFACTS.md)
- [Fluxo Lab, Forex e MT5](docs/LAB_FOREX_MT5_FLOW.md)
- [Contrato Lab, Forex e MT5](docs/LAB_FOREX_MT5_CONTRACT.md)
- [Runbook Operacional MT5 Research](docs/MT5_RESEARCH_OPERATION_RUNBOOK.md)
- [Contrato do JSON Visual MT5](docs/MT5_VISUAL_SIGNAL_CONTRACT.md)
- [Pipeline CI Critico](docs/CI_PIPELINE.md)
- [TraderIA Nuvem no GitHub Codespaces](docs/CODESPACES_RUNBOOK.md)
- [Checklist de Mudanca Segura](docs/GOVERNANCE_CHANGE_CHECKLIST.md)
- [Plano de Migracao e Organizacao](docs/MIGRATION_PLAN.md)
- [Catalogo de Datasets Historicos](docs/HISTORICAL_DATASET_CATALOG.md)
- [Auditoria de Stops Moveis](docs/MOBILE_STOPS_ANALYSIS.md)
- [Rastreabilidade de Stops](governance/traceability/STOP_LOGIC_TRACEABILITY.md)

## Como rodar localmente

O app principal continua sendo executado localmente:

```powershell
python -m streamlit run dashboard_app.py --server.port 8501 --server.headless true
```

O ciclo leve Forex/MT5 fica em:

```powershell
python scripts\mt5_forex_cycle_runner.py
```

Validacao critica local:

```powershell
python scripts\run_critical_ci.py
```

## Como trabalhar na nuvem

Abra o repositorio no GitHub Codespaces:

```text
https://github.com/evilasiocabana-png/TraderIA
```

No Codespaces, rode:

```bash
streamlit run dashboard_app.py --server.port 8530 --server.headless true
```

Na nuvem o app aparece como `TraderIA Nuvem`. A integracao real com MT5 continua
local, pois depende do MetaTrader 5 aberto nesta maquina.

## Politica do repositorio

O GitHub deve conter codigo, testes, documentacao e templates fonte.

Nao devem entrar no Git:

- `Python/`
- `.traderia/`
- logs e arquivos `.pid`
- snapshots grandes
- bancos locais `.db`
- credenciais reais
- backups `.zip`
- compilados MT5 `.ex5`

O baseline local e remoto foi marcado com a tag:

```text
baseline-20260706
```

## Restauracao

Existem dois pontos de seguranca:

1. Git tag `baseline-20260706`.
2. Ponto de restauracao local em `.traderia/restore_points/20260706_github_migration_audit_baseline`.

Nenhuma reorganizacao fisica de pastas deve ser feita sem uma etapa propria,
validacao e commit separado.
