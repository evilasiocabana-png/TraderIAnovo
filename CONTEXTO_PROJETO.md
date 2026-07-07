# TraderIA_WDO - Contexto do projeto

Este arquivo registra a evolucao do TraderIA_WDO apos a refatoracao para Clean Architecture.

## Ideia central

O TraderIA_WDO e uma base para simular e evoluir um robo de leitura operacional do WDO.

O sistema combina:

- entidades de dominio puras;
- estrategias independentes;
- motor de risco;
- MARKET DNA como memoria operacional;
- persistencia isolada;
- dashboard e analytics separados do dominio.

## Arquitetura atual

```text
TraderIA_WDO/
app.py
config.py
requirements.txt
README.md
core/
domain/
strategies/
market/
backtest/
risk/
analytics/
database/
tests/
```

## Principais decisoes

- `domain/` contem `Candle`, `Operacao` e `MarketState`.
- `core/` orquestra estrategias, risco, ordens, posicoes, broker simulado e eventos.
- `strategies/` padroniza sinais com `StrategySignal`.
- `market/market_dna.py` concentra persistencia e comparacao de padroes do MARKET DNA.
- `risk/risk_engine.py` substitui o gerenciamento antigo de risco.
- `analytics/dashboard.py` gera o HTML estatico do MARKET DNA.
- `database/sqlite.py` isola a persistencia em banco.
- `tests/` valida dominio, engine e MARKET DNA.

## Como executar

```powershell
python app.py
python -m unittest discover -s tests
```
