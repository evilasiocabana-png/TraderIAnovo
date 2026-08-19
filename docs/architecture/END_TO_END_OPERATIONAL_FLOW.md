# TraderIA Novo - Fluxo Operacional E Relacoes De Ponta A Ponta

`M24_CONTRACT=M24_SETUP_V4_20260819; SHA256=6b80b8928dc6ad3389c8295913bb2d2f81b3c6365f0716adff971124ec2d4dfd`

## Rota autonoma M24

O M24 e calculado uma unica vez por ciclo sobre o cache `XAUUSD/M5`. Seu
contrato executavel fica em `application/model24_setup_contract.py`; o plano,
a interface e o estado persistido carregam a mesma versao/fingerprint. IDs de
fontes antigas sao somente compatibilidade historica e nao multiplicam o setup.
Apos o TP confirmado de uma `REENTRY`, o mesmo ciclo pode publicar uma
`CONTINUATION` a mercado com `0,40` lote quando preco e RSI extremo confirmam a
continuidade. O watch e persistente, consumido no aceite e falha fechado sem a
confirmacao read-only do historico MT5.
O plano `INITIAL` usa TP fixo a `0,25` do tick executavel. A `CONTINUATION`
usa TP fixo a `0,13` e SL na minima/maxima do M5 fechado anterior, com margem
de um pip no lado de protecao.

## Rota Combinavel M23

Quando M23 esta selecionado, os modelos marcados continuam calculando seus sinais
e gates. O M23 copia entrada e o contrato completo de saida da origem. Se a fonte tambem estiver
marcada para operacao direta, o mesmo sinal gera uma ordem da fonte e uma copia
M23, com comentarios e deduplicacao separados. A unica regra coletiva da cesta e
o Full Exit a mercado em +US$1.000; nao ha stop nem trailing financeiro global.
Esse Full Exit seleciona somente tickets identificados como M23; as posicoes
diretas M1-M22 nao entram no resultado da cesta e preservam suas saidas normais.

## Conjunto operacional vigente em 2026-08-12

M1, M2, M5, M7, M8, M10 e M16-M22 ficam visiveis no chaveamento e podem ser
selecionados livremente em qualquer combinacao. A selecao e persistida e
restaurada apos refresh, ciclo e reinicio. `Todos` marca somente esse conjunto;
M23 pode ser marcado junto com esse conjunto. Nesse modo, a duplicacao direta +
cesta e deliberada e precisa permanecer visivel na auditoria e no historico.

O executor avalia somente o conjunto marcado. Desmarcar um modelo bloqueia
apenas novas entradas dele e nao altera posicoes ja abertas.

M3, M4, M6, M9, M11, M12, M13, M14 e M15 permanecem fora do seletor e do
funil de novas ordens. Seus IDs continuam reconhecidos somente para historico e
gestao segura de posicoes legadas.

Retirada operacional nao apaga dados nem abandona risco existente. Comentarios,
historico e contratos de Position Manager permanecem reconhecidos para que uma
posicao legada possa ser acompanhada e encerrada pela regra com que nasceu.

M5 permanece independente e pode consultar pesquisa historica de M1-M4 para
materializar seu proprio plano. M3 e M4 somente geram suas proprias ordens quando
suas caixas estiverem marcadas; a consulta feita pelo M5 nao os ativa sozinha.

## Compatibilidade Com Modelos Historicos

IDs historicos continuam disponiveis para auditoria e para administrar com
seguranca posicoes antigas. Eles nao substituem os IDs canonicos M1-M22 usados
no chaveamento atual.

Os derivados M19, M21 e M22 permanecem modelos operacionais independentes.
Consultar a formula-base de um modelo retirado nao concede permissao de entrada
ao modelo de origem.

## Variante M18-M22

```text
snapshot XAUUSD/M5 compartilhado
  -> avaliador da origem M8/M9/M10/M11/M12
  -> entrada inicial MARKET, SL estrutural, sem TP
  -> Position Manager / Full Exit extremo
  -> estado local arma uma reentrada
  -> BUY_STOP ou SELL_STOP no candle M5 fechado
  -> TP no topo/fundo M5 confirmado antes da correcao enviado ao MT5
  -> TP do broker ou Full Exit pela perda do RSI50/inversao SMA
  -> novos recuos podem gerar novas reentradas sem duplicar candle/plano
```

Todos os modelos consomem a mesma janela deslizante de 200 velas fechadas mais
a vela atual em formacao. M18-M22 nao
iniciam Lab, backtest nem uma segunda leitura MT5 no ciclo leve; seus filtros
locais percorrem apenas esse lote pequeno ja carregado.

Status: referencia arquitetural canonica
Atualizado em: 2026-08-06

## Finalidade

Este documento e o mapa unico das relacoes operacionais do TraderIA Novo. Ele
deve ser consultado antes de alterar Lab, Forex, modelos ativos, Robo Demo, MT5,
Position Manager, Relatorio, persistencia local ou ciclos em segundo plano.

`docs/ARCHITECTURE.md` define camadas e invariantes gerais. Este documento
explica como os componentes se conectam na operacao real. Documentos mais
especificos continuam validos, mas nao podem contradizer este fluxo.

## Fluxo Canonico

```text
Historico MT5 local
        |
        v
Research Lab pesado, sob demanda
        |
        v
Snapshot + indice runtime do Lab
        |
        v
DashboardService enriquece leitura MT5 leve
        |
        v
DashboardMT5ForexSignalViewModel compartilhado
        |
        +--> Aba MT5 Forex / monitores M1-M12
        |
        +--> Seletor de modelos para novas entradas
        |
        v
Trade Plan materializa o plano do modelo
        |
        v
Robo Demo avalia gates e solicita abertura
        |
        v
DemoExecutionService --> Provider MT5 Demo
        |
        v
Posicao aberta no MT5
        |
        v
Position Manager le mercado e administra SL/saida autorizada
        |
        v
DemoExecutionService --> Provider MT5 Demo
        |
        v
Historico/Auditoria --> Aba Relatorio
```

