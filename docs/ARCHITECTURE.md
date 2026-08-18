# Architecture

## Modelo 23

O M23 e o acumulador financeiro das entradas validas dos modelos selecionados e
pode operar sozinho ou junto com as ordens diretas dessas fontes. Ele copia os
SL/TP individuais e acrescenta somente o Full Exit coletivo a mercado quando a
cesta atingir +US$1.000 liquidos; nao usa stop ou trailing financeiro global.
Contrato completo em
`docs/architecture/OPERATIONAL_MODEL_23_ACCUMULATOR.md`.

## Implantacao local com watcher desligado

O Streamlit operacional usa `server.fileWatcherType=none` para reduzir consumo de
CPU e memoria. Por isso, alteracoes de imports nao entram em um processo ja vivo.
Depois dessas alteracoes, o fluxo oficial deve reiniciar o TraderIAnovo por
`scripts/abrir_traderianovo.ps1` e validar `/_stcore/health` e a pagina principal.

## Modelos XAU de reentrada controlada

M18-M22 derivam de M8-M12 sem modificar suas origens. A diferenca operacional
esta limitada a uma reentrada por ciclo com TP de 7,50 pontos. A entrada inicial
permanece sem TP fixo e a saida dinamica original funciona como fallback. O
contrato detalhado esta em
`docs/architecture/OPERATIONAL_MODELS_M18_M22_XAU_REENTRY_TP75.md`.

## Visao Geral

TraderIA Novo e uma aplicacao local Streamlit com camadas de aplicacao,
dominio, infraestrutura e pesquisa. O GitHub guarda o codigo e a governanca. A
execucao operacional com MT5 e Lab pesado permanece local.

O mapa canonico das relacoes de ponta a ponta e
`docs/architecture/END_TO_END_OPERATIONAL_FLOW.md`. Toda mudanca que atravesse
Lab, Forex, modelos, Robo Demo, MT5, Position Manager ou Relatorio deve atualizar
esse mapa e validar todos os consumidores relacionados.

## Camadas

### UI

Arquivo principal:

```text
dashboard_app.py
```

Responsabilidade:

- renderizar Streamlit;
- escolher abas;
- chamar apenas a fachada de aplicacao;
- evitar logica pesada na renderizacao.

### Application

Pasta principal:

```text
application/
```

Responsabilidade:

- orquestrar casos de uso;
- expor `DashboardService`;
- converter dados para ViewModels;
- isolar UI de infraestrutura.

### Domain

Pasta principal:

```text
domain/
```

Responsabilidade:

- contratos e dataclasses estaveis;
- objetos de decisao, risco, execucao e resultado;
- regras independentes de UI e infraestrutura.

### Research / Lab

Pastas principais:

```text
research/
alpha/
strategies/
```

Responsabilidade:

- motores de pesquisa;
- alphas;
- calibracao e ranking;
- calculo local a partir de `.traderia/`.

#### Invariantes do Lab Forex

- M1 materializa direcao, timeframe, entrada, stop inicial, alvo e RR sem
  normalizacao posterior.
- M1 preserva o SL e o TP do plano vencedor ate o primeiro toque. O Position
  Manager apenas audita e nao move SL nem executa fechamento antecipado.
- Os resultados promovidos em 2026-07-22 substituem os modelos legados M2-M5.
  A promocao e congelada em
  `research/alpha_suggested/lab_operational_models_manifest.json`.
- M2 usa `ALPHA_SUGERIDA_001_PLUS`; M3 usa a selecao individual
  `ALPHA_SUGERIDA_002_PLUS`; M4 usa contexto causal M30/H1/H4; M5 delega ao
  melhor vencedor consolidado por par.
- O consolidado operacional chama-se somente M5. Nao existe M5-P operacional.
- M3 opera exclusivamente XAUUSD/M5 sobre uma janela deslizante das ultimas
  200 velas fechadas: BUY exige RSI14
  fechado acima de 50 e fechamento acima da SMA20; SELL exige RSI14 abaixo de
  50 e fechamento abaixo da SMA20. O Full Exit continua sendo pelo RSI no lado
  oposto e a inversao ocorre no ciclo seguinte. Usa SL estrutural 2+2 e nao
  possui TP fixo.
