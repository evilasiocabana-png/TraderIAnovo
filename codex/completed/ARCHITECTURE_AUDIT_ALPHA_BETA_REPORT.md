# ARCHITECTURE_AUDIT_ALPHA_BETA_REPORT

Status: completed
Tipo: auditoria arquitetural read-only
Data: 2026-07-10
Repositorio alvo: TraderIAnovo
Missao origem: codex/inbox/ARCHITECTURE_AUDIT_ALPHA_BETA.md

## Resumo executivo

A arquitetura atual ja separa, na pratica, tres responsabilidades principais:

1. O Research Lab e o plano de pesquisa definem entrada, stop inicial, RR e alvo inicial.
2. O Robo Demo apenas materializa esse plano em uma ordem MT5.
3. O Position Manager administra a posicao depois de aberta, sem recalcular o Lab.

O ponto que ainda nao esta formalmente separado e a identidade das estrategias:

- Alpha hoje identifica majoritariamente a logica de entrada/modelo vencedor.
- A saida/gestao ainda aparece como `stop_management`, `exit_setup`, `exit_policy`, `dynamic_exit_*` e `exit_model`, sem um identificador unico de Beta.

Conclusao: o menor ajuste arquitetural futuro e introduzir `beta_id` como metadado opcional, com valor inicial `LEGACY_CURRENT_EXIT`, sem alterar comportamento operacional. Isso permite rastrear a saida sem vincular a aprovacao da entrada a uma "melhor saida" predefinida.

## Contrato atual observado

### Onde o plano nasce

O plano institucional nasce em `research/mt5_research_trade_plan.py`.

Evidencias:

- `MT5ResearchTradePlanInput` recebe `symbol`, `timeframe`, `decision`, `entry_signal_status`, `entry_price`, `atr`, `active_model`, `atr_stop_factor`, `research_risk_reward` e `stop_management` (`research/mt5_research_trade_plan.py:69`).
- `MT5ResearchTradePlan` guarda `entry_price`, `stop`, `target`, `risk_reward`, `stop_multiplier`, `exit_model` e `stop_management` (`research/mt5_research_trade_plan.py:93`).
- `MT5ResearchTradePlanEngine.build_plan()` cria o plano somente quando ha `SINAL_TEORICO`, direcao `BUY/SELL` e preco de entrada valido (`research/mt5_research_trade_plan.py:143`).
- O stop inicial e o alvo sao calculados por distancia de ATR e RR (`research/mt5_research_trade_plan.py:186`).
- O proprio texto do plano confirma que a saida dinamica sera decidida pelo Position Manager em tempo de posicao (`research/mt5_research_trade_plan.py:272`).

Leitura arquitetural: o plano de entrada nao deve depender de pesquisa de "melhor saida". A saida aparece como hint/compatibilidade, nao como criterio de aprovacao do trade.

### Como o plano chega ao dashboard

O `DashboardService` monta a linha Forex a partir do modelo ativo do Lab, calcula entrada teorica, gera o plano e anexa campos de leitura dinamica.

Evidencias:

- O Lab fornece `active_model`, `lab_parameters`, `lab_alpha_id`, timeframe e parametros vencedores (`application/dashboard_service.py:5006`, `application/dashboard_service.py:5055`).
- A linha carrega `research_plan_stop`, `research_plan_target`, `research_plan_risk_reward`, `research_plan_exit_model` e `research_plan_stop_management` (`application/dashboard_service.py:5133`).
- A mesma linha carrega campos `dynamic_exit_policy`, `dynamic_exit_action`, `dynamic_exit_reason`, `dynamic_exit_candidate_stop` e `dynamic_exit_allowed_to_execute_demo` (`application/dashboard_service.py:5151`).
- O ViewModel ja possui `lab_alpha_id` e campos `dynamic_exit_*`, mas nao possui `beta_id` (`application/dashboard_view_model.py:204`, `application/dashboard_view_model.py:220`, `application/dashboard_view_model.py:310`).

Leitura arquitetural: existe espaco natural para transportar `beta_id` na linha Forex, junto dos campos de `research_plan_*` e `dynamic_exit_*`, sem mudar decisao operacional.

### Como o Robo Demo executa

O Robo Demo recebe `MT5DemoTradePlan` e cria `ExecutionOrder`.

Evidencias:

