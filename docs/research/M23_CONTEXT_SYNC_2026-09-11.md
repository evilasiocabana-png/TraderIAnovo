# Correcao de sincronizacao do contexto M23 — 11/09/2026

Autorizacao: aplicar as correcoes de disponibilidade, sincronizacao e rastreabilidade identificadas nesta conversa. As regras estatisticas e o arquivo instalado do filtro ficam preservados.

## Comportamento

O M23 solicita M5 para os ativos das fontes mesmo sem contratos ativos do M28. Cada leitura de mercado bem-sucedida registra uma marca monotônica apenas em memoria; seed, cache do disco, falha e fallback nao renovam essa marca. Para avaliar uma entrada, a leitura precisa ter ocorrido nos ultimos 60 segundos.

O contexto usa exatamente os 200 candles fechados ate o candle declarado pelo sinal. Nas fontes sem horario M5 declarado, usa o ultimo M5 fechado anterior ao candle corrente, registrando explicitamente essa origem. A vela em formacao nunca entra no calculo. Falta da vela exata, aquecimento insuficiente, dados invalidos, serie nao confirmada ao vivo ou desencontro temporal produzem M23_CONTEXT_WAITING: tentativa aguarda dados validos, sem ordem nova. Contexto valido com NO_EVIDENCE estatistica preserva entrada, como antes. Stops, lotes e posicoes abertas nao mudam.

A leitura depende de uma janela deterministica de 200 fechadas, distinta do motor anterior que acumulava estado durante o processo. O arquivo das regras nao mudou, mas indicadores e zonas reconstruidos podem diferir do estado antigo. Nao foi demonstrada paridade retrospectiva nem economia de filtro.

O avaliador agora diferencia identificacao da regra e do contexto, fotografa os sete campos, registra candle, validacao e data do relatorio. Os parametros seguem no log de execucao; um diagnostico local mostra a ultima avaliacao, inclusive esperas/bloqueios. Valores de horario MT5 permanecem no mesmo dominio do candle da fonte; nao se subtrai um fuso arbitrario para comparar sinal e contexto.

A analise historica futura passa a escolher somente candle ja fechado e descartar registro velho ou sem aquecimento. Isso nao recalcula nem substitui o relatorio instalado.

## Validacao

Testes isolados verificam formacao da vela, candle ausente/errado, leitura envelhecida, seed, indicador com aquecimento insuficiente, cache invalidado por revisao, independencia de M28, preservacao de NO_EVIDENCE com contexto valido, fotografia e metadados. Contratos existentes do M23, servico de mercado e compatibilidade M28 foram executados. Relatorio congelado conferido por SHA-256 antes/depois da instalacao.

## Operacao e reversibilidade

Backup de cada arquivo modificado e manifesto de hashes preservados fora do projeto, na area m23_sync_review. Instalar nao envia ordens de teste. Recarregamento usa o mesmo comando, ambiente e autorizacoes do painel Demo existente. A atividade automatica previamente habilitada pode retomar; configuracoes de contas nao sao alteradas.

O replay integral continua pendente. Nao atribuir a queda inteira aos problemas de contexto nem transformar perdas associadas em economia prometida.

## Resultado da instalacao

210 testes passaram: sincronizacao, construcao causal, contratos do dashboard/M23, observacao de dados ao vivo, servico de mercado, cesta e compatibilidade M28. Painel recarregado com saude HTTP confirmada.

Avaliacao observada apos a recarga: M7 no ouro, contexto ALIGNED/VALID, 200 candles fechados, candle esperado igual ao utilizado e leitura ao vivo confirmada em menos de 60 segundos. Regras do relatorio de 31/08 preservadas byte a byte por SHA-256. Essa verificacao confirma a integracao neste ciclo; nao certifica o replay financeiro nem todas as decisoes futuras.
