# ADR-0009: Operação Real Permanece Desabilitada

- Status: Aprovado
- Data: 2026-06-26
- Autor: CTO / TraderIA

## Contexto

O TraderIA_WDO possui replay, simulação, pesquisa quantitativa e paper trading
visual.

## Problema

Habilitar operação real sem sprint específica, revisão de risco e aprovação
formal criaria risco financeiro e arquitetural.

## Alternativas Consideradas

- Permitir operação real parcial.
- Integrar MT5 ou corretora imediatamente.
- Manter operação real desabilitada.

## Decisão Adotada

Operação real permanece desabilitada.

## Justificativa

O projeto ainda está orientado a pesquisa, replay, simulação e paper trading
visual. Operação real exige governança própria.

## Impactos Positivos

- Elimina risco de envio acidental de ordens reais.
- Mantém foco em validação quantitativa.
- Preserva clareza dos limites operacionais.

## Impactos Negativos

- O sistema não executa ordens reais.

## Riscos

- Integrações futuras com corretora ou MT5 devem ser bloqueadas sem aprovação.

## Consequências Futuras

Qualquer habilitação operacional real exigirá nova sprint, novo ADR, atualização
de manifesto, baseline, testes e autorização explícita do CTO.

## Referências

- README.md
- ARCHITECTURE_RULES.md
- docs/ARCHITECTURE_CHANGE_WORKFLOW.md

## Sprints Relacionadas

- SPRINT CTO 001
- SPRINT CTO 026
- SPRINT CTO 027
