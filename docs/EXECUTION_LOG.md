# Execution Log

## 2026-08-13 - Sinal M5 volta a gerar ordem pendente e copia M23 independente

- corrigida a expiracao da ordem Stop: o timestamp do ultimo candle fechado e
  sua abertura, portanto a pendencia vale ate o fechamento do candle corrente;
- removida a falsa duplicidade entre a ordem direta e sua copia M23;
- mantida a deduplicacao do mesmo modelo/carteira no mesmo candle;
- confirmado no MT5 Demo que sinais diretos e M23 voltaram a receber
  `Request executed`, sem reaproveitar gatilho Stop ja rompido;
- ciclo leve verificado online, com leitura compartilhada de 200 velas e app
  saudavel na porta 8532.

## 2026-08-13 - Cruzamento inicial e reentradas ilimitadas da familia SMA20/50

- M7 permaneceu inalterado.
- Do M8 em diante, nos modelos baseados em SMA20/50 + RSI50, primeira entrada exige
  cruzamento novo no ultimo candle M5 fechado e os filtros proprios aprovados.
- Tendencia ja cruzada passa ao fluxo de reentrada, sem entrada imediata a mercado.
- Reentradas deixam de ter limite numerico: continuam exigindo posicao anterior
  encerrada, recuo estrutural, retomada e novo candle/plano nao duplicado.
- M23 herda o contrato da fonte e conserva como regra adicional somente o Full Exit
  coletivo de +US$1.000 sobre as suas proprias posicoes.

## 2026-08-13 - M23 passa a herdar tambem a saida dinamica da fonte

- removido o bloqueio que excluia tickets M23 do Position Manager;
- o registro da ordem M23 agora conserva modelo, politica e Beta nativos da fonte;
- cada posicao M23 continua com SL/TP individual e volta a obedecer ao Full Exit
  dinamico de sua origem;
- o Full Exit coletivo de +US$1.000 permanece como regra adicional e exclusiva
  da cesta M23;
- 12 vendas XAUUSD/M23 antigas, abertas pelas fontes M8/M10 e ja invalidadas
  pelo cruzamento SMA20/SMA50, foram encerradas na conta Pepperstone-Demo.

## 2026-08-13 - Janela deslizante canonica de 200 velas fechadas

- A janela anterior solicitava 52 registros e removia a vela atual, deixando
  apenas 51 velas fechadas para os indicadores.
- A auditoria de ordens confirmou `LOCAL_MT5_CANDLES_52` e encontrou leitura
  indicadora defasada em relacao ao horario de geracao do plano.
- O runtime agora solicita 201 registros, ordena e deduplica por timestamp,
  exclui a vela em formacao e calcula sobre exatamente 200 fechamentos.
- A regra foi aplicada ao fluxo principal, modelos M5, adaptadores do Lab,
  contextos e Position Manager. Os parametros do Lab permanecem congelados.
- A fonte nova e `LOCAL_MT5_CLOSED_CANDLES_200`; a fonte antiga permanece aceita
  apenas para compatibilidade de auditoria de ordens legadas.
- Testes provam que mudar a vela em formacao nao altera indicadores e que a
  janela so desliza quando surge um novo candle.

## 2026-08-12 - M23 habilitado junto com modelos diretos

- criado modo persistente `MODELOS_SELECIONADOS_COM_M23`;
- permitida selecao simultanea de fontes diretas e M23 no chaveamento;
- cada sinal aprovado pode gerar uma ordem direta e uma copia M23 auditavel;
- preservados entrada, SL, TP, candle e deduplicacao de cada rota;
- mantida uma unica leitura compartilhada do universo por ciclo;
- mantido como unica regra coletiva do M23 o Full Exit em +US$1.000 liquidos.

## 2026-08-12 - M23 simplificado para Full Exit unico

- removidos do caminho operacional o stop financeiro global e o trailing da cesta;
- removido o gate de orcamento agregado dos SL antes de novas entradas;
- mantidos os SL/TP individuais herdados de cada modelo-fonte;
- permitidas reentradas da mesma fonte/par quando houver novo sinal executavel;
- mantida a deduplicacao do mesmo plano no mesmo candle;
- definida como unica zeragem coletiva o Full Exit a mercado em +US$1.000 liquidos;
- estados persistidos pelas regras antigas sao migrados sem disparar fechamento.

## 2026-08-12 - M23 acumulador financeiro

- criado o roteamento exclusivo das entradas dos modelos ativos para M23;
- preservados os gates de cada fonte e removidos SL/TP individuais da cesta;
- implementado limite de uma posicao por modelo-fonte e par;
- implementados stop global em -US$300 e trailing apos +US$300 com recuo de 25%;
- definido Full Exit de toda a cesta **a mercado** ao atingir +US$1.000;
- adicionados estado persistente, auditoria, trava de zeragem e candle novo;
- isolado o M23 do Position Manager legado;
- adicionados seletor, status leve e curva M23 no Relatorio;
- validado sem envio ao MT5 real por testes automatizados.

## 2026-08-12 - Retirada operacional de M3, M4, M6, M13, M14 e M15

- M3, M4, M6, M13, M14 e M15 foram removidos do seletor, do radar de entrada
  MT5 e dos graficos e filtros ativos do Relatorio.
- O conjunto operacional passou a ser M1, M2, M5, M7, M8, M10 e M16-M22.
- O Robo Demo e o provider rejeitam qualquer nova ordem dos modelos retirados.
- Historico, comentarios MT5 e contratos de saida foram preservados para
  auditoria e gestao segura de posicoes abertas antes da retirada.
- M5 continua ativo e pode consultar evidencias historicas de M1-M4 sem
  reativar M3 ou M4 como modelos independentes.
- Selecionar internamente um numero retirado no filtro patrimonial agora retorna
  zero linhas, em vez de cair no conjunto de todos os modelos ativos.

## 2026-08-12 - Retirada operacional de M9, M11 e M12

- M9, M11 e M12 foram removidos da selecao de modelos, do radar de entrada
  MT5 e dos filtros e paineis individuais do Relatorio.
- Os tres IDs foram retirados da politica de novas entradas e nao podem mais
  produzir ordens.
- O historico foi preservado e continua reconhecendo os comentarios M9, M11 e
  M12 pelo numero exato, sem deslocamento causado pelas lacunas na lista ativa.
- Posicoes legadas continuam sob gestao ate o encerramento; retirar entrada nao
  pode abandonar uma posicao ja aberta.
- M19, M21 e M22 permanecem ativos e independentes. Suas definicoes matematicas
  podem consultar os contratos-base, mas nao reativam M9, M11 ou M12.

## 2026-08-12 - Graficos do Relatorio vazios apos reinicio

- Sintoma: a aba Relatorios mostrava posicoes abertas, mas todas as curvas
  patrimoniais tinham zero linhas.
- Causa: a sonda historica aguardava apenas 0,05 segundo pelo canal MT5; ao
  falhar, o relatorio leve de `positions_get` substituia um cache ainda vazio.
- Correcao: espera limitada de 2 segundos para a sonda completa e snapshot
  persistente do ultimo relatorio auditado em `.traderia/runtime`.
- Desempenho: assinatura das linhas encerradas impede regravar o snapshot de
  aproximadamente 16 MB durante atualizacoes de preco aberto.
- Guardrail: posicoes abertas podem atualizar o snapshot, mas nunca apagar as
  operacoes fechadas usadas nos graficos.
- Complemento: sessoes de navegador anteriores a correcao agora reconhecem o
  cache leve incompleto e restauram o historico automaticamente.

## 2026-08-12 - Curvas M18-M22 isoladas dos modelos legados

- Sintoma: os novos paineis M18-M22 exibiam resultados dos IDs antigos que
  reutilizavam os mesmos numeros.
- Causa: o filtro patrimonial usava somente o numero quando nao encontrava um
  contrato ativo protegido.
- Correcao: M18-M22 agora exigem correspondencia com o ID operacional completo;
  as curvas novas iniciam vazias e recebem somente negociacoes dos novos modelos.

## 2026-08-12 - Reinicio obrigatorio apos alteracao de imports

- Sintoma: `ImportError` para `MODEL_18_ID` mesmo com o simbolo presente no arquivo.
- Causa: Streamlit iniciado antes da alteracao com `server.fileWatcherType=none`.
- Correcao: encerrada somente a arvore antiga do TraderIAnovo e iniciada uma
  instancia limpa pela rotina `scripts/abrir_traderianovo.ps1`.
- Prevencao: manter o watcher desligado para preservar desempenho, mas reiniciar
  o processo do app depois de qualquer implantacao que altere imports ou contratos.

## 2026-08-12 - M18-M22 XAU Reentry TP75

- Criados M18<-M8, M19<-M9, M20<-M10, M21<-M11 e M22<-M12.
- M8-M12 preservados sem alteracao de contrato.
- Entrada inicial sem TP; uma reentrada por ciclo com TP de 7,50 pontos.
- SL estrutural e Full Exit de contingencia preservados.
- Provider Demo passou a enviar TP na ordem pendente dos novos modelos.
- Seletor, radar MT5 e Relatorio ampliados ate M22.
- IDs M18-M22 antigos permanecem apenas historicos.

## 2026-08-11 - Aquecimento imediato M8-M17 com 52 velas M5

- Sintoma: M13-M17 iniciavam em `AQUECENDO_0_DE_52_CANDLES` ou `Dados TF`,
  apesar de o historico local ja conter os pares e o MT5 estar aberto.
- Diagnostico: o lote externo dos 17 pares expirou inclusive com 60 segundos;
  a ponte Python ficou presa em `initialize()`, enquanto o terminal continuou
  visualmente responsivo.
- Correcao: M8-M17 restauram um cache atomico leve de 52 velas por ativo; na
  ausencia do cache, as 52 ultimas velas M5 do SQLite local pre-aquecem os
  indicadores.
- Seguranca: historico local recebe origem `LOCAL_HISTORY_SEED` e nunca libera
  ordem. Somente uma leitura MT5 valida troca a origem para `LIVE`.
- Resultado observado: 18/18 ativos com 52 velas; XAUUSD renovado como `LIVE`;
  17 pares Forex aquecidos e aguardando renovacao viva da ponte MT5.
- Validacao: compilacao aprovada, 53 testes focados aprovados e health HTTP
  `200` na porta 8532.
- Ajuste de memoria: a janela M5 operacional de M8-M17 tambem ficou limitada
  a 52 velas em RAM; ao receber a 53a, descarta a mais antiga. Teste unitario
  especifico aprovado em `tests/test_runtime_lightweight_io.py`.
- Incidente de fonte: uma janela XAUUSD misturou 45 velas de 05/08 com 7 velas
  de 11/08. A contagem 52 promoveu a serie prematuramente para `LIVE` e gerou
  uma BUY STOP M12 invalida quando a serie atual tinha SMA20 abaixo da SMA50.
- Correcao: cache restaurado sempre volta como semente; a promocao para `LIVE`
  exige um lote integral de 52 candles retornado pelo MT5. Alem disso, o
  provider de execucao rejeita M8-M17 sem fonte auditada no mesmo candle M5 do
  plano. Validacao focada: 69 testes aprovados.
- Decisao final do usuario: baixar exatamente 52 velas M5 do MT5 e calcular
  SMA20, SMA50, RSI14, ADX14, ATR14, distancia/ATR, inclinacao e pivo 2+2
  localmente. A fonte operacional passou a ser `LOCAL_MT5_CANDLES_52`.
- O lote XAUUSD atual permanece `LIVE`. Os 17 pares Forex continuam
  `LOCAL_HISTORY_SEED` porque tanto a ponte Python quanto a tentativa MQL5 de
  historico ficaram bloqueadas no terminal; nenhum desses pares foi promovido
  nem liberado falsamente.
- Validacao final: 139 testes focados aprovados; Streamlit reiniciado na porta
  8532 com health HTTP 200. Nenhuma ordem ou posicao foi alterada.

## 2026-08-10 - Família M8-M12 XAUUSD/M5, setups A-E

- M8 permanece como Setup A, a base SMA20/50 + nível RSI50;
- criado M9/Setup B com ADX14 > 25;
- criado M10/Setup C com distância SMA20/50 por ATR14 >= 0,25;
- criado M11/Setup D com inclinação SMA50 de um candle por ATR14 >= 0,05;
- criado M12/Setup E exigindo simultaneamente os três filtros;
- cada modelo recebeu ID, Alpha, Beta, fonte, comentário e auditoria próprios;
- contratos antigos M8-M12 permanecem aposentados;
- validação ocorreu sem iniciar MT5 ou enviar ordens reais/Demo.

## 2026-08-10 - Novo M8 XAUUSD/M5 por RSI50 e SMA20/50

- criado `MODELO_8_XAU_M5_SMA_RSI_REENTRY`, sem reativar os IDs M8 históricos;
- SMA20/SMA50 simples funcionam como filtro direcional, nao como preco de entrada;
- entrada inicial ocorre a mercado quando o RSI14 fechado está do lado de 50 permitido pela direção das médias;
- após Full Exit extremo, a reentrada ocorre por Buy Stop/Sell Stop exatamente no extremo do último candle M5 fechado, mantendo RSI50 e direção SMA válidos;
- posição originada por reentrada possui Full Exit adicional no cruzamento fechado do RSI50 contra sua direção;
- Full Exit por RSI exige confirmação no fechamento M5: BUY cruza de 70 para baixo; SELL cruza de 30 para cima;
- SL inicial fica `0,01` alem do ultimo pivo M5 confirmado 2+2 e nao ha TP fixo;
- o Position Manager executa Full Exit se RSI14 perder 50 contra a posicao ou
  se SMA20/SMA50 inverterem;
