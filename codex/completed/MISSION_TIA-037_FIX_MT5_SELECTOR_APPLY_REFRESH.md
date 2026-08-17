# MISSION_TIA-037_FIX_MT5_SELECTOR_APPLY_REFRESH

Status: completed

Data: 2026-08-17

## Objetivo

Fazer o botao `Aplicar modelos` persistir a troca M23/M24 e atualizar os textos
da mesma tela de forma deterministica.

## Implementacao

- A persistencia foi movida para o callback do botao do formulario.
- O callback executa antes do rerender do fragmento Streamlit.
- Resumo, avisos e caixas passam a ser hidratados pelo novo estado persistido.

## Validacao

- quatro testes direcionados aprovados;
- teste Streamlit real M23 -> M24 aprovado;
- `python scripts/run_critical_ci.py`: 188 testes aprovados;
- painel reiniciado e `/_stcore/health` respondeu `ok`.

## Seguranca

O teste restaurou o estado operacional original e nao conectou nem enviou ordem
ao MT5.
