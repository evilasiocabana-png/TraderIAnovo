"""Small read-only reconciliation, isolated from the trading MT5 session."""

import json
import subprocess
import sys

from core.mt5_external_process_gate import mt5_external_process_slot
from core.mt5_process_probe import resolve_mt5_terminal_path


SCRIPT = r'''
import json, sys
import MetaTrader5 as mt5
request = json.loads(sys.argv[1])
if not mt5.initialize(path=request['path']):
    print(json.dumps({'ok':False,'reason':'initialize_failed'})); sys.exit(0)
try:
    account = mt5.account_info()
    if account is None or int(account.trade_mode) != int(mt5.ACCOUNT_TRADE_MODE_DEMO):
        print(json.dumps({'ok':False,'reason':'demo_account_not_confirmed'})); sys.exit(0)
    results = []
    for item in request['items']:
        if item.get('account') != str(account.login)+'@'+str(account.server):
            results.append({'id':item['id'],'ok':False,'reason':'account_mismatch'})
            continue
        ticket = int(item['ticket'])
        orders = mt5.history_orders_get(ticket=ticket)
        positions = mt5.positions_get(ticket=ticket)
        position_id = int(orders[0].position_id) if orders else 0
        if not position_id and positions:
            position_id = int(positions[0].identifier)
        if not position_id:
            cancelled = bool(orders and int(orders[0].state) in (int(mt5.ORDER_STATE_CANCELED),int(mt5.ORDER_STATE_REJECTED),int(mt5.ORDER_STATE_EXPIRED)))
            results.append({'id':item['id'],'ok':False,'reason':'position_not_resolved','cancelled':cancelled})
            continue
        deals = mt5.history_deals_get(position=position_id)
        all_open = mt5.positions_get(symbol=orders[0].symbol if orders else positions[0].symbol)
        results.append({'id':item['id'],'ok':deals is not None and all_open is not None,
            'account':str(account.login)+'@'+str(account.server), 'position_id':position_id,
            'open': any(int(p.identifier)==position_id for p in (all_open or [])),
            'deals':[d._asdict() for d in (deals or [])]})
    print(json.dumps({'ok':True,'results':results},default=str))
finally:
    mt5.shutdown()
'''


def reconcile_batch(items: list[dict]) -> dict:
    if not items:
        return {"ok": True, "results": []}
    path = resolve_mt5_terminal_path()
    if not path:
        return {"ok": False, "reason": "demo_terminal_path_missing"}
    request = {"path": path, "items": items[:10]}
    # Never queue behind execution work: skip this optional read when the gate is busy.
    with mt5_external_process_slot(timeout=0.01) as acquired:
        if not acquired:
            return {"ok": False, "reason": "execution_read_gate_busy"}
        try:
            result = subprocess.run([sys.executable, "-c", SCRIPT, json.dumps(request)],
                                    capture_output=True, text=True, timeout=5,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return json.loads(result.stdout.strip().splitlines()[-1])
        except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
            return {"ok": False, "reason": "native_read_unavailable"}