- `MT5DemoTradePlan` materializa `entry_price`, `stop`, `target`, `risk_reward`, `exit_model` e `stop_management` (`application/mt5_demo_robot_service.py:85`).
- `evaluate_once()` valida kill switch, candle novo, direcao, regime, bloqueios temporais/macro e plano valido antes de enviar ordem (`application/mt5_demo_robot_service.py:131`).
- A ordem usa exatamente `entry_price`, `stop` e `target` do plano (`application/mt5_demo_robot_service.py:233`).
- `exit_setup` e `exit_policy` recebem `trade_plan.stop_management` apenas como metadado da ordem (`application/mt5_demo_robot_service.py:242`).
- `ExecutionOrder` possui `plan_identity`, `entry_setup`, `exit_setup` e `exit_policy`, mas nao possui `alpha_id` nem `beta_id` explicitos (`domain/contracts/execution_order.py:7`).

Leitura arquitetural: o melhor ponto para registrar `beta_id` em execucao futura e `ExecutionOrder`, mas como campo opcional/backward-compatible. O Robo nao deve ganhar inteligencia de saida.

### Como a ordem chega ao MT5

O provider MT5 envia ordem com `TRADE_ACTION_DEAL`, `sl` e `tp`.

Evidencias:

- `_request()` monta a ordem MT5 com `action`, `symbol`, `volume`, `type`, `price`, `sl`, `tp`, `magic` e comentario (`infrastructure/execution/mt5_demo_execution_provider.py:915`).
- A modificacao de stop usa `TRADE_ACTION_SLTP`, preservando o TP (`infrastructure/execution/mt5_demo_execution_provider.py:438`, `infrastructure/execution/mt5_demo_execution_provider.py:576`).
- O provider tambem possui `close_position()` para fechamento, mas a chamada depende do Position Manager e das configuracoes (`infrastructure/execution/mt5_demo_execution_provider.py:143`).

Leitura arquitetural: o MT5 nao decide estrategia. Ele recebe ordem inicial e, depois, pode receber modificacao de SL ou fechamento quando autorizado.

### Como o Position Manager funciona hoje

O Position Manager acompanha posicoes abertas e calcula decisoes depois que a posicao existe.

Evidencias:

- `PositionManagerService` tem `assisted_execution_enabled=False` e `early_exit_enabled=False` por padrao (`application/position_manager_service.py:225`).
- `manage_plan()` exige plano valido e posicao aberta antes de agir (`application/position_manager_service.py:268`).
- Se nao houver posicao, retorna `POSITION_ABSENT`; se faltar preco, stop ou dados, preserva o SL (`application/position_manager_service.py:268`).
- `_decide()` pode gerar `HOLD_POSITION`, `PROTECT_POSITION` ou, se `early_exit_enabled` estiver ativo e confirmado, `FULL_EXIT` (`application/position_manager_service.py:558`).
- A saida antecipada so e considerada quando `early_exit_enabled` esta ativo (`application/position_manager_service.py:574`).
- `_dynamic_candidate_stop()` escolhe protecao por cenario e nao exige que a saida tenha sido predefinida no plano (`application/position_manager_service.py:677`).
- Acoes `EARLY_EXIT` e `FULL_EXIT` existem no conjunto suportado, mas nao nascem automaticamente ativas (`application/position_manager_service.py:984`).

Leitura arquitetural: o Position Manager ja esta mais proximo de um gestor pos-entrada do que de uma saida fixa. A saida antecipada precisa continuar desligavel e auditavel.

## Alpha atual

Alpha hoje representa a familia/configuracao do Lab que gerou a entrada.

Campos observados:

- `lab_alpha_id` no ViewModel Forex (`application/dashboard_view_model.py:220`).
- `alpha_id` no ViewModel de cenario (`application/dashboard_view_model.py:443`).
- `lab_alpha_id` populado a partir de `lab_parameters.get("alpha", "ALPHA001")` (`application/dashboard_service.py:5055`).
- `alpha_id` enviado nos metadados de auditoria antes da ordem (`application/mt5_demo_robot_service.py:245`).

Contrato recomendado:

```text
alpha_id = identidade da logica de entrada do Research Lab
alpha_version = versao da configuracao/definicao dessa entrada
```

Alpha nao deve significar saida.

## Beta proposto

Beta deve representar a politica/arquitetura de gestao da posicao apos entrada, sem decidir a entrada.

Contrato recomendado:

```text
beta_id = identidade da gestao de saida/posicao
beta_version = versao da politica de gestao
beta_mode = LEGACY | READ_ONLY | PROTECT_ONLY | DYNAMIC
```

Valor inicial obrigatorio:

```text
beta_id = LEGACY_CURRENT_EXIT
```

Esse Beta legado deve significar exatamente o comportamento atual:

