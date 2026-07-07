# Project Charter

## Nome

TraderIA Novo.

## Objetivo

Manter uma versao organizada, versionada e operacional do TraderIA no GitHub,
sem mudar o local de trabalho do usuario e sem perder a capacidade local de
integracao com MetaTrader 5.

## Proposta De Valor

TraderIA Novo deve permitir:

- leitura Forex/MT5 local;
- pesquisa e calibracao pelo Lab local;
- acompanhamento de execucao demo;
- relatorios de auditoria TraderIA x MT5;
- evolucao por missoes pequenas, rastreaveis e versionadas no GitHub.

## Escopo Atual

Inclui:

- dashboard Streamlit;
- abas MT5 Forex, Lab e Relatorios;
- contratos de ViewModel;
- servicos de aplicacao;
- leitura MT5 em modo controlado;
- runtime local em `.traderia/`;
- governanca de missoes em `codex/` e `governance/`.

Fora do escopo sem missao explicita:

- operar conta real;
- mover pasta local;
- versionar artefatos pesados;
- substituir o MT5 local por Codespaces;
- automatizar ciclos bloqueantes na UI.

## Fonte Da Verdade

- Codigo e documentacao: GitHub `evilasiocabana-png/TraderIAnovo`.
- Runtime local: `C:\Users\evcab\OneDrive\Documentos\traderiaianovo\.traderia`.
- App local: `http://localhost:8532`.

## Principios

- Primeiro preservar funcionamento.
- Depois organizar.
- Alteracoes pequenas, testaveis e com commit.
- Lab e MT5 localmente; GitHub para codigo e governanca.
- Nenhum ciclo automatico deve tornar a maquina inutilizavel.

## Stakeholders

- Usuario operador: Evilasio.
- Agente de desenvolvimento: Codex.
- Plataforma de execucao local: Windows + Streamlit + MetaTrader 5.
- Plataforma de versionamento: GitHub.

## Definicao De Sucesso

O projeto e considerado saudavel quando:

- `http://localhost:8532` abre como TraderIA Novo;
- MT5 Forex nao trava a UI;
- Lab carrega resultados locais em poucos segundos;
- Relatorios mostram auditoria local funcional;
- codigo esta no GitHub;
- `.traderia/` contem runtime local e nao entra no Git.

