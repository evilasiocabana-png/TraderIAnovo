# ADR-0008: IA Não Executa Ordens

- Status: Aprovado
- Data: 2026-06-26
- Autor: CTO / TraderIA

## Contexto

O TraderIA_WDO pode evoluir com recursos analíticos e assistência por IA no
futuro.

## Problema

Permitir que IA execute ordens introduz risco operacional, quebra o pipeline de
decisão e contorna governança.

## Alternativas Consideradas

- IA executando ordens diretamente.
- IA sugerindo sinais sem gates.
- IA restrita a análise, explicação e apoio à pesquisa.

## Decisão Adotada

IA não executa ordens.

## Justificativa

Execução operacional exige contratos, risco, autorização explícita e governança.
IA não pode contornar esses controles.

## Impactos Positivos

- Preserva segurança operacional.
- Mantém Decision Pipeline e Risk Engine como autoridades.
- Evita automação não autorizada.

## Impactos Negativos

- IA fica limitada a apoio analítico enquanto não houver governança específica.

## Riscos

- Integrações futuras podem tentar misturar recomendação e execução.

## Consequências Futuras

Qualquer uso futuro de IA deve permanecer fora da execução real até nova decisão
arquitetural aprovada.

## Referências

- TRADERIA_ARCHITECTURE_BIBLE.md
- ARCHITECTURE_RULES.md
- architecture_manifest.json

## Sprints Relacionadas

- SPRINT CTO 001
- SPRINT CTO 021
