"""Read-only source/asset views from recovered, closed M23 history."""
import re
import os
import json
from datetime import datetime, timezone
from collections import defaultdict
from application.model23_source_summary import collect_realized_results
from application.source_channel_gate import channel_state, SOURCES


def source_channel_groups(rows):
    groups = defaultdict(list)
    from application.account_channel_continuity import seed_groups
    seeds = seed_groups(dict(login=os.getenv('TRADERIA_DEMO_ACCOUNT_LOGIN'),
                             server=os.getenv('TRADERIA_DEMO_ACCOUNT_SERVER'),
                             trade_mode=0 if os.getenv('TRADERIA_EXECUTION_ACCOUNT_MODE', 'DEMO') == 'DEMO' else 2))
    from application.account_channel_continuity import CONFIG
    config = json.loads(CONFIG.read_text(encoding='utf-8')) if seeds and CONFIG.exists() else {}
    cutover = datetime.fromisoformat(config['report_cutover_utc']) if config.get('report_cutover_utc') else None
    for key in seeds:
        number, symbol = key.split('/', 1)
        groups[(int(number), symbol)]
    for row in rows:
        if cutover is not None:
            # Report timestamps can be entry times, unlike the realized seed's close times.
            # Pre-migration rows belong to the archived period, never add them again.
            try:
                if datetime.fromisoformat(row.mt5_time) < cutover:
                    continue
            except (ValueError, TypeError):
                raise ValueError('Horario do Relatorio invalido para continuidade')
        match = re.fullmatch(r"MODELO_23_BASKET_ACCUMULATOR_SOURCE_M(\d+)", str(row.operational_model))
        if not match or int(match[1]) not in SOURCES:
            continue
        if not row.mt5_found or row.operation_status != "FECHADA/HISTORICO":
            continue
        groups[(int(match[1]), row.symbol)].append(row)
    output = {}
    for (number, symbol), group in sorted(groups.items()):
        results = collect_realized_results(sorted(group, key=lambda r: (r.mt5_time, str(r.mt5_ticket))))
        previous = seeds.get(f'{number}/{symbol}', [])
        if previous:
            historic = [dict(net=r['net'], ticket=r['id'],
                             time=datetime.fromtimestamp(r['time']/1000, timezone.utc).isoformat(),
                             letter='G' if r['net'] > 0 else 'P' if r['net'] < 0 else 'E',
                             origin='Conta anterior; continuidade autorizada') for r in previous]
            # A persisted report may still contain the exact archived deals.
            # Match ticket AND close time AND net; a reused ticket alone is not a duplicate.
            def identity(row):
                return (str(row['ticket']).split(':')[-1],
                        round(datetime.fromisoformat(row['time']).timestamp() * 1000),
                        round(float(row['net']), 2))
            archived = {identity(row) for row in historic}
            current = [dict(row, ticket=f"{os.getenv('TRADERIA_DEMO_ACCOUNT_LOGIN')}:{row['ticket']}")
                       for row in results if identity(row) not in archived]
            results = sorted(historic + current, key=lambda r: (r['time'], r['ticket']))
        if not results:
            continue
        state = channel_state(results)
        source = f"M{number}"
        output[f"{source} / {symbol}"] = dict(source=source, symbol=symbol, results=results,
            summary={"Fonte":source,"Ativo":symbol,"Estrutura atual":state["state"],
                     "Canal":(state["channel"] or {}).get("trend", "Sem canal"),
                     "Faixa":state["zone"],"Encerramentos":len(results),
                     "Ultimo encerramento":results[-1]["time"],
                     "Saldo liquido":round(sum(r["net"] for r in results),2)})
    return output
