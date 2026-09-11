"""Separate, explicitly configured M23 additional context candidates.

This module only reads a catalog and matches supplied context. It never learns,
writes files, sends orders, or modifies the original M23 rule report. The caller
must invoke it only for the M23 route, after context synchronization validation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping

DEFAULT_CATALOG_PATH = Path('config/m23_additional_filters.json')
CATALOG_SCHEMA = 'm23-additional-context-candidates-v1'
CONTEXT_FIELDS = (
    'trend_alignment', 'structure_alignment', 'rsi_zone', 'adx_zone',
    'atr_regime', 'session', 'latest_event',
)
SOURCE_MODEL = 'MODELO_7_LAB_XAU_BTC'
SYMBOL = 'XAUUSD'
DIRECTION = 'BUY'
VALID_MODES = frozenset({'OFF', 'OBSERVE', 'BLOCK'})


@dataclass(frozen=True)
class AdditionalFilterRule:
    rule_id: str
    label: str
    description: str
    source_model: str
    symbol: str
    direction: str
    context_snapshot: Mapping[str, str]
    evidence: Mapping[str, Any] = field(default_factory=dict)
    validated: bool = False


@dataclass(frozen=True)
class AdditionalFilterCatalog:
    mode: str = 'OBSERVE'
    rules: tuple[AdditionalFilterRule, ...] = ()
    status: str = 'MISSING'
    reason: str = 'Catálogo de filtros adicionais indisponível.'
    generated_at: str = ''
    study: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = CATALOG_SCHEMA


@dataclass(frozen=True)
class AdditionalFilterDecision:
    mode: str
    matched_ids: tuple[str, ...] = ()
    matched_labels: tuple[str, ...] = ()
    blocks_execution: bool = False
    status: str = 'NO_MATCH'
    reason: str = 'Nenhum cenário adicional correspondente.'


def _full_context(value: object) -> bool:
    return isinstance(value, Mapping) and all(
        isinstance(value.get(key), str) and bool(value[key].strip())
        for key in CONTEXT_FIELDS
    )


def load_catalog(path: str | Path = DEFAULT_CATALOG_PATH) -> AdditionalFilterCatalog:
    """Read configuration without writing or changing original filter rules.

    Missing or malformed configuration disables matching. An unknown mode never
    silently becomes BLOCK. Matching is deliberately limited to M7 gold buys.
    """
    try:
        payload = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except FileNotFoundError:
        return AdditionalFilterCatalog()
    except (OSError, UnicodeError, ValueError):
        return AdditionalFilterCatalog(status='INVALID', reason='Catálogo adicional não pôde ser lido.')
    try:
        if not isinstance(payload, dict) or payload.get('schema_version') != CATALOG_SCHEMA:
            raise ValueError('schema')
        mode = payload.get('mode', 'OBSERVE')
        if mode not in VALID_MODES:
            raise ValueError('mode')
        definitions = payload.get('rules', [])
        if not isinstance(definitions, list):
            raise ValueError('rules')
        identifiers: set[str] = set()
        rules = []
        for definition in definitions:
            if not isinstance(definition, dict):
                raise ValueError('rule')
            identifier = definition.get('rule_id')
            label = definition.get('label')
            context = definition.get('context_snapshot')
            if not isinstance(identifier, str) or not identifier.strip() or identifier in identifiers:
                raise ValueError('identifier')
            if not isinstance(label, str) or not label.strip():
                raise ValueError('label')
            if not _full_context(context) or set(context) != set(CONTEXT_FIELDS):
                raise ValueError('context')
            if (definition.get('source_model'), definition.get('symbol'), definition.get('direction')) != (SOURCE_MODEL, SYMBOL, DIRECTION):
                raise ValueError('scope')
            evidence = definition.get('evidence', {})
            if not isinstance(evidence, dict) or definition.get('validated', False) is not False:
                raise ValueError('evidence')
            identifiers.add(identifier)
            rules.append(AdditionalFilterRule(
                rule_id=identifier, label=label,
                description=str(definition.get('description', '')),
                source_model=SOURCE_MODEL, symbol=SYMBOL, direction=DIRECTION,
                context_snapshot={key: context[key] for key in CONTEXT_FIELDS},
                evidence=dict(evidence), validated=False,
            ))
        study = payload.get('study', {})
        if not isinstance(study, dict):
            raise ValueError('study')
        return AdditionalFilterCatalog(
            mode=mode, rules=tuple(rules), status='READY',
            reason='Candidatos adicionais separados do filtro original; evidência exploratória.',
            generated_at=str(payload.get('generated_at', '')), study=dict(study),
        )
    except (KeyError, TypeError, ValueError):
        return AdditionalFilterCatalog(status='INVALID', reason='Configuração de filtros adicionais inválida; nenhum bloqueio adicional.')


load_report = load_catalog


def evaluate_additional_filters(
    *, catalog: AdditionalFilterCatalog, source_model: str, symbol: str,
    direction: str, context_snapshot: Mapping[str, str] | None,
    context_status: str = 'UNVERIFIED',
) -> AdditionalFilterDecision:
    """Require exact seven-field equality in valid context, without broadening.

    OBSERVE returns matches with blocks_execution=False. Only an explicitly
    configured BLOCK mode can return True. Missing context is not evidence that
    a candidate matches; the M23 synchronization gate remains the caller's job.
    """
    mode = catalog.mode if catalog.mode in VALID_MODES else 'OBSERVE'
    if catalog.status != 'READY' or catalog.mode not in VALID_MODES:
        return AdditionalFilterDecision(mode=mode, status='INVALID_CATALOG', reason=catalog.reason)
    if mode == 'OFF':
        return AdditionalFilterDecision(mode=mode, status='DISABLED', reason='Filtros adicionais desativados.')
    if (str(source_model).upper(), str(symbol).upper(), str(direction).upper()) != (SOURCE_MODEL, SYMBOL, DIRECTION):
        return AdditionalFilterDecision(mode=mode, status='OUT_OF_SCOPE', reason='Candidatos exclusivos para compras do M7 no ouro dentro do M23.')
    if context_status != 'VALID' or not _full_context(context_snapshot):
        return AdditionalFilterDecision(mode=mode, status='INVALID_CONTEXT', reason='Correspondência adicional exige contexto completo e sincronizado.')
    matches = tuple(rule for rule in catalog.rules if
        (rule.source_model, rule.symbol, rule.direction) == (SOURCE_MODEL, SYMBOL, DIRECTION)
        and _full_context(rule.context_snapshot)
        and all(context_snapshot[key] == rule.context_snapshot[key] for key in CONTEXT_FIELDS)
    )
    if not matches:
        return AdditionalFilterDecision(mode=mode)
    blocks = mode == 'BLOCK'
    return AdditionalFilterDecision(
        mode=mode, matched_ids=tuple(rule.rule_id for rule in matches),
        matched_labels=tuple(rule.label for rule in matches),
        blocks_execution=blocks, status='MATCHED',
        reason=('Bloqueio adicional por correspondência exata configurado explicitamente.' if blocks else
                'Cenário adicional reconhecido em observação; entrada não bloqueada por este catálogo.'),
    )
