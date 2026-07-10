# TraderIA Novo - Dynamic Exit Design

Missao: `MISSION_TIA-005_PROJETAR_SAIDA_DINAMICA_BASEADA_EM_LEITURA_DE_MERCADO`

Data: 2026-07-07

Escopo: desenho tecnico e governanca para saida dinamica baseada em leitura de
mercado. Esta missao nao altera codigo operacional.

## Resumo Executivo

A saida dinamica deve ser uma camada de decisao read-only inicialmente. Ela nao
deve substituir a decisao do Lab, nem fazer o MT5 escolher sozinho. O desenho
correto e:

```text
Lab escolhe a politica base
  -> Forex transporta e observa mercado/posicao
  -> contrato read-only calcula recomendacao auditavel
  -> MT5 visual mostra plano quando houver posicao
  -> Relatorio audita decisao, execucao e resultado
  -> missao futura pode autorizar gestao demo de SL/TP por politica
```

O objetivo e evitar dois problemas:

1. `BREAK_EVEN` dominar por protecao excessiva em baixa volatilidade.
2. Todas as saidas virarem `FIXED_STOP` por compatibilidade ou falta de suporte.

## Principio Arquitetural

O sistema deve preservar tres papeis:

- Lab decide parametros e politica base.
- Runtime Forex/MT5 observa o estado atual e transporta contrato.
- Relatorio audita, sem decidir.

O MT5 demo so deve executar alteracao de SL/TP quando uma missao posterior
autorizar explicitamente a politica e seus testes.

## Entradas da Saida Dinamica

As leituras que devem influenciar a saida dinamica sao:

| Leitura | Origem esperada | Uso |
| --- | --- | --- |
| Ativo/par | Forex row / posicao MT5 | Evitar politica generica para todos os pares. |
| Setup/Alpha | Lab | Vincular saida ao comportamento esperado da entrada. |
| Timeframe do Lab | Lab -> Forex | Preservar TF vencedor; nao forcar M1. |
| Direcao | Lab/posicao MT5 | Calcular se stop melhora para BUY ou SELL. |
| Preco de entrada | TradePlan/posicao MT5 | Medir R atual e distancia do stop. |
| Stop atual | posicao MT5 | Permitir somente melhora de protecao. |
| Alvo atual | TradePlan/posicao MT5 | Medir progresso ate alvo. |
| Preco atual | tick MT5 | Calcular resultado parcial e distancia. |
| ATR/volatilidade | market indicators | Escolher espaco de respiracao. |
| Tendencia/momentum | Lab/indicators | Diferenciar continuacao de reversao. |
| Tempo em posicao | `position_open_time` | Aplicar saida temporal sem pressa indevida. |
| Spread/liquidez | Lab/MT5 | Evitar ajuste em condicao ruim. |
| Politica original | Lab | Base para manter ou adaptar, com auditoria. |

## Modelo Conceitual

```text
ativo + setup + timeframe + regime + posicao aberta
  -> politica base do Lab
  -> leitura dinamica do mercado
  -> recomendacao read-only de saida
  -> campos de auditoria
  -> futura acao demo, se autorizada
```

## Estados da Posicao

| Estado | Definicao | Acao recomendada |
| --- | --- | --- |
| `NO_POSITION` | Sem posicao aberta no papel | Nao aplicar saida; manter grafico limpo. |
| `NEW_POSITION` | Posicao aberta, ainda sem R minimo | Preservar stop inicial; sem `BREAK_EVEN` automatico. |
| `PROTECTED_POSITION` | Posicao ja andou a favor e stop pode melhorar | Permitir recomendacao de protecao. |
| `TREND_RUNNER` | Tendencia/momentum continuam a favor | Preferir trailing que de espaco. |
| `REVERSAL_RISK` | Momentum enfraquece ou reversao aparece | Preferir protecao mais curta. |
| `TIME_DECAY` | Exposicao longa sem progresso | Preferir saida temporal ou aperto gradual. |
| `BAD_EXECUTION_CONTEXT` | Spread alto, liquidez ruim ou MT5 instavel | Nao mexer automaticamente; apenas auditar. |

## Matriz Politica x Mercado

