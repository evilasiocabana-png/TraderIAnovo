"""M28 context filter using the M23 block-only evidence contract."""
import json
import math
from functools import lru_cache
from pathlib import Path

from application.model23_pattern_filter import (
    M23PatternFilterDecision, context_from_record, _context_rule_value,
)

DEFAULT_POLICY = Path(__file__).resolve().parents[1] / 'config' / 'model28_realized_filter.json'


@lru_cache(maxsize=4)
def _read_policy(path, modified, size):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _matches(spec, contract):
    return (
        all(str(getattr(spec, k, '')) == str(contract[k]) for k in
            ('versioned_id', 'symbol', 'direction', 'contract_version'))
        and all(math.isclose(float(getattr(spec, k)),float(contract[k]),rel_tol=0,abs_tol=1e-9)
                for k in ('stop_atr','target_atr','max_holding_candles'))
    )


def evaluate_realized_pattern(spec, record=None, history=(), policy_path=DEFAULT_POLICY):
    """Only a matching negative contextual rule blocks. Missing evidence preserves the setup."""
    no_evidence=M23PatternFilterDecision(reason='M28 sem evidencia contextual suficiente; sinal original preservado.')
    if record is None or not getattr(record,'warmup_complete',False):
        return no_evidence
    try:
        path=Path(policy_path);stat=path.stat()
        policy=_read_policy(str(path.resolve()),stat.st_mtime_ns,stat.st_size)
        if policy.get('schema_version')!=2 or policy.get('mode')!='CONTEXT_BLOCK_ONLY':
            return no_evidence
        identities={key for key,contract in policy['contracts'].items() if _matches(spec,contract)}
        if not identities:return no_evidence
        # Never let a later record influence a previously produced signal.
        causal=tuple(item for item in history if item.timestamp<=record.timestamp)
        if not causal or causal[-1].timestamp!=record.timestamp:causal=(*causal,record)
        context=context_from_record(record,direction=spec.direction,history=causal,index=len(causal)-1)
        matching=[r for r in policy['rules'] if r['source_model'] in identities
                  and r['direction']==spec.direction
                  and r['decision'] in ('BLOCK','APPROVE')
                  and _context_rule_value(context,r['pattern_scope'])==r['pattern_value']]
        if not matching:return no_evidence
        blocks=[r for r in matching if r['decision']=='BLOCK']
        rule=max(blocks or matching,key=lambda r:(min(abs(r['validation_expectancy']),abs(r['oos_expectancy'])),r['samples']))
        return M23PatternFilterDecision(decision=rule['decision'],rule_id=rule['rule_id'],
            pattern_id=rule['pattern_id'],samples=rule['samples'],
            validation_expectancy=rule['validation_expectancy'],oos_expectancy=rule['oos_expectancy'],
            reason=f"M28 contextual {rule['decision']}: {rule['pattern_scope']}={rule['pattern_value']}; n={rule['samples']}.")
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return no_evidence


def allows_realized_pattern(spec, record=None, history=(), policy_path=DEFAULT_POLICY):
    return evaluate_realized_pattern(spec,record,history,policy_path).decision!='BLOCK'
