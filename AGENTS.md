# AGENTS.md

# TraderIA Novo — Guia Oficial para Agentes de Desenvolvimento

**Versão:** 1.0

**Status:** Ativo

---

# Objetivo

Este documento define como qualquer agente de IA deve trabalhar no projeto TraderIA Novo.

Seu propósito é garantir continuidade, rastreabilidade e consistência entre diferentes agentes (Codex, ChatGPT, Claude ou futuros agentes), independentemente do histórico da conversa.

Este documento é obrigatório.

Todo agente deve lê-lo antes de executar qualquer tarefa.

---

# Fonte da Verdade

A fonte oficial do projeto é composta por:

```text
governance/PROJECT_STATE.md
governance/NEXT_MISSION.md
governance/PROGRAM_STATUS.md
governance/ACCEPTANCE_CRITERIA.md
docs/ARCHITECTURE.md
```

O contexto da conversa nunca substitui esses documentos.

---

# Ordem Obrigatória de Leitura

Antes de iniciar qualquer missão, leia exatamente nesta ordem:

1. PROJECT_STATE.md
2. NEXT_MISSION.md
3. PROGRAM_STATUS.md
4. ACCEPTANCE_CRITERIA.md
5. ARCHITECTURE.md
6. EXECUTION_LOG.md

Somente após essa leitura o desenvolvimento pode começar.

---

# Resultado do Ultimo Inbox

Quando o pedido for apenas para relatar o que o inbox executou, o agente deve
ler primeiro:

```text
LATEST_INBOX_RESULT.md
```

Esse arquivo e o ponteiro oficial do resultado mais recente. Nao usar
`codex/inbox/` para resumir resultado executado, porque `codex/inbox/` contem
apenas missoes pendentes. Missoes concluidas ficam em:

```text
codex/completed/
```

Se houver conflito entre uma busca, a memoria da conversa e
`LATEST_INBOX_RESULT.md`, prevalece `LATEST_INBOX_RESULT.md`.

---

# Filosofia do Projeto

O TraderIA Novo evolui por pequenas missões.

Cada alteração deve ser:

* pequena;
* isolada;
* testável;
* reversível;
* documentada;
* rastreável.

Não realizar grandes refatorações sem missão explícita.

---

# Fluxo Oficial

```text
PROJECT_STATE
        ↓
NEXT_MISSION
        ↓
Codex executa
        ↓
Validação
        ↓
EXECUTION_LOG
        ↓
PROGRAM_STATUS
        ↓
PROJECT_STATE
        ↓
Commit
        ↓
Push
```

---

# Regras Gerais

Sempre:

* preservar funcionamento do projeto;
* produzir alterações pequenas;
* atualizar documentação quando necessário;
* manter compatibilidade com a arquitetura existente;
* registrar execução.

Nunca:

* alterar funcionalidades fora da missão;
* criar arquitetura paralela;
* remover funcionalidades existentes sem autorização;
* modificar runtime local.

---

# Runtime Local

O runtime local pertence ao usuário.

Nunca deve ser versionado.

Inclui:

```text
.traderia/
```

Contendo:

* snapshots;
* SQLite;
* logs;
* cache;
* JSONL;
* arquivos temporários.

Esses arquivos permanecem fora do Git.

---

# GitHub

GitHub armazena apenas:

* código-fonte;
* documentação;
* governança;
* testes;
* contratos.

Nunca armazenar artefatos locais pesados.

---

# Execução das Missões

Cada missão deve seguir exatamente o seguinte fluxo:

1. Ler a missão.
2. Validar dependências.
3. Executar somente o escopo definido.
4. Rodar validações.
5. Atualizar documentação.
6. Registrar execução.
7. Gerar commit.
8. Fazer push.

---

# Critérios de Qualidade

Toda alteração deve:

* compilar;
* preservar o funcionamento da aplicação;
* não degradar desempenho;
* não introduzir dependências desnecessárias;
* manter compatibilidade com o estado atual do projeto.

---

# Critérios de Segurança

É proibido:

* executar operações reais de mercado;
* enviar ordens financeiras;
* modificar credenciais;
* armazenar segredos no repositório;
* alterar configurações locais do usuário sem autorização.

---

# Fluxo das Missões

Cada missão percorre:

```text
codex/inbox
        ↓
codex/processing
        ↓
codex/completed
```

Se houver falha:

```text
codex/failed
```

Cada missão deve possuir:

* identificador;
* objetivo;
* arquivos envolvidos;
* critérios de aceite;
* resultado esperado;
* data;
* executor.

---

# Atualizações Obrigatórias

Ao concluir uma missão atualizar:

* PROJECT_STATE.md
* PROGRAM_STATUS.md
* NEXT_MISSION.md
* EXECUTION_LOG.md

Quando aplicável:

* ROADMAP.md
* BACKLOG.md
* CHANGELOG.md

---

# Commits

Os commits devem ser:

* pequenos;
* descritivos;
* relacionados a apenas uma missão.

Exemplo:

```text
feat(governance): implement PROJECT_STATE

fix(mt5): remove blocking refresh

docs: update execution log
```

---

# Pull Requests

Quando utilizados, devem conter:

* objetivo;
* resumo das alterações;
* arquivos modificados;
* validações executadas;
* riscos conhecidos.

---

# Critérios de Aceite

Uma missão somente pode ser considerada concluída quando:

* implementação finalizada;
* validações executadas;
* documentação atualizada;
* estado do projeto atualizado;
* commit realizado;
* nenhum erro crítico restante.

---

# Princípios

1. Preservar estabilidade.
2. Evoluir incrementalmente.
3. Documentar tudo.
4. Automatizar sempre que possível.
5. Nunca depender do contexto do chat.
6. O repositório deve carregar seu próprio estado.
7. Toda decisão relevante deve ser rastreável.
8. O código deve permanecer legível.
9. Mudanças devem ser reversíveis.
10. Governança é parte do produto.

---

# Missão do Agente

O objetivo de todo agente é manter o TraderIA Novo saudável, rastreável e evoluindo continuamente, garantindo que qualquer outro agente possa assumir o desenvolvimento apenas lendo a documentação do repositório.
