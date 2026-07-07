# PROGRAM_TIA_DYNAMIC_EXIT_RUNTIME_FULL_EXECUTION

## Objetivo Geral

Implementar, validar e preparar a execucao da **saida dinamica baseada em leitura de mercado** no TraderIA Novo.

O objetivo e sair do modelo atual, em que o Lab escolhe uma politica de saida fixa, para um modelo em que:

```text
Lab define a politica base
↓
Runtime le o mercado em tempo real
↓
Dynamic Exit Engine gera recomendacao auditavel
↓
Sistema exibe e registra a recomendacao
↓
Depois de validado, Provider Demo executa politicas autorizadas
```

## Regra Principal

Executar o programa em camadas, sem quebrar a operacao atual.

O Codex deve seguir esta ordem:

1. Criar contratos read-only.
2. Criar motor de leitura de mercado.
3. Criar recomendacao dinamica.
4. Exibir no Forex, MT5 e Relatorio.
5. Simular e validar.
6. So depois autorizar execucao demo de SL/TP.
7. Ativar politica por politica.
8. Consolidar em um motor unico.

## Guardrails Obrigatorios

- Nao alterar envio de ordem real.
- Nao mover SL/TP automaticamente antes da fase autorizada.
- Nao fazer o MT5 escolher estrategia sozinho.
- Nao fazer o Relatorio decidir saida.
- Nao recalcular Lab pesado no ciclo leve Forex.
- Nao substituir `stop_management` atual.
- Nao forcar tudo para M1.
- Nao quebrar compatibilidade com snapshots antigos.
- Nao apagar `.traderia`.
- Toda alteracao deve ter teste.
- Toda fase deve permitir rollback.

## PHASE 1 - CONTRATO READ-ONLY

### TIA-006 - IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY

Status esperado: ja executada antes deste programa entrar no inbox.

Objetivo: criar os campos read-only da saida dinamica.

Campos esperados:

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

Regra obrigatoria:

```text
dynamic_exit_allowed_to_execute_demo = false
```

Impacto esperado:

- Lab
- TradePlan
- Forex Runtime
- Dashboard ViewModel
- MT5 Visual JSON
- Relatorio

Criterios de aceite:

- Campos transportados sem quebrar contratos antigos.
- Nenhuma execucao real.
- Testes cobrindo compatibilidade.

## PHASE 2 - LEITURA DE MERCADO

### TIA-007 - IMPLEMENTAR_MOTOR_DE_LEITURA_DE_MERCADO

Objetivo: criar um motor que leia o estado atual do mercado e da posicao.

Entradas:

- ativo/par;
- timeframe do Lab;
- direcao;
- preco de entrada;
- stop atual;
- alvo;
- preco atual;
- ATR;
- volatilidade;
- tendencia;
- momentum;
- spread;
- liquidez;
- tempo em posicao;
- R atual.

Saidas:

```text
NO_POSITION
NEW_POSITION
PROTECTED_POSITION
TREND_RUNNER
REVERSAL_RISK
TIME_DECAY
BAD_EXECUTION_CONTEXT
```

Criterios de aceite:

- Motor apenas calcula estado.
- Nenhuma alteracao em SL/TP.
- Testes para todos os estados.

## PHASE 3 - RECOMENDACAO DINAMICA

### TIA-008 - IMPLEMENTAR_DYNAMIC_EXIT_RECOMMENDATION_ENGINE

Objetivo: criar o motor que transforma MarketState em recomendacao read-only.

Acoes possiveis:

```text
KEEP_ORIGINAL_PLAN
PROTECT_TO_BREAK_EVEN
TRAIL_BY_ATR
TRAIL_BY_STRUCTURE
TIGHTEN_BY_MOMENTUM_LOSS
TIME_DECAY_EXIT_WATCH
NO_ACTION_BAD_CONTEXT
```

Criterios de decisao:

- tendencia forte -> manter ou trailing largo;
- momentum fraco -> apertar stop;
- reversao provavel -> proteger;
- baixa volatilidade -> evitar break-even automatico dominante;
- spread ruim -> nao agir;
- posicao nova -> preservar stop inicial.

Criterios de aceite:

- Recomendacao auditavel.
- Motivo obrigatorio.
- Confianca obrigatoria.
- Nenhuma execucao real.

## PHASE 4 - EXIBICAO E AUDITORIA

### TIA-009 - EXIBIR_SAIDA_DINAMICA_NO_FOREX_E_DASHBOARD

Objetivo: mostrar no Dashboard:

```text
Politica original do Lab
Estado atual do mercado
Recomendacao dinamica
Motivo
Confianca
R atual
Stop candidato
Execucao permitida: false
```

Criterios de aceite:

- Dashboard exibe sem travar.
- Sem recalcular Lab pesado.
- Sem mover stop.

### TIA-010 - EXIBIR_SAIDA_DINAMICA_NO_MT5_VISUAL

Objetivo: adicionar a recomendacao dinamica ao JSON visual e ao indicador MT5.

Regra:

- Mostrar somente quando houver posicao aberta.
- Sem posicao: nao poluir grafico.

Criterios de aceite:

- JSON preserva compatibilidade.
- MT5 visual mostra texto curto.
- Nenhuma execucao real.

### TIA-011 - REGISTRAR_SAIDA_DINAMICA_NO_RELATORIO

Objetivo: Relatorio deve registrar:

```text
politica original
recomendacao dinamica
motivo
confianca
estado de mercado
acao executada
resultado final
```

Regra:

- Relatorio observa. Nao decide.

