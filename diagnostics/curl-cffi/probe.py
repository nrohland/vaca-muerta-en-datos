"""Bounded public connectivity experiment; no extraction, cloud, credentials or freshness writes."""
import csv
import argparse
import io
import json
from curl_cffi import Curl, CurlError, CurlInfo, CurlOpt

HOST='https://datos.energia.gob.ar'
RESOURCE='fb7a47a0-cba9-4667-a004-6f6c1c346c23'
PATH='/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/'+RESOURCE+'/download/produccin-de-pozos-de-gas-y-petrleo-2026.csv'
ENDPOINTS={
    'metadata_https':HOST+'/api/3/action/resource_show?id='+RESOURCE,
    'metadata_http':HOST.replace('https://','http://')+'/api/3/action/resource_show?id='+RESOURCE,
    'csv_https':HOST+PATH,
    'csv_http':HOST.replace('https://','http://')+PATH,
    'tor_check':'https://check.torproject.org/api/ip',
    'eia_control':'https://www.eia.gov/dnav/ng/hist/rngwhhdm.htm',
}
LIMIT=65536


def probe(name,profile,route="direct",session="direct"):
    if route not in ("direct","tor"):
        raise ValueError("Only direct or local Tor diagnostic routes allowed")
    curl=Curl();body=bytearray();bounded=False;code=0
    def write(chunk):
        nonlocal bounded
        available=LIMIT-len(body)
        body.extend(chunk[:available])
        if len(chunk)>available:
            bounded=True
            return 0
        return len(chunk)
    try:
        if profile and curl.impersonate(profile)!=0:
            return {'endpoint':name,'profile':profile,'status':'unsupported_profile'}
        options={CurlOpt.URL:ENDPOINTS[name],CurlOpt.PROXY:'socks5h://127.0.0.1:19050' if route=='tor' else '',CurlOpt.FOLLOWLOCATION:0,
            CurlOpt.CONNECTTIMEOUT_MS:15000 if route=='tor' else 5000,CurlOpt.TIMEOUT_MS:30000 if route=='tor' else 15000,
            CurlOpt.SSL_VERIFYPEER:1,CurlOpt.SSL_VERIFYHOST:2,CurlOpt.WRITEFUNCTION:write,
            CurlOpt.ACCEPT_ENCODING:b""}
        if route=='tor':
            options[CurlOpt.PROXYUSERNAME]=session
            options[CurlOpt.PROXYPASSWORD]=session
        if name.startswith('csv_'):options[CurlOpt.RANGE]='0-65535'
        for key,value in options.items():curl.setopt(key,value)
        try:curl.perform()
        except CurlError as error:code=int(error.code)
        status=int(curl.getinfo(CurlInfo.RESPONSE_CODE))
        identity=False
        if name.startswith('metadata_') and status==200 and not bounded:
            try:
                value=json.loads(body)
                identity=value.get('success') is True and value.get('result',{}).get('id')==RESOURCE
            except (ValueError,AttributeError):pass
        elif name.startswith('csv_') and status in (200,206):
            try:
                header=next(csv.reader(io.StringIO(body.decode('utf-8-sig'))))
                identity={'idpozo','anio','mes','prod_pet','prod_gas'}<=set(header)
            except (ValueError,UnicodeError,StopIteration,csv.Error):pass
        elif name=='tor_check' and status==200:
            try:identity=json.loads(body).get('IsTor') is True
            except (ValueError,AttributeError):pass
        elif name=='eia_control' and status==200:
            identity=b'Henry Hub' in body
        return {'endpoint':name,'route':route,'session':session,'profile':profile or 'plain_libcurl','http_status':status,
            'curl_exit':code,'bounded_prefix':bounded,'bytes_retained':len(body),
            'expected_payload_prefix':identity,
            **{label:round(float(curl.getinfo(info)),4) for label,info in [
                ('dns_seconds',CurlInfo.NAMELOOKUP_TIME),('tcp_seconds',CurlInfo.CONNECT_TIME),
                ('tls_seconds',CurlInfo.APPCONNECT_TIME),('first_byte_seconds',CurlInfo.STARTTRANSFER_TIME),
                ('total_seconds',CurlInfo.TOTAL_TIME)]}}
    finally:curl.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tor',action='store_true',help='Probe through local Tor SOCKS5 with remote DNS')
    args=parser.parse_args()
    if args.tor:
        for session in ('tor_a','tor_b'):
            for name in ('tor_check','eia_control','metadata_https','metadata_http','csv_https','csv_http'):
                print(json.dumps(probe(name,None,'tor',session),sort_keys=True),flush=True)
    else:
        for profile in (None,'chrome110','chrome142'):
            for name in ENDPOINTS:
                if name!='tor_check':
                    print(json.dumps(probe(name,profile),sort_keys=True),flush=True)
    print(json.dumps({'diagnostic':'completed','warehouse_writes':False,
                      'freshness_updated':False,'complete_csv_downloaded':False}))


if __name__=='__main__':main()
