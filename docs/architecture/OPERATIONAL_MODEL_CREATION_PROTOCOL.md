# Protocolo de Criacao de Modelo Operacional

## Extensao: variante com reentrada limitada

Quando um novo modelo reutilizar outro e alterar apenas a reentrada, o contrato
deve registrar separadamente: modelo de origem, entrada inicial, condicao que arma
a reentrada, tipo da ordem pendente, alvo exclusivo da reentrada, fallback de
saida e quantidade maxima de reentradas por ciclo. O provider nao pode classificar
o modelo inteiro como `sem TP`: a decisao depende de `active_entry_order_type`.

M18-M22 sao a referencia implementada desse padrao. Consulte
`OPERATIONAL_MODELS_M18_M22_XAU_REENTRY_TP75.md`.

Data: 2026-07-16
Projeto: TraderIA Novo
Status: protocolo operacional e retrospectiva de aprendizado
Referencia de origem: criacao dos Modelos 3 a 7

## Objetivo

Registrar o processo correto para criar novos modelos operacionais no TraderIA Novo.

Este protocolo existe para que proximos modelos sejam criados com menos retrabalho, menos ambiguidade e menor risco de quebrar a operacao atual.

Um modelo operacional e um fluxo completo de entrada e saida que pode coexistir com outros modelos no mesmo par, desde que respeite os contratos do sistema.

## Extensao: modelo acumulador financeiro

Quando um modelo agrega entradas de outros modelos, como o M23, o protocolo
tambem exige: lista explicita de fontes ativas, selecao exclusiva, identidade por
fonte e par, separacao dos SL/TP originais, estado persistente da cesta, trava de
nova rodada, formula financeira com custos expostos e fechamento ticket por
ticket. Consulte `OPERATIONAL_MODEL_23_ACCUMULATOR.md`.

## Pesquisa Historica De Stop E Alvo Antes Da Promocao

Para variantes de timeframe de um modelo existente, a entrada pode ser copiada
como contrato, mas stop e alvo devem permanecer em pesquisa ate existir replay
reproduzivel. O protocolo abaixo foi aplicado aos antigos contratos M8, M9 e
M10, hoje aposentados para novas entradas:

```text
1. Fixar a regra de entrada e os dois timeframes do modelo.
2. Usar os 5.000 candles locais de cada par.
3. Entrar na abertura posterior ao candle fechado de confirmacao.
4. Testar a grade de stop ATR x alvo R sem alterar o runtime.
5. Permitir apenas uma posicao por modelo/par no replay.
6. Em colisao intrabar de stop e alvo, assumir stop primeiro.
7. Persistir vencedor agregado, vencedor por par e ranking completo.
8. Exibir o artefato na aba Replay, selecionado primeiro por modelo.
9. Promover parametros operacionais somente em uma missao posterior e explicita.
```

O calculo pesado nunca roda no ciclo leve Forex. A Replay le o artefato
`.traderia/research/model8_10_stop_target_research.json` e informa claramente
que o resultado e bruto, sem spread, comissao ou swap.

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

Regra atual apos M10:

```text
Maximo por par: 10 posicoes
Regra: uma posicao por modelo M1 a M10
Decima primeira posicao no mesmo par: bloqueada
Mesmo modelo no mesmo par: bloqueado
```

Para M11 ou modelos futuros, o limite precisa ser reavaliado explicitamente. Nao aumentar automaticamente sem decisao.

## Registro do M4

O M4 nasceu como espelho operacional do M1, sem recalculo pesado de Lab.

Definicao:

```text
Identificador: MODELO_4_ESPELHO_M1
Nome curto: M4
Origem: plano valido do Modelo 1 / Lab vencedor
Selecao: copia o plano vigente do M1
Contrato M1: entrada, stop, alvo e RR permanecem exatamente como vieram do Lab
Entrada: inverte BUY/SELL do M1
Stop inicial: distancia propria de 1R no sentido contrario ao alvo do M4
Alvo: stop original do M1
RR operacional M4: 1.0
Beta/saida: BETA004_ESPELHO_M1
Coexistencia: pode operar sozinho quando M4 for selecionado isoladamente; no
modo Todos, M1 e M4 continuam independentes e podem ser aceitos ou rejeitados
separadamente
Limite: uma posicao M4 por par; respeita o limite operacional global vigente
Comentario MT5: TraderIA M4
```

