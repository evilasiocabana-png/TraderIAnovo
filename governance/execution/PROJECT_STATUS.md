# Project Status

Status: pronto para fluxo de inbox.

## Estado Atual

- Estrutura `codex/` criada.
- Estrutura `governance/execution/` criada.
- Templates de missao e relatorio criados.
- Guardrails read-only documentados.
- `MISSION_INDEX.md` controla historico resumido das missoes.
- Camada 1 de governanca operacional criada em `docs/`.
- Nenhuma funcionalidade de produto foi criada por esta infraestrutura.

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
