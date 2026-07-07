# ALPHA101_CERTIFIED

## Missao

MISSÃO 243 — ALPHA101_CERTIFICATION.md

Sprint 17 — Alpha Discovery Lab

## Objetivo

Certificar ou rejeitar oficialmente a Alpha101 após pesquisa, implementação e validação exploratória.

## Alpha

```text
ALPHA101_DAILY_VOLUME_MOMENTUM_BREAKOUT
```

## Mercado

| Campo | Valor |
| --- | --- |
| Ativo | PETR4 |
| Timeframe | 1d |
| Tipo | Pesquisa quantitativa |
| Operação real | Proibida |

## Evidências

Documentos base:

- `DATASET_EXPLORATORY_ANALYSIS.md`
- `HYPOTHESIS_GENERATION.md`
- `FEATURE_DISCOVERY.md`
- `FEATURE_IMPORTANCE.md`
- `ALPHA101_RESEARCH.md`
- `ALPHA101_FACTORY_APPROVAL.md`
- `ALPHA101_PLAYBOOK.md`
- `ALPHA101_STRATEGY.md`
- `ALPHA101_VALIDATION.md`

## Métricas Finais

| Métrica | Valor |
| --- | ---: |
| Candles avaliados | 2491 |
| BUY signals | 185 |
| Trades não sobrepostos | 88 |
| Win rate | 64.77% |
| Profit Factor | 2.15 |
| Expectancy | 1.33% |
| Retorno acumulado exploratório | 192.14% |
| Drawdown máximo | -20.03% |
| Sharpe por trade | 2.08 |

## Riscos

- descoberta e validação no mesmo dataset;
- sem custos e slippage;
- sem walk-forward formal;
- anos negativos em 2022 e 2024;
- buy-and-hold teve retorno bruto maior;
- risco específico de PETR4;
- risco de overfitting por features escolhidas após EDA.

## Decisão Final

```text
CERTIFIED_WITH_WARNINGS
```

## Justificativa

Alpha101 merece certificação com advertências porque:

- demonstrou expectativa positiva;
- reduziu drawdown em relação ao buy-and-hold;
- gerou amostra razoável de sinais;
- preservou contratos arquiteturais;
- funciona como Strategy de pesquisa;
- não executa ordens.

Ela não recebe certificação plena porque:

- ainda não possui validação out-of-sample;
- ainda não inclui custos operacionais;
- não superou buy-and-hold em retorno bruto;
- precisa de robustez por parâmetros;
- precisa de walk-forward.

## Condições para Uso Futuro

Antes de qualquer avanço operacional:

- executar walk-forward anual;
- aplicar custos conservadores;
- testar sensibilidade dos thresholds;
- comparar contra baseline long-only;
- validar em outros ativos líquidos da B3 apenas por missão aprovada;
- manter operação real proibida.

## Confirmação Operacional

```text
OPERAÇÃO REAL PROIBIDA
CORRETORA NÃO CONECTADA
ORDENS REAIS NÃO AUTORIZADAS
ALPHA101 APENAS PESQUISA/SIMULAÇÃO
```

## Declaração Final

Alpha101 está certificada com advertências como Alpha de pesquisa quantitativa para PETR4 diário. Ela pode ser usada no Replay e no Research Lab para estudo, mas não autoriza operação real.
