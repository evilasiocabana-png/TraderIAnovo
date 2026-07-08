# Runtime Preservation Policy

## Objetivo

Definir a politica de preservacao do runtime do TraderIA Novo. Esta politica orienta futuras missoes do Codex e pedidos gerados via GPT para evitar que melhorias de performance, limpeza, refresh ou diagnostico danifiquem a operacionalidade do sistema.

## Regra Principal

Runtime Guard pode limpar, pausar, preservar e diagnosticar recursos temporarios. Runtime Guard nao pode alterar decisao operacional, posicao, ordem, stop, alvo, entrada, plano do Lab ou estrategia.

## Implementacao Atual

A politica foi materializada em `core/runtime_guard/runtime_state.py`, `runtime_cleanup_policy.py` e `runtime_state_preserver.py`.

O dashboard usa a politica para preservar snapshot Forex e sugestoes do Lab quando leituras novas vierem vazias, e para limpar somente chaves classificadas como temporarias.

## Classificacao de Estado

### Estado Operacional Protegido

Nunca pode ser apagado, recalculado ou sobrescrito por rotina de limpeza/refresh:

- posicao aberta;
- ticket MT5;
- lado da posicao;
- entrada;
- stop loss atual;
- take profit atual;
- trailing stop;
- break-even;
- alvo;
- plano do Lab;
- politica de saida base;
- parametros do setup;
- timeframe vencedor;
- alpha vencedora;
- estado persistente do Robo Demo;
- Position Manager;
- ordens MT5;
- historico local;
- banco `.traderia`;
- configuracoes persistentes.

### Estado Visual Preservavel

Pode ser mantido na tela quando a nova leitura vier vazia, incompleta ou offline:

- ultimo snapshot Forex com pares validos;
- ultimo card visivel do Robo Demo;
- ultimas sugestoes validas do Lab;
- ultima auditoria MT5 valida;
- ultimo status de relatorio;
- aba selecionada;
- posicao visual de trabalho quando possivel;
- mensagens de runtime recentes.

Estado visual preservado deve ser substituido assim que uma leitura nova valida chegar.

### Estado Temporario Limpavel

Pode ser limpo por acao manual ou politica automatica controlada:

- caches temporarios de UI;
- logs temporarios em memoria;
- mensagens de diagnostico antigas;
- filas expiradas;
- duracoes de render antigas;
- locks stale;
- recursos de UI obsoletos;
- snapshots visuais sem valor operacional;
- subprocessos orfaos confirmados;
- threads orfas confirmadas.

### Estado De Diagnostico

Pode ser atualizado sem side effects:

- status de conexao MT5;
- ultimo erro MT5;
- latencia de leitura;
- lock busy;
- tamanho do session state;
- tempo desde ultimo ciclo;
- refresh id;
- eventos de runtime;
- status de cache.

Diagnostico nao pode iniciar ciclo operacional, recalcular Lab pesado ou enviar ordem.

## Pode Alterar

Runtime Guard pode alterar:

- caches temporarios;
- logs temporarios;
- filas expiradas;
- locks stale;
- subprocessos orfaos;
- threads orfas;
- snapshots visuais;
- recursos de UI;
- indicadores de refresh;
- mensagens de diagnostico;
- contadores de render;
- cache de auditoria quando substituido por auditoria valida.

## Nunca Pode Alterar

Runtime Guard nunca pode alterar:

- posicao aberta;
- stop movel;
- trailing stop;
- break-even;
- alvo;
- entrada;
- plano do Lab;
- estado persistente do Robo Demo;
- Position Manager;
- ordens MT5;
- estrategia;
- politica de entrada;
- politica de saida base;
- dados historicos persistentes;
- `.traderia`;
- banco local;
- credenciais;
- conta real.

## Politica Para Leituras Vazias

Quando uma leitura nova vier vazia:

1. Nao apagar a tela operacional.
2. Verificar se existe ultimo snapshot valido.
3. Se existir, renderizar o snapshot valido.
4. Registrar mensagem leve indicando que o sistema aguarda nova leitura.
5. Nao recalcular Lab.
6. Nao acionar diagnostico pesado.
7. Nao desarmar Robo Demo por leitura transitoria.
8. Nao limpar estado operacional.

## Politica Para Robo Demo

O Robo Demo pode ter estado visual preservado durante polling. Uma leitura transitoria do backend nao deve apagar:

