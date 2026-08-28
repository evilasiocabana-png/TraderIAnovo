# Modelo Operacional 26 - Estrutura de candles XAUUSD/M5

## Contrato vigente

- ID legado: `MODELO_26_XAU_M5_SMART_MONEY`, preservado para historico.
- Contrato: `M26_CANDLE_SEQUENCE_V21_20260826`.
- Alpha: `ALPHA026_CANDLE_CONTINUATION_RANGE`.
- Beta: `BETA026_CANDLE_CONTINUATION_RANGE_EXIT`.
- Universo: exclusivamente `XAUUSD`.
- Timeframe: exclusivamente `M5`.
- Janela deslizante: 200 candles fechados; candle atual ignorado na decisao.
- SMA20 e SMA50 nao participam deste contrato. O RSI14 delimita as faixas de
  entrada das rotas de continuidade e lateralizacao e controla a exaustao.

## Cor dos candles

- verde: fechamento acima da abertura;
- vermelho: fechamento abaixo da abertura;
- doji: neutro e incapaz de confirmar sequencia.

## Continuidade

- BUY: um ou mais verdes e um vermelho de pausa; arma `BUY_STOP` na maxima da
  pausa, que executa quando o movimento retoma;
- SELL: um ou mais vermelhos e um verde de pausa; arma `SELL_STOP` na minima da
  pausa, que executa quando o movimento retoma;
- no BUY, o SL inicial fica `0,01` abaixo do microfundo anterior, formado pela
  minima do candle vermelho de recuo;
- no SELL, o SL inicial fica `0,01` acima do microtopo anterior, formado pela
  maxima do candle verde de recuo;
- volume: `0,01`;
- sem TP fixo;
- dois candles fechados contra a posicao geram Full Exit;
- no BUY, depois que o RSI14 superar 70, o retorno abaixo de 70 tambem gera
  Full Exit; no SELL, depois que perder 30, o retorno acima de 30 e o espelho;
- cada nova pausa confirmada pela retomada cria um fundo no BUY ou topo no SELL
  e atualiza o candidato de SL. O Position Manager aplica apenas movimentos
  mais protetivos e nunca afasta o stop atual.

## Lateralizacao

A rota identifica uma correcao pela sequencia fechada, sem aguardar uma vela
adicional de retomada:

- SELL: duas ou mais velas verdes consecutivas, com `30 <= RSI14 < 50`, armam
  `SELL_STOP` na minima da ultima verde. O SL fica `0,01` acima do topo criado,
  isto e, da maior maxima de toda a sequencia verde. O TP fica no ultimo fundo
  estrutural confirmado antes da correcao;
- BUY: duas ou mais velas vermelhas consecutivas, com `50 < RSI14 <= 70`, armam
  `BUY_STOP` na maxima da ultima vermelha. O SL fica `0,01` abaixo do fundo
  criado, isto e, da menor minima de toda a sequencia vermelha. O TP fica no
  ultimo topo estrutural confirmado antes da correcao.

O volume e `0,02`. Esta rota preserva seu SL e TP e nao recebe a gestao
dinamica da continuidade.

## Coexistencia das rotas

- continuidade e lateralizacao sao avaliadas independentemente no mesmo ciclo;
- quando os dois padroes estiverem prontos, podem existir simultaneamente uma
  ordem `CONT` e uma ordem `LAT`;
- cada rota mantem no maximo uma pendencia ou posicao propria por simbolo;
- atualizar a pendencia `CONT` substitui somente `CONT`; atualizar `LAT`
  substitui somente `LAT`;
- comentarios MT5 e auditoria carregam o token da rota para impedir mistura.

## Identidade operacional V22

Cada plano M26 transporta obrigatoriamente `active_signal_kind`, `setup_id` e
`route_key` desde a decisao ate o Robot Service e o provider. O controle de
candle processado usa `simbolo + timeframe + modelo + rota`, e nao somente o
modelo. Portanto, a avaliacao de `LATERALIZATION` ou `EXHAUSTION` nunca consome
o candle de uma `CONTINUATION` valida. A mesma rota continua idempotente: o
mesmo candle nao pode gerar duas ordens iguais.

Antes de materializar qualquer plano, o M26 valida entrada e SL, lado da ordem
pendente e TP estrutural da lateralizacao. Uma decisao incoerente e descartada
antes do provider, com cobertura automatizada para impedir regressao.

## Runtime e seguranca

- usa somente o snapshot compartilhado `XAUUSD/M5`;
- nenhuma leitura MT5 adicional e nenhum Lab pesado no ciclo;
- continuidade de alta e `verde + vermelha + verde rompendo a maxima da
  vermelha`; apos `verde + vermelha`, arma `BUY_STOP` na maxima da pausa com
  `50 < RSI14 <= 70`, ou `SELL_STOP` na minima da pausa verde com
  `30 <= RSI14 < 50` no espelho `vermelha + verde + vermelha`; a lateralizacao
  usa `BUY_STOP` apos duas ou mais vermelhas e `SELL_STOP` apos duas ou mais
  verdes, sem aguardar candle adicional de confirmacao;
- exaustao BUY entra a mercado quando o RSI14 estava abaixo de 30 e cruza para
  cima de 30; exaustao SELL e o espelho, entrando quando estava acima de 70 e
  cruza para baixo de 70;