| Condicao de mercado | Setup mais comum | Politica candidata | Motivo |
| --- | --- | --- | --- |
| Tendencia forte e volatilidade normal/alta | `TREND_MOMENTUM`, `ADX_TREND_STRENGTH` | `ATR_TRAILING_STOP`, `CHANDELIER_EXIT` | Deixa a operacao respirar e acompanha a tendencia. |
| Rompimento estrutural | `BREAKOUT_CONSOLIDATION`, `DONCHIAN_BREAKOUT`, `DONCHIAN_STRUCTURE_BREAKOUT` | `DONCHIAN_CHANNEL_STOP`, `ATR_TRAILING_STOP` | Stop deve respeitar estrutura do rompimento. |
| Reversao curta | `RSI_REVERSAL`, `VWAP_MEAN_REVERSION`, `PIVOT_REJECTION` | `BREAK_EVEN`, `MOVING_AVERAGE_EXIT`, `TIME_STOP` | Reversoes curtas nao devem ficar expostas demais. |
| Volatilidade muito baixa | `ATR_VOLATILITY_REGIME` | `TIME_STOP`, `VOLATILITY_STOP`, `BREAK_EVEN` com penalidade | Evitar que `BREAK_EVEN` sempre ganhe so por reduzir perda simulada. |
| Volatilidade alta | `BOLLINGER_VOLATILITY_EXPANSION`, `ATR_VOLATILITY_REGIME` | `VOLATILITY_STOP`, `ATR_TRAILING_STOP` | Stop precisa aumentar espaco conforme ruido. |
| Alinhamento multi-TF | `MULTI_TIMEFRAME_ALIGNMENT` | `CHANDELIER_EXIT`, `ATR_TRAILING_STOP` | Movimento pode ter continuidade maior. |
| Spread/liquidez desfavoravel | `LIQUIDITY_SPREAD_FILTER` | manter politica base, sem ajuste automatico | Reduz risco de ajuste ruim por custo de execucao. |

## Quando Manter a Politica Original do Lab

Manter a politica original quando:

- a posicao ainda esta antes de 0.5R a favor;
- a leitura de mercado atual nao contradiz o setup;
- a volatilidade e coerente com o parametro escolhido;
- o stop atual ja protege melhor que o candidato;
- o contexto de execucao esta ruim;
- falta dado confiavel de ATR, preco, posicao ou timeframe.

## Quando Adaptar a Politica

Uma adaptacao futura pode ser recomendada, inicialmente apenas read-only, quando:

- a posicao esta aberta e identificada no mesmo simbolo;
- o preco andou pelo menos um limiar minimo a favor;
- a politica original e muito agressiva para o regime atual;
- a tendencia continua e `BREAK_EVEN` cortaria ganho cedo demais;
- a posicao esta parada por tempo excessivo;
- a volatilidade mudou de regime desde a entrada;
- o setup exige saida mais estrutural do que simples ATR/RR.

## Controle de Dominancia do BREAK_EVEN

Para reduzir dominancia indevida de `BREAK_EVEN`, a futura logica deve:

1. Exigir progresso minimo alem de 1R quando tendencia/momentum seguem fortes.
2. Penalizar `BREAK_EVEN` quando o setup e de continuacao e a volatilidade nao
   esta colapsando.
3. Comparar ganho capturado, nao apenas perda reduzida.
4. Registrar motivo quando `BREAK_EVEN` for escolhido.
5. Permitir que `ATR_TRAILING_STOP` ou `CHANDELIER_EXIT` superem `BREAK_EVEN`
   em tendencias claras.
6. Aplicar `BREAK_EVEN` cedo apenas em reversao curta, baixa conviccao ou perda
   de momentum.

## Contrato Read-only Proposto

A proxima missao deve adicionar um contrato read-only, sem execucao real, com
campos como:

```text
dynamic_exit_policy
dynamic_exit_action
dynamic_exit_reason
dynamic_exit_confidence
dynamic_exit_market_state
dynamic_exit_r_multiple
dynamic_exit_candidate_stop
dynamic_exit_allowed_to_execute_demo
dynamic_exit_source
```

Valor esperado de `dynamic_exit_allowed_to_execute_demo` na primeira fase:

