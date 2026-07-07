# MARKET_DNA_ALIGNMENT.md

## Missao 223 - Market DNA Alignment

Sprint 14 - TraderIA UX Consolidation  
Projeto: TraderIA  
Data: 2026-06-28

## Objetivo

Alinhar o Market DNA ao dataset atualmente em uso no Replay.

## Implementacao

A aba Market DNA agora segue esta regra visual:

```text
Se existe candle atual no Replay:
    exibir Market DNA derivado do candle atual do Replay
Senao:
    informar que nenhum Replay real foi carregado
```

## Correcao Estrutural

O `ReplayService` deixou de gerar `MarketSnapshot` sempre com `symbol="WDO"`.

Agora o snapshot usa o simbolo do dataset historico carregado.

## Resultado

Market DNA nao mostra mais leitura de ativo diferente do Replay em uso.

## Limitacao

A leitura ainda depende dos engines existentes de feature/regime/research. Nao foi criado novo classificador nem nova logica de Market DNA.
