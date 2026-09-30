# Estado compartilhado das abas

## Escopo
MT5, Relatorios e Aprendizado compartilham o contrato de apresentacao em `application/model_ui_state.py`. O catalogo dos graficos deriva dos modelos ativos do dominio e acrescenta M30, cuja autorizacao continua individual. O resumo distingue autorizacao para novas entradas de execucao confirmada.

## Persistencia e compatibilidade
`application/model30_configuration.py` e o unico leitor/escritor de `m30_enabled` na base existente. O facade DashboardService delega a escrita; o export `model30_learning.enabled` permanece compativel para os consumidores de execucao. Nao ha migracao de dados, novo banco, alteracao de sinais, lotes, canais, stop, TP ou posicoes.

## Sincronizacao entre abas
`sync_persisted_widget` atualiza cada widget quando o valor persistido difere da ultima leitura daquela superficie. Reexecucoes com o mesmo estado preservam edicoes ainda nao aplicadas. Ao abrir Aprendizado depois de desabilitar M30 no MT5, o toggle reflete o estado salvo sem reabilitar o modelo acidentalmente. Aplicar modelos e o toggle usam o mesmo comando de persistencia.

## Historicos
Graficos M23 por fonte permanecem separados dos historicos proprios. O M30 informa explicitamente que o periodo pode conter a politica anterior de copia e a atual de canal. Descricoes antigas de entrada condicionada ao aceite M23 foram removidas da apresentacao atual; comparacoes legadas continuam identificadas como legado.

## Validacao
33 testes passaram: persistencia isolada, leitores de execucao, troca de abas em Streamlit AppTest, preservacao de edicao nao aplicada, catalogo, graficos, fluxo independente e provider. Nenhuma ordem enviada para teste.