## Autoridades

| Informacao ou decisao | Autoridade | Consumidores | Nao pode fazer |
|---|---|---|---|
| Candles historicos | MT5 + base local | Lab e Replay | Ser baixado em cada ciclo leve |
| Alpha, setup e TF vencedor M1 | Research Lab | Forex, Trade Plan, Robo, Replay | Ser inventado pela UI |
| Parametros M1 | Snapshot/indice runtime do Lab | DashboardService e Trade Plan | Ser substituido por fallback silencioso |
| Leitura de mercado atual | MT5MarketDataService | Forex e Position Manager | Recalcular o Lab pesado |
| Modelo autorizado para nova entrada | Estado persistido do seletor | Robo Demo | Encerrar gestao de posicoes existentes |
| Entrada, stop e alvo iniciais | Trade Plan do modelo | Robo Demo e MT5 | Ser recalculado pelo provider |
| Abertura Demo | Robo Demo | DemoExecutionService | Gerenciar posicao aberta |
| Gestao da posicao | Position Manager | DemoExecutionService e Relatorio | Criar nova entrada ou recalcular Lab |
| Envio/modificacao/fechamento Demo | DemoExecutionService | Provider MT5 Demo | Decidir estrategia |
| Posicao e resultado efetivos | MT5 | Position Manager e Relatorio | Ser inferidos apenas pela tela |
| Auditoria | Relatorio | Usuario e governanca | Decidir entrada ou saida |

## Artefatos E Fontes De Verdade

| Artefato | Papel | Escritor | Leitor |
|---|---|---|---|
| `.traderia/mt5_research_history_snapshot.json` | Base historica de pesquisa | Atualizacao manual do Lab | Research Lab e Replay |
| `.traderia/mt5_research_snapshot.json` | Resultado completo do Lab | Research Lab | Lab e relatorios |
| `.traderia/mt5_research_runtime_index.json` | Configuracao leve por par/TF | Research Lab | Ciclo Forex e Robo Demo |
| `research/alpha_suggested/model2_trend_pullback.py` | Contrato M2 independente nos oito pares | Governanca operacional | Runtime do Modelo 2 |
| `research/alpha_suggested/lab_operational_models_manifest.json` | Promocao versionada dos resultados pesquisados para M3-M5 | Auditoria de paridade | Runtime dos modelos M3-M5 |
| `.traderia/mt5_operational_model.json` | Modelos autorizados para novas entradas | Seletor MT5 Forex | UI e ciclo do Robo Demo |
| `.traderia/mt5_demo_robot_online_state.json` | Ultimo comando armar/desarmar | UI | Ciclo do Robo Demo |
| `.traderia/weekly_robot_schedule_state.json` | Janela semanal, proxima transicao e resultado do zeramento | Agenda semanal | UI, auditoria e ciclo do Robo Demo |
| `.traderia/mt5_demo_execution.jsonl` | Trilha de execucao | Execucao Demo | Relatorio |
| `.traderia/traderia_mt5_history.sqlite` | Historico local consolidado | Sincronizacao MT5 | Relatorio e auditoria |
| Snapshot compartilhado em memoria | Estado leve mais recente | Um unico ciclo background | Todas as sessoes Streamlit |

Arquivos compartilhados de estado devem usar escrita atomica. Uma sessao antiga
do navegador nunca pode sobrescrever um estado apenas porque renderizou.

## Pesquisa Pesada Do Lab

1. O usuario atualiza o historico quando necessario.
2. O usuario aciona `Atualizar calculos`.
3. O Lab avalia Alphas, timeframes, parametros e evidencia historica.
4. O Lab persiste o snapshot completo e o indice runtime leve.
5. O Replay reproduz a configuracao persistida sobre os 5.000 candles.
6. O ciclo Forex apenas consome o resultado; ele nao repete a pesquisa.

O painel principal do Lab apresenta uma linha para cada par analisado. O ICT e
uma referencia historica complementar e, no contrato atual, nao decide se a
linha pode operar no M1 Demo. Sua faixa nunca apaga nem oculta a configuracao
vencedora produzida pelo Lab.

O contexto temporal do replay e do Lab historico usa o horario do proprio
candle. O horario vivo do servidor MT5 participa apenas de gates operacionais
ao vivo, como a protecao de rollover. Misturar esses dois relogios torna o mesmo
backtest diferente conforme a hora em que ele e executado.

Uma configuracao ausente deve aparecer como `SEM_CONFIG_LAB` e permanecer
bloqueada. `ALPHA001`, `TREND_MOMENTUM` ou `BETA001` nao podem ser exibidos como
configuracao real quando forem somente defaults tecnicos.

Alphas sugeridas automaticamente pertencem a um fluxo de pesquisa separado. A
selecao deve ser congelada por treino e validacao antes de abrir o holdout; uma
candidata so recebe identidade operacional depois de aprovada em holdout,
estresse de custos, walk-forward e Demo futura. Ate la, nao entra no indice
runtime, nao aparece como Alpha ativa e nao envia ordem.

## Ciclo Leve Forex

1. Um unico ciclo process-local le o MT5.
2. `DashboardService.get_mt5_forex_runtime_view_model()` combina a leitura atual
   com as constantes persistidas do Lab.
3. O ciclo publica somente `DashboardMT5ForexSignalViewModel` enriquecido.
4. Abas e sessoes Streamlit consomem o mesmo snapshot compartilhado.
5. Nenhuma aba inicia leitura duplicada enquanto o ciclo compartilhado esta
   ativo.

O snapshot compartilhado precisa transportar, por par:

- Alpha e Beta;
- setup/modelo do Lab;
- timeframe vencedor;
- parametros do Lab;
- nota e status ICT informativos;
- sinal teorico e Trade Plan;
- leitura atual necessaria aos gates;
- estado de posicao e recomendacao do Position Manager quando aplicavel.

