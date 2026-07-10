# Auditoria do Contrato de Entrada, Saida e Gestao de Posicao

Data: 2026-07-08
Projeto: TraderIA Novo
Escopo: Research Lab, Trade Plan, Robo Demo, Position Manager, saida dinamica e Relatorio.

Nota de consolidacao: este documento descreve o estado atual auditado. A referencia oficial consolidada para futuras implementacoes e `docs/architecture/POSITION_MANAGER_OFFICIAL_CONTRACT.md`.

## Objetivo

Mapear o contrato operacional atual sem alterar codigo. Esta auditoria responde quem decide entrada, stop inicial, RR, alvo, politica de saida, gestao de stop e eventual fechamento antecipado.

## Resumo Executivo

O fluxo atual esta dividido em quatro camadas:

```text
Research Lab
  define setup, timeframe, direcao candidata e parametros do cenario vencedor
        ↓
Trade Plan
  materializa entrada, stop inicial, RR, alvo e politica de stop management
        ↓
Robo Demo
  envia ao MT5 a ordem com entry_price, stop, target, volume e direction
        ↓
Position Manager
  acompanha posicoes abertas e pode modificar somente SL, quando autorizado
```

O ponto mais importante: o stop inicial atual nao e um contrato fixo de RR3. O `Trade Plan` calcula o stop inicial por `ATR x multiplicador` ou distancia minima, e depois calcula o alvo multiplicando essa distancia pelo RR. Portanto, se o ATR ou `atr_stop_factor` estiver alto, o stop inicial nasce longo mesmo que o RR seja 3.

Hoje nao existe fechamento antecipado real pelo Position Manager. Existem classificacoes e recomendacoes de perda de momentum, reversao e time decay, mas elas resultam em recomendacao read-only, simulacao, ou no maximo modificacao de SL. Nao ha porta operacional de `close_position` no contrato do Position Manager/DemoExecutionService.

## Arquivos Envolvidos

- `research/mt5_research_trade_plan.py`
- `application/dashboard_service.py`
- `application/mt5_demo_robot_service.py`
- `application/demo_execution_service.py`
- `application/position_manager_service.py`
- `application/dynamic_exit_market_state_service.py`
- `application/dynamic_exit_recommendation_service.py`
- `application/dynamic_exit_demo_sl_execution_service.py`
- `infrastructure/execution/mt5_demo_execution_provider.py`
- `application/mt5_trade_audit_service.py`
- `domain/contracts/dynamic_exit.py`
- `domain/contracts/trade_audit.py`
- `tests/test_mt5_research_trade_plan.py`
- `tests/test_mt5_demo_robot_service.py`
- `tests/test_position_manager_service.py`
- `tests/test_dynamic_exit_*`
- `tests/test_mt5_demo_execution_provider.py`

## 1. O Que o Research Lab Decide Hoje

O Research Lab alimenta o Dashboard/Forex com a linha vencedora do estudo e seus parametros finais. No fluxo MT5 atual, esses parametros sao extraidos de `active_research_row.final_configuration` por `DashboardService`.

Campos decididos ou carregados a partir do Lab:

| Campo | Estado atual |
| --- | --- |
| `timeframe` | Sim. Vem da configuracao vencedora ou do timeframe ideal da linha do Lab. |
| `direction` | Indiretamente. O Lab define setup/modelo/parametros; a decisao BUY/SELL/WAIT e calculada no Forex a partir desses parametros e do candle atual. |
| `entry_price` | Nao como preco fixo final do Lab. O preco teorico vem do Forex/candle atual quando ha `SINAL_TEORICO`. |
| `stop inicial` | Indiretamente. O Lab fornece `atr_stop_factor`; o Trade Plan calcula o stop. |
| `RR` | Sim, quando `rr` esta em `final_configuration`. |
| `target` | Nao diretamente. O Trade Plan calcula target usando distancia do stop x RR. |
| `atr_stop_factor` | Sim, quando presente no cenario vencedor. |
| `stop_management` | Campo legado/hint de compatibilidade. Nao deve aprovar entrada nem predefinir saida. |
| `exit_policy` | A saida operacional passa a ser decisao dinamica do Position Manager apos posicao aberta. |

