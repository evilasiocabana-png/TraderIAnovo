# Roadmap 01 - Governance

Este roadmap organiza as Sprints CTO_001 ate CTO_049 como trilha de
governanca, auditoria, qualidade e maturidade operacional do TraderIA_WDO.

O arquivo e documental. Ele nao implementa funcionalidades, nao altera
arquitetura, nao cria modulos e nao autoriza operacao real.

## Sprints CTO

<!-- START CTO_001 -->
## CTO_001 - Inventario Inicial do Projeto

Objetivo: mapear a estrutura inicial do TraderIA_WDO.

Escopo:
- listar diretorios, arquivos centrais e responsabilidades existentes;
- identificar ponto de entrada da aplicacao;
- registrar dependencias conhecidas.

Resultado esperado: inventario inicial aprovado pelo CTO.
<!-- END CTO_001 -->

<!-- START CTO_002 -->
## CTO_002 - Definicao de Fronteiras Arquiteturais

Objetivo: separar dominio, core, infraestrutura, estrategias e apresentacao.

Escopo:
- classificar responsabilidades por camada;
- identificar acoplamentos indevidos;
- propor fronteiras minimas de Clean Architecture.

Resultado esperado: fronteiras arquiteturais documentadas.
<!-- END CTO_002 -->

<!-- START CTO_003 -->
## CTO_003 - Contratos de Dominio

Objetivo: consolidar contratos compartilhados entre modulos.

Escopo:
- revisar DTOs do dominio;
- validar independencia do dominio;
- impedir dependencia de infraestrutura nos contratos.

Resultado esperado: contratos de dominio preservados e auditaveis.
<!-- END CTO_003 -->

<!-- START CTO_004 -->
## CTO_004 - Regras Arquiteturais Basicas

Objetivo: formalizar regras centrais de arquitetura.

Escopo:
- registrar regras de dependencia;
- registrar bloqueios de operacao real;
- definir responsabilidades de estrategias, risco e execucao.

Resultado esperado: regras arquiteturais iniciais aprovadas.
<!-- END CTO_004 -->

<!-- START CTO_005 -->
## CTO_005 - Testes de Regressao Arquitetural

Objetivo: proteger as fronteiras arquiteturais por testes.

Escopo:
- validar pureza do dominio;
- validar dependencias proibidas;
- validar contratos publicos.

Resultado esperado: testes arquiteturais integrados a suite.
<!-- END CTO_005 -->

<!-- START CTO_006 -->
## CTO_006 - Organizacao de Application Services

Objetivo: centralizar fachadas consumidas por interfaces externas.

Escopo:
- identificar servicos publicos;
- proteger assinaturas;
- reduzir acesso direto a camadas internas.

Resultado esperado: application services tratados como API interna estavel.
<!-- END CTO_006 -->

<!-- START CTO_007 -->
## CTO_007 - Dashboard como Camada de Apresentacao

Objetivo: garantir que o dashboard consuma somente fachadas autorizadas.

Escopo:
- revisar imports do dashboard;
- bloquear acesso direto a providers, persistencia e dominio interno;
- validar fluxo por `DashboardService`.

Resultado esperado: dashboard isolado como UI.
<!-- END CTO_007 -->

<!-- START CTO_008 -->
## CTO_008 - Congelamento da Arquitetura Base

Objetivo: declarar a arquitetura-base consolidada.

Escopo:
- revisar dominio, core, application, replay, research e dashboard;
- registrar baseline conceitual;
- bloquear mudancas estruturais silenciosas.

Resultado esperado: arquitetura-base congelada.
<!-- END CTO_008 -->

<!-- START CTO_009 -->
## CTO_009 - Governanca de ADRs

Objetivo: instituir Architectural Decision Records.

Escopo:
- definir template de ADR;
- registrar decisoes aprovadas;
- estabelecer politica de substituicao e historico.

Resultado esperado: ADRs como memoria arquitetural oficial.
<!-- END CTO_009 -->

<!-- START CTO_010 -->
## CTO_010 - EventBus Oficial

Objetivo: consolidar eventos oficiais do sistema.

Escopo:
- revisar eventos publicados e assinados;
- impedir comunicacao lateral indevida;
- documentar eventos arquiteturais.

Resultado esperado: EventBus reconhecido como canal oficial de comunicacao.
<!-- END CTO_010 -->

<!-- START CTO_011 -->
## CTO_011 - Replay Governance

Objetivo: proteger Replay contra operacao real e infraestrutura indevida.

Escopo:
- validar ReplayService;
- validar ReplayEngine;
- impedir acesso direto a formatos fisicos de dados.

Resultado esperado: Replay restrito a simulacao e pesquisa.
<!-- END CTO_011 -->

<!-- START CTO_012 -->
## CTO_012 - Research Lab Governance

