# MISSÃO – Investigação do Contrato do Position Manager

## Objetivo
Mapear exatamente como o Research Lab, Trade Plan, Robô Demo e Position Manager se relacionam, sem alterar código.

## Perguntas
1. O Research Lab decide: entry_price, direction, timeframe, stop inicial, RR, target, atr_stop_factor, stop_management e exit_policy?
2. O Trade Plan apenas materializa o plano ou recalcula stop, RR, target ou ATR?
3. O Robô Demo envia exatamente o plano recebido ao MT5 ou adapta algum campo?
4. O Position Manager consegue fechar posição antes do TP? Em quais condições?
5. O Position Manager apenas move SL ou também pode emitir fechamento de posição? Identificar os métodos existentes.
6. BREAK_EVEN e ATR_TRAILING_STOP nascem ativos ou apenas como política futura? Onde isso é definido?
7. Existe hoje lógica de enfraquecimento, perda de momentum, reversão, falha de continuação ou incapacidade provável de atingir o TP?
8. O relatório diferencia TP, SL, Break-even, Trailing e Fechamento antecipado?
9. Investigar o contrato futuro ideal:
- Research Lab decide entrada, stop inicial, RR e política de saída.
- Trade Plan apenas materializa.
- Robô executa.
- Position Manager atua somente após posição aberta.
- Position Manager pode encerrar antecipadamente quando detectar perda de potencial.
10. Levantar testes existentes e lacunas.

## Entregável
Gerar relatório Markdown com estado atual, arquivos envolvidos, responsabilidades, lacunas, riscos, proposta de contrato futuro e testes necessários.

**Não implementar nenhuma alteração. Apenas investigar e documentar.**