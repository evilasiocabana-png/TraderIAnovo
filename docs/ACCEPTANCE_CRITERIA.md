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
- nunca reutiliza precos/SL do XAUUSD para gerar candidato em outro simbolo;
- entrada inicial exige cruzamento do preco na SMA20 e do RSI14 no nivel 50 na
  mesma direcao; os eventos podem ocorrer em M5 diferentes, mas ambos precisam
  permanecer validos ate o segundo completar o sinal;
- entrada inicial usa micro pivo 1+1 anterior mais proximo como SL e entra a
  mercado somente depois da confirmacao do conjunto;
- entrada principal nao exige SMA20 acima/abaixo da SMA50 e nao executa Full
  Exit quando essas duas medias invertem; BUY e SELL sao simetricos;
- reentrada nao exige novo cruzamento: BUY requer fechamento acima da SMA20 e
  RSI14 acima de 50; SELL requer fechamento abaixo da SMA20 e RSI14 abaixo de 50;
- reentrada e pendente na maxima/minima do ultimo M5 e deve ser atualizada a
  cada novo candle enquanto as condicoes permanecerem validas;
- plano-base H1 sem gatilho nao bloqueia a materializacao do plano proprio M5
  do M24;
- o avaliador M24 aceita diretamente os objetos `Candle` canonicos recebidos do
  cache operacional, sem conversao manual de campos;
- a entrada inicial M24 envia `tp=0`; a reentrada envia TP no fechamento da
  vela do ultimo topo/fundo principal 2+2 confirmado na janela de ate 200 M5;
- o TP da reentrada nunca usa a maxima/minima da vela estrutural;
- a reentrada exige SL em micro pivo 1+1 confirmado nos ultimos cinco
  candles M5 fechados;
- o SL da reentrada so avanca para um novo micro pivo favoravel e nunca
  afrouxa;
- depois de Full Exit BUY no retorno do RSI abaixo de 70 ou SELL no retorno
  acima de 30, a primeira oportunidade de reentrada na mesma direcao e ignorada;
- repeticoes do mesmo sinal na mesma vela M5 nao contam como segunda
  oportunidade; somente uma nova oportunidade valida em nova vela e liberada;
- Full Exit RSI 70/30, SL individual e cesta continuam ativos na entrada
  principal; perda do RSI50 e inversao SMA20/50 continuam ativas somente nas
  reentradas;
- cesta fecha somente posicoes M24 em +US$1.000 liquidos;
- comentarios, estado, auditoria e relatorio distinguem M24 de M23;
- a tabela `Em negociacao` mostra `Tipo de entrada` antes de `Alvo`, usando
  `PRINCIPAL` ou `REENTRADA` somente quando o contrato persistido comprovar;
- testes nao conectam nem enviam ordem ao MT5.

## Modelo 25 Multiativo M5

Aceito quando:

- cobre exatamente os 19 ativos canonicos em M5;
- replica entrada, reentrada e saida tecnica do M24 sem alterar o M24;
- mantem estado, duplicidade e papeis `INITIAL/REENTRY` independentes por ativo;
- admite no maximo uma posicao de cada papel por ativo e bloqueia lados opostos;
- usa `0,20` lote na inicial e `0,10` na reentrada;
- aplica pip `0,0001` no Forex comum e `0,01` em JPY, XAUUSD e BTCUSD;
- usa `tp=0` na entrada inicial e o fechamento do ultimo pivo principal 2+2
  confirmado como TP da reentrada, sem usar a maxima/minima desse candle;
- usa somente o snapshot M5 compartilhado e nao chama Lab pesado no runtime;
- bloqueia ordens depois de reinicio ate reconciliar o cache com o MT5 vivo;
- fecha somente a cesta M25 ao atingir `+US$1.000` liquidos;
- aparece no seletor, Entrada Teorica, Saida Teorica e Relatorio;
- preserva bloqueio de conta real e testes nao enviam ordens ao MT5.
