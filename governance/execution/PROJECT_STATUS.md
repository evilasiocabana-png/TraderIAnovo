## 2026-09-24 - Aprendizado persistente e M30 Demo

Coleta causal separada do runtime de mercado; baseline versionada preserva
Replay, setups e filtros M23. M30 adicional habilitado na mesma Demo hedging,
com identidade, pareamento e cesta independentes. Real permanece desligada.
Ciclo estatistico diario persistente: candidato congelado, validacao futura,
promocao somente M30 e reversao conservadora. Sem amostra, mantem baseline.
Validacao: 272 testes e dois subtestes; recarga controlada com health OK e
selecao, estado online e agenda byte-identicos. Aba Aprendizado confirmada
no navegador com 313 variantes (60 prospectivas), banco 4.44 MiB e consulta
local de aproximadamente 3 ms. Diario inicial INCONCLUSIVO. Nenhum par M30
natural confirmado ainda; nenhuma ordem forcada para testar. Proximo marco:
conciliar a primeira dupla natural e acumular evidencia futura suficiente.
Contrato: docs/architecture/OPERATIONAL_MODEL_30_LEARNING.md.

Recarga concluida pelo launcher oficial. Health ok e pagina HTTP200;
selecao, estado online e agenda preservados por hash. Real DISABLED.
Construtor historico M29 aceita historical_alternations em processo novo;
a recarga remove a classe antiga em memoria observada no erro do relatorio.
Nenhuma ordem enviada para testar, nenhum ajuste de posicao executado.

## 2026-09-23 - Defesa inicial USD200 nas entradas diretas M23

Novas ordens diretas M23 recebem SL limitado a USD200 de perda bruta modelada
por order_calc_profit da corretora, com ativo, volume e preco do request.
Stops estruturais menores sao preservados; falhas bloqueiam envio. TP, RSI,
fontes, lotes e gestao existente preservados. Copias M29 mantem sua defesa
vigente separada. Nenhuma alteracao retroativa de posicoes ou pendentes.
Validacao: 241 testes e quatro subtestes aprovados, incluindo executor falso,
M18/M20 BUY/SELL, stops menores/maiores, falhas e saidas RSI50.
Contrato: docs/architecture/M23_FIXED_LOSS_DEFENSE.md.

## 2026-09-23 - Restauracao historica M29 e defesa fixa USD200

Usuario confirmou a referencia da operacao 5400 e autorizou o pacote completo.
Copias normais M8/M10/M18/M20 a 0.10; M7 por sequencia historica, espelho 0.20.
Canais deixam de comandar entradas. Defesa somente em novas copias normais
dessas quatro fontes via M23, mantendo TP e stop estrutural mais proximo.
Broker calcula risco bruto em USD; falha bloqueia entrada. Sem trailing.
Posicoes existentes e M7 espelhado fora da defesa; Real permanece desligada.
Validacao final: 248 testes e dois subtestes aprovados. Recarregado pelo
launcher oficial; health local ok, publico HTTP200, novo ciclo Demo
AGUARDANDO_PLANO/SEM_GATILHO_VALIDO e Real DISABLED confirmados.
Contrato e limitacoes: docs/architecture/M29_HISTORICAL_FIXED_DEFENSE.md.

## 2026-09-21 - Canais independentes M7, M8, M10, M18 e M20 no M29

Usuario autorizou ampliar normal/espelhado para M8, M10, M18 e M20.
Cada fonte usa apenas suas posicoes originais M23 encerradas no ouro.
Estado separado por fonte, conta e ativo; sem canal confirmado aguarda.
Mesma regra causal de tendencia e um fechamento fora; RR1 no espelho,
lote 0.20 espelhado e 0.10 normal. Dupla exige entrada original confirmada
do mesmo sinal e espera ambas encerrarem. Retry persistente legado segue
somente M7; demais fontes nao reutilizam confirmacoes historicas.
M1/M2/M5 normais, M21/M22 fora, Real desabilitada; sem alterar posicoes abertas.
Primeira regressao: 147 testes aprovados. Checagem final: 178 testes e dois
subtestes aprovados. Carregado pelo launcher oficial; health local ok e
site publico HTTP 200. Status Real DISABLED confirmado apos a recarga.

## 2026-09-21 - M7/M29: um encerramento fora do canal

Complemento autorizado: primeiro canal confirmado ou mudanca de tendencia
define NORMAL na alta e ESPELHADO na baixa. Um rompimento inferior antecipa
ESPELHADO; superior antecipa NORMAL. Reformar canal da mesma tendencia nao
desfaz essa antecipacao. No mesmo encerramento, rompimento tem precedencia.
Referencia M23/M7, sincronizacao e lotes preservados.

Usuario autorizou um encerramento abaixo do piso para ESPELHADO e um acima
do teto para NORMAL. Referencia segue M23/M7 no ouro, pivos confirmados sem
futuro. Grafico canonico usa a mesma constante operacional. Formacao do canal
continua exigindo dois topos e dois fundos. Lotes normal 0.10 e espelhado 0.20,
sincronizacao, fontes e autorizacao Real nao alterados.

## 2026-09-20 - Origem registrada na tabela de saidas

Modelo entrada prioriza envio Demo aceito com mesmo ticket e simbolo, em vez
do fallback TREND_MOMENTUM. Copias M29 incluem origem e modo registrado.
Leitura local limitada aos ultimos 2000 registros, com cache invalidado por mtime.
Sete verificacoes passaram: cinco posicoes de ouro e dois casos sem match.
Sem alteracao de sinais, posicoes ou autorizacao da Real.

## 2026-09-20 - Estado armado restaurado nos fragments

Corrigida sessao aberta antes da retomada semanal: fragments global e Forex
restauram o estado online persistido antes de consultar o snapshot do robo.
Antes, somente o layout completo fazia essa leitura, mantendo INATIVO/DISARMED
na tela enquanto o background ja monitorava. Nao altera agenda, sinais ou Real.
Tres testes especificos passaram. Suite facade: sete falhas preexistentes
reproduzidas tambem sem este patch; nao corrigidas nesta missao.

## 2026-09-18 - M7 somente ouro; Bitcoin retirado de novas entradas

Usuario reiterou retirar Bitcoin do M7. Escopo canonico passa a XAUUSD; universo
global de pesquisa mantem BTCUSD para outros modelos. Provider recusa M7 BTC
direto e copias M23/M29 antes de acessar terminal, inclusive plano antigo em cache.
Identidade legada M7 preservada para historico e gestao. Nao fecha posicoes, nao
apaga grafico/historico BTC e nao altera selecao, Real, agenda ou demais fontes.
Validacao: 93 testes passaram, incluindo escopo, barreira, copia e sincronizacao.
Catalogo consultado: M28 tem 3 candidatos BTC elegiveis, mas selecao salva contem
somente M23; nenhum modelo adicional foi ativado.

## 2026-09-18 - Graficos M7 separados: ouro e Bitcoin

Corrigida mistura da curva M23/M7: relatorio mostrava 46 XAUUSD e 20 BTCUSD
juntos. A vista agora tem dois graficos independentes, ambos lendo as posicoes
conciliadas pelo mesmo leitor do modo: ouro 46 / +US$3543.19; Bitcoin 21 /
-US$469.57 na verificacao. Custos entram uma vez por posicao; a diferenca de
US$16.10 do ouro no agregador antigo nao e herdada na nova vista. Agregador geral
legado nao foi alterado nesta missao. Historico completo por ativo, controles e
sequencias separados; uma leitura em cache abastece ambas as curvas. Falha de
leitura nao substitui silenciosamente a curva pelo relatorio misto.

Ancoras das duas bordas passam a aparecer tracejadas ate a confirmacao; projecoes
posteriores mantidas. Nao muda geometria operacional nem criterio de modo.
Somente ouro e referencia M29/M7; Bitcoin continua descritivo. Testes: 98 passaram,
incluindo isolamento por ativo, equivalencia com modo, schema e chaves unicas.
Selecao, Real, agenda, lotes, fontes e ordens preservados. Nenhum trade manual.

## 2026-09-18 - Canal por pivos operacional somente no M7 do M29

Usuario autorizou substituir o gatilho G/P por canal paralelo causal: dois
encerramentos consecutivos abaixo do piso ativam ESPELHADO, dois acima do teto
ativam NORMAL. Referencia M23 S7 liquidada, isolada por conta e ativo. Dois topos
e dois fundos confirmados formam o canal; todo encerramento pode romper, mesmo
sem novo pivo ou com resultado zero. Canal congelado durante a confirmacao;
geometria identica nao apaga contagem. Ausencia de estrutura/historico bloqueia
novo plano. Detalhes em docs/architecture/M29_M7_PIVOT_CHANNEL.md.

Fontes atuais, lotes, RR, sincronizacao, posicoes e selecao somente M23 preservados.
Real segue DISABLED. Painel mostra por padrao pivos para M23/M7, historico inteiro,
com controles apenas visuais. Dados/recortes visuais nao comandam o modo.

Validacao: 260 testes e 26 subtestes passaram; 47 prefixos dos 46 encerramentos
conciliados sem uso de futuro. Leitura atual Demo confirmada: modo NORMAL apos
os encerramentos 45 e 46 acima do teto. Estado recalculado pelo servico normal,
sem envio de ordens. Launcher oficial recarregou painel, health local OK e publico
HTTP 200; novo ciclo segue WEEKLY_WINDOW_CLOSED. Nenhum fechamento manual.
Tela autenticada nao inspecionada; schema do grafico validado em teste.
Proximo acompanhamento: observar ciclo automatico apos domingo 18:05 BRT sem
forcar entradas; criterio exploratorio nao comprova rentabilidade.

## 2026-09-18 - Historico completo de canais e resultados restaurado

