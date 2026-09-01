# Modelo 28 - Pattern Miner Adaptativo Demo

## Identidade

- Identificador persistido: `MODELO_28_PATTERN_MINER_SHADOW`
- Nome curto: `M28`
- Origem: `REPLAY_PATTERN_MINER`
- Contrato: `M28_PATTERN_BRIDGE_V6_EMPIRICAL_CONTRACTS`
- Alpha: `ALPHA028_PATTERN_MINER_PROMOTED`
- Beta: `BETA028_REPLAY_DERIVED_EMPIRICAL_CONTRACT`
- Execucao: `DEMO_ADAPTIVE`
- Ativos e timeframe: os `19` mercados canonicos, todos em `M5`
- Volume: `0.11`

O sufixo `SHADOW` permanece no identificador apenas para compatibilidade com os
registros locais criados na fase de validacao. O M28 agora e um modelo
operacional selecionavel, autorizado exclusivamente na conta Demo.

## Objetivo

O M28 transforma os 100 mil candles de cada ativo em uma biblioteca de
`Pattern ID -> contrato operacional`. Cada contrato preserva a sequencia causal,
o contexto, a direcao, a distancia empirica do SL, a distancia empirica do TP,
o prazo maximo e o custo observado. No mercado ao vivo, os mesmos detectores
reconhecem um Pattern ID ja aprendido e materializam exatamente o contrato
versionado daquele padrao. Nao existe um SL, TP, RR ou prazo universal do M28.

## Fluxo oficial

```text
historicoATIVO (19 bases independentes)
  -> Replay / Event Engine
  -> entrada simulada na abertura da vela seguinte
  -> Pattern Miner com spread historico, validacao e OOS
  -> descoberta causal do padrao e de sua distribuicao MAE/MFE nos primeiros 60%
  -> congelamento de SL, TP e prazo especificos do Pattern ID
  -> avaliacao cronologica do contrato congelado em Validation e OOS
  -> ranking adaptativo por ativo e familia de padrao
  -> ate tres contratos distintos por ativo
  -> classificacao VALIDATED ou EXPLORATION_DEMO
  -> ativacao automatica do portfolio dos 19 ativos
  -> OperationalPatternSpec habilitada
  -> cache compartilhado ATIVO/M5 em candle fechado
  -> LivePatternTracker
  -> SignalCandidate
  -> seletor adaptativo
  -> Trade Plan M28 com entrada ao proximo preco negociavel, SL, TP, prazo e lote 0.11
  -> MT5DemoRobotService
  -> DemoExecutionService
  -> provider MT5 Demo
```

Nao existe chamada direta do Pattern Miner ao provider. O motor reconhece e
decide; o robo valida; o `DemoExecutionService` executa. A conta Real continua
bloqueada pelo provider.

## Regras operacionais

- Entrada historica: abertura da vela seguinte a que conclui a sequencia causal.
- Entrada ao vivo: primeiro preco negociavel disponivel depois da conclusao; as
  distancias aprendidas sao reancoradas nesse preco sem mudar o contrato.
- Stop: quantil da distribuicao MAE daquele Pattern ID, medido em ATR na
  descoberta. Nao existe grade universal de stop.
- Target: quantil da distribuicao MFE daquele Pattern ID, medido em ATR na
  descoberta. O RR e consequencia de `TP_ATR / SL_ATR`, nao uma entrada fixa.
- Prazo: horizonte empirico escolhido para o Pattern ID entre os horizontes
  pesquisados; no vencimento, a posicao recebe `FULL_EXIT`.
- Custos da pesquisa: spread registrado no candle de entrada e convertido para
  R pela distancia empirica do stop. Comissao e swap nao existem nos CSVs e
  permanecem declarados como indisponiveis, nunca estimados silenciosamente.
- Ordem: mercado, somente apos candle M5 fechado.
- Volume: `0.11` lote.
- Escopo: 19 ativos com contrato proprio; nenhum contrato de um ativo pode
  consumir candle de outro.
- Evidencia: `VALIDATED` identifica sobrevivencia integral; `EXPLORATION_DEMO`
  identifica pesquisa positiva na descoberta, ranqueada com Validation e OOS.
- Repeticao: cada nova ocorrencia completa pode entrar uma vez, mesmo que ainda
  nao exista resultado anterior daquele padrao.
- Expiracao do sinal: a selecao vale apenas para a primeira oportunidade de
  envio depois do candle de conclusao. A posicao usa o prazo do contrato.
