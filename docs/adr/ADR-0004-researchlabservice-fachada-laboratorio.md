# ADR-0004: ResearchLabService como Fachada do Laboratório Quantitativo

- Status: Aprovado
- Data: 2026-06-26
- Autor: CTO / TraderIA

## Contexto

O Research Lab executa experimentos, simulações e análises quantitativas para
avaliar estratégias.

## Problema

O laboratório não pode se tornar uma camada operacional nem acessar UI,
corretora, MT5 ou arquivos físicos diretamente.

## Alternativas Consideradas

- Research Lab acessando dados físicos diretamente.
- Dashboard executando experimentos diretamente.
- ResearchLabService como fachada de aplicação.

## Decisão Adotada

`ResearchLabService` é a fachada do laboratório quantitativo.

## Justificativa

A fachada preserva o laboratório como ambiente de pesquisa e mantém a obtenção
de candles via provider autorizado.

## Impactos Positivos

- Research Lab permanece restrito a pesquisa e simulação.
- Métricas quantitativas ficam protegidas por contratos.
- UI não conhece detalhes internos do laboratório.

## Impactos Negativos

- Novos experimentos devem respeitar contratos públicos do serviço.

## Riscos

- Introduzir execução real no Research Lab violaria limites operacionais.

## Consequências Futuras

Research Lab nunca deve criar ou enviar ordens reais.

## Referências

- application/research_lab_service.py
- research/research_lab.py
- tests/test_research_contracts.py
- tests/test_research_market_data_provider.py

## Sprints Relacionadas

- SPRINT MARKET DATA 003
- SPRINT MARKET DATA 011
- SPRINT CTO 010