### Monitor De Indicadores M1-M12

O monitor da aba MT5 Forex e uma projecao read-only do mesmo ciclo operacional.
Sua primeira coluna identifica `M1` a `M7`; cada linha seguinte representa um
indicador ou uma condicao efetivamente usada pelo modelo naquele par e TF.

- M1 usa os indicadores declarados pelo setup vencedor do Lab.
- M2 usa o contrato congelado em `model2_trend_pullback.py`, com leitura M15/H1
  e os mesmos parametros para os oito pares.
- M3-M5 usam os parametros congelados no manifesto operacional.
- M6 usa a configuracao historica congelada `ALPHA001/MARCO_ZERO_A3BC912` e
  publica MA20, MA50, momentum 10, volatilidade 20, RSI14 e ATR20.
- M7 reutiliza a mesma leitura de entrada do M6 sem nova consulta ao MT5 e
  acrescenta o contrato de protecao `BETA007` para a posicao aberta.
- M4 e os vencedores M4 dentro do M5 incluem apenas o contexto H1/H4 realmente
  habilitado pelo overlay.
- `Leitura atual` vem do ultimo candle fechado usado na decisao.
- `Movimento` compara a leitura atual com o ciclo anterior da mesma sessao e
  informa `SUBINDO`, `CAINDO`, `ESTAVEL`, `MUDOU` ou `INICIAL`.
- Um modelo bloqueado por paridade gera somente a linha de bloqueio, sem dezenas
  de indicadores `N/D`.

O monitor nao consulta o MT5 de novo, nao recalcula o Lab e nao participa dos
gates. Ele consome os diagnosticos ja produzidos por
`LabOperationalModelService` e pelos adaptadores M6/M7, publicados no snapshot process-local compacto
`mt5_lab_operational_decisions`. A sessao Streamlit nunca recebe o cache bruto
de candles. Portanto, uma leitura pode permanecer `ESTAVEL` entre ciclos e
mudar quando o proximo candle do TF fechar.

## Modelos Operacionais

Os resultados pesquisados de M3-M5 foram promovidos formalmente em 2026-07-22.
A fonte versionada e
`research/alpha_suggested/lab_operational_models_manifest.json`. A liberacao
operacional Demo e definida separadamente em
`research/alpha_suggested/lab_demo_forward_policy.json`; ela pode autorizar uma
linha reprovada pela evidencia sem apagar o resultado original da auditoria.
O M2 possui contrato operacional proprio, aprovado em 2026-07-29.

| Modelo | Origem | Contrato vivo | Pares habilitados |
|---|---|---|---|
| M1 | Vencedor persistido do Research Lab | Materializa Alpha, TF, direcao, SL, TP e RR do Lab; SL/TP permanecem fixos | 8 pares do snapshot vigente |
| M2 | `ALPHA_M2_TREND_PULLBACK` | H1 EMA20/50 define direcao; M15 exige EMA9/21, ADX14 > 20, pullback e confirmacao fechada; SL 1,25 ATR e TP 2R fixos | 8 pares Demo |
| M3 | `ALPHAXAU3_RSI14_50_FLIP` | XAUUSD/M5, ultimas 52 velas: BUY RSI14>50 e fechamento>SMA20; SELL RSI14<50 e fechamento<SMA20; Full Exit no lado oposto do RSI e inversao no ciclo seguinte; SL pivo 2+2; sem TP | XAUUSD |
| M4 | Liquidity Reclaim experimental | Candle M30 fechado, BUY_ONLY, EMA34/144, ADX 28-35, proximo preco vivo, SL 2,5 ATR e TP 3R fixos | 8 pares Demo; AUDUSD e a evidencia-base nao certificada |
| M5 | Melhor evidencia consolidada M1-M4 | Delega ao contrato vencedor por par, sem recalcular | 8 pares por politica Demo |
| M6 | Vencedor individual do Lab nos novos pares Forex | Mesmo contrato vencedor pesado usado pelo M1, restrito ao universo de expansao; SL/TP fixos | 9 pares Forex adicionais |
| M7 | Vencedor individual do Lab em mercados alternativos | Mesmo contrato vencedor pesado usado pelo M1, restrito a ouro e Bitcoin; SL/TP fixos | XAUUSD e BTCUSD |
| M8-M12 novos | XAUUSD/M5, RSI14 no lado de 50 correspondente à direção SMA20/50; filtros A-E incrementais | Entrada inicial a mercado; reentrada por Stop no extremo do candle M5 anterior; SL além do pivô M5 2+2; sem TP | Full Exit no cruzamento fechado 70→baixo para BUY ou 30→cima para SELL, ou se SMA20/50 inverter |
| M13-M17 novos | 17 pares Forex/M5 com a mesma familia A-E de SMA20/50, RSI14 e filtros incrementais | Entrada inicial a mercado; reentrada Stop; SL estrutural 2+2; sem TP | Full Exit RSI 70/30 ou inversao SMA20/50 |
| M8-M14 históricos | Aposentados em 2026-08-06 | Contratos preservados somente para leitura historica; novas ordens bloqueadas | Nenhum |
| M15 | Aposentado em 2026-08-06 | Contrato preservado somente para leitura historica; novas ordens bloqueadas | Nenhum |
| M16 | Aposentado em 2026-08-06 | Contrato preservado somente para leitura historica; novas ordens bloqueadas | Nenhum |

O nome operacional do consolidado e somente M5. `M5-P` deixa de ser modelo
operacional separado. M1-M17 sao os contratos ativos e independentes.
Os IDs históricos M8-M12 e M13-M16 permanecem fora do seletor; os IDs novos e
isolados das familias M8-M12 e M13-M17 aparecem no funil de novas entradas.

