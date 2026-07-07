# Dynamic Exit Paper Simulation

## Status

Implementado em modo read-only pela `MISSION_TIA-013`.

## Objetivo

Rodar a saida dinamica em modo simulado/paper, registrando cada recomendacao e
comparando com o resultado observado da politica original.

## Motor

```text
application/dynamic_exit_paper_simulation.py
```

O motor recebe registros `DynamicExitPaperRecommendationRecord`, garante que
nenhum registro seja marcado como executado e consolida a comparacao usando o
backtest read-only da TIA-012.

## O Que Fica Registrado

- ativo;
- setup;
- timeframe;
- politica original do Lab;
- acao dinamica recomendada;
- motivo;
- confianca;
- estado de mercado;
- resultado original observado em R;
- resultado dinamico paper em R;
- duracao original;
- duracao dinamica paper;
- RR planejado;
- flag `executed`, sempre normalizada para `false`.

## Guardrails

- `read_only = true`.
- `execution_allowed = false`.
- Nenhuma ordem enviada.
- Nenhum SL/TP movido.
- Nenhum provider demo alterado.
- Nenhum ciclo leve Forex alterado.
- A simulacao nao executa recomendacao dinamica no Provider Demo.

## Arquivos Principais

```text
domain/contracts/dynamic_exit_paper.py
application/dynamic_exit_paper_simulation.py
tests/test_dynamic_exit_paper_simulation.py
```

## Validacao

```text
python -m unittest tests.test_dynamic_exit_paper_simulation tests.test_dynamic_exit_backtest tests.test_dynamic_exit_recommendation_service tests.test_dynamic_exit_market_state_service
python -m py_compile application/dynamic_exit_paper_simulation.py domain/contracts/dynamic_exit_paper.py application/dynamic_exit_backtest.py domain/contracts/dynamic_exit_backtest.py
```