- M6 cobre os nove pares adicionais do Lab Forex; M7 cobre XAUUSD e BTCUSD.
  Eles reutilizam resultado pesado persistido e nao recalculam pesquisa no ciclo leve.
- M1-M2 e M4-M7 preservam entrada, SL inicial, TP e RR fixos do plano de origem
  sob `RESEARCH_FIXED_SL_TP`; o M3 possui gestao propria pelo RSI14/50.
- Os IDs históricos M8-M14 reutilizavam, respectivamente, as entradas M1-M7 e
  permanecem aposentados. Eles mudavam somente a
  gestao pos-entrada para `DYNAMIC_PROTECT_ONLY`.
- Nas variantes M8-M14, antes de 1,50R o SL inicial e preservado; depois, o
  Position Manager pode somente melhorar o SL por break-even ou ATR trailing.
  `EARLY_EXIT` e `FULL_EXIT` sao sempre proibidos.
- Com `TimeTradeServer` valido, o gate de rollover usa exclusivamente a janela
  de 5 minutos antes/depois da virada do dia do servidor. O horario UTC fixo e
  apenas fallback de seguranca quando o relogio MT5 estiver indisponivel.
- A entrada historica nasce apenas em transicao `WAIT -> BUY/SELL`.
- Um replay nao pode abrir nova entrada enquanto o trade teorico anterior do
  mesmo cenario estiver ativo.
- Resultado historico e definido pelo primeiro toque real em SL ou TP; candle
  que toca ambos e contabilizado conservadoramente como stop.
- Indicadores historicos devem ser calculados somente com informacao disponivel
  naquele candle.
- A aprovacao de entrada nao depende de uma politica Beta que nao tenha sido
  reproduzida pelo replay.
- Linha sem configuracao, sem gatilho ou com plano invalido pode ser exibida para
  diagnostico, mas nao pode chegar ao envio como plano executavel.
- A visao principal do Lab mostra uma configuracao vencedora para cada par
  analisado. O ICT aparece como referencia historica por linha; no contrato
  atual ele nao bloqueia Demo e nao pode ocultar Alpha, Beta, timeframe ou
  parametros. Tornar ICT bloqueante exige mudanca explicita de arquitetura.
- A prova de uma recomendacao pertence ao Replay: ela reexecuta exatamente o
  par, Alpha, timeframe, stop e RR persistidos sobre os 5.000 candles da base,
  sem recalcular o Lab nem participar do ciclo leve Forex.
- Alphas sugeridas por pesquisa automatizada usam namespace separado das Alphas
  oficiais, divisao cronologica com holdout fechado e permanecem nao
  operacionais ate aprovacao explicita. Resultado de treino ou validacao nao
  autoriza renomear, publicar no runtime nem enviar ordem.
- Somente linhas marcadas `demo_forward_enabled=true` no manifesto podem gerar
  plano. Linhas bloqueadas continuam visiveis, mas retornam `WAIT`.
- A pesquisa pesada permanece sob demanda. O ciclo Forex usa cache leve e nao
  recalcula os 5.000 candles.
- Modelos sao independentes, mas o provider bloqueia a duplicacao do mesmo
  plano exato e candle entre modelos.
- O provider permite no maximo uma posicao por modelo e dez posicoes por par
  no conjunto M1-M10.
- Conta real permanece bloqueada; a promocao autoriza somente forward Demo.

### MT5 / Infrastructure

Pastas principais:

```text
infrastructure/
mt5/
```

Responsabilidade:

- acesso externo;
- leitura MT5;
- provider de execucao demo;
- deteccao de caminho visual MT5.

## Runtime Local

Pasta:

```text
.traderia/
```

Conteudo esperado:

