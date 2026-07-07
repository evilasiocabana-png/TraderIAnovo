# Execution Protocol

Este protocolo e obrigatorio para qualquer execucao de Sprint CTO.

## Fluxo Obrigatorio

1. Ler `STATE.json`.
2. Abrir o roadmap correspondente.
3. Localizar a Sprint indicada em `current_sprint`.
4. Executar somente aquela Sprint.
5. Rodar validacoes.
6. Atualizar `STATE.json`.
7. Gerar relatorio.
8. Parar.

## Regras

- Jamais executar duas Sprints na mesma rodada.
- Jamais antecipar Sprint futura.
- Jamais implementar funcionalidade fora do escopo da Sprint atual.
- Jamais alterar contratos sem autorizacao explicita.
- Jamais mascarar falhas de validacao.
- Ao finalizar a Sprint, parar imediatamente.
