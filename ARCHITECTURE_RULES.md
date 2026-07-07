# Regras de Arquitetura - TraderIA_WDO

## Regra 1 - Estrategias nao executam ordens
Estrategias apenas analisam o mercado e retornam sinais:
BUY, SELL ou WAIT.
Nenhuma estrategia pode abrir, fechar ou modificar ordens.

## Regra 2 - Market DNA nao opera
O Market DNA apenas classifica o contexto de mercado.
Ele nao pode gerar ordem diretamente.

## Regra 3 - IA nao executa ordens
Qualquer modulo de IA so pode alterar:
- score
- confidence
- risk_multiplier

IA nunca pode enviar ordem.

## Regra 4 - Dominio puro
A pasta `domain/` nao pode depender de:
- banco de dados
- dashboard
- Streamlit
- corretora
- API externa
- arquivos CSV

## Regra 5 - Execucao centralizada
Apenas modulos de execucao, broker simulado ou order_manager podem criar ordens
operacionais.

## Regra 6 - Quatro modos obrigatorios
Toda estrategia deve ser compativel com:
- Backtest
- Simulacao
- Replay
- Tempo real

## Regra 7 - Seguranca primeiro
Antes de qualquer operacao real, o sistema deve passar por:
- backtest
- paper trading
- limite de perda diaria
- limite de operacoes
- logs completos

## Regra 8 - VALIDACAO FUNCIONAL OBRIGATORIA
Nenhuma sprint pode ser aprovada apenas porque o codigo compila ou os testes
automatizados passam. A aplicacao funcionando possui prioridade superior ao
simples fato de todos os testes estarem verdes.

## Regra 8.1 - VALIDAÇÃO POR RISCO
A validacao funcional deve ser proporcional ao risco real da missao.

BAIXO RISCO:
- documentacao
- testes isolados
- refatoracao interna sem mudanca de API pública
- mudancas que nao afetam Dashboard, Replay, Research Lab,
  `MarketDataProvider`, `HistoricalDataProvider`, `EventBus` ou contratos

Validacao obrigatoria para BAIXO RISCO:
- `python app.py`
- `python -m unittest discover -s tests`

ALTO RISCO:
- alteracao em Dashboard
- alteracao em `DashboardService`
- alteracao em `ReplayService`
- alteracao em `ResearchLabService`
- alteracao em `MarketDataProvider`
- alteracao em `HistoricalDataProvider`
- alteracao em registry/factory de providers
- alteracao em contratos publicos
- alteracao em `st.session_state`
- criacao, remocao ou mudanca de metodo publico
- alteracao em fluxos de Replay, Research Lab ou Dataset Management

Validacao obrigatoria para ALTO RISCO:
- `python app.py`
- `python -m unittest discover -s tests`
- `python -m streamlit run dashboard_app.py`
- validacao dos fluxos principais impactados

Se houver dúvida sobre o risco da missão, classificar como ALTO RISCO.

Validacao minima obrigatoria:
- `python app.py` sem erros
- `python -m unittest discover -s tests` com sucesso
- `python -m streamlit run dashboard_app.py` iniciando corretamente quando a
  entrega afetar dashboard ou servicos consumidos pelo dashboard
- fluxos principais preservados: Home, Replay, Research Lab, Estrategias,
  Eventos e Sistema
- logs sem novas excecoes

Niveis oficiais de validacao:
- Unit Tests
- Integration Tests
- Streamlit AppTest
- End-to-End Validation

## Regra 9 - CORRECAO EM CASCATA
Se uma correcao revelar novos erros, a investigacao deve continuar ate que a
aplicacao esteja operacional. Nao e permitido encerrar uma missao apos remover
apenas o primeiro erro quando novos erros impedem o funcionamento real do app.
Em missoes de ALTO RISCO, erro em cascata bloqueia encerramento ate o app ficar
operacional.

## Regra 10 - PROIBICAO DE WORKAROUNDS
E proibido:
- ocultar excecoes
- silenciar erros
- remover funcionalidades apenas para fazer testes passarem
- mascarar sintomas sem corrigir causa raiz
- criar solucao temporaria sem justificativa arquitetural explicita

