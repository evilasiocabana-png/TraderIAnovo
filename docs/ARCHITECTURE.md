# Architecture

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
  M6 e um baseline historico independente e pode enviar somente ao MT5 Demo.
- M6 reproduz o `TREND_MOMENTUM` original congelado no marco `a3bc912`:
  M1, media simples 20/50, momentum 10, volatilidade 20, RSI14 e decisao no
  ultimo candle fechado. A entrada usa o preco vivo seguinte.
- O risco inicial do M6 usa a maior distancia entre 2 ATR e 0,10% do preco,
  com alvo RR2. Sua saida e fixa por primeiro toque no SL inicial ou TP RR2.
  O M6 nao usa break-even, trailing, `EARLY_EXIT`, `FULL_EXIT` ou qualquer
  movimento do Position Manager.
- M2-M5 usam o ultimo candle fechado, entram no proximo preco vivo dentro da
  janela autorizada e preservam SL/TP fixos da pesquisa.
- O Position Manager apenas audita M2-M5 sob `RESEARCH_FIXED_SL_TP`: nao move
  SL e nao executa `FULL_EXIT` nesses modelos.
- Para M6, o Position Manager possui bypass defensivo inclusive para snapshots
  antigos que ainda declarem `DYNAMIC_POSITION_MANAGER`.
- M7 preserva a mesma entrada congelada do M6 em um contrato independente:
  `MODELO_7_TREND_MOMENTUM_DYNAMIC` + `BETA007_DYNAMIC_PROTECT_ONLY_V1`.
- M7 mede o progresso pelo risco inicial imutavel, mantem o SL antes de 1,50R
  e, depois, permite somente break-even ou ATR trailing mais protetivo. Ele
  nunca executa `EARLY_EXIT` ou `FULL_EXIT`.
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

## Fronteiras Criticas

- `dashboard_app.py` nao deve importar providers diretamente.
- MT5 real nao roda no Codespaces.
- GitHub nao armazena runtime local.
- Recalculo pesado precisa ser explicito.
- Execucao real nao e autorizada por padrao.

## Variantes Trend Pullback M8-M10

M8, M9 e M10 sao modelos operacionais independentes derivados da formula M2,
sem copiar ou alterar o estado do M2. M8 usa H1 para direcao e M5 para entrada;
M9 usa M15 e M1; M10 usa D1 e M15. Todos usam EMA20/50 no contexto, EMA9/21,
ADX14 e pullback no timeframe de entrada, com SL fixo 1,25 ATR e TP fixo 2R.

O Market Data coleta somente os timeframes requeridos e reaproveita o cache
compartilhado. O Lab operacional congela a decisao por candle fechado; o Robo
Demo materializa o Trade Plan; o provider grava `TraderIA M8`, `TraderIA M9`
ou `TraderIA M10`; o Position Manager nao move o SL desses contratos fixos; o
Relatorio identifica cada modelo separadamente. O limite e uma posicao por
modelo e dez por par. Conta real permanece bloqueada.

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

O ranking do sublaboratorio seleciona candidatos exclusivamente no treino
cronologico. Score, classificacao e desempenho do holdout nao participam da
ordenacao; o holdout e somente auditoria posterior. O score e ajustado contra
o baseline aleatorio de 50%. A cobertura detalhada deve permanecer visivel por
ativo e timeframe, pois uma mesma posicao pode gerar eventos nao independentes
em varias series.

O bootstrap do extrato e feito pela fachada com `source_path` ou, em instalacao
limpa, pela variavel `TRADERIA_MULTI_EA_POSITIONS_CSV`. A tela nao acessa o CSV
diretamente.
