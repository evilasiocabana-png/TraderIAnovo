# Auditoria preventiva diaria

Todos os dias 19h America/Sao_Paulo; preservar desligamento de sexta 17h30 e abertura domingo 18h05. O agendador Codex chama a auditoria; o painel registra eventos, nao executa sozinho a auditoria de codigo.

Toda execucao deve registrar inicio e conclusao reais via application.operational_audit.event, acao Auditoria preventiva, estados INICIADA, CONCLUIDA ou CONCLUIDA_COM_PENDENCIA, com evidencias resumidas. Nao registrar como executado apenas porque foi agendado. Falhas e reparos devem ter seus proprios eventos e timestamps reais. Eventos antigos importados devem indicar a origem.

Conferir MT5, ciclo, agenda, candles por ativo, TTL, curvas, custos e identidade. Comparar deals recentes com mt5_demo_execution.jsonl e execution_attempts.jsonl; detectar ATTEMPT sem RESULT, registros alternativos, rejeicoes por persistencia e operacoes nativas sem registro. Nao inferir causa pela idade do arquivo se nao houve novas tentativas. Testar gravacao em arquivo isolado e ler de volta; nunca enviar ordens de teste. Testes de envio precisam controlar o relogio semanal apenas no processo de teste.

Falha comprovada: preservar copia, reproduzir, aplicar reparo pequeno reversivel, validar e registrar. Sem modificar estrategias, filtros, lotes, stops, selecoes ou posicoes. Nao reconstruir os detalhes antigos ausentes. Relatar falhas sem causa demonstrada como pendentes. O fechamento semanal continua sob agenda do robo; nao reativar depois do encerramento.

O journal e anterior ao envio: indisponibilidade dos dois destinos impede nova tentativa. Se a persistencia do resultado falhar depois do envio, nunca converter aceite em rejeicao ou reenviar automaticamente. Conciliar com MT5. Destino alternativo em LocalAppData/TraderIANovo/audit_fallback; manter arquivos originais.


## 2026-10-27 - Historico de execucao local autorizado
Usuario alterou auditoria para diariamente 19h Brasilia e solicitou migracao para C local. Caminho ativo resolvido por core.execution_log_storage.execution_log_path, com marcador por runtime .traderia/execution_storage.json. Demo usa C:/Users/evcab/TraderIAnovo_Refactor_Safe/Historico/mt5_demo_execution.jsonl. Nao consultar apenas o arquivo antigo no OneDrive para diagnosticar gravação. Runtime Real e caminhos explicitos preservados.
Original recusa append (Errno 22) e substituicao (WinError 5); causa de sistema operacional ainda indeterminada. Copia integral dos bytes antigos mais 384 registros alternativos deduplicados por event_id. Originais e backup mantidos. Journal de tentativas copiado. Escrita/fsync e leitura conferidas; 306 aceites conciliados no MT5; 8497 custos sem divergencia. 29 testes passaram; painel recarregado health 200. Nenhuma ordem de teste. Proxima gravacao natural no novo destino ainda precisa ser validada; nao afirmar que ocorreu.