- snapshots do Lab;
- banco local SQLite;
- logs;
- jsonl de execucao demo;
- JSON visual MT5;
- arquivos de restauracao.

Essa pasta e ignorada pelo Git.

## Fluxo Das Abas

### MT5 Forex

- Abre com ultimo estado local/snapshot.
- Nao possui ciclo automatico bloqueante.
- Nao deve prender a UI em leitura MT5 longa.
- O Robo Demo online deve sobreviver a reruns do Streamlit. Se a sessao visual
  indica monitoramento online ativo, mas um `DashboardService` recem-criado
  aparece `DISARMED`, o ciclo pode rearmar o backend em memoria antes da
  avaliacao. Isso nao autoriza envio extra nem recalculo pesado; apenas preserva
  o contrato operacional ate que haja bloqueio real ou desarme explicito.

### Lab

- Usa o motor local da TraderIA Novo.
- Lida com `.traderia/mt5_research_snapshot.json`.
- Usa `.traderia/traderia_mt5_history.sqlite` como banco local.
- Auditoria completa fica sob demanda.

### Relatorios

- Audita `.traderia/mt5_demo_execution.jsonl` contra historico MT5/local.
- Carrega uma vez, cacheia na sessao e atualiza por botao.
- A leitura leve `positions_get` atualiza apenas posicoes abertas e nunca pode
  substituir o historico fechado usado nas curvas patrimoniais.
- O ultimo relatorio completo fica persistido em
  `.traderia/runtime/mt5_trade_audit_report.json`, permitindo restaurar os
  graficos apos reinicio mesmo quando o canal externo MT5 estiver ocupado.
- O snapshot e assinado pelas operacoes fechadas e so volta a ser gravado
  quando esse conjunto muda; ticks e lucro flutuante nao geram escrita.
- Uma sessao Streamlit que ainda retenha apenas linhas `ABERTA` ou
  `ORDEM_ABERTA` deve considerar esse cache incompleto e hidrata-lo
  automaticamente com o snapshot completo, sem exigir limpeza do navegador.
- A sonda completa continua isolada em subprocesso e aguarda somente uma
  janela curta pelo canal compartilhado; o ciclo de mercado permanece prioritario.
- As curvas operacionais ativas exibem M1-M22. M13-M17 aceitam somente os IDs
  atuais da familia Forex/M5 e os 17 pares canonicos, sem misturar contratos
  historicos que reutilizavam os numeros M13-M16. M18-M22 tambem exigem seus
  IDs operacionais completos para nao incorporar os contratos legados.

## Politica De Travamentos E Regressao De Velocidade

Todo travamento, congelamento, queda aparente do app, demora incomum ou
reinicio manual necessario deve ser tratado como evento arquitetural.

Cada evento deve ser registrado antes de seguir com novas mudancas, contendo:

- data e horario aproximado;
- aba ou fluxo afetado;
- sintoma observado;
- porta/processo envolvido quando disponivel;
- se o backend respondeu ou nao;
- causa provavel;
- acao corretiva aplicada;
- prevencao sugerida para nao repetir.

Guardrails:

- nao aceitar travamento como comportamento normal do Streamlit;
- nao resolver apenas reiniciando sem registrar;
- nao desarmar Robo Demo por leitura transitoria de backend recem-instanciado;
- nao desligar leitura de mercado essencial para mascarar lentidao;
- medir antes de otimizar quando a causa nao estiver clara;
- manter tabelas grandes paginadas;
- impedir leitura pesada do Lab dentro do ciclo leve;
- manter logs/snapshots leves para Position Manager e Relatorios.
- ciclos operacionais em background devem possuir registro singleton fora do
  script rerun do Streamlit; trocar de aba, atualizar a pagina ou reconectar a
  sessao nunca pode criar uma segunda thread Forex ou Robo Demo no processo.
- apenas um ciclo process-local pode consultar MT5 e executar Position Manager;
  sessoes Streamlit e abas devem consumir o snapshot compartilhado publicado
  por esse ciclo, sem repetir a leitura externa.
