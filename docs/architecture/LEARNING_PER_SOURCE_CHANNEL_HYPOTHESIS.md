# Aprendizado por origem e hipotese manual dos canais

## Isolamento

Escopo canonico: conta Demo confirmada, modelo de origem, setup de origem,
ativo e timeframe. A base versionada limita cada avaliacao. M23 e M30 sao
executores comparados dentro do escopo, nao modelos agrupadores de treinamento.
Nao ha compartilhamento de amostras ou promocao entre escopos. Familias de
sinais correlacionados continuam agrupadas, sem duplicar tickets da mesma conta.

Candidatos antigos sem escopo ficam LEGACY_UNSCOPED, preservados para auditoria,
sem atribuicao inventada e sem admissao operacional. Filtros aprendidos usam
chave ativa por escopo. Requisitos de descoberta, calibracao, teste futuro,
significancia e reversao permanecem; a hipotese manual nao os contorna.

## Canais: hipotese manual, nao ordem

MANUAL_REALIZED_CHANNEL_V1 usa resultados liquidos encerrados originais M23
da propria origem, antes da entrada avaliada. Exclui curva M30 e copias M29
da referencia. Dois topos e dois fundos descendentes confirmados formam canal
paralelo de baixa; alta fica normal. Romper a borda superior da baixa normaliza
sem aguardar novo pivo de alta. Sensibilidade 1 e um fechamento fora, conforme
geometria causal existente. Ausencia de estrutura fica pendente.

Cada escopo/base congela uma hipotese com inicio explicito. So entradas
prospectivas posteriores sao avaliadas. Esta hipotese nao pertence a tabela
de filtros operacionais e nunca e promovida automaticamente.

Simulacao espelhada: mesma quantidade, lado oposto, alvo no stop inicial da
referencia, stop simetrico RR 1:1. Entrada/saida usam bid/ask dos ticks,
inclusive preco observado apos atravessar a borda (nao preenchimento perfeito).
Comissao e taxas sao estimadas pelas cobradas na referencia; isso e informado
no grafico, nao e resultado executado. Resultado sem custos resolvidos fica
pendente. Operacao normal reutiliza o liquido nativo da referencia.

## Limites explicitos

- Uma leitura opcional de ticks por ciclo do observador, timeout 5 segundos,
  maximo 100000 ticks; janela excedida permanece TICK_WINDOW_LIMIT.
- Ordens Stop/Limit aguardam simulacao propria de acionamento; nao sao
  tratadas como ordens a mercado nem recebem resultado inventado.
- Entrada sem cotacao proxima, geometria invalida e posicao sem saida sao
  estados pendentes. Saida em outra data exige custos adicionais, sem lucro
  liquido artificial.
- O grafico usa o prefixo continuo de pares resolvidos; nao pula uma operacao
  nao resolvida para mostrar apenas as posteriores favoraveis.
- Resultados sao simulacao de oportunidades fixas, nao reexecucao completa
  das interacoes futuras de cesta, margem ou sequencia de ordens.
- Volumes nao sao dobrados implicitamente nesta hipotese.

M23, M30 operacional, selecoes, agenda e Real nao sao alterados pela simulacao.