- contrato restrito ao MT5 Demo; nenhuma ordem foi enviada durante a validacao.

## 2026-08-07 - Atalho com supervisao do app e Cloudflare Tunnel

- o atalho `TraderIA Novo` passou a validar `/_stcore/health`, e nao apenas a
  existencia de um listener na porta 8532;
- um Streamlit travado e encerrado antes da inicializacao limpa, evitando que o
  Cloudflare publique uma origem sem resposta;
- o mesmo atalho inicia o tunnel nomeado por `--token-file`, sem duplicar
  processos existentes;
- o endereco publico e testado e um `cloudflared` vivo, mas desconectado, e
  reiniciado automaticamente;
- stdout e stderr do tunnel ficam em `logs/cloudflared-traderianovo.*.log`;
- as leituras MT5 voltaram a processos externos para impedir que uma chamada
  nativa bloqueante congele o Streamlit e derrube indiretamente o tunnel.

## 2026-08-06 - Aposentadoria operacional dos modelos M8-M16

- M8-M16 foram removidos do conjunto autorizado a criar novas ordens;
- o seletor e o funil da aba MT5 Forex agora exibem somente M1-M7;
- os controles e graficos individuais do Relatorio agora exibem somente M1-M7;
- selecoes persistidas de M8-M16 migram com seguranca para M1;
- a politica central rejeita M8-M16 mesmo em chamadas diretas;
- contratos, codigo de leitura e negocios historicos foram preservados para
  auditoria e compatibilidade, sem apagar resultados passados.

## 2026-08-06 - Modelo 16 XAUUSD/M5 por preco versus EMA20

- criado o M16 independente, exclusivo para XAUUSD/M5;
- preco acima da EMA20 prepara BUY STOP; abaixo prepara SELL STOP;
- entrada fica um pip alem do extremo anterior e o SL nasce no extremo oposto
  exato;
- nao existe TP fixo, EARLY_EXIT ou FULL_EXIT;
- Position Manager move o SL somente pelo candle M5 fechado e nunca o afasta;
- M16 usa o snapshot M5 compartilhado, persistencia compacta por mudanca e nao
  executa Lab pesado no ciclo leve;
- o antigo M16 `VWAP_MEAN_REVERSION` permanece aposentado no historico.

## 2026-08-05 - Modelo 15 XAUUSD/M5 por rompimento

- criado o M15 independente, exclusivo para XAUUSD no timeframe M5;
- EMA20 acima/abaixo da EMA50 define a direcao;
- entrada e stop inicial recebem margem de um pip (`0,01` no XAUUSD);
- removido TP fixo somente deste modelo;
- Position Manager move o SL pelo ultimo candle M5 fechado e nunca o afasta;
- `EARLY_EXIT` e `FULL_EXIT` permanecem fora do contrato M15;
- seletor, radar MT5 e graficos do Relatorio passaram a reconhecer o M15;
- validacao feita sem envio de ordem real ou Demo.

## 2026-08-05 - Travamento de inicializacao do Streamlit no OneDrive

- processos de teste interrompidos foram encerrados para eliminar concorrencia;
- confirmado que a porta 8532 aceitava conexao, mas nao respondia ao HTTP;
- o Streamlit basico respondeu normalmente em porta isolada;
- o guardiao passou a iniciar o app com `--server.fileWatcherType none`;
- o ciclo MT5, o intervalo de 10 segundos e a gestao de posicao nao foram alterados.

## 2026-08-05 - Independencia M8-M14 e rollover pelo servidor MT5

- confirmado que M8-M14 possuem chave de candle, identidade de plano,
  comentario MT5, limite de posicao e deduplicacao independentes dos M1-M7;
- o seletor persistido foi restaurado para `TODOS_MODELOS`;
- removido o bloqueio indevido da hora inteira das 21h UTC quando o horario do
  servidor MT5 esta disponivel;
- mantida a protecao de 5 minutos antes/depois da virada do dia do servidor;
- o horario UTC fixo permanece somente como fallback se o MT5 nao fornecer hora.
- M8 passou a repetir tambem o gate de regime do M1; M9-M14 preservam os gates
  canonicos das respectivas origens M2-M7, sem compartilhar estado de posicao.

## 2026-08-04 - Resultado bruto, custos e lucro liquido nos graficos MT5

- o antigo cartao `Patrimonio final` foi renomeado para `Lucro bruto`;
- cada painel M1-M22 e o grafico principal agora somam separadamente comissao,
  swap/rollover e fee informados pelos deals MT5;
- `Custos MT5` representa comissao + swap + fee; `Lucro liquido` representa
  lucro bruto + custos assinados;
- posicoes abertas e registros nao encontrados no MT5 permanecem fora dessa
  conta realizada; a curva azul continua sendo o lucro bruto acumulado.

## 2026-08-04 - Modelo 22 espelho independente do M9

- criado `MODELO_22_ESPELHO_M9`, comentario `TraderIA M22`;
- M22 usa o mesmo Trend Pullback M15/M1 e o mesmo candle fechado do M9;
- BUY/SELL sao invertidos e `TP_M22 = SL_M9`, `SL_M22 = TP_M9`;
- parametros derivados do M9: SL 2,5 ATR, alvo 1,25 ATR e RR 0,5;
- M9 permanece inalterado e ambos podem coexistir no mesmo par;
- seletor, monitor, Relatorio, provider e limite por par ampliados ate M22;
- Position Manager apenas audita e conta real continua bloqueada.

## 2026-08-04 - Modelo 21 espelho independente do M19

- criado `MODELO_21_ESPELHO_M19`, comentario `TraderIA M21`;
- M21 usa o mesmo gate ALPHA015 e candle M1 do M19, com BUY/SELL invertido;
- `TP_M21 = SL_M19` e `SL_M21 = TP_M19`;
- parametros derivados do M19 atual: SL 4 ATR, TP 2 ATR e RR 0,5;
- M19 permanece inalterado e ambos podem coexistir no mesmo par;
- seletor, monitor, Relatorio, provider e limite por par ampliados ate M21;
- Position Manager apenas audita e conta real continua bloqueada.

## 2026-08-01 - Modelos 11 a 20 para as Alphas oficiais restantes

- Criados dez modelos independentes, em sequencia, de M11/ALPHA001 ate
  M20/ALPHA016, cobrindo as Alphas ainda sem fluxo operacional proprio.
- Cada modelo cobre os oito pares, usa somente candle fechado e preserva SL/TP
  fixos do contrato congelado.
- Seletor, funil MT5 Forex, monitor de indicadores, Robo Demo, provider,
  comentarios MT5 e Relatorio foram ampliados ate M20.
- O limite passou a vinte posicoes por par, no maximo uma por modelo.
- Features sao compartilhadas por par/timeframe/candle; decisoes continuam
  independentes por modelo.
- Benchmark sintetico: 80 avaliacoes em 1,35 segundo, abaixo do gate de 3 s.
- Execucao continua exclusiva em MT5 Demo; conta real permanece bloqueada.
- Commit: pendente.

## 2026-07-31 - Agenda semanal obrigatoria do Robo Demo

- Definida janela `America/Sao_Paulo`: domingo 18:01 ate sexta 17:30.
- Dentro da janela, o robo e mantido sempre ligado.
- Sexta 17:30, o robo e desarmado e todas as posicoes MT5 Demo sao encerradas.
- Domingo 18:01, o robo e rearmado automaticamente; se o app iniciar depois
  desse horario, ele rearma no primeiro ciclo da agenda.
- Thread semanal independe do estado online anterior e persiste auditoria.
- Conta real permanece bloqueada pelo provider.
- Testes de fronteira temporal e zeramento Demo adicionados.
- Validacao real em 2026-07-31: transicao executada as 17:30 BRT, 11 posicoes
  Demo encontradas, 11 fechadas, 0 rejeitadas e 0 remanescentes.
- Estado final confirmado: robo offline, ciclo auxiliar offline, conta Demo
  zerada e Streamlit saudavel na porta 8532.
- Commit: pendente.

## 2026-07-31 - Pesquisa de stop/alvo M8-M10 na Replay

- Executada grade de 30 combinacoes de stop ATR x alvo R para M8, M9 e M10.
- Base: 5.000 candles locais por par, oito pares por modelo.
- A Replay passou a selecionar primeiro o modelo e exibir vencedor agregado,
  vencedor por par, mapa de calor e ranking completo.
- O calculo pesado gera JSON uma vez; a Replay faz somente leitura leve.
- Nenhum parametro foi promovido ao runtime porque todos os vencedores globais
  tiveram resultado agregado negativo.
- Testes: 3 testes do motor e 126 testes do dashboard aprovados.
- Commit: pendente.

## 2026-07-31 - Modelos 8, 9 e 10 por pares de timeframe

- Criados M8 H1->M5, M9 M15->M1 e M10 D1->M15 com a mesma formula mecanica do
  M2 Trend Pullback, sem alterar M2 nem os demais modelos.
- Cada modelo cobre os oito pares, usa candle fechado, SL fixo 1,25 ATR, TP 2R
  e identidade propria no Trade Plan, provider, MT5, funil visual e Relatorio.
- A coleta usa o cache compartilhado dos timeframes M1, M5, M15, H1 e D1; nao
  adiciona recalculo pesado do Lab por ciclo.
- O limite foi deliberadamente ampliado para dez posicoes por par, uma por
  modelo M1-M10. Execucao continua exclusiva em MT5 Demo.
- A liberacao operacional nao afirma vantagem estatistica. Replay e forward
  test por par permanecem como evidencia pendente.

## 2026-07-26 - Janela De Entrada M2-M4 Alinhada Ao Relogio MT5

- Auditoria confirmou que os modelos novos M2, M3 e M4 nao chegaram ao
  `mt5_demo_execution.jsonl`, embora o replay dos candles da semana tenha
  encontrado 12 sinais depois da promocao: 6 em M2, 4 em M3 e 2 em M4.
- MT5, oito pares e timeframes H1/M30/H4 estavam online e sem erro de leitura.
- Causa raiz: a janela viva de 120 segundos comparava a barra marcada no
  relogio Pepperstone com o UTC da maquina. A diferenca observada de cerca de
  tres horas classificava a barra correta como futura antes da criacao do
  Trade Plan.
- Correcao: `LabOperationalModelService` recebe o timestamp vivo do servidor
  MT5 e usa esse mesmo relogio para medir a idade da barra. UTC local permanece
  somente como fallback.
- O ciclo continua em 10 segundos; indicadores, manifestos, candles historicos,
  SL/TP e regras dos modelos nao foram alterados.
- Validacao: 101 testes de LabOperationalModelService e DashboardService
  aprovados, incluindo regressao explicita para servidor MT5 com deslocamento
  de tres horas.

## 2026-07-24 - Modelo 7 Trend Momentum Dinamico

- Criado `MODELO_7_TREND_MOMENTUM_DYNAMIC` como modelo independente, sem
  alterar o M6 fixo.
- A entrada preserva `ALPHA001/MARCO_ZERO_A3BC912`, M1, medias 20/50,
  momentum 10, volatilidade 20, RSI14, SL inicial por 2 ATR ou 0,10% e TP RR2.
- A saida possui identidade `BETA007_DYNAMIC_PROTECT_ONLY_V1`: abaixo de
  1,50R mantem o plano; depois permite somente break-even ou ATR trailing mais
  protetivo. `EARLY_EXIT` e `FULL_EXIT` permanecem proibidos.
- M7 foi integrado ao seletor individual/Todos, funil MT5 Forex, monitor,
  Robo Demo, provider `TraderIA M7`, Position Manager, Relatorio, historico e
  curvas patrimoniais.
- O limite passou a sete posicoes por par, no maximo uma por modelo M1-M7.
- A leitura de entrada M6/M7 e compartilhada por par/candle para nao duplicar
  consulta ao MT5 nem tornar o ciclo leve mais pesado.
- Validacao focada: 214 testes operacionais aprovados, mais contratos
  especificos M6/M7 aprovados.
- Os gates arquiteturais legados continuam com divergencias anteriores ao M7
  em imports da UI, persistencia direta, scripts de pesquisa e API freeze; o
  M7 nao adiciona acesso a conta real e permanece somente Demo.

## 2026-07-24 - Contrato Original De Saida Do M6 Restaurado

- Auditoria do Git confirmou que a configuracao ALPHA001 foi recuperada do
  TraderIA original, mas o adaptador M6 criado em 22/23 de julho anexou o
  wrapper global `BETA001_PROTECT_ONLY_V1` e `DYNAMIC_POSITION_MANAGER`.
- A partir de agora, M6 usa `BETA001_FIXED_SL_TP_RR2_V1` e
  `RESEARCH_FIXED_SL_TP`: SL inicial pela maior distancia entre 2 ATR e 0,10%
  do preco, TP RR2 e encerramento por primeiro toque.
- Break-even, trailing, `EARLY_EXIT` e `FULL_EXIT` ficam fora do M6.
- Snapshots antigos do M6 recebem bypass defensivo antes de qualquer comando do
  Position Manager. Posicoes abertas preservam o SL/TP que ja existe no MT5;
  nenhum stop e afastado ou restaurado.
