# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-029_A_DEFINIR
```

Objetivo: definir a proxima melhoria a partir do estado operacional apos a
reparacao do ciclo do robo demo, diagnostico MT5, Forex e Relatorio.

Qualquer proxima missao nao deve:

- executar em conta real;
- abrir nova ordem;
- fechar posicao;
- alterar TP;
- executar automaticamente por ciclo;
- recalcular Lab pesado;
- apagar `.traderia`;
- mascarar falhas do provider MT5.

Para executar, coloque o pacote da proxima missao em `codex/inbox/` e solicite:

```text
Inbox.
```
