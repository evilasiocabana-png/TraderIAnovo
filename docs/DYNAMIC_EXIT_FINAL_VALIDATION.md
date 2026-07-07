# Dynamic Exit Final Validation

## Status

Validacao final da implementacao dynamic exit concluida em modo read-only.

## Conclusao executiva

A saida dinamica do TraderIA Novo esta implementada como camada auditavel e
read-only:

- Lab continua definindo a politica base.
- Runtime le o mercado.
- Motor gera recomendacao dinamica.
- Autorizadores marcam elegibilidade futura.
- Motor unificado consolida leitura, recomendacao e pre-autorizacao.
- MT5 visual e Relatorio observam sem decidir.
- Provider Demo nao foi alterado para executar estas politicas.

## Evidencia de testes focados

Comando executado:

```text
python -m unittest discover -s tests -p "test_dynamic_exit*.py"
python -m unittest tests.test_lab_forex_mt5_contract tests.test_mt5_trade_audit_service tests.test_report_service
python -m py_compile application\dynamic_exit_engine.py application\dynamic_exit_market_state_service.py application\dynamic_exit_recommendation_service.py domain\contracts\dynamic_exit.py domain\contracts\dynamic_exit_engine.py domain\contracts\dynamic_exit_demo_authorization.py
```

Resultado:

```text
107 testes OK
py_compile OK
```

## Gates oficiais

### run_critical_ci

Status: falhou por pendencias estruturais fora do escopo dynamic exit.

Falhas registradas:

- contrato congelado de servicos publicos em `application`;
- contrato congelado de metodos de `DashboardService`;
- uso de `positions_get` em `dashboard_app.py`;
- expectativa antiga `MA_RSI_FILTER` SELL versus resultado BUY.

### architecture_health

Status: `CRITICO`

Principais pontos:

- manifest divergente;
- baseline drift;
- UI desacoplada com falha.

### architecture_audit

Status: `DIVERGENT`

Principais pontos:

- servicos extras no manifest: `ForexMT5Service`, `LabService`,
  `MT5TradeAuditService`, `ReportService`;
- contratos dynamic exit e contratos operacionais novos ainda nao estao
  reconciliados com o manifest;
- Dashboard depende de item fora da fachada esperada.

### static_analysis

Status: `OK_WITH_WARNINGS`

Erros: `0`

Warnings: `1`

## Guardrails auditados

- Nenhum novo `order_send()` foi criado pela sequencia dynamic exit.
- `allowed_to_execute_demo` permanece `false` nos contratos e resultados
  dynamic exit.
- Fallbacks seguros retornam `REJECTED`.
- Ativos sem posicao continuam sem texto visual dynamic exit.
- Relatorio observa e registra; nao decide saida.
- Provider Demo existente permanece fora do acionamento dynamic exit.

## Pendencias fora do escopo

O sistema ainda precisa de uma missao propria para reconciliar os gates
estruturais:

```text
MISSION_TIA-025_CORRIGIR_GATES_ESTRUTURAIS_API_DASHBOARD
```

Essa missao deve tratar:

- manifest/API freeze de servicos publicos;
- contrato congelado de `DashboardService`;
- remocao do acesso direto `positions_get` do dashboard;
- expectativas antigas dos testes `MA_RSI_FILTER` e, se reaparecer,
  `TREND_MOMENTUM`.

## Rollback

Rollback seguro da sequencia dynamic exit:

1. Reverter commits das missoes TIA-006 a TIA-024 em ordem inversa.
2. Manter `.traderia` intacto.
3. Reexecutar testes de contrato Lab-Forex-MT5 e Relatorio.
4. Validar que MT5 visual volta ao contrato anterior.

## Decisao

Dynamic Exit esta pronto como infraestrutura read-only auditavel.

Nao esta autorizado executar SL/TP automaticamente ate nova missao formal
corrigir gates estruturais e ativar politica operacional explicitamente.
