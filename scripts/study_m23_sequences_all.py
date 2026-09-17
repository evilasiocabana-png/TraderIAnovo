"""Describe observed M23 streaks by asset/source; no operational writes."""
import json
from collections import defaultdict
from pathlib import Path
if __package__:
    from .study_m7_loss_pause import ROOT, collect, simulate
else:
    from study_m7_loss_pause import ROOT, collect, simulate


def describe(rows):
    ordered = sorted(rows, key=lambda r: (r['exit'], r['ticket']))
    runs, alternating = [], []
    win_count = loss_count = 0
    transitions = defaultdict(list)
    prior_losses = 0
    block = []
    equity = peak = 0.0
    phases = {'at_peak': [], 'below_peak': []}
    for row in ordered:
        net = row['net']
        sign = 'G' if net > 0 else 'P' if net < 0 else 'E'
        phases['at_peak' if equity >= peak-0.001 else 'below_peak'].append(net)
        equity += net
        peak = max(peak, equity)
        if prior_losses:
            transitions[prior_losses].append(net)
        prior_losses = prior_losses+1 if net < 0 else 0
        win_count += sign == 'G'
        loss_count += sign == 'P'
        if runs and runs[-1]['sign'] == sign:
            runs[-1]['count'] += 1
            runs[-1]['net'] = round(runs[-1]['net']+net, 2)
            runs[-1]['last_ticket'] = row['ticket']
        else:
            runs.append(dict(sign=sign, count=1, net=net,
                first_ticket=row['ticket'], last_ticket=row['ticket']))
        if block and (sign == 'E' or block[-1]['net']*net >= 0):
            if len(block) >= 3:
                alternating.append(dict(sequence=' '.join('G' if r['net']>0 else 'P' for r in block),
                    count=len(block), net=round(sum(r['net'] for r in block),2),
                    first_ticket=block[0]['ticket'], last_ticket=block[-1]['ticket']))
            block = []
        if sign != 'E':
            block.append(row)
    if len(block)>=3:
        alternating.append(dict(sequence=' '.join('G' if r['net']>0 else 'P' for r in block),
            count=len(block), net=round(sum(r['net'] for r in block),2),
            first_ticket=block[0]['ticket'], last_ticket=block[-1]['ticket']))
    return dict(count=len(rows), wins=win_count, losses=loss_count,
        net=round(equity,2), win_rate=round(100*win_count/len(rows),1) if rows else None,
        max_loss_run=max([r['count'] for r in runs if r['sign']=='P'] or [0]),
        max_win_run=max([r['count'] for r in runs if r['sign']=='G'] or [0]),
        runs=runs, alternating_blocks=alternating,
        after_losses={str(n): dict(samples=len(v), next_wins=sum(x>0 for x in v),
            next_net=round(sum(v),2)) for n,v in sorted(transitions.items())},
        phases={k: dict(count=len(v), wins=sum(x>0 for x in v), net=round(sum(v),2))
            for k,v in phases.items()})


