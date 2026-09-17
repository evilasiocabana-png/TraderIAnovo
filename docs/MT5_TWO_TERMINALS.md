# Dois terminais MT5 - TraderIA Novo

## Instalacoes locais

| Destino | Executavel | Conta esperada | Servidor |
| --- | --- | --- | --- |
| Real | C:\Program Files\MetaTrader 5\terminal64.exe | 51517136 | PepperstoneBS-MT5-Live01 |
| Demo | %LOCALAPPDATA%\TraderIANovo\MT5-Demo\terminal64.exe | 61551556 | Pepperstone-Demo |

A instalacao Demo usa /portable, com dados separados na propria pasta.
Foi preparada a partir dos executaveis locais com assinatura MetaQuotes valida.
Somente executaveis, icone, catalogo de servidores e licenca do programa foram
copiados. Nenhum cadastro de contas, senha ou historico de negociacoes foi copiado.
Atalhos separados foram criados na area de trabalho.

O atalho principal TraderIA Novo usa scripts/abrir_traderianovo.ps1 e abre
o painel e os dois terminais. Verifica o caminho de cada processo e abre
somente a instancia ausente; Demo sempre usa /portable. Nao troca contas,
nao informa senhas e nao habilita Real por abrir o aplicativo.

Referencia: https://www.metatrader5.com/en/terminal/help/start_advanced/start

## Estado em 2026-09-04

Os dois processos foram abertos. Sonda somente leitura confirmou a conta Real
51517136. A nova instancia Demo ainda retornou IPC timeout na primeira sonda;
precisa concluir primeiro acesso/login pelo usuario. Nenhuma ordem foi enviada.

## Conexao do robo

MT5_PATH identifica explicitamente o executavel de cada conexao. O executor
rejeita caminho ausente ou terminal conectado divergente, sem fallback para
outro terminal quando ha caminho configurado.

O seletor atual do painel ainda e exclusivo (Demo OU Real). Nao representa
envio simultaneo. A integracao de dois executores em processos separados,
com estados, tickets, caches, gestao de saidas e logs por conta, permanece
pendente. Nao reutilizar a conexao global MetaTrader5 de um unico processo
para alternar contas enquanto envia ou gerencia ordens.

O codigo e os contratos de estrategia devem ser os mesmos nos dois processos;
nao criar uma segunda copia do repositorio. Validar independentemente o ciclo
completo de entrada, rejeicao, duplicidade, SL/TP e encerramento em cada conta.
