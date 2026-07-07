# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-028_VALIDAR_SL_ASSISTIDO_DEMO_EM_AMBIENTE_CONTROLADO
```

Objetivo: validar o modo assistido de SL dinamico com MT5 Demo aberto, flag
ligada manualmente e uma posicao demo real controlada.

Esta missao nao deve:

- executar em conta real;
- abrir nova ordem;
- fechar posicao;
- alterar TP;
- executar automaticamente por ciclo;
- recalcular Lab pesado;
- apagar `.traderia`;
- mascarar falhas do provider MT5.

Escopo sugerido:

- ligar `dynamic_exit_demo_sl_assisted_execution_enabled` somente em ambiente Demo;
- abrir ou usar uma posicao Demo controlada;
- acionar confirmacao assistida uma unica vez;
- confirmar que request MT5 usa `TRADE_ACTION_SLTP`;
- confirmar que TP foi preservado;
- confirmar auditoria antes/depois;
- documentar rollback.

Para executar, coloque o pacote da TIA-028 em `codex/inbox/` e solicite:

```text
Inbox.
```