O ciclo restaura 201 registros M5 por ativo antes de avaliar M8-M17 e calcula
os indicadores apenas sobre os 200 fechados. Uma semente do
SQLite local aquece os indicadores, mas permanece `WAIT` ate que uma leitura
MT5 valida marque a serie como `LIVE`.

M1-M7 obedecem `RESEARCH_FIXED_SL_TP`; o Position Manager apenas audita.
Posicoes historicas M8-M16 continuam identificaveis no Relatorio ate seu
encerramento, sem reativar esses modelos para novas entradas.

Cada linha do manifesto possui `demo_forward_enabled`. A politica vigente deixa
as oito linhas de M2, M3, M4 e M5 verdadeiras. O resultado cientifico anterior
continua nos campos `evidence_*`; por isso, liberacao operacional nao deve ser
interpretada como certificacao estatistica. A entrada usa somente o ultimo
candle fechado e pode ser solicitada no proximo preco vivo durante 120 segundos.
Essa janela deve comparar o inicio da barra atual com o horario vivo do servidor
MT5, pois ambos pertencem ao mesmo relogio da corretora. O relogio UTC da
maquina e apenas fallback quando o servidor estiver indisponivel. O ciclo
continua em 10 segundos, oferecendo varias avaliacoes dentro da janela sem
alterar indicadores nem timestamps historicos.

Os modelos sao independentes. A deduplicacao continua bloqueando repeticao do
mesmo modelo no mesmo plano/candle. A unica coexistencia deliberada do mesmo
plano e entre um modelo fixo M1-M7 e uma variante dinamica M8-M14, para que a
comparacao A/B seja real sem misturar as politicas de saida.

O seletor controla apenas novas entradas. Posicoes ja abertas de qualquer modelo
continuam visiveis e gerenciadas ate o fechamento. Em `TODOS_MODELOS`, cada
modelo passa por seus proprios gates; falha de um modelo nao pode cancelar,
fechar ou bloquear outro modelo aceito.

Detalhes de criacao e extensao ficam em
`docs/architecture/OPERATIONAL_MODEL_CREATION_PROTOCOL.md`.

## Fluxo De Entrada

Para cada par e modelo autorizado:

1. localizar configuracao valida e sua identidade;
2. ler o timeframe decisor correto;
3. produzir sinal teorico vivo;
4. validar novo candle/plano e deduplicacao;
5. validar filtros especificos do modelo;
6. registrar ICT/certificacao como referencia informativa;
7. validar mercado, fim de semana, rollover, conta Demo e permissao MT5;
8. validar ausencia de posicao daquele mesmo modelo/par;
9. materializar Trade Plan;
10. solicitar abertura ao `DemoExecutionService`;
11. registrar resultado aceito ou motivo exato da rejeicao.

O Robo Demo abre posicao. Ele nao escolhe Alpha, nao altera o racional do Lab e
nao gerencia a posicao depois da abertura.

## Fluxo De Posicao E Saida

1. O Position Manager detecta a posicao aberta no MT5.
2. Reidrata o Trade Plan pelo identificador/snapshot registrado na abertura.
3. Le preco e indicadores leves no timeframe de saida do modelo.
4. Calcula estado e acao auditavel.
5. Mantem a posicao, melhora o SL ou solicita fechamento apenas quando a politica
   operacional daquele modelo permitir.
6. O `DemoExecutionService` executa a modificacao; o provider nao decide.
7. O resultado e o motivo final seguem para historico e Relatorio.

O Position Manager deve continuar rodando mesmo se o seletor de novas entradas
mudar. Ele nunca pode afastar o stop contra o trader e nunca pode depender da
aba MT5 Forex estar aberta.

## Relatorio

O Relatorio cruza registros da aplicacao com posicoes e historico MT5. Ele deve
mostrar modelo, Alpha/setup de entrada, Beta/modo de saida, parametros efetivos,
movimento de SL, motivo de fechamento, custos e resultado. Ele observa fatos;
nao cria sinais nem envia ordens.

Tabelas grandes devem ser paginadas e dados historicos devem ser lidos de modo
incremental ou sob demanda. O ciclo de 10 segundos nao pode reconstruir todo o
historico.

## Abas E Ciclos

| Aba | Atualizacao permitida | Operacao proibida |
|---|---|---|
| MT5 Forex | Snapshot leve compartilhado | Lab pesado e historico completo |
| Laboratorio | Calculo pesado explicito | Execucao de ordem |
| Replay | Prova historica explicita | Alterar snapshot vencedor automaticamente |
| Relatorio | Cache/paginacao e refresh controlado | Decidir trade |

Trocar aba, recarregar pagina, abrir Safari/Chrome ou reconectar nao pode:

- desarmar o Robo Demo;
- alterar o modelo operacional;
- criar outro ciclo background;
- apagar o snapshot valido;
- interromper o Position Manager.

## Funil Visual De Entrada M1-M12

A tabela `Entrada Teorica MT5` deve decompor, para cada par e para cada modelo
M1-M12, as mesmas condicoes que antecedem o envio ao Robo Demo. A coluna
`Envio` e o resumo operacional: ela exibe `PRONTO` quando todas as etapas estao
aptas ou apresenta o gargalo mais relevante, no formato
`BLOQ/AGUARDA: etapa - motivo`.

Ordem das etapas exibidas:

1. `Modelo`: modelo selecionado para novas entradas;
2. `Liberacao Demo`: par presente e autorizado no manifesto operacional;
3. `Dados TF`: candles do timeframe do plano disponiveis;
4. `Candle fechado`: referencia temporal usada pela decisao;
5. `Indicadores`: parametros da Alpha calculados sem erro;
6. `Sinal`: direcao BUY/SELL confirmada, ou ausencia de gatilho;
7. `Janela`: sinal ainda dentro da janela executavel;
8. `Trade Plan`: entrada, SL, TP e RR materializados;
9. `Zona`: gate M1 ou condicao ja incorporada ao sinal pesquisado M2-M5;
10. `Filtro`: gate M1 ou parametros ja incorporados ao modelo M2-M5;
11. `Regime`: gate M1 ou contexto ja incorporado ao sinal M2-M5;
12. `Preco no plano`: preco vivo ainda executavel em relacao ao plano;
13. `Tempo`: sessao, fim de semana e rollover;
14. `Duplicidade`: plano/candle ainda nao executado;
15. `Posicao`: paridade por modelo disponivel;
16. `Robo`: Robo Demo armado;
17. `MT5 Demo`: terminal conectado e disponivel.

