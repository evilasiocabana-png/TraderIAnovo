# MT5 Visual Signals Indicator

## Objetivo

Criar uma ponte visual read-only entre o TraderIA e o MetaTrader 5.

O TraderIA continua sendo o cerebro da decisao:

- modelo ativo;
- BUY, SELL ou WAIT;
- entrada teorica;
- stop;
- alvo;
- RR;
- motivo;
- status do plano.

O MT5 apenas desenha essas informacoes no grafico.

## Arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| `application/mt5_visual_signal_exporter.py` | Gera o JSON visual a partir do `DashboardViewModel` |
| `mt5/indicators/TraderIAVisualSignals.mq5` | Indicador visual read-only para MT5 |
| `.traderia/traderia_signals.json` | Caminho padrao de exportacao no projeto |

## JSON Visual

Schema:

```json
{
  "schema_version": "traderia.mt5.visual_signals.v1",
  "mode": "VISUAL_ONLY",
  "read_only": true,
  "order_execution": "NOT_ALLOWED_BY_INDICATOR",
  "signals": [
    {
      "symbol": "EURUSD",
      "timeframe": "H1",
      "timestamp": "29/06/2026 18:00",
      "decision": "BUY",
      "entry": 1.1422,
      "stop": 1.1402,
      "target": 1.1482,
      "rr": 3.0,
      "model": "TREND_MOMENTUM",
      "plan_status": "PLANO_VALIDO",
      "reason": "Plano visual pronto."
    }
  ]
}
```

## Uso

1. No TraderIA, abrir a aba `MT5 Forex`.
2. Clicar em `Exportar visual MT5`.
3. Copiar o JSON gerado para a pasta `MQL5/Files` do terminal MT5, quando necessario.
4. Copiar `mt5/indicators/TraderIAVisualSignals.mq5` para `MQL5/Indicators`.
5. Compilar o indicador no MetaEditor.
6. Anexar o indicador ao grafico do simbolo correspondente.

Opcionalmente, definir:

```text
TRADERIA_MT5_VISUAL_SIGNALS_PATH=C:\...\MQL5\Files\traderia_signals.json
```

Assim o TraderIA exporta diretamente para a pasta lida pelo indicador.

## O Que O Indicador Desenha

| Condicao | Visual |
| --- | --- |
| BUY | Seta verde |
| SELL | Seta vermelha |
| WAIT | Sem seta |
| Entrada | Linha azul |
| Stop | Linha vermelha |
| Alvo | Linha verde |
| Texto | Modelo, RR e status do plano |

## Restricoes

- O indicador nao envia ordens.
- O indicador nao calcula estrategia.
- O indicador nao acessa broker.
- O indicador nao altera posicoes.
- O indicador nao substitui o Research Lab.
- O indicador apenas le arquivo visual e desenha objetos no grafico.

## Status

`TRADERIA_MT5_VISUAL_INDICATOR_READY`