- Validacao: 38 testes M6/Position Manager e 217 testes Dashboard aprovados;
  processo `traderiaianovo` reiniciado na porta 8532 e health check `ok`.

## 2026-07-23 - Snapshot Atomico Dos Graficos Patrimoniais

- Corrigida a divergencia visual em que o cartao do M6 mostrava 13 operacoes e
  patrimonio `-12,80`, mas a linha ja representava 20 operacoes e `100,61`.
- A conta MT5 estava correta; o problema era o reaproveitamento visual de
  elementos durante rerenders do fragmento da aba Relatorio.
- Patrimonio final, numero de operacoes e pontos do grafico agora nascem do
  mesmo snapshot imutavel.
- Cada painel e grafico possui identidade por modelo e uma versao derivada dos
  dados. Uma nova operacao substitui o desenho anterior em vez de mistura-lo.
- A correcao nao adiciona consulta MT5, leitura de JSONL, recalculo do Lab ou
  trabalho ao ciclo operacional.

## 2026-07-22 - M6 Trend Momentum Original Ativado

- O identificador operacional vigente passou a ser
  `MODELO_6_TREND_MOMENTUM_ORIGINAL`; o antigo
  `MODELO_6_ESPELHO_M5` migra no seletor, sem reescrever ordens historicas.
- A configuracao foi recuperada do marco `a3bc912`: M1, media simples 20/50,
  momentum 10, volatilidade 20, RSI14, corte de volatilidade `0.00001`, faixa
  RSI 30/70 e confianca base 55%.
- O sinal usa o ultimo candle M1 fechado e materializa a entrada no preco vivo
  seguinte. O risco inicial usa a maior distancia entre 2 ATR e 0,10% do
  preco, com alvo RR2.
- A saida declarada e `BETA001_PROTECT_ONLY_V1`: o Position Manager pode
  manter ou proteger o SL, mas o contrato M6 nao autoriza `FULL_EXIT`.
- M6 ficou disponivel sozinho e em `TODOS_MODELOS`, com uma posicao por par e
  comentario `TraderIA M6`. A execucao continua exclusiva em conta Demo.
- O monitor MT5 exibe MA20, MA50, momentum 10, volatilidade 20, RSI14 e ATR20
  reutilizando o snapshot do ciclo, sem nova leitura do MT5 nem Lab pesado.
- Validacao: compilacao aprovada e 263 testes focados de M6, ViewModel,
  interface, Robo Demo e provider aprovados.

## 2026-07-22 - Funil Visual Rastreavel M1-M5

- A tabela `Entrada Teorica MT5` passou a decompor o caminho de envio em
  modelo, liberacao Demo, dados do TF, candle fechado, indicadores, sinal,
  janela, Trade Plan, zona, filtro, regime, preco, tempo, duplicidade, posicao,
  Robo e MT5 Demo.
- A coluna `Envio` agora apresenta somente `PRONTO` ou o gargalo com etapa e
  motivo; as demais celulas permitem acompanhar simultaneamente todo o funil.
- M2-M5 deixam de herdar visualmente sinal, direcao, candle, entrada, SL e TP da
  linha M1 quando sua decisao propria ainda nao gerou gatilho.
- Corrigida a colisao de duas chaves `Zona`: o status permanece em `Zona` e a
  leitura tecnica passou para `Zona atual`.
- `NO_THEORETICAL_TRIGGER` no M1 passou a ser exibido como espera amarela, pois
  representa ausencia momentanea de gatilho e nao falha estrutural do plano.
- O diagnostico reutiliza o snapshot compacto do ciclo e o log de execucao e
  nao adiciona leitura MT5, recalculo do Lab ou novo loop.
- Escopo operacional preservado: a tabela observa o fluxo; Robo Demo,
  DemoExecutionService e Provider continuam sendo os responsaveis pelo envio.
- Validacao: `py_compile` aprovado; 236 testes de dashboard, ViewModel,
  LabOperationalModelService e Robo Demo passaram; navegador confirmou M1-M5,
  `Envio` amarelo para espera e separacao entre `Zona` e `Zona atual`.

## 2026-07-22 - Liberacao Demo De Todos Os Pares M2-M5

- Os oito pares foram liberados operacionalmente em M2, M3, M4 e M5.
- A decisao ficou separada em
  `research/alpha_suggested/lab_demo_forward_policy.json`.
- O manifesto preserva a evidencia estatistica original nos campos `evidence_*`.
- O escopo permanece exclusivamente Demo; conta real continua bloqueada.
- M1 permanece com os oito planos vigentes do Lab e M6 continua inativo.

## 2026-07-22

### Corte Patrimonial Exato Em 22/07/2026 04:30 Brasil

- O grafico principal e as curvas individuais passaram a converter a hora real
  de fechamento do MT5 para o fuso do Brasil, em vez de comparar a data UTC.
- O corte padrao e `22/07/2026 04:30` em `America/Sao_Paulo`; uma operacao
  realizada antes desse instante fica fora e um fechamento a partir dele entra.
- Timestamps ISO, ISO com `Z` e formato brasileiro sao aceitos. Registros sem
  horario confiavel ficam fora da curva quando existe corte ativo.
- Removido o segundo filtro por indice, que podia ocultar ou incluir um trecho
  diferente do solicitado e deixava a legenda `desde indice` ambigua.
- A data, a hora e o saldo inicial agora alimentam uma unica janela compartilhada
  pelo grafico principal e por M1-M6.
- A chave da hora foi versionada para impedir que uma sessao anterior restaure
  automaticamente o antigo valor `00:00`.

### Monitor Vivo De Indicadores M1-M5

- A aba MT5 Forex passou a apresentar `M1` a `M5` na primeira coluna e uma
  linha para cada indicador efetivamente usado pelo modelo em cada par/TF.
- A coluna `Movimento` compara o valor com o ciclo anterior e informa subida,
  queda, estabilidade ou mudanca categorica.
- O M4/M5 transporta tambem o contexto H1/H4 habilitado; paridades bloqueadas
  exibem somente seu bloqueio.
- A tela reutiliza o snapshot compacto `mt5_lab_operational_decisions`; o cache
  bruto de candles permanece no ciclo background e nao e copiado para a sessao.
- Nenhuma nova leitura MT5, novo loop ou recalculo pesado do Lab foi criado.
- Perfil real do ciclo quente identificou 113 mil normalizacoes repetidas de
  candles e montagem desnecessaria do dashboard completo durante o export MT5.
- O runtime passou a reutilizar candles normalizados pelo candle fechado,
  exportar diretamente o ViewModel Forex, compartilhar o horario do servidor
  no ciclo e publicar as decisoes que o Robo ja calculou.
- Medicao controlada caiu de `3,13 s` para `0,80 s` por ciclo quente, mantendo
  o intervalo operacional de 10 segundos e todas as leituras de M1 a M5.

### Promocao Dos Planos Do Lab Para Os Modelos MT5 M2-M5

- Os artefatos pesquisados foram confrontados com o contrato executavel e
  congelados em `research/alpha_suggested/lab_operational_models_manifest.json`.
- M2, M3, M4 e M5 agora usam as Alphas, timeframes, indicadores, filtros de
  sessao/dia, ATR, RR, SL e TP da pesquisa; os modelos operacionais antigos
  espelho/Price Action foram retirados desse caminho.
- O consolidado deixou de ser M5-P separado e passou a ser somente M5. M6 ficou
  inativo e fora do seletor, do modo Todos e do envio.
- M2-M5 operam por ultimo candle fechado e proximo preco vivo, com janela de
  120 segundos e `RESEARCH_FIXED_SL_TP`. O Position Manager acompanha e audita,
  mas nao move SL nem executa `FULL_EXIT` nesses planos.
- O provider passou a bloquear duplicata exata entre modelos no mesmo candle.
- A leitura suplementar M30/H1/H4 usa cache e atualizacao incremental; o Lab
  pesado nao entra no ciclo leve.
- Corrigida a conversao de timestamp do tick para UTC. Fim de semana e rollover
  agora sao bloqueios duros mesmo com filtro geral de sessao desmarcado.
- A auditoria visual encontrou e removeu o ultimo monitor M2 espelho e a legenda
  BETA2/RR1 que ainda eram montados pela UI. As tabelas exibidas agora refletem
  o manifesto M2-M5; contratos legados aparecem somente em posicoes/historico
  realmente abertos antes da promocao.
- Auditoria somente leitura confirmou MT5 Pepperstone Demo conectado, permissao
  algoritmica ativa, oito pares negociaveis e dados M1/M5/M30/H1/H4 presentes.
- Validacao: 363 testes aprovados e compilacao Python aprovada. Nenhuma ordem
  foi enviada durante a auditoria.
- A tentativa adicional de `unittest discover` global atingiu o timeout de 15
  minutos sem concluir ou emitir falha. O incidente foi registrado como
  `FLOW-009`; ele nao substitui os grupos criticos aprovados e exige futura
  divisao da suite por perfil de custo.
- Relatorio: `docs/research/LAB_MODELS_MT5_OPERATIONAL_PARITY_2026-07-22.md`.

### Graficos Do Relatorio Reiniciados Em 22/07/2026

- O grafico principal e as curvas individuais M1-M6 passaram a usar
  `22/07/2026` como data inicial padrao.
- O corte atua somente nas curvas patrimoniais; historico completo, ultima
  negociacao e tabelas de auditoria permanecem intactos.
- O seletor de data continua editavel e recebeu uma nova chave de sessao para
  nao restaurar o valor anterior de `01/07/2026` apos a atualizacao.

### Consolidacao Dos Melhores M1-M4 Como M5 De Pesquisa

- Criado `MODELO_5_PESQUISA_CONSOLIDADO`, exibido no Lab como M5-P e separado
  do `MODELO_5_PRICE_ACTION` operacional.
- O seletor compara uma candidata de M1, M2, M3 e M4-P por par, priorizando
  certificacao, custo estressado, cobertura de holdout, PF conservador, ICT,
  amostra e drawdown.
- Vencedores: M3 em AUDUSD, EURJPY, EURUSD, GBPUSD e NZDUSD; M1 em USDCAD e
  USDJPY; M4-P em USDCHF. O M2 participou, mas nao venceu nenhum par.
- O artefato local preserva todos os candidatos comparados e possui
  `operational=false`; nenhum runtime, gate, ordem ou Position Manager mudou.
- Relatorio: `docs/research/MODEL_5_BEST_M1_M4_2026-07-22.md`.
- Validacao inicial: compilacao aprovada e 18 testes focados aprovados.

## 2026-07-21

### Fronteira Contextual Salva Como Modelo 4 De Pesquisa

- Criado `MODELO_4_PESQUISA`, isolado do `MODELO_4_ESPELHO_M1` operacional.
- Avaliadas 19.065 combinacoes unicas em M30 com H1/H4 concluidos, forca
  relativa entre moedas, BUY/SELL assimetrico, percentil de volatilidade e
  entrada na proxima abertura.
- O contrato usou descoberta 60%, validacao 15%, embargo 5% e holdout 20%, com
  custo liquido e estresse.
- Nenhum par passou todos os gates. USDCHF SELL contextual e AUDUSD BUY por
  Liquidity Reclaim ficaram registrados como hipoteses promissoras com amostra
  insuficiente.
- O Lab ganhou tabela M4-P abaixo do M3, com pendencias e status explicitos.
- Nenhuma ordem, Trade Plan, gate ou componente MT5 foi alterado.
- Relatorio: `docs/research/MODEL_4_CONTEXTUAL_FRONTIER_2026-07-21.md`.

### Pesquisa Individual Da Alpha Sugerida 002+ Para M3

- Avaliados 144.000 candidatos em oito pares e tres timeframes, sobre 400.000
  candles cronologicos no total.
- Desenvolvimento, quatro blocos de estabilidade e holdout foram mantidos
  separados; custos de 1,5 bps e estresse de 2,5 bps foram descontados.
- O melhor cenario observado de cada par foi salvo em
  `.traderia/research/m3_alpha_sugerida_2_plus_best_by_pair.json`, sempre com
  `operational=false`.
- EURUSD M30 atingiu ICT B e passou o contrato completo para Replay; AUDUSD,
  EURJPY, GBPUSD, NZDUSD e USDCAD ficaram como promissores para Replay; USDCHF
  e USDJPY foram rejeitados por holdout.
- O Lab passou a exibir a tabela M3 imediatamente abaixo da tabela M2, sem
  acoplamento ao ciclo MT5 e com cache por data de modificacao.
- O M3 RR3 operacional, os gates e o envio de ordens permaneceram inalterados.
- Relatorio: `docs/research/ALPHA_SUGERIDA_002_PLUS_M3_INDIVIDUAL_2026-07-21.md`.
- Validacao: compilacao e 13 testes focados aprovados.

### Pesquisa Isolada Da Alpha Sugerida 1+

- Criado pesquisador reproduzivel em
  `research/alpha_suggested/alpha_suggested_1_plus_discovery.py`.
- A base foi ampliada em modo read-only para 20.000 candles H1 por par, cobrindo
  oito pares e 160.000 candles, sem alterar o snapshot operacional.
- Foram pesquisadas familias ineditas de compressao/expansao, impulso,
  rejeicao de pullback e varredura de liquidez, com sessao, eficiencia,
  inclinacao e regime ATR.
