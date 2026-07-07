# Dynamic Exit Unified Engine Traceability

## Missao

`MISSION_TIA-022_UNIFICAR_DYNAMIC_EXIT_ENGINE`

## Fluxo rastreavel

```text
Lab policy
-> DynamicExitEngineInput
-> DynamicExitMarketStateClassifier
-> DynamicExitRecommendationEngine
-> DynamicExit*Authorizer
-> DynamicExitEngineResult
-> Auditoria/GitHub
```

## Fonte de decisao

O Lab continua definindo a politica base. O motor unificado apenas consolida:

- leitura de mercado;
- recomendacao dinamica;
- pre-autorizacao read-only.

## Fallback

Politicas sem autorizador registrado retornam `REJECTED` com
`allowed_to_execute_demo=false`.

## Arquivos

- `domain/contracts/dynamic_exit_engine.py`
- `application/dynamic_exit_engine.py`
- `tests/test_dynamic_exit_unified_engine.py`
- `docs/DYNAMIC_EXIT_UNIFIED_ENGINE.md`
