# Execution Log

## 2026-07-17

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
- Impacto: M1, M2, M3, M4 e M5 mantem Alpha/Beta/modelo/TF originais da ordem
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