Observacao critica corrigida em 2026-07-08: `stop_management` nao deve mais misturar aprovacao de entrada com escolha de saida. O contrato novo separa plano inicial de risco e decisao dinamica de saida.

## 2. O Que o Trade Plan Faz Hoje

O `MT5ResearchTradePlanEngine` nao apenas copia o plano do Lab. Ele materializa e calcula:

```text
stop_multiplier, risk_reward = _initial_risk_parameters(...)
distance = _stop_distance(entry, atr, stop_multiplier)
target_distance = distance * risk_reward
```

Regras atuais:

- Se o Lab fornece `atr_stop_factor` e `rr`, o Trade Plan usa esses valores diretamente.
- Se o Lab nao fornece esses valores, o Trade Plan usa o risco inicial padrao configurado.
- O stop inicial e calculado por `max(ATR x multiplicador, distancia_minima_percentual)`.
- O target e calculado por `distancia_do_stop x RR`.
- O `stop_management` e preservado apenas como compatibilidade/hint; a saida nao nasce escolhida no plano.

Conclusao: o Trade Plan altera/materializa parametros. Ele nao e apenas um envelope passivo. Ele pode:

- alterar stop inicial, porque calcula a distancia;
- materializar RR inicial por parametro do Lab ou padrao conservador;
- alterar target, porque sempre calcula o alvo;
- impor ATR/multiplicador padrao de risco inicial quando os parametros do Lab estao ausentes.

## 3. O Que o Robo Demo Envia ao MT5

O `MT5DemoRobotService` recebe um `MT5DemoTradePlan` ja materializado e cria um `ExecutionOrder` com:

```text
symbol
side
quantity
entry_price
stop
target
```

O volume vem do proprio `MT5DemoRobotService.volume`, com default `0.1`.

Antes de enviar, o Robo Demo aplica gates:

- robo armado;
- candle ainda nao avaliado;
- decisao BUY/SELL;
- regime autorizado;
- direcao do regime igual a decisao;
- filtro temporal;
- bloqueio macro;
- plano valido;
- pipeline de decisao/risco;
- provider MT5 demo habilitado.

O provider MT5 usa o preco real do tick para enviar a ordem de mercado, mas preserva `sl` e `tp` vindos do plano. Portanto, nao ha recalculo de SL/TP no provider de envio.

## 4. O Position Manager Pode Fechar Antes do TP?

Hoje, nao.

O `PositionManagerService` possui contrato para:

- detectar posicao aberta;
- ler preco atual;
- calcular candidato de SL;
- validar se o novo SL melhora risco;
- chamar `modify_position_sl`.

Ele nao possui metodo operacional para:

- `close_position`;
- `exit_order`;
- `flatten`;
- fechamento parcial;
- fechamento total antes do TP.

O provider MT5 tambem tem porta explicita de `modify_demo_position_stop_loss` e `modify_position_sl`, ambas orientadas a alterar somente SL via `TRADE_ACTION_SLTP`.

Existe `TRADE_ACTION_DEAL` no provider, mas no fluxo atual ele e usado para abrir ordem nova, nao para fechar posicao existente.

## 5. Position Manager Move SL ou Tambem Fecha?

Move somente SL.

Politicas atualmente suportadas pelo Position Manager:

- `BREAK_EVEN`
- `ATR_TRAILING_STOP`
- `MARKET_AWARE_STOP_PROTECTION`
- `VOLATILITY_STOP_PROTECTION`
- `MOMENTUM_WEAKNESS_STOP_TIGHTENING`
- `STRUCTURE_BASED_STOP_PROTECTION`

Politicas nao suportadas, como `FULL_EXIT`, sao bloqueadas como acao nao suportada.

