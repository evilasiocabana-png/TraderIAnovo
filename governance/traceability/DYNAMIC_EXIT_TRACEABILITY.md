# Dynamic Exit Traceability

Missao: `MISSION_TIA-005_PROJETAR_SAIDA_DINAMICA_BASEADA_EM_LEITURA_DE_MERCADO`

Data: 2026-07-07

## Objetivo

Registrar como a futura saida dinamica deve ser rastreada sem quebrar o fluxo
atual Lab -> Forex -> MT5 -> Relatorio.

## Cadeia de Rastreabilidade

```text
Alpha
  -> setup/modelo
  -> entrada teorica
  -> politica original do Lab
  -> leitura de mercado atual
  -> recomendacao dinamica read-only
  -> timeframe do Lab
  -> Forex MT5
  -> JSON visual MT5
  -> provider demo, quando autorizado
  -> Relatorio/auditoria
```

## Fontes por Campo

| Campo | Fonte atual | Futura extensao read-only |
| --- | --- | --- |
| `alpha_id` | `DashboardMT5ScenarioViewModel.alpha_id` | Preservar como origem da logica. |
| `model` | setup/modelo ativo | Usar para matriz de saida por setup. |
| `timeframe` | Lab/Forex row | Nao substituir por M1 sem registro. |
| `decision` | candidato de entrada | Usar apenas se BUY/SELL e posicao coerente. |
| `stop_management` | Lab/TradePlan | Politica original e obrigatoria. |
| `stop_management_parameters` | Lab/TradePlan | Parametros originais auditaveis. |
| `entry` | TradePlan/posicao MT5 | Base para R atual. |
| `stop` | TradePlan/posicao MT5 | Base para melhora de stop. |
| `target` | TradePlan/posicao MT5 | Base para progresso ate alvo. |
| `market_indicators` | Exportador MT5 visual | Base para ATR/volatilidade/momentum. |
| `is_positioned` | posicao MT5 | Condicao para exibir/avaliar gestao. |
| `position_open_time` | posicao MT5 | Base para `TIME_STOP`. |
| `dynamic_exit_policy` | futuro contrato | Politica recomendada read-only. |
| `dynamic_exit_action` | futuro contrato | Acao sugerida, sem execucao automatica inicial. |
| `dynamic_exit_reason` | futuro contrato | Justificativa auditavel. |

## Matriz Alpha/Setup -> Saida Dinamica

| Grupo | Alphas | Politicas dinamicas candidatas |
| --- | --- | --- |
| Tendencia/continuacao | ALPHA001, ALPHA002, ALPHA006, ALPHA014 | `ATR_TRAILING_STOP`, `CHANDELIER_EXIT`, `MOVING_AVERAGE_EXIT` |
| Rompimento/estrutura | ALPHA003, ALPHA005, ALPHA010, ALPHA013 | `DONCHIAN_CHANNEL_STOP`, `CHANDELIER_EXIT`, `ATR_TRAILING_STOP` |
| Reversao/media | ALPHA004, ALPHA011, ALPHA012 | `BREAK_EVEN`, `TIME_STOP`, `MOVING_AVERAGE_EXIT` |
| Volatilidade | ALPHA008, ALPHA009 | `VOLATILITY_STOP`, `ATR_TRAILING_STOP`, `TIME_STOP` |
| Execucao/liquidez | ALPHA015 | manter politica base ou `NO_ACTION_BAD_CONTEXT` |

## Regras de Preservacao

- A politica original do Lab nunca deve desaparecer do contrato.
- A recomendacao dinamica deve ser campo adicional, nao substituicao silenciosa.
- Sem posicao aberta, nao deve haver acao de saida.
- Com dado incompleto, usar `NO_ACTION_BAD_CONTEXT`.
- O Relatorio deve mostrar divergencia entre politica original e recomendacao,
  mas nao escolher uma delas.
- Provider demo so executa politica quando houver missao explicita e teste.

## Reducao de Dominancia do BREAK_EVEN

Rastrear, em cada recomendacao futura:

- R atual da posicao;
- volatilidade atual;
- momentum atual;
- se setup e continuacao ou reversao;
- se `BREAK_EVEN` foi escolhido por protecao ou por falta de alternativa;
- quanto de ganho potencial seria sacrificado.

Se o setup for de continuacao e momentum/tendencia estiverem favoraveis,
`BREAK_EVEN` deve exigir justificativa mais forte que a simples baixa
volatilidade.

## Campos Recomendados Para a Proxima Missao

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

## Testes de Rastreabilidade Futuros

- Alpha/setup continuam presentes quando campos dinamicos sao adicionados.
- `stop_management` original chega ao JSON mesmo com recomendacao dinamica.
- Campos dinamicos aparecem no Relatorio sem alterar decisao.
- Sem posicao aberta, MT5 visual nao mostra poluicao de saida.
- Falta de ATR/tick/posicao gera `NO_ACTION_BAD_CONTEXT`.
- `BREAK_EVEN` nao substitui `ATR_TRAILING_STOP` em tendencia forte sem motivo.

## Proxima Missao

`MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY`

Essa missao deve implementar apenas contrato/campos read-only e testes. Nao deve
executar gestao real de SL/TP.
