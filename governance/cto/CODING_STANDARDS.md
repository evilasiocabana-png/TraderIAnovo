# Coding Standards

Padroes obrigatorios para implementacoes futuras.

## Type Hints

- Usar type hints em funcoes, metodos e contratos publicos.
- Evitar tipos genericos quando houver DTO ou contrato apropriado.

## Dataclasses

- Usar dataclasses para DTOs e estruturas de dados simples.
- Preferir objetos imutaveis quando representarem contratos.

## Docstrings

- Classes e metodos publicos devem explicar responsabilidade.
- Docstrings devem ser objetivas e tecnicas.

## Imports

- Imports devem respeitar as camadas arquiteturais.
- Dominio nao importa infraestrutura.
- UI nao importa adapters diretamente.

## Responsabilidade Unica

- Cada classe deve ter responsabilidade clara.
- Evitar misturar orquestracao, persistencia, regra de negocio e UI.

## Testabilidade

- Codigo deve ser testavel sem servicos externos.
- Dependencias externas devem ficar atras de portas/adapters.

## Acoplamento

- Reduzir acoplamento entre camadas.
- Preferir contratos explicitos a dicionarios livres.
- Evitar dependencias circulares.