Condicoes obrigatorias antes de mover:

- posicao aberta existe;
- plano esta `PLANO_VALIDO`;
- stop atual existe;
- preco atual existe;
- politica gera candidato;
- candidato e mais protetivo;
- candidato esta do lado correto do mercado;
- `assisted_execution_enabled=True`.

Se a flag estiver desligada, ele calcula o candidato, registra auditoria e preserva o SL.

## 6. BREAK_EVEN e ATR_TRAILING_STOP Nascem Ativos ou Futuros?

Eles nao devem nascer ativos no Trade Plan. Quando `stop_management` aparece, ele deve ser tratado apenas como hint legado de compatibilidade.

Porem, ha duas camadas diferentes:

1. No Trade Plan, `stop_management` nao aprova entrada nem predefine saida.
2. No Position Manager, a saida e decidida dinamicamente pelo estado da posicao e so executa se houver posicao aberta e se `dynamic_exit_demo_sl_assisted_execution_enabled` estiver ligada.

Hoje nao existe campo explicito separando:

```text
runtime_exit_state = OBSERVED | CANDIDATE | EXECUTED | BLOCKED
```

O controle pratico e feito por:

- existencia de posicao aberta;
- estado dinamico calculado pelo Position Manager;
- dados disponiveis;
- `dynamic_exit_demo_sl_assisted_execution_enabled`;
- retorno do Position Manager.

Lacuna historica corrigida: a saida nao deve ser aprovada junto da entrada. O runtime pode usar parametros como `atr_trailing_activation_rr`, mas a decisao final pertence ao Position Manager.

## 7. Conceitos de Fraqueza, Reversao e Saida Antecipada

Existem conceitos read-only/dinamicos:

- `REVERSAL_RISK`
- `TIME_DECAY`
- `TREND_RUNNER`
- `PROTECTED_POSITION`
- `BAD_EXECUTION_CONTEXT`
- perda de momentum via `momentum_against`
- `TIME_DECAY_EXIT_WATCH`
- `TIGHTEN_BY_MOMENTUM_LOSS`

Eles aparecem em:

- `domain/contracts/dynamic_exit.py`
- `application/dynamic_exit_market_state_service.py`
- `application/dynamic_exit_recommendation_service.py`
- testes `tests/test_dynamic_exit_*`

Mas o efeito operacional atual nao e fechamento antecipado. O sistema pode:

- recomendar read-only;
- simular/paper;
- mover SL mais protetivo em modo demo assistido;
- registrar no relatorio.

Nao ha execucao de fechamento total/parcial por fraqueza, reversao ou incapacidade provavel de atingir TP.

## 8. O Relatorio Diferencia Motivos de Saida?

Parcialmente.

O relatorio atual registra:

- politica dinamica;
- acao dinamica;
- motivo dinamico;
- confianca;
- estado de mercado;
- R atual;
- stop candidato;
- se execucao demo e permitida;
- acao executada;
- resultado final.

Mas o relatorio nao diferencia de forma robusta e final:

- TP;
- SL;
- break-even;
- trailing;
- fechamento antecipado por fraqueza;
- fechamento manual;
- fechamento assistido.

O servico `MT5TradeAuditService` retorna basicamente `POSICAO_ABERTA` ou `SEM_POSICAO` no contrato read-only. Ja a tela do dashboard tem campos extras, mas a semantica de motivo final de fechamento ainda nao esta consolidada no contrato de auditoria.

## 9. Contrato Final Ideal

Contrato recomendado para evitar distorcao operacional:

