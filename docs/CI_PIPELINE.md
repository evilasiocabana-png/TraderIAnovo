# CI Pipeline

Este documento descreve o pipeline critico atual do TraderIA.

## Workflow

```text
.github/workflows/quality-gate.yml
```

O workflow roda em:

- push para `main`;
- pull request;
- execucao manual por `workflow_dispatch`.

## Comando oficial

O CI chama um unico script:

```powershell
python scripts\run_critical_ci.py
```

Esse script tambem e o comando padrao para validar localmente antes de commit.

## O que o script valida

O script executa:

1. `py_compile` dos modulos criticos do dashboard, MT5 e contratos.
2. Testes estaveis de contrato:
   - `tests.test_application_api`
   - `tests.test_dashboard_view_model`
   - `tests.test_lab_forex_mt5_contract`
   - `tests.test_mt5_demo_execution_provider`
   - `tests.test_mt5_research_trade_plan`
   - `tests.test_mt5_process_probe`

## O que o CI nao executa

O CI critico nao roda `python -m unittest discover -s tests` como validacao
padrao.

Motivo: a suite completa pode incluir testes live, externos, Streamlit/MT5 ou
dependentes da maquina local. Esses testes devem ficar em validacoes manuais ou
em workflows especificos.

O CI tambem nao deve:

- iniciar MetaTrader 5;
- abrir Streamlit de forma bloqueante;
- enviar ordens;
- recalcular Lab pesado automaticamente;
- publicar snapshots locais;
- versionar artefatos de `.traderia/`.

## Dependencias no GitHub Actions

O workflow instala apenas dependencias suficientes para os contratos criticos:

```text
streamlit
duckdb
```

O pacote `MetaTrader5` nao e instalado no Ubuntu do GitHub Actions. A integracao
real com MT5 continua sendo validacao local/controlada.

## Falhas

Em falha, o workflow tenta gerar:

```powershell
python scripts\collect_failure_context.py
```

e publica `reports/failure_context.json` quando disponivel.

## Regra de entrega

Antes de subir mudancas relevantes:

```powershell
python scripts\run_critical_ci.py
```

Para mudancas em configuracao:

```powershell
python -m unittest tests.test_configuration_contracts
```

Mudancas que tocam Lab, Forex, MT5, configuracao operacional ou dashboard devem
ter pelo menos essas validacoes verdes antes do push.
