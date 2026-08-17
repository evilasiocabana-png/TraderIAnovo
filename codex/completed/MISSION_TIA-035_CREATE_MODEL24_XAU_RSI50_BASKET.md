# MISSION_TIA-035 - Create Model24 XAU RSI50 Basket

## Objetivo

Criar o M24 operacional, selecionavel e auditavel, sem ativacao automatica e sem envio de ordens durante a implementacao.

## Escopo executado

- contrato M24 e cesta financeira isolada;
- entradas inicial e duas reentradas;
- TP individual desligado;
- trailing monotono da reentrada RSI50;
- integracao com seletor, servico, provider, Position Manager, dashboard e relatorio;
- politica canonica de IDs atualizada ate M24;
- testes unitarios e de regressao.

## Resultado

Status: completed.

Fontes M24: M8, M10, M18, M19, M20, M21 e M22 em XAUUSD/M5.

Nenhuma ordem foi enviada. O estado operacional persistido do usuario nao foi alterado, portanto o M24 permanece desmarcado ate selecao manual.

## Validacao

- `tests/test_model24_xau_basket.py`: aprovado.
- `tests/test_mt5_demo_execution_provider.py`: aprovado.
- regressao M23/provider/robot/demo/dashboard service: aprovada.
- dashboard Streamlit: aprovado apos atualizar a expectativa M24.

## Rollback

Remover o ID M24 do seletor/politica, retirar o roteamento M24 e excluir apenas os novos arquivos de contrato/teste. Nao apagar `.traderia` nem alterar posicoes existentes.