## PHASE 5 - SIMULACAO E BACKTEST

### TIA-012 - BACKTEST_SAIDA_DINAMICA_READ_ONLY

Objetivo: comparar:

```text
saida original do Lab
versus
saida dinamica recomendada
```

Metricas:

- lucro liquido;
- drawdown;
- win rate;
- profit factor;
- expectancy;
- duracao media;
- RR medio;
- dominancia de break-even;
- ganho perdido por saida precoce;
- protecao contra perda.

Criterios de aceite:

- Nenhuma execucao real.
- Relatorio comparativo gerado.

### TIA-013 - PAPER_SIMULATION_SAIDA_DINAMICA

Objetivo: rodar a saida dinamica em modo simulado/paper.

Regras:

- Recomenda, mas nao executa.
- Registra cada recomendacao.
- Compara com o resultado real da politica original.

## PHASE 6 - AUTORIZACAO CONTROLADA

### TIA-014 - AUTORIZAR_BREAK_EVEN_DINAMICO_DEMO

Objetivo: primeira politica autorizada a executar no Provider Demo.

Regra: Break-even so deve ocorrer se:

- posicao andou a favor;
- momentum nao esta forte demais;
- contexto nao e tendencia clara;
- nao corta operacao promissora cedo;
- stop novo melhora protecao;
- stop nao fica do lado errado do mercado.

### TIA-015 - AUTORIZAR_ATR_TRAILING_DINAMICO_DEMO

Objetivo: migrar ATR trailing para obedecer ao DynamicExitEngine.

Regras:

- tendencia forte -> trailing mais largo;
- perda de momentum -> trailing mais curto;
- volatilidade alta -> respeitar ruido;
- nunca piorar stop.

### TIA-016 - AUTORIZAR_CHANDELIER_EXIT_DEMO

Objetivo: implementar execucao demo para `CHANDELIER_EXIT`.

Uso ideal:

- tendencia forte;
- alinhamento multi-timeframe;
- operacao trend runner.

### TIA-017 - AUTORIZAR_DONCHIAN_CHANNEL_STOP_DEMO

Objetivo: implementar execucao demo para `DONCHIAN_CHANNEL_STOP`.

Uso ideal:

- rompimento;
- estrutura;
- consolidacao rompida.

### TIA-018 - AUTORIZAR_VOLATILITY_STOP_DEMO

Objetivo: implementar execucao demo para `VOLATILITY_STOP`.

Uso ideal:

- mudanca de volatilidade;
- ruido alto;
- expansao ou compressao de ATR.

### TIA-019 - AUTORIZAR_TIME_STOP_DEMO

Objetivo: implementar saida temporal dinamica.

Uso ideal:

- posicao sem progresso;
- lateralizacao;
- tempo excessivo em trade.

### TIA-020 - AUTORIZAR_MOVING_AVERAGE_EXIT_DEMO

Objetivo: implementar saida por media movel.

Uso ideal:

- perda de tendencia;
- reversao gradual;
- saida de posicao direcional.

### TIA-021 - AUTORIZAR_PARABOLIC_SAR_DEMO

Objetivo: implementar saida por Parabolic SAR.

Uso ideal:

- reversoes rapidas;
- tendencias curtas;
- trailing sensivel.

## PHASE 7 - MOTOR UNIFICADO

### TIA-022 - UNIFICAR_DYNAMIC_EXIT_ENGINE

Objetivo: criar um motor unico de decisao dinamica.

Fluxo final:

```text
TradePlan
↓
MarketState
↓
DynamicExitEngine
↓
DynamicExitRecommendation
↓
Provider Demo
↓
MT5
↓
Relatorio
```

Criterios:

- Uma entrada unica.
- Uma recomendacao unica.
- Log auditavel.
- Fallback seguro.
- Compatibilidade com politica original.

## PHASE 8 - PERFORMANCE E SEGURANCA

### TIA-023 - OTIMIZAR_DYNAMIC_EXIT_RUNTIME

Objetivo: garantir que o runtime continue leve.

Regras:

- cache quando possivel;
- nada de Lab pesado;
- nada de loops caros;
- tolerancia a dados ausentes;
- tempo de execucao baixo.

### TIA-024 - VALIDACAO_FINAL_DYNAMIC_EXIT

Objetivo: auditoria final da implementacao.

Validar:

- contratos;
- testes;
- MT5 visual;
- Provider Demo;
- Relatorios;
- rollback;
- ausencia de regressoes;
- compatibilidade com `.traderia`;
- seguranca operacional.

## Criterio Final de Conclusao

O programa so estara completo quando:

- o Lab continuar definindo a politica base;
- o Runtime conseguir ler o mercado;
- a recomendacao dinamica estiver auditavel;
- o MT5 visual mostrar corretamente;
- o Relatorio comparar plano original, recomendacao e execucao;
- o Provider Demo executar apenas politicas autorizadas;
- cada politica tiver teste especifico;
- o sistema nunca mover stop para piorar a posicao;
- o sistema nunca mover stop para o lado errado do mercado;
- o rollback estiver documentado.

## Resultado Esperado

Ao final, o TraderIA Novo tera uma saida dinamica real, baseada em leitura de mercado, com:

```text
Lab estrategico
+
Runtime adaptativo
+
MT5 executor controlado
+
Relatorio auditavel
```

O sistema deixara de depender apenas de `BREAK_EVEN` e `ATR_TRAILING_STOP`, passando a usar gestao contextual por tendencia, momentum, volatilidade, estrutura e tempo em posicao.
