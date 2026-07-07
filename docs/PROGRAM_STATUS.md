# Program Status

## Resumo

| Programa | Status | Observacao |
| --- | --- | --- |
| A01 Foundation | ativo | Estrutura GitHub, governanca e app local existem. |
| A02 Forex MT5 | estabilizando | Aba deve abrir por snapshot/local sem ciclo bloqueante. |
| B01 Lab | estabilizando | Motor roda localmente em `.traderia/` da TraderIA Novo. |
| C01 Reports | estabilizando | Auditoria local funcional e carregada sob cache de sessao. |
| D01 GitHub Governance | ativo | Codigo/documentacao no GitHub; runtime local ignorado. |

## Estado Operacional Atual

- App: `http://localhost:8532`
- Nome visual: `TraderIA Novo`
- Runtime local: `.traderia/`
- Repositorio remoto: `evilasiocabana-png/TraderIAnovo`

## Ultimas Decisoes

- MT5 Forex nao atualiza por ciclo automatico na aba.
- Lab nao depende de `TraderIA_WDO`.
- Relatorios carregam auditoria local ao abrir e atualizam por botao.
- Codigo vai para GitHub; runtime local fica fora do Git.

## Riscos Abertos

- Snapshot do Lab ainda pode ser grande.
- Banco local ainda precisa de contrato formal.
- MT5 pode ficar lento ou indisponivel dependendo do terminal.
- Textos antigos com acentuacao corrompida ainda existem em partes da UI.

