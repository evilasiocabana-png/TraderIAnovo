# Protocolo de Criacao de Modelo Operacional

Data: 2026-07-16
Projeto: TraderIA Novo
Status: protocolo operacional e retrospectiva de aprendizado
Referencia de origem: criacao do Modelo 3 / M3 RR3 e Modelo 4 / M4 espelho do M1

## Objetivo

Registrar o processo correto para criar novos modelos operacionais no TraderIA Novo.

Este protocolo existe para que proximos modelos sejam criados com menos retrabalho, menos ambiguidade e menor risco de quebrar a operacao atual.

Um modelo operacional e um fluxo completo de entrada e saida que pode coexistir com outros modelos no mesmo par, desde que respeite os contratos do sistema.

## Principio Central

Novo modelo nao e apenas uma nova coluna na tela.

Todo modelo precisa atravessar as mesmas camadas:

```text
Research Lab ou snapshot separado
  -> configuracao vencedora
  -> Trade Plan
  -> gates visuais
  -> Robo Demo
  -> Provider MT5
  -> Position Manager / Saida
  -> Relatorio / Historico
  -> testes
```

Se uma dessas camadas nao for atualizada, o modelo pode aparecer na tela mas nao operar, ou pode operar sem rastreabilidade.

## Retrospectiva do M3

O M3 nasceu para operar um fluxo proprio RR3, separado do snapshot operacional principal.

O objetivo era:

- usar um snapshot RR3 separado;
- buscar os cenarios vencedores desse snapshot;
- mostrar visualmente os gates como em M1/M2;
- enviar ordem quando o sinal vivo confirmasse o candidato M3;
- permitir ate uma posicao M3 por par, coexistindo com M1 e M2.

Durante a criacao do M3, apareceram alguns erros importantes:

- o snapshot RR3 havia sido calculado, mas a tela/runtime lia apenas `best_scenarios_by_market`;
- o ranking completo `scenario_ranking` tinha dados melhores que o resumo;
- metricas diagnosticas como amostra, PF e confirmacao foram tratadas como bloqueio operacional, quando o pedido era usar o cenario vencedor aprovado;
- a tabela M3 mostrou parametros antes dos gates, dificultando acompanhar o que faltava para enviar ordem;
- a saida teorica reconhecia apenas M1/M2 como modelos oficiais;
- o provider MT5 ainda limitava o mesmo par a duas posicoes, bloqueando o M3;
- comentarios e testes ainda conheciam apenas `M1` e `M2`;
- textos antigos diziam que o snapshot RR3 nao alimentava o robo, mesmo apos o M3 se tornar operacional.

Esses pontos viram checklist obrigatorio daqui em diante.

## Definicao Oficial de Modelo Operacional

Um modelo operacional deve definir:

- identificador interno;
- nome curto visual;
- origem do plano;
- regra de selecao de cenario vencedor;
- regra de entrada;
- regra de stop inicial;
- regra de alvo;
- beta ou politica de saida;
- permissao de coexistencia com outros modelos;
- limite de posicoes por par;
- comentarios MT5;
- campos de auditoria;
- testes de envio e bloqueio.

Exemplo do M3:

```text
Identificador: MODELO_3_RR3
Nome curto: M3
Origem: snapshot RR3 experimental separado
Selecao: scenario_ranking, agrupado por par
Entrada: sinal vivo confirma a direcao do cenario RR3
Stop/alvo: Trade Plan gerado pelo cenario RR3
Coexistencia: pode operar junto com M1 e M2
Limite: uma posicao por modelo, maximo tres por par
Comentario MT5: TraderIA M3
```

## Checklist Obrigatorio Para Criar Um Novo Modelo

### 1. Nome e Identidade

Definir:

- constante interna;
- nome curto;
- label de tela;
- comentario MT5.

Arquivos a verificar:

- `dashboard_app.py`
- `application/dashboard_service.py`
- `infrastructure/execution/mt5_demo_execution_provider.py`

Exemplo:

```text
MODELO_4_NOME_DO_MODELO
M4
Modelo 4 - descricao curta
TraderIA M4
```

### 2. Fonte do Plano

Definir de onde o modelo tira sua configuracao:

- snapshot operacional principal;
- snapshot separado;
- ranking completo;
- estudo experimental;
- regra manual aprovada.

Nunca assumir que o resumo e suficiente.

Regra aprendida com M3:

```text
Se existir scenario_ranking, ele deve ser a fonte preferencial para escolher vencedor.
best_scenarios_by_market pode ser fallback, nao fonte unica obrigatoria.
```

