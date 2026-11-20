"""Canonical learning ownership, separate from the execution model."""
import re
from application.learning_store import encoded


def scope_identity(snapshot, account):
    p = snapshot.get('stop_management_parameters') or {}
    source = str(p.get('m23_m29_origin_source') or p.get('source_operational_model') or '')
    match = re.match(r'^(?:MODELO_|M)(\d+)(?:_|$)', source)
    setup = p.get('source_entry_setup') or snapshot.get('source_setup') or snapshot.get('setup_id') or snapshot.get('entry_setup') or snapshot.get('setup')
    symbol = snapshot.get('symbol')
    if not account or not match or not setup or setup == 'UNKNOWN' or not symbol:
        return ''
    return encoded(dict(account=account, source='M'+match[1], setup=setup,
                        symbol=symbol, timeframe=snapshot.get('timeframe') or 'UNKNOWN'))


def scope_tables(db):
    db.execute('CREATE TABLE IF NOT EXISTS learning_candidate_scopes (candidate TEXT PRIMARY KEY, scope TEXT NOT NULL)')


def active_key(scope):
    from application.learning_store import digest
    return 'm30_active_filter:' + digest(scope)
