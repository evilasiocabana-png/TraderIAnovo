# MISSION_TIA-031 — Auditar Safe Mode MT5 e stop móvel

## Objetivo

Produzir uma auditoria documental sobre o aviso da UI:

```text
MT5 Safe Mode ativo: usando leitura simples e heurística. Pesquisa Quantitativa temporariamente desativada.
```

A auditoria deve responder se, nesse modo, o TraderIAnovo ainda consegue acompanhar o mercado para fins de stop móvel, trailing, break-even e saída dinâmica.

Esta missão não deve alterar código operacional. Deve apenas analisar e documentar.

---

## Pergunta principal

Com o Research Quantitativo desativado pelo Safe Mode, o sistema ainda consegue:

1. Ler preço e candles do MT5?
2. Atualizar dados mínimos de mercado?
3. Alimentar o acompanhamento de posição?
4. Preservar o último plano válido do Lab?
5. Manter stop móvel baseado em mercado?
6. Evitar recalcular estratégia durante uma posição aberta?

---

## Hipótese arquitetural desejada

O desenho esperado é:

```text
Research Lab
    ↓
Gera plano inicial:
- entrada
- stop inicial
- alvo
- política de saída
- modelo de gestão

Depois da posição aberta:

Position Manager
    ↓
Lê mercado continuamente
    ↓
Atualiza acompanhamento:
- stop móvel
- trailing
- break-even
- saída dinâmica
```

O stop móvel não deve depender de recalcular o Research Lab a cada ciclo. O Lab gera o plano; o Position Manager acompanha o mercado usando o plano salvo.

---

## Tarefa 1 — Mapear dependências do stop móvel

Localizar no repositório os componentes relacionados a:

- stop móvel;
- trailing;
- break-even;
- saída dinâmica;
- Position Manager;
- dynamic exit;
- SL assistido demo;
- acompanhamento de posição.

Responder:

- Quais dados o stop móvel usa?
- Ele usa apenas leitura de mercado?
- Ele consulta o Research Lab durante a posição aberta?
- Ele depende de `mt5_heuristic_research`?
- Ele depende de `mt5_forex_signals`?
- Ele depende de plano salvo?

---

## Tarefa 2 — Auditar Safe Mode

Investigar o que acontece quando `mt5_safe_mode=True`.

Responder:

- Quais leituras continuam ativas?
- Quais campos continuam preenchidos?
- Quais campos ficam ausentes, zerados ou congelados?
- `last_price` continua atualizando?
- `last_candle_time` continua atualizando?
- ATR continua disponível?
- tendência, momentum e volatilidade continuam disponíveis?
- sinais continuam em modo heurístico?
- saída dinâmica recebe insumos mínimos?

---

## Tarefa 3 — Separar plano inicial de acompanhamento

Confirmar se existe separação real entre:

```text
Lab / Research = gera plano
Position Manager = acompanha posição
```

Se essa separação não estiver clara, propor ajuste arquitetural em documentação, sem implementar.

---

## Tarefa 4 — Critérios mínimos para stop móvel em Safe Mode

Criar uma matriz:

| Recurso | Necessário? | Disponível em Safe Mode? | Fonte | Risco |
|---|---|---|---|---|
| preço atual |  |  |  |  |
| candle atual |  |  |  |  |
| ATR |  |  |  |  |
| direção da posição |  |  |  |  |
| entrada |  |  |  |  |
| stop atual |  |  |  |  |
| alvo |  |  |  |  |
| maior preço desde entrada |  |  |  |  |
| menor preço desde entrada |  |  |  |  |
| política de saída do Lab |  |  |  |  |

---

## Tarefa 5 — Classificar cenários

Classificar:

### Cenário A
Safe Mode ligado, sem posição aberta.

### Cenário B
Safe Mode ligado, posição aberta com plano válido salvo.

### Cenário C
Safe Mode ligado, posição aberta sem plano válido.

### Cenário D
Research Lab desligado, mas Market Data online.

Para cada cenário, responder:

- o que é seguro manter ativo;
- o que deve ser bloqueado;
- qual alerta deve aparecer na UI.

---

## Tarefa 6 — Propor política operacional

Propor regra documental:

```text
Safe Mode pode manter acompanhamento de posição somente se:
- houver posição aberta válida;
- houver plano operacional válido salvo;
- houver leitura de preço/candle atualizada;
- houver stop atual conhecido;
- houver política de saída definida;
- o modo de execução permitido for seguro para o ambiente atual.
```

Se qualquer requisito faltar:

```text
não atualizar stop;
manter estado atual;
exibir alerta;
registrar log.
```

---

## Entregáveis

Criar:

```text
docs/architecture/SAFE_MODE_STOP_MOVEL_AUDIT.md
docs/architecture/SAFE_MODE_POSITION_MANAGER_POLICY.md
```

Se necessário, atualizar:

```text
docs/architecture/RUNTIME_PRESERVATION_POLICY.md
```

---

## Guardrails

Não alterar código operacional.
Não alterar lógica de entrada, saída, Lab, Position Manager, stop móvel, trailing, break-even, proteção de ambiente ou Runtime Guard.

---

## Resultado esperado

O relatório deve responder claramente:

```text
Pode usar stop móvel em Safe Mode? SIM / NÃO / DEPENDE
Condições obrigatórias:
...
Riscos:
...
Recomendação:
...
```