- o cruzamento e persistido ate a confirmacao da execucao. Um cruzamento oposto
  mais recente substitui somente o alerta antigo, sem gerar entrada retroativa
  durante migracao de contrato;
- na entrada por exaustao, o SL da venda fica exatamente na maxima do candle
  fechado que confirmou o cruzamento, e o SL da compra fica na minima dele;
- apos BUY, o primeiro retorno abaixo de 50 depois de conquista-lo gera Full
  Exit; se o RSI conquistar 70, o retorno abaixo de 70 tambem gera Full Exit;
- apos SELL, o primeiro retorno acima de 50 depois de perde-lo gera Full Exit;
  se o RSI perder 30, o retorno acima de 30 tambem gera Full Exit;
- enquanto nenhum Full Exit ocorrer, cada novo microfundo confirmado no BUY ou
  microtopo confirmado no SELL produz um candidato de SL. O Position Manager
  aplica somente niveis mais protetivos, portanto o SL nunca recua;
- o lote da rota e gravado no Trade Plan e preservado quando M23 copiar M26;
- a Saida Teorica le `active_signal_kind` do Trade Plan para identificar
  `CONTINUATION`, `LATERALIZATION` ou `EXHAUSTION`; contratos antigos usam o
  comentario tecnico `M26 CONT`, `M26 LAT` ou `M26 EXH` como fallback;
- opera somente em conta Demo;
- a protecao nunca afasta um SL existente.

## Incidente do alerta oposto impedir exaustao - 26/08/2026

Um alerta BUY antigo, armado quando o RSI esteve abaixo de 30, permanecia
gravado e impedia o codigo anterior de armar SELL quando o RSI posteriormente
superava 70. Em 26/08, o RSI14 do XAUUSD/M5 atingiu `74,49` e depois formou
duas velas vermelhas fechadas, mas o estado continuou somente com
`buy_armed=true`; por isso nenhuma ordem SELL de exaustao chegou ao provider.

O contrato V19 corrige a origem e simplifica o gatilho: o cruzamento de retorno
do RSI e a propria confirmacao da entrada. O extremo mais recente invalida
apenas o alerta oposto obsoleto, preserva o novo alerta ate sua entrada ser
aceita e nao abre retroativamente sinais antigos durante migracao. Continuidade
e lateralizacao permanecem independentes.

Na mesma validacao, a sonda direta revelou que a colecao NumPy retornada por
`copy_rates_from_pos()` ainda era submetida a uma avaliacao booleana ambigua
antes da conversao para lista. O limite de entrada agora testa apenas
`candles is not None`, permitindo tanto arrays NumPy quanto listas do cache.

## Incidente de adaptacao dos candles MT5 - 26/08/2026

O provider de execucao entrega `copy_rates_from_pos()` como registros
estruturados do NumPy. Esses registros aceitam acesso por chave (`row["open"]`),
mas nao sao `dict` e tambem expõem `data` como buffer interno. O adaptador M26
anterior confundia esse buffer com o horario e rejeitava OHLC valido. O efeito
operacional era manter a posicao com `M26_EXIT_DADOS_INVALIDOS`, impedindo Full
Exit e movimento de SL mesmo quando o padrao de candles estava confirmado.

O contrato vigente exige que o adaptador:

- aceite `Mapping`, objetos de dominio e registros estruturados do NumPy;
- priorize os nomes declarados em `dtype.names` antes de atributos internos;
- mantenha o candle em formacao fora da decisao;
- cubra em teste o Full Exit sobre o mesmo formato retornado pelo MT5.

Na reproducao de 26/08/2026, uma posicao SELL de continuidade encontrou duas
velas M5 verdes fechadas as 12:40 e 12:45. Com o adaptador corrigido, o resultado
e `M26_CONTINUATION_EXIT_DOIS_VERDES_SELL`. A entrada de lateralizacao permanece
uma decisao independente e somente fica pronta depois de sua terceira vela de
confirmacao e do enquadramento na faixa RSI da direcao correspondente.

## Incidente de falso bloqueio por sonda externa - 26/08/2026

Um SELL de exaustao estava pronto, com alerta persistente e duas velas M5
vermelhas fechadas, mas o gate antecipado transformava a indisponibilidade
transitoria da sonda externa de posicoes em "posicao duplicada". O provider
atomico mostrava que nao havia posicao M26; havia apenas uma posicao M23 no
mesmo XAUUSD, que deve coexistir por ser outro modelo.

O contrato operacional passa a exigir:

- falha de leitura externa nunca pode ser classificada como duplicidade M26;
- o M26 atravessa o gate antecipado e e validado novamente pelo provider,
  imediatamente antes do `order_send`;
- `CONT`, `LAT` e `EXH` sao rotas distintas e podem coexistir;
- somente a mesma combinacao `XAUUSD + M26 + rota` e bloqueada;
- a entrada de exaustao continua a mercado, com SL na maxima da ultima vela
  fechada para SELL e na minima da ultima vela fechada para BUY;
- testes de regressao devem cobrir falha da sonda, coexistencia entre rotas e
  bloqueio da duplicidade verdadeira.
