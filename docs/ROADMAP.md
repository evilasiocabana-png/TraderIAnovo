# Roadmap

## Agora

- Manter TraderIA Novo rodando em `localhost:8532`.
- Consolidar Lab local em `.traderia/`.
- Garantir MT5 Forex rapido sem ciclo automatico bloqueante.
- Garantir Relatorios funcionais com cache local.
- Criar documentacao mestre para agentes.

## Proximas Missoes

1. Criar validador local de `.traderia/`.
2. Criar health check das abas MT5 Forex, Lab e Relatorios.
3. Limpar textos antigos e acentuacao corrompida na UI.
4. Documentar contrato do banco `traderia_mt5_history.sqlite`.
5. Criar teste automatizado para `DashboardService` nas tres abas.

## Medio Prazo

- Melhorar persistencia de candles no SQLite local.
- Reduzir dependencia de snapshots JSON grandes.
- Criar painel de saude operacional.
- Separar relatorios de execucao demo, auditoria MT5 e resultados do Lab.
- Criar rotina de backup local de `.traderia/` sem subir para Git.

## Longo Prazo

- Evoluir biblioteca de Alphas com governanca.
- Melhorar stop management por ativo/setup/timeframe.
- Criar pipeline de validacao antes de armar robo demo.
- Preparar ambiente de desenvolvimento em Codespaces sem MT5 real.

## Itens Fora Do Roadmap Sem Nova Decisao

- Operacao real.
- Migracao fisica da pasta local.
- Versionamento de snapshots pesados.
- Reintroducao de ciclos automaticos bloqueantes.

