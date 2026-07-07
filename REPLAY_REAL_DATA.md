# REPLAY_REAL_DATA.md

## Missao 221 - Replay Real Data

Sprint 14 - TraderIA UX Consolidation  
Projeto: TraderIA  
Data: 2026-06-28

## Objetivo

Eliminar o Replay demonstrativo da experiencia principal do Dashboard.

## Implementacao

A aba Replay passou a usar como acao principal:

```text
Carregar Dataset Selecionado
```

O carregamento usa exclusivamente:

- `DashboardService`
- `HistoricalDataProvider`
- dataset certificado
- `metadata.json`
- `checksum.sha256`

O Dashboard nao acessa arquivos, provider ou diretorios diretamente.

## Informacoes Exibidas

- dataset selecionado;
- ativo;
- timeframe;
- provider;
- readiness;
- candle atual;
- posicao;
- progresso;
- quantidade total de candles;
- eventos do Replay;
- operacao real nao autorizada.

## Correcao Importante

O `ReplayService` agora preserva `active_symbol` e `active_timeframe` do `HistoricalDataset`.

Assim, ao carregar PETR4 1D, o `MarketSnapshot` gerado pelo Replay passa a usar:

```text
symbol = PETR4
timeframe = 1d
```

## Teste de Protecao

Foi criado teste garantindo que dataset PETR4 gera `DecisionContext.market_snapshot.symbol == PETR4`.

## Resultado

Replay real alinhado ao dataset certificado.