### 3. Regra de Selecao do Vencedor

O modelo precisa dizer exatamente como escolhe o cenario por par.

Para M3, a regra ficou:

```text
1. Ler scenario_ranking.
2. Filtrar RR = 3.0.
3. Agrupar por par.
4. Preferir status APROVADO.
5. Usar metricas como diagnostico e ordenacao, sem bloquear indevidamente se o cenario aprovado for o vencedor solicitado.
```

Para modelos futuros, decidir explicitamente:

- quais campos filtram;
- quais campos ranqueiam;
- quais campos bloqueiam;
- quais campos sao apenas diagnostico.

### 4. Trade Plan

O modelo deve materializar um Trade Plan completo.

Campos minimos:

- par;
- timeframe;
- direcao;
- entrada;
- stop inicial;
- alvo;
- RR;
- alpha;
- beta;
- setup;
- parametros;
- motivo;
- modelo operacional.

Regra:

```text
Se o modelo aparece como pronto, o Trade Plan precisa carregar exatamente os parametros do cenario vencedor.
```

### 5. Gates Visuais

Todo modelo com entrada deve ter tabela de acompanhamento visual.

Ordem padrao das primeiras colunas:

```text
Par
Timeframe
Envio resumo
Duplicidade
Sinal
Plano
Zona gate
Robo
MT5
Filtro
Regime
Plano vigente
Posicao
Envio
```

Depois dos gates entram as configuracoes:

```text
Alpha
Beta
Setup
Config vencedora
Direcao
Stop
Alvo
RR
Score
Confirmacao
PF
Amostra
Motivo
```

Regra aprendida com M3:

```text
Gates precisam ficar antes dos parametros para o operador enxergar rapido o que falta encaixar.
```

### 6. Cores de Tela

Quando a tabela comparar modelos, usar cor por modelo:

```text
M1: verde
M2: amarelo
M3: rosa
M4+: definir cor antes de implementar
```

Quando a tabela mostrar gates, usar cor por status:

```text
OK: verde
Aguardando: amarelo
Bloqueado/Rejeitado: vermelho
```

Nao misturar essas duas sem deixar claro qual legenda esta ativa.

### 7. Robo Demo

O Robo Demo deve saber:

- quando o modelo esta habilitado;
- se esta em modo individual ou `TODOS`;
- se deve enviar ordem;
- qual Trade Plan usar;
- qual comentario gravar no MT5;
- qual modelo registrar no historico.

Regra:

```text
Robo Demo executa o plano. Ele nao deve inventar a estrategia do modelo.
```

### 8. Provider MT5

O provider precisa reconhecer o novo modelo.

Checklist:

- `_model_comment`;
- limite por par;
- bloqueio de duplicidade por modelo;
- comentarios legados;
- testes de envio;
- testes de bloqueio.

Regra atual apos M4:

```text
Maximo por par: 4 posicoes
Regra: uma posicao por modelo M1, M2, M3 e M4
Quinta posicao no mesmo par: bloqueada
Mesmo modelo no mesmo par: bloqueado
```

Para M5 ou modelos futuros, o limite precisa ser reavaliado explicitamente. Nao aumentar automaticamente sem decisao.

## Registro do M4

O M4 nasceu como espelho operacional do M1, sem recalculo pesado de Lab.

Definicao:

```text
Identificador: MODELO_4_ESPELHO_M1
Nome curto: M4
Origem: plano valido do Modelo 1 / Lab vencedor
Selecao: copia o plano vigente do M1
Entrada: inverte BUY/SELL do M1
Stop inicial: alvo original do M1
Alvo: stop original do M1
Beta/saida: BETA004_ESPELHO_M1
Coexistencia: pode operar junto com M1, M2 e M3
Limite: uma posicao M4 por par; maximo quatro posicoes por par
Comentario MT5: TraderIA M4
```

Aprendizado:

```text
Modelo espelho nao precisa recalcular Lab quando a fonte e um plano ja aprovado.
Mesmo assim, precisa atravessar tela, backend, provider, relatorio e testes.
```

### 9. Position Manager e Saida

Novo modelo deve declarar como sera acompanhado apos a entrada:

- usa Position Manager padrao;
- usa beta especifica;
- usa stop fixo;
- usa stop movel;
- usa somente leitura;
- pode fechar posicao ou apenas proteger.

Regra:

```text
Entrada e saida precisam estar registradas, mas o Position Manager nao deve recalcular o Lab.
```

### 10. Relatorio e Historico

