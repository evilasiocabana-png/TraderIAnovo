# MISSION_TIA-043 — Contrato canonico e protecao contra drift do M24

Status: completed

Data: 2026-08-19

Branch: `codex/multi-ea-trading-lab`

Commit funcional: `ad2716d`

## Objetivo

Auditar o setup vigente do M24, eliminar informacao antiga na interface e nos
documentos, corrigir identidade instavel de candle e criar protecoes para que
as alteracoes nao voltem a se perder ou divergir.

## Causas encontradas

- motor, tabela e documentos mantinham copias independentes da regra;
- a tabela ainda afirmava cruzamento obrigatorio do RSI, SL/trailing antigos e
  saida RSI50 somente para reentrada;
- documentos ativos misturavam micro-pivo 1+1 e topo/fundo principal 2+2;
- registros numpy/MT5 podiam expor `.data` como `memoryview`, persistido como
  se fosse horario do candle;
- historico e contrato vigente nao estavam identificados separadamente.

## Implementacao

- criado `Model24SetupContract` imutavel, versionado e com fingerprint SHA-256;
- constantes, avaliadores, Position Manager, Trade Plan e tabela publica
  consomem o mesmo contrato;
- novas gravacoes do plano e runtime carregam versao/fingerprint;
- estado legado com `<memory at 0x...>` e sanitizado conservadoramente;
- documentos ativos declaram marker exato e teste impede drift;
- log historico foi preservado e o status vigente passou a prevalecer de forma
  explicita;
- criado ponto local sanitizado em `.traderia/restore_points/20260819_121834`.

## Validacao

- 54 testes direcionados M24/RSI50/persistencia: aprovados;
- 180 testes de interface e auditoria, mais 41 subtestes: aprovados;
- gate critico oficial: 198 testes aprovados;
- `git diff --check`: aprovado;
- `scripts/architecture_audit.py`: `OK`;
- `scripts/architecture_health.py`: `CRITICO` somente pelo debito preexistente
  de UI desacoplada, com drift classificado como informativo;
- nenhuma ordem MT5 foi aberta, fechada, cancelada ou modificada.

## Contrato vigente

`M24_CONTRACT=M24_SETUP_V1_20260819; SHA256=4cf288896f842909a4ca160904aaef32577e3a027ecb7a786db9acb34a3d85b1`
