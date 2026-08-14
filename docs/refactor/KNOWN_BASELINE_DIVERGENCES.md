# Divergencias Conhecidas Antes da Refatoracao

Data da coleta: 2026-08-13
Base: `8ee6ed9`

## Testes de janela MT5 desatualizados

O runtime canonico define:

```text
200 candles fechados para indicadores
+ 1 candle atual em formacao
= 201 registros solicitados no ciclo leve
```

Sete testes em `tests/test_mt5_market_data_service.py` esperavam o contrato
antigo de 1.000 candles ou permitiam configuracao local abaixo da janela
canonica. Esses testes falhavam antes de qualquer refatoracao funcional.

Resolvido na branch de refatoracao segura: nomes, fixtures e asserts agora
distinguem `configured_closed_candles=200` de `requested_raw_candles=201`.
O diagnostico registra 200 candles recebidos pelo analisador porque o candle
atual e removido antes dos indicadores.
O diagnostico reconhece essa relacao como valida; o fluxo pesado continua
solicitando 5.000 velas somente quando acionado.

## IDs historicos escapando da aposentadoria

Os testes abaixo falhavam porque o fallback por numero considerava o numero do
modelo ativo mesmo quando o ID completo era historico:

```text
MODELO_8_TREND_PULLBACK_H1_M5
MODELO_21_ESPELHO_M19
MODELO_22_ESPELHO_M9
```

O gate ampliado encontrou a mesma causa nos IDs historicos
`MODELO_8_DYNAMIC_EXIT_FROM_M1` ate `MODELO_14_DYNAMIC_EXIT_FROM_M7`.

Os IDs canonicos ativos atuais possuem escopo explicito. A politica deve rejeitar
esses IDs historicos antes de aplicar o fallback numerico.

Risco: uma rota antiga pode abrir ordem mesmo estando fora do conjunto canonico
selecionavel.

Resolvido na branch de refatoracao segura: todos esses IDs foram adicionados a
`RETIRED_LEGACY_MODEL_IDS`. Um teste dedicado confirma simultaneamente que os
legados ficam bloqueados e que os IDs canonicos atuais continuam ativos.

## Pandas analitico em scripts offline de Research

O gate historico `test_adapters_sao_pontos_autorizados_para_formatos_fisicos`
trata qualquer `import pandas` como acesso fisico. Cinco scripts offline em
`research/alpha_suggested/` usam DataFrame sobre payloads JSON ja carregados,
sem chamar `read_csv`, `read_parquet` ou DuckDB.

Decisao: nao ampliar excecoes nem reescrever os motores nesta refatoracao. Uma
missao propria deve separar dependencia analitica de acesso fisico e reconciliar
o texto de governanca com o teste.

## SQLite direto na fachada de aplicacao

`DashboardService` ainda possui tres consultas SQLite diretas. A UI deixou de
importar `sqlite3`: falhas da prova de replay agora saem como
`DashboardServiceError`, preservando a fronteira visual. A extracao completa de
um repositorio SQLite permanece uma refatoracao propria, com testes de paridade
das consultas e rollback independente.

## Suite historica completa

A execucao completa chegou a 790 testes aprovados antes de entrar em testes
historicos de longa duracao. Ela foi interrompida de forma controlada por baixa
velocidade, sem processo residual. O gate oficial desta branch e
`python scripts/run_safe_refactor_gate.py`, que nao acessa MT5 real nem executa
Lab pesado.

## Regra de uso

Nenhuma dessas divergencias pode ser apagada da baseline apenas por exclusao de
teste. Cada uma deve terminar em teste verde por reconciliacao documental ou
correcao isolada do comportamento.