- O ranking foi congelado em treino + validacao antes da abertura do holdout.
- Nenhuma candidata atingiu ICT A no holdout. O identificador
  `ALPHA_SUGERIDA_001_PLUS` ficou reservado, sem promocao operacional.
- O M1 e o M2 permaneceram inalterados e nenhuma ordem foi autorizada.
- O Lab passou a exibir, abaixo da planilha operacional do M1, uma planilha
  separada com os oito resultados da pesquisa, todas as linhas identificadas
  como M2 e com qualificacao/ativacao explicitas. A leitura usa cache por data de
  modificacao do artefato e nao entra no ciclo MT5.
- Relatorio: `docs/research/ALPHA_SUGERIDA_001_PLUS_DISCOVERY_2026-07-21.md`.
- Validacao: compilacao do pesquisador, smoke test sobre a base ampliada e dois
  testes do contrato cronologico aprovados.

### Persistencia Da Ultima Selecao Operacional

- O seletor de modelos grava a ultima escolha explicita em
  `.traderia/mt5_operational_model.json`.
- Reinicio do Streamlit, navegador ou ciclo background restaura esse valor e
  nao impoe `TODOS_MODELOS`.
- Adicionada gravacao defensiva no render e regressao de partida fria para
  confirmar a restauracao de M1-M6 ou Todos conforme a ultima escolha.

### Incidente: Configuracoes Do Lab Sumiam No Monitor Do Robo

- Sintoma: o monitor mostrava todos os pares como H1, `TENDENCIA_MOMENTO`,
  `BETA001` e `PARADA_FIXA`, apesar de o indice runtime conter Alpha, setup e
  parametros diferentes por par.
- Causa raiz: os ciclos Forex e Robo Demo em segundo plano publicavam uma
  leitura MT5 crua em rotas que substituiam o ViewModel enriquecido. A UI entao
  preenchia defaults tecnicos, escondendo a perda do contrato do Lab.
- Correcao: ambos os ciclos passaram a publicar exclusivamente
  `DashboardService.get_mt5_forex_runtime_view_model()`, que combina leitura
  leve com constantes persistidas do Lab.
- Correcao visual defensiva: o monitor passou a exibir Alpha, setup, parametros,
  fonte e referencia ICT. Ausencia real agora aparece como `SEM_CONFIG_LAB`, nunca
  como uma configuracao generica aparentemente valida.
- Relacao adicional encontrada: uma sessao Streamlit antiga podia sobrescrever
  o seletor operacional no rerender. O estado atomico persistido tornou-se a
  fonte compartilhada; somente uma mudanca real do usuario e gravada.
- Arquitetura: criado
  `docs/architecture/END_TO_END_OPERATIONAL_FLOW.md` como mapa canonico e
  adicionadas invariantes em `docs/ARCHITECTURE.md`.
- Testes de regressao: enriquecimento do snapshot, publicacao nos dois ciclos,
  parametros no monitor, ausencia explicita de configuracao e sincronizacao do
  seletor entre sessoes.
- Falha relacionada encontrada pela suite completa: o Lab historico recebia o
  rollover vivo do servidor MT5 e os mesmos testes mudavam conforme a hora real.
  A classificacao foi separada: Lab/Replay usam o candle; apenas o fluxo ao vivo
  consulta o relogio do servidor. O caso foi registrado como `FLOW-004`.
- Correcao de visibilidade `FLOW-005`: o painel principal filtrava os sete pares
  abaixo de ICT 70 e mostrava somente USDCAD. A tabela agora exibe os oito pares.
- Correcao semantica `FLOW-006`: a UI chamava a faixa ICT de bloqueio operacional,
  embora Trade Plan e Robo Demo ja a tratassem como informativa. A tela agora
  exibe nota/status ICT sem afirmar que ela libera ou bloqueia a ordem.

### Auditoria E Recalculo Integral Do Modelo 1

- O M1 foi restaurado para receber sem alteracao direcao, timeframe, entrada,
  stop, alvo e RR do Research Lab; somente M4 adapta uma copia para o espelho.
- A base local foi corrigida e validada com 200.000 candles: 8 pares, 5
  timeframes e 5.000 candles por mercado.
- O Lab deixou de contar sinais sobrepostos e de inferir resultado por horizonte
  fixo. O replay `SCENARIO_TRADE_PLAN_REPLAY_V2` usa o primeiro toque em SL/TP,
  com ambiguidade resolvida pelo stop.
- A aprovacao de entrada foi separada da Beta. O snapshot final usa BETA001 como
  marcador do plano inicial; o Position Manager decide protecao depois da
  abertura.
- O historico realizado mostrou 252 M1 fechados, todos registrados em M1, com
  resultado bruto -157,63, custos -268,01 e liquido -425,64. O novo Lab escolheu
  H1, evidenciando que pratica e expectativa anteriores nao usavam o mesmo
  contrato.
- Recálculo final: somente USDCAD H1 / ALPHA003 / RR1,5 / ATR1,5 passou o gate
  completo. Os outros sete pares permanecem visiveis e nao executaveis.
- Relatorio detalhado:
  `docs/research/MODEL_1_LAB_VS_REAL_AUDIT_2026-07-21.md`.
- Validacao focada: 169 testes aprovados.

### Restauracao: M1 Volta A Materializar Integralmente O Lab

- Decisao: a normalizacao RR1 aplicada ao M1 foi revertida. M1 volta a receber
  sem alteracao a entrada, o stop, o alvo e o RR produzidos pelo Lab.
- Apenas M4 se adapta: inverte a direcao, usa o stop do M1 como alvo e calcula
  stop proprio equidistante, com `RR=1.0`.
- O snapshot do Lab permanece fonte da verdade do M1.
- A secao historica "M1 E M4 Normalizados Para RR1" abaixo registra o estado
  temporario anterior e esta explicitamente superada por esta restauracao.

### Estado Historico Superado: Preflight Pareado M1/M4

Status: **SUPERADO** pelo contrato independente descrito na auditoria acima.

- Sintoma: historico mostrou resultados M1 `0.00`, `-0.10` e `-0.20`.
- Causa: havia M4 aberta no mesmo par; o fluxo enviava M1, recebia rejeicao da
  nova M4 e fechava M1 imediatamente por
  `MIRROR_PAIR_ROLLBACK_M4_NOT_ACCEPTED`.
- Impacto final antes do reinicio corrigido: 35 rollbacks, todos negativos apos
  custos, totalizando `-26.88` liquidos. O `0.00` visual era lucro bruto e escondia `-0.70` de
  comissao por operacao zerada no preco.
- A solucao pareada foi removida porque M1 e M4 devem operar de forma
  independente. Cada modelo consulta apenas seus proprios gates e uma rejeicao
  M4 nunca pode fechar nem impedir uma M1 ja aceita, e vice-versa.
- Historico antigo foi preservado; a correcao impede novos custos pela mesma
  causa sem apagar rastreabilidade.
- Validacao: 77 testes operacionais e 188 testes completos do dashboard foram
  aprovados.

### Ajuste Operacional: M1 E M4 Normalizados Para RR1

Status: **SUPERADO** pela restauracao do M1 ao contrato integral do Lab descrita
acima.

- Objetivo: tornar o resultado bruto do M4 simetrico ao M1 quando as duas pernas
  forem executadas com mesmo lote e niveis reciprocos.
- M1 preserva entrada e stop produzidos pelo Research Lab; o alvo operacional e
  recalculado para a mesma distancia do stop (`RR=1.0`).
- M4 inverte BUY/SELL do M1 RR1, usa o stop do M1 como alvo e o alvo operacional
  do M1 como stop; portanto tambem nasce com `RR=1.0`.
- O snapshot e o calculo pesado do Lab nao foram modificados. O plano enviado
  registra `rr_lab_original` e `rr_operacional=1.0000` para auditoria.
- Posicoes ja abertas nao foram alteradas; a regra vale para novas entradas.
- Validacao: 78 testes operacionais e 188 testes completos do dashboard foram
  aprovados.

### Incidente De Lentidao: Sessoes Repetindo MT5 E Escrita Concorrente

- Sintoma: porta `8532` responsiva, mas interface lenta; processo Streamlit com
  aproximadamente 1,2 GB de RAM e um nucleo de CPU ocupado continuamente.
- Evidencia: quatro conexoes Streamlit simultaneas, ciclo operacional concluindo
  em cerca de 20 a 27 segundos, 23 posicoes abertas e
  `.traderia/position_manager_current.json` com byte UTF-8 interrompido.
- Causa: cada sessao podia executar leitura MT5; o ciclo do Robo Demo contornava
  o lock do ciclo Forex; instancias concorrentes do Position Manager gravavam o
  mesmo snapshot diretamente; o JSONL de execucao era relido por inteiro.
- Correcao: ciclo MT5 com dono unico process-local, lock comum para Forex/Robo
  Demo, snapshot compartilhado para as abas, estado do Position Manager gravado
  atomicamente uma vez por lote e leitura incremental do JSONL.
- Preservado: intervalo de 10 segundos, leitura de mercado, gerenciamento de SL,
  modelos M1-M6, regras de entrada e envio demo.
- Aprendizado permanente: conexao de navegador nao e unidade de execucao. A UI
  observa snapshots; somente o runtime process-local consulta o MT5 e altera
  estado operacional.
- Resultado apos reinicio, com cinco conexoes Streamlit: RAM caiu de cerca de
  1,5 GB para aproximadamente 486 MB; o app consumiu 12,08 segundos de CPU em
  32,2 segundos observados, em vez de manter um nucleo continuamente ocupado.
- O ciclo online concluiu normalmente, preservou a espera de 10 segundos e o
  snapshot do Position Manager voltou a ser JSON UTF-8 valido.
- Validacao automatizada: suite focada com 80 testes e suite completa de
  dashboard com 187 testes, ambas aprovadas.

## 2026-07-20

### Incidente De Lentidao: Ciclos Background Duplicados

- Sintoma: TraderIA Novo lento mesmo com apenas um processo Streamlit e cerca
  de 303 MB de RAM.
- Fluxo afetado: ciclo automatico do Robo Demo, leitura MT5 e Position Manager
  na porta `8532`.
- Evidencia: o processo consumiu 11,72 segundos de CPU em uma janela de 20
  segundos; o heartbeat concluiu ciclos com apenas 7 segundos de separacao,
  apesar do `sleep` configurado de 10 segundos apos cada ciclo.
- Causa: os marcadores `MT5_*_BACKGROUND_THREAD_STARTED` pertenciam ao script
  rerun do Streamlit e podiam voltar a `False`, permitindo criar novas threads
  daemon no mesmo processo.
- Correcao: criado registro singleton process-local em
  `core/background_runtime_registry.py`; os ciclos Forex e Robo Demo agora
  reutilizam a thread viva registrada, inclusive apos rerun ou troca de aba.
- Preservado: intervalo de 10 segundos, leitura MT5, envio demo, estado armado
  persistido e gerenciamento do Position Manager.
- Resultado medido apos reinicio: heartbeat regular a cada aproximadamente
  13,5 segundos (duracao do trabalho mais 10 segundos de espera), RAM em 296 MB
  e consumo de CPU reduzido para 7,7 segundos em uma janela de 25 segundos.
- Validacao: testes focados do registro singleton e do estado persistido do
  Robo Demo passaram; compilacao de `dashboard_app.py` aprovada e health HTTP
  `200` confirmado.

## 2026-07-17

### Modelo Operacional: M6 Espelho Do M5

- Pedido: criar o `MODELO_6_ESPELHO_M5` usando o protocolo de criacao de
  modelo, sem alterar o M5 original.
- Regra: calcula o plano Price Action do M5; se M5 estiver pronto, inverte
  BUY/SELL, usa o stop original do M5 como alvo e o alvo original do M5 como
  stop.
- Identidade: Alpha `ALPHAPRICE6`, Beta `BETAPRICE6`, source
  `PRICE_ACTION_MODEL`, modelo operacional `MODELO_6_ESPELHO_M5`.
- Visual: M6 aparece no seletor, no modo Todos, na Entrada Teorica MT5, na
  Saida Teorica MT5, no relatorio e nos graficos patrimoniais por modelo.
- Guardrail: M6 e independente do M5 para selecao/envio, mas depende de um
  plano M5 valido para construir o espelho no ciclo atual.

### Correcao: Position Manager Por Ticket E Modelo

- Sintoma: auditoria do `EURJPY M15` em `MODELO_3_RR3` mostrou a ordem enviada
  com `BETA006 / CHANDELIER_STOP_MANAGER`, mas a leitura posterior do Position
  Manager aparecia como `BETA004 / BREAK_EVEN_MANAGER`.
- Causa: o ciclo do Position Manager era alimentado pelo JSON visual, que tem
  uma linha por par/sinal atual. Com varios modelos posicionados no mesmo par,
  isso podia associar a posicao aberta ao plano visual errado.
- Correcao aplicada: planos de posicoes abertas agora sao reconstruidos a partir
  das ordens aceitas em `.traderia/mt5_demo_execution.jsonl` e vinculados pelo
  `ticket` da posicao MT5.
- Impacto: M1, M2, M3, M4, M5 e M6 mantem Alpha/Beta/modelo/TF originais da ordem
  aceita durante a gestao de saida.
- Guardrail: se o ticket do plano nao existir mais no MT5, o Position Manager
  registra `POSITION_ABSENT` e nao mexe em outra posicao do mesmo par.
