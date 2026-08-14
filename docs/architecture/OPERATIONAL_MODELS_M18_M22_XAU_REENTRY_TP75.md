# Modelos Operacionais M18-M22 - Reentrada XAU com alvo estrutural

## Estado

Contrato operacional Demo implementado em 12/08/2026.

## Mapeamento

| Novo modelo | Origem preservada | Filtro de entrada |
|---|---|---|
| M18 | M8 | SMA20/50 + RSI14/50 |
| M19 | M9 | Base + ADX14 > 25 |
| M20 | M10 | Base + distancia SMA/ATR >= 0,25 |
| M21 | M11 | Base + inclinacao SMA50/ATR >= 0,05 |
| M22 | M12 | Base + ADX, distancia/ATR e inclinacao |

M8-M12 nao foram alterados. Os identificadores legados M18-M22 continuam
historicos; os novos IDs completos sao distintos e explicitamente ativos.

## Contrato de entrada e saida

1. A entrada inicial repete integralmente sinal, direcao e SL estrutural do modelo
   de origem.
2. A entrada inicial e a mercado e nao possui TP fixo.
3. O Full Exit original por RSI 70/30 ou inversao SMA permanece ativo na entrada inicial.
4. Quando o runtime identifica uma retomada valida, ele pode armar novas
   reentradas na mesma direcao enquanto o contexto permanecer valido.
5. A reentrada usa BUY_STOP no topo ou SELL_STOP no fundo do ultimo candle M5
   fechado, preservando o SL estrutural.
6. Somente a reentrada recebe TP: BUY mira o ultimo topo M5 confirmado antes da
   correcao; SELL mira o ultimo fundo M5 confirmado antes da correcao.
7. Reentrada BUY exige RSI14 fechado acima de 50 e executa Full Exit quando um
   candle fechar em 50 ou abaixo. Reentrada SELL exige RSI14 abaixo de 50 e
   executa Full Exit quando um candle fechar em 50 ou acima. A verificacao usa o
   estado atual e continua segura depois de reinicio, mesmo se o cruzamento ocorreu
   enquanto o app estava desligado.
8. A inversao SMA20/SMA50 tambem permanece como Full Exit. As reentradas podem
   repetir em novos recuos/retomadas, mas o mesmo candle/plano nao pode duplicar.
9. Cada BUY_STOP/SELL_STOP vale por um candle M5. Se nao executar, no fechamento
   seguinte a pendencia anterior e removida e reposicionada na nova maxima
   fechada para BUY ou nova minima fechada para SELL, com SL e TP estrutural
   novamente validados.

## Fronteiras

- DashboardService materializa o plano e o alvo.
- MT5DemoRobotService valida fonte, SL e TP conforme o tipo da entrada.
- DemoExecutionService bloqueia reentrada sem TP valido.
- MT5DemoExecutionProvider envia o TP junto da ordem pendente.
- PositionManager identifica entrada inicial/reentrada e atualiza o estado do ciclo.
- Relatorio usa o ID operacional completo gravado na ordem para separar M18-M22;
  registros legados com o mesmo numero nao entram nas novas curvas.

## Evidencia e limite

A mudanca substitui o alvo fixo experimental por uma referencia estrutural do
proprio movimento. Isso nao representa garantia de lucro. A aprovacao permanece
exclusiva para conta Demo ate existir amostra prospectiva suficiente.

## Rollback

Remover os cinco IDs de `ACTIVE_SCOPED_MODEL_IDS` e da selecao operacional
interrompe novas entradas sem alterar M8-M12 nem reinterpretar o historico. Os
arquivos `.traderia/model18_runtime_state.json` a `model22_runtime_state.json`
sao estado local e nunca devem ser versionados.
