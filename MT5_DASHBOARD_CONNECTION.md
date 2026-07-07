# MT5_DASHBOARD_CONNECTION.md

## Resumo

A Missao 245 integrou leitura de dados de mercado do MetaTrader 5 ao dashboard do TraderIA em modo exclusivamente read-only.

A nova secao visual e:

- `MT5 MARKET DATA`

Ela aparece na aba `Live` do `dashboard_app.py` e consome dados exclusivamente via `DashboardService`.

## Arquivos criados

- `MT5_DASHBOARD_CONNECTION.md`

## Arquivos alterados

- `infrastructure/market_data/mt5_market_data_provider.py`
- `application/mt5_market_data_service.py`
- `application/dashboard_service.py`
- `application/dashboard_view_model.py`
- `dashboard_app.py`
- `tests/test_mt5_market_data_service.py`
- `tests/test_dashboard_view_model.py`
- `tests/test_dashboard_app_runtime.py`
- `tests/test_dashboard_facade.py`
- `tests/test_application_api.py`

## Como a conexao MT5 funciona

O adaptador `MT5MarketDataProvider` inicializa a biblioteca MT5 em modo de leitura.

O fluxo utilizado e:

1. `Dashboard` chama apenas `DashboardService`.
2. `DashboardService` chama `MT5MarketDataService`.
3. `MT5MarketDataService` chama o provider read-only.
4. O provider utiliza `initialize`, `symbols_get`, `symbol_select` e `copy_rates_from_pos`.
5. Os candles sao convertidos para estruturas internas e expostos ao dashboard.

Nenhum modulo de estrategia, risco, replay, research ou decisao foi alterado.

## Simbolos encontrados

Validacao local em 2026-06-29:

- `EURUSD`
- `GBPUSD`
- `USDCHF`
- `USDJPY`

## Timeframes suportados

- `M1`
- `M5`
- `M15`
- `H1`
- `D1`

## Quantidade de candles carregados

Validacao direta pela fachada:

- simbolo: `EURUSD`
- timeframe: `H1`
- candles carregados: `10`
- ultimo candle: `2026-06-29T07:00:00+00:00`
- OHLC: `1.1383 / 1.13855 / 1.13811 / 1.13848`
- volume: `1866`

Validacao pelo runtime Streamlit:

- botao `Carregar MT5`: OK
- simbolo: `EURUSD`
- timeframe: `H1`
- candles carregados: `100`
- status: `CONNECTED`
- modo: `SOMENTE MARKET DATA`

## Status da conexao local

- servidor: `Pepperstone-Demo`
- conta: `61551556`
- tipo da conta: `0`
- status: `CONNECTED`

## Limitacoes

- A conexao depende do terminal MT5/local estar instalado, autenticado ou configurado com credenciais externas.
- Caso a biblioteca ou terminal nao esteja disponivel, o dashboard exibe erro claro e continua funcionando.
- A integracao e apenas para observabilidade de market data.
- Esta missao nao transforma MT5 em broker operacional.

## Testes executados

```bash
python -m unittest tests.test_mt5_market_data_service tests.test_mt5_market_data_provider tests.test_dashboard_view_model tests.test_dashboard_app_runtime tests.test_application_api
```

Resultado:

```text
28 tests OK
```

```bash
python -m unittest tests.test_dashboard_facade tests.test_dashboard_app_runtime tests.test_application_api tests.test_mt5_market_data_service tests.test_mt5_market_data_provider
```

Resultado:

```text
30 tests OK
```

```bash
python -m unittest discover -s tests
```

Resultado:

```text
3192 tests OK
```

```bash
python scripts\architecture_audit.py
```

Resultado:

```text
Architecture audit status: OK
```

## Validacao manual Streamlit

Comando executado:

```bash
python -m streamlit run dashboard_app.py --server.port 8501 --server.address localhost
```

Resultado:

```text
URL: http://localhost:8501
HTTP 200
```

## Confirmacao de seguranca

- Somente leitura de market data: SIM
- Envio de ordens: NAO
- Abertura de posicao: NAO
- Fechamento de posicao: NAO
- Automacao operacional: NAO
- Operacao real autorizada: NAO
- Dashboard consome MT5 via `DashboardService`: SIM

