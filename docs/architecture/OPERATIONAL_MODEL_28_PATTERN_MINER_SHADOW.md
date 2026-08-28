# Modelo 28 - Pattern Miner Adaptativo Demo

## Identidade

- Identificador persistido: `MODELO_28_PATTERN_MINER_SHADOW`
- Nome curto: `M28`
- Origem: `REPLAY_PATTERN_MINER`
- Contrato: `M28_PATTERN_BRIDGE_V2`
- Alpha: `ALPHA028_PATTERN_MINER_PROMOTED`
- Beta: `BETA028_REPLAY_DERIVED_FIXED_RISK`
- Execucao: `DEMO_ADAPTIVE`
- Ativos e timeframe: os `19` mercados canonicos, todos em `M5`
- Volume: `0.11`

O sufixo `SHADOW` permanece no identificador apenas para compatibilidade com os
registros locais criados na fase de validacao. O M28 agora e um modelo
operacional selecionavel, autorizado exclusivamente na conta Demo.

## Objetivo

O M28 acompanha os candles fechados dos caches compartilhados de cada mercado,
executa maquinas de estado isoladas por `ativo/timeframe` e escolhe o contrato
validado mais forte quando uma sequencia causal termina. A ocorrencia escolhida
e materializada como Trade Plan do mesmo ativo e segue o pipeline Demo.

## Fluxo oficial

```text
historicoATIVO (19 bases independentes)
  -> Replay / Event Engine
  -> Pattern Miner, validacao e OOS
  -> promocao versionada apos comando explicito do usuario
  -> OperationalPatternSpec habilitada
  -> cache compartilhado ATIVO/M5 em candle fechado
  -> LivePatternTracker
  -> SignalCandidate
  -> seletor adaptativo
  -> Trade Plan M28 com entrada, SL, TP e lote 0.11
  -> MT5DemoRobotService
  -> DemoExecutionService
  -> provider MT5 Demo
```

Nao existe chamada direta do Pattern Miner ao provider. O motor reconhece e
decide; o robo valida; o `DemoExecutionService` executa. A conta Real continua
bloqueada pelo provider.

## Regras operacionais

- Entrada: preco de fechamento que conclui a sequencia validada.
- Stop: referencia adversa congelada pela geometria causal do Replay.
- Target: referencia favoravel de `1 ATR` ou `2 ATR`, definida na promocao.
- Ordem: mercado, somente apos candle M5 fechado.
- Volume: `0.11` lote.
- Escopo: 19 ativos; nenhum contrato de um ativo pode consumir candle de outro.
- Expiracao: a selecao vence ao ultrapassar a janela causal do contrato.
- Ausencia de padrao: `WAIT`, sem inventar direcao ou geometria.
- Geometria BUY obrigatoria: `SL < entrada < TP`.
- Geometria SELL obrigatoria: `TP < entrada < SL`.

## Idempotencia

Cada conclusao recebe um `pattern_occurrence_id`. O M28 grava esse valor em
`setup_id` e `route_key`; junto com candle, modelo e versao do plano, ele forma
a identidade operacional. A mesma ocorrencia nao pode gerar duas ordens.

## Chaveamento

O M28 aparece como caixa `M28` no Chaveamento operacional. Somente uma selecao
persistida que contenha M28 permite novas ordens desse modelo. Marcar outros
modelos nao transforma o M28 em fonte da cesta M23: as duas rotas permanecem
independentes.

## Persistencia e auditoria

Os contratos versionados continuam no registro compartilhado:

`.traderia/research/historicoXAU/model28_operational_patterns.json`

Cada dataset preserva seu proprio cache e `pattern_miner_summary.json`. Cada
sinal preserva ativo, Pattern ID, versao, ocorrencia, candle de conclusao,
direcao, entrada, stop, target, score, Validation, OOS e contexto de mercado.
O snapshot efetivamente enviado grava ainda o lote e a identidade do plano.

## Guardrails

- promocao exige comando explicito; o lote sequencial nao roda no ciclo leve;
- somente contratos validados e habilitados participam da leitura ao vivo;
- o M28 nao recalcula o Lab pesado no ciclo de 10 segundos;
- somente candles fechados e cronologicamente novos sao consumidos;
- os 19 replays Maximum rodam um por vez e liberam RAM entre ativos;
- o runtime so atualiza mercados M28 quando M28 estiver selecionado;
- o filtro de regime legado nao e reaplicado sobre a decisao causal do M28;
- toda ordem passa pelos gates temporal, plano, duplicidade e conta Demo;
- conta Real permanece proibida;
- falha ou ausencia de dados resulta em `WAIT`.

## Rollback

Desmarcar M28 interrompe novas entradas sem alterar posicoes anteriores. O
identificador persistido e o registro de padroes foram preservados para que o
rollback para Shadow nao exija migracao dos arquivos de pesquisa.
