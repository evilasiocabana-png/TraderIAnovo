# M29 / M7: canal de resultados por pivos

## Regra vigente - 2026-09-21

Confirmacao operacional: um encerramento fora da borda, nao dois.
Primeiro canal confirmado ou mudanca de tendencia define NORMAL na alta e
ESPELHADO na baixa. Rompimento inferior antecipa ESPELHADO; superior antecipa
NORMAL. Reancoragem na mesma tendencia nao desfaz a antecipacao; lateralizacao
preserva o modo. No mesmo fechamento o rompimento tem precedencia.
Lotes preservados: normal 0.10, espelhado 0.20. Referencia M23/M7 e sincronizacao
preservadas. Esta secao substitui requisitos anteriores conflitantes abaixo.

Autorizado pelo usuario em 2026-09-18. Substitui a sequencia G/P somente para
escolher o modo do M7 no M29, inclusive seu setup copiado dentro do M23.

## Referencia

- Posicoes M23 S7 totalmente encerradas, separadas por conta e ativo.
- Resultado liquido de todos os negocios da posicao: lucro, comissao, swap e taxa.
- Ordem cronologica de encerramento, com identificador como desempate.
- Posicoes abertas/parciais, M29 proprio e M23 S29 nao alimentam a referencia.
- Historico indisponivel/incompleto ou estrutura ainda ausente bloqueia a
  definicao de novo plano; nao reaproveita silenciosamente um modo antigo.

## Geometria causal

Reutiliza analyze_equity_structure com sensibilidade 1.0: extremo confirmado
apos movimento contrario de pelo menos a mediana dos ultimos 20 resultados
absolutos nao nulos conhecidos. Empates sao resultados de zero, nao ganhos.

Exige dois topos e dois fundos confirmados na mesma direcao. Na alta, une os
dois fundos e posiciona uma paralela pelo maior residuo dos dois topos. Na baixa,
une os dois topos e posiciona uma paralela pelo menor residuo dos dois fundos.
As quatro ancoras nao precisam tocar as duas retas: ligar exatamente os quatro
extremos em duas retas nao garante paralelismo. Estrutura mista nao cria canal.
Antes do primeiro canal, aguarda estrutura; depois, mantem o canal anterior.

Cada encerramento e comparado com o canal conhecido ANTES dele, mesmo que nao
forme pivo. Empates podem ficar fora de uma borda inclinada. Toque na borda e
considerado dentro. Nao ha uso de posicoes flutuantes nem de dados futuros.

Dois pontos consecutivos abaixo do piso: ESPELHADO. Dois acima do teto: NORMAL.
Um ponto dentro zera a contagem, mas mantem o modo. Trocar de borda reinicia em
um. O canal nao e reposicionado entre as duas confirmacoes. Geometria identica
nao reinicia a contagem. Novos pivos podem atualizar o canal fora dessa espera.
O modo inicial e NORMAL apos a primeira estrutura valida; todos os eventos do
historico conciliado sao reproduzidos deterministamente.

## Preservado

Mesma sincronizacao com M23, mesmo sinal confirmado, espera de encerramento da
dupla, SL/TP, RR, lotes, fontes M1/M2/M5/M7/M8/M10/M18/M20, filtros e agenda.
M21/M22 continuam fora. Nao altera selecao de modelos ou autorizacao da Real.
M23 continua executando normalmente suas fontes originais.

O painel oferece a mesma geometria, com historico inteiro visivel. Seus filtros,
periodo, agrupamento e controles exploratorios nao mudam a regra operacional,
fixa em sensibilidade 1 e duas confirmacoes. O modo operacional usa o historico
broker conciliado por conta/ativo, nao o recorte do grafico.

## Limitacao

Este criterio foi escolhido apos estudo pequeno. Testes de software verificam
causalidade e comportamento, nao comprovam rentabilidade. Espelhamento nao
garante resultado financeiro oposto devido a execucao, SL/TP e custos.
# Atualizacao operacional 2026-09-21

Confirmacao vigente: UM encerramento fora da borda. Abaixo do piso ativa
ESPELHADO; acima do teto ativa NORMAL. Substitui o requisito anterior de dois
encerramentos descrito no historico abaixo. Formacao por pivos, sincronizacao
e lotes permanecem inalterados.
