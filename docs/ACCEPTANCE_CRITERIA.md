# Acceptance Criteria

`M24_CONTRACT=M24_SETUP_V5_20260819; SHA256=671f36c14a1762b47e401b937a1798e7eaee5f8028ebea19014e584d9895dbef`

`M25_CONTRACT=M25_XAU_SOURCES_V2_20260819; FINGERPRINT=a12f39d9751994ea`

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

- opera uma unica rota autonoma `M24_PROPRIO` somente em XAUUSD/M5; IDs de
  fontes M8, M10 e M18-M22 sao reconhecidos apenas em historico legado;
- nunca reutiliza precos/SL do XAUUSD para gerar candidato em outro simbolo;
- entrada inicial exige novo cruzamento do preco na SMA20 e novo cruzamento do
  RSI14 em 50 na mesma direcao; podem ocorrer em candles M5 diferentes, mas
  ambos devem existir e permanecer validos;
- a distancia atual `abs(SMA20-SMA50)/ATR14` deve ser maior ou igual a
  `0,25` para liberar a entrada;
- entrada inicial entra a mercado sem micro-pivo; o cruzamento preco/SMA20
  permanece como gatilho, mas o SL usa o M5 fechado imediatamente anterior:
  minima menos `0,01` no BUY e maxima mais `0,01` no SELL;
- depois de dois fechamentos favoraveis consecutivos, a SMA20 pode apertar o
  SL inicial e nunca afrouxa-lo;
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
- a entrada inicial M24 envia TP fixo a `0,25` do preco executavel; BUY soma
  `0,25` e SELL subtrai `0,25`;
- a reentrada exige TP no fechamento do microtopo/microfundo 1+1 lucrativo
  mais recente;
- o TP da reentrada nunca usa a maxima/minima da vela estrutural;
- a reentrada exige SL em micro pivo 1+1 confirmado nos ultimos cinco
  candles M5 fechados;
- o SL da reentrada so avanca para um novo micro pivo favoravel e nunca
  afrouxa;
- depois de Full Exit BUY no retorno do RSI abaixo de 70 ou SELL no retorno
  acima de 30, a primeira reentrada valida na mesma direcao pode ser liberada;
- `CONTINUATION` somente e armada por uma `REENTRY` aceita e so entra depois
  que o historico MT5 confirmar o encerramento efetivo dessa reentrada por TP;
- BUY `CONTINUATION` exige preco acima do TP anterior e RSI14 maior que 70;
  SELL exige preco abaixo do TP anterior e RSI14 menor que 30;
- `CONTINUATION` entra a mercado com `0,40` lote, SL na minima do M5 fechado
  anterior menos um pip no BUY ou maxima mais um pip no SELL, TP fixo a `0,13`
  do preco executavel e saida integral no retorno do RSI abaixo de 70 no BUY
  ou acima de 30 no SELL;
- existe no maximo uma posicao M24 aberta por papel (`INITIAL`, `REENTRY` e
  `CONTINUATION`) e lados opostos nunca coexistem;
- Full Exit RSI 70/30, inversao do RSI50, SL individual e cesta permanecem
  ativos na entrada inicial, reentrada e continuacao; inversao SMA20/50 nao
  encerra nenhuma posicao M24;
- cesta fecha somente posicoes M24 em +US$1.000 liquidos;
- comentarios, estado, auditoria e relatorio distinguem M24 de M23;
- a tabela `Em negociacao` mostra `Tipo de entrada` antes de `Alvo`, usando
  `PRINCIPAL`, `REENTRADA` ou `CONTINUAÇÃO` somente quando o contrato persistido
  comprovar;
- testes nao conectam nem enviam ordem ao MT5.

## Modelo 25 - cesta das fontes XAU

Aceito quando:

- opera exclusivamente `XAUUSD/M5`;
- avalia exatamente M8, M10, M18, M19, M20, M21 e M22;
- copia sem recalculo direcao, candle, ordem, entrada, SL e TP da fonte;
- mantem estado, duplicidade e papeis `INITIAL/REENTRY` independentes por fonte;
- admite no maximo uma posicao de cada papel por fonte e bloqueia lados opostos;
- usa `0,20` lote na inicial e `0,10` na reentrada;
- nao inventa TP: preserva a ausencia de alvo ou o alvo estrutural da fonte;
- usa somente o snapshot M5 compartilhado e nao chama Lab pesado no runtime;
- rejeita no Robo Demo e no provider qualquer simbolo diferente de XAUUSD;
- fecha somente a cesta M25 ao atingir `+US$1.000` liquidos;
- aparece no seletor, Entrada Teorica, Saida Teorica e Relatorio;
- nao entra em `Todos` nem se combina acidentalmente com M23/M24;
- preserva o historico V1 sem ler seu estado no roteamento V2;
- preserva bloqueio de conta real e testes nao enviam ordens ao MT5.