Objetivo: proteger Research Lab como ambiente quantitativo isolado.

Escopo:
- revisar experimentos, benchmarks e validadores;
- impedir acesso a broker real;
- registrar limitacoes de dados demonstrativos.

Resultado esperado: Research Lab restrito a pesquisa.
<!-- END CTO_012 -->

<!-- START CTO_013 -->
## CTO_013 - Paper Trading Visual Governance

Objetivo: diferenciar paper trading visual de execucao real.

Escopo:
- revisar motor paper;
- validar travas de broker e MT5;
- registrar natureza em memoria do fluxo.

Resultado esperado: paper trading visual sem autorizacao operacional real.
<!-- END CTO_013 -->

<!-- START CTO_014 -->
## CTO_014 - Strategy Contract Governance

Objetivo: garantir que estrategias retornem contratos e nao executem ordens.

Escopo:
- revisar `StrategySignal`;
- revisar registry de estrategias;
- bloquear imports de risco, broker e execucao nas estrategias.

Resultado esperado: estrategias protegidas por contrato comum.
<!-- END CTO_014 -->

<!-- START CTO_015 -->
## CTO_015 - Alpha 001 Playbook Governance

Objetivo: formalizar a Alpha 001 como primeira estrategia proprietaria.

Escopo:
- revisar hipotese IORB;
- registrar criterios de aceitacao e rejeicao;
- bloquear uso operacional real.

Resultado esperado: playbook Alpha 001 aprovado como referencia.
<!-- END CTO_015 -->

<!-- START CTO_016 -->
## CTO_016 - Alpha 001 Architecture Review

Objetivo: auditar a implementacao arquitetural da Alpha 001.

Escopo:
- revisar motores internos;
- revisar StrategySignal;
- revisar integracao com Replay e Research Lab.

Resultado esperado: Alpha 001 aderente a arquitetura.
<!-- END CTO_016 -->

<!-- START CTO_017 -->
## CTO_017 - Alpha 001 Validation Governance

Objetivo: estruturar validacao quantitativa da Alpha 001.

Escopo:
- revisar metrics minimas;
- revisar validators;
- registrar limites de amostra.

Resultado esperado: validacao Alpha 001 governada e rastreavel.
<!-- END CTO_017 -->

<!-- START CTO_018 -->
## CTO_018 - Dashboard Alpha 001 Governance

Objetivo: auditar a exposicao da Alpha 001 no dashboard.

Escopo:
- revisar status, ranking, relatorios e filtros;
- garantir consumo via `DashboardService`;
- impedir acesso direto a research ou estrategias.

Resultado esperado: Dashboard Alpha 001 aderente a fachada.
<!-- END CTO_018 -->

<!-- START CTO_019 -->
## CTO_019 - Data Source Governance

Objetivo: estabelecer governanca para fontes historicas.

Escopo:
- definir contratos de dados historicos;
- revisar provider default;
- impedir acoplamento de Replay e Research a arquivos fisicos.

Resultado esperado: dados historicos acessados por portas e adapters.
<!-- END CTO_019 -->

<!-- START CTO_020 -->
## CTO_020 - CSV Historical Adapter Review

Objetivo: auditar o adapter CSV como fonte historica inicial.

Escopo:
- validar contrato do adapter;
- validar compatibilidade com provider;
- registrar limitacoes do CSV.

Resultado esperado: CSV mantido como fonte historica suportada.
<!-- END CTO_020 -->

<!-- START CTO_021 -->
## CTO_021 - Data Source Checkpoint

Objetivo: consolidar checkpoint da fase Data Source.

Escopo:
- revisar CSV, Parquet e DuckDB;
- validar catalogo e registry;
- documentar fontes futuras possiveis.

Resultado esperado: fase Data Source registrada como encerrada.
<!-- END CTO_021 -->

<!-- START CTO_022 -->
## CTO_022 - Parquet Adapter Governance

Objetivo: auditar suporte Parquet em dados historicos.

Escopo:
- validar adapter Parquet;
- validar readiness gate;
- preservar isolamento de formato fisico.

Resultado esperado: Parquet governado como provider alternativo.
<!-- END CTO_022 -->

<!-- START CTO_023 -->
## CTO_023 - DuckDB Adapter Governance

Objetivo: auditar suporte DuckDB em dados historicos.

Escopo:
- validar adapter DuckDB;
- validar configuracao de tabela;
- restringir SQL ao adapter autorizado.

Resultado esperado: DuckDB governado como provider alternativo.
<!-- END CTO_023 -->

<!-- START CTO_024 -->
## CTO_024 - Historical Dataset Catalog Governance

Objetivo: revisar catalogo de datasets historicos.

Escopo:
- validar metadados;
- validar selecao de dataset;
- revisar integracao com DashboardService.

