# ALPHA101_FACTORY_APPROVAL

## Missao

MISSÃO 239 — ALPHA101_FACTORY_APPROVAL.md

Sprint 17 — Alpha Discovery Lab

## Objetivo

Submeter a hipótese `ALPHA101_DAILY_VOLUME_MOMENTUM_BREAKOUT` à Alpha Factory.

## Resumo da Hipótese

PETR4 diário pode apresentar continuidade de curto prazo quando momentum de 5 dias, volume relativo e proximidade de breakout ocorrem juntos, desde que filtros de volatilidade e esticamento evitem entradas excessivamente tardias.

## Evidências a Favor

- Melhor triagem inicial: `volume_momentum_5d`.
- Retorno médio futuro 5d: 0.776%.
- Hit rate: 58.70%.
- Amostra: 322 ocorrências.
- Segunda melhor triagem: `breakout_20d`.
- Breakout 20d teve hit rate de 59.72%.
- Volume tem correlação forte com retorno absoluto, indicando participação/intensidade.
- Momentum 5d teve correlação positiva com retorno futuro 5d.

## Evidências Contra

- Edge ainda é exploratório.
- Não há custos ou slippage na triagem.
- PETR4 teve fortes ciclos; resultado pode depender de anos específicos.
- Correlações individuais são baixas.
- Existe risco de mineração de features.
- A hipótese long-only pode sofrer em ciclos de queda.

## Riscos

- overfitting;
- concentração temporal;
- drawdown elevado;
- compra após movimento já esticado;
- dependência de volume anômalo;
- confusão entre intensidade e direção.

## Dependências

- Dataset PETR4 diário certificado para pesquisa.
- `StrategySignal` como contrato.
- `DashboardService` como fachada.
- `ReplayService` sem acesso direto a arquivos.
- `StrategyFactory` para registro controlado.

## Critérios de Aprovação

| Critério | Status |
| --- | --- |
| Hipótese baseada em dados reais | Atendido |
| Mercado/timeframe definidos | Atendido |
| Features rastreáveis | Atendido |
| Risco de overfitting reconhecido | Atendido |
| Operação real proibida | Atendido |
| Implementável sem quebrar arquitetura | Atendido com restrições |

## Decisão Final

```text
APPROVED_WITH_RESTRICTIONS
```

## Restrições de Aprovação

- Implementar somente como pesquisa/simulação.
- Não executar ordens reais.
- Não conectar corretora.
- Não alterar `HistoricalDataProvider`.
- Não alterar `ReplayEngine`.
- Não alterar `ResearchLab` fora dos contratos existentes.
- Registrar Alpha101 apenas se respeitar `StrategySignal`.
- Exigir validação quantitativa posterior.
- Certificação só pode ocorrer após validação completa.

## Próxima Etapa

Criar `ALPHA101_PLAYBOOK.md`.

## Declaração Final

A Alpha101 foi aprovada com restrições para implementação controlada como pesquisa quantitativa. A aprovação não certifica edge, não autoriza operação real e não transforma a hipótese em robô.