- Validacao: `py_compile` em `application/position_manager_service.py`,
  `application/demo_execution_service.py`,
  `infrastructure/execution/mt5_demo_execution_provider.py`,
  `application/dashboard_service.py` e `tests/test_position_manager_service.py`.
- Validacao: suite focada com 85 testes passou, incluindo regressao
  `test_plano_com_ticket_nao_usa_posicao_errada_do_mesmo_par`.

### Regra Operacional: Ultimo Comando Manual Mantem Robo Armado

- Sintoma: usuario relatou que o botao `Armar robo demo` voltava para desligado
  apos abrir pagina, trocar aba, reiniciar navegador ou reiniciar Streamlit.
- Regra definida: o estado armado/desarmado do Robo Demo deve seguir o ultimo
  comando manual do usuario.
- Correcao aplicada: falha transitoria do backend, leitura vazia, reload de
  pagina ou backend recem-instanciado nao persistem mais `online=false`.
- Novo comportamento: se o usuario armou o robo, o app mantem `online=true`,
  registra mensagem de reidratacao/bloqueio temporario e tenta rearmar no
  proximo ciclo leve.
- Unicas excecoes documentadas: botao `Desarmar robo` ou rollback/restauracao
  explicitamente solicitada pelo usuario.
- Politica registrada em
  `docs/architecture/RUNTIME_PRESERVATION_POLICY.md`.

### Operacao Assistida: Position Manager Move SL E Guardiao De RAM

- Decisao operacional: o Position Manager deve modificar SL em DEMO quando houver
  stop candidato mais protetivo, sem abrir nova ordem e sem fechar posicao por
  `FULL_EXIT`/`EARLY_EXIT`.
- Confirmacao tecnica: `SystemConfiguration.dynamic_exit_demo_sl_assisted_execution_enabled`
  esta com default `True`; quando a acao calculada e `PROTECT_POSITION` ou stop
  movel valido, `PositionManagerService` chama `modify_position_sl`.
- Estado atual observado: registros `HOLD_POSITION` continuam aparecendo como
  sem movimento porque nao ha `new_stop` candidato; isso e esperado e nao
  significa que a execucao assistida esta desligada.
- Acao aplicada: criado `scripts/traderianovo_ram_guard.ps1`, um supervisor
  externo leve para monitorar o Streamlit na porta `8532`.
- Guardiao de RAM: registra saude em
  `.traderia/runtime/streamlit_ram_guard.jsonl`, reinicia o app se o processo
  dono da porta `8532` atingir `3500 MB` e sobe o app com
  `TRADERIA_DEMO_EXECUTION_ENABLED=1` e `TRADERIA_MT5_INPROCESS_ENABLED=1`.
- Correcao no guardiao: o monitor considera apenas o processo que realmente esta
  em `Listen` na porta `8532`, ignorando processos auxiliares do PyManager que
  nao sao donos da porta.
- App reiniciado uma vez para assumir o supervisor e reduzir RAM. Processo ativo
  validado na porta `8532`.
- Validacao: `py_compile` em `application/position_manager_service.py`,
  `application/dashboard_service.py` e `dashboard_app.py`.
- Validacao: `python -m unittest tests.test_position_manager_service.PositionManagerServiceTest tests.test_demo_execution_service.DemoExecutionServiceTest tests.test_mt5_demo_execution_provider.MT5DemoExecutionProviderTest -v`
  executou 83 testes com sucesso.

### Detalhe Corrigido: `Invalid Stops` Sem Diagnostico Preventivo

- Sintoma: auditoria do log `.traderia/mt5_demo_execution.jsonl` encontrou
  rejeicoes recorrentes `Invalid stops`, principalmente em tentativas `SELL` de
  `USDCHF` e `NZDUSD`.
- Diagnostico: o provider ja validava se SL/TP estavam do lado correto do preco
  atual, mas ainda nao validava a distancia minima exigida pelo broker
  (`trade_stops_level` / `trade_freeze_level`).
- Acao aplicada: `MT5DemoExecutionProvider` agora consulta `symbol_info`, calcula
  a distancia minima em pontos e rejeita o plano antes do `order_send` quando SL
  ou TP ficam perto demais do preco atual.
- Guardrail: a correcao nao altera entrada, stop, alvo ou modelo. Ela apenas
  evita envio invalido ao MT5 e grava uma mensagem explicita para auditoria.
- Teste adicionado: provider bloqueia SL/TP abaixo da distancia minima do broker
  sem chamar `order_send`.
- Validacao: `python -m unittest tests.test_position_manager_service.PositionManagerServiceTest tests.test_demo_execution_service.DemoExecutionServiceTest tests.test_dashboard_app_runtime.DashboardAppRuntimeTest tests.test_mt5_demo_execution_provider.MT5DemoExecutionProviderTest -v`
  executou 183 testes com sucesso.

### Auditoria Operacional Completa Do Runtime MT5

- Escopo: fluxo do Robo Demo, ciclo online fora da aba MT5, Position Manager,
  logs locais, performance percebida e testes de regressao principais.
- Achado 1: o estado persistido em `.traderia/mt5_demo_robot_online_state.json`
  podia marcar `online=true` enquanto o backend recem-instanciado ainda estava
  `DISARMED`, gerando tela contraditoria: banner verde ativo com card
  `DISARMED`/`Envio MT5 DESLIGADO`.
- Correcao aplicada: a tela do Robo Demo agora reconfirma o backend quando
  `online=true`; se o backend aceita, reidrata o snapshot armado; se nao aceita,
  desliga o online persistido e remove o falso positivo visual.
- Achado 2: o dedupe do Position Manager podia usar o arquivo global
  `.traderia/position_manager_history_dedupe.json` mesmo quando o servico era
  instanciado com `log_path` isolado, mascarando registros em testes/caminhos
  alternativos.
- Correcao aplicada: o caminho de dedupe agora acompanha o `log_path` quando o
  servico usa diretorio customizado, preservando isolamento e rastreabilidade.
- Achado 3: o Position Manager esta monitorando posicoes, mas em estado atual
  aparece como `READ_ONLY`; ele calcula HOLD/PROTECT, mas nao envia modificacao
  de SL enquanto a execucao assistida nao estiver realmente habilitada no
  runtime.
- Achado 4: no arquivo `.traderia/mt5_demo_execution.jsonl`, a amostra recente
  mostrava muitas rejeicoes `Invalid stops`; a auditoria dedicada corrigiu a
  ausencia de preflight de distancia minima do broker.
- Achado 5: os arquivos quentes ficaram pequenos apos dedupe, mas o processo
  Streamlit ainda chegou a aproximadamente 1.2 GB durante a suite, entao a
  lentidao deve continuar como risco monitorado em abas com tabelas grandes.
- Validacao: `python -m py_compile dashboard_app.py application/dashboard_service.py
  application/position_manager_service.py tests/test_demo_execution_service.py
  tests/test_dashboard_app_runtime.py`.
- Validacao: `python -m unittest tests.test_position_manager_service.PositionManagerServiceTest
  tests.test_demo_execution_service.DemoExecutionServiceTest
  tests.test_dashboard_app_runtime.DashboardAppRuntimeTest -v` retornou 157
  testes OK.
- Pendencias recomendadas: decidir se
  `dynamic_exit_demo_sl_assisted_execution_enabled` deve ficar ativo para mover
  SL real em DEMO; monitorar memoria em uso prolongado do app.

### Correcao De Regra: M4 Independente Do M1

- Sintoma: usuario esclareceu que o M4 e espelho do M1, mas deve poder operar
  independentemente, inclusive quando apenas M4 estiver selecionado ou quando M1
  for rejeitado por gate/provider no mesmo ciclo.
- Diagnostico: havia trava temporaria `M4_AGUARDANDO_M1_ACEITO` que impedia o
  envio do M4 quando M1 nao fosse aceito antes no mesmo ciclo.
- Acao aplicada: removida dependencia de aceite do M1 para liberar M4.
- Regra atual: M4 usa o plano do M1 como fonte de espelho, mas passa por seus
  proprios gates de duplicidade, posicao, provider, MT5 e risco.
- Guardrail: M1 e M4 podem ser simultaneos por serem modelos diferentes; M4 nao
  deve ser bloqueado apenas porque M1 foi rejeitado ou nao foi enviado.

### Incidente De Performance: HOLD Repetido Do Position Manager

- Sintoma: usuario relatou nova lentidao apos o app ficar aberto.
- Fluxo afetado: TraderIA Novo local em `localhost:8532`, Relatorio e Saida
  Teorica MT5.
- Diagnostico:
  - processo Streamlit/Python chegou a aproximadamente 6.7 GB de RAM;
  - `.traderia/position_manager.jsonl` cresceu para aproximadamente 10.5 MB em
    poucas horas;
  - 7.912 de 8.495 registros analisados eram `HOLD_POSITION` repetido;
  - havia centenas de registros com a mesma assinatura operacional, por exemplo
    mesmo ticket, simbolo, politica, beta e estado.
- Causa raiz: o Position Manager atualizava corretamente o estado atual, mas
  tambem persistia leituras HOLD sem mudanca real no JSONL historico. Isso
  aumentava I/O, memoria e custo de auditoria/render com o app aberto.
- Acao aplicada:
  - mantido `position_manager_current.json` como fonte leve de estado atual;
  - criado indice persistente de deduplicacao para historico de baixo sinal;
  - `STOP_MOVED`, envio, rejeicao, erro, fechamento e eventos de alto sinal
    continuam sendo gravados sempre;
  - `HOLD_POSITION` e manutencoes sem mudanca real deixam de repetir no JSONL.
- Guardrail: leitura por ciclo pode atualizar estado atual, mas nao pode gravar
  historico repetitivo sem alteracao operacional relevante.
- Validacao: `py_compile` e suite completa
  `tests.test_position_manager_service.PositionManagerServiceTest`.

### Incidente De Performance: Log Quente Do Position Manager

- Sintoma: usuario relatou lentidao/travamento na aba Relatorio, especialmente
  ao rolar tabelas e acompanhar Saida Teorica MT5.
- Fluxo afetado: TraderIA Novo local em `localhost:8532`, aba Relatorio,
  Position Manager e ciclo leve MT5 Forex.
- Diagnostico:
  - processo Streamlit/Python ativo consumia aproximadamente 2.31 GB de RAM;
  - `.traderia/position_manager.jsonl` estava com aproximadamente 115 MB e
    mais de 100 mil linhas;
  - `.traderia/position_manager_current.json` ja existia como fonte leve para
    estado atual;
  - `load_mt5_forex_signals(timeframe="M1")` podia ficar pesado quando o rerun
    acionava export visual/Position Manager varias vezes no mesmo intervalo.
- Causa provavel: arquivo JSONL quente do Position Manager cresceu sem rotacao e
  passou a competir com renderizacao Streamlit, auditoria e leitura MT5.
- Acao aplicada:
  - arquivo quente arquivado como
    `.traderia/position_manager_20260717_002641.archive.jsonl`;
  - `PositionManagerService` passou a rotacionar automaticamente
    `position_manager.jsonl` quando exceder o limite configuravel;
  - limite padrao definido em 25 MB via
    `TRADERIA_POSITION_MANAGER_LOG_MAX_MB`;
  - export visual automatico MT5 passou a respeitar intervalo minimo padrao de
    5 segundos via `TRADERIA_MT5_VISUAL_AUTO_EXPORT_MIN_INTERVAL_SECONDS`.
- Resultado medido:
  - `load_mt5_forex_signals(timeframe="M1")` passou a responder em cerca de
    1.95 s na primeira leitura e 0.55 s na segunda leitura em cache quente;
  - `position_manager.jsonl` voltou para tamanho leve apos arquivamento.
- Guardrail: logs operacionais quentes nao podem crescer indefinidamente; o
  estado atual deve vir de snapshot leve e o JSONL deve ser tratado como trilha
  historica rotacionavel.
- Validacao: `py_compile` em `dashboard_app.py`,
  `application/dashboard_service.py` e `application/position_manager_service.py`;
  suite `tests.test_position_manager_service.PositionManagerServiceTest`; teste
  focado de sincronismo M4/M1 no Robo Demo.

## 2026-07-13

### Ajuste Operacional: BETA002 Protege Sem Full Exit

- Sintoma: usuario observou que as saidas nao alcancavam nem ganho cheio nem
  loss cheio.
- Diagnostico: os fechamentos `BETA_FULL_EXIT` recentes estavam concentrando
  perdas pequenas e impedindo que alguns trades respirassem ate TP/SL.
- Acao aplicada: `BETA002` passou a operar com `allow_full_exit=false`.
- Acao aplicada: protecao de SL do BETA002 passou a exigir pelo menos `1.0R`
  antes de mover stop.
- Comportamento esperado: entrada, stop inicial e alvo continuam vindos do Lab;
  Position Manager acompanha o mercado, preserva a posicao antes de 1R e, depois
  de 1R, pode proteger o SL quando houver enfraquecimento/defesa.
- Guardrail: nenhuma leitura pesada do Lab foi adicionada ao ciclo leve.

### Nova Alpha Experimental: ALPHA016 BETA002 Reversal Signal

- Hipotese: a leitura que tornava o `FULL_EXIT` ruim como saida pode ter valor
  como entrada contraria, quando tendencia previa perde continuidade e momentum
  vira contra o fluxo.
