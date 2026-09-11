# M28 original com contexto sincronizado - 11/09/2026

## Escopo autorizado e resultado

O usuario pediu o setup original do M28, sem o filtro contextual baseado nas
66 operacoes encerradas, e manteve a correcao de sincronizacao dos candles.
O interruptor operacional do overlay foi desativado no construtor de todas as
instancias, inclusive o registro padrao. O modulo e a politica de estudo ficam
arquivados, sem serem consultados pelas selecoes normais do M28. Nao ha retorno
a lista antiga de apenas dois padroes.

## Entrada e contexto

Os padroes, contratos versionados, ranking, limites originais de repeticao,
geometria SL/TP e prazos de saida da mineracao permanecem como estavam.
O contexto continua acumulado no minerador original: nao foi substituido por
reconstrucao de uma janela fixa, nem reaprendido com os resultados recentes.

O Dashboard exige, para M28:

- Uma leitura MT5 bem-sucedida e nao vazia, confirmada neste processo em ate 60s
  pelo marcador monotonicamente atualizado no servico compartilhado.
- Cache nao classificado como somente restaurado de historico local.
- Serie ordenada, ultima linha em formacao excluida e intervalo de cinco minutos
  ate a ultima fechada; lacuna nessa fronteira aguarda dados.
- Registro do minerador aquecido, correspondente ao horario e aos quatro precos
  da ultima M5 fechada recebida.
- Selecao sem horario futuro e ainda dentro do proprio limite de indices.

Uma selecao anterior pode continuar valida conforme seu contrato; esta correcao
nao inventa regra de cancelar todo padrao a cada candle. O cenario consultado,
entretanto, precisa acompanhar a ultima fechada confirmada.

As verificacoes abrangem a lista exibida, o plano adaptativo e a fila antes de
chamar o executor. Se a leitura vencer durante outras avaliacoes, ou se mudar
o candle/contexto ou a ocorrencia selecionada, a entrada aguarda a proxima
montagem. Nao ha envio financeiro nos testes.

## Auditoria e limites

Metadados de sincronizacao acompanham os planos permitidos e os motivos de
espera. Diagnostico por ativo em `.traderia/runtime/m28_context_sync_latest.json`,
fora do Git. Horarios mantem o dominio do MT5, sem deduzir offset pelo relogio local.
A confirmacao recente prova leitura do terminal; nao prova que o mercado esteja
aberto. Permissoes e recusas da corretora continuam nas verificacoes existentes.

Precos revisados com o mesmo horario, enquanto o minerador ainda tiver a versao
anterior, geram espera em vez de aceitar um contexto divergente.
Nenhuma economia financeira ou melhora de resultado foi calculada nesta mudanca.
M23, seus filtros antigos e os tres filtros adicionais permanecem preservados.

## Validacao

Testes de validador puro, integracao de selecao/plano, setup original, contratos
do M28, filtro arquivado e sincronizacao M23/MT5 e fila completa do executor: 97 aprovados, alem de 28 subtestes.
Fila validada com executor falso: leitura vencida nao envia; M7 permanece independente.
Os arquivos de politica M28, filtro antigo M23 e filtros adicionais M23 sao
conferidos por hash antes e depois da instalacao.
