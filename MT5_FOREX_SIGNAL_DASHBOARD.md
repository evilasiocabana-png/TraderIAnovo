# MT5 Forex Signal Dashboard

## Resumo Executivo

A Missao 245 criou uma tela principal de Forex no dashboard do TraderIA consumindo dados de mercado do MetaTrader 5 em modo somente leitura.

O dashboard passa a exibir imediatamente os oito pares Forex institucionais:

- EURUSD
- GBPUSD
- USDCHF
- USDJPY
- AUDUSD
- NZDUSD
- EURJPY
- GBPJPY

Cada par apresenta status, ultimo preco, horario do ultimo candle, tendencia, momentum, volatilidade, RSI, medias moveis, decisao BUY/SELL/WAIT, confianca e motivo textual.

## Arquivos Criados

Nenhum modulo estrutural novo foi criado para execucao operacional.

Este relatorio foi criado:

- `MT5_FOREX_SIGNAL_DASHBOARD.md`

## Arquivos Alterados

- `application/mt5_market_data_service.py`
- `application/dashboard_service.py`
- `application/dashboard_view_model.py`
- `infrastructure/market_data/mt5_market_data_provider.py`
- `dashboard_app.py`
- `tests/test_application_api.py`
- `tests/test_dashboard_app_runtime.py`
- `tests/test_dashboard_facade.py`
- `tests/test_dashboard_view_model.py`
- `tests/test_mt5_market_data_provider.py`
- `tests/test_mt5_market_data_service.py`

## Como a Tela Funciona

Fluxo implementado:

```text
MT5 Market Data
        |
        v
MT5MarketDataProvider
        |
        v
MT5MarketDataService
        |
        v
DashboardService
        |
        v
dashboard_app.py
```

A interface nao acessa o MT5 diretamente. A tela `MT5 Forex` consome informacoes por meio do `DashboardService`.

## Pares Disponiveis

Na validacao local com MT5 conectado ao servidor `Pepperstone-Demo`, todos os pares obrigatorios foram encontrados:

- EURUSD
- GBPUSD
- USDCHF
- USDJPY
- AUDUSD
- NZDUSD
- EURJPY
- GBPJPY

## Pares Indisponiveis

Nenhum par obrigatorio ficou indisponivel na validacao local.

Quando um par nao existir no terminal MT5, o dashboard exibe:

```text
INDISPONIVEL NO MT5
```

e a decisao permanece:

```text
WAIT
```

## Timeframe

Timeframe padrao:

```text
H1
```

Timeframes previstos na interface:

- M1
- M5
- M15
- H1
- H4
- D1

## Indicadores Usados

A logica inicial usa apenas indicadores simples, rastreaveis e calculados a partir dos candles carregados:

- media curta: 20 candles
- media longa: 50 candles
- RSI: 14 candles
- momentum: retorno dos ultimos 10 candles
- volatilidade: desvio padrao populacional dos retornos dos ultimos 20 candles

## Logica de Decisao

### BUY

Gerado quando:

- media curta acima da media longa;
- momentum positivo;
- RSI abaixo de zona extrema de sobrecompra;
- volatilidade suficiente.

### SELL

Gerado quando:

- media curta abaixo da media longa;
- momentum negativo;
- RSI acima de zona extrema de sobrevenda;
- volatilidade suficiente.

### WAIT

Gerado quando:

- sinais conflitantes;
- volatilidade insuficiente;
- dados insuficientes;
- par indisponivel;
- MT5 desconectado;
- tendencia indefinida.

Toda decisao exibe motivo textual.

## Exemplos de Decisao

Validacao local com MT5 conectado:

| Par | Decisao | Confianca | Exemplo de motivo |
| --- | --- | --- | --- |
| EURUSD | WAIT | 0.50 | Sinais conflitantes entre tendencia, momentum e RSI. |
| AUDUSD | SELL | 0.62 | Tendencia negativa, momentum negativo, RSI saudavel e volatilidade suficiente. |
| EURJPY | BUY | 0.58 | Tendencia positiva, momentum positivo, RSI saudavel e volatilidade suficiente. |
| GBPJPY | BUY | 0.61 | Tendencia positiva, momentum positivo, RSI saudavel e volatilidade suficiente. |

## Seguranca Operacional

O dashboard exibe aviso fixo:

```text
SOMENTE ANALISE DE MERCADO. NENHUMA ORDEM REAL SERA ENVIADA.
```

A integracao MT5 permanece exclusivamente read-only.

Funcoes operacionais proibidas continuam ausentes do fluxo:

- envio de ordens;
- checagem de ordens;
- abertura de posicao;
- fechamento de posicao;
- modificacao de posicao.

## Limitacoes

- A logica BUY/SELL/WAIT e uma heuristica inicial de leitura de mercado, nao uma Alpha final.
- A disponibilidade dos pares depende do terminal MT5 instalado, logado e com os simbolos habilitados.
- Em ambientes de teste isolados sem MT5 conectado, a tela exibe os oito pares com status de desconexao e decisao WAIT.
- O dashboard nao executa ordens e nao possui autorizacao operacional.

## Testes Executados

```bash
python -m unittest tests.test_mt5_market_data_service tests.test_mt5_market_data_provider tests.test_dashboard_view_model tests.test_dashboard_app_runtime tests.test_dashboard_facade tests.test_application_api
```

Resultado:

```text
39 tests OK
```

```bash
python scripts\architecture_audit.py
```

Resultado:

```text
Architecture audit status: OK
```

```bash
python -m unittest discover -s tests
```

Resultado:

```text
3195 tests OK
```

```bash
python app.py
```

Resultado:

```text
Executado com sucesso.
```

```bash
python -m streamlit run dashboard_app.py --server.port 8501 --server.address localhost
```

Resultado:

```text
Streamlit iniciado em http://localhost:8501
HTTP 200 confirmado.
```

## Confirmacao

O TraderIA mostra os oito pares Forex vindos do MT5 com analise BUY/SELL/WAIT quando o terminal MT5 esta conectado e os simbolos estao disponiveis.

Nao existe envio de ordem nesta implementacao.

Operacao real permanece proibida.
