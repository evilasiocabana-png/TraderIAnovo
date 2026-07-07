# MISSION_TIA-027 — Execucao Assistida Demo para Mover SL da Saida Dinamica

## Objetivo

Evoluir a saida dinamica apos a TIA-026 de simulacao/paper para **execucao assistida em conta Demo**, permitindo mover o SL de uma posicao existente no MT5 Demo somente quando o gate aprovar e quando houver confirmacao operacional explicita no dashboard.

Esta missao NAO autoriza conta real, NAO abre nova ordem, NAO altera TP e NAO fecha posicao.

## Dependencia obrigatoria

Executar somente depois da TIA-026 estar concluida e validada.

A TIA-026 deve entregar:

- decisao simulada de stop dinamico;
- gate de seguranca;
- auditoria;
- dashboard mostrando stop atual, stop candidato e aprovacao/rejeicao.

A TIA-027 consome essa decisao simulada aprovada e adiciona um modo assistido para modificar SL em Demo.

## Principio de seguranca

O sistema nunca pode operar em conta real nesta missao.

Antes de qualquer chamada de modificacao SL:

1. confirmar que a conta e Demo;
2. confirmar que o robo esta armado em modo Demo;
3. confirmar que `dynamic_exit_demo_sl_assisted_execution_enabled=True`;
4. confirmar que o usuario clicou explicitamente em botao de execucao assistida;
5. confirmar que a decisao simulada da TIA-026 esta aprovada;
6. confirmar que o novo SL melhora o risco e nao piora a posicao;
7. registrar auditoria antes e depois da tentativa.

## Escopo funcional

### 1. Nova flag de seguranca

Adicionar flag padrao desligada:

```text
dynamic_exit_demo_sl_assisted_execution_enabled = False
```

Default obrigatorio: `False`.

Essa flag nao deve habilitar execucao automatica. Ela apenas permite o botao assistido aparecer/ficar habilitado.

### 2. Novo contrato de resultado da execucao assistida

Criar contrato, por exemplo:

```python
DynamicExitDemoSLExecutionResult
```

Campos sugeridos:

```python
symbol: str
ticket: int | None
side: str
requested_stop: float | None
previous_stop: float | None
new_stop: float | None
allowed: bool
submitted: bool
success: bool
retcode: str
message: str
rejection_reasons: tuple[str, ...]
source: str
created_at: str
```

### 3. Gate final de execucao assistida

Revalidar antes de enviar ao MT5 Demo:

- conta demo;
- ticket valido;
- posicao ainda aberta;
- simbolo e lado conferem;
- preco atual ainda permite o SL candidato;
- spread aceitavel;
- stop candidato ainda melhora risco;
- stop candidato nao cruza preco atual;
- stop candidato nao e igual/irrelevante em relacao ao stop atual;
- mesma vela/janela nao executou modificacao repetida;
- TP permanece inalterado;
- nenhuma ordem nova sera aberta.

### 4. Adaptador MT5 para modificar apenas SL

Se nao existir adaptador seguro, criar um metodo com nome explicito, por exemplo:

```python
modify_demo_position_stop_loss(...)
```

Regras:

- deve ser impossivel chamar sem `demo=True` ou verificacao equivalente;
- nao pode criar posicao nova;
- nao pode alterar volume;
- nao pode alterar TP, exceto preservando exatamente o TP atual quando API exigir campo TP;
- deve registrar retcode e mensagem;
- deve falhar fechado se nao conseguir confirmar conta demo.

### 5. Dashboard assistido

Na area de saida dinamica, exibir:

```text
Modo: DEMO ASSISTIDO
Stop atual
Stop sugerido
Gate: APROVADO/REJEITADO
Motivos
Botao: Aplicar SL sugerido na conta DEMO
```

O botao so fica habilitado quando:

- flag de assistido esta ligada;
- decisao simulada esta aprovada;
- conta demo confirmada;
- robo demo armado;
- gate final aprovado.

Antes do botao, mostrar aviso forte:

```text
Esta acao modifica SOMENTE o SL de uma posicao existente em conta DEMO. Nao abre ordem, nao fecha posicao e nao altera TP.
```

### 6. Auditoria obrigatoria

Registrar:

- decisao simulada consumida;
- resultado do gate final;
- tentativa de envio;
- resposta MT5;
- stop anterior;
- stop solicitado;
- sucesso/falha;
- motivo de rejeicao.

A auditoria deve aparecer no dashboard e/ou relatorio.

### 7. Testes obrigatorios

Criar testes para:

1. default desligado nao mostra/habilita execucao.
2. conta nao-demo rejeita.
3. BUY nao permite SL menor que stop atual.
4. SELL nao permite SL maior que stop atual.
5. candidato que cruza preco atual rejeita.
6. candidato irrelevante rejeita.
7. TP e preservado.
8. nao chama abertura de ordem.
9. nao fecha posicao.
10. confirmacao assistida chama apenas modificacao de SL.
11. falha da API MT5 fica registrada em auditoria.
12. chamada repetida na mesma vela/janela e rejeitada.

## Criterios de aceite

- TIA-026 concluida antes desta missao.
- Execucao assistida aparece apenas quando habilitada por flag.
- Default permanece desligado.
- Apenas conta Demo pode modificar SL.
- Nenhuma ordem nova e aberta.
- Nenhuma posicao e fechada.
- TP nao e alterado.
- SL so move se melhorar risco.
- Gate final revalida o estado imediatamente antes da chamada MT5.
- Auditoria completa registrada.
- Testes novos passam.
- `python -m compileall dashboard_app.py application domain research tests` passa.
- `python scripts\run_critical_ci.py` executado; se falhar por pendencia preexistente, registrar no relatorio.

## Proibido

- Conta real.
- Execucao automatica sem clique/confirmacao assistida.
- Abrir ordem.
- Fechar posicao.
- Alterar TP.
- Recalcular Lab no ciclo operacional.
- Buscar historico pesado para decidir stop.
- Apagar `.traderia`, banco, logs ou snapshots.

## Resultado esperado

O TraderIA Novo passa a ter modo assistido de gestao dinamica de SL em conta Demo: o sistema sugere, valida, exibe e, mediante confirmacao operacional explicita, move somente o stop loss de uma posicao existente, com auditoria completa e sem risco de operar conta real.