Regras de integridade:

- as celulas de etapa mostram status; detalhes tecnicos usam colunas distintas,
  como `Zona atual`;
- M2-M5 nunca herdam direcao, candle, entrada, SL ou TP da linha M1 quando a
  decisao propria estiver sem sinal;
- M2-M5 reutilizam a decisao compacta publicada pelo ciclo de 10 segundos;
- M6 e M7 compartilham uma unica leitura ALPHA001 por par/candle, mas
  materializam planos e saidas independentes;
- a tabela nao abre leitura MT5, nao recalcula o Lab e nao cria gate novo;
- bloqueios duros tem prioridade no resumo `Envio`; sem bloqueio duro, aparece
  a primeira etapa ainda aguardando;
- ausencia normal de gatilho (`NO_THEORETICAL_TRIGGER`) e espera operacional,
  nao rejeicao estrutural;
- a ordem continua sendo decidida e enviada pelo fluxo operacional, nunca pela
  tabela.

## Registro De Falhas Estruturais

Toda falha que atravesse mais de um componente deve entrar nesta secao e no
`docs/EXECUTION_LOG.md`.

| ID | Sintoma | Causa raiz | Componentes relacionados | Invariante corretiva |
|---|---|---|---|---|
| FLOW-001 | Monitor mostrou H1/TENDENCIA_MOMENTO/BETA001 iguais para todos os pares | Ciclo background publicou leitura MT5 crua, sem enriquecimento do Lab; UI aplicou defaults | Ciclo Forex, ciclo Robo, DashboardService, ViewModel, UI | Todo snapshot compartilhado Forex deve sair de `get_mt5_forex_runtime_view_model()` |
| FLOW-002 | Seletor parecia mudar sozinho ou voltar para M1 | Sessao Streamlit antiga persistia o valor do widget durante rerender passivo | UI, estado `.traderia`, ciclo Robo | Arquivo atomico e fonte compartilhada; persistir somente mudanca real do usuario |
| FLOW-003 | Ausencia de configuracao parecia ALPHA001/TREND_MOMENTUM real | Defaults tecnicos eram apresentados sem marcar a origem ausente | ViewModel, formatacao da tabela, gates | Exibir `SEM_CONFIG_LAB` e bloquear; nunca mascarar ausencia como setup valido |
| FLOW-004 | Testes e cenarios historicos mudavam durante o rollover real | O horario vivo do servidor MT5 sobrescrevia o contexto temporal do candle historico | ForexTimeLayer, Research Lab, Replay, gate de rollover | Lab/replay usam horario do candle; Robo Demo ao vivo usa horario do servidor |
| FLOW-005 | Lab mostrava somente USDCAD embora oito pares tivessem configuracao | A tela filtrava a lista pela nota ICT e confundia faixa de certificacao com plano inexistente | Snapshot do Lab, resumo e tabela principal | Mostrar todos os pares e apresentar ICT apenas como referencia historica informativa |
| FLOW-006 | A tela dizia que o ICT liberava ou bloqueava o M1, mas o Trade Plan e o Robo o tratam como informativo | A nomenclatura visual ficou atras do contrato operacional atual | Lab, Trade Plan, Robo Demo, UI e documentacao | ICT nao bloqueia Demo; qualquer mudanca de pesos, corte ou autoridade operacional exige missao explicita e testes de ponta a ponta |
| FLOW-007 | O runtime podia indicar rollover em horario incorreto | Timestamp Unix do tick era convertido como horario local e depois rotulado como UTC | Provider MT5, ForexTimeLayer, gates do Robo Demo | Converter epoch diretamente em UTC com timezone explicito; bloqueios duros de fim de semana/rollover nunca dependem do filtro opcional de sessao |
| FLOW-008 | Pesquisa promovida ainda aparecia com nomes e fluxos legados M4 espelho, M5 Price Action e M5-P | UI, runtime e documentacao mantinham contratos historicos diferentes | Manifesto, DashboardService, Trade Plan, Robo Demo, Provider, UI e testes | Uma promocao de modelo deve trocar todos os consumidores; M1-M5 continuam os modelos promovidos do Lab |
| FLOW-009 | `unittest discover` global permaneceu mais de 15 minutos sem concluir nem publicar progresso | A suite agregada mistura testes leves, pesquisa pesada e rotinas com ciclos/threads; o teste global ainda nao possui particionamento e timeout por grupo | Testes, pesquisa, dashboard e runtime background | Gates de entrega usam suites focadas com tempo limitado; a suite global deve ser particionada e nunca pode ser executada dentro do ciclo operacional |
| FLOW-010 | O monitor nao permitia rastrear quais indicadores M2-M5 estavam mudando | A execucao calculava os indicadores, mas a UI exibia apenas o resumo textual do modelo | LabOperationalModelService, manifesto, ciclo compartilhado e aba MT5 Forex | Projetar uma linha por indicador usado, com modelo na primeira coluna e movimento entre ciclos, reutilizando o snapshot sem leitura MT5 adicional |
| FLOW-011 | O novo monitor estava correto, mas o ciclo quente ainda consumia CPU por varios segundos | As mesmas velas eram normalizadas dezenas de vezes, o ViewModel visual montava dados alheios ao MT5 e o horario do servidor era consultado por candidato | LabOperationalModelService, DashboardService, ciclo Robo e exportador visual | Uma vela fechada deve ser normalizada uma vez por par/TF; o exportador recebe o ViewModel Forex direto; o horario do servidor e compartilhado no ciclo; o ciclo Robo publica a decisao ja calculada |
| FLOW-012 | Graficos configurados para 22/07 ainda mostravam resultados realizados em 21/07 no Brasil e legenda `desde indice` | O filtro comparava somente a data UTC de fechamento, aceitava horario desconhecido e depois aplicava outro corte por indice | Historico MT5, aba Relatorio, graficos M1-M10 e testes | A janela patrimonial converte o fechamento MT5 para `America/Sao_Paulo`; resultado anterior fica fora; horario desconhecido nao entra; nao existe segundo corte por indice |
| FLOW-013 | A tabela M2-M5 podia mostrar sinal/zonas herdados do M1 e duas colunas `Plano` sem revelar o gargalo real | A projecao clonava a linha M1 sem limpar campos operacionais e uma chave `Zona` duplicada sobrescrevia o status do gate | Snapshot compartilhado, projecao M1-M5, tabela MT5 Forex e testes | Cada modelo limpa campos herdados, usa sua decisao compartilhada e expoe um funil unico; `Envio` mostra `PRONTO` ou o motivo do gargalo sem executar logica propria |
| FLOW-014 | O seletor e o historico ainda tratavam M6 como espelho inativo do M5 depois da recuperacao do setup original | Identificador, visual, Robo Demo e comentario MT5 nao compartilhavam o novo contrato | Configuracao M6, DashboardService, snapshot, UI, Robo Demo, provider, testes e documentos | M6 e independente, usa `MODELO_6_TREND_MOMENTUM_ORIGINAL`, candle M1 fechado, risco maximo entre 2 ATR e 0,10% do preco, TP RR2 fixo e provider Demo |
| FLOW-015 | O cartao M6 mostrava 13 operacoes e `-12,80`, enquanto a linha ja desenhava 20 operacoes e `100,61` | Elementos sem identidade explicita eram reaproveitados durante rerenders do fragmento do Relatorio | Cache do Relatorio, fragmento Streamlit, cartoes e graficos M1-M10 | Cartao, contagem e pontos devem nascer de um snapshot unico; painel e grafico recebem chave por modelo e versao dos dados, sem nova leitura MT5 |
| FLOW-016 | M6 moveu SL apesar de ter sido concebido para reproduzir entrada e saida fixas do marco zero | Ao criar o adaptador M6, a configuracao de entrada ALPHA001 recebeu por heranca o wrapper global `BETA001_PROTECT_ONLY_V1` e `DYNAMIC_POSITION_MANAGER` | Configuracao M6, Trade Plan, reconstrucao de snapshots, Position Manager, UI, testes e documentacao | M6 declara `BETA001_FIXED_SL_TP_RR2_V1`; snapshots antigos sao identificados pelo modelo/origem e bloqueados antes de qualquer leitura ou comando de gestao |
| FLOW-017 | M1 recebia SL/TP do Lab, mas o runtime ainda podia mover o SL | `FIXED_STOP` era reinterpretado como `DYNAMIC_POSITION_MANAGER` depois da abertura | Research Lab, Trade Plan M1, registro de execucao, Position Manager, UI, testes e documentacao | M1 publica `RESEARCH_FIXED_SL_TP`; snapshots M1 antigos sao bloqueados pela identidade `MODELO_1_ALPHA_ATUAL`; o PM somente audita |
| FLOW-018 | A versao dinamica historica do ALPHA001 poderia voltar a contaminar o M6 fixo | Entrada e politica de saida compartilhavam identidade, permitindo heranca de `DYNAMIC_POSITION_MANAGER` | Configuracao M6/M7, Trade Plan, Robo Demo, provider, Position Manager, MT5 Forex, Relatorio e testes | M6 continua `BETA001_FIXED_SL_TP_RR2_V1`; a variante dinamica vira M7 independente com `BETA007`, risco inicial imutavel, protecao somente apos 1,50R e nenhum fechamento antecipado |
| FLOW-019 | M8-M14 recebiam sinais validos, mas nao enviavam durante uma falsa janela de rollover | O fallback fixo de 21h UTC continuava prevalecendo mesmo com `TimeTradeServer` valido | Camada Tempo, Robo Demo, funil M1-M14 e testes temporais | Com horario MT5 valido, somente os 5 minutos antes/depois da virada do servidor bloqueiam; o horario fixo fica restrito ao fallback sem relogio MT5. As variantes continuam independentes, mas repetem todos os gates de entrada da origem; em especial, M8 preserva o regime adicional do M1 |
| FLOW-019 | M2, M3 e M4 produziram sinais historicos, mas nenhum plano novo chegou ao executor | A janela de 120 segundos comparava barras marcadas no relogio do servidor Pepperstone com o UTC da maquina; a diferenca de aproximadamente tres horas classificava a barra viva como futura | Provider MT5, LabOperationalModelService, ciclo de 10 segundos, Trade Plan, Robo Demo, funil visual e testes | Frescor de entrada compara barra atual e `server_timestamp` no mesmo relogio MT5; UTC local e fallback; candles historicos e parametros pesquisados permanecem inalterados |
| FLOW-020 | Depois de reiniciar o app fora do horario operacional, o diagnostico MT5 respondia, mas os monitores desapareciam aguardando o primeiro snapshot | O bloqueio correto dos ciclos de fim de semana tambem impedia a leitura inicial read-only e o snapshot existia apenas na memoria do processo encerrado | Inicializacao Streamlit, DashboardService, snapshot compartilhado, MT5 Forex e Relatorio | Na ausencia de snapshot valido, a inicializacao faz uma unica leitura historica read-only, publica o resultado compartilhado e nao arma o Robo nem envia ordens; ciclos automaticos e execucao continuam sujeitos aos bloqueios temporais |
| FLOW-021 | O grafico patrimonial mostrava `Patrimonio final` usando somente `profit` do MT5 | Comissao, swap/rollover e fee existem em campos separados nos deals MT5 | Historico MT5, auditoria, graficos por modelo e Relatorio | Cada painel mostra lucro bruto, custos MT5, lucro liquido e detalha comissao, swap/rollover e taxas; somente operacoes fechadas, encontradas no MT5 e dentro da mesma data-base entram na conta |
| FLOW-022 | O app abria e depois deixava de responder, mesmo com RAM baixa | A interface possuia fallbacks que executavam leitura MT5 e ciclo completo do Robo Demo durante o rerender quando o thread de fundo ainda nao estava ativo; uma sessao reconectada podia bloquear o servidor inteiro | Streamlit, ciclo Forex, ciclo Robo Demo, snapshot compartilhado, MT5 e guardiao de RAM | A UI nunca executa ciclo operacional nem leitura MT5 automatica; threads de fundo sao os unicos donos dessas operacoes e a tela apenas consome o ultimo snapshot publicado |
| FLOW-023 | M23 fez somente uma entrada e varias fontes ficaram uma hora inteira em `ROLLOVER_BLOQUEADO` | Quando a sonda do horario do servidor estava ocupada, o runtime reutilizava o horario do candle H1 fechado; a barra `21:00 UTC` mantinha o fallback de rollover ativo durante toda a formacao do candle | ForexTimeLayer, cache de horario MT5, ciclo Robo Demo, funil M23 e UI | No fluxo ao vivo, rollover usa exclusivamente o horario vivo ou extrapolado do servidor; sem esse relogio, o candle fechado nunca cria bloqueio estatico. A barreira historica permanece apenas em Lab/Replay, e o provider MT5 continua sendo a autoridade final para `Market closed` |
| FLOW-024 | M23 encerrava ou bloqueava a cesta por stop global, trailing e orcamento agregado de SL | Regras financeiras transitorias competiam com os SL/TP herdados e impediam reentradas normais | Model23BasketManager, DashboardService, provider MT5, UI e testes | M23 preserva SL/TP das fontes, permite reentrada em novo sinal e possui uma unica zeragem coletiva: Full Exit a mercado em +US$1.000 liquidos. O mesmo sinal/candle continua deduplicado |
| FLOW-025 | Position Manager ignorava todo ticket M23 | A cesta preservava SL/TP, mas descartava a saida dinamica do modelo-fonte; uma inversao SMA podia permanecer aberta ate o SL | DashboardService, PositionManagerService, M23, UI, documentacao e testes | Cada ticket M23 e reconstruido com o modelo e a politica de saida da fonte; SL/TP e saida dinamica continuam validos, com Full Exit coletivo adicional em +US$1.000 |
| FLOW-026 | Sinal M5 aparecia na tela, mas a ordem Stop era rejeitada como candle expirado e a copia M23 competia com a fonte | A expiracao somava 5 minutos a abertura do ultimo candle fechado, exatamente o instante em que o plano nascia; alem disso, a deduplicacao tratava carteira direta e cesta M23 como uma unica execucao | Indicadores M5, Trade Plan, Robo Demo, provider MT5, M23, logs e testes | A pendencia vale ate o fim do candle corrente (`candle fechado + 10 minutos`) no relogio MT5. Modelo-fonte e M23 podem executar o mesmo sinal em carteiras independentes; repeticao dentro da mesma carteira e candle continua bloqueada |