Aprendizado:

```text
Modelo espelho nao precisa recalcular Lab quando a fonte e um plano ja aprovado.
M1 nunca deve ser normalizado depois do Lab. Somente o M4 se adapta: usa o stop
do M1 como alvo e cria stop proprio de mesma distancia (`RR1`).
M4 precisa passar por seus proprios gates de duplicidade, posicao aberta,
provider, MT5 e risco. A aprovacao ou rejeicao do M4 nunca fecha, bloqueia ou
desfaz o M1; o mesmo vale no sentido contrario.
Mesmo assim, precisa atravessar tela, backend, provider, relatorio e testes.
```

## Registro do M5

O M5 nasceu como fluxo proprio de Price Action simples, independente de M1-M4.

Definicao:

```text
Identificador: MODELO_5_PRICE_ACTION
Nome curto: M5
Origem: leitura leve de Price Action sobre a linha MT5 atual
Selecao: estrutura + zona de interesse + confirmacao viva
Entrada: PRICE_ACTION_ENTRY_MODEL
Stop inicial: estrutural, alem de suporte/fundo ou resistencia/topo com buffer
Alvo: nivel estrutural ou projecao minima de 1.5R
Alpha: ALPHAPRICE5
Beta/saida: BETAPRICE5_PRICE_ACTION_STRUCTURE_EXIT
Coexistencia: pode operar junto com M1, M2, M3 e M4
Limite: uma posicao M5 por par; maximo sete posicoes por par apos M7
Comentario MT5: TraderIA M5
```

Aprendizado:

```text
Modelo proprio nao deve falsificar origem como Research Lab.
M5 usa source=PRICE_ACTION_MODEL e o robo aceita essa fonte como contrato operacional autorizado.
Mesmo sem passar no Lab pesado, M5 precisa expor gates, plano, provider, historico, saida e testes.
```

## Registro do M6

Em 2026-08-04, o M6 anterior foi preservado apenas como identidade historica e
o numero M6 passou a representar a expansao do Lab M1 para nove pares Forex.

Definicao:

```text
Identificador: MODELO_6_LAB_FOREX_EXPANSION
Nome curto: M6
Origem: snapshot MT5 compartilhado e pesquisa pesada manual do mesmo Lab do M1
Escopo: nove pares definidos em domain/market_universe.py
Selecao: melhor Alpha, timeframe, ATR SL e RR individual de cada par
Entrada: sinal vivo posterior ao candle fechado do timeframe vencedor
Stop/alvo: Trade Plan fixo materializado pelo Lab
Contrato de saida: RESEARCH_FIXED_SL_TP
Coexistencia: independente de M1-M5 para selecao e envio
Limite: uma posicao M6 por par
Comentario MT5: TraderIA M6
Execucao: somente MT5 Demo
```

Aprendizado:

```text
Expandir mercados nao significa copiar o vencedor de outro par. Cada novo par
precisa dos proprios candles e do proprio vencedor, mas deve reutilizar o motor
do M1. O snapshot novo e mesclado ao existente para nao apagar o M1.
```

## Registro do M7

Em 2026-08-04, o M7 dinamico anterior foi preservado somente para historico. O
M7 atual aplica o mesmo Lab do M1 exclusivamente a ouro e Bitcoin.

Definicao:

```text
Identificador: MODELO_7_LAB_XAU_BTC
Nome curto: M7
Origem: snapshot MT5 compartilhado e pesquisa pesada manual do mesmo Lab do M1
Escopo: XAUUSD e BTCUSD; BITCOIN do CSV e mapeado para BTCUSD
Selecao: melhor Alpha, timeframe, ATR SL e RR individual por ativo
Entrada: sinal vivo posterior ao candle fechado do timeframe vencedor
Stop/alvo: Trade Plan fixo materializado pelo Lab
Contrato de saida: RESEARCH_FIXED_SL_TP
Coexistencia: independente de M1-M6 para selecao, envio e gestao
Limite: uma posicao M7 por ativo
Comentario MT5: TraderIA M7
Execucao: somente MT5 Demo
```

