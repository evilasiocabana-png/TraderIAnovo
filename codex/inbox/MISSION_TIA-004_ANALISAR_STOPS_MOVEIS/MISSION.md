# MISSION_TIA-004_ANALISAR_STOPS_MOVEIS

Missão de auditoria para analisar a lógica atual dos stops móveis do TraderIAnovo sem alterar código operacional.

Objetivos:
- Mapear BREAK_EVEN, ATR_TRAILING_STOP, TRAILING_STOP, FIXED_STOP, TIME_EXIT e demais estratégias.
- Identificar onde o Lab escolhe a saída.
- Mapear o fluxo Lab -> Forex Runtime -> MT5 -> Relatórios.
- Explicar por que BREAK_EVEN ocorre com frequência.
- Criar documentação em docs/MOBILE_STOPS_ANALYSIS.md e governance/traceability/STOP_LOGIC_TRACEABILITY.md.

Critérios:
- Não alterar código operacional.
- Não quebrar testes.
- Documentar arquivos, classes e funções reais.
- Preparar a próxima missão: MISSION_TIA-005_PROJETAR_SAIDA_DINAMICA_BASEADA_EM_LEITURA_DE_MERCADO.