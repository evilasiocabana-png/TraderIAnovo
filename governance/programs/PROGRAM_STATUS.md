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

# Program Status

## Observacao operacional - 2026-09-05

Marco 01/09/2026 00:00 BRT registrado com baseline Demo descritivo e protocolo
de continuidade. Sem mudanca operacional. Primeira revisao estruturada proposta
para 12 semanas, sem inferencia automatica de consistencia. Referencia:
docs/research/EVOLUCAO_OPERACIONAL_MARCO_2026-09-01.md.

`M24_CONTRACT=M24_SETUP_V19_20260823; SHA256=d918353322bc17fd17e1c7d0ba47272cf19431ef2c60d9cd1686829f2802c05f`

`M25_CONTRACT=M25_XAU_SOURCES_V6_20260820; FINGERPRINT=d0d758099058ffde`

`M26_CONTRACT=M26_SMART_MONEY_V3_20260825; FINGERPRINT=4df7d17616d6a82e`

| Programa | Status |
| --- | --- |
| A01 Foundation | active |
| A02 Forex MT5 | planned |
| B01 Lab | planned |
| C01 Reports | planned |
| TIA Dynamic Exit Runtime Full Execution | accepted |
| M7 Trend Momentum Dynamic Protect Only | completed |
| M24 XAU RSI50 Basket | V19 canonical contract; INITIAL/REENTRY com TP Fibonacci; INITIAL, REENTRY e CONTINUATION em 0,10 lote; CONTINUATION Stop no TP da INITIAL sem TP e trailing por candle; lateralizacao da REENTRY aberta reposiciona SL/TP em RR 3:1 sem nova ordem; awaiting demo observation |
| M25 XAU Source Basket | contract V2 restricted to XAUUSD/M5; independently copies M8, M10 and M18-M22 entry/SL/TP; automated validation complete; awaiting demo observation |
| M26 XAU M1 Smart Money | independent deterministic structure/sweep/BOS/FVG/OB/retest contract; Demo-only automated validation in progress |
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


## 2026-09-29 — Refatoracao da integracao das abas
Contrato compartilhado de apresentacao, catalogo e estado do M30; persistencia extraida sem migracao. Sincronizacao evita toggle antigo do Aprendizado sobrescrever escolha do MT5. Historico legado e politica atual identificados. 33 testes passaram. Ver docs/architecture/MODEL_UI_STATE.md. Sem alteracao de regras financeiras ou posicoes.


## 2026-09-30 — Graficos somente das politicas atuais
Relatorio M29 mostra somente M7 espelhado com m29_sequence_mode identificado; canal anterior, normais e gatilho desconhecido ficam fora. M30 mostra somente m30_policy atual. Filtro no snapshot, nunca por data presumida. Registros e execucao intactos. Dez testes passaram; recarga oficial preserva selecao, agenda e online.


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
