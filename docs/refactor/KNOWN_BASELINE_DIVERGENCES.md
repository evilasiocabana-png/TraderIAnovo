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

Sete testes em `tests/test_mt5_market_data_service.py` ainda esperam o contrato
antigo de 1.000 candles ou permitem configuracao local abaixo da janela
canonica. Esses testes falham antes de qualquer refatoracao funcional.

Acao futura: atualizar nomes, fixtures e asserts para distinguir claramente
`configured_closed_candles=200` de `requested_raw_candles=201`, sem mudar o
runtime.

## IDs historicos escapando da aposentadoria

Os testes abaixo falham porque o fallback por numero considera o numero do
modelo ativo mesmo quando o ID completo e historico:

```text
MODELO_8_TREND_PULLBACK_H1_M5
MODELO_21_ESPELHO_M19
MODELO_22_ESPELHO_M9
```

Os IDs canonicos ativos atuais possuem escopo explicito. A politica deve rejeitar
os tres IDs historicos antes de aplicar o fallback numerico.

Risco: uma rota antiga pode abrir ordem mesmo estando fora do conjunto canonico
selecionavel.

Acao futura: incremento isolado em `domain/operational_model_policy.py`, com os
testes existentes como criterio de aceite e sem alterar IDs canonicos ativos.

## Regra de uso

Nenhuma dessas divergencias pode ser apagada da baseline apenas por exclusao de
teste. Cada uma deve terminar em teste verde por reconciliacao documental ou
correcao isolada do comportamento.