Usuario rejeitou o recorte recente. Vista de canais agora inicia com todo o periodo selecionado, todos os canais e todos os pontos; tabela das tres ultimas operacoes permanece apenas como detalhe. Remocao das faixas/pivos sobrepostos preservada. Novo estado do controle evita herdar opcao antiga de recorte. 20 testes passaram. Nenhuma alteracao de calculo ou execucao.

## 2026-09-18 - Limpeza visual dos canais

Pedido do usuario: reduzir poluicao do estudo. Padrao mostra canal atual e anterior (anterior com menor opacidade), ultimas duas janelas de resultados e tres pontos recentes destacados. Removidas sobreposicoes de pivos/faixas estruturais apenas nesta vista; historico completo continua opcional. Calculo causal, confirmacoes e operacao do robo inalterados. 85 testes passaram, incluindo limites de linhas e schema Vega-Lite. Previa com dados do M7 inspecionada.

## 2026-09-18 - Canais paralelos descritivos no grafico M23/M7

Sobreposicao visual habilitada por padrao apenas no historico M23 fonte M7; opcional nos demais graficos. Janelas 8/12/18 e confirmacao 2/3, padrao 12/3. Canais robustos paralelos congelados ate rompimento confirmado, com tabela dos tres ultimos encerramentos e respectivas bordas anteriores. Modulo descritivo sem conexao com execucao, sem mudar modos, fontes, lotes, contas ou agenda. Validacao: 84 testes passaram, incluindo prefixos causais, paralelismo, terceira confirmacao, tabela e schema Vega-Lite. Painel recarregado pelo launcher oficial, health local/publico OK; ciclo 2026-09-18T23:29:47Z permanece WEEKLY_WINDOW_CLOSED. Validacao automatizada do grafico concluida; sessao autenticada do navegador nao inspecionada.

## 2026-09-18 - Restauracao das fontes historicas M29

Usuario autorizou restaurar fontes dos dias 15/16: M1, M2, M5, M7, M8, M10, M18 e M20. Whitelist, avaliacao, copia M29 para M23 e painel restaurados. M21/M22 continuam excluidos; somente M7 alterna NORMAL/ESPELHADO e mantem sincronizacao e duas regras simetricas confirmadas. Demais fontes normais com contratos e filtros existentes, sem canal financeiro novo. Selecao operacional somente M23 preservada; envio proprio M29 e Real nao ativados. Agenda semanal preservada. Validacao: 305 testes e 16 subtestes passaram; nenhuma ordem manual ou fechamento forcado. Painel recarregado pelo launcher oficial, novo PID 25904; health local e publico OK. Agenda permanece WEEKLY_WINDOW_CLOSED, retorno domingo 18:05 BRT; selecao salva inalterada.

## 2026-09-17 - Duas regras simetricas M7 confirmadas

Usuario confirmou: no ouro, NORMAL somente por GGGG ou GPGPGG; ESPELHADO por PPPP ou PGPGPP. Removidas transicoes PGPGGG e GPGPPP. Referencia continua nos encerramentos liquidos M23/M7; sincronizacao, lotes, selecoes e posicoes preservados. Validacao: 132 testes passaram, incluindo rejeicao das sequencias removidas e isolamento dos resultados M29. Painel recarregado pelo launcher oficial; health local/publico OK e novo ciclo online em 2026-09-18T01:02:27Z, aguardando plano. Estado observado permanece ESPELHADO. Nenhuma ordem manual ou fechamento forcado.

## 2026-09-17 - Ampliacao cancelada: somente M7 normal e espelhado

Por nova solicitacao explicita do usuario, a ampliacao para M1/M2/M8/M10/M18/M20 foi retirada. Restaurados whitelist M7, fluxo anterior de execucao, volume por modo e detector M7. Sincronizacao existente M23/M29 preservada, assim como fontes proprias M23, historico e selecao salva (somente M23). Removidos modulo e testes exclusivos do canal financeiro. Rotulos de origem e modo solicitados separadamente foram mantidos. Nao foram enviadas ordens nem fechadas posicoes. Validacao de regressao em andamento. Registros abaixo descrevem a implementacao cancelada, nao a configuracao efetiva.

## 2026-09-17 - Espelhos financeiros condicionais em implementacao (cancelado)

Usuario autorizou M1, M2, M8, M10, M18 e M20: curva liquida de cada fonte dentro do M23, canal descendente confirmado, espelho apos ordem original executada, volume dobrado e RR 1:1. M7 permanece com sua regra existente. Codigo novo usa pivos causais, sensibilidade fixa 1.0 e historico broker disponivel desde julho/2026; recortes visuais nao alteram o gate. Rompimento superior, canal ausente, conta divergente, historico indisponivel ou dupla ocupada bloqueiam a nova perna. Provider revalida a curva e o original imediatamente antes do envio. M23 normal nao depende do sucesso do espelho.

NAO CARREGADO: selecao salva contem apenas M23; destino das novas pernas (proprias M29 ou copias dentro do M23) foi perguntado ao usuario antes de ativar, para nao ligar involuntariamente ordens proprias M7. Implementacao atual trata confirmacoes imediatas de mercado; preenchimentos posteriores de pendencias ainda precisam de acompanhamento antes da conclusao. Primeira bateria: 137 testes passaram; validacao ampliada em andamento. Nenhuma ordem ou encerramento forçado nesta implementacao.

## 2026-09-17 - M29 restrito a fonte M7

Novas entradas M29 aceitam somente M7, nos modos NORMAL e ESPELHADO. A lista de avaliacao e a whitelist compartilhada pelos preflights de mercado/pendentes foram restringidas. A copia de sinais M29 para M23 tambem recusa origens diferentes de M7; fontes proprias M23 permanecem inalteradas. Historico legado, posicoes existentes, regras de modo, lotes e sincronizacao foram preservados. Painel informa apenas M7.

Validacao: 129 testes passaram em integracao M29, cesta, sequencia M7, copia M23, retry, sincronizacao, identidade de saida e rotulo de modo. Nenhuma ordem foi enviada pelos testes. Proximo controle: observar o primeiro ciclo apos carregar o aplicativo; nao forcar entradas nem encerramentos.

## 2026-09-13 - Entradas teoricas M29/M28 e relatorio M29

Secoes M29 e M28 adicionadas imediatamente apos M27 na aba MT5. M29 exibe ultima avaliacao real da rota em cache, incluindo bloqueios, modo e horario; nao reexecuta sinal na tela. M28 reutiliza reconhecimento ao vivo existente. Grafico individual M29 ja presente; corrigido filtro do grafico principal para reconhecer M29 sem agregar outros modelos. Testes M29/ciclo: 26 passaram.

## 2026-09-13 - Correcao da selecao M29 no ciclo automatico

O carregamento persistido do ciclo automatico agora inclui M29 junto ao M23. Antes descartava M29 mesmo selecionado; sincronizacao da interface ja o incluia. Preservadas selecoes, fontes, regras M7/espelhamento, risco e contas. Regressao isolada reproduziu falha anterior e validou M23+M29, M29 sozinho e M23 sozinho (4 testes). Nenhuma ordem de teste enviada.

## 2026-09-13 - Retirada da excecao BTCUSD

Por solicitacao do usuario, todos os ativos voltam a mesma janela:
domingo 18:05 ate sexta 17:30 BRT, incluindo BTCUSD. Removidos ciclo e
roteamento BTC_ONLY da Demo e Real; fechamento semanal nao exclui Bitcoin.
Contas, modelos e stops preservados. 16 testes de agenda e transporte passaram.
O painel estava sem processo; foi restaurado pelo launcher oficial e health
local/publico responderam OK. Sem envio de ordem de teste.

## 2026-09-12 - Agenda semanal com excecao BTCUSD

BTCUSD permanece elegivel no fim de semana nas contas ja autorizadas.
Outros ativos encerram sexta 17:30 BRT e retomam domingo 18:05 BRT.
Fechamento agendado exclui BTCUSD e cancela pendencias nao BTC do proprio robo.
Entrada revalidada por ativo no provider; saidas e SL/TP continuam permitidos.
Selecao de modelos, lotes e autorizacao Real preservadas. Usuario autorizou
concluir e ativar a excecao apos o bloqueio inicial da revisao de seguranca.
168 testes passaram com MT5 simulado; testes de agenda usam limites reais
de sexta/domingo e regressao geral isola o relogio via agenda desativada apenas
no processo de testes. Implantado pelo launcher oficial, health local/publico OK.
Painel confirmou monitoramento ativo; estado online BTCUSD e agenda BTC_ONLY.
Selecao M23/M28/M29 preservada por hash. Real permanece desautorizada.
Primeiro ciclo teve falha transitoria na sonda de posicoes; recuperou sem
fallback nem retirada de protecoes. Verificacao 20:16 BRT: online BTCUSD,
AGUARDANDO_PLANO / SEM_GATILHO_VALIDO. Agenda BTC_ONLY, nenhuma posicao
ou pendencia nao BTC restante. Nao foi forcada ordem para testar.

## 2026-09-12 - M29 independente, publicado e desmarcado

M29 recebe diretamente M1/M2/M5/M7/M8/M10/M18/M20, sem depender
do envio M23. Identidade, comentarios, deduplicacao, cesta e sequencia proprios.
M7 alterna normal/espelhado por ativo e conta: quatro resultados alternados
seguidos de duas perdas espelham; nova alternancia seguida de dois ganhos
normaliza. Bootstrap M23/fonte M7 somente na inicializacao; depois resultados
liquidos encerrados M29. SL original vira TP, stop simetrico e RR geometrico 1:1.
150 testes do recorte passaram. App publicado, health ok e selecao M23/M28
preservada. M29 desmarcado; Real nao autorizada nem ligada nesta entrega.
Ver docs/architecture/OPERATIONAL_MODEL_29_ACCUMULATOR.md. Proximo passo:
conferencia autenticada do painel e observacao controlada, sem assumir melhora
financeira comprovada e sem habilitar o M29 automaticamente.

## 2026-09-11 - M28 original com sincronizacao de candles

