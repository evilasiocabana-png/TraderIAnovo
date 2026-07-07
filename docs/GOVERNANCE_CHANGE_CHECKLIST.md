# Checklist de Mudanca Segura

Este checklist deve ser usado antes de alterar fluxo operacional, Lab, Forex,
MT5, dashboard ou arquivos de runtime.

## Regra base

Nao mudar o local de trabalho atual:

```text
C:\Users\evcab\OneDrive\Documentos\TraderIA_WDO
```

Mudancas devem ser pequenas, testaveis e reversiveis.

## Antes de alterar

- Confirmar branch de trabalho diferente de `main`.
- Ler o documento relacionado ao fluxo afetado.
- Identificar se a mudanca toca:
  - Lab;
  - Forex;
  - MT5;
  - Dashboard;
  - JSON visual;
  - runner externo;
  - dados operacionais.
- Confirmar se algum arquivo ignorado pelo Git sera necessario para teste.
- Evitar mexer em `.traderia/`, `Python/`, logs, banco local ou snapshots.

## Durante a alteracao

- Fazer uma mudanca por vez.
- Evitar refatoracao misturada com correcao de bug.
- Preservar contratos publicos ja usados pelo dashboard e pelo MT5.
- Nao mover arquivos fisicamente sem uma tarefa propria.
- Se alterar saida visual, validar o contrato JSON antes do MT5.
- Se alterar Lab, validar entrada, setup, timeframe e stop/saida.

## Validacao minima

Para mudancas pequenas em Lab, Forex ou MT5:

```powershell
python -m py_compile dashboard_app.py application\dashboard_service.py application\mt5_market_data_service.py application\mt5_visual_signal_exporter.py application\dashboard_view_model.py research\mt5_research_trade_plan.py scripts\mt5_forex_cycle_runner.py infrastructure\market_data\mt5_market_data_provider.py
```

Para mudancas no indicador MT5:

- Confirmar que `mt5/indicators/TraderIAVisualSignals.mq5` continua como fonte.
- Compilar no MetaEditor quando a mudanca for de MQL5.
- Confirmar que o `.ex5` compilado nao entra no Git.

Para mudancas visuais no dashboard:

- Subir Streamlit localmente.
- Confirmar que as abas nao duplicam estado.
- Confirmar que relatorio e Forex atualizam no ciclo esperado.

## Antes do commit

- Rodar `git status --short`.
- Conferir que nao entraram:
  - `.traderia/`;
  - `Python/`;
  - logs;
  - `.pid`;
  - `.db`;
  - snapshots grandes;
  - credenciais reais;
  - `.ex5`.
- Escrever mensagem de commit clara.
- Fazer push da branch, nao direto na `main`, quando houver risco.

## Rollback

Pontos de retorno:

- Tag Git: `baseline-20260706`.
- Backup local: `.traderia/restore_points/20260706_github_migration_audit_baseline`.

Para voltar ao baseline pelo Git:

```powershell
git checkout baseline-20260706
```

Usar rollback local por ZIP somente quando a restauracao por Git nao for
suficiente.
