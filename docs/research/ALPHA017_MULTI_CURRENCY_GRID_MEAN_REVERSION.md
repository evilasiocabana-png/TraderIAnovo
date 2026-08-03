# ALPHA017 - Multi-Currency Grid Mean Reversion

## Estado

`RESEARCH_ONLY`. Esta Alpha pertence ao Lab/Replay e nao esta associada a um
modelo operacional, ao Robo Demo, ao Position Manager ou ao provider MT5.

## Origem da hipotese

A hipotese foi inspirada no perfil publico de estrategias multiativos com alta
frequencia de acertos e retorno a media. A regra proprietaria observada nao e
publica; portanto, a ALPHA017 e uma formulacao original, explicita e auditavel.

## Hipotese

Quando o preco alcanca um extremo estatistico em mercado sem tendencia forte,
existe possibilidade de retorno a media. A entrada inicial exige confirmacao
simultanea por:

- preco fora ou sobre a Banda de Bollinger;
- `Z-Score` extremo;
- RSI em sobrecompra ou sobrevenda;
- ADX abaixo do limite de tendencia;
- ATR valido e largura das bandas controlada em relacao ao ATR.

## Regras candidatas

### Compra

```text
preco <= banda inferior
Z-Score <= -limite
RSI <= sobrevenda
ADX <= maximo
largura Bollinger / ATR <= maximo
```

### Venda

```text
preco >= banda superior
Z-Score >= limite
RSI >= sobrecompra
ADX <= maximo
largura Bollinger / ATR <= maximo
```

### Espera

Qualquer requisito ausente ou desalinhado produz `WAIT`. ADX acima do limite
bloqueia expressamente a hipotese para evitar grade contra tendencia forte.

## Grade inicial de pesquisa

- RSI: `25/75` e `30/70`;
- Z-Score: `1.5`, `2.0` e `2.5`;
- ADX maximo: `18`, `22` e `25`;
- stop substituto de Replay: `2.5 ATR`;
- RR substituto de Replay: `0.5`, `0.75` e `1.0`;
- largura Bollinger maxima: `6 ATR`.

O SL/TP acima existe apenas para o Replay de uma posicao unica. Ele nao valida
grade, progressao de lote, cesta de pares ou encerramento por lucro agregado.

## Limites de seguranca

- nao abre ordens em grade;
- nao aumenta lote;
- nao calcula martingale;
- nao altera Position Manager;
- nao gera plano operacional MT5;
- nao e automaticamente promovida a modelo;
- correlacao e exposicao agregada ainda precisam de um contrato de portfolio.

## Proxima decisao

Executar a pesquisa explicita no Lab/Replay, comparar amostra, profit factor,
expectativa e drawdown por par/timeframe. Somente uma missao posterior e
explicitamente aprovada pode definir uma Beta de cesta e promover a Alpha a um
novo modelo Demo.