Usuario determinou preservar o setup original minerado e retirar o filtro contextual das 66 operacoes. Overlay realizado desativado para todos os registros, sem reaprender, alterar contratos minerados ou substituir por whitelist. Sincronizacao de dados mantida por solicitacao: leitura MT5 confirmada em ate 60s, sem cache somente restaurado, registro aquecido com horario/OHLC iguais a ultima M5 fechada. Rechecagem antes do executor impede plano envelhecido ou contexto/ocorrencia substituidos. Fontes M23 e suas regras permanecem preservadas. Ver docs/research/M28_ORIGINAL_CONTEXT_SYNC_2026-09-11.md.

## 2026-09-11 - Bloco separado de filtros adicionais M23

Usuario autorizou bloquear novas entradas nos tres contextos exatos de compra M23 originada no M7 no ouro. Catalogo independente em config/m23_additional_filters.json, modo BLOCK explicito, sem reaprender ou sobrescrever o filtro contextual original. Correspondencia exige contexto VALID e todos os sete campos iguais. Bloco de consulta apos Replay dos Sinais M23. Evidencias financeiras ficam apenas no runtime local, fora do Git. Ver docs/research/M23_ADDITIONAL_FILTERS_2026-09-11.md.

## 2026-09-11 - Sincronizacao do contexto M23

Correcao autorizada: contexto independente de contratos M28, candle fechado alinhado ao sinal, 200 fechadas deterministicas e leitura MT5 recente. Contexto ausente/invalido aguarda dados; NO_EVIDENCE com contexto valido preserva entrada. Regras congeladas e posicoes abertas preservadas. Identificadores de regra/contexto e fotografia auditavel separados. Ver docs/research/M23_CONTEXT_SYNC_2026-09-11.md. Replay financeiro integral nao certificado.


## 2026-09-10 - Reversao completa da trava nova de repeticao

A pedido do usuario, removida a chamada da trava nova do executor. M7 direto e M23 fonte M7 voltam ao comportamento anterior a essa trava. Filtro contextual anterior e atualizacao do relatorio preservados.

## 2026-09-10 - Reversao da trava de repeticao no M23

A pedido do usuario, retirada a rota M23 fonte M7 da trava de repeticao. M23 retorna ao comportamento anterior a essa trava; filtro contextual original preservado. M7 direto e atualizacao do relatorio mantidos. 11 testes focados aprovados para a reversao.

## 2026-09-10 - Protecao de repeticao M7 XAU e atualizacao de relatorios

Autorizado pelo usuario: M7 direto e M23 fonte M7 em XAUUSD bloqueiam repeticao na mesma direcao ate 60s da saida completa, sem novo M5 fechado. Rotas separadas por comentario/magic; falha de leitura suspende entrada abrangida. Demais fontes, BTC e saidas preservados. Relatorio mantem intervalo de 30s, independente da janela de entrada. Estudo retrospectivo nao equivale a replay de carteira. 11 testes focados aprovados antes da instalacao.

## 2026-09-08 - M28 contextual substitui lista de dois padroes

Metodo de contexto e evidencia do M23 aplicado ao M28: 66 contextos reconstruidos de candles atuais, 630 regras sem evidencia minima e zero bloqueios. Retirada a lista exclusiva BTCUSD/USDJPY. Sem evidencia preserva entrada; recalculo sob demanda. M23, lotes e saidas preservados. 37 testes aprovados. Ver docs/research/M28_CONTEXTUAL_FILTER_2026-09-08.md.


## 2026-09-08 - Filtro M28 por resultado executado Demo

Filtro de novas entradas implementado com lista de dois padroes versionados positivos nos dois recortes observados. Evidencia exploratoria pequena, sem promessa de lucro. M23 e gestao de posicoes preservados. 33 testes aprovados no codigo instalado; painel recarregado e health OK. Verificado em 2026-09-08T00:28:14.194137-03:00. Ver docs/research/M28_REALIZED_ENTRY_FILTER_2026-09-07.md.

# Project Status

## 2026-09-06 - Estado por conta no painel

Demo e Real identificadas separadamente, com solicitacao de entrada distinta
de conexao/permissoes confirmadas e descarte visual de heartbeat antigo.
Guardiao de RAM alinhado ao terminal portable Demo no restart. Estrategias e
autorizacoes preservadas. Ver docs/MT5_SIMULTANEO.md.

## 2026-09-05 - Marco de observacao operacional

Prioridade solicitada: documentar a evolucao desde 01/09/2026 00:00 BRT,
sem alterar o setup. Baseline Demo inicial separa novas entradas dos
encerramentos herdados; resultado principal +USD 1529.31 e secundario
+USD 2415.86. Referencia: docs/research/EVOLUCAO_OPERACIONAL_MARCO_2026-09-01.md.
Revisoes propostas em 4, 8 e 12 semanas e 6 meses; sem consolidacao automatica,
sem agendamento, alteracao de runtime, ativacao de conta ou envio de ordens.

## 2026-09-04 - Demo e Real simultaneos

Demo retomada como ambiente principal do painel, terminal e identidade fixados.
Real adicional com processo isolado, autorizacao por checkbox, estado proprio
e revogacao de novos envios no transporte. Reinicio e interface verificados.
Terminais conectados: Demo 61551556 e Real 51517136. Real desmarcada e sem
Algotrading. Testes sem operacoes reais; ver docs/MT5_SIMULTANEO.md.

## 2026-09-04 - Checagem de permissoes MT5

Transporte passa a bloquear qualquer envio sem Algotrading, API Python e
permissoes da conta comprovadamente liberados. Erros exibem esses status.
Validado com fakes; carregamento no processo do painel aguarda reinicio.

## 2026-09-04 - Preparacao Real/Demo

Executor compartilhado com selecao explicita de conta Real e verificacao
de login/servidor. Estrategias e lotes preservados. Limite diario padrao 0,
conforme solicitacao; SL por entrada mantido. Ativacao Real e homologacao
na corretora pendentes; nenhuma ordem Real enviada nesta implementacao.
Ver docs/MT5_REAL_DEMO_EXECUTION.md.

Status: pronto para fluxo de inbox.

`M24_CONTRACT=M24_SETUP_V19_20260823; SHA256=d918353322bc17fd17e1c7d0ba47272cf19431ef2c60d9cd1686829f2802c05f`

`M25_CONTRACT=M25_XAU_SOURCES_V6_20260820; FINGERPRINT=d0d758099058ffde`

`M26_CONTRACT=M26_SMART_MONEY_V3_20260825; FINGERPRINT=4df7d17616d6a82e`

## Contrato vigente M26 - 2026-08-25

- rota independente em `XAUUSD/M1`, sem substituir o M25;
- 200 candles fechados mais candle atual somente informativo;
- confluencia obrigatoria de estrutura, sweep, BOS/deslocamento, FVG, OB e reteste;
- entrada a mercado, SL estrutural, RR minimo 2 e lote Demo `0,01`;
- integrado ao ciclo compartilhado e ainda nao ativado automaticamente.

## Contrato vigente M24 V18 - 2026-08-20

- M24 atual e uma unica rota autonoma `M24_PROPRIO` em XAUUSD/M5;
- entrada inicial: novo cruzamento do preco/SMA20 e novo cruzamento RSI14/50 na
  mesma direcao; podem ocorrer em M5 diferentes, mas ambos permanecem validos;
- distancia atual `abs(SMA20-SMA50)/ATR14` e somente informativa e nao bloqueia;
- SL inicial: extremidade da vela que cruzou a SMA20 afastada `0,01`; depois so avanca
  quando houver rompimento do topo/fundo e novo fundo/topo de protecao;
- TP inicial: Fibonacci 100% da ultima perna estrutural completa anterior,
  projetado a partir da entrada e congelado como preco absoluto; RSI extremo
  remove o TP e o retorno confirma Full Exit;
- reentrada: ordem Stop, SL no micro-pivo 1+1 mais um pip e TP obrigatorio no
  fechamento do micro-pivo 1+1 lucrativo mais recente;
- a primeira reentrada valida apos Full Exit RSI 70/30 nao e descartada;
- `CONTINUATION`: ordem Stop um pip alem do TP da `INITIAL`, `0,10` lote, sem TP,
  SL e trailing no extremo do ultimo M5 fechado; Full Exit ao atingir RSI70/30;
- `LATERALIZATION`: uma REENTRY aberta que falha o TP Fibonacci e retorna ao
  range reposiciona SL/TP do mesmo ticket em RR `3:1`; nao abre nova ordem,
  nao aumenta o lote e nunca afrouxa o SL;
- `INITIAL` espera duas velas M5 fechadas antes de liberar Full Exit RSI50;
  as demais regras RSI permanecem e nenhuma posicao sai por inversao SMA20/SMA50;
- interface, motor, Trade Plan, runtime e documentos ativos agora compartilham
  contrato versionado e fingerprint; teste impede drift documental;
- corrigida a identidade temporal de registros MT5 para nunca persistir o
  `memoryview` de `.data` como horario do candle;
- secoes M24 datadas antes de 2026-08-19 abaixo sao historico de execucao e nao
  substituem este contrato vigente.

## Sincronizacao do ciclo M25 V1 - 2026-08-18 (historico, substituido pelo V2)

- o ciclo de fundo passa a restaurar M25 a partir da mesma lista canonica usada
  pelo seletor e pela interface;
- corrigido o filtro legado que aceitava somente fontes do M23 e fazia M25
  aparecer selecionado sem receber a reconciliacao das 201 velas M5;
- setup, entrada, reentrada, SL, TP, cesta e posicoes existentes nao foram
  alterados;
- a tabela publica usa o snapshot M25 ja reconciliado pelo ciclo de fundo, sem
  criar leitura MT5 adicional na interface;
- regressao direcionada, 53 testes de M5/M24/M25 e gate critico com 197 testes
  aprovados sem envio MT5.

