# Dynamic Exit MT5 Visual Display

## Status

Implementado em modo read-only pela `MISSION_TIA-010`.

## Objetivo

Levar a recomendacao dinamica de saida para o payload visual do MT5 e para o
indicador `TraderIAVisualSignals.mq5`, sem autorizar execucao automatica.

## Campo Visual

O payload JSON agora inclui:

```text
dynamic_exit_visual_text
```

Quando existe posicao aberta no MT5, o campo recebe texto curto com:

- acao recomendada;
- estado atual de mercado;
- confianca;
- stop candidato, quando existir;
- execucao `NAO`;
- motivo resumido.

Quando nao existe posicao aberta:

```text
dynamic_exit_visual_text = ""
```

## Regra Operacional

O indicador MT5 somente desenha o bloco visual quando o sinal estiver marcado
como:

```text
robot_status = POSICAO_ABERTA_MT5
```

Assim, ativos sem posicao permanecem limpos no grafico.

## Guardrails

- Nenhuma ordem enviada.
- Nenhum SL/TP movido.
- Nenhum provider demo alterado.
- `dynamic_exit_allowed_to_execute_demo` permanece `false`.
- Nenhum recalculo pesado de Lab no ciclo leve Forex.

## Arquivos Principais

```text
application/mt5_visual_signal_exporter.py
mt5/indicators/TraderIAVisualSignals.mq5
tests/test_lab_forex_mt5_contract.py
```

## Validacao

```text
python -m unittest tests.test_mt5_visual_signal_exporter tests.test_lab_forex_mt5_contract tests.test_dynamic_exit_recommendation_service tests.test_dynamic_exit_market_state_service
python -m py_compile application/mt5_visual_signal_exporter.py
```