Aprendizado:

```text
Ativos de classes diferentes precisam de simbolo MT5 executavel e pesquisa
propria. O ID antigo nao pode ser reutilizado, pois faria o Position Manager
aplicar a saida dinamica historica ao novo Trade Plan fixo.
```

## Substituicao Robusta do M3 em 2026-07-29

O M3 anterior escolhia um vencedor diferente por par usando desenvolvimento e
um unico holdout final. A auditoria encontrou pares liberados por politica
manual apesar de resultado negativo no holdout, criando divergencia entre
evidencia e operacao.

O novo M3 usa tres janelas cronologicas sem embaralhamento:

1. treino nos 60% mais antigos;
2. validacao nos 20% seguintes;
3. holdout final nos 20% mais recentes, aberto somente depois de congelar
   candidato e timeframe.

Foram comparados M30 e H1 com custos de 1,5 bps e estresse de 2,5 bps. Somente
USDCAD/H1 com `STRUCTURE_CONTINUATION` passou todos os gates. Portanto, o M3
tem certificacao historica individual somente para USDCAD.

Em 2026-07-29, o usuario autorizou a expansao do mesmo contrato M3 para os oito
pares em conta Demo. Essa expansao nao equivale a nova pesquisa: os outros sete
pares devem permanecer identificados como
`USER_APPROVED_DEMO_EXPANSION_UNVALIDATED`, sem herdar metricas do USDCAD.

O contrato operacional permanece:

`candle H1 fechado -> sinal congelado -> proximo preco vivo -> SL 1,75 ATR -> TP 2,5R`

O Position Manager nao altera esse plano. Conta real permanece bloqueada.

## Substituicao Experimental do M4 em 2026-07-29

O M4 passou a usar um unico contrato `LIQUIDITY_RECLAIM` derivado do candidato
AUDUSD BUY. A escolha considerou amostra completa de 100 trades, PF 1,468,
holdout de 14 trades com PF 2,121 e custo estressado com PF 2,017.

O contrato congelado usa M30, EMA34/144, ADX entre 28 e 35, lookback 40, wick
minimo 0,5, RSI extremo 40, exclui segunda-feira, SL 2,5 ATR e TP 3R. O mesmo
contrato foi autorizado nos oito pares somente em Demo.

Como o holdout possui apenas 14 trades, AUDUSD permanece
`BEST_AVAILABLE_DEMO_CANDIDATE_UNCERTIFIED`. Os outros sete pares permanecem
`USER_APPROVED_DEMO_EXPANSION_UNVALIDATED`. A expansao nao pode copiar metricas
historicas do AUDUSD nem autorizar conta real.

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

## Substituicao do M3 por vencedores de todo o Forex em 2026-08-05

O contrato `MODELO_3_LAB_ALPHA_SUGERIDA_2_PLUS` foi aposentado para novas
entradas. O M3 ativo passou a ser `MODELO_3_LAB_ALL_FOREX_WINNERS`, reunindo os
vencedores individuais do Lab nos 17 pares de moedas. XAUUSD e BTCUSD continuam
fora do M3. A substituicao preserva o historico antigo, separa as curvas pelo ID
e reutiliza o snapshot compartilhado, sem acrescentar pesquisa ao ciclo leve.

O caminho seguro e:

```text
configuracao vencedora -> Trade Plan -> gates -> Robo -> Provider -> Relatorio -> testes
```

Esse protocolo passa a ser a referencia para qualquer modelo ou variante futura.

## Substituicao do M3 por XAUUSD/M5 RSI14 + SMA20 em 2026-08-11

