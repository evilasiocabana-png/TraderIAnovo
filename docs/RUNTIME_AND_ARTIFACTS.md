# Runtime e Artefatos Locais

Este repositorio nao deve tentar versionar a maquina inteira. Ele versiona o
codigo e a documentacao; o runtime e os artefatos locais permanecem fora do Git.

## Ficam fora do Git

| Caminho | Motivo |
|---|---|
| `Python/` | Runtime Python local; deve ser recriado por dependencias. |
| `.traderia/` | Estado operacional, snapshots, restore points e logs. |
| `.traderia/mt5_research_snapshot.json` | Snapshot grande do Lab/MT5. |
| `.traderia/restore_points/` | Backups locais. |
| `.traderia/audits/` | Auditorias locais e inventarios. |
| `logs/` | Logs de execucao. |
| `*.log` | Logs Streamlit/MT5. |
| `*.pid` | Marcadores de processo local. |
| `*.db`, `*.sqlite`, `*.sqlite3` | Bancos locais. |
| `data/market_dna/*.jsonl` | Diario operacional de mercado. |
| `*.zip` | Backups e pacotes locais. |
| `*.ex5`, `*.ex4` | Compilados MT5. |
| `.env` | Credenciais reais. |

## Ficam no Git

| Tipo | Exemplos |
|---|---|
| Codigo Python | `application/`, `research/`, `market/`, `tests/` |
| Fonte MT5 | `mt5/indicators/*.mq5` |
| Templates MT5 | `mt5/templates/*.tpl` |
| Documentacao | `README.md`, `docs/`, ADRs |
| Configuracao sem segredo | `.env.example`, `.gitignore`, `.github/` |
| Manifesto operacional do Lab | `research/alpha_suggested/lab_operational_models_manifest.json` |

O manifesto operacional e versionado porque define quais resultados pesquisados
podem chegar ao forward Demo. Os artefatos brutos que o geraram permanecem em
`.traderia/research/` e continuam fora do Git.

## Variaveis de ambiente

O arquivo `.env.example` documenta as variaveis esperadas sem gravar segredo:

```text
MT5_LOGIN=
MT5_PASSWORD=
MT5_SERVER=
TRADERIA_MT5_VISUAL_SIGNALS_ENABLED=1
TRADERIA_MT5_FOREX_CYCLE_SECONDS=10
# Opcional: deixe ausente para o Lab receber os 5000 candles configurados.
TRADERIA_MT5_EXTERNAL_MAX_CANDLES=
```

Credenciais reais devem ficar apenas no ambiente local.

## Restauracao

O baseline de seguranca tem duas camadas:

| Camada | Local |
|---|---|
| Git | Tag `baseline-20260706` |
| Backup local | `.traderia/restore_points/20260706_github_migration_audit_baseline` |

Para restaurar pelo Git:

```powershell
git checkout baseline-20260706
```

Para restaurar pelo backup local, usar o README dentro da pasta de restore point.
