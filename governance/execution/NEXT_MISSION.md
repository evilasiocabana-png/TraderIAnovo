# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-030_A_DEFINIR
```

Objetivo: auditar o M24 em paper/demo com candles novos, sem promover parametros
nem alterar suas sete fontes, confirmando entradas, SL movel e Full Exit da cesta.

Pre-condicao de interface concluida em 2026-08-17: o seletor operacional voltou
a renderizar `Todos` e M24 com chaves Streamlit distintas.

Pendencia registrada em 2026-07-13:

- criar sentinela de velocidade do TraderIA Novo;
- medir aba Relatorios, Saida Teorica MT5, Position Manager e historico MT5;
- preservar leitura de mercado essencial do BETA002;
- impedir que snapshot pesado do Lab volte ao ciclo leve;
- manter tabelas grandes paginadas e rastrear qualquer regressao de lentidao.
- registrar obrigatoriamente todo travamento aparente, congelamento de UI,
  queda do Streamlit ou reinicio manual como incidente arquitetural.

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
