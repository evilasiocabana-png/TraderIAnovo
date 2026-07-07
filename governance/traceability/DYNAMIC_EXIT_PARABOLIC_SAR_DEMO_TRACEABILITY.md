# Dynamic Exit Parabolic SAR Demo Traceability

## Missao

`MISSION_TIA-021_AUTORIZAR_PARABOLIC_SAR_DEMO`

## Fluxo

```text
Lab policy PARABOLIC_SAR
-> DynamicExitRecommendation
-> DynamicExitMarketReading
-> DynamicExitParabolicSarAuthorizer
-> DynamicExitDemoAuthorization
-> Relatorio/GitHub auditavel
```

## Politica

`PARABOLIC_SAR`

## Acao dinamica

`TIGHTEN_BY_MOMENTUM_LOSS`

## Uso ideal

- reversoes rapidas;
- tendencias curtas;
- trailing sensivel;
- posicao ja protegida com momentum contra.

## Contrato de seguranca

- `eligible_to_authorize` pode ser `true`;
- `allowed_to_execute_demo` permanece sempre `false`;
- `execution_mode` permanece `READ_ONLY_PRE_AUTHORIZATION`;
- Provider Demo nao e chamado;
- MT5 nao recebe ajuste de ordem por esta missao.

## Arquivos

- `application/dynamic_exit_parabolic_sar_authorizer.py`
- `tests/test_dynamic_exit_parabolic_sar_authorizer.py`
- `docs/DYNAMIC_EXIT_PARABOLIC_SAR_DEMO_AUTHORIZATION.md`
