# EXECUTION_REPORT - MISSION_ROLLOVER_FIRST_DAILY_OPERATION_LAB_DECISION

## Status

completed

## Objetivo executado

Implementada a capacidade do Research Lab avaliar o pos-rollover como evento
prioritario do novo dia operacional, sem substituir as Alphas existentes.

## Resultado

Criado:

```text
research/post_rollover_analyzer.py
```

Com:

- `POST_ROLLOVER_DAILY_OPEN`;
- `EVENT_POST_ROLLOVER_DAILY_OPEN`;
- `PostRolloverAnalyzer`;
- `PostRolloverDecision`.

O evento analisa:

- horario do servidor MT5 via `ForexTimeLayer`;
- fim da janela de protecao;
- spread atual;
- spread medio recente;
- normalizacao do spread;
- tick volume;
- ATR;
- volatilidade;
- momentum;
- direcao dos primeiros candles;
- gap/tick gap estimado.

## Integracao

O `DashboardService` agora injeta o evento pos-rollover no ranking do Lab antes
dos cenarios normais quando ele esta ativo.

Se houver edge:

```text
POST_ROLLOVER_TRADE_READY
```

Se nao houver edge:

```text
POST_ROLLOVER_SKIPPED
```

Se estiver fora da janela:

```text
NORMAL_LAB_FLOW
```

O evento aparece no ranking como:

```text
EVENT_POST_ROLLOVER_DAILY_OPEN
```

## Exibicao

O dashboard do Scenario Runner passou a mostrar:

- modo do Lab;
- evento;
- contexto;
- motivo.

As linhas de cenario carregam tambem:

- evento;
- modo do evento;
- contexto do evento.

## Documentacao e rastreabilidade

Criados:

```text
docs/POST_ROLLOVER_DAILY_OPEN.md
governance/traceability/POST_ROLLOVER_DAILY_OPEN_TRACEABILITY.md
```

Atualizado:

```text
governance/traceability/TRACEABILITY_INDEX.md
```

## Guardrails preservados

- Nenhuma operacao abre durante a janela de rollover.
- O evento so e avaliado apos fim da protecao.
- Nenhuma Alpha existente foi removida.
- Nao foi criada Alpha 16.
- Nao ha horario fixo de Brasilia.
- O horario do servidor MT5 e preferido quando disponivel.
- O Lab continua responsavel por entrada, timeframe, RR, stop e alvo.
- O evento nao executa ordem por si so.
- Se nao houver edge, o sistema volta ao fluxo normal das Alphas.

## Validacao

Executado com sucesso:

```text
python -m unittest tests.test_post_rollover_analyzer
python -m unittest tests.test_dashboard_view_model.DashboardViewModelContractTest.test_research_lab_prioriza_evento_pos_rollover_antes_das_alphas tests.test_dashboard_view_model.DashboardViewModelContractTest.test_research_lab_cenario_bloqueia_rollover tests.test_dashboard_view_model.DashboardViewModelContractTest.test_research_lab_cenario_ignora_rollover_quando_filtro_desligado
python -m unittest tests.test_forex_time_layer
python -m unittest tests.test_dashboard_app_runtime.DashboardAppRuntimeTest.test_lab_sugestoes_normalizam_modelo_saida_legado
python -m py_compile research\post_rollover_analyzer.py application\dashboard_service.py application\dashboard_view_model.py dashboard_app.py
```

## Observacao

Esta missao cria capacidade de avaliacao prioritaria pos-rollover. Ela nao cria
uma regra automatica fixa de compra/venda apos rollover.