- Acao aplicada: criada `ALPHA016` com modelo `BETA002_REVERSAL_SIGNAL`.
- Escopo: somente comparacao no Lab; nao substitui Alphas atuais e nao reativa
  `FULL_EXIT`.
- Grade adicionada: 54 cenarios novos combinando EMA, ATR stop, RR e forca de
  reversao.
- Regra: tendencia `BAIXA` com momentum positivo suficiente gera candidato
  `BUY`; tendencia `ALTA` com momentum negativo suficiente gera candidato
  `SELL`.
- Validacao: testes focados confirmam registro na biblioteca, entrada na grade e
  decisao BUY/SELL reversa.

### Conferencia Visual: Entrada Teorica Versus Posicao Aberta

- Sintoma: usuario pediu para checar se entrada teorica estava batendo com a
  pratica.
- Diagnostico: algumas posicoes abertas pertenciam a planos anteriores, enquanto
  a leitura teorica atual ja estava em `WAIT` ou direcao oposta.
- Acao aplicada: tabela `Entrada Teorica MT5` passou a exibir `Posicao aberta`,
  `Direcao posicao`, `Alpha posicao`, `Sinal teorico atual` e `Confere posicao`.
- Resultado esperado: divergencias ficam visiveis como `BATE`,
  `DIVERGIU: sinal atual WAIT` ou `DIVERGIU: posicao X x sinal Y`.
- Guardrail: a conferencia usa dados ja presentes na linha da tabela; nao cria
  nova leitura pesada do MT5 no render.

### Aprendizado Operacional: Robo Demo Desarmava No Rerun Do Streamlit

- Sintoma: usuario informou que o TraderIA Novo nao estava enviando ordem,
  apesar de existirem candidatos com `PLANO_VALIDO`.
- Fluxo afetado: aba MT5 Forex, painel Robo Demo MT5, porta `8532`.
- Diagnostico:
  - MT5 conectado com `trade_allowed=True`, `trade_expert=True` e servidor
    `Pepperstone-Demo`;
  - `.traderia/mt5_demo_execution.jsonl` registrava ordens aceitas ate
    `2026-07-13 11:17`;
  - havia candidatos atuais com `PLANO_VALIDO` e `BETA002 ADAPTIVE_FULL_EXIT`;
  - `DashboardService.get_demo_robot_status()` retornava `DISARMED` e
    `MT5_DEMO_DISABLED` apos rerun/restart do Streamlit.
- Causa raiz: o estado online do Robo Demo ficava na sessao Streamlit, mas o
  `DashboardService` novo criado no rerun nascia sem memoria de que o robo
  estava armado. O ciclo online interpretava esse estado transitorio como
  bloqueio real e desligava antes de avaliar/enviar ordem.
- Acao aplicada: `_run_demo_robot_online_cycle_if_due()` passou a rearmar o
  backend em memoria quando a sessao Streamlit ainda esta online e a leitura
  inicial do servico vem `DISARMED`.
- Guardrail de velocidade: a correcao nao adiciona consulta pesada, nao
  recalcula Lab, nao reduz o intervalo do ciclo e nao inicia envio extra; apenas
  reidrata o estado do backend antes da avaliacao normal.
- Validacao: `python -m py_compile dashboard_app.py` e testes focados do ciclo
  online do Robo Demo passaram.
- Aprendizado: estado operacional confirmado pela sessao nao pode ser apagado
  por leitura transitoria de backend recem-instanciado. Desarmar robo deve ser
  acao explicita, bloqueio real de backend persistente ou flag demo desligada.

### Pendencia De Velocidade Registrada

- Usuario sinalizou que a velocidade do TraderIA Novo deve continuar no radar.
- Registrado em `docs/NEXT_MISSION.md` como parte da proxima missao de health
  check operacional e sentinela de velocidade.
- Pontos criticos a acompanhar: aba Relatorios, Saida Teorica MT5, leitura do
  Position Manager, historico MT5, paginacao de tabelas grandes e ausencia de
  leitura pesada do snapshot do Lab no ciclo leve.
- Guardrail: nao desligar leitura de mercado essencial do BETA002 apenas para
  ganhar velocidade; primeiro medir, localizar o gargalo e otimizar.

### Incidente Operacional: App Aparentemente Parado

- Sintoma: usuario informou que o app parou apos ajustes no BETA002.
- Fluxo afetado: TraderIA Novo local em `localhost:8532`.
- Diagnostico executado: processo Streamlit estava ativo; porta `8532`
  respondia `HTTP 200`; `get_light_dashboard_view_model()` retornou OK;
  `get_mt5_trade_audit_report()` retornou 171 registros.
- Causa provavel: congelamento/estado antigo da sessao do navegador ou sessao
  Streamlit travada no cliente, nao queda do backend.
- Acao aplicada: reinicio limpo do Streamlit na porta `8532`.
- Resultado: novo processo iniciado e `HTTP 200` confirmado.
- Prevencao registrada: todo travamento aparente deve ser tratado como evento
  arquitetural e registrado com aba afetada, sintoma, processo/porta, resposta
  backend, causa provavel e acao corretiva antes de novas mudancas.
- Arquitetura atualizada: `docs/ARCHITECTURE.md` recebeu a politica de
  travamentos e regressao de velocidade.

## 2026-07-07

### Estado Base Registrado

- Projeto assumido como `TraderIA Novo`.
- App local rodando em `http://localhost:8532`.
- Runtime local mantido em `.traderia/`.
- GitHub usado para codigo, documentacao e governanca.

### Ajustes Operacionais Recentes

- Titulo principal alterado para `TraderIA Novo`.
- Fast boot deixou de ser tela principal.
- MT5 Forex deixou de atualizar por ciclo automatico bloqueante.
- Lab passou a rodar localmente na propria pasta `traderiaianovo`.
- Relatorios passaram a carregar auditoria local ao abrir e atualizar por botao.

### Validacoes Observadas

- Lab local retornou 8 pares e 16956 cenarios a partir do snapshot local.
- Relatorios retornaram 102 registros locais, 100 aceitos, 100 auditados,
  100 conferem e 0 divergencias.
- App respondeu `HTTP 200` em `localhost:8532` apos reinicios.

### Commits Relevantes

- `a0629a4` - Run TraderIAnovo Lab from local runtime
- `a39252e` - Load reports tab from local audit cache

## Politica

Novas entradas devem registrar:

- data;
- missao;
- arquivos alterados;
- validacao executada;
- commit gerado;
- pendencias.

## 2026-08-10 - Integracao visual e relatorios M13-M17

- Sintoma: a aba MT5 ainda declarava M1-M12 e Relatorios oferecia somente os
  filtros M1-M12, apesar de a familia Forex M13-M17 existir no motor.
- Correcao: seletor, avisos, rotulos curtos e blocos de entrada MT5 passaram a
  expor M13-M17; o grafico principal e as curvas individuais passaram a usar
  M1-M17.
- Auditoria: M13-M17 foram separados por ID operacional atual e universo dos
  17 pares Forex, impedindo mistura com os contratos historicos M13-M16.
- Validacao: compilacao aprovada, 16 testes focados aprovados e conferencia
  visual confirmou os cinco blocos na aba MT5 e os cinco filtros em Relatorios.
- Runtime: Streamlit reiniciado na porta 8532; health HTTP 200 confirmado.
- Seguranca: nenhuma ordem foi enviada ou modificada durante a correcao.

## 2026-08-05 - Modelos M8-M14 com saida dinamica protect-only

- Missao: criar sete variantes independentes de M1-M7 sem alterar os modelos
  fixos existentes.
- Implementacao:
  - M8->M1, M9->M2, M10->M3, M11->M4, M12->M5, M13->M6 e M14->M7;
  - entrada, Alpha, timeframe, SL inicial, TP e RR preservados integralmente;
  - politica pos-entrada `DYNAMIC_PROTECT_ONLY`;
  - protecao liberada somente depois de 1,50R;
  - `EARLY_EXIT` e `FULL_EXIT` bloqueados inclusive quando a chave global esta
    ativa;
  - resultado de entrada do modelo de origem reutilizado no ciclo, sem Lab
    pesado nem consulta MT5 adicional;
  - coexistencia A/B entre modelo fixo e sua variante dinamica, mantendo a
    deduplicacao da mesma variante no mesmo plano/candle.
- Superacao historica: IDs antigos M8-M22 permanecem no historico e aposentados
  para novas entradas; somente os novos IDs canonicos M8-M14 estao ativos.
- Validacao inicial: testes de mapa, identidade, paridade do plano e movimento
  de SL protect-only aprovados.
- Commit: pendente de solicitacao explicita.

## 2026-08-04 - Auditoria e reducao de memoria do runtime

- Sintoma: app lento apos permanecer aberto; processo da porta `8532` usava
  aproximadamente 1707,9 MB de RAM de trabalho e 1966,4 MB de memoria privada.
- Causa principal: cada sessao Streamlit mantinha uma `DashboardService`
  pesada, enquanto ciclos Forex, Robo Demo e agenda mantinham outras fachadas;
  o historico JSONL de execucao era convertido novamente por fachada.
- Correcao:
  - fachada visual compartilhada entre sessoes do mesmo processo;
  - cache process-local incremental de `mt5_demo_execution.jsonl`;
  - rejeicoes antigas compactadas em memoria, preservando contagem;
  - operacoes aceitas preservadas integralmente para auditoria e Position
    Manager;
  - ciclo Forex libera caches quando o Robo Demo assume a leitura;
  - aviso repetitivo do seletor operacional removido.
- Resultado apos reinicio e sessao completa: 366,7 MB de RAM de trabalho e
  564,3 MB privada; apos 35 segundos e varios ciclos, aumento de apenas 1,66 MB.
- Operacao preservada: health `200`, MT5 `CONNECTED`, Robo Demo `online` em
  `TODOS`, ciclo de 10 segundos e `BATCH_COMPLETED` confirmados.
- Guardiao atualizado: limite 1600 MB, checagem a cada 60 segundos e log
  saudavel a cada 10 minutos. A descoberta do processo usa diretamente o PID
  em `LISTENING` retornado por `netstat`, sem consulta CIM bloqueante. O guardiao
  exige tres falhas consecutivas de health e usa mutex por porta para impedir
  supervisores duplicados.
- Validacao: 3 testes do registro de runtime, 15 testes de persistencia, teste
  incremental do JSONL e 10 testes focados de ciclos/chaveamento passaram.
- Incidente durante validacao: Relatorio recebeu `PermissionError` ao gravar
  `.traderia/runtime/runtime_lock.json` sob concorrencia do OneDrive. A origem
  foi corrigida com lock process-local, escrita atomica, tres tentativas curtas
  e fallback sem stacktrace; o ultimo cache do Relatorio e preservado.
## 2026-08-03 - ALPHA017 experimental de reversao multiativos

- adicionada `ALPHA017_MULTI_CURRENCY_GRID_MEAN_REVERSION` ao Lab/Replay;
- entrada exige Bollinger, Z-Score, RSI, ADX baixo e ATR valido;
- Replay usa SL/TP substitutos de posicao unica e nao representa uma grade;
- Alpha permanece `RESEARCH_ONLY`, sem modelo operacional e sem envio MT5;
- documentados limites de correlacao, exposicao de cesta e progressao de lote.

## 2026-08-03 - Sublaboratorio Multi EA Trading

- Missao: extrair hipoteses de setup a partir do CSV/PDF publico, usando a
  primeira amostra aprovada de 5.000 candles por serie e incluindo ouro.
- Seguranca inicial:
  - restore package local `20260803_202301` criado;
  - branch `codex/multi-ea-trading-lab` criada;
  - tag local `restore-traderia-20260803-2023` preservada;
  - estado anterior consolidado no commit `604c6f3`.
- Implementacao:
  - motor puro `research/multi_ea_trading_lab.py`;
  - adapter isolado `infrastructure/research/multi_ea_local_data_adapter.py`;
  - caso de uso sob demanda e fachada `DashboardService`;
  - painel `Multi EA Trading` dentro do Lab;
  - banco XAUUSD separado do historico operacional;
  - guardrail `operational_eligible=False` no Trade Plan e nos seletores do Lab.
- Dados executados:
  - 322 posicoes fechadas e cinco eventos Balance;
  - 25.000 candles XAUUSD baixados em M1/M5/M15/M30/H1;
  - 40 series completas, 200.000 candles e cobertura de 212/322 posicoes;
  - banco operacional preservado com data de modificacao 2026-07-21.
- Resultado:
  - EMA 20/50 liderou somente no treino (0,1703) e ficou instavel no holdout
    (0,0333); nenhuma regra global foi identificada como o setup original;
  - melhor aproximacao parcial do ouro: M15, Z-Score 20/1,5 e RSI14
    25/75 ou 30/70, classificada como `HOLDOUT_INCONCLUSIVO` por ter apenas
    quatro gatilhos no holdout;
  - ALPHA017 estrita classificada como `NAO_SUPORTADA_PELA_AMOSTRA`.
- Validacao:
  - 51 testes focados de sublab, adapter, API, painel e Trade Plan passaram;
  - 17 testes especificos passaram novamente apos o hardening do ouro;
  - `scripts/run_critical_ci.py`: 152 testes passaram;
  - `git diff --check` sem erro.
