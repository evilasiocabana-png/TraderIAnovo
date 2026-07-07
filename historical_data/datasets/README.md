# Historical Datasets

Este diretorio reserva o local oficial para datasets historicos internos.

Nenhum dataset real e obrigatorio para a aplicacao funcionar. Quando houver
dataset local importado, ele deve seguir a estrutura aprovada e ser lido apenas
pelos providers/adapters oficiais.

## Estrutura Aprovada

```text
datasets/
    <symbol>/
        <timeframe>/
            <year>/
                <dataset files>
                metadata.json
```

Exemplo:

```text
datasets/
    WDO/
        1m/
            2025/
                WDO_1m_2025.parquet
                metadata.json
```

## Contrato de Metadados

`metadata.json` deve conter, no minimo:

- `symbol`
- `timeframe`
- `exchange`
- `timezone`
- `first_timestamp`
- `last_timestamp`
- `candle_count`
- `source`
- `version`

Opcional:

- `checksum`

## Politica

- Nao tornar dataset local requisito para inicializacao da aplicacao.
- Nao exigir arquivos reais para a suite de testes passar.
- Nao ler dados diretamente desta pasta fora dos providers/adapters oficiais.
- Nao incluir credenciais ou dados sensiveis no repositorio.
