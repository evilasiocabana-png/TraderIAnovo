# MISSION_TIA-032 - Implementar Position Manager Stop Movel Real

## Objetivo

Implementar no TraderIA Novo o stop movel real via Position Manager, separando entrada de gestao de posicao.

## Escopo

- Criar Position Manager para acompanhar posicoes abertas.
- Detectar posicao aberta no MT5.
- Carregar Trade Plan valido salvo.
- Ler preco atual e ATR.
- Calcular break-even.
- Calcular ATR trailing stop.
- Preservar stop atual quando nao houver condicao segura.
- Nunca afastar stop contra o trader.
- Enviar atualizacao de SL ao MT5 apenas quando o novo stop for mais protetivo e a configuracao de execucao assistida estiver ligada.
- Manter `dynamic_exit_demo_sl_assisted_execution_enabled=False` como default.
- Atualizar documentacao e testes.

## Guardrails

- Position Manager nao abre ordem.
- Position Manager nao fecha posicao.
- Position Manager nao altera TP.
- Position Manager nao recalcula Research Lab.
- MT5DemoRobotService continua responsavel por entrada.
- DemoExecutionService/Provider continuam responsaveis por envio/modificacao.
- Safe Mode acompanha stop somente com preco atual, posicao aberta e Trade Plan valido.

