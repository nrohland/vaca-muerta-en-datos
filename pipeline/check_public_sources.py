"""Read-only transport diagnosis; never load data, notify, or advance freshness."""
import json
import subprocess
import time
import source_monitor as monitor

RESOURCE = monitor.source.RESOURCES[2026]
PATHS = {
    'production_https': 'https://datos.energia.gob.ar/api/3/action/resource_show?id='+RESOURCE,
    'production_http': 'http://datos.energia.gob.ar/api/3/action/resource_show?id='+RESOURCE,
    'catalogue_https': 'https://datos.energia.gob.ar/api/3/action/package_show?id='+monitor.source.PACKAGE,
    'catalogue_http': 'http://datos.energia.gob.ar/api/3/action/package_show?id='+monitor.source.PACKAGE,
}


def transport_probe(name):
    url = PATHS[name]
    # No redirect following, credentials, response bodies, proxy changes or TLS bypass.
    result = subprocess.run(['curl','--silent','--output','/dev/null','--connect-timeout','5',
                             '--max-time','12','--write-out','%{json}',url],
                            capture_output=True,text=True,timeout=15,check=False)
    try: detail=json.loads(result.stdout)
    except (ValueError, TypeError): detail={}
    status = int(detail.get('http_code') or 0)
    redirect = detail.get('redirect_url') or ''
    expected_redirect = url.replace('https://','http://',1)
    accepted = result.returncode == 0 and ((name.endswith('https') and status in (301,302,307,308)
                                          and redirect == expected_redirect) or status == 200)
    return {'source':name,'status':'reachable' if accepted else 'unavailable',
            'curl_exit':result.returncode,'http_status':status,
            'redirect':'reviewed_public_http' if redirect == expected_redirect and redirect else 'unexpected' if redirect else 'none',
            **{key:round(float(detail.get(key) or 0),3) for key in
               ('time_namelookup','time_connect','time_appconnect','time_starttransfer','time_total')}}


def main():
    probes=[]
    for name in PATHS:
        result=transport_probe(name);probes.append(result)
        print(json.dumps(result),flush=True)
    checks=[('oil',lambda:monitor.fetch_eia(monitor.import_brent)),
            ('gas',lambda:monitor.fetch_eia(monitor.import_henry_hub))]
    if all(p['status']=='reachable' for p in probes):
        checks += [('production_2026_metadata',lambda:monitor.source.read_metadata(2026,monitor.build_opener(monitor.source.AnnualRedirect(2026)))),
                   ('catalogue',monitor.discover_resources)]
    unavailable=any(p['status']!='reachable' for p in probes)
    for name,read in checks:
        started=time.monotonic()
        try: read(); result={'source':name,'status':'passed'}
        except Exception as error:
            unavailable=True; result={'source':name,'status':'unavailable',**monitor.source_error(error)}
        result['seconds']=round(time.monotonic()-started,3)
        print(json.dumps(result),flush=True)
    print(json.dumps({'diagnostic':'completed','origin_status':'unavailable' if unavailable else 'reachable',
                      'freshness_updated':False,'warehouse_writes':False}),flush=True)
    # This job collects diagnostics. The real source monitor retains its failure gate.
    return 0


if __name__=='__main__':
    raise SystemExit(main())
