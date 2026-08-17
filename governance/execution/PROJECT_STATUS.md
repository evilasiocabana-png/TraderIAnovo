# Project Status

Status: pronto para fluxo de inbox.

## Correcao do seletor MT5 - 2026-08-17

- eliminada a colisao entre a chave Streamlit de `Todos` e a de um modelo novo
  ainda nao reconhecido por um modulo antigo mantido em memoria;
- o botao `Aplicar modelos` agora persiste a selecao em callback antes do
  rerender do fragmento, atualizando imediatamente resumo e textos M23/M24;
- chaves desconhecidas agora recebem sufixo derivado do ID canonico, sem usar
  o sufixo reservado `todos`;
- teste de interface comprovou a troca M23 -> M24 na mesma tela e restaurou o
  estado operacional anterior ao final da validacao.

## Estado Operacional M24 - 2026-08-17

- M24 criado como cesta XAUUSD/M5 independente do M23.
- Fontes fixas: M8, M10 e M18-M22.
- Entrada inicial: micropivo 1+1 + cruzamento RSI50 + fechamento alem da SMA20.
- Reentrada estrutural Stop e reentrada RSI50 a mercado permanecem separadas.
- Nenhuma rota M24 usa TP individual; alvo coletivo liquido em +US$1.000.
- SL da reentrada RSI50 acompanha o extremo do ultimo M5 apenas a favor.
- Modelo foi selecionado manualmente como unico modo operacional em 2026-08-17,
  por solicitacao do usuario; isso nao comprova robo armado nem ordem enviada.
- Fonte canonica: `docs/architecture/OPERATIONAL_MODEL_24_XAU_RSI50_BASKET.md`.

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
