# Reforcos do ouro por seis recortes — V1

Autorizacao do usuario: aplicar somente nos reforcos M29/M30, incluindo M29 executado dentro do M23. M23 original permanece inalterado. Politica exploratoria escolhida depois de estudo retrospectivo; nao e filtro estatisticamente validado.

## Matriz permitida em XAUUSD

| Fonte | Estrutura | Faixa | N no estudo | Saldo original USD |
|---|---|---|---:|---:|
| M8 | Alta | Perto do piso | 33 | 97.00 |
| M8 | Transicao | Abaixo do piso | 109 | 1114.94 |
| M10 | Transicao | Abaixo do piso | 71 | 1148.80 |
| M18 | Baixa | Meio | 25 | 786.00 |
| M18 | Baixa | Acima do teto | 44 | 1038.80 |
| M20 | Alta | Abaixo do piso | 25 | 315.30 |

Somente esses pares fonte/estado/faixa liberam reforcos no ouro. M7/M1/M2/M5 e formacao/sem canal ficam bloqueados. Outros ativos preservam filtro anterior de baixa.

## Referencia e causalidade

Referencia exclusiva dos encerramentos originais M23 por fonte/ativo, conciliados por posicao e liquidos de custos, excluindo copias M29 e M30. Pivos confirmados; sensibilidade 1 e confirmacao 1. Posicao relativa calculada no ultimo encerramento: (equity-piso)/(teto-piso).

- z < 0: abaixo; 0 <= z < 1/3: piso; 1/3 <= z < 2/3: meio; 2/3 <= z <= 1: teto; z > 1: acima.
- A estrutura e o canal projetado sao campos distintos; Alta pode estar abaixo do piso sem ainda ter mudado a estrutura.
- Encerramento atualiza elegibilidade; somente novo sinal valido pode produzir nova ordem. Nao aumenta posicao aberta nem usa lucro flutuante.
- Planos carregam versao GOLD_SOURCE_CHANNEL_SIX_CONTEXTS_V1, estado, faixa e localizacao relativa. Ouro com plano antigo sem versao e rejeitado.
- Mesmo filtro reavaliado na geracao e barreira final do envio; digest exige plano atualizado.

## Pendentes e preservacao

A mesma decisao aplica-se a pendentes identificadas da familia atual de reforcos, inclusive enviadas antes desta revisao. Se sair da matriz, a pendente pode ser cancelada no ciclo Demo; se M18 estiver no recorte autorizado de Baixa, nao cancelar so por estar em Baixa. Conta/ticket/magic/comentario/fonte sao conferidos e pendente relida antes de remover. Se ja virou posicao, nao fechar. Erro de historico impede nova entrada e nao provoca cancelamento cego. Ordens originais M23 e legadas nao identificadas preservadas.

## Lotes e defesa

Reforcos ouro 0.20 e limite bruto modelado USD400; original M23 0.10 e USD200. Stops estruturais menores, TP, RSI e demais saidas preservados. Sem espelhamento. Execucao/gaps/custos podem exceder limite modelado. Outros ativos sem mudanca de lote/limite.

## Validacao

212 testes passaram com objetos simulados. Replay de classificacao comparado com todos os 1809 casos do estudo: 1809 identicos, 307 elegiveis. Auditoria previa de 1412 pendentes e 397 ordens a mercado nao encontrou mudanca de faixa/estrutura entre aceite e execucao na amostra. Nao foi enviada ordem para testar. Horario de aceite nao reconstrui latencia/cache anterior ao envio; lucro observado em 0.10 nao e lucro adicional projetado do reforco em 0.20.