## Estado Operacional M25 - 2026-08-19

- Contrato V2: M25 opera exclusivamente XAUUSD/M5.
- Fontes exatas: M8, M10, M18, M19, M20, M21 e M22.
- O agregador copia entrada, SL, TP, ordem e candle sem recalcular o setup.
- Identidade, duplicidade e papeis `INITIAL/REENTRY` sao isolados por fonte.
- Robo Demo e provider rejeitam M25 fora de XAUUSD.
- A saida tecnica permanece a da fonte; a cesta M25 adiciona Full Exit em
  `+US$1.000` liquidos somente para suas posicoes.
- O estado de entrada/reentrada V1 nao e lido pelo contrato V2; arquivos e
  historico antigos permanecem preservados.
- M25 e selecionavel como cesta exclusiva e nao foi ativado automaticamente.
- Validacao: 378 testes + 45 subtestes focados e 203 testes criticos aprovados;
  auditoria arquitetural `OK`, sem conexao ou envio MT5.

## Correcao do seletor MT5 - 2026-08-17

- eliminada a colisao entre a chave Streamlit de `Todos` e a de um modelo novo
  ainda nao reconhecido por um modulo antigo mantido em memoria;
- o botao `Aplicar modelos` agora persiste a selecao em callback antes do
  rerender do fragmento, atualizando imediatamente resumo e textos M23/M24;
- chaves desconhecidas agora recebem sufixo derivado do ID canonico, sem usar
  o sufixo reservado `todos`;
- teste de interface comprovou a troca M23 -> M24 na mesma tela e restaurou o
  estado operacional anterior ao final da validacao.

## Estado Operacional M24 - 2026-08-17 (historico substituido)

- M24 criado como cesta XAUUSD/M5 independente do M23.
- Fontes fixas: M8, M10 e M18-M22.
- As fontes identificam apenas a origem; M24 nao herda ADX, inclinacao ou filtros
  proprios delas. A distancia SMA20/SMA50 nao bloqueia o M24.
- Entrada inicial: preco cruza e permanece alem da SMA20; RSI14 cruza e
  permanece alem de 50. Os dois cruzamentos podem ocorrer em M5 diferentes.
- Reentrada unica e pendente: fechamento e RSI no lado permitido geram
  BUY_STOP/SELL_STOP na maxima/minima do ultimo M5, sem exigir novo cruzamento.
- A entrada inicial M24 nao usa TP individual; a reentrada usa o fechamento do
  ultimo topo/fundo principal 2+2 confirmado. O alvo coletivo permanece em
  +US$1.000 liquidos.
- SL da reentrada usa o micro pivo 1+1 anterior mais proximo nos ultimos cinco M5;
  o Position Manager so aceita um novo micro pivo quando ele melhora a protecao.
- Apos Full Exit RSI 70/30, a primeira oportunidade de reentrada do mesmo lado
  e ignorada; repeticoes na mesma vela nao contam e somente a segunda
  oportunidade em nova vela M5 pode ser liberada, tanto no BUY quanto no SELL.
- Modelo foi selecionado manualmente como unico modo operacional em 2026-08-17,
  por solicitacao do usuario; isso nao comprova robo armado nem ordem enviada.
- Relatorio `Em negociacao` identifica cada plano M24 como `PRINCIPAL` ou
  `REENTRADA` antes da coluna `Alvo`, usando o papel persistido no snapshot.
- Fonte canonica: `docs/architecture/OPERATIONAL_MODEL_24_XAU_RSI50_BASKET.md`.
- Contrato V9: INITIAL nasce no pivo estrutural 2+2, move o SL somente apos
  rompimento estrutural e espera dois M5 fechados antes de liberar Full Exit RSI50.
- Escrita atomica dos estados M24 possui repeticao curta contra bloqueios
  transitorios do Windows/OneDrive, sem alterar nem apagar o runtime local.
- O ciclo Demo nao exige plano-base H1 valido antes de avaliar o plano proprio
  XAUUSD/M5 do M24.
- O avaliador le diretamente o objeto `Candle` canonico do cache M5 e nao perde
  OHLC/horario por diferenca entre nomes de campos.
- Trava de escopo impede materializacao do M24 sobre qualquer linha diferente
  de XAUUSD; primeiro ciclo corrigido aceitou M24/M8 BUY no XAUUSD Demo.
- Correcao de 2026-08-17 removeu da posicao principal a saida por inversao
  SMA20/50, coerente com a entrada que tambem nao depende da SMA50. Full Exit
  RSI 70/30, SL e cesta permanecem; reentradas preservam inversao SMA e RSI50.
- Reentrada M24/M8 fica pendente no book como BUY_STOP/SELL_STOP, com SL na
  vela de referencia e TP no fechamento do topo/fundo principal confirmado.

## Estado Atual

- Estrutura `codex/` criada.
- Estrutura `governance/execution/` criada.
- Templates de missao e relatorio criados.
- Guardrails read-only documentados.
- `MISSION_INDEX.md` controla historico resumido das missoes.
- Camada 1 de governanca operacional criada em `docs/`.
- Nenhuma funcionalidade de produto foi criada por esta infraestrutura.

## Estado Operacional M11-M20 - 2026-08-01

- M11-M20 materializam, uma por vez, as dez Alphas oficiais ainda sem modelo.
- Todos cobrem oito pares e permanecem restritos ao MT5 Demo.
- Entradas usam candle fechado; SL/TP sao fixos; Position Manager somente
  observa e audita essas posicoes.
- Indicadores sao calculados uma vez por par/timeframe/candle e compartilhados.
- O seletor `TODOS_MODELOS` inclui M1-M20 e o provider aceita no maximo uma
  posicao por modelo/par, vinte por par no total.
- Teste sintetico do ciclo M11-M20 ficou abaixo do gate de tres segundos.
- Fonte canonica: `docs/architecture/OPERATIONAL_MODELS_M11_M20.md`.

## Correcao Operacional M2-M4 - 2026-07-26

- MT5 e os timeframes H1/M30/H4 foram auditados online para os oito pares.
- A janela de entrada dos modelos promovidos M2-M4 passou a usar o relogio do
  servidor MT5, evitando bloqueio incorreto de barras marcadas como futuras
  pelo deslocamento entre Pepperstone e UTC da maquina.
- O ciclo permanece em 10 segundos e a janela executavel em 120 segundos.
- Nenhum indicador, setup, SL/TP ou candle historico foi alterado.

## Estado Operacional M7 - 2026-07-24

- M6 permanece baseline fixo `ALPHA001/BETA001`.
- M7 esta implementado como modelo independente
  `MODELO_7_TREND_MOMENTUM_DYNAMIC`.
- M7 usa `BETA007_DYNAMIC_PROTECT_ONLY_V1`: protege somente depois de 1,50R e
  nunca executa fechamento antecipado.
- Seletor, MT5 Forex, Robo Demo, provider, Position Manager, Relatorio,
  historico e graficos reconhecem M7.
- Limite vigente: uma posicao por modelo e sete posicoes por par.
- Execucao continua exclusiva em MT5 Demo; conta real permanece bloqueada.

## Camada 1 - Mapa Operacional

Arquivos de referencia:

- `docs/SYSTEM_FLOW.md`
- `docs/APP_TABS_FLOW.md`
- `docs/ALPHA_TRACEABILITY.md`
- `docs/SETUP_LOGIC_TRACEABILITY.md`
- `docs/OPERATIONAL_GUARDRAILS.md`
- `docs/CHANGE_PROTOCOL.md`

Esses documentos devem ser usados pelo GPT/Codex antes de propor melhorias em
Forex MT5, Lab, Relatorio, MT5 Visual, Alphas ou setups.

## Camada 2 - Template GPT para Inbox

Arquivos de referencia:

- `codex/templates/GPT_IMPROVEMENT_MISSION_TEMPLATE.md`
- `codex/templates/README_GPT_MISSIONS.md`
- `docs/GPT_MISSION_AUTHORING_GUIDE.md`

Toda melhoria desenhada no GPT deve usar esse template para gerar pacote de
missao completo em `codex/inbox`.

## Camada 3 - Rastreabilidade Alpha/Setup/Contratos

Arquivos de referencia:

- `governance/traceability/TRACEABILITY_INDEX.md`
- `governance/traceability/ALPHA_INDEX.md`
- `governance/traceability/SETUP_INDEX.md`
- `governance/traceability/LAB_TO_FOREX_CONTRACT.md`
- `governance/traceability/FOREX_TO_MT5_CONTRACT.md`
- `governance/traceability/REPORT_CONTRACT.md`
- `governance/traceability/TRACEABILITY_MATRIX.md`

Toda mudanca em Alpha, setup, entrada, saida, timeframe, visual MT5 ou relatorio
deve atualizar a rastreabilidade correspondente.

## Camada 4 - Auditoria de Stops Moveis

Arquivos de referencia:

- `docs/MOBILE_STOPS_ANALYSIS.md`
- `governance/traceability/STOP_LOGIC_TRACEABILITY.md`

A auditoria confirma que o Lab avalia 9 politicas canonicas de stop management,
mas a gestao demo MT5 aplica ajuste dinamico de SL/TP apenas para `BREAK_EVEN` e
`ATR_TRAILING_STOP`. Qualquer ampliacao de saida dinamica deve ser feita por
missao especifica e com testes do contrato Lab -> Forex -> MT5 -> Relatorio.

## Camada 5 - Desenho de Saida Dinamica

Arquivos de referencia:

- `docs/DYNAMIC_EXIT_DESIGN.md`
- `governance/traceability/DYNAMIC_EXIT_TRACEABILITY.md`

O desenho define que a saida dinamica deve nascer como contrato read-only antes
de qualquer acao real no MT5 demo. O Lab continua decidindo a politica base, o
Forex transporta e observa contexto leve, o MT5 consome plano e o Relatorio
audita. A proxima etapa segura e implementar apenas campos read-only.

