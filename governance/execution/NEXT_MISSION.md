# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-030_A_DEFINIR
```

Objetivo: definir a proxima melhoria a partir do estado operacional apos a
reparacao do ciclo do robo demo, diagnostico MT5, Forex e Relatorio.

Pendencia registrada em 2026-07-13:

- criar sentinela de velocidade do TraderIA Novo;
- medir aba Relatorios, Saida Teorica MT5, Position Manager e historico MT5;
- preservar leitura de mercado essencial do BETA002;
- impedir que snapshot pesado do Lab volte ao ciclo leve;
- manter tabelas grandes paginadas e rastrear qualquer regressao de lentidao.

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
