# Paridade Operacional Dos Modelos Do Lab No MT5

Data da certificacao: 2026-07-22
Ambiente autorizado: MT5 Demo
Conta real: bloqueada

## Decisao

Os planos pesquisados no Lab passam a ser os modelos operacionais M2, M3, M4
e M5. O M1 continua sendo o vencedor canonico do Research Lab. Nao existe um
segundo modelo operacional chamado M5-P: o antigo consolidado de pesquisa foi
promovido e agora se chama somente M5. O M6 permanece inativo e fora do
seletor, do modo Todos e do envio.

O manifesto versionado que congela essa promocao e:

`research/alpha_suggested/lab_operational_models_manifest.json`

A decisao operacional posterior de liberar todos os pares em ambiente Demo fica
versionada separadamente em:

`research/alpha_suggested/lab_demo_forward_policy.json`

Essa politica nao apaga a auditoria estatistica. Cada linha preserva os campos
`evidence_demo_forward_enabled`, `evidence_parity_status` e
`evidence_parity_reason`, enquanto `demo_forward_enabled` representa a decisao
operacional vigente. A politica nao autoriza conta real.

## Contrato Comum M2-M5

- sinal calculado somente no ultimo candle fechado;
- entrada solicitada no proximo preco vivo, por no maximo 120 segundos;
- Alpha, familia, timeframe, filtros, sessao, dias, ATR, stop e RR sao os do
  artefato de pesquisa;
- SL e TP nascem fixos com `RESEARCH_FIXED_SL_TP`;
- o Position Manager acompanha e audita, mas nao move SL nem executa
  `FULL_EXIT` nesses planos;
- somente linhas com `demo_forward_enabled=true` podem chegar ao Robo Demo;
- linha bloqueada permanece visivel para auditoria, mas retorna `WAIT`;
- modelos sao independentes; falha de um nao cancela outro;
- um mesmo plano exato no mesmo candle nao pode ser duplicado entre modelos;
- toda execucao permanece Demo. Conta real continua proibida.

## Matriz Operacional

| Modelo | ID operacional | Pares habilitados | Timeframes | Saida |
|---|---|---|---|---|
| M1 | `MODELO_1_ALPHA_ATUAL` | 8 pares do snapshot vigente | TF vencedor por par, atualmente H1 | Plano do Lab |
| M2 | `MODELO_2_LAB_ALPHA_SUGERIDA_1_PLUS` | 8 pares | H1 | SL/TP fixos pesquisados |
| M3 | `MODELO_3_LAB_ALPHA_SUGERIDA_2_PLUS` | 8 pares | M30 e H1 por par | SL/TP fixos pesquisados |
| M4 | `MODELO_4_LAB_CONTEXTUAL_MTF` | 8 pares | M30 com contexto H1/H4 | SL/TP fixos pesquisados |
| M5 | `MODELO_5_LAB_CONSOLIDADO` | 8 pares | M30/H1 conforme vencedor | SL/TP fixos pesquisados |
| M6 | inativo | nenhum | nenhum | nenhum |

USDCAD e USDJPY no M5 delegam ao vencedor M1 congelado no consolidado. Quando
M1 e M5 gerarem o mesmo plano no mesmo candle, a deduplicacao permite apenas
uma abertura.

## Gates Antes Do Envio

Uma ordem Demo so pode ser solicitada depois de todos estes pontos:

1. modelo selecionado ou incluido em Todos;
2. par habilitado no manifesto;
3. candles e indicadores do TF exigido disponiveis;
4. sinal novo no ultimo candle fechado;
5. janela de entrada de 120 segundos ainda valida;
6. plano com direcao, entrada, SL, TP e volume validos;
7. ausencia de duplicata do mesmo plano/candle;
8. mercado Forex fora de fim de semana e rollover;
9. terminal conectado, negociacao algoritmica permitida e conta Demo;
10. ausencia de posicao duplicada daquele modelo no par.

A preferencia de sessao da Alpha e avaliada pelo proprio motor. O filtro geral
de sessao pode continuar opcional, mas fim de semana, domingo antes da abertura,
sexta no fechamento e rollover sao bloqueios duros e nao podem ser ignorados.

## Dados E Performance

O calculo historico pesado continua sob demanda no Lab. O runtime nao recalcula
5.000 candles a cada ciclo. Para os modelos ativos, o cache suplementar carrega
uma janela inicial suficiente para os indicadores e depois atualiza somente os
candles recentes:

- M30: cache por 10 segundos;
- H1: cache por 30 segundos;
- H4: cache por 60 segundos.

O M4 recebe contexto H1/H4 causal. Ausencia de qualquer serie necessaria gera
`MARKET_DATA_UNAVAILABLE`, nunca um fallback silencioso.

## Auditoria Do MT5 Vivo

Auditoria somente leitura realizada em 2026-07-22:

- terminal MetaTrader 5 conectado;
- conta identificada como Pepperstone Demo;
- `trade_allowed` e `trade_expert` habilitados;
- oito pares selecionados e negociaveis;
- candles M1, M5, M30, H1 e H4 disponiveis para todos os oito pares;
- adaptadores M2-M5 executados sobre dados vivos sem excecao;
- nenhuma ordem foi enviada durante a auditoria;
- posicoes existentes foram preservadas.

Foi corrigida uma falha de relogio: o timestamp Unix do tick era convertido
como horario local e depois rotulado como UTC, podendo criar falso rollover.
Agora ele e convertido diretamente para UTC com timezone explicito.

## Validacao Automatizada

- 133 testes de sessao, rollover, provider, Robo Demo, execucao, modelos do Lab
  e Position Manager;
- 114 testes do dashboard;
- 91 testes do ViewModel e contratos compartilhados;
- 25 testes dos artefatos de pesquisa e seletores;
- compilacao Python dos modulos operacionais aprovada.

Total desta certificacao: 363 testes aprovados.

## Limite Da Certificacao

Esta certificacao prova coerencia de codigo, contratos, dados e preflight Demo.
Ela nao promete rentabilidade futura e nao autoriza conta real. A prova de
execucao real em Demo deve continuar sendo acompanhada no historico MT5 e no
Relatorio, com modelo, Alpha, TF, SL, TP e motivo de eventual bloqueio.
