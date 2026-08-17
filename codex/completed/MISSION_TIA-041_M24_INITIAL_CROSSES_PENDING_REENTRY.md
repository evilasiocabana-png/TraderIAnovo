# MISSION_TIA-041_M24_INITIAL_CROSSES_PENDING_REENTRY

Status: completed

Data: 2026-08-17

## Objetivo

Separar no M24 os cruzamentos da entrada inicial, permitindo que preco/SMA20 e
RSI14/50 confirmem em candles M5 diferentes, e transformar a reentrada em ordem
pendente sem exigir novos cruzamentos.

## Implementacao

- Entrada inicial BUY memoriza o cruzamento do preco acima da SMA20 e do RSI14
  acima de 50; SELL aplica a regra simetrica.
- O segundo evento somente libera a entrada quando o primeiro continua valido.
- A entrada principal permanece a mercado, com SL no micro pivo anterior mais
  proximo confirmado nos ultimos cinco M5.
- Reentrada BUY exige fechamento acima da SMA20 e RSI14 acima de 50; SELL exige
  fechamento abaixo da SMA20 e RSI14 abaixo de 50, sem novo cruzamento.
- A reentrada gera BUY_STOP na maxima ou SELL_STOP na minima do ultimo M5 e e
  recalculada a cada novo candle.
- A protecao que ignora a primeira oportunidade depois do Full Exit RSI 70/30
  foi preservada.
- Escritas atomicas do estado M24 repetem bloqueios curtos do Windows/OneDrive.
- O ciclo Demo deixa o M24 materializar o plano proprio M5 mesmo quando o
  plano-base heuristico H1 estiver sem gatilho.
- O avaliador aceita diretamente `Candle` canonico com campos em portugues,
  eliminando o falso `M24_DADOS_INVALIDOS` do runtime.
- Trava de escopo impede que o plano XAU seja materializado sobre linhas de
  outros ativos.

## Seguranca

Validacao feita com candles sinteticos, arquivos temporarios e provider local.
Nenhuma operacao MT5 real foi aberta, fechada ou modificada.

## Validacao

- testes direcionados M24, Position Manager e provider: 77 aprovados;
- `python scripts/run_critical_ci.py`: 188 testes aprovados;
- `python -m py_compile`: aprovado.

## Commit funcional

`7350e4b`, `d665719`, `f91c01b` e `1553f7e` em
`codex/multi-ea-trading-lab`.