## Camada 6 - Contrato Read-only de Saida Dinamica

Arquivos de referencia:

- `docs/DYNAMIC_EXIT_READ_ONLY_CONTRACT.md`
- `governance/traceability/DYNAMIC_EXIT_CONTRACT_TRACEABILITY.md`

O contrato `dynamic_exit_*` foi implementado como camada read-only em contratos,
view models, JSON visual MT5 e auditoria. A execucao demo permanece
desabilitada para estes campos com `dynamic_exit_allowed_to_execute_demo=false`.

## Observacao Operacional

O app local pode acessar recursos locais e MT5 da maquina. O app em Codespaces
serve para desenvolvimento, testes e revisao, mas nao substitui o MT5 local.

## Quality Gate Inicial

- `python scripts/run_critical_ci.py`: aprovado em 2026-07-06.
- `python scripts/architecture_health.py`: BOM em 2026-07-06.
- `python scripts/architecture_audit.py`: OK em 2026-07-06.
- `python scripts/run_static_analysis.py`: OK_WITH_WARNINGS em 2026-07-06
  porque `pyflakes` opcional nao esta instalado.
- Gates de arquitetura adicionais devem ser executados por missao quando
  aplicaveis e registrados no relatorio.
## 2026-09-14 - Sincronizacao M7 ouro M23/M29

Por autorizacao do usuario, novas entradas M7/XAU do M29 exigem confirmacao
M23 no mesmo ciclo, candle e plano fonte. Fonte calculada uma vez para ambas
as rotas. Normal/espelhado preservados; em espelhado o TP confere com SL M23.
Somente uma tentativa por confirmacao; ticket M23 registrado no plano M29.
Com ambos selecionados, nova dupla aguarda ambas as posicoes M7/XAU encerrarem
e plano correspondente M29 pronto. Sem reentrada isolada, catch-up ou fechamento
forcado. Outras fontes e BTC permanecem independentes. Contas e selecao intactas.
67 testes do recorte passaram, incluindo fluxo completo com executor simulado.
A suite geral demo apresentou 9 falhas; uma foi reproduzida em memoria sem
as alteracoes de sincronizacao. Nao se declara a suite geral integralmente verde.
Ordens separadas nao sao atomicas: M29 ainda pode ser rejeitado apos aceite M23.
SL/TP e saidas nao foram sincronizados; RR1 nao garante resultados inversos.


## 15/09/2026 — Retomada da copia M29/M7 no M23

Confirmado pelo usuario: manter original aceita e repetir somente a rejeitada enquanto o mesmo plano for valido. Implementacao e limites em docs/M23_M29_REJECTED_LEG_RETRY.md. 198 testes e 2 subtestes passaram; falhas legadas M24/M25 reproduzidas sem a mudanca. Sem ordens de teste, commit ou push nesta etapa.


## 15/09/2026 — Gatilho adicional de quatro perdas M7 ouro
Usuario autorizou NORMAL -> ESPELHADO apos quatro perdas consecutivas encerradas do M7 original no M23/XAUUSD. Gatilho anterior de quatro alternados + PP preservado; retorno por quatro alternados + GG preservado. Perdas no modo ESPELHADO nao alternam modo repetidamente. Empate/ganho interrompe a sequencia; tickets duplicados nao contam. Aplicacao apenas ouro, sem mudar lotes, sincronizacao, stops ou posicoes abertas.
99 testes passaram. Historico nativo consultado: 42 encerramentos originais, maior sequencia de 9 perdas, liquido -1968.46. Reconstituicao do detector antigo e novo mudou para ESPELHADO na operacao 32 nos dois casos; nao e simulacao de lucro nem prova de execucao historica do espelho. Alteracao local, sem commit/push nesta etapa.


### Correcao imediata: apenas pesquisa, sem novo gatilho
O usuario esclareceu que estava apenas pesquisando. Removido imediatamente o gatilho de quatro perdas que havia sido interpretado como pedido de instalacao, restaurando o detector e sua chamada anteriores. O registro anterior de aplicacao esta supersedido por esta correcao. Pesquisa historica preservada separadamente. Sem alteracao solicitada no modo, lotes, sincronizacao ou posicoes.


## 15/09/2026 — Autorizacao explicita dos gatilhos adicionais simetricos
Apos esclarecer que a fala anterior era pesquisa, o usuario agora autorizou implementar: quatro perdas consecutivas -> ESPELHADO; quatro ganhos consecutivos -> NORMAL. Preservadas as alternativas existentes de quatro resultados alternados seguidos de PP/GG. Referencia exclusiva M7 original do M23/XAUUSD; resultados M29 e copias M23/S29 nao decidem modo. Ganho/perda oposto e empate interrompem a serie; fechamento duplicado nao conta. Mesmo modo nao dispara alternancia repetida. Ao mudar, janela reinicia como antes. Outros ativos mantem criterio anterior. Lotes e sincronizacao preservados.
106 testes passaram, incluindo todos os gatilhos, series interrompidas, nao alternancia repetitiva, execucao da dupla e retomada. Instalacao local autorizada; sem commit/push nesta etapa.


## 16/09/2026 — Encerramentos recentes omitidos na sequencia
Diagnostico: consulta m29_sequence terminava em now UTC, mas timestamps recentes do terminal estavam adiantados; encerramento real da copia M29/M7 no M23 com lote 0.2 e liquido -470.60 nao era retornado. Consulta limitada ao agora omitia; consulta estendida retornou. Corrigido limite superior para now UTC + 1 dia (somente deals ja existentes no MT5; nenhum resultado sintetico). Consumidores continuam excluindo posicoes abertas e conciliando volumes. Nova leitura nativa confirmou sequencia combinada PGGGGGP, incluindo a perda. Historico proprio M29 permanece independente. 61 testes passaram, incluindo regressao com fechamento em horario de servidor adiantado. Sem alteracao das regras, lotes ou ordens; sem commit/push nesta etapa.


## 16/09/2026 — Tabela de letras por fonte do M23 no Relatorio
Conforme esclarecimento do usuario, tabela somente com fonte do sinal e sequencia das ultimas sete operacoes encerradas em G/P (E para empate), abaixo da selecao dos modelos e antes do grafico principal. Sem valores financeiros nem contagens. Recorte usa data/hora inicial do relatorio; ordenacao cronologica existente, MT5 confirmado, deduplicacao de ticket. Letra considera lucro + comissao + swap + taxas. M29 apenas operacoes incorporadas ao M23; fontes desconhecidas identificadas sem adivinhar. Dois testes passaram cobrindo custos, duplicacao, posicoes abertas, corte em sete e fontes separadas. Sintaxe do painel validada. Sem alteracao de estrategia ou ordens; sem commit/push nesta etapa.


## 2026-09-29 — M30 independente por canal original M23/M7

Autorizado pelo usuario e implementado conforme docs/architecture/M30_INDEPENDENT_CHANNEL.md.
M30 recebe fontes originais independentemente do aceite M23, sem copiar M29.
Canal usa resultados encerrados originais M7 no M23: Alta abaixo do piso espelha, retorno normaliza; Baixa confirmada espelha.
Rascunho de curva propria M30 cancelado antes de instalar. Históricos legados separados.
209 testes direcionados passaram; nenhuma ordem manual de teste. Consulta nativa confirmou modo NORMAL.
M23/M29 preservados; controles de conta Real desabilitados. Recarga pelo launcher oficial autorizada.


## 2026-09-29 — Comparacao M7/M29/M30 e seletor M30
Relatorio posiciona M29 e M30 imediatamente apos M7/Ouro, antes do Bitcoin, sem duplicar graficos. M30 incluido no filtro de historicos proprios. Formulario Aplicar modelos exibe M30 e controla a mesma autorizacao persistida usada em Aprendizado; Todos preserva a autorizacao individual M30. Usuario esclareceu que deve aparecer marcado: habilitacao restaurada, M23 preservado. Quatro validacoes direcionadas passaram. Suite ampla: 190 passaram e cinco falharam; expectativa da lista atualizada, demais falhas em fixtures/expectativas anteriores (position ausente, BTC M7 legado, lista sem M29, navegacao sem Aprendizado). Sem mudanca de estrategia ou posicoes.


## 2026-09-29 — Refatoracao da integracao das abas
Contrato compartilhado de apresentacao, catalogo e estado do M30; persistencia extraida sem migracao. Sincronizacao evita toggle antigo do Aprendizado sobrescrever escolha do MT5. Historico legado e politica atual identificados. 33 testes passaram. Ver docs/architecture/MODEL_UI_STATE.md. Sem alteracao de regras financeiras ou posicoes.


## 2026-09-30 — Graficos somente das politicas atuais
Relatorio M29 mostra somente M7 espelhado com m29_sequence_mode identificado; canal anterior, normais e gatilho desconhecido ficam fora. M30 mostra somente m30_policy atual. Filtro no snapshot, nunca por data presumida. Registros e execucao intactos. Dez testes passaram; recarga oficial preserva selecao, agenda e online.


## 2026-09-30 — Geral e M7 no mesmo periodo
Conforme esclarecimento final, M29 e M30 exibem Geral e M7 abaixo, ambos com o mesmo corte temporal do Relatorio e sem forcar quantidades iguais. M29 geral inclui demais fontes normais identificadas; M7 permanece espelhado por sequencia identificada. M30 geral contem todas as fontes da politica atual e M7 isola a fonte pelo snapshot. Doze testes passaram e Streamlit AppTest renderizou os quatro graficos sem erro de chaves duplicadas. Historicos e regras operacionais preservados.


## 2026-09-30 — Reforcos por canal da fonte original no M23

Autorizado: M29/M30 seguem a direcao original e suspendem novas entradas somente em canal de baixa confirmado da fonte/ativo no M23. Referencia inclui apenas encerramentos originais conciliados, com custos. Alta, lateral, transicao e formacao nao suspendem; falha de leitura/conta/conciliacao bloqueia. Sensibilidade operacional 1; os controles visuais nao mudam a regra. Planos de politicas antigas nao podem enviar novas ordens.