- entrada aprovada pelo Lab;
- stop inicial calculado pelo plano;
- alvo inicial por RR;
- Robo Demo abre a posicao;
- Position Manager acompanha apenas depois da posicao aberta;
- alteracao de SL somente se habilitada e mais protetiva;
- early/full exit desligado por padrao;
- nenhuma estrategia de saida escolhida pelo MT5;
- nenhum recalculo pesado do Lab no ciclo leve.

## Menor ponto de insercao de alpha/beta

### Ponto 1: plano de pesquisa

Adicionar campos opcionais em `MT5ResearchTradePlan`:

```python
alpha_id: str = "ALPHA001"
beta_id: str = "LEGACY_CURRENT_EXIT"
beta_version: str = "1.0"
```

Motivo: o plano e a origem documental do ciclo. Campos opcionais preservam snapshots antigos.

### Ponto 2: ViewModel Forex

Adicionar `beta_id` ao `DashboardMT5ForexSignalRowViewModel`.

Motivo: a aba Forex e a tabela de entrada precisam mostrar a rastreabilidade Alpha -> Beta sem alterar envio.

### Ponto 3: ExecutionOrder

Adicionar `alpha_id` e `beta_id` como campos opcionais em `ExecutionOrder`.

Motivo: isso leva rastreabilidade ate o provider/MT5 audit log sem mudar `sl`, `tp`, `volume` ou `side`.

### Ponto 4: auditoria/relatorio

Adicionar colunas no historico:

```text
Alpha entrada
Beta gestao
Modo Beta
Acao Position Manager
Motivo Position Manager
```

Motivo: permitir busca no GitHub e auditoria posterior sem depender de prints.

## Compatibilidade com o comportamento antigo

Para nao quebrar o sistema:

- `beta_id` deve ser opcional.
- Ausencia de `beta_id` deve resolver para `LEGACY_CURRENT_EXIT`.
- `stop_management` deve continuar sendo lido.
- `exit_setup` e `exit_policy` devem continuar recebendo `stop_management` ate a migracao completa.
- `dynamic_exit_*` deve permanecer read-only quando a execucao estiver desligada.
- Nenhum snapshot antigo deve ser invalidado por ausencia de Beta.

## Compatibilidade com Beta dinamico M1 futuro

A futura Beta M1 dinamica deve entrar como sensor de gestao, nao como motor de entrada.

Regra sugerida:

```text
Alpha decide entrada e plano inicial.
Beta observa M1 depois que existe posicao aberta.
Beta pode recomendar protecao ou saida.
Execucao depende dos gates do Position Manager.
```

Exemplo futuro:

```text
beta_id = BETA_M1_EMA14_MARKET_SENSOR
beta_mode = READ_ONLY ou PROTECT_ONLY
```

Guardrail: EMA14/M1 nao deve fechar posicao sozinho. Deve gerar evidencia para o Position Manager, que decide por estado, contexto, R, stop atual, preco atual e seguranca operacional.

## Lacunas encontradas

1. Nao existe `beta_id` formal.
2. `stop_management`, `exit_setup`, `exit_policy`, `exit_model` e `dynamic_exit_policy` ainda misturam conceitos de plano, gestao e execucao.
3. O Lab ainda pode expandir variantes de `stop_management` em grid (`application/dashboard_service.py:6818`), mas o plano ja trata isso como hint/compatibilidade. Isso precisa ficar documentado para nao voltar a bloquear entrada por "melhor saida".
4. `ExecutionOrder` nao transporta Alpha/Beta diretamente.
5. O relatorio ja carrega `dynamic_exit_*`, mas nao possui identidade Beta oficial (`application/dashboard_view_model.py:664`).

## Riscos se Alpha e Beta nao forem separados

- A entrada pode voltar a depender indevidamente de uma pesquisa de saida.
- O usuario pode interpretar `stop_management` como saida predefinida, quando o Position Manager deveria decidir pelo cenario.
- Fica dificil auditar se uma perda veio da entrada, do stop inicial, do trailing, do early exit ou do regime.
- Melhorias enviadas por GPT podem mexer no modulo errado.

## Recomendacao final

Formalizar em proxima missao documental/leve:

1. `alpha_id` = entrada.
2. `beta_id` = gestao de saida/Position Manager.
3. `LEGACY_CURRENT_EXIT` = comportamento atual.
4. `stop_management` = campo legado/hint de compatibilidade.
5. Entrada nao deve ser reprovada por nao existir uma "melhor saida".
6. Position Manager decide pos-entrada, com early/full exit desligavel e rastreavel.

## Confirmacao de nao alteracao operacional

Esta auditoria nao altera codigo de producao, banco de dados, testes, configuracao MT5, Lab, Robo Demo, Position Manager ou comportamento operacional. O entregavel e somente este relatorio Markdown.