## Regra De Mudanca Interligada

Uma correcao nao esta completa ate verificar todos os pontos aplicaveis:

1. fonte de dados ou regra de dominio;
2. contrato/DTO/ViewModel;
3. fachada `DashboardService`;
4. ciclo background e snapshot compartilhado;
5. Trade Plan e gates;
6. Robo Demo e execucao;
7. Position Manager;
8. persistencia `.traderia`;
9. abas MT5 Forex, Lab, Replay e Relatorio;
10. auditoria/historico;
11. testes unitarios, de integracao e regressao;
12. este documento, `docs/ARCHITECTURE.md` e `docs/EXECUTION_LOG.md`.

Se um item nao for afetado, a revisao deve registrar por que ele ficou fora.
Correcao apenas visual nao encerra falha cuja causa esteja no contrato ou no
runtime.

## Testes De Protecao

Os testes devem garantir no minimo:

- ciclos background publicam ViewModel enriquecido pelo Lab;
- ausencia de configuracao aparece explicitamente e bloqueia entrada;
- parametros por par/TF chegam ao monitor;
- sessao antiga nao sobrescreve modelo operacional persistido;
- desarme ocorre somente por comando explicito ou bloqueio operacional real;
- modelos independentes nao cancelam uns aos outros;
- bloqueios duros de fim de semana e rollover continuam ativos mesmo com filtro
  geral de sessao desmarcado;
