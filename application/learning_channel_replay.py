"""Bounded read-only tick replay; missing evidence never becomes simulated profit."""
import json
import subprocess
import sys
from core.mt5_external_process_gate import mt5_external_process_slot
from core.mt5_process_probe import resolve_mt5_terminal_path


SCRIPT = r'''
import json,sys
from datetime import datetime,timezone
import MetaTrader5 as m
r=json.loads(sys.argv[1])
out={'state':'WAITING_MARKET_DATA'}
if m.initialize(path=r['path']):
 try:
  a=m.account_info()
  if a is None or a.trade_mode != m.ACCOUNT_TRADE_MODE_DEMO or str(a.login)+'@'+a.server != r['account']:
   out={'state':'ACCOUNT_UNCONFIRMED'}
  else:
   ticks=m.copy_ticks_from(r['symbol'],datetime.fromtimestamp(r['opened'],timezone.utc),100000,m.COPY_TICKS_ALL)
   if ticks is not None and len(ticks):
    valid=[t for t in ticks if t['time_msc']>=r['opened']*1000 and t['bid']>0 and t['ask']>0]
    if valid and valid[0]['time_msc']/1000-r['opened']<=5:
     buy=r['original_side']=='SELL'
     entry=float(valid[0]['ask'] if buy else valid[0]['bid'])
     target=float(r['original_stop'])
     distance=(target-entry) if buy else (entry-target)
     if distance>0:
      stop=entry-distance if buy else entry+distance
      out={'state':'WAITING_EXIT','entry':entry,'stop':stop,'target':target}
      for t in valid:
       price=float(t['bid'] if buy else t['ask'])
       if (buy and (price<=stop or price>=target)) or (not buy and (price>=stop or price<=target)):
        gross=m.order_calc_profit(m.ORDER_TYPE_BUY if buy else m.ORDER_TYPE_SELL,r['symbol'],r['volume'],entry,price)
        close_time=float(t['time_msc'])/1000
        if gross is not None and datetime.fromtimestamp(close_time,timezone.utc).date()==datetime.fromtimestamp(r['opened'],timezone.utc).date():
         out.update(state='RESOLVED_ESTIMATED_COSTS',gross=gross,net=gross+r['reference_fees'],exit=price,closed_at=close_time,cost_method='REFERENCE_NATIVE_COMMISSION_AND_FEES_INTRADAY_NO_SWAP')
        else:
         out.update(state='WAITING_COSTS',gross=gross,closed_at=close_time)
        break
      if out['state']=='WAITING_EXIT' and len(ticks)>=100000:
       out['state']='TICK_WINDOW_LIMIT'
     else:
      out={'state':'INVALID_MIRROR_GEOMETRY'}
    else:
     out={'state':'ENTRY_QUOTE_GAP'}
 finally:
  m.shutdown()
print(json.dumps(out))
'''


def replay(request):
    path = resolve_mt5_terminal_path()
    if not path:
        return {'state':'WAITING_TERMINAL'}
    with mt5_external_process_slot(timeout=0.01) as acquired:
        if not acquired:
            return {'state':'WAITING_READ_GATE'}
        try:
            process = subprocess.run([sys.executable,'-c',SCRIPT,json.dumps({**request,'path':path})],
                capture_output=True,text=True,timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            return json.loads(process.stdout.strip().splitlines()[-1])
        except (OSError,ValueError,IndexError,subprocess.TimeoutExpired):
            return {'state':'WAITING_MARKET_DATA'}
