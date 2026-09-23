Recarga concluida pelo launcher oficial. Health ok e pagina HTTP200;
selecao, estado online e agenda preservados por hash. Real DISABLED.
Construtor historico M29 aceita historical_alternations em processo novo;
a recarga remove a classe antiga em memoria observada no erro do relatorio.
Nenhuma ordem enviada para testar, nenhum ajuste de posicao executado.

# M23 initial USD200 loss defense

Authorized 2026-09-23. Extends defense to all new direct M23 source orders,
including M18/M20, across symbols and volumes. M23 source M29 is deliberately
excluded here: its current normal/mirror configuration and existing scoped
USD200 defense remain unchanged. No change to M29 sources or sizing.

The executor applies application/model23_fixed_loss_stop.py after constructing
the broker request, before order_check and order_send. It prices gross loss
with broker order_calc_profit at the request entry and actual request volume.
USD account required; no guessed currency conversion. A structural stop with
loss <= USD200 is retained exactly. Larger risk is reduced by bounded search
and tick rounding toward entry. Missing calculation, invalid prices/volume,
non-USD account or an unrepresentable compliant stop rejects the new entry.
Broker stop-distance checks still apply; rejection never widens the stop.

Only SL changes. TP, entry, lot, source, RSI invalidation, basket exits and other
existing early exits remain applicable. This is neither trailing nor a target
loss to wait for. Existing positions and accepted pending orders are not
retroactively edited or closed by this extension. Normal pre-existing order
lifecycle rules remain unchanged. Gaps, slippage, fees and swap can make actual
loss exceed the modeled USD200. Stop metadata logs structural and applied SL.

M18/M20 example: SELL 4284.08, SL 4292.37, 0.10 at 100 units/lot has USD82.90
modeled risk and is preserved. SELL reentry RSI14 >=50 remains an early exit.

Validation uses only fake brokers; no test trades or Real activation.
241 tests and four subtests passed across defense, provider, M29 compatibility,
basket and reentry/RSI suites. Runtime reload and publication recorded separately.