- M2 usa exatamente o contrato `ALPHA_M2_TREND_PULLBACK` documentado, sem
  herdar o M1;
- M3 usa RSI14 e SMA20 nas ultimas 52 velas XAUUSD/M5 para autorizar a entrada;
  o Full Exit e a inversao continuam em torno de 50; M4-M5 usam Alpha, TF,
  filtros e SL/TP do manifesto;
- M6 aparece, calcula somente com candles ja carregados e envia exclusivamente
  ao MT5 Demo quando selecionado, armado e com todos os gates aprovados;
- M6 e M7 reutilizam somente os resultados persistidos do Lab nos seus
  universos e preservam SL/TP fixos;
- Position Manager continua administrando posicoes abertas fora da aba MT5;
- Relatorio nao participa da decisao nem torna o ciclo leve pesado.
- Lab e Replay permanecem deterministas mesmo durante rollover vivo do MT5.
- a mesma colecao de candles nao e normalizada novamente enquanto o candle
  fechado e o timestamp da barra atual permanecerem iguais.
- a janela viva M2-M5 usa o relogio do servidor MT5 e aceita o sinal durante
  120 segundos; o ciclo permanece em 10 segundos e o UTC da maquina so entra
  como fallback.
- Em `TODOS_MODELOS`, somente M1-M12 podem gerar novas entradas, no maximo uma
  posicao por modelo.
