# Project Status

Status: pronto para fluxo de inbox.

`M24_CONTRACT=M24_SETUP_V19_20260823; SHA256=d918353322bc17fd17e1c7d0ba47272cf19431ef2c60d9cd1686829f2802c05f`

`M25_CONTRACT=M25_XAU_SOURCES_V6_20260820; FINGERPRINT=d0d758099058ffde`

`M26_CONTRACT=M26_SMART_MONEY_V1_20260825; FINGERPRINT=1a5af96d8383950d`

## Contrato vigente M26 - 2026-08-25

- rota independente em `XAUUSD/M5`, sem substituir o M25;
- 200 candles fechados mais candle atual somente informativo;
- confluencia obrigatoria de estrutura, sweep, BOS/deslocamento, FVG, OB e reteste;
- entrada a mercado, SL estrutural, RR minimo 2 e lote Demo `0,10`;
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
