# MISSION_TIA-005_PROJETAR_SAIDA_DINAMICA_BASEADA_EM_LEITURA_DE_MERCADO

## Tipo

Missao de arquitetura, desenho tecnico e governanca.

Esta missao nao autoriza alteracao operacional de envio de ordem, gestao real
de SL/TP, `order_send()`, broker, `RiskEngine`, `DecisionPipeline`,
estrategias ou execucao MT5.

## Contexto

A missao anterior, `MISSION_TIA-004_ANALISAR_STOPS_MOVEIS`, documentou que o
TraderIA Novo avalia 9 politicas canonicas de stop management:

- `FIXED_STOP`
- `ATR_TRAILING_STOP`
- `BREAK_EVEN`
- `CHANDELIER_EXIT`
- `PARABOLIC_SAR`
- `DONCHIAN_CHANNEL_STOP`
- `MOVING_AVERAGE_EXIT`
- `TIME_STOP`
- `VOLATILITY_STOP`

Tambem foi identificado que a gestao demo MT5 aplica ajuste dinamico real de
SL/TP apenas para:

- `BREAK_EVEN`
- `ATR_TRAILING_STOP`

As demais politicas sao avaliadas/transportadas, mas ainda nao possuem execucao
dinamica no provider demo.

## Objetivo

Projetar a saida dinamica baseada em leitura de mercado, por ativo, setup e
timeframe, antes de qualquer implementacao operacional.

O desenho deve permitir que futuras missoes implementem a melhor saida para cada
contexto sem quebrar a estabilidade atual do sistema.

## Arquivos de Referencia Obrigatorios

Ler antes de propor qualquer desenho:

- `docs/MOBILE_STOPS_ANALYSIS.md`
- `governance/traceability/STOP_LOGIC_TRACEABILITY.md`
- `governance/traceability/ALPHA_INDEX.md`
- `governance/traceability/SETUP_INDEX.md`
- `governance/traceability/LAB_TO_FOREX_CONTRACT.md`
- `governance/traceability/FOREX_TO_MT5_CONTRACT.md`
- `governance/traceability/REPORT_CONTRACT.md`
- `governance/traceability/TRACEABILITY_MATRIX.md`
- `application/dashboard_service.py`
- `research/mt5_research_trade_plan.py`
- `infrastructure/execution/mt5_demo_execution_provider.py`
- `application/mt5_visual_signal_exporter.py`
- `mt5/indicators/TraderIAVisualSignals.mq5`
- `tests/test_lab_forex_mt5_contract.py`
- `tests/test_mt5_demo_execution_provider.py`

## Entregaveis

Criar:

```text
docs/DYNAMIC_EXIT_DESIGN.md
governance/traceability/DYNAMIC_EXIT_TRACEABILITY.md
```

Atualizar, se aplicavel:

```text
governance/traceability/TRACEABILITY_INDEX.md
governance/execution/PROJECT_STATUS.md
governance/execution/NEXT_MISSION.md
docs/GPT_SYNC_STATUS.md
```

## Perguntas que a Missao Deve Responder

1. Quais leituras de mercado devem influenciar a saida dinamica?
2. Como combinar ativo, setup, timeframe, volatilidade, tendencia, momentum,
   posicao aberta, preco de entrada, stop atual, alvo e resultado parcial?
3. Quando manter a politica original do Lab?
4. Quando permitir troca ou adaptacao da politica de saida apos a entrada?
5. Quais politicas devem continuar apenas avaliadas e quais devem virar
   candidatas para execucao demo futura?
6. Como evitar que `BREAK_EVEN` domine por excesso em baixa volatilidade?
7. Como preservar o principio: Relatorio audita, MT5 executa apenas plano,
   Lab decide parametros?
8. Quais testes serao obrigatorios na futura missao de implementacao?

## Modelo de Decisao Esperado

Documentar uma matriz conceitual:

```text
ativo + setup + timeframe + regime de mercado + posicao aberta
  -> politica de saida permitida
  -> parametros dinamicos
  -> acao futura no MT5 demo
  -> campos de auditoria no Relatorio
```

## Regras e Guardrails

- Nao alterar codigo operacional nesta missao.
- Nao alterar o provider MT5 demo nesta missao.
- Nao alterar MQL5 nesta missao.
- Nao alterar envio de ordens nesta missao.
- Nao criar nova politica sem documentar contrato e impacto.
- Nao transformar o Relatorio em fonte de decisao.
- Nao fazer Forex recalcular Lab pesado em cada ciclo.
- Nao quebrar compatibilidade com os nomes canonicos atuais de stop management.
- Qualquer proposta de execucao futura deve ser descrita como proxima missao,
  nao implementada agora.

## Criterios de Aceite

- `docs/DYNAMIC_EXIT_DESIGN.md` explica a arquitetura proposta de saida dinamica.
- `governance/traceability/DYNAMIC_EXIT_TRACEABILITY.md` conecta Alpha -> setup
  -> entrada -> saida -> timeframe -> Forex -> MT5 -> Relatorio.
- A documentacao diferencia claramente avaliacao do Lab, transporte de contrato,
  visual MT5, gestao demo e relatorio.
- A documentacao identifica como reduzir dominancia indevida de `BREAK_EVEN`.
- A documentacao propõe uma sequencia segura de futuras missoes de
  implementacao.
- Nenhum codigo operacional e alterado.
- `codex/processing` fica vazio ao final.
- `EXECUTION_REPORT.md` e criado no pacote concluido.
- Commit e push sao realizados.

## Validacao

Como a missao e documental, executar validacao proporcional:

```powershell
git diff --check
git status --short --branch
```

Se houver alteracao em arquivos Python por engano, parar e reverter essa parte
antes do commit.

## Proxima Missao Sugerida ao Final

Preparar, mas nao executar automaticamente:

```text
MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY
```

Essa futura missao deve adicionar apenas campos/contratos read-only e testes,
ainda sem mexer em gestao real de SL/TP.
