"""Export complete observed gold sequences from the saved read-only study."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / '.traderia/research/m23_sequences_19_2026-09-12'
data = json.loads((folder / 'results.json').read_text(encoding='utf-8'))
models = ['M1', 'M2', 'M5', 'M7', 'M8', 'M10', 'M18', 'M20']
lines = ['# Ouro: sequencias completas por fonte atual do M23', '',
    '**G = ganho liquido; P = perda liquida; E = resultado zero.**', '',
    'Todos os blocos do primeiro ao ultimo encerramento conciliado, sem limitar aos ultimos dez.',
    'Conta Demo. Copias do M23, nao ordens diretas dos modelos. Fontes autorizadas na configuracao consultada em 12/09/2026.',
    f"Auditoria utilizada: {data['audit_updated']}.",
    'Este e todo o historico disponivel e conciliado no estudo, nao garantia de cobertura de toda a conta ou sinais nao executados.',
    'Resultados liquidos nativos MT5. Mudancas de setup e fechamentos coletivos estao presentes; sequencias nao sao previsoes.', '',
    '## Indice', '']
for model in models:
    lines.append(f'- [{model}](#{model.lower()})')
for model in models:
    lines += ['', f'## {model}', '']
    item = data['sources'].get(f'XAUUSD/{model}')
    if not item:
        lines += ['Sem posicoes encerradas de ouro conciliadas neste estudo. Nao e resultado zero nem prova de ausencia de sinais.']
        continue
    d = item['description']
    rows = sorted([r for r in data['rows'] if r['symbol']=='XAUUSD' and r['source']==model],
                  key=lambda r: (r['exit'], r['ticket']))
    lines += [f"**{d['count']} operacoes | {d['wins']} ganhos | {d['losses']} perdas | saldo liquido US$ {d['net']:+.2f}**", '',
        '### Sequencia inteira', '',
        'Cada linha continua a anterior. Os numeros antes de G/P indicam operacoes consecutivas, nao probabilidades.', '']
    runs = d['runs']
    for offset in range(0, len(runs), 8):
        lines.append(f"Blocos {offset+1}-{min(offset+8,len(runs))}: " +
                     ' -> '.join(f"{r['count']}{r['sign']}" for r in runs[offset:offset+8]))
        lines.append('')
    lines += ['### Saldo de cada bloco', '',
        '| Bloco | Sequencia | Saldo do bloco (USD) | Acumulado (USD) |',
        '|---:|---|---:|---:|']
    accumulated = 0
    for i,r in enumerate(runs,1):
        accumulated += r['net']
        lines.append(f"| {i} | {r['count']}{r['sign']} | {r['net']:+.2f} | {accumulated:+.2f} |")
    assert sum(r['count'] for r in runs) == len(rows)
    assert abs(accumulated-sum(r['net'] for r in rows)) < 0.02
    lines += ['', '### Operacao por operacao', '',
        'Ordem pelo encerramento nativo MT5. Tickets permitem conferir os negocios sem depender da conversao de fuso do painel.', '',
        '| Ordem | Ticket | Resultado | Liquido (USD) |', '|---:|---:|---|---:|']
    for i,r in enumerate(rows,1):
        label = 'G' if r['net']>0 else 'P' if r['net']<0 else 'E'
        lines.append(f"| {i} | {r['ticket']} | {label} | {r['net']:+.2f} |")
target = folder/'OURO_SEQUENCIAS_COMPLETAS.md'
target.write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(dict(path=str(target), models=models, positions=sum(
    data['sources'].get(f'XAUUSD/{m}',{}).get('description',{}).get('count',0) for m in models))))
