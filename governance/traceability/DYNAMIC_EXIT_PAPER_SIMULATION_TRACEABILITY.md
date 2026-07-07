# Dynamic Exit Paper Simulation Traceability

## Missao

`MISSION_TIA-013_PAPER_SIMULATION_SAIDA_DINAMICA`

## Fluxo

```text
DynamicExitRecommendation
->
DynamicExitPaperRecommendationRecord
->
DynamicExitPaperSimulationEngine
->
DynamicExitBacktestEngine
->
DynamicExitPaperSimulationReport
->
Relatorio paper read-only
```

## Contrato

| Campo | Origem | Uso |
| --- | --- | --- |
| `original_policy` | Lab | politica original observada |
| `dynamic_action` | recomendacao dinamica | acao paper simulada |
| `dynamic_reason` | motor dinamico | motivo auditavel |
| `dynamic_confidence` | motor dinamico | confianca auditavel |
| `market_state` | leitura de mercado | contexto paper |
| `original_result_r` | resultado observado | comparacao baseline |
| `dynamic_paper_result_r` | simulacao paper | comparacao dinamica |
| `executed` | guardrail | sempre normalizado para `false` |

## Guardrail

A simulacao registra e compara. Ela nao chama Provider Demo, nao envia ordem,
nao move SL/TP e nao autoriza execucao.
