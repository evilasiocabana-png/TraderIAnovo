"""Deterministic daily reconciliation, independent of a Codex conversation."""
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from application.system_supervisor import ROOT, RUNTIME, read_json, atomic_json
from application.operational_audit import event, append_record, fallback_path


def run():
    from filelock import FileLock
    with FileLock(str(RUNTIME/'supervisor_daily.lock'), timeout=0):
        return _run()


def _run():
    from scripts.system_supervisor import configure
    from core.execution_log_storage import execution_log_path
    cfg=configure()
    start=datetime.now(timezone.utc)
    out=RUNTIME/'supervisor_audits'/start.strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=True)
    event('Auditoria automática horária','INICIADA','Conciliação de histórico, custos, curvas e registros iniciada.',details={'evidencias':str(out)})
    rows=[]
    def record(name, ok, text, corrected='NÃO NECESSÁRIO'):
        row=dict(name=name,checked='SIM',error='NÃO' if ok else 'SIM',corrected=corrected if ok else 'NÃO',explanation=text,status='OK' if ok else 'FAIL')
        rows.append(row)
        event('Auditoria automática - '+name,'CONFIRMADO' if ok else 'FALHA',text,details=row)
    try:
        from application.system_supervisor import age
        saved=read_json(RUNTIME/'supervisor_observations/m29_sequence.json')
        payload=saved.get('payload',{})
        if not 0 <= age(saved.get('observed_at')) <= 180:
            raise LookupError('Evidencia operacional recente indisponivel')
        a=payload.get('account') or {}
        if not a or not payload.get('ok'):
            raise LookupError('Evidencia incompleta')
        assert a.get('login')==cfg['login'] and a.get('server')==cfg['server'] and a.get('trade_mode')==0
        deals=payload['rows']
        known={str(d['order']) for d in deals}|{str(p['ticket']) for p in payload.get('open_positions',[])}
        atomic_json(out/'native_snapshot.json',payload)
        log=execution_log_path();accepted=[];invalid=[]
        with log.open(encoding='utf-8-sig') as stream:
            for number,line in enumerate(stream,1):
                if not line.strip():continue
                try:r=json.loads(line)
                except ValueError:
                    invalid.append(dict(line=number, raw=line));continue
                if str(r.get('execution_account_login') or r.get('observed_account_login'))==str(cfg['login']) and r.get('accepted'):accepted.append(r)
        if invalid:
            atomic_json(out/'invalid_historical_lines.json',invalid)
            record('Leitura do histórico local',True,f'Leitor recuperado: {len(invalid)} linhas ilegíveis isoladas nas evidências; original intacto e registros válidos analisados. Conteúdo dessas linhas não foi recuperado nem inventado.', 'SIM')
        missing=[str(r.get('ticket')) for r in accepted if str(r.get('ticket')) not in known]
        if missing:
            rows.append(dict(name='Aceites contra MT5',checked='NÃO',error='NÃO DETERMINADO',corrected='NÃO',status='PENDING',explanation=f'{len(accepted)} aceites; {len(missing)} sem deal/posição correspondente. Ordens canceladas ou pendentes exigem histórico de ordens; não concluir falha de envio.'))
        else:
            record('Aceites contra MT5',True,f'{len(accepted)} aceites conferidos nos dados nativos capturados.')
        from scripts.system_supervisor import journal
        j=journal();record('Tentativas e resultados',j['ok'] and not j['orphans'],f"{j['attempts']} tentativas; {j['results']} resultados; {j['orphans']} tentativas antigas sem resultado.")
        append_record(out/'isolated_probe.jsonl',dict(probe=True))
        record('Persistência',json.loads((out/'isolated_probe.jsonl').read_text().splitlines()[-1])['probe'],'Gravação com confirmação e leitura em arquivo isolado; nenhuma ordem de teste.')
        report_path=RUNTIME/'mt5_trade_audit_report.json'
        report=read_json(report_path)
        historical_orders={str(x.get('mt5_ticket') or x.get('local_ticket')) for x in report.get('rows',[]) if x.get('mt5_found') and x.get('operation_status')=='ORDEM_HISTORICA'}
        unresolved=[ticket for ticket in missing if ticket not in historical_orders]
        for row in rows:
            if row['name']=='Aceites contra MT5' and missing:
                row['explanation']=f'{len(accepted)} aceites; {len(missing)-len(unresolved)} adicionais confirmados como ordens históricas no Relatório; {len(unresolved)} exigem próxima leitura nativa de ordens. Não são perdas nem falhas de envio comprovadas.'
                if not unresolved: row.update(status='OK',checked='SIM',error='NÃO',corrected='NÃO NECESSÁRIO')
        report_rows={str(x['mt5_ticket']):x for x in report.get('rows',[]) if x.get('operation_status')=='FECHADA/HISTORICO'}
        groups=defaultdict(list)
        for d in deals:
            if d['type'] in (0,1):groups[str(d['position_id'])].append(d)
        closed={k:v for k,v in groups.items() if any(d['entry']==0 for d in v) and abs(sum(d['volume']*(1 if d['entry']==0 else -1) for d in v))<1e-8}
        errors=[]
        for k,v in closed.items():
            if k not in report_rows:errors.append(k);continue
            native=sum(d.get(f,0) for d in v for f in ('profit','commission','swap','fee'))
            displayed=sum(float(report_rows[k].get(f) or 0) for f in ('mt5_realized_profit','mt5_commission','mt5_swap','mt5_fee'))
            if abs(native-displayed)>.011:errors.append(k)
        repaired = False
        if errors:
            from application.supervisor_report_repair import repair
            event('Reparador do Relatório','TENTATIVA','Divergência comprovada; reconstruir somente encerramentos nativos, preservando cópia anterior.')
            report, repaired_count = repair(report_path,payload,out)
            report_rows={str(x['mt5_ticket']):x for x in report.get('rows',[]) if x.get('operation_status')=='FECHADA/HISTORICO'}
            errors=[]
            for k,v in closed.items():
                row=report_rows.get(k)
                native=sum(d.get(f,0) for d in v for f in ('profit','commission','swap','fee'))
                shown=sum(float(row.get(f) or 0) for f in ('mt5_realized_profit','mt5_commission','mt5_swap','mt5_fee')) if row else float('inf')
                if abs(native-shown)>.011:errors.append(k)
            repaired=not errors
        record('Histórico e custos',not errors,f'{len(closed)} encerramentos comparados; {len(errors)} divergências. Backup antes de reparar; nenhuma consulta adicional ao MT5.', 'SIM' if repaired else 'NÃO' if errors else 'NÃO NECESSÁRIO')
        from application.report_source_channels import source_channel_groups
        from application.source_channel_gate import reconciled_results,channel_state
        from application.account_channel_continuity import seed_groups
        curves=source_channel_groups([SimpleNamespace(**x) for x in report.get('rows',[]) if x.get('operation_status')=='FECHADA/HISTORICO' and x.get('mt5_found')])
        differences=[]
        for key in seed_groups(payload['account']):
            source,symbol=key.split('/');name=f'M{source} / {symbol}'
            if name not in curves:differences.append(name);continue
            native=reconciled_results(payload,int(source),symbol);shown=curves[name]['results'];ns=channel_state(native);rs=channel_state(shown)
            if (len(native),ns['state'],ns['zone'],round(sum(x['net'] for x in native),2))!=(len(shown),rs['state'],rs['zone'],round(sum(x['net'] for x in shown),2)):differences.append(name)
        record('Curvas patrimoniais',not differences,f'{len(curves)} curvas comparadas por fonte e ativo; {len(differences)} diferenças. Sem reconstruir metadados antigos.')
        # Group rejected attempts for evidence, rather than treating every rejection as a system fault.
        rejected=defaultdict(list);seen=set();cut=start-timedelta(days=1)
        for p in (log.with_name('execution_attempts.jsonl'),fallback_path(log.with_name('execution_attempts.jsonl'))):
            if not p.exists():continue
            for line in p.read_text(encoding='utf-8-sig').splitlines():
                if not line.strip():continue
                r=json.loads(line)
                if r.get('stage')!='RESULT' or r.get('attempt_id') in seen:continue
                seen.add(r.get('attempt_id'))
                if datetime.fromisoformat(r['timestamp'])>=cut and not r['result'].get('accepted'):rejected[r['result'].get('message','Sem motivo')].append(r['timestamp'])
        rejection_summary={k:dict(count=len(v),first=min(v),last=max(v)) for k,v in rejected.items()}
        atomic_json(out/'rejections.json',rejection_summary)
        record('Motivos de rejeição',True,f'{sum(len(v) for v in rejected.values())} rejeições agrupadas com motivos e horários. Diagnóstico causal de cada plano exige análise; não foi alterado nenhum filtro.')
        record('Escopo da auditoria',True,'Analise offline de evidencias operacionais; nao faz consultas concorrentes ao MT5 nem executa pytest durante a operacao.')
    except LookupError:
        rows.append(dict(name='Evidencia operacional',checked='NÃO',error='NÃO DETERMINADO',corrected='NÃO',explanation='Aguardando captura recente do ciclo; nao abrir consulta concorrente ao MT5.',status='PENDING'))
    except Exception as exc:
        record('Conclusão da auditoria',False,'Auditoria incompleta: '+type(exc).__name__, 'NÃO')
    ok=bool(rows) and all(r['status']=='OK' for r in rows)
    result=dict(ok=ok,status='OK' if ok else 'FAIL' if any(r['status']=='FAIL' for r in rows) else 'PENDING',finished_at=datetime.now(timezone.utc).isoformat(),checks=rows,evidence=str(out),
        summary='Conciliação horária das evidências disponíveis concluída. Sem erro nos itens verificados; não precisa de correção adicional.' if ok else 'Auditoria horária com falhas ou etapas incompletas. Consulte os resultados.')
    atomic_json(RUNTIME/'supervisor_daily.json',result)
    event('Auditoria automática horária','CONCLUIDA' if ok else 'CONCLUIDA_COM_PENDENCIA',result['summary'],details=result)
    return result
