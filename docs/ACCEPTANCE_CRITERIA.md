# Acceptance Criteria

## Criterios Gerais

Toda mudanca deve:

- preservar abertura do app em `http://localhost:8532`;
- manter `.traderia/` fora do Git;
- ter validacao local minima;
- evitar ciclos automaticos bloqueantes;
- respeitar o limite read-only/demo do MT5;
- atualizar documentacao quando mudar fluxo operacional.

## MT5 Forex

Aceito quando:

- aba abre sem chamar leitura MT5 pesada por ciclo;
- mostra ultimo estado local ou snapshot disponivel;
- nao trava a UI quando MT5 esta lento;
- nao possui botao ou texto prometendo atualizacao automatica por ciclo;
- nao envia ordem real.

## Lab

Aceito quando:

- usa `.traderia/` local da TraderIA Novo;
- nao depende de `TraderIA_WDO`;
- `Atualizar calculos` roda localmente;
- se nao houver candles completos, preserva ultimo snapshot local valido;
- resultados pesados nao entram no Git.

## Relatorios

Aceito quando:

- carrega auditoria local ao abrir;
- guarda cache de sessao;
- atualiza por botao;
- mostra totais de registros, aceitos, auditados, conferencias e divergencias;
- nao reroda por fragmento/ciclo automatico.

## GitHub

Aceito quando:

- codigo e docs sao commitados;
- remoto `origin` aponta para `evilasiocabana-png/TraderIAnovo`;
- `.gitignore` protege runtime local;
- commits tem mensagens claras.

## Validacao Minima

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m py_compile dashboard_app.py application\dashboard_service.py
```

## Validacao Funcional Recomendada

```powershell
python - <<'PY'
from application.dashboard_service import DashboardService
s = DashboardService()
print(len(s.get_mt5_research_constants().rows))
report = s.get_mt5_trade_audit_report()
print(report.total_local_records, report.total_audited, report.total_matched)
PY
```

## Modelo 24 XAU RSI50 Basket

Aceito quando:

- opera somente XAUUSD/M5 pelas fontes M8, M10 e M18-M22;
- entrada inicial exige micropivo 1+1, cruzamento RSI50 e fechamento alem da SMA20;
- reentrada estrutural permanece pendente Stop e reentrada RSI50 entra a mercado;
- nenhuma ordem M24 envia TP individual ao MT5;
- SL da reentrada a mercado nunca afrouxa;
- saidas nativas de seguranca da fonte continuam ativas;
- cesta fecha somente posicoes M24 em +US$1.000 liquidos;
- comentarios, estado, auditoria e relatorio distinguem M24 de M23;
- testes nao conectam nem enviam ordem ao MT5.
