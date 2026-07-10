# MISSION_ROLLOVER_FIRST_DAILY_OPERATION_LAB_DECISION

## Objetivo

Implementar no TraderIA Novo a capacidade do Research Lab avaliar o pós-rollover como a primeira oportunidade operacional do dia, considerando que todas as posições devem ser encerradas antes do rollover e que a primeira análise do novo ciclo diário deve ser a oportunidade pós-rollover.

## Comando único para o Codex

Implemente no TraderIA Novo um fluxo de decisão do Research Lab para tratar o pós-rollover como a primeira operação candidata do dia.

Contexto operacional:
- O TraderIA deve considerar que posições abertas são encerradas antes do rollover.
- Portanto, o rollover não deve ser tratado como evento para manter posição aberta.
- O pós-rollover deve ser tratado como o primeiro evento operacional do novo dia.
- Todos os dias, após o rollover, o Lab deve avaliar se existe oportunidade estatística para operar.
- Se houver oportunidade, essa operação deve ser priorizada antes do fluxo normal das Alphas.
- Se não houver oportunidade, o sistema deve seguir para o fluxo normal do Research Lab.

Requisitos funcionais:
1. Criar uma etapa de análise prioritária no Research Lab chamada, por exemplo, `PriorityEventAnalysis` ou equivalente.
2. Criar o evento operacional `POST_ROLLOVER_DAILY_OPEN`.
3. O evento `POST_ROLLOVER_DAILY_OPEN` deve ser avaliado antes das Alphas normais.
4. O Lab deve decidir se existe ou não oportunidade operacional após o rollover.
5. A decisão deve ser baseada em dados de mercado e não em regra fixa.
6. O Lab deve analisar, no mínimo:
   - horário do servidor MT5;
   - fim da janela de rollover;
   - spread atual;
   - spread médio recente;
   - normalização do spread;
   - tick volume;
   - retorno da liquidez;
   - gap ou tick gap entre pré e pós-rollover;
   - ATR;
   - volatilidade recente;
   - momentum pós-rollover;
   - direção dos primeiros candles após o rollover;
   - rejeição, continuação ou consolidação após o evento.
7. O Lab deve classificar o contexto pós-rollover, por exemplo:
   - `NO_TRADE`;
   - `GAP_FILL_CANDIDATE`;
   - `CONTINUATION_CANDIDATE`;
   - `LOW_LIQUIDITY_SKIP`;
   - `SPREAD_TOO_HIGH_SKIP`;
   - `NO_EDGE_SKIP`.
8. Se o contexto for operacional, o Lab deve gerar um plano completo:
   - par;
   - timeframe;
   - direção;
   - entrada;
   - stop inicial;
   - alvo;
   - RR;
   - justificativa;
   - status de confiança;
   - motivo da decisão.
9. O Lab continua responsável por entrada, timeframe, RR, stop e alvo.
10. O fluxo normal das Alphas existentes não deve ser removido nem substituído.
11. A análise pós-rollover deve apenas ter prioridade diária antes do ciclo normal.
12. Se não houver sinal pós-rollover válido, o sistema deve retornar ao comportamento normal atual.
13. O sistema deve registrar no histórico do Lab que aquela avaliação foi do tipo `POST_ROLLOVER_DAILY_OPEN`.
14. Registrar métricas separadas para esse evento:
   - quantidade de avaliações pós-rollover;
   - quantidade de trades executados;
   - quantidade de skips;
   - motivo dos skips;
   - resultado por par;
   - resultado por timeframe;
   - resultado por dia da semana;
   - tempo após rollover até entrada;
   - spread no momento da entrada;
   - gap/tick gap detectado;
   - resultado financeiro;
   - MFE/MAE quando disponível.
15. A operação pós-rollover deve aparecer como primeira candidata do dia na tela/relatório do TraderIA.
16. A tela deve deixar claro quando o Lab está em modo:
   - `POST_ROLLOVER_ANALYSIS`;
   - `POST_ROLLOVER_TRADE_READY`;
   - `POST_ROLLOVER_SKIPPED`;
   - `NORMAL_LAB_FLOW`.
17. Garantir que nenhuma posição seja aberta durante a janela de rollover.
18. Garantir que a análise só comece após o fim da janela de proteção do rollover.
19. Não criar uma Alpha fixa chamada rollover se isso quebrar o desenho atual; a prioridade é que o Lab decida sobre a oportunidade pós-rollover.
20. Se for necessário representar internamente como Alpha/cenário, usar nomenclatura de evento, por exemplo `EVENT_POST_ROLLOVER_DAILY_OPEN`, sem substituir as 15 Alphas existentes.

Requisitos de arquitetura:
1. Preservar a arquitetura atual do TraderIA Novo.
2. Não alterar a lógica de entrada das Alphas existentes sem necessidade.
3. Não remover as Alphas atuais.
4. Não hardcodar horário fixo de Brasília.
5. Preferir horário do servidor MT5 para detectar o rollover.
6. Permitir configuração da janela de proteção antes/depois do rollover.
7. Separar claramente:
   - `RolloverGuard`: bloqueia operação durante janela de risco;
   - `PostRolloverAnalyzer`: avalia oportunidade após o evento;
   - `ResearchLab`: decide se opera ou se segue fluxo normal.
8. Integrar com o histórico e relatório sem quebrar dados existentes.
9. Atualizar rastreabilidade em `governance/traceability`, se aplicável.
10. Atualizar documentação explicando que:
    - rollover é o evento de virada operacional;
    - swap é o custo/crédito financeiro;
    - posições devem ser encerradas antes do rollover;
    - o pós-rollover é a primeira oportunidade candidata do novo dia;
    - o Lab deve decidir se existe edge ou não.

Critérios de aceite:
- O TraderIA não abre operação durante a janela de rollover.
- Após o rollover, o Lab avalia primeiro o evento `POST_ROLLOVER_DAILY_OPEN`.
- Se houver oportunidade, o Lab gera um plano operacional completo.
- Se não houver oportunidade, o Lab registra skip com motivo e segue o fluxo normal.
- As 15 Alphas existentes continuam funcionando.
- O evento pós-rollover aparece no histórico/relatório com identificação própria.
- O sistema registra métricas próprias para essa família de operações.
- Não há horário fixo dependente de Brasília.
- A implementação possui testes unitários com mocks do MT5.
- A documentação e rastreabilidade são atualizadas.

## Observação estratégica

Esta missão não cria uma regra automática de compra ou venda após rollover. Ela cria uma capacidade do Research Lab de avaliar diariamente se o pós-rollover oferece ou não uma oportunidade estatística. O evento é prioritário porque representa a primeira operação candidata do novo dia após o encerramento obrigatório das posições antes do rollover.
