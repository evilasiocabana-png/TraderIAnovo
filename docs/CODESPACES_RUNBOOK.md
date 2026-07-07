# TraderIA Nuvem no GitHub Codespaces

Este projeto pode ser aberto no GitHub Codespaces para editar codigo, rodar testes
criticos e visualizar o dashboard em modo nuvem.

## Como abrir

1. Acesse `https://github.com/evilasiocabana-png/TraderIA`.
2. Clique em `Code`.
3. Abra a aba `Codespaces`.
4. Clique em `Create codespace on main`.

## Como rodar o app na nuvem

No terminal do Codespaces:

```bash
streamlit run dashboard_app.py --server.port 8530 --server.headless true
```

Depois abra a porta encaminhada `8530`.

O titulo da aba fica como:

```text
TraderIA Nuvem
```

## Limite importante

O Codespaces nao roda o MetaTrader 5 local do Windows.

Na nuvem, use o TraderIA para:

- editar codigo;
- revisar documentacao;
- rodar testes criticos;
- validar telas que nao dependem do MT5 real.

Para operar com MT5, candles ao vivo, posicoes abertas, visual no grafico e robo
demo, continue usando o app local:

```text
http://localhost:8530
```

## Validacao critica na nuvem

```bash
python scripts/run_critical_ci.py
```