- Revisao cientifica final:
  - selecao e ordenacao passaram a usar somente o treino cronologico;
  - score recalibrado contra baseline aleatorio de 50%;
  - download de ouro falha fechado se qualquer um dos cinco timeframes tiver
    menos de 5.000 candles unicos efetivamente persistidos;
  - painel passou a exibir cobertura detalhada por timeframe e separar score
    de treino, holdout e amostra completa;
  - bootstrap limpo disponivel por `TRADERIA_MULTI_EA_POSITIONS_CSV`.
- Pendencias:
  - confirmar o fuso do CSV antes de tratar a associacao temporal como forte;
  - baixar os dez ativos ainda sem historico se for necessaria cobertura maior;
  - nao inferir regras de saida, grade ou lote sem dados adicionais.

## 2026-08-06 - Correcao de travamento por ciclo MT5 na interface

- Sintoma: porta 8532 iniciava, mas `/_stcore/health` deixava de responder apos
  uma sessao web reconectar, mesmo com uso de memoria proximo de 225 MB.
- Causa: fallbacks de `_maybe_run_mt5_forex_auto_cycle()` e
  `_maybe_run_demo_robot_global_cycle()` podiam executar leitura MT5 ou o ciclo
  completo do Robo Demo dentro do rerender Streamlit.
- Correcao: ciclos automaticos permanecem nos threads de fundo; Forex, demais
  abas e fragmentos apenas consomem o snapshot compartilhado.
- Seguranca: nenhuma regra de entrada, stop, alvo, modelo ou envio foi alterada.
- Uma segunda origem foi encontrada no exportador visual, que consultava
  `positions_get()` diretamente, e na auditoria do Relatorio, que consultava
  sessao, saldo e historico no processo Streamlit.
- Candles, posicoes visuais e Relatorio passaram a usar processos externos com
  timeout; `TRADERIA_MT5_INPROCESS_ENABLED=1` continua disponivel para os
  componentes operacionais que exigem a sessao persistente.
- Validacao final: 11 sondas consecutivas da rota de saude responderam em
  73-974 ms durante mais de 80 segundos, com ciclo Forex de fundo e Relatorio
  ativos, app em aproximadamente 270 MB de RAM e execucao desativada.
- Testes focados: 48 verificacoes do M15/runtime e 13 do exportador/runtime
  passaram; compilacao dos modulos alterados e `git diff --check` sem erro.
- No modo operacional completo, `list_open_positions()` do Position Manager foi
  a ultima chamada nativa bloqueante identificada. Lista de posicoes,
  duplicidade, preco e candles recentes passaram para sonda externa fail-closed;
  modificacao de SL e envio Demo permaneceram no provider operacional.
- Validacao operacional final: seis sondas consecutivas responderam em 45-153
  ms depois da inicializacao, com aproximadamente 191 MB de RAM; estado do robo
  preservado online e ultimo ciclo `NO_SIGNAL`, sem ordem enviada nesse ciclo.
- Mais 85 testes do provider, Position Manager e M15 passaram apos o isolamento.

## 2026-08-06 - Auditoria de RAM e rastreabilidade do M15

- RAM do Streamlit cresceu de aproximadamente 152 MB para 474 MB em pouco mais
  de duas horas; uma sonda de Relatorio consumia cerca de 130 MB e concorria
  com as leituras operacionais do MT5.
- O log `mt5_demo_execution.jsonl` atingiu aproximadamente 19,6 MB; leitores
  que precisavam somente dos ultimos 2.000 registros carregavam o arquivo todo.
- Foi criado um gate unico para os subprocessos MT5. Relatorio e visual agora
  preservam cache quando o ciclo operacional ocupa o gate.
- Cache read-only de posicoes e horario foi alinhado ao ciclo de 10 segundos.
- Leituras de duplicidade e da interface passaram a usar cauda binaria limitada.
- O M15 passou a gravar `.traderia/model15_runtime_state.json` somente quando
  candle ou decisao mudam, registrando EMA20/50, gatilho, stop e motivo atual.
- O guard de RAM passa a reiniciar preventivamente o Streamlit em 900 MB,
  preservando o estado persistido do robo e do modelo selecionado.

## 2026-08-06 - Preservacao visual das posicoes e entrada M15

- A ausencia intermitente da Saida Teorica foi rastreada a uma dependencia do
  Relatorio completo: quando a sonda de historico cedia o gate ao ciclo
  operacional, a interface interpretava a falta temporaria de resposta como
  ausencia de posicao.
- A interface passou a complementar o Relatorio com uma leitura leve de
  `positions_get()`, mesclada por ticket e preservando modelo/plano auditado.
- Falha transitoria da sonda mantem a ultima lista valida; ela nao apaga mais
  as posicoes exibidas.
- O M15 permanece independente no XAUUSD/M5. Seu estado compacto permite que a
  UI mostre candle fechado, EMA20/50, gatilho e stop mesmo sem carregar candles
  pesados na sessao Streamlit.
- Validacao: 43 posicoes abertas recuperadas da conta Demo e classificadas por
  comentario `TraderIA M#`; 52 testes focados passaram.

## 2026-08-10 - Correcao do monitor M8-M12

- A tabela de indicadores rotulava M8-M12 como M1 e mostrava pares Forex/H1.
- Causa: ausencia dos casos M8-M12 no rotulo curto e uso indevido do adaptador
  generico do Lab para uma familia exclusiva XAUUSD/M5.
- M8-M12 passaram a consumir o mesmo avaliador XAUUSD/M5 usado pelo executor,
  com uma unica linha por modelo e indicadores especificos de cada setup.
- Validacao visual confirmou a sequencia M8, M9, M10, M11 e M12 em M5.
- Compilacao e 24 testes focados passaram; app local e URL publica permaneceram
  online, sem envio ou modificacao de ordens durante a correcao.

## 2026-08-10 - Supervisor de RAM integrado ao inicializador

## 2026-08-10 - Modelos Forex M13-M17

- M13/Setup A criado nos 17 pares Forex/M5;
- M14 adiciona ADX; M15 distância/ATR; M16 inclinação SMA50; M17 combina os três;
- entrada inicial a mercado, reentrada Stop, SL no pivô 2+2, sem TP e Full Exit
  RSI 70/30 ou inversão SMA foram preservados;
- buffer adaptado para um pip e estado isolado por modelo/par;
- identidades históricas M13-M16 preservadas somente para auditoria.

## 2026-08-10 - Supervisor de RAM integrado ao inicializador

- Auditoria operacional encontrou o Streamlit saudavel, mas com aproximadamente
  1,44 GB de RAM e sem processo persistente do supervisor de RAM.
- O limite preventivo de 900 MB ja existia em
  `scripts/traderianovo_ram_guard.ps1`, mas o inicializador nao o mantinha ativo.
- `scripts/abrir_traderianovo.ps1` passou a iniciar uma unica instancia do
  supervisor sempre que o app estiver saudavel.
- Na primeira ativacao, o supervisor reiniciou somente o Streamlit e reduziu o
  consumo para aproximadamente 113 MB. MT5, posicoes e estado online do Robo
  Demo foram preservados.
- O comando de recuperacao do supervisor foi alinhado ao inicializador oficial:
  escuta apenas em `127.0.0.1`, desativa telemetria do navegador e deixa a
  publicacao exclusivamente sob responsabilidade do tunnel HTTPS.
- App local e endereco publico responderam com HTTP 200 apos a recuperacao; a
  leitura direta confirmou MT5 conectado, negociacao permitida e candles M1.
# 2026-08-11 - Substituicao do M3 por XAUUSD/M5 RSI14=50

- criado `MODELO_3_XAU_M5_RSI50_FLIP` com RSI14 fechado: BUY acima de 50 e
  SELL abaixo de 50;
- Full Exit da posicao quando o RSI fecha no lado oposto e nova entrada
  contraria somente no ciclo posterior ao fechamento;
- SL estrutural 0,01 alem do pivo M5 2+2, sem TP fixo;
- antigo `MODELO_3_LAB_ALL_FOREX_WINNERS` aposentado para novas entradas e
  preservado por ID nos historicos;
- plano, gates, Robo Demo, Provider, Position Manager, monitor e curvas
  discriminam o novo ID;
- nenhuma ordem foi enviada durante a implementacao e o runtime nao foi
  reiniciado enquanto o Robo Demo poderia estar armado.
## 2026-08-11 - Diagnostico MT5: timeout do conector nao e terminal offline

- Confirmado que `terminal64.exe` (PID 3848) permaneceu aberto e responsivo, enquanto a leitura externa read-only expirava.
- O painel agora diferencia `CONNECTOR_TIMEOUT`/`AGUARDANDO_DADOS_MT5` de `DISCONNECTED`/`OFFLINE`.
- O gate visual passou a informar `AGUARDA: conector MT5 sem leitura`; o envio continua bloqueado ate haver candles M5 atuais.
- Streamlit reiniciado isoladamente na porta 8532, saude HTTP 200; terminal MT5 e posicoes nao foram reiniciados nem alterados.
- Validacao: 129 testes focados aprovados (2 de diagnostico + 127 da familia M8-M17/executor/position manager).

## 2026-08-11 - Janela M5 incremental de 52 velas

- Corrigido o warm cache operacional M8-M17 para preservar 51 velas anteriores e solicitar somente `count=1` no ciclo normal.
- A vela recebida substitui a vela em formacao do mesmo horario ou entra como a nova vela; a mais antiga e descartada, mantendo exatamente 52.
- Cache persistido com fonte `LIVE` continua vivo apos reinicio e nao exige novo lote de 52.
- Download completo de 52 fica restrito ao primeiro carregamento, cache com menos de 52 ou recuperacao de lacuna temporal real.
- Validacao: 68 testes de market data/cache/modelos + 83 testes de executor e position manager aprovados.

## 2026-08-11 - Recuperacao autorizada do IPC MT5

- Usuario autorizou reinicio do terminal com posicoes abertas.
- Leitor externo e painel foram encerrados antes do terminal; MT5 fechou normalmente por `CloseMainWindow()` e reabriu na mesma instalacao.
- Conta `61551556`/`Pepperstone-Demo` reconectada; `initialize()` e `CopyRates(EURUSD, M5, count=1)` retornaram sucesso.
- Confirmadas 18 posicoes preservadas no servidor; nenhuma ordem foi criada, fechada ou modificada.
- Streamlit religado na porta 8532 com saude HTTP 200.

## 2026-08-11 - Auditoria operacional e ativacao exclusiva M8-M17

- Criado o chaveamento persistente `MODELOS_8_A_17`; ele avalia e permite
  novas entradas somente para M8-M12 em XAUUSD/M5 e M13-M17 nos 17 pares
  Forex/M5. M1-M7 ficaram fora da fila de novas entradas, sem interferir na
  gestao das posicoes antigas.
- Eliminada a coexistencia de duas instancias Streamlit na porta 8532. O
  supervisor passou a manter uma unica instancia oficial saudavel.
- Cache auditado com exatamente 52 velas M5 `LIVE` em todos os 18 mercados.
- Corrigida a deduplicacao do executor para considerar M8-M17 modelos
  independentes. Planos A-E que compartilham par, candle, entrada e stop podem
  manter uma posicao separada por modelo, preservando a auditoria comparativa.
- MT5 `61551556`/`Pepperstone-Demo` confirmado conectado e com AlgoTrading
  liberado. A ativacao ao vivo abriu somente comentarios M8-M15; M16-M17
  permaneceram corretamente bloqueados pelos filtros do candle atual.
- Confirmadas posicoes separadas M8, M9, M10, M11 e M12 no XAUUSD e saidas
  automaticas `TraderIA PM EXIT` nas posicoes Forex M13-M15.
- O estado de reentrada Forex deixou de herdar `symbol: XAUUSD`; cada arquivo
  M13-M17 agora persiste o par Forex auditado, inclusive os estados EURNZD ja
  existentes.
- Validacao: 7 testes focados do chaveamento/deduplicacao e 137 testes da
  familia M8-M17, cache, executor e runtime aprovados; mais 75 testes passaram
  apos a correcao do estado de reentrada por par.

## 2026-08-11 - Recuperacao preventiva de RAM do painel

- O processo Streamlit da porta 8532 consumia 860,2 MB de RAM de trabalho e
  1.072,8 MB de memoria privada; o Windows estava com 92,1% da RAM em uso.
- Foram encontradas cinco abas duplicadas do painel MT5 Forex. Quatro copias
  foram fechadas e uma unica sessao visual foi preservada.
- Somente o processo Streamlit foi reiniciado pelo supervisor oficial. O
  terminal MT5, a conta Demo, as posicoes, as ordens e o cache local nao foram
  alterados.
- Depois da reconexao e de varios ciclos visuais, o painel estabilizou em
  aproximadamente 361 MB de RAM de trabalho; a memoria livre do Windows subiu
  de 1,25 GB para 2,66 GB.
- Validacao: porta 8532 com HTTP 200, uma unica instancia oficial, supervisor
  de RAM ativo, terminal64 preservado e selecao operacional M8-M17 mantida.
# 2026-08-12 - Rollover vivo e entradas teoricas M23

- restauradas as tabelas individuais de entrada teorica M1-M22 abaixo do consolidado M23, reutilizando o mesmo snapshot;
- eliminada a falsa janela de rollover de uma hora causada pelo horario do candle H1 quando a sonda do servidor estava ocupada;
- preservado e extrapolado o ultimo horario MT5 valido entre leituras transitorias;
- mantida a rejeicao final `Market closed` no provider MT5 para instrumentos realmente fechados;
- validacao focada: 42 testes aprovados para Camada Tempo, Robo Demo e cesta M23.

