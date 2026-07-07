# PROGRAM_TIA_DYNAMIC_EXIT_RUNTIME_FULL_EXECUTION

## Status

accepted

## Objetivo

Implementar a saida dinamica baseada em leitura de mercado em camadas
auditaveis, preservando a operacao atual do TraderIA Novo.

## Ordem Canonica

1. `MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY`
2. `MISSION_TIA-007_IMPLEMENTAR_MOTOR_DE_LEITURA_DE_MERCADO`
3. `MISSION_TIA-008_IMPLEMENTAR_DYNAMIC_EXIT_RECOMMENDATION_ENGINE`
4. `MISSION_TIA-009_EXIBIR_SAIDA_DINAMICA_NO_FOREX_E_DASHBOARD`
5. `MISSION_TIA-010_EXIBIR_SAIDA_DINAMICA_NO_MT5_VISUAL`
6. `MISSION_TIA-011_REGISTRAR_SAIDA_DINAMICA_NO_RELATORIO`
7. `MISSION_TIA-012_BACKTEST_SAIDA_DINAMICA_READ_ONLY`
8. `MISSION_TIA-013_PAPER_SIMULATION_SAIDA_DINAMICA`
9. `MISSION_TIA-014_AUTORIZAR_BREAK_EVEN_DINAMICO_DEMO`
10. `MISSION_TIA-015_AUTORIZAR_ATR_TRAILING_DINAMICO_DEMO`
11. `MISSION_TIA-016_AUTORIZAR_CHANDELIER_EXIT_DEMO`
12. `MISSION_TIA-017_AUTORIZAR_DONCHIAN_CHANNEL_STOP_DEMO`
13. `MISSION_TIA-018_AUTORIZAR_VOLATILITY_STOP_DEMO`
14. `MISSION_TIA-019_AUTORIZAR_TIME_STOP_DEMO`
15. `MISSION_TIA-020_AUTORIZAR_MOVING_AVERAGE_EXIT_DEMO`
16. `MISSION_TIA-021_AUTORIZAR_PARABOLIC_SAR_DEMO`
17. `MISSION_TIA-022_UNIFICAR_DYNAMIC_EXIT_ENGINE`
18. `MISSION_TIA-023_OTIMIZAR_DYNAMIC_EXIT_RUNTIME`
19. `MISSION_TIA-024_VALIDACAO_FINAL_DYNAMIC_EXIT`

## Estado Atual

- `MISSION_TIA-006` ja foi executada e concluiu o contrato read-only.
- A proxima missao executavel gerada por este programa e `MISSION_TIA-007`.
- Nenhuma fase de execucao demo de SL/TP esta autorizada antes das fases
  read-only, simulacao e validacao.

## Guardrails

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

## Fonte

Este programa foi aceito a partir de:

```text
codex/completed/PROGRAM_TIA_DYNAMIC_EXIT_RUNTIME_FULL_EXECUTION/PROGRAM.md
```

