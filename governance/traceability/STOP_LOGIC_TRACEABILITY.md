# Stop Logic Traceability

Missao: `MISSION_TIA-004_ANALISAR_STOPS_MOVEIS`

Data: 2026-07-07

## Trilha Oficial

```text
Alpha/setup
  -> parametros do Lab
  -> stop_management
  -> MT5ResearchTradePlan
  -> Dashboard Forex MT5
  -> JSON visual MT5
  -> indicador TraderIAVisualSignals.mq5
  -> provider demo aplica SL/TP quando suportado
  -> Relatorio/auditoria
```

## Fonte de Verdade por Camada

| Camada | Arquivos | Responsabilidade |
| --- | --- | --- |
| Catalogo | `research/stop_management_catalog.py`, `research/mt5_research_trade_plan.py` | Lista politicas aceitas e parametros permitidos. |
| Lab/Pesquisa | `application/dashboard_service.py` | Expande grade, pontua saida, escolhe parametros por Alpha/setup/timeframe. |
| Plano | `research/mt5_research_trade_plan.py` | Normaliza politica, calcula entrada/stop/alvo/RR e transporta saida. |
| Forex | `application/forex_mt5_service.py`, `application/dashboard_service.py` | Exibe leitura leve e carrega plano recomendado. |
| Exportacao MT5 | `application/mt5_visual_signal_exporter.py` | Escreve `stop_management` e parametros no JSON do indicador. |
| Indicador MT5 | `mt5/indicators/TraderIAVisualSignals.mq5` | Mostra saida no grafico e limita texto conforme estado da posicao. |
| Execucao Demo | `infrastructure/execution/mt5_demo_execution_provider.py` | Envia ordens demo e aplica gestao de SL/TP quando a politica e suportada. |
| Relatorio | `application/report_service.py`, `application/mt5_trade_audit_service.py` | Audita status, sem decidir entrada ou saida. |

## Politicas Canonicas

| Politica | Status no Lab | Status no JSON/MT5 visual | Status na gestao demo |
| --- | --- | --- | --- |
| `FIXED_STOP` | Avaliada | Exportada | Nao move SL/TP apos entrada. |
| `ATR_TRAILING_STOP` | Avaliada | Exportada | Implementada. |
| `BREAK_EVEN` | Avaliada | Exportada | Implementada. |
| `CHANDELIER_EXIT` | Avaliada | Exportada | Ainda nao implementada no provider demo. |
| `PARABOLIC_SAR` | Avaliada | Exportada | Ainda nao implementada no provider demo. |
| `DONCHIAN_CHANNEL_STOP` | Avaliada | Exportada | Ainda nao implementada no provider demo. |
| `MOVING_AVERAGE_EXIT` | Avaliada | Exportada | Ainda nao implementada no provider demo. |
| `TIME_STOP` | Avaliada | Exportada | Ainda nao implementada no provider demo. |
| `VOLATILITY_STOP` | Avaliada | Exportada | Ainda nao implementada no provider demo. |

## Normalizacao de Nomes

| Nome citado | Nome canonico recomendado | Observacao |
| --- | --- | --- |
| `TRAILING_STOP` | `ATR_TRAILING_STOP` | O trailing atual e baseado em ATR. |
| `TIME_EXIT` | `TIME_STOP` | O contrato atual usa saida por tempo como stop management. |

## Pontos de Decisao

### Entrada

A entrada teorica e decidida por Alpha/setup e regime de mercado no Lab. A regra
operacional desejada permanece: entrar na zona de interesse quando houver sinal
autorizado e nao houver posicao aberta no mesmo papel.

### Saida

A saida e escolhida no Lab pela combinacao:

- Alpha/setup;
- timeframe;
- parametros da grade;
- ajuste de politica de stop;
- evidencia historica leve;
- contexto temporal;
- certificacao.

O plano final carrega `stop_management` e `stop_management_parameters`.

### MT5

O MT5 nao deve escolher politica sozinho. Ele consome o JSON exportado e, na
execucao demo, so deve mover SL/TP quando:

- existe posicao aberta;
- existe sinal correspondente ao simbolo;
- a politica e suportada pelo provider;
- o novo stop melhora a protecao;
- o novo stop fica antes do mercado.

## Por Que o BREAK_EVEN Pode Dominar

`application/dashboard_service.py` favorece `BREAK_EVEN` em baixa volatilidade e
simula reducao de perdas mais agressiva do que outras politicas. Isso pode
melhorar a metrica de protecao, especialmente quando os retornos futuros sao
fracos ou laterais. A contrapartida e capturar menos ganho quando o movimento
continua.

## Guardrails para Proximas Missoes

- Nao trocar nomes de politicas sem atualizar contrato, exportacao, MQL5, testes
  e rastreabilidade.
- Nao fazer o Relatorio decidir saida.
- Nao deixar o MT5 recalcular Lab pesado.
- Nao aplicar gestao real para politica sem teste especifico no provider demo.
- Nao misturar mudanca visual com mudanca de regra operacional na mesma missao.

## Proxima Missao

`MISSION_TIA-005_PROJETAR_SAIDA_DINAMICA_BASEADA_EM_LEITURA_DE_MERCADO`

Entrega esperada:

- desenho tecnico da saida dinamica por leitura de mercado;
- matriz politica -> condicao de mercado -> acao;
- impactos em Lab, Forex, MT5 visual, provider demo e relatorio;
- criterios de aceite antes de qualquer codigo operacional.
