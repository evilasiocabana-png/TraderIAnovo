# Modelos M8-M14 - Variantes De Saida Dinamica

## Objetivo

M8-M14 sao variantes operacionais independentes dos modelos fixos M1-M7.
Cada variante copia o plano de entrada do seu modelo de origem e altera somente
o contrato aplicado depois que a posicao ja estiver aberta.

| Modelo dinamico | Origem da entrada | Identificador |
|---|---|---|
| M8 | M1 | `MODELO_8_DYNAMIC_EXIT_FROM_M1` |
| M9 | M2 | `MODELO_9_DYNAMIC_EXIT_FROM_M2` |
| M10 | M3 | `MODELO_10_DYNAMIC_EXIT_FROM_M3` |
| M11 | M4 | `MODELO_11_DYNAMIC_EXIT_FROM_M4` |
| M12 | M5 | `MODELO_12_DYNAMIC_EXIT_FROM_M5` |
| M13 | M6 | `MODELO_13_DYNAMIC_EXIT_FROM_M6` |
| M14 | M7 | `MODELO_14_DYNAMIC_EXIT_FROM_M7` |

## Contrato Imutavel Da Entrada

A variante deve preservar sem recalculo:

- par e timeframe;
- Alpha, setup, filtros e candle de sinal;
- direcao;
- preco de entrada;
- SL inicial;
- TP inicial;
- RR;
- parametros e evidencia do modelo de origem.

O Lab pesado nao roda no ciclo leve. O mesmo resultado de entrada calculado
para M1-M7 e reutilizado por sua variante M8-M14.

## Contrato Dinamico Depois Da Entrada

As variantes publicam `DYNAMIC_PROTECT_ONLY`:

- antes de 1,50R: preservar o SL inicial;
- a partir de 1,50R: permitir break-even ou ATR trailing;
- mover somente para um SL mais protetivo;
- nunca afastar o SL;
- nunca executar `EARLY_EXIT`;
- nunca executar `FULL_EXIT`;
- preservar o TP original.

O Position Manager decide `HOLD_POSITION` ou protecao. O
`DemoExecutionService` continua sendo a unica porta que solicita a modificacao
ao provider MT5 Demo.

## Independencia E Duplicidade

Cada modelo possui ID, Beta, comentario MT5, cache, historico e posicao
independentes. Uma posicao do modelo fixo e sua variante dinamica podem
coexistir para permitir comparacao A/B. A mesma variante nao pode repetir o
mesmo plano no mesmo candle.

Modelos historicos que anteriormente ocupavam os numeros M8-M22 continuam no
historico, mas permanecem aposentados para novas entradas. A identidade
canonica completa, e nao apenas o numero, separa os contratos.

## Seguranca

- somente conta Demo;
- conta real permanece bloqueada;
- chave assistida pode autorizar apenas melhora de SL;
- uma variante dinamica nunca cria entrada por conta propria;
- mudanca do seletor nao interrompe a gestao de posicao aberta;
- falha de dados preserva o SL atual e registra o motivo.

## Rollback

O rollback operacional consiste em retirar M8-M14 do conjunto ativo e do
seletor. M1-M7 nao precisam ser alterados porque seus planos e politicas fixas
nao foram modificados. Posicoes dinamicas ja abertas devem continuar sob
auditoria ate o fechamento ou ser tratadas por procedimento Demo explicito.

## Testes Obrigatorios

- mapa exato M8->M1 ate M14->M7;
- entrada, SL, TP, RR e Alpha preservados;
- politica `DYNAMIC_PROTECT_ONLY` transportada ao Position Manager;
- SL move somente depois do limiar e somente a favor;
- `EARLY_EXIT` e `FULL_EXIT` bloqueados mesmo com chave global ativa;
- modelos historicos com os mesmos numeros continuam aposentados;
- seletor, monitores e Relatorio mostram M1-M14 sem recalculo pesado.
