# Mapa do Projeto TraderIA

Este documento mapeia o projeto sem exigir mudanca de local ou reorganizacao
fisica imediata. A pasta local oficial continua sendo:

```text
C:\Users\evcab\OneDrive\Documentos\TraderIA_WDO
```

## Entrada principal

| Caminho | Papel |
|---|---|
| `dashboard_app.py` | Aplicacao Streamlit principal. |
| `app.py` | Entrada/apoio historico do projeto. |
| `scripts/mt5_forex_cycle_runner.py` | Runner leve para ciclo Forex/MT5. |
| `mt5/indicators/TraderIAVisualSignals.mq5` | Fonte do indicador visual do MT5. |
| `mt5/templates/TraderIAVisualSignals.tpl` | Template MT5 associado ao indicador. |

## Camadas de codigo

| Pasta | Papel | Git |
|---|---|---|
| `application/` | Casos de uso, servicos de aplicacao e fachada do dashboard. | Sim |
| `domain/` | Contratos e entidades de dominio. | Sim |
| `core/` | Componentes centrais de motor, eventos, sessao e decisao. | Sim |
| `research/` | Pesquisa, laboratorio, ranking, validacao e planos. | Sim |
| `market/` | Leitura de mercado, contexto, estrutura, features e instrumentos. | Sim |
| `market_data/` | Fontes, adapters e catalogos de dados historicos. | Sim |
| `infrastructure/` | Integracoes externas, MT5 provider e resolucao de paths. | Sim |
| `strategies/` | Estrategias certificadas/experimentais. | Sim |
| `risk/` | Politicas e calculos de risco. | Sim |
| `decision/` | Qualidade, score e relatorio de decisao. | Sim |
| `replay/` | Replay de candles/datasets. | Sim |
| `backtest/` | Backtests e metricas. | Sim |
| `analytics/` | Leitura analitica e estatisticas. | Sim |
| `database/` | Codigo de persistencia, nao banco local. | Sim |
| `tests/` | Testes automatizados. | Sim |
| `scripts/` | Ferramentas operacionais e de governanca. | Sim |
| `docs/` | Documentacao viva. | Sim |

## Dados e artefatos

| Caminho | Papel | Git |
|---|---|---|
| `.traderia/` | Estado operacional, snapshots, logs, restore points. | Nao |
| `Python/` | Runtime Python local. | Nao |
| `logs/` | Logs operacionais. | Nao |
| `reports/` | Saidas geradas. | Nao por padrao |
| `resultados/` | Saidas geradas. | Nao por padrao |
| `data/traderia.db` | Banco local. | Nao |
| `data/market_dna/*.jsonl` | Diario operacional de mercado. | Nao |
| `historical_data/` | Datasets pequenos e metadados historicos. | Sim, com revisao |

## Arquivos de maior atencao

| Arquivo | Motivo |
|---|---|
| `application/dashboard_service.py` | Fachada muito grande; concentra responsabilidades. |
| `dashboard_app.py` | UI Streamlit extensa; risco alto de regressao em mudancas visuais. |
| `application/mt5_market_data_service.py` | Leitura MT5 e dados de mercado. |
| `application/mt5_visual_signal_exporter.py` | Contrato JSON visual para MT5. |
| `research/mt5_research_trade_plan.py` | Contrato de entrada, stop e alvo vindo do Lab. |
| `mt5/indicators/TraderIAVisualSignals.mq5` | Desenho visual no MT5. |

## Regra de organizacao

Organizar primeiro por documentacao, branches e commits. Mudancas fisicas de
pastas so devem acontecer depois de uma etapa especifica, pequena e validada.
