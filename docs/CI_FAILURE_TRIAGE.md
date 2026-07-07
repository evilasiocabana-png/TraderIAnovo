# CI Failure Triage

Este guia padroniza a triagem de falhas no pipeline de CI do TraderIA_WDO.

O objetivo e corrigir causa raiz sem enfraquecer arquitetura, testes,
seguranca operacional ou governanca CTO.

## Categorias de Falha

- Static analysis
- `app.py`
- Unit tests
- Architecture audit
- Architecture manifest
- Architecture baseline drift
- Repository compliance
- CI readiness
- Reproducible build
- Artifact upload
- Unknown failure

## Fluxo de Triagem

Para qualquer falha:

1. Identificar a etapa exata que falhou.
2. Ler o relatorio correspondente em `reports/`.
3. Reproduzir localmente o comando da etapa.
4. Identificar a causa raiz.
5. Corrigir preservando Clean Architecture.
6. Rodar o Quality Gate completo.
7. Confirmar o Dashboard manualmente.
8. Somente atualizar baseline ou manifesto se houver aprovacao CTO explicita.

## Proibicoes

Nunca:

- remover teste para "fazer passar";
- enfraquecer teste arquitetural;
- mascarar excecoes;
- ignorar drift sem justificativa;
- atualizar baseline automaticamente;
- atualizar manifesto sem justificativa;
- adicionar dependencia externa desnecessaria;
- aproximar o sistema de operacao real;
- integrar corretora, MT5 ou Broker real.

## Comandos de Diagnostico

Analise estatica:

```powershell
python scripts/run_static_analysis.py
```

Quality Gate:

```powershell
python scripts/run_quality_gate.py
```

Auditoria arquitetural:

```powershell
python scripts/architecture_audit.py
```

Diagnostico de falhas de testes:

```powershell
python scripts/test_failure_diagnostics.py
```

Prontidao de CI:

```powershell
python scripts/ci_readiness.py
```

Build reproduzivel:

```powershell
python scripts/reproducible_build.py
```

Suite de testes:

```powershell
python -m unittest discover -s tests
```

Dashboard Streamlit:

```powershell
python -m streamlit run dashboard_app.py
```

## Relatorios por Categoria

| Categoria | Relatorio principal |
| --- | --- |
| Static analysis | `reports/static_analysis_report.json` |
| `app.py` | `reports/quality_gate_summary.json` |
| Unit tests | `reports/test_failure_diagnostics.json` |
| Architecture audit | `reports/architecture_audit.json` |
| Architecture manifest | `architecture_manifest.json` |
| Architecture baseline drift | `reports/architecture_audit.json` |
| Repository compliance | `reports/repository_compliance.json` |
| CI readiness | `reports/ci_readiness.json` |
| Reproducible build | `reports/reproducible_build.json` |
| Artifact upload | logs do workflow de CI |
| Unknown failure | logs da etapa e ultimo relatorio disponivel |

## Criterios de Correcao Aceitavel

Uma correcao e aceitavel quando:

- resolve a causa raiz;
- preserva contratos publicos;
- nao reduz cobertura;
- nao move logica para UI;
- nao adiciona acoplamento;
- nao altera comportamento funcional fora do escopo;
- mantem todos os testes passando.

## Politica CTO

Falha no CI bloqueia entrega ate que a causa raiz seja corrigida ou formalmente
classificada pelo CTO.

Baseline so muda com aprovacao explicita. Manifesto so muda com justificativa
arquitetural. Operacao real permanece desabilitada.