M23 original mantido com lote padrao 0,10. Pedido de 0,05 foi cancelado antes de implementacao. Ausencia de reforco nao impede o original M23; sincronizacao existente continua para duplas elegiveis. Fontes e ativos vigentes preservados. Defesa financeira vigente de US$200, TP/RSI e demais saidas preservados; sem alteracao ou fechamento de posicoes/pendentes existentes. Nao foram enviadas ordens de teste.

Validacao: suites locais de canais, segregacao por fonte/ativo, rejeicao de referencias antigas/falhas, defesa financeira, sincronizacao e interface. Regras anteriores continuam apenas no historico/estudo; relatorios correntes filtram identificadores da nova politica.


## 2026-09-30 — Resumo textual dos reforcos

Relatorio / Em negociacao: texto identifica fonte, ativo e rota M29/M30 das posicoes confirmadas da politica atual. Pendentes separados de posicoes abertas; ausencia nao significa suspensao pelo canal. Nenhuma mudanca de estrategia. Validacao: 12 testes passaram; recarga oficial com saude ok e selecao, agenda e estado online preservados.


## 2026-10-01 — Lote dos reforcos no ouro

Autorizado lote 0,20 para novas entradas M29/M30 XAUUSD, incluindo M29 executado pelo M23. Original M23 permanece 0,10. Outros ativos e posicoes/pendentes existentes inalterados. Validacao final recusa planos antigos de ouro em 0,10. Defesa financeira vigente precifica o novo lote sem afastar stops menores. 195 testes passaram sem ordens reais; painel recarregado pelo procedimento oficial, saude ok, selecao/agenda/estado online preservados.


## 2026-10-01 — Cancelar reforcos pendentes em baixa e defesa US$400

Autorizado cancelar somente ordens pendentes da politica atual M29/M30 (incluindo copias M29 no M23) quando o canal da fonte/ativo original no M23 confirmar Baixa. Lateral continua permitido. Confirmacao por conta Demo, ticket, magic, comentario, fonte e plano; pendencia relida antes de remover. Ordens originais M23 e posicoes abertas preservadas. Falha de historico nao provoca cancelamento cego.

Novos reforcos XAUUSD 0,20 recebem limite previsto US$400; original M23 0,10 permanece US$200. Stops menores, TP e saidas preservados. Outros ativos seguem limite US$200. Custos/gaps podem superar a perda modelada. Corrigida inicializacao Demo antes da verificacao M30; conexao Demo hedging confirmada sem ordem de teste. 148 testes passaram.


## 2026-10-01 — Fonte e canal na entrada no Relatorio

Posicoes abertas, historico compacto/detalhado e CSV exibem Fonte original e Canal na entrada. Usam exclusivamente metadados do plano persistido, sem recalcular o passado pelo canal atual. Registros antigos sem evidencia mostram Nao registrado. Canal e o estado registrado ao liberar o sinal/ordem, inclusive pendentes; nao garante estado na ativacao posterior. Regras, lotes, stops e posicoes preservados. Validacao: 28 testes passaram sem envio de ordens.


## 2026-10-01 — Canal atual do M23 nas abertas

Adicionada coluna Canal atual da fonte em Em negociacao, por origem/ativo usando os encerramentos originais M23. Consulta Demo com identidade/caminho explicitos e cache de 30 segundos. Canal na entrada continua imutavel e historico nao recebe estado atual retroativo. Falha de leitura mostra Indisponivel. 30 testes passaram; nenhuma regra operacional alterada.


## 2026-10-01 — Seis recortes para reforcos no ouro

Aplicados seis pares fonte/estrutura/faixa de GOLD_REINFORCEMENT_SIX_CONTEXTS.md somente a reforcos XAUUSD M29/M30 e M29 dentro do M23. Mesma matriz no envio e reavaliacao de pendentes identificadas. M23 original, posicoes abertas, outros ativos, lotes e limites financeiros preservados. Planos ouro anteriores sem versao bloqueados. 212 testes passaram; classificacao reproduziu 1809/1809 casos e 307 elegiveis. Politica exploratoria autorizada; sem promessa de resultado futuro.


## 2026-10-02 - Espelho RR1 por faixa nos reforcos do ouro

Autorizado: 18 recortes positivos no replay .20 com defesa USD400 e alvo ajustado para RR1; M10 excluido desta modalidade. Seis recortes normais preservados. Exige original M23 preenchido, mesmo sinal e conta; saida independente por SL/TP nos novos espelhos. M23 original e legados preservados. Relatorio identifica Espelhado. Validacao isolada: 396 testes e sete subtestes. Contrato: docs/architecture/GOLD_MIRROR_REINFORCEMENT_RR1.md. Instalacao concluida e recarga oficial com health OK; selecao, online e agenda byte-identicos, M30 habilitado preservado e Real DISABLED. Bateria instalada: 396 testes e sete subtestes. Nenhuma ordem de teste. Commit/push nao realizados: a base versionada ainda restringe copias a M7 e diverge de alteracoes locais anteriores nos mesmos trechos; patch isolado nao aplica. Alteracoes alheias preservadas, sem commit parcial.

## 2026-10-21 - Recuperacao do historico dos Relatorios
Pedido direto: baixar historico MT5 e atualizar graficos. Chrome confirmou curvas gerais encerrando em 02/10 apesar de positions_get recente. Reconstrucao nativa Demo validada em arquivo separado: 12468 linhas, CONNECTED, 12,49s (sem contar importacao inicial), contra 10984 no snapshot anterior. Launcher limitava consulta externa a 8s. Prazo minimo da auditoria completa ampliado para 45s; snapshot antigo e fonte anterior preservados em TEMP/traderia_audit_oct21. CSV exportado. Snapshot reconstruido substituido atomicamente. Recarga pelo launcher oficial, health OK. Nenhuma ordem manual enviada; configuracoes de estrategia e posicoes nao alteradas. Validacao: 18 testes de historico/auditoria e 1 regressao do timeout passaram. Commit isolado bloqueado por divergencia do trecho em HEAD; nao incluir alteracoes locais alheias. Confirmacao visual final em andamento.

### Complemento - recuperacao de identidade e canais por ativo
- Historico MT5_ONLY preserva comentario de entrada mesmo apos saida SL/TP; recupera executor e fonte, inclusive M30, sem inferir canal/politica historicos ausentes.
- Curvas originais do M23 passaram a incluir os encerramentos recentes. M29/M30 recuperados sem evidencia da politica aparecem em curva separada, explicitamente sem filtro registrado.
- Adicionada consulta de canais por fonte/ativo no Relatorio (27 curvas com encerramentos), mantendo Transicao distinta de lateral confirmado e Formacao.
- Validacao: 22 testes passaram (21 auditoria/identidade/timeout e 1 separacao fonte/ativo); recompilacao Python OK. Recarga oficial realizada; health OK. Hashes de selecoes, robot_online e agenda identicos. Nenhuma ordem de teste.
- CSVs historico e canais em pasta temporaria traderia_audit_oct21. Confirmacao visual final em andamento; nao confundir timestamp de posicoes abertas com ultima data dos encerramentos.

### Complemento - custos reconciliados
- Corrigida dupla contagem de comissao de entrada quando ticket da ordem coincide com position_id: agora cada chave e mesclada uma vez por deal. Teste de regressao incluido.
- M29 nos seis recortes atuais: 64 posicoes, +US$ 783,63 liquidos; conferidos os 64 contra a conciliacao nativa, zero diferencas. Politicas antigas separadas.
- Aba restaura snapshot validado quando ciclo MT5 ocupado, sem marcar leitura nova como concluida. Teste de regressao passou. Total: 24 testes relevantes passaram ao longo da verificacao.
- Historico reimportado apos correcao (12.469 linhas de auditoria); CSV reexportado. Sem mudanca em regras/ordens. Validacao visual final ainda em andamento.

### Verificacao final e risco operacional separado
- Corrigida classificacao de ordens historicas sem deal (ORDEM_HISTORICA), que nao sao encerramentos realizados; ordens pendentes executadas passam a usar BUY/SELL, volume e preco do deal de entrada. Teste especifico passou. Total de 25 testes relevantes aprovados.
- Resultado dos seis recortes M29 conferido contra 64 posicoes nativas: +US$ 783,63; nenhuma diferenca apos custos.
- Pedido adicional: investigar se janela/curva antiga bloqueia entrada. source_channel_gate.reference_state consulta m29_sequence diretamente no MT5, nao snapshot de Relatorios. Ultimo contexto M7 XAUUSD alinhado (200 candles, gap zero).
- RISCO AINDA NAO CORRIGIDO: MT5DemoExecutionProvider._external_mt5_read retorna cached[1] sem idade maxima quando nao consegue slot ou subprocesso expira. Possivel uso operacional de dados vencidos; nao ha prova retrospectiva de impacto em entradas/prejuizos. Nao alterar logica operacional neste reparo de Relatorios.

## 2026-10-21 - Correcao autorizada de cache operacional vencido
- Causa: _external_mt5_read validava TTL no caminho normal, mas retornava cache sem verificar idade em slot ocupado ou timeout/OSError. Cache compartilhado tambem era recopiado com timestamp novo.
- Correcao: falha retorna ok=False/rows vazias com motivo e idade descartada; log warning identifica acao e causa. Cache compartilhado nao renova idade ao ser consultado. Proxima tentativa busca dado novo. Nao modifica filtros, lotes, stops ou selecoes.
- 29 testes passaram (6 regressao de frescor e integracao M29/M30). Consulta operacional real somente leitura: Demo confirmada, 16.582 deals, 1,26s, ok=True, nenhuma ordem enviada.
- Relatorio confirmado no Chrome: M23 3.628 encerramentos, ultima data presente no MT5; fontes M10/M18/M20 tambem mostram encerramentos recentes. 27 curvas separadas por fonte/ativo e CSV/HTML exportados.
- Limite da auditoria: nao foi demonstrado retrospectivamente que cache vencido causou entradas ou prejuizos. Lacuna de metadados historicos permanece explicitamente nao registrada.
- Recarga final para ativar correcao operacional em andamento.

