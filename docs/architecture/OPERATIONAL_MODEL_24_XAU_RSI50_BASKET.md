# Modelo Operacional 24 — XAU/M5 RSI50 Basket

## Identidade

- ID: `MODELO_24_XAU_RSI50_BASKET`.
- Variantes: `MODELO_24_XAU_RSI50_BASKET_SOURCE_M<n>`.
- Fontes permitidas: M8, M10, M18, M19, M20, M21 e M22.
- Ativo/timeframe: `XAUUSD/M5`.
- Comentário MT5: `TraderIA M24 S<n>`.
- Estado e auditoria são próprios; M23 nunca compartilha posições, resultado ou arquivo de estado com M24.

## Entrada inicial

O candle M5 precisa estar fechado. A entrada é a mercado.

BUY exige simultaneamente:

1. microfundo 1+1 confirmado nos últimos cinco candles M5;
2. RSI14 estritamente de abaixo de 50 para acima de 50;
3. fechamento do candle-sinal acima da SMA20;
4. aprovação dos filtros específicos da fonte.

SELL é simétrico: microtopo 1+1, RSI14 de acima de 50 para abaixo de 50 e fechamento abaixo da SMA20.

O SL inicial fica no micropivô confirmado. A saída individual da entrada inicial continua sendo a saída nativa da fonte: cruzamento confirmado RSI 70/30 ou inversão SMA20/50.

## Reentrada 1 — estrutural Stop

- Mantém o gatilho estrutural da fonte.
- BUY_STOP na máxima / SELL_STOP na mínima do candle M5 anterior.
- A pendente é reposicionada a cada novo M5 fechado enquanto o contrato da fonte continuar válido.
- Mantém o SL estrutural da fonte.
- Não possui TP individual.
- É reentrada para a regra de invalidação RSI50.

## Reentrada 2 — RSI50 a mercado

BUY exige SMA20>SMA50 e RSI14 cruzando 50 de baixo para cima no fechamento M5. SELL exige SMA20<SMA50 e RSI14 cruzando 50 de cima para baixo.

- Entrada a mercado.
- SL inicial no extremo do candle imediatamente anterior.
- A cada novo M5 fechado, o SL candidato passa para a mínima anterior no BUY ou máxima anterior no SELL.
- O SL só é modificado quando melhora a proteção e continua no lado válido do preço; nunca é afastado.
- Não possui TP individual.
- Perda do RSI50 ou inversão SMA20/50 produz Full Exit individual de segurança.

## Ordem de precedência

1. cruzamento RSI50 válido para a etapa atual (inicial ou reentrada a mercado);
2. reentrada estrutural Stop da fonte;
3. aguardar.

O primeiro cruzamento RSI50 de cada nova direção é classificado como entrada inicial. Depois do aceite do provider Demo, os próximos cruzamentos na mesma direção são reentradas. A mudança de direção reinicia a classificação.

## Cesta financeira

- TP nativo MT5: sempre `0.0` para M24.
- Alvo coletivo: resultado líquido da cesta M24 `>= +US$1.000`, somando `profit + swap + commission + fee` expostos pelo MT5.
- Atingido o alvo, todas e somente as posições com comentário M24 são fechadas a mercado.
- Posições M23 e posições diretas não participam da cesta M24.

## Persistência

- `.traderia/model24_runtime_state.json`: consumo da entrada inicial por fonte/direção.
- `.traderia/model24_basket_state.json`: estado financeiro compacto da cesta.
- `.traderia/model24_basket_audit.jsonl`: auditoria dos Full Exits coletivos.

## Segurança e validação

- Somente conta MT5 Demo passa pelo provider.
- A criação e os testes do modelo não enviam ordens.
- O candle dos indicadores deve coincidir com o candle do Trade Plan.
- M24 é modelo ativo e selecionável, mas não é ativado automaticamente pela implantação.
- Testes dedicados cobrem gatilho inicial, ausência de micropivô, reentrada RSI50, isolamento M23/M24, seleção das sete fontes, retirada de TP e comentário MT5.