O historico precisa registrar:

- modelo de envio;
- alpha;
- beta;
- setup de entrada;
- setup ou politica de saida;
- parametros usados;
- motivo de entrada;
- motivo de saida;
- se stop movel foi acionado;
- se foi M1, M2, M3, M4 ou modelo futuro.

Regra:

```text
Se nao aparece no historico, nao esta auditavel.
```

### 11. MT5 Visual

Se o modelo afeta grafico MT5:

- atualizar JSON visual;
- evitar acumulo de texto antigo;
- mostrar alpha/beta/modelo corretamente;
- mostrar texto apenas quando necessario;
- nao poluir graficos sem posicao.

### 12. Testes Obrigatorios

Todo modelo novo precisa de testes cobrindo:

- selecao do cenario vencedor;
- montagem do Trade Plan;
- gate visual principal;
- envio permitido quando tudo esta OK;
- bloqueio quando sinal vivo nao confirma;
- bloqueio por duplicidade do mesmo modelo;
- coexistencia com modelos existentes;
- limite maximo por par;
- comentario MT5;
- registro no historico.

Para M3, o teste critico foi:

```text
M1 + M2 abertas no mesmo par -> M3 pode abrir.
M1 + M2 + M3 abertas no mesmo par -> quarta ordem bloqueia.
```

## Fluxo Recomendado Para Proximo Modelo

1. Criar documento curto da ideia do modelo.
2. Definir identidade: `MODELO_N`, nome curto e comentario MT5.
3. Definir fonte do plano.
4. Definir regra de selecao do vencedor.
5. Definir se metricas sao bloqueio ou apenas diagnostico.
6. Implementar montagem do Trade Plan.
7. Criar tabela visual com gates nas primeiras colunas.
8. Integrar Robo Demo.
9. Integrar provider MT5.
10. Integrar saida/Position Manager.
11. Integrar relatorio/historico.
12. Criar testes.
13. Rodar validacao.
14. Reiniciar app.
15. Registrar aprendizado.

## Erros Que Nao Devem Se Repetir

### Snapshot calculado mas nao usado

O botao pode gerar arquivo corretamente, mas o runtime pode estar lendo outra fonte.

Sempre validar:

```text
arquivo gerado
campos existentes
fonte consumida pelo runtime
fonte consumida pela tela
fonte consumida pelo robo
```

### Diagnostico virando bloqueio sem decisao

Amostra, PF, score e confirmacao podem ser:

- criterio de selecao;
- criterio de bloqueio;
- apenas diagnostico.

Isso precisa ser decidido antes. No M3, a decisao final foi usar o cenario RR3 aprovado como operacional, mantendo metricas como diagnostico.

### Tela e backend discordando

Se a tabela usa uma regra e o backend usa outra, o operador perde confianca.

Regra:

```text
Tabela visual e backend devem chamar ou replicar a mesma regra de selecao.
```

### Modelo novo sem provider atualizado

Se o provider nao conhece o modelo, ele pode:

- bloquear indevidamente;
- classificar como legado;
- impedir coexistencia;
- gravar comentario errado.

### Modelo novo sem historico

Sem historico, nao da para comparar resultado real, teorico, alpha, beta e saida.

## Template Para Especificar Novo Modelo

```text
Nome:
Identificador:
Comentario MT5:
Cor visual:

Origem do plano:
Fonte preferencial:
Fonte fallback:

Regra de selecao:
Metricas de diagnostico:
Metricas de bloqueio:

Regra de entrada:
Regra de stop inicial:
Regra de alvo:
Regra de saida:

Pode coexistir com:
Limite por par:
Bloqueio por duplicidade:

Tabelas impactadas:
Historico impactado:
MT5 visual impactado:

Testes obrigatorios:
Rollback:
```

## Comando De Uso Para GPT/Codex

Quando for pedir um novo modelo, usar:

```text
Crie um novo modelo operacional seguindo docs/architecture/OPERATIONAL_MODEL_CREATION_PROTOCOL.md.
Antes de implementar, preencha o template do modelo, confirme fonte do plano, regra de selecao, gates, provider, limite por par, saida e historico.
Depois implemente com testes.
```

## Conclusao

O aprendizado principal do M3 e que um modelo operacional precisa nascer como fluxo completo, nao como ajuste isolado.

O caminho seguro e:

```text
configuracao vencedora -> Trade Plan -> gates -> Robo -> Provider -> Relatorio -> testes
```

Esse protocolo passa a ser a referencia para qualquer M4, M5 ou variante futura.
