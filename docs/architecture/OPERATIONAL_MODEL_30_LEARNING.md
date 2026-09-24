# M30 e Aprendizado

## Contrato autorizado

M30 executa novas copias na mesma conta **Demo hedging** do M23. Real e conta
netting sao recusadas antes do envio. O M23 permanece baseline, sem novo filtro.
Identidade: `MODELO_30_ADAPTIVE_M23_SOURCE_*`, magic `260630`, comentario
`TraderIA M30 S<origem> P<ticket M23>`. M30 nao alimenta M23 nem M29.

Uma ordem M23 aceita produz no maximo uma tentativa M30 por conta/ticket. O
contrato copiado preserva direcao, volume e SL/TP efetivamente enviados, incluindo
TP zero, ordem pendente e parametros de saida. Sao ordens separadas: slippage,
rejeicao ou diferenca de encerramento podem produzir resultados diferentes.
Resultado incerto permanece bloqueado para repeticao, nunca e reexecutado as cegas.

As posicoes M30 possuem cesta propria de +US$1000, com estado e auditoria
`model30_basket_state.json` / `model30_basket_audit.jsonl`. Reutiliza-se o manager
existente com predicado explicito por magic/comentario; o predicado padrao M23 nao
muda. O Position Manager recebe a origem e o plano de cada ticket M30. Os limites
tecnicos existentes do terminal nao sao elevados. Nao altera posicoes anteriores.

## Persistencia e custo

Arquivo: `.traderia/learning/signals.sqlite3`, SQLite WAL separado do banco de
mercado e do cache UI. Tabelas de sinais, variantes, eventos, execucoes, deals
nativos, baselines, pares M30, candidatos e diario. Sem exclusao automatica.
Backup consistente deve usar a API SQLite `Connection.backup`, nao copiar apenas
o arquivo principal enquanto ha um WAL ativo. Runtime nunca vai para Git.

Fila limitada a 512 itens de no maximo 16 KiB; um lote pendente adicional de ate
100 itens para repetir transacao falhada, e LRU de 2048 identidades. Escritor
isolado; falha de observacao nao modifica o resultado M23. A primeira importacao
e limitada aos ultimos 2 MiB do log e identificada como historica, nunca como
captura prospectiva. Cursor de bytes persistente acompanha todas as novas linhas.
Nao guarda screenshots nem ticks completos.

UI pagina 50 registros (maximo 100). Reconciliacao nativa: ate 10 tickets/minuto,
subprocesso somente leitura, timeout 5s, gate existente sem fila prolongada.
Conta precisa coincidir; logs antigos sem identificacao ficam nao conciliados.
Entrada e saida sao conciliadas por deal unico, com comissao/swap/taxa uma vez.
Ordem aceita nao significa fill; parcial, cancelada e custos ausentes sao explicitos.

## Observacao causal

Observa planos efetivamente avaliados, inclusive os que nao chegam ao envio, por
fonte, ativo e timeframe. Nao executa fontes desabilitadas so para preencher dados.
Captura primeiro contexto imutavel, indicadores numericos, canal/estado existente,
geometria, decisao/motivo e hash dos setups/configuracoes/Replay existentes.
Original, copia e espelho compartilham grupo, mas preservam variantes de execucao.
Sem candle identificavel nao inventa nova identidade a cada polling.

## Ciclo estatistico automatico

Implementado em `learning_policy.py`; nao e um LLM nem promete lucro. Nao refaz
Replay pesado. A versao atual dos filtros/Replay e baseline, nao ponto de partida
para apagar pesquisas anteriores. Agenda interna persistente abre revisao diaria
enquanto o aplicativo esta ativo; no maximo um candidato novo por sete dias.

Politica inicial de engenharia, conservadora e versionada:

1. Somente grupos prospectivos M23 integralmente encerrados, conta confirmada e
   custos nativos completos. Sem resultado hipotetico atribuido a nao executados.
2. Pelo menos 200 grupos descoberta, 100 calibracao e 30 dias distintos. Purga
   posicoes que cruzam a fronteira temporal. Contextos simples de origem, ativo,
   direcao, tendencia e modo, com ao menos 30/15 casos nas duas amostras.
3. Seleciona apenas um contexto negativo nas duas amostras. Congela candidato,
   politica, baseline e data; dados anteriores nunca validam esse candidato.
4. Exige ao menos 100 grupos futuros, 30 no contexto, 14 dias distintos e 14 dias
   decorridos. Usa bootstrap de blocos diarios, intervalo de 99%, ganho inferior
   maior que zero, drawdown nao pior e descarte de vencedoras <=25%.
5. A simulacao mantem oportunidades reais M23 fixas e retira as rejeitadas pelo
   filtro. Nao inventa fills M30 nem presume reproducao exata da curva, pois a cesta
   e trajetoria operacional podem divergir. O grafico real usa apenas pares
   efetivamente conciliados; simulacao e execucao sao rotuladas separadamente.
6. Promove atomicamente apenas a admissao M30 Demo. Sem evidencia, mantem baseline.
   Mudanca de baseline ou deterioracao futura estatisticamente sustentada reverte
   para baseline. Maximo 90 dias sem evidencia invalida candidato pendente.

Diario persistente em portugues: em teste, inconclusivo, aplicado, rejeitado,
monitorando e revertido, com amostra/metricas/motivo. A UI atualiza a cada 15s,
sem encher o diario com uma mensagem repetida a cada ciclo. Ativar/desativar novas
copias M30 nao fecha posicoes. M23 e Real nao recebem filtros aprendidos.

## Superficies e verificacao

Aba Aprendizado; painel e entradas teoricas M30 em MT5; painel pareado e grafico
real em Relatorios. Sem historico pareado, exibe aguardando dados, nao lucro fake.
Testes cobrem SQLite/restart/custos/fila, clones/provider, conta Demo/netting,
idempotencia, isolamento de cesta, politica futura, promocao/reversao e UI.

Verificacao local em 2026-09-24: 272 testes e dois subtestes aprovados. Recarga
controlada, health OK, conta Demo hedging confirmada, Real desligada e selecao,
estado online e agenda byte-identicos. Banco com 313 variantes, incluindo 60
prospectivas, 4.44 MiB; consulta de pagina em aproximadamente 3 ms. Aprendizado
validado no navegador e painel pareado em Relatorios mostrando Demo habilitada
e aguardando conciliacao. A leitura automatizada da extensa aba MT5 apresentou
timeouts intermitentes; isso nao foi usado como evidencia de falha do executor.
Nenhuma ordem M30 natural nem filtro promovido foi observado nesta verificacao.
Esses resultados exigem sinais e encerramentos futuros; nao foram fabricados.

O conteudo exato do indice Git tambem foi exportado e validado isoladamente:
109 testes e dois subtestes passaram, sem depender das alteracoes anteriores
na arvore de trabalho. A recarga final preservou os mesmos arquivos de estado;
a coleta alcancou 387 variantes (banco e WAL aproximadamente 4.90 MiB).
A tabela teorica consulta exclusivamente as variantes M23, sem ser deslocada
pela paginacao dos registros de outras fontes.
