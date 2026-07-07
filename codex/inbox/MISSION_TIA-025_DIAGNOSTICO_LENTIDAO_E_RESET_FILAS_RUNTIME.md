# MISSION_TIA-025 — Diagnostico de Lentidao e Reset Seguro de Filas Runtime

## Objetivo

Investigar pontos de lentidao no TraderIA Novo e implementar uma acao segura no dashboard para zerar estados temporarios, caches leves, ciclos pendentes e filas operacionais nao criticas, sem apagar dados historicos, sem modificar parametros vencedores do Lab e sem enviar qualquer ordem ao MT5.

A missao deve preservar a arquitetura atual:

- Streamlit como interface principal.
- MT5 Forex em modo read-only.
- Lab/pesquisa pesada sob demanda.
- Runner externo separado quando aplicavel.
- Nenhuma execucao real autorizada.

## Problema observado

Durante atualizacao de codigo e uso do app aberto, o sistema pode ficar lento ou parecer travado. Hipoteses principais:

1. Rerun/reload do Streamlit durante alteracao de codigo.
2. Recriacao parcial de `DashboardService`.
3. Ciclo MT5/Forex automatico ativo.
4. Leitura MT5 repetida por varios pares.
5. Renderizacao de tabelas/relatorios grandes.
6. Estados antigos em `st.session_state` mantendo mensagens, caches ou diagnosticos manuais.
7. Possivel concorrencia entre ciclo em background e acao manual.

## Escopo obrigatorio

### 1. Criar diagnostico de lentidao runtime

Adicionar um diagnostico visivel no dashboard, preferencialmente em `Sistema Forex` ou em um expander lateral chamado:

```text
Diagnostico de performance / lentidao
```

O diagnostico deve exibir, quando disponivel:

- timestamp atual;
- refresh_id MT5 Forex;
- ultimo refresh MT5;
- segundos desde ultimo refresh;
- status da conexao MT5;
- `fast_refresh_duration_ms`;
- `research_refresh_duration_ms`;
- `latency_breakdown`;
- quantidade de pares carregados;
- quantidade total de candles recebidos;
- se auto-cycle UI esta ligado;
- se background cycle esta ligado;
- se o lock `MT5_FOREX_CYCLE_LOCK` esta ocupado, se for possivel verificar de forma segura;
- tamanho aproximado de chaves relevantes em `st.session_state`;
- existencia de relatorio de auditoria MT5 em cache;
- status do demo robot;
- mensagem de saude do MT5.

Nao quebrar a tela se algum campo nao existir.

### 2. Criar botao seguro de limpeza runtime

Adicionar um botao:

```text
Limpar filas e caches temporarios do runtime
```

Esse botao deve limpar apenas estado temporario da UI/runtime, por exemplo:

- diagnostico manual MT5 pendente;
- mensagens temporarias de replay;
- cache temporario de relatorio MT5 mantido em `st.session_state`;
- ultimo auto-load MT5;
- erro de initial load;
- flags temporarias de acao pendente;
- caches leves de exibicao se existirem;
- opcionalmente chamar `st.cache_data.clear()` e `st.cache_resource.clear()` se as APIs existirem.

O botao NAO pode apagar:

- arquivos `.traderia` persistentes;
- snapshots historicos;
- parametros do Lab;
- configuracoes do usuario;
- banco local;
- logs permanentes;
- historico de trades;
- tickets/posicoes MT5;
- arquivos JSON visuais usados pelo indicador, exceto se houver acao separada e explicitamente confirmada.

Depois da limpeza, mostrar mensagem clara:

```text
Filas e caches temporarios limpos. Reinicie o ciclo MT5 manualmente se necessario.
```

### 3. Criar acao opcional de pausa do auto-cycle

Se o app tiver auto-cycle UI ativo, oferecer checkbox ou botao seguro para desligar:

```text
Pausar ciclo automatico MT5 Forex
```

A acao deve apenas desligar flag de UI/session/env runtime quando possivel. Nao deve alterar arquivo de configuracao persistente sem decisao explicita.

### 4. Instrumentar tempo de renderizacao

Medir tempo de renderizacao das principais areas:

- Home;
- MT5 Forex;
- Laboratorio de Pesquisa;
- Replay;
- Historico MT5;
- Relatorios;
- Sistema Forex.

A medicao pode ser simples com `time.perf_counter()` e exibida no diagnostico quando a aba estiver ativa.

### 5. Garantir seguranca operacional

A missao deve manter estas invariantes:

- Nenhuma ordem real enviada ao MT5.
- Nenhum arquivo persistente apagado automaticamente.
- Nenhum recalculo pesado do Lab disparado pelo botao de limpeza.
- Nenhuma leitura MT5 pesada disparada ao abrir o diagnostico.
- A limpeza deve ser idempotente: clicar varias vezes nao deve quebrar o app.

## Arquivos provaveis

Priorizar alteracoes pequenas e localizadas em:

```text
dashboard_app.py
application/dashboard_service.py
application/mt5_market_data_service.py
```

Criar novos helpers se necessario, mas evitar refatoracao ampla.

## Implementacao sugerida

### Helper de diagnostico

Criar funcao em `dashboard_app.py`, por exemplo:

```python
def _runtime_performance_snapshot(service: DashboardService, data: object) -> dict[str, object]:
    ...
```

Ela deve coletar dados sem disparar leitura externa pesada.

### Helper de limpeza

Criar funcao em `dashboard_app.py`, por exemplo:

```python
def _clear_runtime_queues_and_temporary_caches() -> list[str]:
    ...
```

Ela deve remover chaves conhecidas de `st.session_state` e limpar caches Streamlit se disponiveis.

### Renderizacao

Criar funcao:

```python
def _render_runtime_performance_controls(service: DashboardService, data: object) -> None:
    ...
```

Exibir em `Sistema Forex` e/ou sidebar.

## Criterios de aceite

1. O app abre sem erro.
2. O botao de limpeza aparece no dashboard.
3. Clicar no botao nao apaga dados persistentes.
4. Clicar no botao nao dispara ordem MT5.
5. Clicar no botao nao recalcula Lab.
6. O diagnostico mostra metricas de refresh/latencia quando existem.
7. O diagnostico funciona mesmo com MT5 desconectado.
8. Testes existentes continuam passando.
9. Adicionar pelo menos um teste unitario para garantir que a limpeza remove apenas chaves temporarias esperadas, se viavel.
10. Atualizar relatorio da missao em `codex/completed` ao final.

## Validacao minima

Executar:

```powershell
python -m compileall dashboard_app.py application
python scripts\run_critical_ci.py
```

Se o CI critico nao for aplicavel no ambiente, registrar motivo no `EXECUTION_REPORT.md`.

## Resultado esperado

Ao final, o usuario deve conseguir abrir o app, acessar o diagnostico de performance e clicar em um botao para limpar filas/caches temporarios quando perceber lentidao, sem reiniciar todo o sistema e sem risco operacional.

## Proibido nesta missao

- Reorganizar pastas.
- Alterar contrato visual MT5 sem necessidade.
- Apagar `.traderia`.
- Alterar dados historicos.
- Alterar parametros vencedores do Lab.
- Ativar ordem real.
- Criar refatoracao grande fora do escopo.
