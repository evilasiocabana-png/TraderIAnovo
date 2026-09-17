"""Exploratory read-only admission study; never changes operational settings."""
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def simulate(rows, limit, recovery):
    events = []
    for row in rows:
        events.extend([(row['entry'], 1, row), (row['exit'], 0, row)])
    paused = False
    losses = wins = generation = 0
    admitted = {}
    net = peak = drawdown = 0.0
    pauses = resumes = 0
    excluded = []
    for stamp, kind, row in sorted(events, key=lambda e: (e[0], e[1], e[2]['ticket'])):
        ticket = row['ticket']
        if kind == 1:
            admitted[ticket] = (not paused, generation)
            continue
        take, epoch = admitted[ticket]
        profit = row['net']
        if take:
            net += profit
            peak = max(peak, net)
            drawdown = max(drawdown, peak-net)
            if not paused:
                losses = losses+1 if profit < 0 else 0
                if limit and losses >= limit:
                    paused = True
                    generation += 1
                    wins = 0
                    pauses += 1
        else:
            excluded.append(row)
            if paused and epoch == generation:
                wins = wins+1 if profit > 0 else 0
                if wins >= recovery:
                    paused = False
                    losses = wins = 0
                    resumes += 1
    return dict(limit=limit, recovery=recovery, net=round(net, 2),
        max_realized_drawdown=round(drawdown, 2), taken=sum(v[0] for v in admitted.values()),
        skipped=len(excluded), avoided_losses=round(-sum(r['net'] for r in excluded if r['net']<0),2),
        missed_gains=round(sum(r['net'] for r in excluded if r['net']>0),2),
        pauses=pauses, resumes=resumes, ends_paused=paused,
        skipped_tickets=[r['ticket'] for r in excluded])


def collect(all_m23=False):
    import MetaTrader5 as mt5
    source = ROOT / '.traderia/runtime/mt5_trade_audit_report.json'
    raw = source.read_bytes()
    audit = json.loads(raw)
    candidates = [r for r in audit['rows'] if r.get('mt5_found')
        and r.get('operation_status') == 'FECHADA/HISTORICO'
        and (str(r.get('operational_model', '')).startswith('MODELO_23_BASKET_ACCUMULATOR_SOURCE_')
             if all_m23 else r.get('operational_model') == 'MODELO_23_BASKET_ACCUMULATOR_SOURCE_M7')]
    terminal = Path.home() / 'AppData/Local/TraderIANovo/MT5-Demo/terminal64.exe'
    try:
        assert mt5.initialize(path=str(terminal), portable=True, timeout=10000), mt5.last_error()
        account = mt5.account_info()
        assert account and account.login == 61551556 and account.trade_mode == 0
        deals = mt5.history_deals_get(datetime(2026,7,1,tzinfo=timezone.utc), datetime.now(timezone.utc))
        assert deals is not None, mt5.last_error()
        positions = mt5.positions_get()
        assert positions is not None, mt5.last_error()
        opened = {p.ticket for p in positions}
    finally:
        mt5.shutdown()
    groups = defaultdict(list)
    for d in deals:
        if d.position_id:
            groups[d.position_id].append(d)
    rows, omitted, seen = [], [], set()
    for r in candidates:
        ticket = int(r['mt5_ticket'])
        if ticket in seen:
            continue
        seen.add(ticket)
        ds = groups.get(ticket, [])
        ins = [d for d in ds if d.entry == 0]
        outs = [d for d in ds if d.entry in (1,3)]
        if not ins or not outs or ticket in opened or any(d.entry==2 for d in ds):
            omitted.append(ticket)
            continue
        entry, end = min(d.time_msc for d in ins), max(d.time_msc for d in outs)
        if entry >= end or abs(sum(d.volume for d in ins)-sum(d.volume for d in outs))>1e-7:
            omitted.append(ticket)
            continue
        rows.append(dict(ticket=ticket, symbol=r['symbol'], entry=entry, exit=end,
            source=r['operational_model'].split('_SOURCE_')[-1],
            setup=r.get('entry_setup', ''), side=r.get('side', ''),
            report_exit=r.get('mt5_time', ''),
            net=round(sum(d.profit+d.commission+d.swap+d.fee for d in ds),2),
            report_net=round(sum(float(r.get(k) or 0) for k in
                ('mt5_realized_profit','mt5_commission','mt5_swap','mt5_fee')),2)))
    return rows, omitted, audit['last_update'], hashlib.sha256(raw).hexdigest()


def main():
    rows, omitted, audit_updated, source_hash = collect()
    results = {}
    for symbol in sorted({r['symbol'] for r in rows}):
        subset = [r for r in rows if r['symbol']==symbol]
        results[symbol] = [simulate(subset, None, 1)] + [
            simulate(subset, n, k) for n in (3,4,5) for k in (1,2,3)]
    payload = dict(created_at=datetime.now(timezone.utc).isoformat(),
        audit_updated=audit_updated, audit_sha256=source_hash,
        rows=rows, omitted=omitted, results=results,
        limitations=['Retrospective admission overlay on executed Demo trades, not candle replay.',
            'Future signals absent from executed history are unavailable.',
            'Basket exits, margin and strategy versions held as observed, not recomputed.',
            'Four-loss threshold selected after observing recent loss streak; no OOS proof.',
            'Native deal timestamps share terminal clock; used for event ordering, not BRT labels.',
            'Same-time exits processed before entries; grouped closes are correlated.'])
    output = ROOT / '.traderia/research/m7_loss_pause_2026-09-12'
    output.mkdir(parents=True, exist_ok=True)
    (output/'results.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(dict(count=len(rows), omitted=omitted,
        net_mismatches=[r['ticket'] for r in rows if abs(r['net']-r['report_net'])>0.02],
        results=results), indent=2))


if __name__ == '__main__':
    main()