Resultado esperado: catalogo historico governado por fachada.
<!-- END CTO_024 -->

<!-- START CTO_025 -->
## CTO_025 - Data Quality Governance

Objetivo: consolidar criterios de qualidade de dados historicos.

Escopo:
- revisar OHLC invalido;
- revisar volume invalido;
- revisar gaps temporais e duplicidade.

Resultado esperado: data quality auditavel por dataset.
<!-- END CTO_025 -->

<!-- START CTO_026 -->
## CTO_026 - Data Readiness Gate Governance

Objetivo: governar bloqueios de uso de dataset em Replay e Research.

Escopo:
- revisar status de readiness;
- revisar logs do gate;
- validar metricas por provider.

Resultado esperado: datasets bloqueados quando insuficientes.
<!-- END CTO_026 -->

<!-- START CTO_027 -->
## CTO_027 - Provider Metrics Governance

Objetivo: consolidar metricas agregadas por provider historico.

Escopo:
- revisar total de datasets;
- revisar validacoes e bloqueios;
- revisar exposicao no dashboard.

Resultado esperado: metricas de provider disponiveis para auditoria.
<!-- END CTO_027 -->

<!-- START CTO_028 -->
## CTO_028 - Architecture Manifest Governance

Objetivo: consolidar manifesto tecnico da arquitetura.

Escopo:
- revisar camadas;
- revisar servicos, contratos, providers, adapters e eventos;
- validar aderencia ao baseline.

Resultado esperado: `architecture_manifest.json` auditavel.
<!-- END CTO_028 -->

<!-- START CTO_029 -->
## CTO_029 - Architecture Baseline Governance

Objetivo: proteger baseline arquitetural contra atualizacoes indevidas.

Escopo:
- revisar politica de baseline;
- registrar drift como informativo quando aplicavel;
- impedir atualizacao automatica.

Resultado esperado: baseline tratado como instrumento de auditoria.
<!-- END CTO_029 -->

<!-- START CTO_030 -->
## CTO_030 - Market Data Architecture Review

Objetivo: auditar arquitetura de Market Data.

Escopo:
- revisar providers e adapters;
- revisar isolamento de formatos;
- registrar riscos e proximas fontes possiveis.

Resultado esperado: Market Data pronto para evolucao governada.
<!-- END CTO_030 -->

<!-- START CTO_031 -->
## CTO_031 - Architecture Audit Automation

Objetivo: consolidar auditoria arquitetural automatizada.

Escopo:
- revisar script de auditoria;
- revisar relatorios JSON e Markdown;
- validar uso informativo da auditoria.

Resultado esperado: auditoria arquitetural continua disponivel.
<!-- END CTO_031 -->

<!-- START CTO_032 -->
## CTO_032 - Architecture Health Automation

Objetivo: consolidar relatorio de saude arquitetural.

Escopo:
- revisar metricas de saude;
- revisar servicos protegidos;
- revisar governanca e ADRs.

Resultado esperado: health report disponivel para revisao CTO.
<!-- END CTO_032 -->

<!-- START CTO_033 -->
## CTO_033 - Static Analysis Gate

Objetivo: integrar analise estatica ao fluxo de qualidade.

Escopo:
- revisar compilacao automatica;
- revisar ferramentas opcionais;
- registrar warnings sem mascarar falhas.

Resultado esperado: analise estatica integrada ao Quality Gate.
<!-- END CTO_033 -->

<!-- START CTO_034 -->
## CTO_034 - Quality Gate Summary Report

Objetivo: gerar resumo consolidado do Quality Gate.

Escopo:
- registrar status por etapa;
- registrar duracao e exit code;
- propagar falhas sem mascaramento.

Resultado esperado: `reports/quality_gate_summary.json` como relatorio informativo.
<!-- END CTO_034 -->

<!-- START CTO_035 -->
## CTO_035 - MANIFEST Governance

Objetivo: institucionalizar o `MANIFEST.md` como fonte oficial do estado.

Escopo:
- separar README, arquitetura e estado operacional;
- registrar sprint atual, ultima sprint e proxima missao;
- definir regra de conclusao de Sprint CTO.

Resultado esperado: MANIFEST como Single Source of Truth.
<!-- END CTO_035 -->

<!-- START CTO_036 -->
## CTO_036 - Full Project State Audit

Objetivo: auditar o estado real do projeto antes de novas decisoes.

Escopo:
- revisar modulos, testes, documentos e playbooks;
- identificar duplicidades e documentos desatualizados;
- reconstruir roadmap atualizado.

Resultado esperado: diagnostico tecnico aprovado pelo CTO.
<!-- END CTO_036 -->

<!-- START CTO_037 -->
## CTO_037 - Documentation Reconciliation

Objetivo: reconciliar documentos historicos com o MANIFEST.

