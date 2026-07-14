# Execution Log

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
