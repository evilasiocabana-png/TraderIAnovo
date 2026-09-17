# M29 - acumulador independente

Status: implementado e publicado em 12/09/2026; desmarcado para novas ordens.

## Contrato

- Identidade: MODELO_29_BASKET_ACCUMULATOR, ALPHA029, BETA029.
- Fontes diretas: M1, M2, M5, M7, M8, M10, M18, M20.
- M21 e M22 retirados do M29 por solicitacao do usuario; demais modelos preservados.
- Recebe os planos originais, incluindo entradas adicionais. Nao recebe ordens
  nem depende da selecao, cesta ou aprovacao do M23.
- Cesta, comentarios, deduplicacao, resultados e estado separados do M23.
- Preserva lotes e contratos de origem, salvo o espelhamento M7 abaixo.
- Full Exit independente em +US$1.000 liquidos, apenas tickets M29.
- Selecao inicial desmarcada; nenhuma autorizacao Real e alterada.

## Alternancia M7 Por Ativo E Conta

G significa resultado liquido positivo; P, negativo; E, empate.
Somente posicoes integralmente encerradas contam, uma vez por posicao.
Fechamentos parciais nao constituem novos resultados.

Modo inicial NORMAL. Um bloco de quatro resultados alternados GPGP ou PGPG,
seguido de PP, muda para ESPELHADO na proxima entrada. No modo espelhado,
um bloco de quatro resultados alternados seguido de GG volta a NORMAL.
Os blocos exigem seis resultados distintos. Empates interrompem o bloco.
Resultados simultaneos sao ordenados por horario e identificador estavel.
Nao reutilizar resultados anteriores a uma transicao para uma nova transicao.

O historico conciliado do M23 com fonte M7 anterior a criacao pode inicializar
o detector, por ativo e conta, classificando a sequencia cronologicamente.
Isso nao equivale a simular resultados espelhados passados nem comprova lucro
do espelhamento. Depois, somente resultados do M29/fonte M7 atualizam o detector.

ESPELHADO inverte BUY/SELL. O SL original passa a TP; o novo SL fica a mesma
distancia do lado oposto da entrada. RR geometrico 1:1 antes dos custos.
No modo espelhado os SL/TP individuais sao fixos; nao herdar trailing/saida
direcional M7 que alteraria essa geometria. A zeragem coletiva M29 permanece.
Protecoes invalidas bloqueiam o plano. Nao alterar posicoes ja abertas.

## Validacao Obrigatoria

Identidade, fontes, fonte M23 recusada, cesta isolada, sequencia causal,
bootstrap unico, custos/empates, duplicatas, isolamento conta/ativo,
espelhamento BUY/SELL, fontes adicionais, selecao independente, provider,
saidas e relatorio. Publicar somente apos integracao e testes.

## Evidencias Da Entrega

- 150 testes passaram, incluindo 2 subtestes, no recorte M29 + executor/provider.
- AppTest confirmou caixa M29 inicialmente desmarcada, selecao isolada sem M23,
  painel proprio e separacao como MODELO29 nos relatorios.
- Provider falso confirmou envio independente e SL/TP espelhados preservados.
- Gestor falso encerrou somente ticket M29, ignorando ticket M23 lucrativo.
- Fonte de dados, filtros e estado M23 nao foram reescritos. As 31 regras
  efetivas APPROVE/BLOCK foram congeladas em config/m29_pattern_filter.json;
  regras NO_EVIDENCE e amostras nao sao necessarias ao avaliador operacional.
  Filtros adicionais copiados para config/m29_additional_filters.json.
- Inicializacao Demo read-only: XAUUSD ESPELHADO; BTCUSD NORMAL; zero encerradas
  M29 na inicializacao. Resultados seguintes pertencem exclusivamente ao M29.
- Processo reiniciado pelo launcher oficial; health publico respondeu ok.
  Hash da selecao operacional identico antes/depois (M23 e M28).
- Conferencia visual autenticada na internet ficou pendente do login do usuario.
  A interface foi validada via AppTest, sem alterar a selecao em producao.
- Recortes legados mais amplos possuem expectativas antigas sobre M24/M25
  aposentados e um teste M23/EURUSD dependente do catalogo local. Nao foram
  alteradas essas politicas para fazer tais expectativas passarem.

O bootstrap classifica a sequencia observada; nao e backtest contrafactual
de lucro espelhado. Nao ha validacao de rentabilidade da nova regra nem
promessa de reducao de perdas. A ativacao operacional continua manual.
## 2026-09-14 - Sincronizacao M7 ouro M23/M29

Por autorizacao do usuario, novas entradas M7/XAU do M29 exigem confirmacao
M23 no mesmo ciclo, candle e plano fonte. Fonte calculada uma vez para ambas
as rotas. Normal/espelhado preservados; em espelhado o TP confere com SL M23.
Somente uma tentativa por confirmacao; ticket M23 registrado no plano M29.
Com ambos selecionados, nova dupla aguarda ambas as posicoes M7/XAU encerrarem
e plano correspondente M29 pronto. Sem reentrada isolada, catch-up ou fechamento
forcado. Outras fontes e BTC permanecem independentes. Contas e selecao intactas.
67 testes do recorte passaram, incluindo fluxo completo com executor simulado.
A suite geral demo apresentou 9 falhas; uma foi reproduzida em memoria sem
as alteracoes de sincronizacao. Nao se declara a suite geral integralmente verde.
Ordens separadas nao sao atomicas: M29 ainda pode ser rejeitado apos aceite M23.
SL/TP e saidas nao foram sincronizados; RR1 nao garante resultados inversos.
