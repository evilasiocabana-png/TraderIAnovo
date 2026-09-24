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
