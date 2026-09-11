# Filtros adicionais M23 — 11/09/2026

O usuario solicitou um bloco separado de filtros adicionais e autorizou explicitamente bloquear novas entradas nos tres contextos de compra do M23 originada no M7 no ouro. A camada original continua como referencia, sem recalculo de suas regras. O novo catalogo e manual, exploratorio, com uma ocorrencia por cenario; nao e apresentado como estatisticamente validado.

## Regras e escopo

- Compra com tendencia alinhada, estrutura contra, RSI >=70, ADX >=25, ATR normal, Londres e ORDER_BLOCK_UP:WITH.
- Compra com tendencia e estrutura neutras, RSI de30 a menos de50, ADX <20, ATR normal, Londres e FVG_RETEST:AGAINST.
- Compra com tendencia contra, estrutura alinhada, RSI de30 a menos de50, ADX >=25, ATR normal, Nova York e SWEEP_HIGH:AGAINST.

Todas exigem MODELO_7_LAB_XAU_BTC, XAUUSD, BUY, contexto sincronizado VALID e igualdade exata dos sete campos. A integracao ocorre somente em _mt5_model23_variant_from_source. M7 direto, vendas, Bitcoin e outras fontes nao correspondem. O bloqueio e verificado em cada avaliacao; quando o contexto deixa de corresponder, essa camada deixa de bloquear. Nao e remocao permanente do sinal nem uma trava de espera por tempo.

## Integracao

O catalogo separado usa OFF, OBSERVE ou BLOCK, sendo BLOCK a configuracao explicitamente autorizada. Ausencia ou formato invalido nao cria uma regra implicita; a UI informa o erro. O portao de contexto sincronizado e os bloqueios originais mantem precedencia. Uma correspondencia adicional transforma somente a nova proposta M23 em WAIT, com motivo M23_ADDITIONAL_FILTER_BLOCKED. Lotes, stops, alvos e posicoes ja abertas nao sao editados.

O painel Replay recebe o bloco Filtros adicionais logo apos Replay dos Sinais M23, com modo, cenarios, amostra exploratoria e condicoes completas. Parametros de cada avaliacao e o diagnostico local registram modo, resultado e identificadores adicionais separadamente dos campos do filtro antigo.

O catalogo versionado nao contem tickets ou resultados financeiros privados. Evidencia do estudo permanece em .traderia/research/m23_additional_filters/evidence.json e pode ser consultada no painel local. O arquivo original .traderia/research/m23_pattern_filter/report.json e conferido por SHA-256 e preservado.

## Validacao

Testes cobrem correspondencia exata, cada campo divergente, campos ausentes, outras fontes/ativos/direcoes, contexto invalido, modos OBSERVE/OFF/BLOCK, catalogo malformado, prioridade das regras antigas, preservacao dos contratos M23 e registro da decisao. O bloco visual e renderizado isoladamente com Streamlit AppTest. Nenhuma ordem de teste e enviada.

Nao foi realizado replay financeiro integral nem validacao adicional em cem mil candles nesta instalacao. Valores historicos associados nao sao economia comprovada, e bloqueios futuros podem afetar ganhos e reentradas.

Resultado: 147 testes aprovados e renderizacao isolada do bloco com Streamlit AppTest aprovada. Um contrato existente inicialmente carregou o relatorio real do diretorio do projeto; repetido em diretorio isolado, passou. Os 29 testes novos e os demais contratos passaram. Revisao independente confirmou escopo e precedencia.
