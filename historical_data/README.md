# Historical Data

Esta pasta define a estrutura oficial para datasets historicos do TraderIA_WDO.

Ela nao substitui providers, adapters, Replay ou Research Lab. Toda leitura
funcional de dados historicos continua passando exclusivamente pelo
`HistoricalDataProvider` e pelas portas ja protegidas pela arquitetura.

## Objetivo

Estabelecer uma base padronizada para descoberta, armazenamento controlado e
validacao de datasets historicos internos.

## Estrutura Oficial

```text
historical_data/
    README.md
    datasets/
        README.md
        <symbol>/
            <timeframe>/
                <year>/
                    <dataset files>
                    metadata.json
```

Exemplo de organizacao:

```text
historical_data/
    datasets/
        WDO/
            1m/
                2025/
                    WDO_1m_2025.parquet
                    metadata.json
```

Nenhum arquivo de candle e obrigatorio para a aplicacao inicializar. Quando
existir dataset local, ele deve seguir esta estrutura e possuir metadados.

## Padrao de Dataset

Cada dataset historico futuro deve declarar:

- ativo;
- timeframe;
- timezone;
- fonte;
- periodo;
- formato;
- quantidade de candles;
- integridade;
- versao.

## Nomenclatura

O padrao oficial de caminho e:

```text
historical_data/datasets/<symbol>/<timeframe>/<year>/
```

Regras:

- `symbol`: codigo do ativo em maiusculas, por exemplo `WDO`.
- `timeframe`: granularidade em formato curto, por exemplo `1m`, `5m`, `1h`.
- `year`: ano com quatro digitos.
- arquivos de dados devem manter symbol, timeframe e periodo no nome.

## Metadados Minimos

Todo dataset futuro deve possuir metadados equivalentes a:

```json
{
  "symbol": "WDO",
  "timeframe": "1m",
  "exchange": "B3",
  "timezone": "America/Sao_Paulo",
  "first_timestamp": "2025-01-01T09:00:00-03:00",
  "last_timestamp": "2025-12-30T18:00:00-03:00",
  "candle_count": 0,
  "source": "provider-origem",
  "version": "1.0",
  "checksum": "opcional"
}
```

Campos obrigatorios:

- `symbol`
- `timeframe`
- `exchange`
- `timezone`
- `first_timestamp`
- `last_timestamp`
- `candle_count`
- `source`
- `version`

Campo opcional:

- `checksum`

## Regras Arquiteturais

- Esta pasta nao substitui `HistoricalDataProvider`.
- Esta pasta nao autoriza leitura direta por Replay, Research Lab, Dashboard ou
  dominio.
- Datasets locais so devem ser adicionados por missao explicita.
- Credenciais, dados sensiveis e dados operacionais privados nao devem ser
  armazenados aqui.
- Validacoes futuras devem preservar determinismo, rastreabilidade e isolamento
  de adapters.
