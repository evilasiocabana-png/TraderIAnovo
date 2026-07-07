# MISSION_TIA-XXX - NOME_CURTO_DA_MELHORIA

Use este template quando uma melhoria for desenhada pelo GPT e executada pelo
Codex via `codex/inbox`.

## 1. Resumo Executivo

**Objetivo:**  
Descrever em uma frase o resultado esperado.

**Problema observado:**  
Explicar o comportamento atual, onde aparece e por que precisa mudar.

**Resultado desejado:**  
Explicar como o sistema deve se comportar depois da mudanca.

## 2. Area Impactada

Marcar uma ou mais areas:

- [ ] `GOVERNANCE_ONLY`
- [ ] `TAB_FOREX_MT5`
- [ ] `TAB_LAB`
- [ ] `TAB_RELATORIO`
- [ ] `MT5_VISUAL`
- [ ] `ALPHA_LIBRARY`
- [ ] `SETUP_LOGIC`
- [ ] `TRADE_PLAN`
- [ ] `DEMO_EXECUTION`
- [ ] `REPORT_AUDIT`

## 3. Documentos Obrigatorios para Leitura

- `docs/SYSTEM_FLOW.md`
- `docs/APP_TABS_FLOW.md`
- `docs/OPERATIONAL_GUARDRAILS.md`
- `docs/CHANGE_PROTOCOL.md`

Adicionar conforme a area:

- Alpha/setup: `docs/ALPHA_TRACEABILITY.md`
- Setup/saida/stop: `docs/SETUP_LOGIC_TRACEABILITY.md`
- Lab-Forex-MT5: `docs/LAB_FOREX_MT5_CONTRACT.md`
- Visual MT5: `docs/MT5_VISUAL_SIGNAL_CONTRACT.md`

## 4. Escopo Autorizado

**Arquivos/pastas permitidos:**

- `CAMINHO/DO/ARQUIVO.py`

**Arquivos/pastas proibidos:**

- `.traderia/`
- `Python/`
- `.env`
- logs, bancos locais, snapshots e credenciais

**Camadas permitidas:**

- Exemplo: `application`, `docs`, `tests`.

**Camadas proibidas:**

- Exemplo: `mt5`, `risk`, `execution`, se nao forem parte da missao.

## 5. Guardrails Obrigatorios

- [ ] Nao usar `order_send()`.
- [ ] Nao habilitar operacao real.
- [ ] Nao recalcular Lab pesado dentro do ciclo leve Forex.
- [ ] Nao forcar todos os pares/timeframes para M1.
- [ ] Nao versionar runtime local, bancos, logs ou snapshots.
- [ ] Preservar app local funcionando.
- [ ] Preservar rollback por commit.

## 6. Rastreabilidade de Alpha/Setup

Preencher quando a missao tocar Lab, Alpha, setup, saida ou trade plan.

| Campo | Valor |
| --- | --- |
| Alpha afetada | `ALPHA###` ou `N/A` |
| Modelo/setup afetado | `NOME_DO_SETUP` ou `N/A` |
| Timeframe afetado | `M1/M5/M15/M30/H1/MULTI/N/A` |
| Entrada afetada | `BUY/SELL/WAIT/N/A` |
| Saida/stop management afetado | `FIXED_STOP/ATR_TRAILING_STOP/.../N/A` |
| Contrato afetado | `Lab -> Forex`, `Forex -> MT5`, `Relatorio`, `N/A` |
| Documento a atualizar | caminho |

## 7. Plano de Implementacao

1. Ler os documentos obrigatorios.
2. Confirmar `codex/processing` vazio.
3. Validar estado Git.
4. Alterar somente arquivos permitidos.
5. Executar validacao proporcional.
6. Gerar `EXECUTION_REPORT.md`.
7. Atualizar governanca.
8. Commit e push.

## 8. Validacao Obrigatoria

Escolher conforme risco:

- Documentacao/governanca: `git diff`, revisao de links e `git status`.
- UI: `python -m py_compile dashboard_app.py`.
- Application service: `python -m py_compile application/dashboard_service.py`.
- Lab/Alpha/setup: teste ou script que prove Alpha, TF e stop management.
- MT5 visual: validar JSON e campos do contrato.
- Relatorio: validar fallback sem MT5 e leitura do historico local.

Comandos especificos desta missao:

```powershell
<comando 1>
<comando 2>
```

## 9. Criterios de Aceite

- [ ] O comportamento desejado foi implementado.
- [ ] Nenhum arquivo proibido foi alterado.
- [ ] Guardrails foram respeitados.
- [ ] Validacao obrigatoria foi executada ou justificadamente registrada.
- [ ] Documentacao/rastreabilidade foi atualizada quando aplicavel.
- [ ] `codex/processing` ficou vazio ao final.
- [ ] Commit e push realizados.

## 10. Plano de Rollback

Descrever como voltar ao estado anterior.

Padrao:

```text
Reverter o commit da missao.
Nao apagar runtime local.
Nao alterar snapshots em .traderia.
```

## 11. Risco Operacional

Classificar:

- [ ] Baixo: documentacao/teste isolado.
- [ ] Medio: UI ou service sem envio MT5.
- [ ] Alto: Lab, Forex, visual MT5, trade plan ou demo execution.

Mitigacao:

- Descrever como a missao reduz risco.