Toda correcao deve atacar a causa raiz e preservar Clean Architecture, SOLID,
Event Driven, Ports & Adapters e contratos do dominio.

## Regra 11 - Compatibilidade da interface
Alteracoes em servicos consumidos pelo dashboard devem validar:
- metodos publicos e assinaturas
- inicializacao do dashboard
- funcionamento do `st.session_state`
- inexistencia de `AttributeError`
- preservacao da regra de que `dashboard_app.py` acessa apenas
  `DashboardService`

O dashboard nao pode acessar provider, catalogo, persistencia, CSV, Path,
pandas, diretorios ou arquivos diretamente.

## Regra 12 - ANALISE DE IMPACTO OBRIGATORIA
Toda mudanca em API publica, contrato, interface, servico de aplicacao, metodo
publico ou comportamento compartilhado exige analise de impacto antes da
entrega.

Componentes publicos incluem:
- `DashboardService`
- `ReplayService`
- `ResearchLabService`
- `ConfigurationService`
- `MarketDataProvider`
- `HistoricalDataProvider`
- `EventBus`
- `DecisionPipeline`
- Domain Contracts
- DTOs
- interfaces
- protocols
- providers

Antes de concluir a missao, o Codex deve:
- identificar todos os consumidores conhecidos do componente alterado
- verificar se todos continuam compativeis
- corrigir regressoes encontradas
- atualizar chamadas afetadas quando necessario
- executar nova validacao funcional completa

E proibido encerrar uma missao com consumidor conhecido quebrado.

Regressoes que devem ser eliminadas antes da entrega:
- `AttributeError`
- `ImportError`
- `ModuleNotFoundError`
- `TypeError` por mudanca de assinatura
- metodo publico removido
- contrato incompativel
- quebra de Dashboard
- quebra de Replay
- quebra de Research Lab
- quebra de integracao entre modulos

Sempre que possivel, preservar retrocompatibilidade. Quando nao for possivel,
todos os consumidores conhecidos da API devem ser atualizados antes da
conclusao.

## Regra 13 - Data Source via adapters
Fontes historicas devem entrar exclusivamente por adapters/providers atras da
porta `HistoricalDataSource`.

Regras obrigatorias:
- CSV so pode ser lido pelo adapter CSV.
- Parquet so pode ser lido pelo adapter Parquet.
- DuckDB so pode ser lido pelo adapter DuckDB.
- Conexoes DuckDB, SQL e configuracao de tabela devem permanecer isolados no
  adapter DuckDB ou em testes especificos do adapter.
- Replay nunca pode acessar CSV, Parquet, DuckDB, `pandas`, `Path`, `open()`,
  diretorios ou arquivos para carregar dados historicos.
- Research Lab nunca pode acessar CSV, Parquet, DuckDB, `pandas`, `Path`,
  `open()`, diretorios ou arquivos para carregar dados historicos.
- Dashboard nunca pode acessar provider, catalogo, registry, persistencia,
  adapter, CSV, Parquet, DuckDB, `Path`, `pandas`, diretorios ou arquivos
  diretamente.
- Dashboard deve consumir Data Source apenas por `DashboardService`.
- Toda nova fonte historica, como PostgreSQL, MT5, Nelogica ou B3, deve ser
  implementada como novo adapter/provider sem alterar Replay, Research Lab,
  Alpha001, Dashboard ou contratos do dominio.
- `HistoricalDataProvider` nao deve conhecer detalhes da origem fisica.

## Regra 14 - MANIFEST como fonte oficial do estado
O arquivo `MANIFEST.md` e a unica fonte oficial para estado operacional do
projeto.

Toda Sprint CTO somente pode ser considerada concluida apos:
- implementacao aprovada;
- testes executados;
- atualizacao obrigatoria do `MANIFEST.md`;
- atualizacao do `CHANGELOG`, quando aplicavel.

Sem atualizacao do `MANIFEST.md`, a Sprint permanece em andamento.

O README nao deve registrar andamento operacional, ultima sprint, proxima
missao, status de Alpha, roadmap operacional ou historico de conclusao. Esses
dados pertencem exclusivamente ao `MANIFEST.md`.