- o snapshot Forex compartilhado deve ser um
  `DashboardMT5ForexSignalViewModel` enriquecido pelas constantes do Lab. Uma
  leitura crua do provider nao pode substituir o snapshot usado pela UI ou pelo
  Robo Demo.
- ausencia de configuracao do Lab deve aparecer como `SEM_CONFIG_LAB`, manter o
  gate bloqueado e nunca ser mascarada por `ALPHA001`, `TREND_MOMENTUM` ou
  `BETA001` usados apenas como defaults tecnicos.
- `.traderia/mt5_operational_model.json` e a fonte compartilhada do seletor de
  novas entradas. Rerender passivo ou sessao antiga deve sincronizar com o
  arquivo, sem sobrescreve-lo. Reinicio do app ou do navegador restaura a
  ultima escolha explicita do usuario; `TODOS_MODELOS` nunca e imposto como
  valor de reinicio.
- mudar o modelo de novas entradas nao interrompe a gestao de posicoes abertas;
  o Position Manager continua independente da aba e do seletor atual.
- Lab e Replay classificam sessao pelo timestamp do candle historico. O horario
  vivo do servidor MT5 entra somente nos gates operacionais ao vivo; ele nao
  pode alterar resultado historico conforme a hora de execucao do teste.
- Timestamp Unix recebido do MT5 deve ser convertido diretamente para UTC. Ele
  nunca pode passar pelo fuso local e depois ser rotulado como UTC.
- A validacao viva da janela de entrada deve comparar a barra atual com
  `TimeTradeServer`/timestamp do tick MT5, mantendo os dois valores no mesmo
  relogio da corretora. O UTC da maquina e apenas fallback; ele nao pode
  invalidar como futura uma barra correta do servidor.
- Fim de semana, domingo antes da abertura, sexta no fechamento e rollover sao
  bloqueios operacionais duros, mesmo quando o filtro geral de sessao estiver
  desmarcado.
- o intervalo operacional de 10 segundos deve ser preservado; a otimizacao deve
  reduzir o trabalho dentro do ciclo, nunca ocultar a lentidao aumentando o
  intervalo nem removendo leitura necessaria para a gestao de posicao.
- arquivos de estado compartilhado em `.traderia` devem usar escrita atomica
  (`arquivo temporario` + `os.replace`) e lock process-local. Um ciclo com
  varias posicoes deve carregar e salvar o estado uma vez por lote.
- `runtime_lock.json` nunca pode derrubar a UI por `PermissionError` do
  OneDrive. A escrita usa lock process-local, arquivo temporario, replace e
  tentativas curtas; falha persistente bloqueia apenas o ciclo atual e preserva
  o ultimo Relatorio valido.
- historicos JSONL crescentes devem ser lidos incrementalmente a partir do
  ultimo offset conhecido. Reler o arquivo inteiro a cada ciclo e uma regressao
  de performance.
- caches de historico JSONL devem ser process-local e compartilhados entre
  sessoes Streamlit. Registros rejeitados podem permanecer compactados em
  memoria quando somente a contagem for necessaria; registros aceitos e seus
  planos continuam integrais para Relatorio e Position Manager.
- sessoes Streamlit nao podem criar uma `DashboardService` pesada por aba ou
  navegador. A fachada visual e compartilhada no processo; cada sessao guarda
  apenas a referencia e seus estados estritamente visuais.
- quando o ciclo do Robo Demo estiver ativo, o ciclo Forex inativo deve liberar
  sua fachada e os respectivos caches MT5. O intervalo de 10 segundos e a
  leitura operacional permanecem sob o unico dono ativo.
- o guardiao de RAM usa limite padrao de 1600 MB, verifica a cada 60 segundos e
  registra saude no maximo a cada 10 minutos. Ele exige tres falhas de health
  consecutivas e possui mutex unico por porta antes de reiniciar. O reinicio
  preserva o ultimo estado armado e nunca altera plano, ordem, SL ou TP.
  A descoberta da porta ocorre apenas quando o PID muda; entre verificacoes o
  guardiao consulta diretamente o processo ja rastreado.