def main():
    rows, omitted, updated, source_hash = collect(all_m23=True)
    audit = json.loads((ROOT/'.traderia/runtime/mt5_trade_audit_report.json').read_text(encoding='utf-8'))
    omitted_set = set(omitted)
    exclusions = [r for r in audit['rows'] if r.get('mt5_ticket') in omitted_set]
    zero_order_exclusions = sum(r.get('mt5_source') == 'ORDER' and not r.get('mt5_realized_profit') for r in exclusions)
    symbols = ['XAUUSD'] + sorted(p.name.removeprefix('historico') for p in
        (ROOT/'.traderia/research/historicosMercado').iterdir() if p.is_dir() and p.name.startswith('historico'))
    assert len(symbols) == 19
    buckets = defaultdict(list)
    for row in rows:
        buckets[(row['symbol'], row['source'])].append(row)
    sources, summary = {}, []
    for symbol in symbols:
        asset_rows = [r for r in rows if r['symbol']==symbol]
        asset = describe(asset_rows)
        simulations = []
        for (sym, source), subset in sorted(buckets.items()):
            if sym != symbol:
                continue
            trials = [simulate(subset,n,k) for n in (3,4,5) for k in (1,2,3)]
            baseline = simulate(subset,None,1)
            sources[f'{symbol}/{source}'] = dict(description=describe(subset), baseline=baseline, trials=trials)
            simulations.append(next(t for t in trials if t['limit']==4 and t['recovery']==1))
        summary.append(dict(symbol=symbol, count=asset['count'], wins=asset['wins'],
            net=asset['net'], source_count=len(simulations),
            four_loss_net=round(sum(t['net'] for t in simulations),2),
            delta=round(sum(t['net'] for t in simulations)-asset['net'],2),
            pauses=sum(t['pauses'] for t in simulations), resumes=sum(t['resumes'] for t in simulations)))
    output = ROOT/'.traderia/research/m23_sequences_19_2026-09-12'
    output.mkdir(parents=True, exist_ok=True)
    payload = dict(audit_updated=updated, audit_sha256=source_hash, rows=rows,
        omitted=omitted, zero_order_exclusions=zero_order_exclusions,
        outside_universe=sorted({r['symbol'] for r in rows}-set(symbols)),
        summary=summary, sources=sources)
    (output/'results.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    lines = ['# M23: sequencias por ativo e fonte', '',
        'Estudo retrospectivo Demo. Nenhuma regra operacional alterada.',
        'Universo: 19 ativos, incluindo XAUUSD. Fonte identificada nos registros M23, resultados e horarios conferidos nos negocios nativos MT5.',
        'Filtro simulado por ativo + fonte, sem compensar perdas de uma fonte com ganhos de outra.', '',
        '## Comparativo', '',
        'P4/G1 = pausa apos 4 perdas e retorno apos 1 ganho simulado. Valor fixado para comparacao, nao melhor parametro selecionado.', '',
        '| Ativo | Operacoes | Fontes | Liquido observado | Liquido P4/G1 | Diferenca | Pausas/retornos |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in summary:
        lines.append(f"| {r['symbol']} | {r['count']} | {r['source_count']} | {r['net']:.2f} | {r['four_loss_net']:.2f} | {r['delta']:+.2f} | {r['pauses']}/{r['resumes']} |")
    lines += ['', '## Limites', '',
        'Nao e replay de candles nem de carteira: so sinais executados e encerrados estao presentes. Saidas coletivas, margem, lotes e mudancas de setup ficam como observados; seriam diferentes em um cenario alternativo.',
        'Pausa so usa perdas encerradas antes da entrada. Ordens ja abertas continuam no resultado. Ganhos simulados nao somam ao realizado.',
        'Contagens de ganhos/perdas por ticket nao sao eventos independentes; fechamentos coletivos podem gerar longas series.',
        'A escolha de quatro perdas foi posterior a queda; nao ha validacao independente. Ausencia de retorno na amostra nao valida regra de reativacao.',
        'Datas de negocios servem para ordenacao no relogio nativo; nao foram reinterpretadas como horario Brasil.',
        f'Registros omitidos por falta de conciliacao: {len(omitted)}. Auditoria: {updated}.',
        f'Desses, {zero_order_exclusions} constam como ORDER com resultado zero no relatorio; nao contam como operacoes encerradas nesta analise.',
        'As fases abaixo distinguem patrimonio no topo anterior ou abaixo dele ANTES de cada encerramento; nao classificam tendencia futura.', '',
        '## Detalhes por fonte', '']
    for key, d in sources.items():
        s = d['description']
        lines += [f'### {key}', '',
            f"{s['count']} operacoes; {s['win_rate']}% ganhos; liquido {s['net']:.2f}; maior serie G={s['max_win_run']}, P={s['max_loss_run']}.",
            'Sequencia completa: ' + ' -> '.join(f"{r['count']}{r['sign']} ({r['net']:+.2f})" for r in s['runs']), '',
            'Blocos alternados (G/P) com pelo menos 3 negocios:']
        lines += [f"- {b['sequence']}: {b['net']:+.2f}" for b in s['alternating_blocks']] or ['- Nenhum.']
        lines += ['', 'Apos perdas consecutivas (observacao, nao previsao):']
        lines += [f"- Apos {n}P: {v['next_wins']} ganhos em {v['samples']} proximos fechamentos; saldo {v['next_net']:+.2f}." for n,v in s['after_losses'].items()]
        for phase,v in s['phases'].items():
            lines.append(f"- Estado {phase}: {v['count']} fechamentos, {v['wins']} ganhos, saldo {v['net']:+.2f}.")
        lines += ['', '| Pausa | Ganhos para retorno | Liquido | Perdas evitadas | Ganhos excluidos | Pausas/retornos |', '|---:|---:|---:|---:|---:|---:|']
        for t in d['trials']:
            lines.append(f"| {t['limit']} | {t['recovery']} | {t['net']:.2f} | {t['avoided_losses']:.2f} | {t['missed_gains']:.2f} | {t['pauses']}/{t['resumes']} |")
        lines.append('')
    (output/'relatorio.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(count=len(rows), omitted=len(omitted), sources=len(sources), summary=summary),indent=2))


if __name__=='__main__':
    main()
