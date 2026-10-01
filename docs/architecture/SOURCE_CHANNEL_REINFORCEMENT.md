# Reforcos M29/M30: suspensao por canal de baixa

Politica autorizada em 30/09/2026, somente para novas entradas Demo.

- M23 original permanece baseline, lote padrao 0,10; lote 0,05 cancelado.
- M29 e M30 recebem sinais originais, sem inversao. Fontes e ativos vigentes preservados.
- Referencia: resultados encerrados originais da mesma fonte e ativo no M23, com custos; nao incorpora copias M29 nem resultados M30.
- Bloqueia quando estrutura e canal por pivos confirmados indicam Baixa. Sensibilidade 1, confirmacao 1. Alta, lateral, transicao ou falta de formacao permitem; falha tecnica de consulta/conciliacao bloqueia.
- Mudanca vale apenas na proxima entrada. Sem canal de baixa, o reforco ainda precisa passar pelos demais filtros, habilitacao, limites e sincronizacao existentes.
- Revalida referencia junto ao envio; planos antigos, espelhados ou de outra fonte sao recusados.
- Original M23 nao depende de um plano de reforco quando o reforco esta suspenso. Duplas elegiveis conservam sua sincronizacao.
- Defesa US$200 existente preservada: M23 direto e M30 via protecao M23; copias M29 conservam seu escopo financeiro vigente documentado em M29_HISTORICAL_FIXED_DEFENSE.md. Nao ampliamos esse escopo nesta tarefa.
- Stops menores preservados; TP, RSI e demais saidas mantidos. Gaps, custos e execucao podem ultrapassar a perda modelada.
- Nenhuma posicao ou pendente existente e alterada. Historicos antigos continuam armazenados; graficos da politica atual nao os misturam.

A regra substitui o espelhamento operacional de M29/M30. Funcoes historicas de sequencia/canal permanecem para leitura e estudos, sem autorizar novos planos.


## 2026-10-01 — Lote dos reforcos no ouro

Autorizado lote 0,20 para novas entradas M29/M30 XAUUSD, incluindo M29 executado pelo M23. Original M23 permanece 0,10. Outros ativos e posicoes/pendentes existentes inalterados. Validacao final recusa planos antigos de ouro em 0,10. Defesa financeira vigente precifica o novo lote sem afastar stops menores. 195 testes passaram sem ordens reais; painel recarregado pelo procedimento oficial, saude ok, selecao/agenda/estado online preservados.


## 2026-10-01 — Cancelar reforcos pendentes em baixa e defesa US$400

Autorizado cancelar somente ordens pendentes da politica atual M29/M30 (incluindo copias M29 no M23) quando o canal da fonte/ativo original no M23 confirmar Baixa. Lateral continua permitido. Confirmacao por conta Demo, ticket, magic, comentario, fonte e plano; pendencia relida antes de remover. Ordens originais M23 e posicoes abertas preservadas. Falha de historico nao provoca cancelamento cego.

Novos reforcos XAUUSD 0,20 recebem limite previsto US$400; original M23 0,10 permanece US$200. Stops menores, TP e saidas preservados. Outros ativos seguem limite US$200. Custos/gaps podem superar a perda modelada. Corrigida inicializacao Demo antes da verificacao M30; conexao Demo hedging confirmada sem ordem de teste. 148 testes passaram.
