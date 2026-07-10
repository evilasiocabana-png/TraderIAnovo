# MISSÃO — AUDITORIA ARQUITETURAL PARA MODELO ALPHA + BETA

## Contexto

O TraderIA deve evoluir para representar cada plano operacional como a combinação entre:

- **Alpha**: lógica de entrada;
- **Beta**: lógica de saída.

Conceito desejado:

```text
Plano operacional = Alpha de entrada + Beta de saída
```

O Beta deve fazer parte da identidade do plano desde sua criação, embora só atue após a entrada da posição.

Exemplo conceitual:

```text
Alpha
Momentum + Volatilidade

+

Beta
Defesa por perda de força no M1

=

Plano Alpha-Beta
```

Neste momento, **não implementar mudanças no código**.

A missão é exclusivamente investigar o estado atual da arquitetura e identificar a forma mais segura de introduzir o conceito Alpha + Beta sem impacto indevido no funcionamento existente.

---

## Objetivo da auditoria

Responder, com evidências do código atual:

1. onde o plano operacional é criado;
2. como a estratégia de entrada é representada;
3. como a estratégia de saída é representada;
4. onde stop, alvo, break-even, trailing e fechamento antecipado são definidos;
5. como o plano chega ao robô e ao Position Manager;
6. qual é o menor ponto de inserção para adicionar `alpha_id` e `beta_id`;
7. como preservar integralmente o comportamento atual como compatibilidade inicial.

---

## Perguntas obrigatórias

### 1. Onde o plano operacional é criado?

Identificar:

- arquivo;
- classe;
- função ou método;
- serviço responsável;
- estrutura de dados utilizada.

Listar todos os campos que compõem o plano atualmente, especialmente:

- setup;
- direção;
- timeframe;
- entrada;
- stop inicial;
- alvo;
- relação risco-retorno;
- tipo de saída;
- demais metadados.

---

### 2. O plano já possui identificador de estratégia?

Verificar se existe hoje algum campo equivalente a:

```text
setup_id
strategy_id
alpha_id
exit_strategy_id
beta_id
```

Informar:

- nome exato do campo;
- onde é preenchido;
- onde é persistido;
- onde é consumido.

---

### 3. Como o Position Manager recebe o plano?

Determinar se o Position Manager recebe:

- o objeto completo do plano;
- apenas ticket ou identificador da posição;
- stop e alvo;
- snapshot operacional;
- configuração separada;
- ou se recalcula dados por conta própria.

Mapear o fluxo completo:

```text
Lab
→ plano
→ robô
→ ordem MT5
→ posição aberta
→ Position Manager
```

---

### 4. Como as saídas funcionam hoje?

Localizar exatamente onde são definidos e executados:

- Take Profit;
- Stop Loss inicial;
- break-even;
- ATR trailing;
- trailing fixo;
- fechamento antecipado;
- fechamento por perda de força;
- encerramento manual ou de segurança.

Para cada mecanismo, informar:

- arquivo;
- classe/função;
- gatilho;
- dados utilizados;
- se nasce junto com o plano;
- se é recalculado durante a posição;
- se está acoplado ao Lab, robô, execução ou Position Manager.

---

### 5. Existe abstração formal de estratégia de saída?

Verificar se existe algo equivalente a:

```text
ExitStrategy
ExitPolicy
ExitMode
StopManager
PositionManager
TradeManager
```

Responder:

- existe uma interface ou contrato formal?
- existem implementações separadas?
- a lógica está centralizada ou espalhada?
- os modos de saída são selecionados por enum, string, configuração ou condicionais?

---

### 6. O Lab escolhe o quê atualmente?

Confirmar, diretamente pelo código, se o Lab escolhe:

- setup de entrada;
- timeframe;
- direção;
- parâmetros;
- preço de entrada;
- stop inicial;
- alvo;
- relação risco-retorno;
- tipo de saída;
- break-even;
- trailing;
- qualquer outra regra de gestão.

Não responder por suposição. Citar os pontos exatos do código.

---

### 7. É possível adicionar metadados sem quebrar compatibilidade?

Avaliar a inclusão futura de campos opcionais como:

```text
alpha_id
alpha_version
beta_id
beta_version
```

Investigar impacto em:

- dataclasses;
- modelos Pydantic;
- JSON;
- banco de dados;
- snapshots;
- histórico;
- relatórios;
- testes;
- interface Streamlit;
- execução MT5;
- serialização e desserialização;
- compatibilidade com dados antigos.

---

### 8. Qual seria o Beta de compatibilidade?

Identificar como o comportamento atual poderia ser preservado através de um Beta inicial, por exemplo:

```text
beta_id = LEGACY_CURRENT_EXIT
```

Esse Beta deve representar exatamente o funcionamento atual, sem mudar resultados ou regras.

Informar quais comportamentos precisariam ser agrupados dentro desse Beta de compatibilidade.

---

### 9. Onde encaixar o futuro Beta de leitura dinâmica do M1?

Sem implementar, indicar o melhor ponto arquitetural para um futuro Beta que monitore, independentemente do timeframe de entrada:

- EMA 14 do M1;
- momentum do M1;
- volatilidade/ATR 14 do M1;
- estrutura e amplitude dos candles;
- perda persistente de força.

Premissa obrigatória:

```text
Virada da EMA 14 do M1 não fecha a posição automaticamente.
```

Ela deve atuar apenas como sensor ou alerta para investigação, exigindo confirmação por outras evidências.

---

## Restrições

Durante esta missão:

- não alterar código de produção;
- não refatorar módulos;
- não criar Alpha ou Beta;
- não mudar o Lab;
- não mudar o Position Manager;
- não alterar banco de dados;
- não alterar comportamento operacional;
- não modificar testes existentes;
- não executar migrações;
- não propor reescrita ampla da arquitetura.

A missão é somente de leitura, rastreamento e documentação.

---

## Entregável obrigatório

Criar um relatório com:

```text
codex/completed/ARCHITECTURE_AUDIT_ALPHA_BETA_REPORT.md
```

O relatório deve conter:

1. resumo executivo;
2. fluxo atual real;
3. tabela ou lista de arquivos envolvidos;
4. responsabilidades atuais de cada módulo;
5. localização das regras de entrada;
6. localização das regras de saída;
7. acoplamentos encontrados;
8. riscos de compatibilidade;
9. menor ponto de inserção possível;
10. proposta de migração incremental;
11. definição do Beta de compatibilidade;
12. pontos que ainda precisam de decisão humana.

---

## Formato obrigatório das evidências

Cada afirmação relevante deve apontar:

```text
arquivo
classe ou função
responsabilidade observada
```

Sempre que possível, incluir trechos curtos ou referências de linha.

---

## Critério de conclusão

A missão será considerada concluída somente quando for possível responder com segurança:

> Como introduzir `Alpha + Beta` no plano operacional preservando integralmente o comportamento atual e evitando uma refatoração ampla?

Não implementar a solução. Apenas produzir o diagnóstico arquitetural necessário para a próxima decisão.
