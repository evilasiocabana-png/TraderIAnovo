# Execution Log

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