- Recarga final concluida: health OK; hashes das selecoes, estado online e agenda preservados. Relatorio deixado aberto no Chrome. Correcao operacional instalada, sem ordem de teste. Registro de impacto retrospectivo permanece inconclusivo.



## 2026-10-27 - Historico de execucao local autorizado
Usuario alterou auditoria para diariamente 19h Brasilia e solicitou migracao para C local. Caminho ativo resolvido por core.execution_log_storage.execution_log_path, com marcador por runtime .traderia/execution_storage.json. Demo usa C:/Users/evcab/TraderIAnovo_Refactor_Safe/Historico/mt5_demo_execution.jsonl. Nao consultar apenas o arquivo antigo no OneDrive para diagnosticar gravação. Runtime Real e caminhos explicitos preservados.
Original recusa append (Errno 22) e substituicao (WinError 5); causa de sistema operacional ainda indeterminada. Copia integral dos bytes antigos mais 384 registros alternativos deduplicados por event_id. Originais e backup mantidos. Journal de tentativas copiado. Escrita/fsync e leitura conferidas; 306 aceites conciliados no MT5; 8497 custos sem divergencia. 29 testes passaram; painel recarregado health 200. Nenhuma ordem de teste. Proxima gravacao natural no novo destino ainda precisa ser validada; nao afirmar que ocorreu.


## 2026-11-01 - Recuperacao autorizada da agenda e ciclos
Inicializacao interna no Streamlit pelo launcher e supervisores existentes, validando avanco real do ciclo; nao depende de navegador visivel. Recuperacao opt-in de rotinas encerradas, sem duplicar threads. Journal Demo impede repeticao de plano aceito e bloqueia fonte/ativo com resultado incerto ate conciliacao. Lock entre processos preserva exclusao. Real, regras e posicoes preservados. Corrigida falsa ausencia de listener quando HTTP responde. Backups em TEMP/traderia_recovery_nov01. 40 testes passaram; recarga oficial e sessao interna confirmaram ciclo novo. Conciliacao atual: 789 tentativas/resultados, 581 aceites nativos, zero nao conciliados. Nenhuma ordem de teste; operacao natural segue autorizada. Causa inicial da parada continua nao demonstrada; Windows desligado/suspenso e threads vivas travadas nao sao recuperados por este mecanismo. Commit isolado pendente: patch do launcher nao aplica em HEAD devido alteracoes anteriores; indice permaneceu intocado, nao incluir mudancas alheias.


## 2026-11-03 - Troca Demo e continuidade autorizada
Demo 61628148/Pepperstone-Demo substitui 61551556 no inicializador. Senha alterada pelo usuario no MT5; nenhum segredo copiado. Historico anterior preservado em Historico/conta-61551556. Continuidade explicita e exclusiva para a nova Demo das 27 curvas M23 por fonte/ativo, 3361 resultados encerrados conciliados na auditoria de 02/11. Identidades por conta evitam colisao de tickets; integridade por SHA256, corrupcao bloqueia a referencia. Nao transfere ordens ou posicoes antigas e nao inventa contexto de entrada. 44 testes passaram, 27 estados/faixas reproduzidos. Instalacao e validacao natural em andamento.


## 2026-11-03 - Validacao final da continuidade Demo
Continuidade autorizada restrita a conta Demo alvo, seed local validado por SHA256, identidades por conta. Relatorio exclui linhas anteriores ao corte da migracao para nao duplicar a copia salva; origem historica preservada. Arquivo real de 13154 linhas resulta nas mesmas 27 curvas e 3361 encerramentos arquivados. 46 testes passaram. Duas entradas naturais M23 (EURUSD e XAUUSD, 0.10) confirmadas como posicoes no MT5; nenhuma ordem de teste. Ciclo voltou a atualizar. Bootstrap reportou timeout antes do primeiro ciclo terminar; retificacao registrada. Controle do navegador indisponivel nesta verificacao final, portanto apresentacao visual nao confirmada. Historicos, configuracao local e credenciais excluidos do commit.


## 2026-11-03 - M29 alta/transicao em todos os ativos
Usuario autorizou substituir recortes M29 por estado patrimonial da mesma fonte/ativo: Alta ou Transicao com canal formado permitem; Baixa/Formacao/ausencia bloqueiam. Todos os ativos do universo e fontes ja atendidos pelo M29, lote 0.20, defesa 300 USD preservando SL menor. M23 selecionado executa copia M29 sem selecionar M29 independente; M30 preserva seis recortes/ouro/0.30 e excecao M7. Nova versao de filtro rejeita planos antigos. Validacao em geracao, envio e reavaliacao de pendentes por rota. 346 testes passaram; nenhum envio de teste. Backup em TEMP/traderia_m29_all_assets_nov03. Selecao apenas M23 e agenda preservadas por hash. Recarga oficial em verificacao. Commit isolado pendente devido dependencias locais anteriores nos mesmos arquivos; nao incluir mudancas alheias. Inicializador ignora listener residual com PID 0 (porta confirmou bind disponivel). Eventos simulados ticket 777 foram retificados no log.

Validacao de ativacao: processo novo carregado, health OK, ciclo atualizado apos recarga e SEM_GATILHO_VALIDO. Leitura de posicoes confirmada diretamente e pela sonda (duas posicoes); bloqueio transitorio de leitura cessou. Selecao somente M23 e agenda preservadas. Nova ordem natural sob a regra M29 ainda nao confirmada.


## 2026-11-04 - M29 somente alta confirmada
Usuario restringiu reforco M29/copia M23 a estrutura Alta E canal Alta, em todos ativos atendidos. Transicao, lateral, baixa, formacao e ausencia de canal bloqueiam. Lote 0.20, defesa 300 USD, fontes, M23 original e M30 preservados. Versao nova rejeita planos anteriores. 303 testes passaram. Backup TEMP/traderia_m29_up_only_nov04. Recarga em validacao; commit isolado ainda depende da separacao das alteracoes anteriores.


## 2026-11-04 - M29 alta ou rompimento superior com memoria
Usuario autorizou antecipar liberacao no primeiro resultado encerrado acima do teto em Transicao e manter ate rompimento inferior. Curva patrimonial da fonte/ativo M23, nao preco. Replay causal dos pivos/canais: Alta confirmada inicia, Acima em Transicao inicia, Dentro mantem, Abaixo bloqueia; alta estrutural inalterada nao rearma logo apos rompimento inferior. Lote 0.20 e defesa 300 preservados, todos ativos atendidos. Pendentes reavaliadas; posicoes abertas preservadas. Versao V3 rejeita planos anteriores. 296 testes passaram, nenhum envio de teste. Backup TEMP/traderia_m29_breakout_latch_nov04. Recarga em andamento; execucao natural da nova politica pendente.

Validacao apos recarga: ciclo atualizado e bloqueio transitorio de leitura cessou; ultima decisao observada rejeitada por limite de posicoes. Teste adicional comprova novo fechamento liquido altera referencia uma unica vez, excluindo abertas e outras fontes. 38 testes focados passaram (296 anteriores). Recalculo na proxima consulta operacional, cache curto de 2s por padrao; nao promessa de atualizacao instantanea. Nova ordem natural V3 e commit isolado permanecem pendentes.

## 2026-11-05 - Prioridade operacional sobre Relatorio MT5
Reproduzida contencao: leitura operacional aguardava 1s enquanto Relatorio podia manter trava por 45s. Relatorio agora usa concessao cancelavel, cede a consultas operacionais, encerra somente seu subprocesso de leitura e devolve fallback existente. Exclusao mutua preservada; dados vencidos continuam bloqueados na execucao. 12 testes passaram incluindo concorrencia real entre threads, cancelamento e regressao de cache. Backup TEMP/traderia_report_priority_nov05. Nenhuma ordem de teste. Causa historica especifica nao demonstrada. Recarga em validacao.

Ativacao validada: ciclo EXECUTED apos recarga; MT5 confirmou duas posicoes naturais EURJPY (.10 M23 e .20 M29). Bootstrap marcou timeout antes de observar o ciclo, mas avancou e foi confirmado depois, sem novo reinicio. Sem ordens de teste. Nao atribuir todo periodo sem entradas a contencao.

## 2026-11-08 - Identidade Demo na recuperacao automatica
Guard ainda tinha login da Demo anterior, divergente do launcher atual e terminal. Journal registrou 48 rejeicoes por conta divergente no domingo; nao era ausencia de sinais nem falha de inicializacao do servidor. Corrigida identidade autorizada no reinicio, mantendo checagem de conta e Real desabilitada. Teste compara login/servidor dos dois inicializadores. 11 testes passaram; backup TEMP/traderia_guard_account_nov08. Recarga em validacao, nenhuma ordem de teste.

Recarga confirmada: ciclo EXECUTED e tres posicoes naturais no MT5 (AUDUSD .10 M23 e .20 M29; USDJPY .10 M23). Rejeicao de conta divergente eliminada nos novos envios. Nao enviada ordem de teste. Auditoria ampliada para identidade dos inicializadores e motivos de rejeicao.


## 2026-11-09 - Auditoria: precisao temporal dos encerramentos
Encontrada divergencia descritiva no M18/XAUUSD: dois encerramentos no mesmo segundo eram ordenados por ticket no Relatorio, enquanto a referencia operacional preserva time_msc. Saldo e custos conferem; classificacao da curva diferia. Relatorio passa a preservar milissegundos dos deals, com fallback de segundos. Teste reproduz tickets 420314410/420299218 em ordem cronologica. Backup e evidencias em TEMP/traderia_audit_nov09_19h. Nenhuma ordem de teste, estrategia ou posicao alterada. Validacao do snapshot regenerado em andamento.

