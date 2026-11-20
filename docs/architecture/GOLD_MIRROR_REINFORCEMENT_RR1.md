# Reforcos espelhados RR1 por faixa - V2

Autorizado em 02/10/2026: novos reforcos XAUUSD M29/M30 (inclusive M29 executado no M23), 0.20, espelhados apenas nas faixas positivas do replay com defesa USD400 e alvo simetrico. M10 excluido do espelhamento. Os seis recortes normais anteriores permanecem; demais ativos e M23 original permanecem inalterados.

## Matriz espelhada

| Fonte | Estado | Faixa | N | N indeterminados | Estimativa USD | Cenario indeterminados no stop USD |
|---|---|---|---:|---:|---:|---:|
| M18 | Alta | Perto do teto | 14 | 0 | 875.40 | 875.40 |
| M18 | Baixa | Abaixo do piso | 6 | 0 | 1332.20 | 1332.20 |
| M18 | Baixa | Perto do teto | 41 | 0 | 1003.40 | 1003.40 |
| M18 | Transicao | Abaixo do piso | 113 | 1 | 649.00 | 580.40 |
| M18 | Transicao | Acima do teto | 99 | 1 | 6230.60 | 6185.80 |
| M20 | Alta | Meio | 22 | 0 | 200.60 | 200.60 |
| M20 | Alta | Perto do piso | 19 | 0 | 789.00 | 789.00 |
| M20 | Baixa | Perto do teto | 30 | 0 | 977.00 | 977.00 |
| M7 | Alta | Acima do teto | 1 | 0 | 398.40 | 398.40 |
| M7 | Alta | Perto do teto | 5 | 0 | 713.40 | 713.40 |
| M7 | Transicao | Abaixo do piso | 8 | 0 | 820.00 | 820.00 |
| M7 | Transicao | Perto do piso | 1 | 0 | 398.60 | 398.60 |
| M8 | Alta | Acima do teto | 12 | 0 | 1732.20 | 1732.20 |
| M8 | Alta | Meio | 11 | 0 | 378.60 | 378.60 |
| M8 | Baixa | Abaixo do piso | 9 | 0 | 1208.80 | 1208.80 |
| M8 | Baixa | Perto do teto | 36 | 0 | 522.60 | 522.60 |
| M8 | Transicao | Acima do teto | 72 | 1 | 3237.40 | 3192.60 |
| M8 | Transicao | Perto do teto | 5 | 0 | 1035.40 | 1035.40 |

Amostra selecionada retrospectivamente: nao e validacao futura. M1 com spread aproximado e ticks para minutos ambiguos disponiveis. Comissao/taxa original escalada pelo lote; sem swap simulado. Alguns recortes tem apenas uma operacao. O cenario conservador atribui stop nominal aos casos sem ticks; gaps podem perder mais, portanto nao e limite matematico de perda. Esta matriz foi congelada por autorizacao, sem reaprendizado automatico.

## Contrato operacional

- Referencia causal: encerramentos originais M23 por fonte/ativo, sensibilidade 1 e pivos confirmados. Faixa e estado antes da entrada; mesmo filtro na geracao e envio.
- Plano atual versionado. Original precisa constar no log da mesma conta Demo, fonte, ativo, candle, timeframe e setup; ordem nativa preenchida e posicao original aberta. Pendencia aceita nao confirma execucao. Falha/ambiguidade bloqueia espelho. Nao ha garantia de simultaneidade atomica entre ordens.
- Espelho enviado a mercado somente apos confirmar original, nunca cria uma pendente invertida antes do preenchimento original. Se o sinal original deixou de ser valido, nao faz catch-up. Deduplicacao e limites de exposicao existentes continuam valendo.
- Direcao oposta; distancia estrutural inicial preservada quando menor. Preco de envio e cotacao executavel da perna contraria. Corretora calcula limite USD400 para lote .20; SL arredondado para dentro, TP espelhado a mesma distancia final. Falha bloqueia envio. Custos, gaps e slippage podem exceder perda prevista.
- Somente novas posicoes com contrato GOLD_MIRROR_RR1_SLTP_V1 e comentario INV R1: nao herdam RSI, trailing ou zeragem por lucro da cesta; aguardam SL/TP. Controles gerais de emergencia/agenda semanal permanecem vigentes. Posicoes antigas sem marcador mantem gestao anterior.
- As abertas e historico/exportacao mostram Modo do reforco: Espelhado. Historicos sem evidencia nao recebem um modo inventado.
- Pendentes de reforco normal sao reavaliadas pela mesma matriz: mudanca para modo espelhado cancela a pendente normal identificada, nunca altera uma posicao aberta.

## Validacao

396 testes e sete subtestes na preparacao isolada, incluindo envio simulado BUY/SELL, RR apos limite financeiro, stops menores, falha de calculo, fonte preenchida, pendencia nao preenchida, isolamento do M23, gestao fixa e relatorio. Nenhuma ordem enviada para testar.

## Instalacao

Versao instalada, 396 testes e sete subtestes aprovados no repositorio. Launcher oficial recarregado; health OK e selecao, online e agenda preservados por hash; M30 habilitado preservado e Real DISABLED. Commit/push pendentes por sobreposicao com alteracoes locais anteriores ainda nao versionadas; nenhum arquivo alheio foi incluido em commit.


## 2026-10-02 - Retirada dos espelhados por faixa

Por confirmacao explicita do usuario, os 18 recortes espelhados foram desativados para novas entradas. Permanecem somente os seis recortes normais da primeira implementacao. Planos espelhados sao rejeitados mesmo com execucao original confirmada; a versao da politica invalida planos antigos. Historico e gestao SL/TP das posicoes existentes foram preservados, assim como M23 original, lotes e protecoes financeiras. Validacao concluida: 396 testes e 7 subtestes passaram. Recarga pelo launcher oficial concluida, health OK; selecao, estado online e agenda preservados por hash. Nenhuma ordem de teste enviada. Alteracoes locais de outros trabalhos preservadas; sem novo commit ou push nesta retirada.
