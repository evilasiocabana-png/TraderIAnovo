# Estudo visual de resultados realizados por modelo

Um grafico por modelo no Relatorio. Se a fonte participa do M23, seletor alterna operacoes proprias e sinais executados pelo M23, sem concatenar ou somar os historicos. Historicos antigos continuam disponiveis. Curva principal agregada preservada.

Curvas individuais liquidas partem de zero no periodo selecionado: lucro, comissao, swap e taxas. Apenas encerramentos confirmados, deduplicados e ordenados; G verde, P vermelho, E cinza. Sequencia completa visivel com rolagem; zoom e seletor de trecho; saldo do periodo.

Estrutura descritiva por extremos confirmados: dois topos e fundos ascendentes definem Alta; ambos descendentes Baixa. Rompimento ou estrutura mista indica Transicao; dados insuficientes Formacao. Confirmacao requer reversao de 0.5, 1 ou 2 vezes a mediana absoluta das ultimas 20 operacoes nao nulas observadas. Padrao: 1. Os extremos ficam no ponto original, com momento de confirmacao no tooltip. Estado so muda na confirmacao, sem retroagir. Linhas tracejadas ligam extremos, nao projetam retornos.

Sete testes passaram: custos/deduplicacao/fontes, alta com perdas, baixa com ganhos, inversao, invariancia do prefixo e dados insuficientes. Streamlit AppTest renderizou os dois tipos de historico sem excecao; schemas Vega-Lite validados por Altair. Nenhuma regra de ordens, lotes, filtros ou espelhamento foi alterada.
