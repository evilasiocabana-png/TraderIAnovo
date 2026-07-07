# DASHBOARD_REALITY_ALIGNMENT.md

## Missao 220 - Dashboard Reality Alignment

Sprint 14 - TraderIA UX Consolidation  
Projeto: TraderIA  
Data: 2026-06-28

## Objetivo

Mapear o Dashboard visual e classificar cada painel conforme sua aderencia ao estado real da plataforma.

## Classificacao

| Area | Classificacao | Observacao |
| --- | --- | --- |
| Home | REAL | Exibe dataset ativo e status via `DashboardService`. |
| Dataset Ativo | REAL | Usa `HistoricalDataProvider`, `metadata.json` e `checksum.sha256` pela camada application. |
| Replay | REAL | Carrega dataset selecionado e executa candles reais. |
| Market DNA | PARCIAL | Agora so exibe leitura alinhada ao candle atual do Replay; antes do Replay informa ausencia de dado real. |
| Research Lab | PARCIAL | Executa dataset real, mas PETR4 ainda nao possui Alpha propria; sem experimento mostra mensagem clara. |
| Estrategias | PARCIAL | Exibe runtime da strategy carregada e ultima decisao, mas ainda nao e um gestor completo de estrategias. |
| Eventos | REAL | Exibe eventos reais recentes emitidos pelo Replay/EventBus com timestamp. |
| Sistema | REAL | Exibe dataset, Replay, Research, eventos e sessao pela fachada de aplicacao. |
| `app.py` | LEGADO | Runner demonstrativo/legado, nao e a aplicacao visual oficial. |
| `dashboard_app.py` | REAL | Aplicacao visual oficial em Streamlit. |

## Inconsistencias Corrigidas

- Replay visual deixou de expor acao principal de demo.
- Research Lab deixou de mostrar botoes de experimento demo.
- Market DNA deixou de mostrar painel desalinhado quando nao ha Replay real.
- Eventos deixaram de ser placeholder.
- Strategy Runtime deixou de ser mensagem futura.
- Sistema ganhou runtime institucional.

## Riscos de Interpretacao

- PETR4 e dataset de pesquisa, nao ativo operacional.
- WDO permanece ativo operacional configurado.
- Research com PETR4 ainda e smoke tecnico enquanto nao houver Alpha compativel.
- Operacao real permanece proibida.

## Prioridade de Correcao

1. Replay real.
2. Research real sem demo.
3. Market DNA alinhado ao Replay.
4. EventBus visivel.
5. Polish e certificacao.

## Resultado

Dashboard classificado e alinhado para orientar as missoes 221 a 228.