- Os IDs M8 historicos e M9-M16 sao rejeitados pela politica central de modelos mesmo que um estado
  persistido antigo ou uma chamada direta tente seleciona-los.

## Documentos Complementares

- `docs/ARCHITECTURE.md`
- `docs/LAB_FOREX_MT5_CONTRACT.md`
- `docs/LAB_FOREX_MT5_FLOW.md`
- `docs/architecture/TRADE_ENTRY_EXIT_CONTRACT_AUDIT.md`
- `docs/architecture/POSITION_MANAGER_OFFICIAL_CONTRACT.md`
- `docs/architecture/OPERATIONAL_MODEL_CREATION_PROTOCOL.md`
- `docs/architecture/DYNAMIC_EXIT_MODELS_M8_M14.md`
- `docs/architecture/OPERATIONAL_MODEL_M15_XAU_M5_BREAKOUT.md`
- `docs/architecture/OPERATIONAL_MODEL_M16_XAU_M5_PRICE_EMA_BREAKOUT.md`
- `docs/architecture/OPERATIONAL_MODELS_M11_M20.md`
- `docs/architecture/OPERATIONAL_MODEL_M21_M19_MIRROR.md`
- `docs/architecture/OPERATIONAL_MODEL_M22_M9_MIRROR.md`
- `docs/RUNTIME_AND_ARTIFACTS.md`
## Protecao contra travamento da ponte MT5

O runtime oficial usa uma unica sessao MT5 persistente em processo quando
`TRADERIA_MT5_INPROCESS_ENABLED=1`. A sessao ativa deve ser reutilizada por
Market Data, auditoria e execucao; `initialize()` so pode ocorrer quando a sessao
ainda nao existir. O caminho canonico do terminal e transportado por `MT5_PATH`.

No processo Streamlit, as leituras potencialmente longas ficam isoladas quando
`TRADERIA_MT5_MARKET_DATA_EXTERNAL_PROCESS_ENABLED=1` e
`TRADERIA_MT5_REPORT_EXTERNAL_PROCESS_ENABLED=1`. A primeira protege candles e
posicoes usadas pelo JSON visual; a segunda protege historico, saldo e auditoria
do Relatorio. Cada ponte possui timeout e falha preservando o ultimo estado,
sem transferir decisao operacional para a UI.

As consultas read-only repetitivas do executor e do Position Manager usam
`TRADERIA_MT5_EXECUTION_READ_EXTERNAL_PROCESS_ENABLED=1`: lista de posicoes,
duplicidade, preco e candles recentes ficam fora do Streamlit. Alteracao de SL e
envio continuam no provider Demo, sob seus gates, locks e auditoria existentes.

A leitura Forex dos oito pares deve ocorrer em lote. Se o lote falhar, o runtime
preserva o ultimo candle valido em cache e publica `WAIT`; e proibido abrir uma
sequencia de consultas individuais por par como fallback, pois isso multiplica
timeouts e bloqueia a interface.

Quando a fonte MT5 estiver aquecendo ou temporariamente indisponivel, o Relatorio
marca a conferencia como `PENDENTE`, com zero registros auditados e zero
divergencias. Ausencia temporaria da fonte nunca equivale a divergencia do
historico local.

As leituras externas de contingencia continuam serializadas e com timeout curto
por tipo de operacao. Um subprocesso sem resposta deve ser encerrado e nunca pode
bloquear o ciclo leve do Streamlit. O guardiao tambem verifica
`/_stcore/health`: processo existente sem resposta HTTP e tratado como travado e
reiniciado, independentemente do consumo de RAM.

As sessoes de navegador compartilham a mesma fachada visual process-local. O
historico de execucao tambem possui cache incremental unico; abrir outra aba nao
repete a conversao de todo o JSONL. Quando o Robo Demo esta online, o ciclo
Forex observador libera sua fachada pesada e consome o snapshot publicado pelo
dono operacional ativo.

Nenhum fragmento, rerender, troca de aba ou reconexao web pode assumir o ciclo
operacional como fallback. Se o snapshot ainda nao existir, a tela preserva o
ultimo estado leve e aguarda a publicacao do thread de fundo. Isso mantem a rota
de saude responsiva mesmo quando uma chamada nativa do MT5 demora.

## Auditoria do pico antes do fechamento

Enquanto uma posicao esta aberta, a mesma leitura leve usada pelo Relatorio
compara o lucro flutuante MT5 com o pico persistido do ticket. Somente um novo
maximo gera atualizacao local. Quando o ticket migra para
`FECHADA/HISTORICO`, o Relatorio apresenta lado a lado o resultado realizado e
o `Pico lucro aberto`, incluindo o horario UTC em que o maximo foi observado.
Esse fluxo e somente leitura e nao interfere na entrada, no SL, no TP ou no
Position Manager.

## Invariante da janela operacional M5

A persistencia `.traderia/mt5_m5_warm_cache.json` serve somente para aquecer a
tela e os indicadores. Depois de qualquer reinicio do processo, mesmo quando o
arquivo declarar fonte `LIVE`, a janela permanece bloqueada para ordens ate ser
substituida por 201 candles obtidos diretamente do terminal MT5.

Durante o runtime leve, cada atualizacao M5 le duas barras: a barra anterior ja
fechada e a barra atual em formacao. Isso corrige no cache o fechamento final da
barra anterior e impede que uma cotacao parcial seja congelada como candle
fechado. Se essas duas barras nao tiverem sobreposicao ou continuidade com a
janela corrente, o runtime baixa novamente as 201 barras e continua bloqueado
ate a reconciliacao terminar. Lab pesado e backtest permanecem fora desse ciclo.
