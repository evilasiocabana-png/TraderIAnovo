# M23/M29: retomada da perna rejeitada — 15/09/2026

Pedido: manter a posição original aceita e tentar novamente apenas a cópia rejeitada, enquanto o mesmo plano continuar válido. Sem fechamento compensatório e sem reabrir uma perna que já foi aceita e encerrada.

Escopo: XAUUSD, fonte M7 original do M23 e cópia M29/M7 dentro do M23. M29 próprio desmarcado continua sem enviar ordens. Modo continua dependente somente dos resultados originais M23/S7. Lotes e regras anteriores preservados.

A rejeição explícita gera autorização local persistida por conta identificada pelo MT5. A retomada exige o mesmo candle, origem, direção, entrada, stop, alvo, modo e lote, e a posição original ainda aberta. Existência de cópia ouro aberta impede a retomada conservadoramente, inclusive cópias legadas sem origem auditável. O estado é consumido antes da tentativa para não duplicar após falha ou reinício. Resposta incerta, erro de transporte, timeout e conexão perdida não autorizam repetição automática. Nova rejeição explícita pode renovar a espera.

O executor não consome o candle por rejeição dessa dupla; aceite continua consumindo. Todas as demais validações de sessão, regime, risco, contexto e plano permanecem. O provider confere novamente a posição original antes do envio. Se ambas abriram e uma encerrou, permanece a espera até a outra encerrar.

Validação: 198 testes passaram e 2 subtestes passaram. Dois métodos de teste antigos do M24/M25 foram excluídos da rodada final: suas três falhas por MODEL_RETIRED foram reproduzidas em memória com a mudança de retomada removida. Não se declara a suíte geral totalmente verde. Incluídos testes integrados de dois ciclos, rejeição seguida de aceite, ausência de duplicação após saída da cópia, persistência, isolamento de conta, alteração do plano, original encerrada e respostas incertas. Testes usam executores simulados; nenhuma ordem de teste foi enviada ao MT5.

Não há envio atômico: as duas ordens são sequenciais e podem executar em preços/horários distintos. Sem promessa de resultados financeiros opostos.

Alterações locais; esta etapa não realizou commit nem push.