Validacao final: snapshot refeito por novo worker; 307 encerramentos e custos conciliados e 27 curvas com estado/faixa/saldo iguais a referencia operacional. 65 testes iniciais e 13 focados apos reparo passaram. Sem reinicio do robo ou ordens de teste. Pendentes conferencia visual e diagnostico causal de oito rejeicoes de gatilho/stop; protecoes preservadas.


## 2026-11-13 - Transporte do tunel Cloudflare
Imagem mostrou timeouts QUIC e DNS. No diagnostico inicial local/publico ja respondiam 200 e DNS resolvia. Tunel reiniciado isoladamente com --protocol http2, alternativa oficial para falhas UDP; quatro conexoes HTTP/2 registradas e precheck TCP/DNS passou. Inicializador preserva transporte HTTP/2. Nao reiniciado robo, nem alteradas contas/posicoes/agenda. Sintaxe PowerShell e teste de identidade passaram. Backup sem credenciais em TEMP/traderia_tunnel_nov13; causa de instabilidade da rede nao determinada, sem promessa de eliminar falhas DNS.


## 2026-11-20 - Versionamento do estado atual autorizado

Usuario solicitou commit e push das alteracoes acumuladas. Incluidos codigo, testes, contratos e governanca; excluidos runtime, credenciais novas e estudos com historicos de operacoes. Nenhuma recarga do robo, mudanca de configuracao ou ordem de teste nesta tarefa.

Validacao em copia isolada: 818 testes passaram, 44 subtestes passaram e 17 testes falharam. Bateria focada de integridade/agenda/curvas: 67 passaram. Sintaxe Python dos arquivos selecionados validada. Este registro e um checkpoint do estado existente, nao certificacao de conformidade completa. Pendencias: testes de interface, mensagens/contratos de espelhamento retirado, historico M29 sem canal e integracao de planos antigos. Proxima missao: investigar essas falhas contra os contratos atuais, sem alterar regras para satisfazer expectativas antigas.


## 2026-11-20 - Supervisor automatico passivo e reparador

Implementacao autorizada: tarefa Windows a cada minuto para saude/ciclo/journal, auditoria horaria offline e vigilancia independente a cada cinco minutos. Interface Sistema Forex com indicador desabilitado para edicao manual, verde apenas com evidencias recentes e completas, amarelo pendente e vermelho falha. Cada item informa checado/erro/corrigido.

Prioridade operacional: removida a proposta de nova leitura sincrona do supervisor por ordem; a validacao patrimonial existente permanece. Telemetria limitada em fila, sem chamadas adicionais MT5, sem espera por disco e descarte em saturacao. Auditoria usa copias de leituras reais; falta ou expiracao vira pendencia. Reparador do painel/ciclo aciona mecanismo existente no mesmo ciclo, confirma por nova observacao e limita repeticao a cinco minutos. Reparador do Relatorio reconstrui encerramentos de dados nativos capturados, preserva backup e valida custos; nao muda setups, conta, selecoes, stops, lotes ou posicoes. Falhas sem causa conhecida nao recebem reparo especulativo.

Validacao: 96 testes focados passaram; sem ordem de teste. Medicao local 10 mil chamadas: mediana 0,0009 ms no caminho limitado e 0,008 ms com fila cheia; nao equivale a garantia de latencia completa no broker. Tarefas instaladas e executadas; coleta real e ciclo apos recarga confirmados. Reparador conciliou 771 encerramentos sem diferenca de custos e 27 curvas sem diferenca de estado/faixa. Teste havia produzido observacao simulada no runtime: removida para evidencia fora da coleta, retificacao registrada e publicacao sob pytest desabilitada.

Pendencias explicitamente preservadas: duas linhas legadas de julho ilegíveis foram isoladas pelo leitor, sem apagar original nem inventar conteudo; 27 aceites ainda exigem historico nativo de ordens (717 outros confirmados como ORDEM_HISTORICA na copia). Ausencia de deal nao prova falha, pois ordens podem ser canceladas. Estado geral nao certificado verde. Futuro fechamento semanal e reinicio de Windows ainda exigem observacao natural; processo Windows depende de sessao do usuario. Nao foram executadas sete auditorias horarias nem garantida ausencia total de falhas.

Validacao final local: AppTest do Streamlit renderizou o indicador e os detalhes sem excecoes; checkbox desabilitado e desmarcado enquanto existem pendencias. Conferencia visual pelo Chrome nao concluida por timeout do controle. Tarefas Windows retornaram codigo 0; ciclo real avancou apos recarga. Estado final da auditoria PENDING: custos e 27 curvas conformes, 27 aceites aguardam historico de ordens. Nao afirmar verde ou sete auditorias horarias.


## 2026-11-25 - Validacao diaria e reparo do snapshot do Relatorio

Revisao externa confirmou 2.093 aceites contra ordens/deals/posicoes nativas,
3.751 tentativas com resultado e nenhuma tentativa orfa. A identidade Demo foi
comparada com os inicializadores e o terminal; conta Real preservada.

O snapshot de exibicao ainda nao refletia oito encerramentos recentes. O
reparador existente foi executado com backup recuperavel e validacao de
persistencia. Depois do reparo, 1.075 encerramentos e 27 curvas conferiram com
a captura operacional, incluindo custos, quantidade, saldo, estado e faixa.
Nao houve alteracao de codigo, estrategia, lote, stop ou posicao nesta auditoria.

Validacao: 96 testes focados passaram em copia isolada, incluindo identidade de
reinicio, cache vencido, prioridade de consultas, agenda, canais e reparador.
Nenhuma ordem de teste foi enviada. As 19 janelas coincidiram com o terminal
nas duas leituras; nove instrumentos nao avancaram ticks tambem no MT5 durante
a amostra proxima ao rollover. Isso nao comprova atraso exclusivo do cache.

Pendencias: validar sessao/avanco posterior desses instrumentos, ambiente
interno efetivo do processo e cobertura integral dos sinais anteriores ao envio
(inclusive NO_NEW_CANDLE). Duas linhas legadas ilegiveis continuam preservadas.
Os 18 resultados rejeitados foram agrupados por motivo e horario, sem atribuir
causa nao comprovada nem modificar protecoes. Estado global permanece PENDING.

Evidencias, backup e testes: TEMP/traderia_audit_nov25_ekwqs5m8, somente local.
Inicio, itens e conclusao registrados via application.operational_audit.event.
Este registro atualiza a validacao; nao representa nova instalacao ou recarga.


## 2026-11-27 - Substituicao da identidade Real solicitada pelo usuario

Conta Real configurada para 51618035 / PepperstoneBS-MT5-Live01 conforme
cadastro fornecido. Atualizados modulo dual, launcher manual e descricao do
atalho. Runtime separado real-51618035; historico real-51517136 preservado,
sem migrar tickets ou curvas. Controle local enabled=false/authorized=false.
Demo, estrategias e posicoes nao foram alteradas. Nenhuma ordem enviada.

Validacao: 14 testes isolados passaram (dual, reinicio Demo e regressao da
troca de identidade). Suite ampliada apresentou 18 falhas tambem reproduzidas
com core/dual_mt5.py anterior a alteracao; nao declarada aprovada.
Autenticacao nativa pendente: MT5 retornou -7, Unsupported authorization mode,
OTP or certificate password needed. Necessaria autenticacao interativa pelo
usuario; nao foi comprovada conexao nem recarga do processo Real instalado.
Backup local sem credenciais: TEMP/traderia_real_account_51618035_to0xs__c.


## 2026-11-28 - Inicializacao da nova conta Real

Login nativo confirmado na conta autorizada 51618035 / PepperstoneBS-MT5-Live01,
com trade_mode Real e permissoes da corretora. Controle operacional permanece
desativado. Atalho MT5 REAL e iniciador principal passam /login:51618035 ao
abrir o terminal Real; terminal Demo preservado. Corrigidos textos antigos
no painel. Senha nao armazenada em scripts. Credencial salva pertence ao MT5.
15 testes isolados aprovados. Atalho relido e confirmado. Reinicio completo
nao executado; reconexao apos reinicio ainda requer validacao natural.


## 2026-11-28 - Lotes e cesta exclusivos da Real autorizados

Real usa 0.01 normal e 0.02 reforco M29, inclusive copia dentro do M23.
Alvo financeiro M23/M29 Real +USD100; Demo permanece +USD1000 com lotes
anteriores. Provider rejeita lote Real divergente, sem arredondar para cima;
gestao de posicoes existentes usa volume nativo. Controle Real habilitado
por pedido explicito. Conta correta confirmada nativamente, sem posicoes
nem pendentes antes da ativacao. Novo worker confirmou WEEKLY_WINDOW_CLOSED;
nenhuma entrada fora da agenda e nenhuma ordem de teste enviada.
41 testes isolados aprovados: dimensionamento, limiares financeiros, cestas,
agenda e identidade. Execucao natural na proxima janela permanece pendente.
Backup local: TEMP/traderia_real_sizing_zfg7acm4. Sem senha nos arquivos.


## 2026-11-28 - Identidades fixas nos dois terminais e recuperacao Real

Leitura nativa confirmou Real 51618035 / PepperstoneBS-MT5-Live01 e Demo
61628148 / Pepperstone-Demo. Atalhos e iniciador fixam /login para cada
terminal, mantendo Demo portable e Real no terminal original. Worker Real
inicializa com login/servidor explicitos; divergencia permanece bloqueada.
Rotina de recuperacao sem navegador garante worker Real somente quando
controle previamente autorizado, inclusive se ciclo Demo ja estiver recente.
15 testes isolados passaram; nenhuma ordem de teste. Reinicio Windows completo
nao realizado. Backup local TEMP/traderia_fixed_accounts_dcncnlrk.
