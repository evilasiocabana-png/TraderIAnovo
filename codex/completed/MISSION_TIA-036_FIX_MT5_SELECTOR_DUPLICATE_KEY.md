# MISSION_TIA-036_FIX_MT5_SELECTOR_DUPLICATE_KEY

Status: completed

Data: 2026-08-17

## Objetivo

Restaurar a renderizacao do seletor operacional MT5 eliminando a colisao da
chave Streamlit `mt5_operational_model_checkbox_todos`.

## Implementacao

- `Todos` conserva sua chave historica reservada.
- Modelos reconhecidos conservam as chaves `m1` ate `m24`.
- Um ID temporariamente desconhecido usa o proprio ID normalizado como sufixo,
  sem colidir com `Todos`.
- Foi adicionado teste que simula a politica anterior ao M24 ainda em memoria.

## Seguranca

Nenhuma conexao MT5, ordem, posicao, setup ou arquivo de runtime foi alterado.

## Validacao

- testes direcionados do seletor: aprovados;
- `python -m py_compile dashboard_app.py`: aprovado;
- `git diff --check`: aprovado;
- `python scripts/run_critical_ci.py`: 188 testes aprovados.