O contrato `MODELO_3_LAB_ALL_FOREX_WINNERS` foi aposentado para novas entradas.
O M3 ativo passou a ser `MODELO_3_XAU_M5_RSI50_FLIP`: somente XAUUSD/M5 e
exatamente as ultimas 52 velas. A compra exige RSI14 fechado acima de 50 e
fechamento acima da SMA20; a venda exige RSI14 abaixo de 50 e fechamento abaixo
da SMA20. O Full Exit permanece pelo RSI no lado oposto e a entrada contraria
ocorre apenas depois do fechamento.
O ID novo impede que posicoes do M3 antigo recebam a politica nova. O contrato
completo esta em `OPERATIONAL_MODEL_M3_XAU_M5_RSI50_FLIP.md`.

## Registro dos M11 ao M20

Em 2026-08-01, as dez Alphas oficiais ainda sem fluxo proprio foram promovidas
sequencialmente para M11-M20. A promocao confirmou novos requisitos do
protocolo:

- uma Alpha por modelo, sem alterar M1-M10;
- contrato congelado e versionado, sem pesquisa pesada no runtime;
- indicadores compartilhados por par, timeframe e candle fechado;
- decisao, duplicidade, comentario e historico independentes por modelo;
- limite global derivado da quantidade de modelos ativos, hoje vinte;
- Alpha originalmente definida como filtro precisa declarar explicitamente
  quem fornece a direcao;
- amostra historica e aprovacao Demo sao campos separados;
- o teste de aceite mede o ciclo completo, nao apenas uma funcao isolada.

O inventario e os parametros estao em
`docs/architecture/OPERATIONAL_MODELS_M11_M20.md`.

## Registro do M21

Em 2026-08-04, o M21 foi criado como espelho independente do M19. Ele reutiliza
o mesmo sinal fechado ALPHA015, inverte BUY/SELL e troca diretamente os niveis:
`TP_M21 = SL_M19` e `SL_M21 = TP_M19`. A derivacao ocorre no contrato runtime,
mantendo uma posicao por modelo e execucao somente Demo. Com a inclusao do M22,
o limite global atual passa a 22 por par.
O contrato completo esta em
`docs/architecture/OPERATIONAL_MODEL_M21_M19_MIRROR.md`.

## Registro do M22

Em 2026-08-04, o M22 foi criado como espelho independente do M9. Ele reutiliza
o mesmo gatilho Trend Pullback M15/M1, inverte BUY/SELL e troca diretamente os
niveis: `TP_M22 = SL_M9` e `SL_M22 = TP_M9`. Os fatores sao derivados do M9:
SL 2,5 ATR, alvo 1,25 ATR e RR 0,5. M9 permanece inalterado; ambos possuem
identidade, cache, Trade Plan, duplicidade e historico proprios. O contrato
completo esta em `docs/architecture/OPERATIONAL_MODEL_M22_M9_MIRROR.md`.

## Registro das variantes dinamicas M8-M14

Em 2026-08-05, o protocolo foi aplicado para criar uma familia A/B sem alterar
M1-M7. M8-M14 copiam, respectivamente, as entradas M1-M7 e trocam somente a
gestao pos-entrada para `DYNAMIC_PROTECT_ONLY`.

| Novo | Origem | Politica | Fechamento antecipado |
|---|---|---|---|
| M8 | M1 | protecao depois de 1,50R | proibido |
| M9 | M2 | protecao depois de 1,50R | proibido |
| M10 | M3 | protecao depois de 1,50R | proibido |
| M11 | M4 | protecao depois de 1,50R | proibido |
| M12 | M5 | protecao depois de 1,50R | proibido |
| M13 | M6 | protecao depois de 1,50R | proibido |
| M14 | M7 | protecao depois de 1,50R | proibido |

O aprendizado adicional e que numero de modelo nao basta como identidade:
modelos historicos M8-M22 continuam preservados no Relatorio. Desde 2026-08-06,
esses IDs M8-M16 estao aposentados e nenhum deles pode abrir nova entrada. O contrato
detalhado esta em `docs/architecture/DYNAMIC_EXIT_MODELS_M8_M14.md`.

## Registro do novo M8 XAUUSD/M5 por RSI50

