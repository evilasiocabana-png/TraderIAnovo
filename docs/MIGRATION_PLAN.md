# Plano de Migracao e Organizacao

Objetivo: manter o local atual funcionando e usar o GitHub para organizar,
documentar e proteger o projeto contra retrabalho.

## Regra principal

Nao mudar o local de trabalho atual sem uma fase especifica:

```text
C:\Users\evcab\OneDrive\Documentos\TraderIA_WDO
```

O GitHub deve refletir o codigo e a documentacao organizada. A reorganizacao
fisica de pastas fica para etapas futuras, pequenas e reversiveis.

## Estado atual

- Repositorio Git local criado.
- Remote GitHub configurado em `origin`.
- Branch principal: `main`.
- Tag de seguranca: `baseline-20260706`.
- Runtime, logs, snapshots e bancos locais excluidos por `.gitignore`.

## Fase 1 - Organizacao documental

Status: em andamento.

Entregas:

- README como porta de entrada.
- Mapa do projeto.
- Documentacao de runtime e artefatos.
- Fluxo Lab, Forex e MT5.
- Plano de migracao.
- Checklist de mudanca segura.
- Contrato Lab -> Forex -> MT5.
- Contrato do JSON visual MT5.

## Fase 2 - Governanca de commits

Cada mudanca deve ter escopo pequeno:

- um bug por commit;
- uma refatoracao por commit;
- uma documentacao por commit;
- uma validacao registrada por commit.

Evitar commits misturando UI, Lab, MT5, dados e arquitetura ao mesmo tempo.

## Fase 3 - Contratos antes de mover pastas

Antes de qualquer reorganizacao fisica:

1. Congelar contratos Lab -> Forex -> MT5.
2. Criar testes de contrato para view model e JSON visual.
3. Confirmar runner e Streamlit com responsabilidades claras.
4. Confirmar restore point e tag Git.

## Fase 4 - Refatoracao incremental

Ordem recomendada:

1. Extrair partes de `dashboard_app.py` por telas ou componentes.
2. Extrair partes de `DashboardService` por dominio:
   - Forex/MT5;
   - Research Lab;
   - Replay;
   - Visual signals;
   - Auditoria de execucao.
3. Manter compatibilidade publica enquanto os testes passam.
4. Atualizar docs junto com cada etapa.

## Fase 5 - Dados e snapshots

Snapshots grandes e dados operacionais devem ter politica propria:

- fora do Git;
- nomeados por data/versao;
- restauraveis por procedimento;
- se necessario, armazenados em release artifact, drive ou storage separado.

## Validacao minima por etapa

Para mudancas pequenas:

```powershell
python -m py_compile dashboard_app.py application\dashboard_service.py application\mt5_market_data_service.py application\mt5_visual_signal_exporter.py application\dashboard_view_model.py research\mt5_research_trade_plan.py scripts\mt5_forex_cycle_runner.py infrastructure\market_data\mt5_market_data_provider.py
```

Para mudancas maiores, rodar testes focados conforme a area alterada.
