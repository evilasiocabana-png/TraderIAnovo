# Fluxo Lab, Forex e MT5

Este documento descreve o fluxo operacional atual sem alterar a estrutura local.

Contratos complementares:

- [Contrato Lab, Forex e MT5](LAB_FOREX_MT5_CONTRACT.md)
- [Runbook Operacional MT5 Research](MT5_RESEARCH_OPERATION_RUNBOOK.md)
- [Contrato do JSON Visual MT5](MT5_VISUAL_SIGNAL_CONTRACT.md)
- [Checklist de Mudanca Segura](GOVERNANCE_CHANGE_CHECKLIST.md)

## Visao geral

```text
Research Lab / Snapshot
        |
        v
DashboardService
        |
        +--> MT5MarketDataService / MT5 provider
        |
        +--> Dashboard ViewModel / Streamlit
        |
        +--> MT5VisualSignalExporter
                    |
                    v
        traderia_visual_signals.json
                    |
                    v
        TraderIAVisualSignals.mq5 no MetaTrader 5
```

## Responsabilidades

| Parte | Responsabilidade |
|---|---|
| Research Lab | Define parametros, setup, timeframe, entrada teorica, stop/saida e modelo. |
| Forex/MT5 cycle | Faz leitura leve do MT5 e aplica parametros ja definidos pelo Lab. |
| DashboardService | Orquestra leitura, view model, exportacao visual e auditoria operacional. |
| MT5MarketDataService | Le candles, precos e dados de mercado do MetaTrader 5. |
| MT5VisualSignalExporter | Escreve o JSON consumido pelo indicador MT5. |
| TraderIAVisualSignals.mq5 | Desenha sinais, linhas e textos no grafico do MT5. |

## Research MT5 em duas etapas

O Research MT5 foi separado em duas acoes para evitar travamento e recalculo
pesado durante o refresh leve:

| Acao | O que faz | O que nao faz |
|---|---|---|
| Atualizar historico MT5 | Baixa candles do MT5 e salva `.traderia/mt5_research_history_snapshot.json`. | Nao recalcula Alpha001-Alpha015 e nao envia ordens. |
| Atualizar calculos | Recalcula o Lab usando o historico salvo quando disponivel. | Nao baixa historico pesado a cada ciclo e nao envia ordens. |

O ciclo leve Forex/MT5 deve usar parametros ja definidos pelo Lab. Ele nao deve
executar pesquisa pesada automaticamente.

## Timeframe

O timeframe decisor vem do Lab por ativo/setup. O grafico aberto no MT5 pode ter
outro timeframe, mas o sistema deve preservar o timeframe definido pelo Lab como
fonte de decisao.

## Entrada

A entrada deve ser autorizada quando o ativo estiver em zona de interesse e nao
houver posicao aberta conflitante naquele papel. A logica de entrada nao deve
depender apenas de uma virada generica; ela deve respeitar o contrato vindo do
Lab.

## Saida e stops moveis

Os tipos de stop/saida conhecidos no contrato atual sao:

- `FIXED_STOP`
- `ATR_TRAILING_STOP`
- `BREAK_EVEN`
- `CHANDELIER_EXIT`
- `PARABOLIC_SAR`
- `DONCHIAN_CHANNEL_STOP`
- `MOVING_AVERAGE_EXIT`
- `TIME_STOP`
- `VOLATILITY_STOP`

A melhor saida deve vir do Lab por ativo, setup e timeframe, assim como a
entrada.

## Ciclos operacionais

Existem dois pontos que podem disparar leitura/exportacao:

- Streamlit em `dashboard_app.py`.
- Runner externo em `scripts/mt5_forex_cycle_runner.py`.

Antes de refatorar, deve-se documentar qual deles e a autoridade em cada
cenario para evitar escrita duplicada ou diagnosticos confusos.

## Arquivo visual MT5

O indicador MT5 le:

```text
traderia_visual_signals.json
```

O caminho e resolvido por `infrastructure/mt5_visual_signal_path_resolver.py`.

## Regra de estabilidade

Mudancas nessa cadeia precisam de teste/validacao em tres pontos:

1. Python compila e gera view model correto.
2. JSON visual e escrito no caminho esperado.
3. MT5 desenha somente o que deve aparecer no grafico.
