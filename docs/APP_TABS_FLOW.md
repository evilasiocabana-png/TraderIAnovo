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

Regra operacional do Robo Demo:

Quando o robo demo estiver online, a entrada automatica pertence ao ciclo de
fundo do TraderIA Novo. A interface Streamlit deve apenas exibir o estado,
permitir armar/desarmar e permitir avaliacao manual explicita. A renderizacao
da aba `MT5 Forex` ou da aba `Relatorios` nao deve disparar uma segunda entrada
automatica, pois isso pode gerar duplicidade de tentativa no mesmo candle.

O ciclo de fundo deve:

- ler `.traderia/mt5_demo_robot_online_state.json`;
- respeitar o horario/feriado Forex;
- respeitar a selecao operacional persistida em `.traderia/mt5_operational_model.json`;
- chamar `run_online_demo_robot_cycle()` em intervalo leve;
- registrar heartbeat em `.traderia/mt5_demo_robot_background_state.json`;
- deixar a UI como camada de visualizacao, nao como motor automatico de entrada.

Limite de operacoes:

Por padrao o TraderIA Novo nao usa limite diario de quantidade de trades demo
(`TRADERIA_DEMO_MAX_TRADES=0`). O valor `0` significa sem limite. Caso seja
necessario impor teto operacional no futuro, configurar
`TRADERIA_DEMO_MAX_TRADES` com numero maior que zero. As travas por par/modelo
continuam ativas para impedir empilhamento indevido no mesmo ativo.

Regra de modelos simultaneos:

Quando a opcao `TODOS_MODELOS` estiver ativa, o ciclo deve avaliar Modelo 1 e
Modelo 2 no mesmo ciclo, sem prioridade artificial. Se ambos estiverem prontos,
ambos podem enviar ordem, respeitando a trava de no maximo uma posicao por
modelo no mesmo par. O Modelo 2 e uma regra espelhada: usa plano valido do Lab,
exige ADX < 20, inverte BUY/SELL, usa TP no stop original da Alpha/BETA2 e stop
em RR1. Por ser espelhado, ele nao deve ser bloqueado pelo regime direcional do
Modelo 1 depois que seu proprio filtro ADX ja autorizou a entrada.

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

Regra adicional:

Se o Robo Demo estiver online, a aba `Relatorios` tambem nao deve disparar ciclo
automatico proprio. Ela consome o estado produzido pelo ciclo de fundo e mostra
auditoria/posicoes. Isso permite acompanhar resultados sem precisar manter a aba
`MT5 Forex` aberta e evita concorrencia entre UI e background.

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
