# TraderIA Novo - System Flow

Este documento e o mapa operacional vivo do TraderIA Novo. Ele registra como o
sistema funciona hoje para que futuras missoes via GPT/Codex respeitem a
operacionalidade atual.

## Objetivo operacional

O TraderIA Novo opera como plataforma local de leitura Forex MT5, pesquisa de
setups no Lab, visualizacao no MetaTrader 5 e auditoria em relatorios. O estado
operacional atual deve ser preservado: app local funcionando, MT5 em leitura
direta, Lab sob demanda e ciclo leve Forex sem recalculo pesado automatico.

## Fluxo principal

```text
MetaTrader 5
  |
  | leitura read-only de candles, precos, posicoes e historico
  v
application/mt5_market_data_service.py
  |
  v
application/dashboard_service.py
  |
  +--> Aba Forex MT5: leitura leve online com parametros do Lab
  |
  +--> Aba Lab: baixa historico MT5 e calcula Alpha001-Alpha015 sob demanda
  |
  +--> Aba Relatorio: audita registros locais contra historico MT5
  |
  +--> Exportador visual MT5: gera JSON para indicador MQL5
            |
            v
        mt5/indicators/TraderIAVisualSignals.mq5
```

## Autoridades do sistema

| Decisao | Autoridade atual | Observacao |
| --- | --- | --- |
| Preco atual | MT5 | Lido por `MT5MarketDataService`. |
| Candles de pesquisa | Lab via MT5 | Baixados por `update_mt5_research_history`. |
| Timeframe vencedor | Lab | Consumido pelo Forex no proximo ciclo leve. |
| Alpha/setup vencedor | Lab | Gravado no snapshot local do Lab. |
| Entrada teorica | Lab + leitura Forex | O Forex aplica parametros do Lab no dado atual. |
| Stop/saida | Lab | Transportado pelo trade plan e visual. |
| Posicao aberta | MT5 | Usada para visual e relatorio. |
| Execucao demo | Politica demo local | Nao e operacao real. |
| Operacao real | Bloqueada | Nao usar `order_send()` sem decisao formal. |

## Artefatos locais importantes

Estes arquivos sao runtime local e nao devem ser tratados como fonte de verdade
do GitHub:

```text
.traderia/mt5_research_history_snapshot.json
.traderia/traderia_mt5_history.sqlite
.traderia/mt5_research_snapshot.json
.traderia/mt5_demo_execution.jsonl
traderia_visual_signals.json em MQL5/Files
```

O GitHub deve guardar codigo, contratos, governanca, templates e documentacao,
mas nao snapshots pesados, logs, bancos locais, credenciais ou PID.

## Estado ideal a preservar

- App local TraderIA Novo abre em `http://localhost:8532`.
- A aba Forex MT5 faz leitura leve, online e sem recalculo pesado do Lab.
- A aba Lab atualiza historico e calculos somente quando acionada.
- O Lab avalia multiplos timeframes configurados, nao força tudo para M1.
- O Forex usa parametros consolidados do Lab por par/timeframe.
- O visual no MT5 evita poluir graficos sem posicao aberta.
- A aba Relatorio audita posicoes/execucoes sem participar de envio real.
- Mudancas operacionais entram por `codex/inbox` com criterio de aceite e
  rollback.

## Fontes de codigo primarias

| Area | Arquivo |
| --- | --- |
| UI Streamlit | `dashboard_app.py` |
| Orquestracao de aplicacao | `application/dashboard_service.py` |
| Leitura MT5 | `application/mt5_market_data_service.py` |
| Exportacao visual | `application/mt5_visual_signal_exporter.py` |
| Resolucao de caminho MT5 | `infrastructure/mt5_visual_signal_path_resolver.py` |
| Plano de trade Lab | `research/mt5_research_trade_plan.py` |
| Indicador MT5 | `mt5/indicators/TraderIAVisualSignals.mq5` |

## Documentos complementares

- `docs/APP_TABS_FLOW.md`
- `docs/ALPHA_TRACEABILITY.md`
- `docs/SETUP_LOGIC_TRACEABILITY.md`
- `docs/OPERATIONAL_GUARDRAILS.md`
- `docs/CHANGE_PROTOCOL.md`
- `docs/LAB_FOREX_MT5_CONTRACT.md`
- `docs/MT5_VISUAL_SIGNAL_CONTRACT.md`
- `governance/traceability/TRACEABILITY_INDEX.md`
- `governance/traceability/TRACEABILITY_MATRIX.md`
