# TraderIA Novo - Guardrails Operacionais

Este documento define limites para missoes GPT/Codex. Ele existe para preservar
o estado operacional atual.

## Regras absolutas

- Nao usar `order_send()` sem missao formal de operacao real.
- Nao criar broker operacional sem decisao explicita.
- Nao versionar credenciais, `.env`, logs, `.pid`, `.traderia/`, bancos locais
  ou snapshots grandes.
- Nao apagar artefatos locais de runtime sem autorizacao.
- Nao mover o local da aplicacao local.
- Nao alterar simultaneamente Lab, Forex, Relatorio e MT5 Visual sem missao de
  arquitetura aprovada.

## Regras do Lab

- Lab pesado roda sob demanda.
- Ciclo leve Forex nao recalcula Alpha001-Alpha015.
- Timeframe vencedor vem do Lab e deve ser preservado.
- Melhor saida/stop management vem do Lab.
- Toda alteracao de Alpha deve atualizar rastreabilidade.

## Regras do Forex MT5

- Forex MT5 usa leitura leve e parametros ja calculados.
- O refresh leve pode atualizar preco/candles, mas nao deve iniciar pesquisa
  pesada.
- O ciclo automatico deve respeitar janela operacional configurada.
- Finais de semana/feriados devem bloquear checagens quando aplicavel.
- O estado online/offline deve ser claro para o usuario.

## Regras do visual MT5

- Ativos sem posicao aberta devem ficar limpos por padrao.
- Ativos posicionados devem mostrar informacao util: entrada, stop, alvo/saida
  e candle de entrada quando disponivel.
- Textos longos no grafico devem ser evitados.
- Mudanca no schema do JSON visual exige atualizacao de contrato.

## Regras do Relatorio

- Relatorio e auditoria/read-only.
- Relatorio pode acionar atualizacao/auditoria quando solicitado, mas nao deve
  recalcular Lab pesado sem missao explicita.
- Relatorio nao decide Alpha, setup ou timeframe.

## Regras de GitHub e inbox

Toda melhoria deve entrar como missao em:

```text
codex/inbox/MISSION_<ID>_<NOME>/
  README.md
  MISSION.md
  CODEX.md
  ACCEPTANCE.md
```

Antes de executar:

1. ler `governance/execution/EXECUTION_STATE.json`;
2. confirmar `codex/processing` vazio;
3. validar escopo permitido;
4. declarar arquivos que podem ser alterados;
5. declarar rollback.

Depois de executar:

1. criar `EXECUTION_REPORT.md`;
2. mover para `codex/completed` ou `codex/failed`;
3. atualizar `governance/execution`;
4. commitar e enviar ao GitHub.

## Validacao minima por tipo de missao

| Tipo | Validacao minima |
| --- | --- |
| Documentacao/governanca | `git diff`, revisao de links e status limpo |
| UI Streamlit | `python -m py_compile dashboard_app.py` |
| Application service | `python -m py_compile application/dashboard_service.py` e teste especifico |
| Lab/Alpha/setup | teste unitario ou script que prove TF, Alpha e stop management |
| MT5 visual | validar JSON gerado e compatibilidade do indicador |
| Relatorio/auditoria | validar leitura local e fallback sem MT5 |

## Criterio de rollback

Toda missao deve ser reversivel por commit. Mudancas que dependam de artefatos
locais devem declarar como preservar o estado anterior antes da execucao.
