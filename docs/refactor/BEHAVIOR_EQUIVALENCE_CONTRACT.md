# Contrato de Equivalencia da Refatoracao Segura

Status: obrigatorio

## Objetivo

Uma refatoracao do TraderIA Novo somente pode ser integrada quando preservar o
comportamento operacional observavel. Melhor organizacao interna nao autoriza
mudanca de estrategia, risco, timing ou execucao.

## Invariantes operacionais

- O Research Lab pesado continua sob demanda e fora do ciclo leve.
- O ciclo operacional continua com a cadencia configurada, hoje 10 segundos.
- Indicadores usam a janela deslizante canonica e somente candles autorizados.
- O fechamento de candle, timeframe e horario do servidor MT5 nao podem mudar.
- A selecao de modelos permanece persistente e limita novas entradas.
- Cada modelo continua independente; M23 pode copiar uma fonte sem impedir a
  ordem direta da mesma fonte.
- Duplicidade continua bloqueada por modelo, par, sinal e candle/plano.
- Entrada, lado, volume, SL, TP, validade e comentario enviados ao MT5 devem ser
  identicos antes e depois da refatoracao para a mesma entrada de dados.
- O Position Manager nao cria entradas e nunca piora um SL.
- M23 fecha somente tickets M23 no Full Exit coletivo de US$ 1.000.
- Posicoes diretas M1-M22 preservam as saidas de seus contratos.
- Conta real continua bloqueada; validacao automatica nao envia ordens.
- Refresh, troca de aba ou reinicio do painel nao alteram o estado do robo.

## Evidencia minima por incremento

Cada incremento deve apresentar:

1. diff pequeno e com responsabilidade unica;
2. testes de caracterizacao antes da alteracao estrutural;
3. testes focados depois da alteracao;
4. auditoria arquitetural executada;
5. comparacao de tempo e memoria quando tocar o ciclo leve;
6. rollback por commit unico;
7. confirmacao de que o worktree operacional nao foi modificado.

## Gates obrigatorios

- Nenhuma nova falha nos testes arquiteturais.
- Nenhuma nova falha nos testes Lab -> Forex -> MT5.
- Nenhuma nova falha em Robo Demo, provider, M23 ou Position Manager.
- Nenhuma chamada adicional ao MT5 por par/modelo no ciclo leve.
- Nenhum Lab/backtest iniciado pelo refresh do dashboard.
- Ciclo completo abaixo de 3 segundos no ambiente de referencia.
- Sem sobreposicao de ciclos e sem escrita concorrente insegura.

## Politica de divergencias existentes

Falhas ou divergencias anteriores devem ser listadas separadamente. Uma
refatoracao nao pode apagar, atualizar ou reclassificar a baseline apenas para
fazer o gate ficar verde. A baseline so muda depois de auditoria e justificativa
documentadas.

## Integracao

O trabalho nasce em branch e worktree isolados. Depois dos gates, o diff e
revisado antes de qualquer integracao. O app operacional e o MT5 permanecem no
commit anterior ate essa aprovacao.