```text
Research Lab
  decide:
    - setup/modelo
    - timeframe
    - direcao candidata
    - stop inicial ou regra de stop inicial
    - RR inicial
    - politica de saida pos-entrada
    - parametros da politica

Trade Plan
  materializa sem distorcer:
    - entry_price
    - initial_stop
    - initial_rr
    - initial_target
    - post_entry_exit_policy
    - activation_condition

Robo Demo
  executa somente abertura:
    - direction
    - volume
    - entry
    - initial_stop
    - initial_target

Position Manager
  atua somente depois da posicao aberta:
    - le posicao/preco/ATR/momentum/estrutura
    - ativa politica pos-entrada quando condicao for atingida
    - move SL somente se proteger mais
    - opcionalmente, no futuro, fecha antes do TP por contrato explicito

Relatorio
  audita:
    - plano inicial
    - stop atual
    - politica pos-entrada
    - estado da politica
    - motivo real da saida
```

Campos sugeridos para contrato futuro:

```text
initial_stop_policy
initial_stop
initial_risk_distance
initial_rr
initial_target
runtime_exit_mode
runtime_exit_state
runtime_exit_hints
runtime_exit_activation_r
current_stop
candidate_stop
stop_move_reason
exit_permission
early_exit_policy
early_exit_action
early_exit_reason
final_exit_reason
```

## 10. Testes Existentes

Cobertura encontrada:

- Nascimento do Trade Plan:
  - `tests/test_mt5_research_trade_plan.py`
  - cobre stop por ATR, RR, target, fallback, BUY/SELL, plano invalido.

- Envio pelo Robo Demo:
  - `tests/test_mt5_demo_robot_service.py`
  - cobre envio de `entry_price`, `stop`, `target`, `risk_reward`, candle novo e gates.

- Provider MT5 Demo:
  - `tests/test_mt5_demo_execution_provider.py`
  - cobre envio de ordem e alteracao de SL via `TRADE_ACTION_SLTP`.

- Position Manager:
  - `tests/test_position_manager_service.py`
  - cobre BUY/SELL trailing, break-even, sem plano, sem posicao, sem ATR, nao afastar stop, default execucao desligada, politicas dinamicas de protecao e auditoria.

- Dynamic Exit:
  - `tests/test_dynamic_exit_market_state_service.py`
  - `tests/test_dynamic_exit_recommendation_service.py`
  - `tests/test_dynamic_exit_simulation_service.py`
  - `tests/test_dynamic_exit_*_authorizer.py`
  - cobre estados, recomendacoes, simulacao e autorizadores read-only/demo.

Lacunas de testes:

- contrato explicito de stop inicial fixo RR3;
- separacao entre `initial_stop_policy` e `post_entry_exit_policy`;
- ativacao de trailing apenas apos condicao, por exemplo +1R;
- uso real de `atr_trailing_activation_rr` no Position Manager;
- fechamento antecipado por fraqueza/reversao/time decay;
- motivo final de saida distinguindo TP, SL, BE, trailing, manual e early exit;
- garantia de que o Robo Demo nunca recebe stop movel como stop inicial quando o contrato exigir stop fixo.

## Riscos Atuais

1. Stop inicial pode nascer longo por ATR/multiplicador, mesmo com RR3.
2. `stop_management` mistura politica do Lab, gestao futura e exibicao de saida dinamica.
3. Falta estado formal para politica pendente/ativa/executada.
4. `atr_trailing_activation_rr` existe no payload, mas nao esta claramente aplicado no Position Manager.
5. O Relatorio ainda nao tem taxonomia final de motivo de fechamento.
6. Fechamento antecipado existe como ideia/recomendacao, mas nao como capacidade operacional.

## Conclusao

O sistema atual esta seguro no sentido de nao fechar posicao antes do TP e nao mover SL quando a flag assistida esta desligada. O problema arquitetural e outro: o stop inicial e a politica pos-entrada ainda estao acoplados demais.

Para chegar ao comportamento desejado, o proximo passo deve ser uma missao de contrato, nao de execucao:

```text
Separar Stop Inicial Fixo/RR3 de Gestao Movel Pos-Entrada
```

Essa missao deve criar campos explicitos para stop inicial e politica pos-entrada, sem mudar ainda o comportamento de envio real. Depois disso, uma segunda missao pode alterar o Robo Demo e o Position Manager para respeitar o novo contrato.
