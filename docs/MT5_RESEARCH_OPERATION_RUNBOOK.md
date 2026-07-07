# Runbook Operacional MT5 Research

Este runbook descreve o fluxo seguro atual entre MT5, Forex leve e Research Lab.

## Regra principal

O refresh leve do Forex/MT5 nao deve recalcular o Lab a cada ciclo.

O fluxo correto e separado em duas acoes manuais:

1. `Atualizar histórico MT5`
   - Le candles do MT5 em modo read-only.
   - Salva o historico bruto em `.traderia/mt5_research_history_snapshot.json`.
   - Nao recalcula Alpha001-Alpha015.
   - Nao envia ordens.

2. `Atualizar cálculos`
   - Usa o historico bruto salvo quando existir.
   - Recalcula o Research Lab.
   - Atualiza `.traderia/mt5_research_snapshot.json`.
   - Nao envia ordens.

## Fluxo visual

```text
MT5 online
   |
   v
Atualizar histórico MT5
   |
   v
.traderia/mt5_research_history_snapshot.json
   |
   v
Atualizar cálculos
   |
   v
.traderia/mt5_research_snapshot.json
   |
   v
Forex leve aplica parametros do Lab
   |
   v
MT5 visual / robo demo
```

## Refresh leve

O refresh leve deve:

- ler MT5;
- usar parametros ja aprovados pelo Lab;
- atualizar dashboard/JSON visual;
- respeitar posicao aberta no papel;
- evitar recalculo pesado do Lab.

O refresh leve nao deve:

- rodar pesquisa pesada automaticamente;
- baixar historico grande a cada ciclo;
- enviar ordens fora do contrato do robo demo;
- reabrir posicao se o papel ja estiver posicionado.

## Filtro de sessao Forex

O checkbox `Operar somente durante as sessoes oficiais do Forex` fica
desmarcado por padrao.

Quando desligado:

- o sistema registra alertas temporais, como rollover;
- o bloqueio temporal nao impede a decisao operacional.

Quando ligado:

- rollover, domingo fechado, sexta tardia e horarios fora da janela podem
  bloquear a decisao.

## Validacao local

Antes de subir mudancas neste fluxo:

```powershell
python scripts\run_critical_ci.py
python -m unittest tests.test_configuration_contracts
```

O `unittest discover` completo nao e a validacao padrao deste fluxo porque pode
acionar testes live/externos e travar no ambiente local.

## Rollback

Pontos de retorno conhecidos:

- `baseline-20260706`: baseline original organizado.
- `organized-20260706-final`: ponto organizado antes da esteira CI.
- tags futuras de operacao estavel devem ser criadas depois de validacao verde.

Para voltar temporariamente a uma tag:

```powershell
git checkout <nome-da-tag>
```

Para voltar o `main`, criar antes uma auditoria do impacto e nao usar
`git reset --hard` sem autorizacao explicita.