Escopo:
- identificar numeros de testes antigos;
- separar historico de estado atual;
- reduzir duplicidade de status operacional.

Resultado esperado: documentacao sem fonte concorrente de estado.
<!-- END CTO_037 -->

<!-- START CTO_038 -->
## CTO_038 - Research/Application Coupling Review

Objetivo: avaliar acoplamento entre Research e Application.

Escopo:
- localizar imports cruzados;
- diferenciar ciclo real de ciclo conceitual;
- propor saneamento sem alterar comportamento.

Resultado esperado: plano de desacoplamento aprovado.
<!-- END CTO_038 -->

<!-- START CTO_039 -->
## CTO_039 - Research Lab Persistence Plan

Objetivo: planejar persistencia robusta de experimentos.

Escopo:
- mapear dados de experimentos;
- definir contrato de persistencia;
- preservar isolamento de infraestrutura.

Resultado esperado: plano aprovado antes de qualquer implementacao.
<!-- END CTO_039 -->

<!-- START CTO_040 -->
## CTO_040 - Historical Dataset Expansion Plan

Objetivo: planejar ampliacao de base historica para Alpha 001.

Escopo:
- definir criterios de amostra;
- definir formatos autorizados;
- definir validacao minima por dataset.

Resultado esperado: plano de expansao historica governado.
<!-- END CTO_040 -->

<!-- START CTO_041 -->
## CTO_041 - Coverage Governance

Objetivo: estabelecer governanca de cobertura de testes.

Escopo:
- escolher ferramenta de cobertura;
- definir metricas minimas;
- separar cobertura de qualidade funcional.

Resultado esperado: politica de cobertura aprovada.
<!-- END CTO_041 -->

<!-- START CTO_042 -->
## CTO_042 - Changelog Governance

Objetivo: definir quando e como atualizar CHANGELOG.

Escopo:
- classificar mudancas aplicaveis;
- definir formato minimo;
- alinhar com regra de conclusao de Sprint CTO.

Resultado esperado: politica de CHANGELOG aprovada.
<!-- END CTO_042 -->

<!-- START CTO_043 -->
## CTO_043 - Execution Layer Review

Objetivo: auditar camada de execucao simulada e legada.

Escopo:
- revisar `OrderManager`;
- revisar `SimulatedBroker`;
- revisar compatibilidade com contratos atuais.

Resultado esperado: estado da execucao classificado sem liberar operacao real.
<!-- END CTO_043 -->

<!-- START CTO_044 -->
## CTO_044 - Risk Engine Contract Review

Objetivo: revisar contrato entre Risk Engine e contratos de dominio.

Escopo:
- identificar compatibilidades legadas;
- revisar adaptacao para `RiskDecision`;
- preservar bloqueios operacionais.

Resultado esperado: plano de saneamento do Risk Engine aprovado.
<!-- END CTO_044 -->

<!-- START CTO_045 -->
## CTO_045 - Broker Real Readiness Block

Objetivo: formalizar bloqueios antes de qualquer broker real.

Escopo:
- listar pre-condicoes obrigatorias;
- registrar travas de MT5/corretora;
- impedir evolucao sem aprovacao explicita.

Resultado esperado: broker real mantido como nao autorizado.
<!-- END CTO_045 -->

<!-- START CTO_046 -->
## CTO_046 - IA Governance

Objetivo: formalizar limites para qualquer modulo futuro de IA.

Escopo:
- reforcar que IA nao executa ordens;
- definir campos permitidos para IA;
- alinhar com ADRs existentes.

Resultado esperado: IA mantida como nao iniciada e governada.
<!-- END CTO_046 -->

<!-- START CTO_047 -->
## CTO_047 - End-to-End Validation Plan

Objetivo: planejar validacao ponta a ponta dos fluxos principais.

Escopo:
- mapear Home, Market DNA, Replay, Research Lab, Estrategias, Eventos e Sistema;
- definir validacao Streamlit;
- preservar Quality Gate nao bloqueante.

Resultado esperado: plano E2E aprovado.
<!-- END CTO_047 -->

<!-- START CTO_048 -->
## CTO_048 - Release Readiness Review

Objetivo: avaliar prontidao para marco de release interno.

Escopo:
- revisar MANIFEST, Quality Gate, arquitetura e testes;
- revisar pendencias impeditivas;
- classificar risco de entrega.

Resultado esperado: parecer CTO de readiness.
<!-- END CTO_048 -->

<!-- START CTO_049 -->
## CTO_049 - Governance Consolidation

Objetivo: consolidar governanca acumulada das Sprints CTO.

Escopo:
- revisar roadmaps;
- revisar regras de conclusao;
- revisar documentos oficiais e historicos;
- preparar proxima fase estrategica.

Resultado esperado: governanca CTO consolidada para nova fase.
<!-- END CTO_049 -->