- falha UTF-8/JSON em snapshot operacional deve ser recuperavel no ciclo
  seguinte e nunca pode derrubar o dashboard inteiro.

Incidentes recorrentes devem virar missao de arquitetura/performance antes de
novas funcionalidades que aumentem custo de renderizacao, leitura MT5 ou leitura
de arquivos `.traderia`.

Em producao local no OneDrive, o Streamlit deve iniciar com
`--server.fileWatcherType none`. A recarga automatica por varredura do repositorio
ja causou porta aberta sem resposta HTTP e reinicios sucessivos pelo guardiao.
Essa opcao nao altera o ciclo MT5 de 10 segundos nem a leitura de mercado.

## Fronteiras Criticas

- `dashboard_app.py` nao deve importar providers diretamente.
- MT5 real nao roda no Codespaces.
- GitHub nao armazena runtime local.
- Recalculo pesado precisa ser explicito.
- Execucao real nao e autorizada por padrao.

## Variantes Dinamicas M8-M14 (historico aposentado)

M8-M14 foram variantes independentes das entradas M1-M7, na mesma ordem. Desde
2026-08-06 nao podem abrir novas ordens e permanecem somente para auditoria. Elas
preservam Alpha, timeframe, sinal, entrada, SL inicial, TP e RR do modelo de
origem. Somente o contrato pos-entrada muda para `DYNAMIC_PROTECT_ONLY`.

O Position Manager preserva o plano antes de 1,50R e, depois, pode apenas mover
o SL para um nivel mais protetivo por break-even ou ATR trailing. `EARLY_EXIT`
e `FULL_EXIT` permanecem proibidos. A entrada fixa e a variante dinamica podem
coexistir para comparacao A/B; a mesma variante nao pode repetir o mesmo plano
no mesmo candle. Os contratos historicos que usavam os numeros M8-M22 ficam
aposentados para novas entradas. O contrato completo esta em
`docs/architecture/DYNAMIC_EXIT_MODELS_M8_M14.md`.

## Modelo M8 XAUUSD/M5 por SMA20/50 e RSI14

O contrato ativo `MODELO_8_XAU_M5_SMA_RSI_REENTRY` e isolado dos IDs M8
historicos. Opera somente XAUUSD/M5. SMA20 e SMA50 simples definem apenas a
direcao: BUY quando SMA20 > SMA50 e SELL quando SMA20 < SMA50. A entrada e a
mercado enquanto o RSI14 estiver do lado do nivel 50 correspondente a direcao autorizada.
O SL fica `0,01` alem do ultimo pivo M5 confirmado por dois candles de cada
lado e nao existe TP fixo. O Position Manager executa Full Exit se candle M5
fechado confirmar RSI14 de 70 para baixo em BUY ou de 30 para cima em SELL, ou
se SMA20/SMA50 inverterem. A reentrada usa Buy Stop/Sell Stop exatamente no
extremo do último candle M5 fechado, com RSI50 e direção das médias válidos. Contrato completo em
`docs/architecture/OPERATIONAL_MODEL_M8_XAU_M5_SMA_RSI_REENTRY.md`.

## Família ativa M8-M12 — setups A-E

M8 é o setup A sem filtro adicional. M9/Setup B acrescenta ADX14 > 25.
M10/Setup C acrescenta distância `abs(SMA20-SMA50)/ATR14 >= 0,25`.
M11/Setup D acrescenta inclinação direcional da SMA50 em um candle,
normalizada pelo ATR14, `>= 0,05`. M12/Setup E exige os três filtros ao mesmo
tempo. Entrada, SL estrutural e Full Exit permanecem iguais ao M8, mas cada
modelo possui identidade e auditoria próprias. Os IDs M8-M12 anteriores não
foram reativados. Contrato completo em
`docs/architecture/OPERATIONAL_MODELS_M8_M12_XAU_TREND_FILTERS.md`.