```text
false
```

Isso permite que Forex, MT5 visual e Relatorio enxerguem a recomendacao sem
mover SL/TP automaticamente.

## Acoes Dinamicas Read-only

| Acao | Significado |
| --- | --- |
| `KEEP_ORIGINAL_PLAN` | Manter politica original do Lab. |
| `PROTECT_TO_BREAK_EVEN` | Recomendar protecao para entrada/offset. |
| `TRAIL_BY_ATR` | Recomendar trailing por ATR. |
| `TRAIL_BY_STRUCTURE` | Recomendar estrutura/canal/chandelier. |
| `TIGHTEN_BY_MOMENTUM_LOSS` | Recomendar apertar por perda de momentum. |
| `TIME_DECAY_EXIT_WATCH` | Recomendar observacao por tempo excessivo. |
| `NO_ACTION_BAD_CONTEXT` | Nao recomendar ajuste por dado/contexto ruim. |

## Impacto Por Camada

### Lab

O Lab continua definindo setup, entrada, stop inicial, RR e alvo inicial.
`stop_management` permanece apenas como legado/hint de compatibilidade. A saida
dinamica nao nasce escolhida no Lab; ela e decidida pelo Position Manager a
partir do cenario da posicao aberta.

### Forex MT5

O Forex pode calcular ou exibir recomendacao read-only a partir de dados leves.
Ele nao deve recalcular biblioteca pesada de Alphas a cada ciclo.

### TradePlan

O `MT5ResearchTradePlan` deve materializar o plano inicial de risco e preservar
parametros legados apenas como hints
canonicos. Campos dinamicos devem ser adicionados em contrato separado ou como
extensao clara, para nao quebrar testes existentes.

### MT5 Visual

O indicador deve receber textos curtos e apenas mostrar recomendacao quando
houver posicao aberta. Sem posicao, o grafico deve ficar limpo.

### Provider Demo

Nenhuma nova politica deve executar SL/TP ate uma missao posterior. O provider
atual suporta `BREAK_EVEN` e `ATR_TRAILING_STOP`; futuras politicas precisam de
testes isolados antes de entrar.

### Relatorio

O Relatorio deve comparar:

- politica original do Lab;
- recomendacao dinamica read-only;
- acao demo efetivamente aplicada, se houver no futuro;
- resultado da posicao.

Ele nao deve decidir politica.

## Testes Obrigatorios Para Implementacao Futura

Antes de qualquer execucao demo nova, exigir:

- teste de contrato Lab -> Forex preservando politica original;
- teste de exportacao JSON com campos dinamicos;
- teste de MT5 visual sem poluir graficos sem posicao;
- teste do provider demo para cada politica executavel;
- teste de fallback quando faltam ATR, posicao, tick ou timeframe;
- teste para impedir piora do stop;
- teste para impedir stop do lado errado do mercado;
- teste para confirmar que Relatorio nao decide saida;
- teste garantindo que Forex nao recalcula Lab pesado no ciclo leve.

## Sequencia Segura de Missoes

1. `MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY`
   - adicionar contrato/campos read-only e testes;
   - sem alterar SL/TP real.

2. `MISSION_TIA-007_EXIBIR_SAIDA_DINAMICA_NO_FOREX_E_RELATORIO`
   - mostrar recomendacao auditavel;
   - preservar visual limpo no MT5.

3. `MISSION_TIA-008_SIMULAR_SAIDA_DINAMICA_EM_BACKTEST_LEVE`
   - comparar saida original x dinamica;
   - medir dominancia de `BREAK_EVEN`.

4. `MISSION_TIA-009_AUTORIZAR_POLITICA_DEMO_ESPECIFICA`
   - escolher uma politica por vez;
   - implementar provider demo com testes.

## Criterio de Pronto Para Codigo

A implementacao so deve comecar quando o contrato read-only estiver aprovado e
quando o GPT/Codex conseguirem rastrear:

```text
Alpha -> setup -> entrada -> saida original -> saida dinamica
-> timeframe -> Forex -> MT5 visual -> provider demo -> Relatorio
```

Enquanto isso, a operacionalidade atual deve permanecer intacta.
