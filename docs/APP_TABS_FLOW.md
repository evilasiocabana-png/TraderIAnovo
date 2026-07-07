# TraderIA Novo - Fluxo das Abas

Este documento explica como as abas principais se comunicam. Ele deve ser lido
antes de qualquer missao que altere Forex, Lab, Relatorio, MT5 ou exportacao
visual.

## Abas principais

O layout principal em `dashboard_app.py` seleciona:

```text
MT5 Forex
Laboratorio de Pesquisa
Replay
Historico MT5
Relatorios
Sistema Forex
```

As tres abas criticas para a operacao atual sao `MT5 Forex`, `Laboratorio de
Pesquisa` e `Relatorios`.

## Aba MT5 Forex

Responsabilidade:

- carregar leitura leve do MT5;
- aplicar timeframe e parametros vencedores vindos do Lab;
- manter o ciclo online leve;
- exportar sinais visuais para o MT5;
- permitir armar/desarmar robo demo conforme politica local.

Chamadas centrais:

```text
dashboard_app.py
  _load_mt5_forex_signals_locked()
  exibir_mt5_forex_dashboard()

application/dashboard_service.py
  load_mt5_forex_signals()
  _mt5_lab_timeframes_by_pair()
  _auto_export_mt5_visual_signals()
  run_online_demo_robot_cycle()
```

Regra de governanca:

O Forex nao deve recalcular Lab pesado no ciclo leve. Ele consome o snapshot
consolidado do Lab e atualiza somente a leitura de mercado.

## Aba Laboratorio de Pesquisa

Responsabilidade:

- baixar historico MT5 sob demanda;
- salvar banco/snapshot local do historico;
- recalcular biblioteca Alpha001-Alpha015 sob demanda;
- consolidar setup, timeframe, direcao, parametros e stop management por par;
- expor recomendacoes para o Forex.

Chamadas centrais:

```text
dashboard_app.py
  exibir_research_lab()
  exibir_research_lab_actions()
  exibir_mt5_setup_suggestions()
  exibir_mt5_alpha_research_report()

application/dashboard_service.py
  update_mt5_research_history()
  _update_mt5_research_history()
  update_mt5_research_calculations()
  _update_mt5_research_calculations()
  suggest_mt5_lab_setups()
```

Fluxo correto:

```text
1. Atualizar historico MT5
2. Atualizar calculos
3. Conferir setups sugeridos
4. Forex MT5 passa a consumir a configuracao consolidada
```

Regra de governanca:

O Lab e pesado e deve ser acionado por botao/missao especifica. Nao deve rodar a
cada ciclo do Forex.

## Aba Relatorios

Responsabilidade:

- confrontar registros locais do TraderIA com historico MT5;
- mostrar status de auditoria;
- acompanhar operacao/posicoes sem recalcular Lab;
- permitir armar todos a partir da visao de relatorio, usando a mesma politica
  da aba Forex.

Chamadas centrais:

```text
dashboard_app.py
  exibir_relatorios_dashboard()
  _arm_all_demo_robot_from_reports()

application/dashboard_service.py
  get_mt5_trade_audit_report()
  _load_mt5_trade_history()
  _read_mt5_demo_execution_jsonl()
```

Regra de governanca:

Relatorio e somente leitura/auditoria. Nao deve virar fonte de decisao do Lab e
nao deve alterar parametros de Alpha/setup.

## Comunicacao entre abas

```text
Lab
  gera snapshot consolidado
  |
  v
DashboardService.get_mt5_research_constants()
  |
  +--> Forex MT5 usa timeframe/setup/saida por par
  |
  +--> Relatorio mostra auditoria e contexto operacional
  |
  +--> Exportador visual gera JSON para MT5
```

## Onde uma melhoria deve declarar impacto

Toda missao GPT/Codex deve declarar uma destas areas:

- `TAB_FOREX_MT5`
- `TAB_LAB`
- `TAB_RELATORIO`
- `MT5_VISUAL`
- `ALPHA_LIBRARY`
- `SETUP_LOGIC`
- `GOVERNANCE_ONLY`

Missoes de uma area nao devem alterar outra sem autorizacao explicita.