## Modelo M15 XAUUSD/M5 (historico aposentado)

M15 foi aposentado para novas entradas em 2026-08-06. Seu contrato historico
permanece auditavel: operava somente XAUUSD/M5 e EMA20/50 definia a
direcao; a entrada fica um pip (`0,01`) alem do extremo do candle anterior
fechado e o SL inicial um pip alem do extremo oposto. O modelo nao possui TP
fixo. Depois da abertura, o Position Manager move o SL pelo ultimo candle M5
fechado somente quando o novo nivel for mais protetivo. O M15 nao usa
`EARLY_EXIT`, `FULL_EXIT` ou Lab pesado no runtime. O contrato completo esta em
`docs/architecture/OPERATIONAL_MODEL_M15_XAU_M5_BREAKOUT.md`.

## Modelo M16 XAUUSD/M5 (historico aposentado)

M16 foi aposentado para novas entradas em 2026-08-06. Seu contrato historico
permanece auditavel: era independente do M15 e operava somente XAUUSD/M5. O preco atual acima da
EMA20 prepara BUY STOP; abaixo da EMA20 prepara SELL STOP. A entrada fica um pip
alem do extremo do candle anterior, o SL nasce no extremo oposto exato e nao ha
TP fixo. Depois da abertura, o Position Manager move somente o SL pelo ultimo
candle fechado, sem EARLY_EXIT ou FULL_EXIT. Contrato oficial em
`docs/architecture/OPERATIONAL_MODEL_M16_XAU_M5_PRICE_EMA_BREAKOUT.md`.

## Regra De Correcao Interligada

## Família ativa M13-M17 — 17 pares Forex/M5

M13-M17 replicam os setups A-E de M8-M12 nos 17 pares Forex canônicos, com
buffer de um pip adaptado ao par e estado independente por modelo/par. Entrada
inicial, reentrada Stop, saída RSI 70/30, inversão SMA e filtros são avaliados
em M5 fechado. XAUUSD/BTCUSD ficam fora do escopo e conta real segue bloqueada.
Contrato: `docs/architecture/OPERATIONAL_MODELS_M13_M17_FOREX_TREND_FILTERS.md`.

M8-M17 iniciam com 201 registros M5 por ativo: 200 velas fechadas e a vela
atual em formacao. A janela e deslizante tanto em RAM quanto no arquivo
persistido: a vela nova substitui uma vela do mesmo horario ou remove a mais
antiga, sem ultrapassar 201. Quando
o ultimo lote vivo ainda nao esta disponivel, o runtime pode preaquecer os
indicadores com os 201 registros mais recentes do banco local, mas marca a serie
como `LOCAL_HISTORY_SEED` e bloqueia qualquer Trade Plan. A primeira leitura
MT5 valida substitui a semente, muda a origem para `LIVE` e somente entao o
modelo pode liberar entrada. O cache fica em `.traderia/`, usa escrita atomica
e nunca e versionado.

Os indicadores de M8-M17 sao calculados localmente somente depois que o MT5
entrega um lote integral, atual e cronologicamente coerente de 201 registros M5.
A vela atual e excluida do calculo. O plano registra
`indicator_source=LOCAL_MT5_CLOSED_CANDLES_200` e o provider exige
`indicator_closed_candle_time` igual ao candle fechado do Trade Plan. Lote
parcial, semente local, mistura de periodos ou cache antigo podem ser exibidos
para diagnostico, mas nunca autorizam ordem. A janela continua deslizante: a
202a observacao remove a mais antiga e mantem exatamente 201 em RAM e no cache.

O mesmo contrato vale para os modelos materializados pelo Lab. O Lab congela
os parametros pesquisados; o runtime atualiza EMA, SMA, RSI, ATR, ADX, momentum,
volatilidade e demais leituras com os 200 fechamentos atuais, sem executar
backtest nem recalcular o Lab pesado.

## Regra De Correcao Interligada

