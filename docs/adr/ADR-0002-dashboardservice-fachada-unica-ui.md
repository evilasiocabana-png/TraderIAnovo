# ADR-0002: DashboardService como Fachada Única da UI

- Status: Aprovado
- Data: 2026-06-26
- Autor: CTO / TraderIA

## Contexto

O dashboard Streamlit é a camada visual do sistema e precisa exibir dados de
mercado, replay, research, configuração, sessão e governança.

## Problema

Se a UI acessar providers, catálogos, persistência, adapters ou serviços
internos diretamente, a aplicação perde isolamento e passa a quebrar com
mudanças internas.

## Alternativas Consideradas

- UI acessando cada serviço diretamente.
- UI acessando infraestrutura quando necessário.
- UI consumindo apenas DashboardService.

## Decisão Adotada

`DashboardService` é a fachada única consumida pelo dashboard.

## Justificativa

A fachada centraliza orquestração de aplicação e impede acoplamento da UI com
infraestrutura ou detalhes internos.

## Impactos Positivos

- Reduz risco de AttributeError por contrato quebrado.
- Facilita testes de contrato entre UI e aplicação.
- Preserva o dashboard como camada de apresentação.

## Impactos Negativos

- Novas ações visuais exigem método público correspondente no DashboardService.

## Riscos

- Criar métodos públicos sem análise de impacto pode quebrar consumidores.

## Consequências Futuras

Toda chamada `service.*` do dashboard deve existir em `DashboardService` e ser
protegida por testes de contrato.

## Referências

- dashboard_app.py
- application/dashboard_service.py
- tests/test_dashboard_service_contract.py
- tests/test_dashboard_facade.py

## Sprints Relacionadas

- SPRINT MARKET DATA 008 a 027
- SPRINT CTO 003
- SPRINT CTO 014
