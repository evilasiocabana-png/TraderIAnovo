# traderiaianovo

Projeto inicial limpo inspirado no TraderIA, preparado para GPT, governanca por
Inbox e dashboard Streamlit com tres abas:

- Forex MT5
- Lab
- Relatorio

Esta base nao executa ordens reais. O MT5 e tratado como fronteira read-only.

## Como rodar

```powershell
pip install -r requirements.txt
python -m streamlit run dashboard_app.py --server.port 8530 --server.headless true
```

## Como testar

```powershell
python -m unittest discover -s tests -t .
```

## Fluxo Inbox

Missoes entram em `codex/inbox/` e sao executadas pelo Codex seguindo a
governanca em `governance/execution/`.

Comando oficial:

```text
Inbox.
```

## Politica read-only

- Nao usar `order_send()`.
- Nao criar broker operacional.
- Nao conectar corretora em modo operacional.
- UI consome apenas `application/DashboardService`.
- Integracoes MT5 permanecem read-only.

## Nao versionar

- `Python/`
- `.traderia/`
- `logs/`
- relatorios gerados
- `.env`
- backups zipados
- bancos locais
- compilados MT5