- Ausencia de padrao: `WAIT`, sem inventar direcao ou geometria.
- Geometria BUY obrigatoria: `SL < entrada < TP`.
- Geometria SELL obrigatoria: `TP < entrada < SL`.

## Idempotencia

Cada conclusao recebe um `pattern_occurrence_id`. O M28 grava esse valor em
`setup_id` e `route_key`; junto com candle, modelo e versao do plano, ele forma
a identidade operacional. A mesma ocorrencia nao pode gerar duas ordens. O
`Pattern ID` identifica o desenho aprendido; a ocorrencia identifica uma
aparicao unica desse desenho no mercado ao vivo.

## Chaveamento

O M28 aparece como caixa `M28` no Chaveamento operacional. Somente uma selecao
persistida que contenha M28 permite novas ordens desse modelo. Marcar outros
modelos nao transforma o M28 em fonte da cesta M23: as duas rotas permanecem
independentes.

## Persistencia e auditoria

Os contratos versionados continuam no registro compartilhado:

`.traderia/research/historicoXAU/model28_operational_patterns.json`

Cada dataset preserva seu proprio cache e `pattern_miner_summary.json`. Cada
contrato v6 grava tambem `stop_rule`, `target_rule`, `expiration_rule`,
`stop_atr`, `target_atr`, `max_holding_candles`, quantis, metodo de derivacao e
custo medio observado em cada bloco. O snapshot enviado preserva ativo,
Pattern ID, versao, ocorrencia, entrada reancorada, distancias, lote e contrato.

## Guardrails

- os candidatos sao descobertos exclusivamente nos primeiros `60%`;
- os 12 melhores candidatos da descoberta sao medidos nos `20%` de Validation
  e nos `20%` OOS para formar o ranking adaptativo Demo;
- a certificacao `VALIDATED` continua exigindo expectativa liquida minima de
  `+0.05R` e limite inferior de confianca de 80% positivo nos tres blocos;
- `EXPLORATION_DEMO` exige evidencia positiva e amostra minima na descoberta,
  mas conserva no contrato os resultados negativos de Validation/OOS em vez de
  esconde-los ou trata-los como aprovacao estatistica;
- o portfolio escolhe ate tres familias distintas por ativo, priorizando
  `VALIDATED`, quantidade de blocos positivos e score adaptativo;
- o Replay desconta o spread efetivamente registrado na entrada, convertido
  para R pela distancia empirica do stop;
- somente uma operacao do mesmo contrato pode permanecer aberta; sinais
  sobrepostos sao ignorados como ocorreria na execucao;
- trades sem o horizonte futuro exigido pelo proprio contrato no fim da amostra
  permanecem abertos e nao viram ganhos ou perdas artificiais;
- a promocao manual foi substituida pela ativacao automatica do portfolio dos
  19 ativos; contratos exploratorios podem enviar apenas para a conta Demo;
- o forward posterior a base congelada monitora degradacao e aderencia da
  execucao, mas nao bloqueia o funcionamento do M28 na conta Demo;
- somente contratos v6 empiricos habilitados participam da leitura ao vivo;
- contratos v2, v3, v4 e v5 permanecem no JSON para auditoria, mas nao geram
  novas ordens enquanto a biblioteca v6 estiver ativa;
- o M28 nao recalcula o Lab pesado no ciclo de 10 segundos;
- somente candles fechados e cronologicamente novos sao consumidos;
- os 19 replays Maximum rodam um por vez e liberam RAM entre ativos;
- o runtime so atualiza mercados M28 quando M28 estiver selecionado;
- o filtro de regime legado nao e reaplicado sobre a decisao causal do M28;
- toda ordem passa pelos gates temporal, plano, duplicidade e conta Demo;
- conta Real permanece proibida;
- falha ou ausencia de dados resulta em `WAIT`.

## Diagnostico legado de 31/08/2026

A verificacao forward encontrou 168 operacoes M28 pareadas: expectativa real
de `-0.583R` por operacao, taxa de acerto de `32.7%`, custo medio de `0.412R` e
desvio adverso medio de `0.070R`. No mesmo conjunto, o Replay antigo indicava
`+18R`, enquanto a execucao acumulou `-97.97R`.

