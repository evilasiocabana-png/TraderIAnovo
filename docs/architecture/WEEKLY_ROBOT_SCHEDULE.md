# Agenda Semanal do Robo Demo

Data: 2026-07-31
Timezone: `America/Sao_Paulo`
Status: regra operacional obrigatoria

## Janela

```text
Domingo 23:30 BRT -> Sexta 17:30 BRT: robo sempre ligado
Sexta 17:30 BRT -> Domingo 23:30 BRT: robo desligado e conta Demo zerada
```

Os limites sao inclusivos: sexta exatamente 17:30 ja pertence a janela
fechada; domingo exatamente 23:30 ja pertence a janela operacional.

## Execucao

- Um thread semanal independente inicia mesmo quando o robo esta offline.
- Dentro da janela, estado persistido OFF e corrigido para ON.
- Fora da janela, estado persistido ON e corrigido para OFF.
- Ao fechar a janela, todas as posicoes abertas da conta MT5 Demo sao
  encerradas pela porta oficial `DemoExecutionService.close_position`.
- O provider continua bloqueando conta real.
- A verificacao de conta zerada e idempotente: sem posicao, nenhuma ordem e
  enviada; com posicao remanescente, o agendador tenta novamente.
- A regra usa `ZoneInfo`, sem horario UTC fixo, e acompanha mudancas do fuso de
  Brasilia definidas pelo sistema operacional.

## Persistencia

- Comando do robo: `.traderia/mt5_demo_robot_online_state.json`.
- Auditoria semanal: `.traderia/weekly_robot_schedule_state.json`.
- Fechamentos: `.traderia/mt5_stop_management.jsonl`.

O estado semanal registra janela, proxima transicao, ultima acao, quantidade
encontrada, fechada, rejeitada e ainda aberta.

## Leveza

- O relogio e verificado a cada 10 segundos.
- Fora da janela, a conta e consultada no maximo a cada 60 segundos quando ja
  esta zerada.
- Se houver posicao remanescente, o retry volta ao intervalo de 10 segundos.
- Nenhum Lab, Replay ou calculo de indicadores e executado por esta agenda.

## Guardrails

- A agenda atua somente quando `TRADERIA_DEMO_EXECUTION_ENABLED=1`.
- Pode ser desabilitada apenas por manutencao explicita com
  `TRADERIA_WEEKLY_ROBOT_SCHEDULE_ENABLED=0`.
- Dentro da janela aberta, desarme manual e temporario: a agenda rearma.
- Fora da janela, armamento manual e temporario: a agenda desarma e zera.
- O fechamento nunca recalcula Lab, Trade Plan, stop ou alvo.
- O ciclo semanal nao interfere na leitura de mercado nem no Position Manager
  durante a janela operacional.