Todo erro encontrado deve ser avaliado no fluxo completo descrito em
`docs/architecture/END_TO_END_OPERATIONAL_FLOW.md`. A correcao deve atingir a
origem, contratos, consumidores, persistencia, telas e testes aplicaveis. Um
ajuste somente visual nao encerra um erro de fluxo, e toda causa estrutural deve
ser registrada tambem em `docs/EXECUTION_LOG.md`.

## Pesquisa De Grade Multiativos

`ALPHA017_MULTI_CURRENCY_GRID_MEAN_REVERSION` e uma hipotese `RESEARCH_ONLY`.
Ela pode usar o Replay de posicao unica para selecionar entradas candidatas,
mas isso nao valida uma grade. Grade, progressao de lote, exposicao correlacionada
e encerramento por cesta exigem contratos proprios de portfolio e uma missao
Demo posterior. A simples inclusao da Alpha no Lab nunca cria modelo operacional,
Trade Plan, ordem MT5 ou permissao de conta real.

## Modelo 21 Espelho Do M19

M21 e um modelo Demo independente derivado do contrato M19/ALPHA015. Ele usa o
mesmo candle M1 e os mesmos indicadores compartilhados, inverte BUY/SELL e
troca diretamente os niveis (`TP_M21 = SL_M19`, `SL_M21 = TP_M19`). A derivacao
dos fatores de risco ocorre a partir dos parametros M19 para impedir drift.
M19 nao depende do M21; ambos possuem cache, Trade Plan, duplicidade, comentario
MT5 e historico proprios. O provider admite no maximo uma posicao por modelo e
22 por par. Position Manager apenas audita os dois contratos fixos e conta real
permanece bloqueada.

## Modelo 22 Espelho Do M9

M22 e um modelo Demo independente derivado do Trend Pullback M9. Ele le os
mesmos candles M15/M1 e o mesmo gatilho fechado, inverte BUY/SELL e troca os
niveis (`TP_M22 = SL_M9`, `SL_M22 = TP_M9`). Com o contrato M9 atual, o M22
usa SL 2,5 ATR, alvo 1,25 ATR e RR 0,5. M9 permanece inalterado; os dois modelos
possuem decisao, cache, Trade Plan, duplicidade, comentario e historico proprios.

### Sublaboratorio Multi EA Trading

O `Multi EA Trading` e um fluxo exploratorio independente dentro da aba Lab.
Ele consome o extrato de posicoes e caches locais somente quando o usuario
aciona a pesquisa. A UI recebe apenas o JSON compacto pela `DashboardService`;
nao le CSV, SQLite nem chama provider diretamente durante o render.

O cache Forex oficial e aberto em modo read-only. Ouro usa exclusivamente
`.traderia/research/multi_ea_trading/history.sqlite`, com 5.000 candles em M1,
M5, M15, M30 e H1. Essa separacao impede que XAUUSD altere a lista oficial de
pares ou seja apagado pela atualizacao do banco operacional.

Resultados com `research_only=true` ou `operational_eligible=false` podem ser
exibidos no ranking de pesquisa, mas devem falhar fechado em selecao de setup,
configuracao vencedora operacional e construcao de Trade Plan.

## Retirada operacional sem perda de rastreabilidade

M3, M4, M6, M9, M11, M12, M13, M14 e M15 estao retirados desde 2026-08-12. A
lista de modelos autorizados para novas entradas nao pode conter esses IDs, e a
UI MT5/Relatorio nao deve oferece-los como selecao ativa. Seus contratos e
registros nao sao apagados: continuam disponiveis para historico, auditoria e
gestao de posicao legada.

O conjunto operacional vigente e M1, M2, M5, M7, M8, M10 e M16-M22. M5 pode
consultar resultados historicos de M1-M4, mas essa composicao nao concede
permissao de entrada aos modelos retirados M3 e M4.

