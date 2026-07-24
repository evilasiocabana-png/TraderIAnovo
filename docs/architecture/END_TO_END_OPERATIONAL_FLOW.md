# TraderIA Novo - Fluxo Operacional E Relacoes De Ponta A Ponta

Status: referencia arquitetural canonica
Atualizado em: 2026-07-22

## Finalidade

Este documento e o mapa unico das relacoes operacionais do TraderIA Novo. Ele
deve ser consultado antes de alterar Lab, Forex, modelos M1-M6, Robo Demo, MT5,
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
        +--> Aba MT5 Forex / monitores M1-M6
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
| `research/alpha_suggested/lab_operational_models_manifest.json` | Promocao versionada dos resultados pesquisados para M2-M5 | Auditoria de paridade | Runtime dos modelos M2-M5 |
| `.traderia/mt5_operational_model.json` | Modelos autorizados para novas entradas | Seletor MT5 Forex | UI e ciclo do Robo Demo |
| `.traderia/mt5_demo_robot_online_state.json` | Ultimo comando armar/desarmar | UI | Ciclo do Robo Demo |
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

### Monitor De Indicadores M1-M6

O monitor da aba MT5 Forex e uma projecao read-only do mesmo ciclo operacional.
Sua primeira coluna identifica `M1` a `M6`; cada linha seguinte representa um
indicador ou uma condicao efetivamente usada pelo modelo naquele par e TF.

- M1 usa os indicadores declarados pelo setup vencedor do Lab.
- M2-M5 usam os parametros congelados no manifesto operacional.
- M6 usa a configuracao historica congelada `ALPHA001/MARCO_ZERO_A3BC912` e
  publica MA20, MA50, momentum 10, volatilidade 20, RSI14 e ATR20.
- M4 e os vencedores M4 dentro do M5 incluem apenas o contexto H1/H4 realmente
  habilitado pelo overlay.
- `Leitura atual` vem do ultimo candle fechado usado na decisao.
- `Movimento` compara a leitura atual com o ciclo anterior da mesma sessao e
  informa `SUBINDO`, `CAINDO`, `ESTAVEL`, `MUDOU` ou `INICIAL`.
- Um modelo bloqueado por paridade gera somente a linha de bloqueio, sem dezenas
  de indicadores `N/D`.

O monitor nao consulta o MT5 de novo, nao recalcula o Lab e nao participa dos
gates. Ele consome os diagnosticos ja produzidos por
`LabOperationalModelService` e pelo adaptador M6 original, publicados no snapshot process-local compacto
`mt5_lab_operational_decisions`. A sessao Streamlit nunca recebe o cache bruto
de candles. Portanto, uma leitura pode permanecer `ESTAVEL` entre ciclos e
mudar quando o proximo candle do TF fechar.

## Modelos Operacionais

Os resultados pesquisados foram promovidos formalmente em 2026-07-22. A fonte
versionada e `research/alpha_suggested/lab_operational_models_manifest.json`.
A liberacao operacional Demo e definida separadamente em
`research/alpha_suggested/lab_demo_forward_policy.json`; ela pode autorizar uma
linha reprovada pela evidencia sem apagar o resultado original da auditoria.

| Modelo | Origem | Contrato vivo | Pares habilitados |
|---|---|---|---|
| M1 | Vencedor persistido do Research Lab | Materializa Alpha, TF, direcao, SL, TP e RR do Lab; SL/TP permanecem fixos | 8 pares do snapshot vigente |
| M2 | `ALPHA_SUGERIDA_001_PLUS` | Ultimo candle fechado H1, proximo preco vivo, SL/TP fixos | 8 pares por politica Demo |
| M3 | `ALPHA_SUGERIDA_002_PLUS` individual | Ultimo candle fechado M30/H1, proximo preco vivo, SL/TP fixos | 8 pares por politica Demo |
| M4 | Pesquisa contextual MTF | Candle M30 fechado com contexto H1/H4, proximo preco vivo, SL/TP fixos | 8 pares por politica Demo |
| M5 | Melhor evidencia consolidada M1-M4 | Delega ao contrato vencedor por par, sem recalcular | 8 pares por politica Demo |
| M6 | Trend Momentum original do marco `a3bc912` | Ultimo candle M1 fechado, proximo preco vivo, SL maximo entre 2 ATR e 0,10% do preco e TP RR2 fixos | 8 pares Demo |

O nome operacional do consolidado e somente M5. `M5-P` deixa de ser modelo
operacional separado. M6 e independente de M1-M5, aparece no seletor, entra em
`TODOS_MODELOS`, cria Trade Plan proprio e envia somente ao provider MT5 Demo.

M1-M5 obedecem `RESEARCH_FIXED_SL_TP`. O Position Manager continua observando
e auditando suas posicoes, mas nao move SL nem executa `FULL_EXIT`. Assim, o
resultado forward pode ser confrontado diretamente com a hipotese historica.
M6 tambem usa `RESEARCH_FIXED_SL_TP`, mas possui bypass adicional por identidade
do modelo para neutralizar snapshots antigos criados com politica dinamica.

