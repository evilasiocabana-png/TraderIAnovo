# Demo principal e Real adicional

## Estado por conta - 2026-09-06

O painel principal distingue solicitacao de novas entradas, ciclo observado,
identidade e fonte da analise de mercado. Mostra Demo e Real separadamente,
reutilizando o refresh existente. A Demo consulta permissoes em subprocesso
read-only isolado, com cache de 15 segundos, timeout de 6 segundos e gate
compartilhado com as leituras MT5. Nao muda login nem habilita negociacao.
A Real usa o status recente do worker separado. Conexao e Algotrading ficam
em campos proprios, independentes do estado do ciclo e da autorizacao de envio.
Estado ausente, invalido, futuro ou com mais de 90 segundos nao comprova conexao
nem permissoes atuais. Horarios sao mostrados em BRT. Permissao nao observada
permanece INDISPONIVEL, nunca presumida pela conexao ou pela opcao marcada.

O guardiao de RAM ainda iniciava o painel Demo no executavel Real. O restart
agora fixa terminal portable, login e servidor Demo, como o inicializador oficial.
Isso corrige a origem da leitura sem modificar sinal, filtro, lote ou autorizacao
Real. A conta Real continua exigindo seu controle independente ja existente.

O inicializador oficial abre os dois terminais. O painel e seu ciclo existente
operam somente a Demo 61551556 (Pepperstone-Demo), no terminal portable
LocalAppData/TraderIANovo/MT5-Demo. Agenda e regras dos modelos continuam valendo.

Na aba MT5 Forex, "Operar tambem na conta Real" e "Aplicar" autorizam novas
operacoes na Real 51517136 (PepperstoneBS-MT5-Live01). Nao alteram o ambiente,
agenda ou estado online da Demo. Nenhuma senha e armazenada por esse controle.

O processo scripts/run_additional_real.py usa o mesmo DashboardService e os
modelos selecionados, consultando o mercado no terminal original. Os sinais
sao calculados independentemente com a cotacao de cada conta, nao copiando
bilhetes ou preenchimentos da Demo. Diferencas de feed, spread e execucao podem
gerar resultados diferentes; nao ha promessa de resultados iguais.

## Isolamento

- Processo/API MT5 separados por conta, com verificacao de login/servidor/path.
- Estado Real em .traderia/accounts/real-51517136; logs, tickets, cestas,
  gestor de posicoes e journal M28 nao compartilham o estado da Demo.
- Apenas configuracoes de estrategia sao copiadas; contratos de pesquisa
  sao lidos do acervo original. Geometria e lotes dos setups preservados.
- Lock do sistema operacional impede dois processos Real concorrentes.
- Real exige autorizacao persistida em additional_real.json. O transporte
  reler essa autorizacao antes e depois do preflight impede envio apos revogacao.
- Desmarcar Real suspende NOVOS ENVIOS de entrada, mantendo gestao de posicoes
  previamente autorizadas. Ordens pendentes ja aceitas no MT5 nao sao apagadas
  pelo checkbox e podem executar conforme suas condicoes originais.
- Falhas de conexao/permissoes nao provocam troca automatica de conta.
- A agenda semanal vale tambem na Real. Fora da janela, o fechamento semanal
  considera apenas posicoes com o magic do robo; posicoes manuais ficam intactas.

## Validacao de 2026-09-04

124 testes e 16 subtestes aprovados no conjunto de contas, transporte, controles,
duplo runtime e dados MT5. Quatro cenarios do inicializador aprovados.
Regressao do painel: 191 testes aprovados; servicos/M28/controles: 70 aprovados
apos atualizar o fake legado para declarar sua identidade de conta.
Segundo processo Real de teste encerrou sem criar ciclo duplicado.
Validacao final da agenda, isolamento e servicos: 43 testes aprovados.
Verificacao read-only: Demo 61551556 conectada, Algotrading ligado;
Real 51517136 conectada, Algotrading desligado. Nenhuma ordem Real de teste.

O checkbox Real foi deixado desmarcado. Homologacao de envio na corretora
nao foi executada. Dados do painel atualizados pelo reinicio oficial.