- par selecionado;
- modelo;
- decisao;
- entrada;
- stop;
- alvo;
- status de envio demo;
- ultimo resultado;
- auditoria recente.

Somente estas acoes podem limpar o snapshot visual do Robo Demo:

- botao Desarmar;
- reset operacional explicito;
- troca confirmada de contexto operacional;
- rollback de runtime.

O Runtime Guard nao pode abrir ordem, fechar posicao ou mover SL/TP automaticamente. Qualquer execucao demo precisa passar pelos gates especificos do Provider Demo e contratos de Dynamic Exit.

## Politica Para Forex MT5

O painel Forex deve:

- atualizar em ciclo leve;
- preservar ultimo snapshot com pares validos;
- nao alternar para painel vazio se o MT5 oscilar;
- nao recalcular Lab pesado;
- nao usar reload total por padrao;
- respeitar horario/feriado Forex;
- usar a fachada `DashboardService`.

## Politica Para Lab

O Lab deve:

- executar calculos pesados somente sob comando explicito;
- exibir ultimas sugestoes validas quando uma leitura vier vazia;
- preservar rastreabilidade Alpha -> Setup -> TF -> Entrada -> Saida;
- nao decidir envio MT5;
- nao ser recalculado por ciclo Forex leve.

## Politica Para Relatorio

O Relatorio deve:

- observar e auditar;
- atualizar em ciclo leve;
- preservar ultima auditoria valida;
- nao decidir entrada ou saida;
- nao mover stop;
- nao recalcular Lab;
- nao apagar operacoes em negociacao por oscilacao temporaria.

## Politica Para Safe Mode E Stop Movel

Safe Mode pode manter acompanhamento de mercado e posicao, desde que isso seja feito em leitura leve e sem recalcular o Lab pesado.

O Safe Mode pode preservar e atualizar:

- preco atual;
- ultimo candle;
- ATR e indicadores heuristicos disponiveis;
- leitura de posicao aberta;
- R atual;
- recomendacao dinamica read-only;
- auditoria visual e relatorio.

O Safe Mode nao pode:

- inventar plano operacional;
- trocar alpha/setup/timeframe durante posicao aberta;
- mover SL/TP sem gates do Provider Demo;
- executar politica que dependa de dado ausente;
- usar diagnostico MT5 como gatilho operacional;
- limpar plano do Lab por leitura transitoria.

Regra obrigatoria:

```text
Com posicao aberta + plano valido + dados minimos completos -> acompanhar.
Com qualquer requisito ausente -> preservar estado, bloquear movimento de stop e alertar.
```

Para `ATR_TRAILING_STOP`, ATR ausente significa bloqueio seguro, nao erro fatal.
Para `BREAK_EVEN`, entrada, stop atual, preco atual e gatilho RR sao obrigatorios.
Para politicas dinamicas ainda read-only, a recomendacao pode aparecer, mas a execucao segue bloqueada ate autorizacao explicita.

## Politica Para Limpeza

Antes de limpar, toda rotina deve classificar o recurso:

```text
TEMPORARIO -> pode limpar
VISUAL_PRESERVAVEL -> pode substituir apenas por novo valido
OPERACIONAL_PROTEGIDO -> nunca limpar
PERSISTENTE -> nunca limpar automaticamente
DIAGNOSTICO -> pode atualizar sem side effect
```

Se a classificacao for desconhecida, a regra e: nao limpar.

## Politica Para Pull Requests e Inbox

Toda missao que mexer em runtime deve declarar:

- quais chaves de session state altera;
- quais caches altera;
- quais ciclos altera;
- se toca MT5;
- se toca Lab;
- se toca Robo Demo;
- como preserva estado operacional;
- como faz rollback.

Checklist obrigatorio:

```text
[ ] Nao altera ordem real.
[ ] Nao move SL/TP sem gate explicito.
[ ] Nao recalcula Lab pesado em ciclo leve.
[ ] Nao apaga .traderia.
[ ] Nao apaga plano do Lab.
[ ] Nao desarma Robo Demo por leitura transitoria.
[ ] Preserva ultimo snapshot valido.
[ ] Possui teste para leitura vazia/transitoria quando aplicavel.
```

## Rollback

Rollback de Runtime Guard deve:

- reverter codigo e testes da missao;
- manter `.traderia`;
- manter banco local;
- manter historico MT5;
- nao limpar posicoes;
- nao alterar ordens;
- nao alterar configuracoes persistentes sem aprovacao explicita.
