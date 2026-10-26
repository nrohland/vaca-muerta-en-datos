"""Read-only catalogue/mirror diagnosis. Never certifies freshness or promotes data."""
import csv
import hashlib
from html.parser import HTMLParser
import io
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener

CATALOGUES = {
    'national_requested': 'https://datos.gob.ar/api/3/action/package_show?id=energia_produccion-de-petroleo-y-gas-por-pozo',
    'national_catalogue_slug': 'https://datos.gob.ar/api/3/action/package_show?id=energia-produccion-petroleo-gas-por-pozo-capitulo-iv',
    'national_page': 'https://datos.gob.ar/dataset/energia-produccion-petroleo-gas-por-pozo-capitulo-iv',
}
HF_COMMIT = 'a53f0fdca86d585edfebee68ff87e73672bfbd11'
HF_FILE = f'https://huggingface.co/spaces/contepablod/vm_app/resolve/{HF_COMMIT}/data/well_prod_data.csv'
HF_SHA256 = '40f56220b48bb71e8f6730432aa25cce14d94b3cbc8ad6b3e02a403a04ea84dd'
HF_SIZE = 21847744


class CatalogueRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlparse(newurl)
        if target.scheme != 'https' or target.hostname not in {'datos.gob.ar','www.datos.gob.ar'} or target.username or target.password:
            raise ValueError('Redirect outside reviewed catalogue hosts')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class MirrorRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = urlparse(newurl)
        allowed = host.hostname == 'huggingface.co' or (host.hostname or '').endswith('.huggingface.co') or (host.hostname or '').endswith('.xethub.hf.co') or (host.hostname or '').endswith('.hf.co')
        if host.scheme != 'https' or not allowed or host.username or host.password:
            raise ValueError('Redirect outside reviewed mirror delivery hosts')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = set()
    def handle_starttag(self, tag, attrs):
        for name,value in attrs:
            if name in {'href','data-url'} and value:
                target = urlparse(value)
                if target.hostname and ('energia' in target.hostname or '.csv' in target.path.lower()):
                    self.links.add(target.scheme+'://'+target.netloc+target.path)


def emit(record):
    print(json.dumps(record, ensure_ascii=False), flush=True)


def catalogue(name, url):
    started = time.monotonic()
    record = {'probe':name,'url':url}
    try:
        request = Request(url, headers={'Accept':'application/json,text/html','User-Agent':'VacaMuertaEnDatos-catalogue-diagnostic/1.0'})
        try: response = build_opener(CatalogueRedirect()).open(request, timeout=20)
        except HTTPError as error: response = error
        with response:
            record.update(http_status=response.status, final_url=response.url, content_type=response.headers.get('Content-Type'))
            raw = response.read(8*1024*1024+1)
            if len(raw) > 8*1024*1024: raise ValueError('Catalogue size limit')
        record['bytes'] = len(raw)
        try: data = json.loads(raw)
        except ValueError: data = None
        if isinstance(data,dict):
            record['ckan_success'] = data.get('success')
            result = data.get('result')
            if isinstance(result,dict):
                record['metadata_modified'] = result.get('metadata_modified')
                record['resources'] = [{'id':r.get('id'),'name':r.get('name'),'host':urlparse(r.get('url','')).hostname,'path':urlparse(r.get('url','')).path} for r in result.get('resources',[]) if isinstance(r,dict)]
            error = data.get('error')
            if isinstance(error,dict): record['ckan_error_type'] = error.get('__type')
        else:
            parser = Links(); parser.feed(raw.decode('utf-8', errors='replace'))
            record['resource_links'] = sorted(parser.links)[:80]
    except (URLError,TimeoutError,ValueError) as error:
        record['error'] = type(error).__name__
    record['seconds'] = round(time.monotonic()-started,3)
    emit(record)


def mirror():
    started = time.monotonic()
    record = {'probe':'huggingface_processed_copy','commit':HF_COMMIT,'url':HF_FILE,'official_raw_equivalent':False}
    try:
        with build_opener(MirrorRedirect()).open(Request(HF_FILE,headers={'User-Agent':'VacaMuertaEnDatos-catalogue-diagnostic/1.0'}),timeout=30) as response:
            raw = response.read(32*1024*1024+1)
            record['http_status'] = response.status
        if len(raw)>32*1024*1024: raise ValueError('Mirror size limit')
        checksum = hashlib.sha256(raw).hexdigest()
        record.update(bytes=len(raw), sha256=checksum, matches_published_lfs=checksum==HF_SHA256 and len(raw)==HF_SIZE)
        if not record['matches_published_lfs']: raise ValueError('Mirror differs from reviewed commit')
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        record['columns'] = reader.fieldnames
        periods=[]; rows=0; wells=set()
        for row in reader:
            periods.append((int(row['year']),int(row['month'])))
            wells.add(row['well_id']); rows+=1
        record.update(rows=rows,unique_wells=len(wells),min_period='%04d-%02d'%min(periods),max_period='%04d-%02d'%max(periods))
    except (URLError,TimeoutError,ValueError,KeyError) as error:
        record['error']=type(error).__name__
    record['seconds']=round(time.monotonic()-started,3)
    emit(record)


if __name__ == '__main__':
    for name,url in CATALOGUES.items(): catalogue(name,url)
    mirror()
    emit({'diagnostic_completed':True,'official_mirror_verified':False,'freshness_updated':False,'warehouse_writes':False})
