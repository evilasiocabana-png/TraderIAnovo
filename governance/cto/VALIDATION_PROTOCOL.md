# Validation Protocol

Validacoes obrigatorias para Sprints CTO que alterem o TraderIA_WDO.

## Comandos Obrigatorios

```powershell
python app.py
```

```powershell
python scripts/run_quality_gate.py
```

```powershell
python -m unittest discover -s tests
```

```powershell
python -m streamlit run dashboard_app.py
```

## Regras

- Falhas nao podem ser mascaradas.
- Streamlit nao deve ser executado de forma bloqueante em automacoes.
- Validacao deve ser proporcional ao risco da Sprint.
- Se qualquer validacao obrigatoria falhar, a Sprint permanece em andamento.