Os 19 historicos de 99.999 candles foram reprocessados pelo contrato v3, um por
vez. Todos os 1.900 rankings analisados tinham pelo menos 100 ocorrencias, mas
nenhum obteve score positivo depois da proxima abertura, do atrito de `0.50R`
e da exigencia de resultado positivo nos tres periodos. Por isso o estado
operacional correto e `WAIT`: nao existe contrato v3 autorizado no momento.

O diagnostico v4 corrigiu tambem a sobreposicao de posicoes. Quatro contratos
historicos sobreviveram: `AUDJPY`, `CADCHF`, `GBPAUD` e `GBPCAD`, todos com stop
de `2 ATR` e alvo de `2R`. No complemento posterior a base original, porem,
houve somente uma operacao resolvida (`GBPAUD`, `-1.25R`), contra o minimo de 20
por contrato. Isso ainda e insuficiente para uma conclusao forward, mas nao
anula a validacao historica: os quatro contratos estao executaveis no M28 Demo
e o forward permanece como painel de acompanhamento.

Os resultados completos ficam em
`.traderia/research/model28_optimizer/geometry_context_v4.json` e
`.traderia/research/model28_optimizer/geometry_context_v4_forward.json`. A
ausencia de amostra forward nao altera os criterios de pesquisa nem autoriza
operacao em conta Real.

## Historico do portfolio adaptativo v5 de 01/09/2026

Os 19 historicos foram reprocessados sequencialmente, sem compartilhar estado
entre ativos. O resultado operacional possui 50 contratos distribuidos nos
19 mercados: 4 contratos `VALIDATED` e 46 contratos
`EXPLORATION_DEMO`. Nao houve falha de dataset ou de processamento.

O v5 nao transforma resultado OOS negativo em validacao. Ele o preserva no
contrato, reduz score e confianca, e limita esse contrato a exploracao Demo.
Esse mecanismo permite observar todos os ativos sem declarar uma vantagem
estatistica inexistente. Conta Real continua proibida.

O relatorio legado fica em
`.traderia/research/model28_optimizer/adaptive_portfolio_v5.json`. A politica
operacional e: a primeira ocorrencia causal completa sempre pode liberar uma
tentativa; nao se aguardam resultados anteriores. Se mais de um contrato
concluir no mesmo candle do mesmo ativo, o desempate usa tier, score adaptativo,
confianca, resultado futuro conservador e tamanho da amostra, nessa ordem.

## Biblioteca empirica v6

O v6 substitui a grade universal de ATR/RR por contratos aprendidos por Pattern
ID. Para cada padrao, somente a parte Discovery fornece as distribuicoes de MAE
e MFE e escolhe o horizonte. Essa geometria e congelada antes de Validation e
OOS. Assim, os dois blocos posteriores medem o contrato sem reajusta-lo com
informacao futura.

O relatorio operacional atual fica em
`.traderia/research/model28_optimizer/empirical_pattern_contracts_v6.json`.
Cada linha explica de onde vieram SL, TP e prazo. O runtime rejeita qualquer
linha sem essas regras empiricas, qualquer schema anterior ou qualquer custo
arbitrario. O contrato versionado permanece imutavel para que Replay, ordem e
resultado possam ser comparados; a adaptacao ao vivo ocorre pela escolha de
outro Pattern ID aprendido quando a sequencia observada muda.

O reprocessamento completo de 01/09/2026 gerou 50 contratos em 19 mercados:
20 `VALIDATED` e 30 `EXPLORATION_DEMO`, sem falha de dataset ou processamento.
O XAUUSD possui tres contratos ativos e independentes: `BOS_UP > FVG_UP`
(`SL 3.565937 ATR`, `TP 3.675709 ATR`, 100 candles),
`FVG_MITIGATION > FVG_FILL > OB_RETEST` (`SL 1.504280 ATR`,
`TP 1.069973 ATR`, 5 candles) e
`FVG_UP > DISPLACEMENT_UP > ORDER_BLOCK_UP` (`SL 2.053308 ATR`,
`TP 1.616534 ATR`, 10 candles). Os tres permanecem restritos a Demo porque nao
passaram pela validacao/OOS robusta; isso nao impede observacao operacional,
mas impede qualquer declaracao de vantagem para conta Real.

## Recorrencia do mesmo padrao