Em 2026-08-10, o protocolo foi aplicado ao contrato independente
`MODELO_8_XAU_M5_SMA_RSI_REENTRY`. Os IDs anteriores que usaram o numero M8
continuam aposentados e auditaveis. O novo M8 opera exclusivamente XAUUSD/M5:
as ultimas 52 velas alimentam a SMA20/SMA50 simples que define a direcao, e a entrada a mercado ocorre somente
enquanto RSI14 estiver do lado de 50 correspondente a essa direcao. O SL fica `0,01` alem do ultimo pivo M5
confirmado 2+2; nao ha TP fixo. O Position Manager faz Full Exit quando candle
M5 fechado confirma RSI14 de 70 para baixo em BUY ou de 30 para cima em SELL,
ou quando SMA20/SMA50 invertem. Depois de uma saida pelo RSI, a reentrada usa
Buy Stop/Sell Stop `0,01` alem do extremo do ultimo candle fechado, condicionada
ao RSI50 e a direcao valida das medias.

Contrato detalhado:
`docs/architecture/OPERATIONAL_MODEL_M8_XAU_M5_SMA_RSI_REENTRY.md`.

## Registro dos setups A-E do XAUUSD/M5

Em 2026-08-10, o protocolo também criou quatro contratos incrementais sobre o
M8/Setup A: M9/Setup B com ADX14 > 25; M10/Setup C com distância entre médias
normalizada pelo ATR14 >= 0,25; M11/Setup D com inclinação direcional da SMA50
em um candle normalizada pelo ATR14 >= 0,05; e M12/Setup E exigindo os três
filtros. Todos mantêm entrada RSI50, SL no pivô 2+2, ausência de TP e Full Exit
por RSI50 ou inversão SMA20/SMA50. Cada um possui ID, Alpha, Beta, plano,
comentário MT5 e relatório separados. IDs históricos M8-M12 permanecem
aposentados.

Contrato detalhado:
`docs/architecture/OPERATIONAL_MODELS_M8_M12_XAU_TREND_FILTERS.md`.

## Registro do novo M15 XAUUSD/M5

Em 2026-08-05, o protocolo foi aplicado ao modelo canonico
`MODELO_15_XAU_M5_EMA_BREAKOUT_TRAILING`. Ele opera somente XAUUSD/M5, usa
EMA20/50 para direcao, entra um pip alem do extremo do candle anterior e inicia
o SL um pip alem do extremo oposto. Nao existe TP fixo: o Position Manager move
o SL pelo ultimo candle M5 fechado, somente a favor do trader. O M15 permanece
independente dos M1-M14 e restrito a Demo. Em 2026-08-06, foi aposentado para
novas entradas; o registro abaixo permanece apenas como rastreabilidade.

Contrato detalhado:
`docs/architecture/OPERATIONAL_MODEL_M15_XAU_M5_BREAKOUT.md`.

## Registro do novo M16 XAUUSD/M5

Em 2026-08-06, o protocolo foi aplicado ao
`MODELO_16_XAU_M5_PRICE_EMA20_BREAKOUT_TRAILING`. O M16 e independente do M15:
usa preco acima/abaixo da EMA20 para definir BUY/SELL, publica ordem STOP um pip
alem do extremo anterior, nasce com SL no extremo oposto exato, nao usa TP e
move o SL somente a favor pelo candle M5 fechado. O antigo
`MODELO_16_ALPHA012_VWAP_MEAN_REVERSION` permanece aposentado para preservar o
historico. Em 2026-08-06, o M16 tambem foi aposentado para novas entradas.

Contrato completo:
`docs/architecture/OPERATIONAL_MODEL_M16_XAU_M5_PRICE_EMA_BREAKOUT.md`.

## Registro dos setups Forex M13-M17

Em 2026-08-10, M13-M17 foram criados sequencialmente para os 17 pares Forex/M5.
Eles reproduzem os setups A-E de M8-M12, adaptam o buffer para um pip do par e
isolam estado por modelo/par. Os IDs históricos M13-M16 permanecem aposentados.
Contrato em `docs/architecture/OPERATIONAL_MODELS_M13_M17_FOREX_TREND_FILTERS.md`.