O mapeamento de comentarios MT5 usa o numero canonico do modelo, nunca o indice
na lista de modelos ativos. Isso evita que a ausencia de M9, M11 ou M12 associe
um comentario `M10`, `M13` ou posterior ao contrato errado.

M19, M21 e M22 sao modelos ativos independentes. A reutilizacao de calculos ou
parametros de M9, M11 e M12 e uma dependencia matematica somente; nao autoriza
novas ordens dos modelos-base retirados.

O ranking do sublaboratorio seleciona candidatos exclusivamente no treino
cronologico. Score, classificacao e desempenho do holdout nao participam da
ordenacao; o holdout e somente auditoria posterior. O score e ajustado contra
o baseline aleatorio de 50%. A cobertura detalhada deve permanecer visivel por
ativo e timeframe, pois uma mesma posicao pode gerar eventos nao independentes
em varias series.

O bootstrap do extrato e feito pela fachada com `source_path` ou, em instalacao
limpa, pela variavel `TRADERIA_MULTI_EA_POSITIONS_CSV`. A tela nao acessa o CSV
diretamente.

## Historico do pico intratrade

O maior lucro flutuante observado por ticket pertence a camada de auditoria,
nao a estrategia. A leitura leve de posicoes atualiza um acumulador monotono em
`.traderia/runtime/mt5_position_profit_peaks.sqlite3`; o Relatorio consulta esse
estado quando a ordem estiver aberta ou fechada. Essa telemetria nao pode abrir
ou fechar ordem, mover SL/TP, recalcular indicadores ou iniciar o Lab.

## Modelo 24

O contrato completo do M24 esta em
`docs/architecture/OPERATIONAL_MODEL_24_XAU_RSI50_BASKET.md`. O modelo reutiliza
o cache compartilhado XAUUSD/M5, mas possui identidade, estado, comentario MT5,
resultado financeiro e auditoria independentes do M23. O provider sempre envia
`tp=0` para M24; a unica meta de lucro e a cesta liquida de +US$1.000. A entrada
inicial memoriza separadamente o cruzamento do preco na SMA20 e o cruzamento do
RSI14 em 50 e so entra a mercado se ambos continuarem validos na mesma direcao.
A reentrada nao exige novo cruzamento: gera BUY_STOP/SELL_STOP na maxima/minima
do ultimo M5 quando fechamento e RSI permanecem do lado permitido. O SL usa o
micro pivo 1+1 confirmado mais recente, limitado aos ultimos cinco M5 fechados.
O roteamento da cesta cria esse plano M5 antes da barreira do plano heuristico
H1; assim, `SEM_GATILHO_VALIDO` no plano-base nao impede a avaliacao do M24.
O Position Manager aceita somente novos micro pivos que apertem o stop. Depois de Full Exit
por retorno do RSI abaixo de 70 no BUY ou acima de 30 no SELL, o runtime M24
persiste por fonte e direcao a primeira oportunidade bloqueada. A segunda so e
reconhecida quando a chave inclui uma nova vela M5 fechada, impedindo que o ciclo
leve conte repetidamente o mesmo sinal. A entrada principal M24 nao consulta a
relacao SMA20/SMA50 e tambem nao fecha por inversao dessas medias; essa protecao,
assim como a perda do RSI50, permanece restrita as reentradas.

## Modelo 25

O contrato oficial esta em
`docs/architecture/OPERATIONAL_MODEL_25_MULTI_ASSET_RSI50_BASKET.md`. O M25
replica a logica operacional do M24 nos 19 ativos canonicos, sempre em M5, mas
possui identidade, estado por simbolo, comentario, duplicidade, auditoria e
cesta financeira proprios. Cada ativo pode manter no maximo uma entrada
`INITIAL` e uma `REENTRY`; os demais ativos continuam independentes.

O M25 reutiliza o snapshot M5 compartilhado e nunca executa Lab pesado no ciclo
leve. O Full Exit coletivo de `+US$1.000` considera somente posicoes M25. Conta
real permanece bloqueada e nenhuma ativacao automatica ocorre na implantacao.