Cada linha do manifesto possui `demo_forward_enabled`. A politica vigente deixa
as oito linhas de M2, M3, M4 e M5 verdadeiras. O resultado cientifico anterior
continua nos campos `evidence_*`; por isso, liberacao operacional nao deve ser
interpretada como certificacao estatistica. A entrada usa somente o ultimo
candle fechado e pode ser solicitada no proximo preco vivo durante 120 segundos.

Os modelos sao independentes. A excecao de seguranca e a deduplicacao: mesma
direcao, entrada, stop, alvo e candle de sinal nao podem criar duas posicoes,
mesmo quando o mesmo vencedor aparece em M1 e M5.

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

## Funil Visual De Entrada M1-M6

A tabela `Entrada Teorica MT5` deve decompor, para cada par e para cada modelo
M1-M6, as mesmas condicoes que antecedem o envio ao Robo Demo. A coluna
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
| FLOW-012 | Graficos configurados para 22/07 ainda mostravam resultados realizados em 21/07 no Brasil e legenda `desde indice` | O filtro comparava somente a data UTC de fechamento, aceitava horario desconhecido e depois aplicava outro corte por indice | Historico MT5, aba Relatorio, graficos M1-M6 e testes | A janela patrimonial converte o fechamento MT5 para `America/Sao_Paulo`; resultado anterior fica fora; horario desconhecido nao entra; nao existe segundo corte por indice |
| FLOW-013 | A tabela M2-M5 podia mostrar sinal/zonas herdados do M1 e duas colunas `Plano` sem revelar o gargalo real | A projecao clonava a linha M1 sem limpar campos operacionais e uma chave `Zona` duplicada sobrescrevia o status do gate | Snapshot compartilhado, projecao M1-M5, tabela MT5 Forex e testes | Cada modelo limpa campos herdados, usa sua decisao compartilhada e expoe um funil unico; `Envio` mostra `PRONTO` ou o motivo do gargalo sem executar logica propria |
| FLOW-014 | O seletor e o historico ainda tratavam M6 como espelho inativo do M5 depois da recuperacao do setup original | Identificador, visual, Robo Demo e comentario MT5 nao compartilhavam o novo contrato | Configuracao M6, DashboardService, snapshot, UI, Robo Demo, provider, testes e documentos | M6 e independente, usa `MODELO_6_TREND_MOMENTUM_ORIGINAL`, candle M1 fechado, risco maximo entre 2 ATR e 0,10% do preco, TP RR2 fixo e provider Demo |
| FLOW-015 | O cartao M6 mostrava 13 operacoes e `-12,80`, enquanto a linha ja desenhava 20 operacoes e `100,61` | Elementos sem identidade explicita eram reaproveitados durante rerenders do fragmento do Relatorio | Cache do Relatorio, fragmento Streamlit, cartoes e graficos M1-M6 | Cartao, contagem e pontos devem nascer de um snapshot unico; painel e grafico recebem chave por modelo e versao dos dados, sem nova leitura MT5 |
| FLOW-016 | M6 moveu SL apesar de ter sido concebido para reproduzir entrada e saida fixas do marco zero | Ao criar o adaptador M6, a configuracao de entrada ALPHA001 recebeu por heranca o wrapper global `BETA001_PROTECT_ONLY_V1` e `DYNAMIC_POSITION_MANAGER` | Configuracao M6, Trade Plan, reconstrucao de snapshots, Position Manager, UI, testes e documentacao | M6 declara `BETA001_FIXED_SL_TP_RR2_V1`; snapshots antigos sao identificados pelo modelo/origem e bloqueados antes de qualquer leitura ou comando de gestao |
| FLOW-017 | M1 recebia SL/TP do Lab, mas o runtime ainda podia mover o SL | `FIXED_STOP` era reinterpretado como `DYNAMIC_POSITION_MANAGER` depois da abertura | Research Lab, Trade Plan M1, registro de execucao, Position Manager, UI, testes e documentacao | M1 publica `RESEARCH_FIXED_SL_TP`; snapshots M1 antigos sao bloqueados pela identidade `MODELO_1_ALPHA_ATUAL`; o PM somente audita |

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
- M2-M5 usam exatamente Alpha, TF, filtros e SL/TP do manifesto promovido;
- M6 aparece, calcula somente com candles ja carregados e envia exclusivamente
  ao MT5 Demo quando selecionado, armado e com todos os gates aprovados;
- Position Manager continua administrando posicoes abertas fora da aba MT5;
- Relatorio nao participa da decisao nem torna o ciclo leve pesado.
- Lab e Replay permanecem deterministas mesmo durante rollover vivo do MT5.
- a mesma colecao de candles nao e normalizada novamente enquanto o candle
  fechado e o timestamp da barra atual permanecerem iguais.

## Documentos Complementares

- `docs/ARCHITECTURE.md`
- `docs/LAB_FOREX_MT5_CONTRACT.md`
- `docs/LAB_FOREX_MT5_FLOW.md`
- `docs/architecture/TRADE_ENTRY_EXIT_CONTRACT_AUDIT.md`
- `docs/architecture/POSITION_MANAGER_OFFICIAL_CONTRACT.md`
- `docs/architecture/OPERATIONAL_MODEL_CREATION_PROTOCOL.md`
- `docs/RUNTIME_AND_ARTIFACTS.md`