# 2026-08-13 - Pico de lucro aberto preservado no historico

- adicionado rastreamento monotonicamente crescente do maior `profit` MT5 por
  ticket aberto;
- persistencia local leve em SQLite, sem chamada adicional ao MT5 e sem Lab;
- historico fechado e CSV passam a informar pico e horario observado;
- dados anteriores a implantacao permanecem `N/D`, sem estimativa artificial;
- testes cobrem crescimento, nao regressao, tickets independentes e preservacao
  do pico apos o fechamento.
- auditoria posterior identificou fechamentos entre ciclos cujo resultado final
  superava o ultimo pico amostrado; para tickets ja monitorados, o fechamento
  agora eleva o pico ao valor realizado, sem preencher operacoes antigas.
- o launcher passou a restaurar o terminal MT5 antes do Streamlit quando ambos
  nao voltarem automaticamente depois de uma reinicializacao do computador.

## 2026-08-13 - Reentrada XAU condicionada ao recuo estrutural M5

- preservadas integralmente a primeira entrada, filtros, SL, TP e saidas;
- SELL agora exige dois candles fechados com maxima/minima ascendentes antes de
  armar SELL STOP na minima do ultimo candle M5 fechado;
- BUY aplica a regra oposta e arma BUY STOP na maxima do ultimo candle fechado;
- regra compartilhada por M8-M12, derivados M18-M22 e copias dessas fontes no M23;
- reentrada em tendencia reta, sem recuo oposto, passou a falhar fechada.

## 2026-08-13 - TP estrutural XAU no M23 e sincronismo do relogio MT5

- confirmada janela deslizante com 200 velas M5 fechadas mais a atual;
- indicadores continuam usando somente candles fechados;
- expiracao de pendencias passou a comparar com `tick.time` do servidor MT5,
  eliminando mistura com o UTC da maquina;
- reentrada SELL do XAU permanece `SELL_STOP` na minima do ultimo M5 fechado
  apos correcao ascendente; BUY aplica a regra oposta;
- M23 usa ultimo fundo confirmado como TP do SELL e ultimo topo confirmado como
  TP do BUY; sem estrutura valida, a rota M23 aguarda;
- novo candle fechado pode substituir o gatilho pendente da mesma estrategia;
- apos Full Exit RSI50 de uma reentrada, o estado volta a aguardar nova correcao
  e nao retorna indevidamente para entrada inicial a mercado;
- Full Exit coletivo do M23 permanece em +US$1.000 liquidos.
# 2026-08-13 - M18-M22 com TP estrutural e Full Exit RSI50

- A primeira entrada de M18-M22 permanece sem TP.
- Reentrada BUY exige RSI14 fechado acima de 50 e recebe TP no ultimo topo M5
  confirmado antes da correcao; SELL exige RSI14 abaixo de 50 e recebe TP no
  ultimo fundo M5 confirmado antes da correcao.
- Reentrada BUY executa Full Exit na perda fechada do RSI50; SELL executa Full
  Exit na retomada fechada acima de 50. Inversao SMA20/SMA50 tambem encerra.
- M23 herda entrada, SL, TP estrutural e Full Exit da fonte, mantendo como regra
  adicional exclusiva a zeragem das posicoes M23 ao atingir US$ 1.000 na cesta.
- Ordem Stop nao executada vale por um candle M5 e e substituida no fechamento
  seguinte pelo novo extremo, sem manter gatilho antigo congelado.
- IDs operacionais M18-M22 foram preservados para compatibilidade com historico
  e posicoes; novos Alpha/Beta/fonte declaram explicitamente o alvo estrutural.

# 2026-08-13 - Reconciliacao obrigatoria do cache operacional M5

- auditoria encontrou cache persistido `LIVE` divergente do lote atual do MT5
  depois de periodo offline, inclusive com fechamentos parciais antigos;
- todo cache M5 restaurado passou a ser somente aquecimento e exige substituicao
  integral pelas 201 barras do terminal antes de liberar sinal operacional;
- o ciclo leve passou a ler a barra fechada anterior e a barra atual, corrigindo
  o fechamento definitivo sem recalcular Lab;
- lacuna, retorno fora de ordem ou cauda incompleta acionam recuperacao integral
  e mantem a entrada bloqueada ate a reconciliacao;
- adicionados testes de regressao para reinicio, fechamento parcial e retorno do
  MT5 apos lacuna de varios candles.

# 2026-08-13 - Fundacao da refatoracao segura

- criado ponto Git `restore-traderia-20260813-2217` e pacote local sanitizado;
- criado worktree isolado `C:\Users\evcab\TraderIAnovo_Refactor_Safe` na branch
  `codex/safe-refactor-foundation`, sem runtime local e sem envio de ordens;
- auditoria arquitetural passou a aceitar fontes Python com BOM UTF-8;
- manifesto reconciliado com servico e contratos publicos ja presentes;
- caminhos obrigatorios de governanca em `AGENTS.md` corrigidos;
- criado contrato de equivalencia e baseline documental para impedir mudancas
  silenciosas em Lab, ciclo leve, modelos, M23, Position Manager e MT5;
- nenhuma alteracao funcional foi aplicada ao app operacional.

# 2026-08-13 - Fechamento do escape de IDs historicos

- IDs historicos `MODELO_8_TREND_PULLBACK_H1_M5`,
  `MODELO_21_ESPELHO_M19` e `MODELO_22_ESPELHO_M9` passaram a ser rejeitados
  explicitamente antes do fallback por numero;
- a mesma defesa foi aplicada a familia historica
  `MODELO_8_DYNAMIC_EXIT_FROM_M1` ate `MODELO_14_DYNAMIC_EXIT_FROM_M7`;
- IDs canonicos atuais M8, M21 e M22 permanecem ativos e independentes;
- o reparo atua somente sobre novas ordens com identificador historico e nao
  altera posicoes existentes, sinais, SL, TP ou modelos canonicos.

# 2026-08-13 - Reconciliacao da janela operacional 200+1

- testes de dados MT5 passaram a refletir 200 candles fechados para indicadores
  e um candle atual em formacao, totalizando 201 registros no ciclo leve;
- fixtures de pesquisa passaram a usar horarios unicos e preservam a prova de
  5.000 velas no fluxo pesado sob demanda;
- o diagnostico considera valida a relacao configurado 200 / solicitado 201;
- nenhum calculo de indicador, sinal ou ordem foi alterado.

# 2026-08-13 - Gate deterministico da refatoracao segura

- criado `scripts/run_safe_refactor_gate.py`, sem conexao MT5, ambiente externo
  ou Lab pesado;
- a UI deixou de importar `sqlite3`; erros da prova de replay passam pela
  excecao `DashboardServiceError` da fachada;
- gate final: 314 testes e 381 subtestes aprovados em 209,61 segundos;
- divergencias historicas de pandas offline e SQLite direto na fachada foram
  documentadas para missoes isoladas, sem mudar trading ou persistencia.

# 2026-08-17 - Criacao operacional do M24

- criado `MODELO_24_XAU_RSI50_BASKET` para XAUUSD/M5 com fontes M8, M10 e M18-M22;
- entrada inicial passou a exigir micropivo 1+1, RSI14 cruzando 50 e fechamento
  acima/abaixo da SMA20; a SMA50 nao participa dessa entrada;
- preservadas duas reentradas: Stop estrutural e RSI50 a mercado com SMA20/50;
- reentrada RSI50 usa SL no candle anterior e trailing monotono por candle M5;
- TP individual foi removido de todas as rotas M24; cesta isolada encerra em
  +US$1.000 liquidos sem tocar M23 ou modelos diretos;
- seletor, provider, Position Manager, dashboard, relatorio e politica de IDs
  passaram a reconhecer M24;
- nenhuma ordem foi enviada durante implementacao ou testes.

# 2026-08-17 - Incidente no seletor operacional apos M24

- sintoma: a aba MT5 Forex interrompia a renderizacao com
  `StreamlitDuplicateElementKey` na chave
  `mt5_operational_model_checkbox_todos`;
- causa: a chave de qualquer ID sem numero reconhecido reutilizava o sufixo
  reservado de `Todos`; um processo vivo com a politica anterior ao M24 podia
  interpretar M24 como desconhecido;
- correcao: `Todos` passou a ser tratado explicitamente e IDs desconhecidos
  recebem sufixo normalizado do proprio identificador;
- prevencao: teste simula o M24 nao reconhecido por uma politica antiga e exige
  unicidade de todas as chaves do seletor;
- validacao: 3 testes direcionados e 188 testes do gate critico aprovados;
- impacto operacional: nenhuma selecao persistida, setup ou ordem foi alterada.

# 2026-08-17 - Aplicar M24 nao atualizava o texto

- sintoma: M24 aparecia marcado no formulario, mas o resumo, o aviso e o arquivo
  persistido continuavam indicando M23;
- causa: no fragmento periodico, a gravacao dependia do valor retornado pelo
  botao depois da renderizacao e podia ser perdida antes do rerender;
- correcao: a persistencia passou para o callback do `form_submit_button`,
  executado antes da nova renderizacao;
- prova: teste Streamlit real trocou M23 por M24, confirmou o resumo `M24`,
  confirmou o aviso `M24 ativo` e a ausencia de `M23 ativo` na mesma tela;
- validacao: 4 testes direcionados, 1 teste real de interface e 188 testes do
  gate critico aprovados;
- seguranca: estado operacional original foi restaurado apos o teste; nenhuma
  conexao ou ordem MT5 foi executada pela validacao.
- apos a validacao, a intencao original do usuario foi reaplicada: somente M24
  ficou selecionado; a interface confirmou M24 marcado, M23 desmarcado, aviso
  `M24 ativo` presente e aviso `M23 ativo` ausente.

# 2026-08-17 - Tipo de entrada visivel em negociacao

- adicionada a coluna `Tipo de entrada` imediatamente antes de `Alvo` na tabela
  compacta de operacoes abertas;
- classificacao usa primeiro o papel persistido no snapshot do plano, incluindo
  `m24_entry_role=INITIAL`, `REENTRY` ou `STRUCTURAL_REENTRY`;
- valores visuais sao `PRINCIPAL`, `REENTRADA` e `N/D` quando nao ha prova;
- leitura do snapshot operacional atual confirmou a posicao M24 aberta como
  `REENTRADA`;
- gate critico: 188 testes aprovados;
- nenhuma regra de entrada, saida, cesta, stop, alvo ou envio foi modificada.

# 2026-08-17 - SL das reentradas M24 no micro pivo

- reentrada Stop estrutural deixou de herdar o pivo 2+2 da fonte;
- reentrada RSI50 a mercado deixou de usar o extremo do candle anterior;
- as duas reentradas agora exigem microfundo 1+1 no BUY ou microtopo 1+1 no
  SELL, confirmado nos ultimos cinco candles M5 fechados;
- sem micro pivo valido, a reentrada permanece bloqueada e informa a causa real;
- o Position Manager reconhece explicitamente as variantes M24 e so move o SL
  para um novo micro pivo mais favoravel, inclusive em contratos M24 existentes;
- validacao: 53 testes direcionados e 188 testes do gate critico aprovados;
- testes usaram provider local; nenhuma ordem, fechamento ou alteracao MT5 real
  foi executada.

# 2026-08-17 - Primeira reentrada M24 ignorada apos RSI extremo

- Full Exit BUY confirmado no retorno do RSI de 70 para baixo passa a armar o
  descarte da primeira reentrada BUY;
- Full Exit SELL confirmado no retorno do RSI de 30 para cima aplica a mesma
  regra para a primeira reentrada SELL;
- o estado e isolado por fonte M24 e direcao;
- reavaliacoes de 10 segundos na mesma vela usam a mesma chave e permanecem
  bloqueadas; somente uma nova oportunidade valida em outra vela M5 e liberada;
- a trava cobre reentrada Stop estrutural e reentrada RSI50 a mercado, sem
  alterar entrada principal, inversao SMA ou Full Exit da cesta;
- validacao: 56 testes direcionados e 188 testes do gate critico aprovados;
- nenhuma operacao MT5 real foi enviada, fechada ou modificada nos testes.

# 2026-08-17 - Entrada inicial mantida e reentrada pendente M24

- entrada inicial passou a memorizar separadamente o cruzamento do preco na
  SMA20 e do RSI14 no nivel 50; os dois podem ocorrer em velas M5 diferentes;
- a entrada so e liberada quando ambos permanecem do mesmo lado na direcao do
  sinal, com SL no micro pivo anterior mais proximo;
- reentrada deixou de exigir novo cruzamento e passou a gerar BUY_STOP/SELL_STOP
  na maxima/minima do ultimo M5 quando preco e RSI permanecem alinhados;
- a pendente usa SL no micro pivo 1+1 anterior mais proximo e continua sujeita
  ao descarte da primeira oportunidade depois do Full Exit RSI 70/30;
- escrita atomica do estado M24 passou a repetir bloqueios curtos do
  Windows/OneDrive, corrigindo o diagnostico intermitente `WinError 5`;
- corrigida a barreira que interrompia o ciclo no plano-base H1 antes de o M24
  materializar seu proprio plano M5; esse era o motivo de o sinal tecnico estar
  pronto sem produzir candidato operacional;
- validacao: 75 testes direcionados e 188 testes do gate critico aprovados;
- nenhuma operacao MT5 real foi enviada, fechada ou modificada nos testes.
