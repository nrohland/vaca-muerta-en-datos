"""Restore metadata observations and deliver idempotent GitHub Issues; never log tokens."""
import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import urllib.error
from urllib.request import Request, urlopen
import zipfile

MAX_BYTES = 5*1024**2


class GitHub:
    def __init__(self, repository, token):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
            raise ValueError('Invalid repository')
        self.repository = repository
        self.root = 'https://api.github.com/repos/'+repository
        self.token = token

    def api(self, path, data=None):
        request=Request(self.root+path, data=json.dumps(data).encode() if data is not None else None,
                        headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json',
                                 'Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28'})
        from urllib.request import HTTPRedirectHandler, build_opener
        root=self.root
        class SameAPI(HTTPRedirectHandler):
            def redirect_request(self, request, fp, code, msg, headers, newurl):
                if not newurl.startswith(root+'/'):raise ValueError('Unexpected GitHub API redirect')
                return super().redirect_request(request,fp,code,msg,headers,newurl)
        try:
            with build_opener(SameAPI()).open(request,timeout=30) as response:
                raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES: raise ValueError('GitHub response exceeds budget')
            return json.loads(raw)
        except urllib.error.HTTPError as error:
            raise RuntimeError('GitHub request rejected: HTTP '+str(error.code)) from None

    def artifact(self, identifier):
        # API redirect receives auth, signed blob destination must NOT receive it.
        from urllib.request import HTTPRedirectHandler, build_opener
        class NoForward(HTTPRedirectHandler):
            def redirect_request(self, request, fp, code, msg, headers, newurl):
                if not newurl.startswith('https://'): raise ValueError('Artifact redirect requires HTTPS')
                redirected=super().redirect_request(request,fp,code,msg,headers,newurl)
                if redirected:
                    for key in list(redirected.headers):
                        if key.lower()=='authorization':del redirected.headers[key]
                    for key in list(redirected.unredirected_hdrs):
                        if key.lower()=='authorization':del redirected.unredirected_hdrs[key]
                return redirected
        request=Request(self.root+f'/actions/artifacts/{int(identifier)}/zip',
                        headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json'})
        with build_opener(NoForward()).open(request,timeout=30) as response:
            raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES: raise ValueError('Artifact exceeds budget')
        with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
            names=bundle.namelist()
            if 'state.json' not in names:raise ValueError('State artifact missing')
            entry=bundle.getinfo('state.json')
            if entry.file_size>MAX_BYTES:raise ValueError('State expands beyond budget')
            return json.loads(bundle.read(entry))


def restore(api, output):
    # Only this workflow on this repository/main; no PR/fork artifacts or unbounded archive discovery.
    runs=api.api('/actions/workflows/source-monitor.yml/runs?branch=main&status=completed&per_page=20')['workflow_runs']
    for run in runs:
        if run.get('head_repository',{}).get('full_name') != api.repository:continue
        if run['head_branch']!='main' or run['event'] not in ('schedule','workflow_dispatch','workflow_run'):continue
        artifacts=api.api(f"/actions/runs/{int(run['id'])}/artifacts")['artifacts']
        for artifact in artifacts:
            if artifact['name']=='source-monitor-state' and not artifact['expired']:
                state=api.artifact(artifact['id'])
                output.write_text(json.dumps(state,indent=2)+'\n')
                return True
    return False


def issue_body(event, run_url):
    kind, period, details=event['kind'],event.get('period'),event['details']
    labels={'new_month_observed':'Nuevo mes disponible para observar',
            'month_ready_for_review':'Mes listo para revisión de cobertura',
            'accepted_month_revised':'Cambios en un mes aceptado',
            'accepted_price_revised':'Referencia de precio revisada',
            'accepted_price_missing':'Referencia de precio ausente',
            'annual_resource_requires_review':'Recurso anual fuera del contrato requiere revisión',
            'month_readiness_withdrawn':'Mes vuelve a requerir observación',
            'source_quality_failure':'Problema de calidad de la fuente',
            'source_observation_failed':'No se pudo verificar la fuente'}
    title=labels[kind]+(' · '+period[:7] if period else '')
    body=f"<!-- vm-source-event:{event['id']} -->\n\n{title}.\n\n"
    if kind=='month_ready_for_review':
        body+='Mes transcurrido, cobertura ≥98% de la mediana de los tres meses aceptados anteriores, dos recuperaciones distintas estables durante ≥48 horas y ambas cotizaciones mensuales disponibles. **Es una señal para revisar, no una certificación oficial de completitud.**\n\n'
    if kind=='accepted_month_revised':
        before,after=details['before'],details['after']
        body+='| Indicador | Anterior | Actual |\n| --- | ---: | ---: |\n'
        for key in ('rows','vm_rows','oil_wells','gas_wells','oil_m3','gas_km3'):
            body+=f'| {key} | {before[key]} | {after[key]} |\n'
        body+='\nCambio de contenido VM: '+str(details['vm_changed'])+'. El fingerprint detecta también reasignaciones/atributos aunque los totales coincidan.\n\n'
    elif kind=='new_month_observed':
        p=details['profile'];body+=f"Registros nacionales: {p['rows']}; registros VM: {p['vm_rows']}. Puede ser parcial.\n\n"
    elif kind in ('accepted_price_revised','accepted_price_missing'):
        body+=f"Fluido: {details['fluid']}. Referencia anterior: {details['before']}; actual: {details.get('after','ausente')}.\n\n"
    elif kind=='source_observation_failed':
        body+='La recuperación/validación falló. No se renueva la frescura ni se certifica ausencia de novedades.\n\n'
    body+=f'[Evidencia de la ejecución]({run_url}).\n\nLa aceptación, corrección de anclajes y promoción del snapshot son decisiones separadas. Este aviso no carga BigQuery ni publica datos.'
    return title,body


def notify(api, state, report, run_url):
    known=set(state.get('notified_event_ids',[])); outcomes=[]
    if all(e['id'] in known for e in report['events']):return outcomes
    labels=api.api('/labels?per_page=100')
    if not any(label['name']=='data-monitor' for label in labels):
        api.api('/labels',{'name':'data-monitor','color':'27627C','description':'Nuevos meses y revisiones de fuentes públicas'})
    existing={}
    for page in range(1,11):
        issues=api.api(f'/issues?state=all&labels=data-monitor&per_page=100&page={page}')
        for issue in issues:
            for identifier in re.findall(r'<!-- vm-source-event:([a-f0-9]{64}) -->',issue.get('body') or ''):
                existing[identifier]=issue['number']
        if len(issues)<100:break
    else:
        raise ValueError('Notification inventory exceeds budget; refusing duplicate delivery')
    for event in report['events']:
        identifier=event['id']
        if identifier in known or identifier in existing:
            known.add(identifier);continue
        title,body=issue_body(event,run_url)
        created=api.api('/issues',{'title':title,'body':body,'labels':['data-monitor'],'assignees':[api.repository.split('/')[0]]})
        known.add(identifier);outcomes.append({'event_id':identifier,'issue_number':created['number']})
        # Keep acknowledgements; the next run also checks existing issue markers after delivery failures.
        state['notified_event_ids']=sorted(known)
    state['notified_event_ids']=sorted(known)
    return outcomes


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['restore','notify'])
    p.add_argument('--repository',required=True);p.add_argument('--state',type=Path,required=True)
    p.add_argument('--report',type=Path);p.add_argument('--run-url');a=p.parse_args()
    api=GitHub(a.repository,os.environ['GH_TOKEN'])
    if a.phase=='restore':print(json.dumps({'restored':restore(api,a.state)}))
    else:
        state=json.loads(a.state.read_text());report=json.loads(a.report.read_text())
        delivered=notify(api,state,report,a.run_url)
        a.state.write_text(json.dumps(state,indent=2)+'\n')
        print(json.dumps({'delivered':len(delivered),'issues':delivered}))
