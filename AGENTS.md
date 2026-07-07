# AGENTS.md

## Projeto

TraderIA Novo e a copia operacional versionada no GitHub do sistema TraderIA.
O repositorio contem codigo, testes, documentacao e governanca. O runtime real
do MT5 e os resultados pesados do Lab ficam localmente em `.traderia/` e nao
devem ser versionados.

## Regra Principal Para Agentes

Antes de alterar codigo, leia:

1. `docs/PROJECT_CHARTER.md`
2. `docs/ARCHITECTURE.md`
3. `docs/MASTER_DEVELOPMENT_PLAN.md`
4. `docs/ACCEPTANCE_CRITERIA.md`
5. `docs/NEXT_MISSION.md`

Depois execute a menor mudanca possivel, valide, registre em
`docs/EXECUTION_LOG.md` quando a mudanca for relevante e faca commit/push.

## Limites Operacionais

- Nao mover a pasta local do projeto.
- Nao versionar `.traderia/`, `Python/`, logs, `.pid`, bancos locais,
  snapshots grandes, credenciais ou compilados MT5.
- Nao reativar ciclos automaticos bloqueantes no MT5 Forex.
- Nao depender de `TraderIA_WDO` para o Lab da TraderIA Novo.
- Nao enviar ordem real pelo indicador visual MT5.
- Toda execucao MT5 deve respeitar modo demo/read-only salvo quando uma missao
  explicita mudar esse contrato.

## Arquitetura De Trabalho

- UI: `dashboard_app.py`
- Fachada da aplicacao: `application/dashboard_service.py`
- Contratos de tela: `application/dashboard_view_model.py`
- Lab: `research/`, `application/research_lab_service.py` e estado local em
  `.traderia/`
- MT5: `application/mt5_market_data_service.py`, `infrastructure/mt5/` e
  providers em `infrastructure/`
- Execucao demo: `application/mt5_demo_robot_service.py` e
  `infrastructure/execution/`
- Governanca: `codex/`, `governance/`, `docs/`

## Como Rodar

App local da TraderIA Novo:

```powershell
python -m streamlit run dashboard_app.py --server.port 8532 --server.headless true
```

Configuracao recomendada da sessao:

```powershell
$env:TRADERIA_APP_TITLE='TraderIA Novo'
$env:TRADERIA_FAST_BOOT_ENABLED='0'
$env:TRADERIA_MT5_FOREX_AUTO_CYCLE_ENABLED='0'
$env:TRADERIA_MT5_INITIAL_LOAD_ENABLED='0'
$env:TRADERIA_MT5_REPORT_FORCE_LOAD_ENABLED='0'
$env:TRADERIA_MT5_LAB_ALLOW_LIVE_RECALC='0'
```

## Validacao Minima

Antes de entregar mudanca de codigo:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m py_compile dashboard_app.py application\dashboard_service.py
```

Quando aplicavel, execute testes focados em `tests/`.

## Politica Do Lab

O motor do Lab roda localmente na propria TraderIA Novo. Resultados ficam em:

```text
.traderia/mt5_research_snapshot.json
.traderia/mt5_research_history_snapshot.json
.traderia/traderia_mt5_history.sqlite
```

O GitHub recebe o codigo que sabe ler/atualizar esses arquivos, nao os arquivos
pesados em si.

## Politica Do MT5 Forex

A aba MT5 Forex deve abrir rapida, usando o ultimo estado local/snapshot.
Atualizacoes bloqueantes por ciclo nao devem ser reintroduzidas na tela.

## Politica Da Aba Relatorios

A aba Relatorios carrega auditoria local uma vez, guarda cache de sessao e
atualiza somente pelo botao `Atualizar auditoria MT5`.

