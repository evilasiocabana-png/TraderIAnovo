# Execucao MT5 Real e Demo

Projeto: TraderIA Novo. TraderIA e TraderIA_WDO nao sao alterados.

O mesmo executor atende Demo e Real. Setups, lotes, SL, TP, agenda e
defesas contra duplicidade permanecem no fluxo existente. Saldo vem da
conta conectada no MT5; nenhum capital inicial e fixado no codigo.

## Configuracao

Na aba MT5 Forex, o bloco Robo MT5 possui Ambiente DEMO/REAL, conta e
servidor Real autorizados e o botao Aplicar conta. Real exige confirmacao
marcada pelo operador. Aplicar desarma o robo e suspende a agenda automatica
nesta sessao; armar e uma acao separada. A selecao nao troca o login do MT5.
As configuracoes pela interface valem para o processo atual; nao persistem
como autorizacao Real automatica apos reiniciar. Cada aplicacao revoga os
executores antigos, inclusive os de tarefas que ja estavam em andamento.

Inicializador manual pronto: scripts/iniciar_traderianovo_real.ps1.
Esta configurado para a conta 51517136 no servidor PepperstoneBS-MT5-Live01,
exige confirmacao digitada e recusa iniciar se o painel ja ocupar a porta 8532.
O arquivo nao foi executado pelo agente. Nao inclui senha e nao e agendado.
Os valores de ambiente sao definidos somente apos a confirmacao do operador.

Demo continua sendo o modo padrao, com TRADERIA_DEMO_EXECUTION_ENABLED=1.
Selecionar uma conta Real no terminal nao autoriza automaticamente o envio.

Para configurar Real, o operador deve definir no ambiente do processo:

```text
TRADERIA_EXECUTION_ACCOUNT_MODE=REAL
TRADERIA_REAL_EXECUTION_ENABLED=1
TRADERIA_REAL_ACCOUNT_LOGIN=<numero da conta autorizada>
TRADERIA_REAL_ACCOUNT_SERVER=<servidor exato da conta autorizada>
```

Essas variaveis nao foram ativadas por esta implementacao. Nao armazenar
senha no repositorio. Reiniciar o processo ao mudar a configuracao de conta;
o provider captura a selecao na inicializacao. O estado armado e a agenda
existentes podem iniciar o ciclo, portanto revisar ambos antes de habilitar.

TRADERIA_DEMO_MAX_DAILY_LOSS tem padrao 0 (sem limite diario adicional),
tanto em Demo como em Real. Um valor positivo explicitamente configurado
continua sendo respeitado. Stops das entradas nao foram removidos.

## Validacao

Antes de cada envio, o executor valida tipo da conta; em Real, tambem
login, servidor e permissoes de negociacao automatica. Falha na leitura da
conta, do book de entrada ou no order_check impede o envio. A conta e
revalidada depois do order_check. Isso nao torna a chamada externa atomica:
nao trocar a conta no terminal enquanto o robo estiver armado.

Logs novos incluem modo e identidade Real. A defesa de duplicidade do
executor nao reutiliza registros de outra conta Real nem registros Demo.
Os nomes legados Demo de classes e arquivos foram preservados.

Testes usam MT5 simulado, sem envio de ordens reais. Resultado de teste
nao comprova rentabilidade nem homologacao na corretora. As qualificacoes
estatisticas de padroes do M28 nao mudam com a selecao de conta Real.