Cada contrato mede separadamente se o mesmo padrao exato costuma ocorrer
isolado, em pares, trios, quatro vezes ou cinco vezes ou mais. Uma sequencia e
considerada o mesmo episodio enquanto a distancia cronologica entre ocorrencias
consecutivas nao exceder o prazo empirico do proprio contrato; depois desse
intervalo, a proxima ocorrencia inicia um episodio novo. A mesma regra
cronologica vale no Replay e no mercado ao vivo, inclusive em fins de semana e
interrupcoes de negociacao.

O limite de repeticao gravado no contrato segue estas regras:

1. a primeira ocorrencia do episodio e sempre elegivel;
2. o comprimento mediano define o tamanho candidato, ou seja, cada posicao deve
   ter sido alcancada em pelo menos 50% dos episodios;
3. cada posicao adicional precisa de pelo menos 10 amostras, expectativa liquida
   minima de `0.05R` e limite inferior de confianca de 80% positivo;
4. uma posicao fraca ou sem amostra encerra a cota, mesmo que existam sequencias
   mais longas no historico;
5. o diario persistido preserva a posicao da sequencia apos reinicio;
6. Replay forward e runtime ao vivo aplicam a mesma janela e a mesma cota.

Essa medicao informa frequencia e expectativa observadas; ela nao transforma
recorrencia em garantia de resultado e nao libera o M28 para conta Real.

## Rollback

Desmarcar M28 interrompe novas entradas sem alterar posicoes anteriores. O
identificador persistido e o registro de padroes foram preservados para que o
rollback para Shadow nao exija migracao dos arquivos de pesquisa.

## Validacao Forward Na Aba Historico MT5

A aba `Historico MT5` comprova se o comportamento posterior a pesquisa
permanece igual ao plano promovido pelo Replay:

1. cada CSV original de 100.000 candles M5 permanece congelado e somente leitura;
2. o corte de cada ativo e a ultima vela fechada do seu CSV original;
3. `Atualizar dados` consulta o MT5 somente sob demanda e baixa apenas candles M5
   fechados posteriores ao ultimo corte incremental daquele ativo;
4. os complementos ficam isolados em
   `.traderia/research/model28_forward_validation/<ATIVO>/` e nunca sao anexados
   ao dataset original;
5. o mesmo `LivePatternEngine` causal recebe 200 candles anteriores apenas para
   aquecimento e processa como evidencia somente o complemento pos-corte;
6. o ciclo leve grava em
   `.traderia/runtime/model28_operational_availability.jsonl` um heartbeat
   compacto com robo armado, M28 selecionado, ciclo concluido e ativos com
   candles MT5 validos;
7. os sinais teoricos sao confrontados com
   `.traderia/mt5_demo_execution.jsonl` por ocorrencia, ativo, padrao, lado e
   candle, incluindo entrada, SL e TP;
8. ausencia, rejeicao ou divergencia ficam explicitas e nunca alteram
   automaticamente o Replay, o modelo promovido ou a execucao.

As curvas da validacao permanecem independentes e usam somente janelas
operacionais comprovadas. Um sinal teorico entra na comparacao apenas quando,
no fechamento daquele candle e para aquele ativo, o heartbeat confirma robo
armado, M28 selecionado, dados MT5 validos e ciclo concluido. Periodos sem
heartbeat sao classificados como nao observaveis e nunca como falha de envio.
A curva teorica reancora a entrada na abertura seguinte e inclui os sinais
elegiveis que ja atingiram SL, TP ou o prazo empirico do contrato, descontando
o spread registrado; a curva executada inclui as operacoes M28 das mesmas
janelas efetivamente encerradas no MT5. Ambas usam `R`,
mas nao sao artificialmente pareadas nem truncadas para possuir a mesma
amostra. O funil `sinal teorico -> tentativa -> conferencia -> encerramento`
mede se o sinal chegou ao executor e a tabela identifica ausencia, rejeicao ou
divergencia de geometria. O pareamento por ticket permanece apenas como dado de
auditoria interna, nao como filtro das duas curvas principais.

A mesma validacao deve abrir os resultados por ativo, mostrando quantidade de
sinais, desfechos teoricos em R, tentativas, confirmacoes, encerramentos, lucro
liquido em USD e resultado normalizado em R. Essa abertura e calculada apenas do
relatorio persistido e nao consulta o MT5, permitindo identificar concentracao
de risco sem acrescentar carga ao ciclo operacional.

Essa atualizacao nao participa do ciclo leve de 10 segundos, nao recalcula os
100.000 candles e nao possui capacidade de enviar ou modificar ordens.
