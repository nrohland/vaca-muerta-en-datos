"""Bounded retries for exact public EIA URLs. No stale fallback or redirect widening."""
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.error import HTTPError, URLError
import time
MAX_BYTES=5*1024**2


def fetch(allowed, *, opener_factory=None, sleep=time.sleep, observe=lambda event:None):
    class SameOfficialURL(HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            if newurl!=allowed:raise ValueError('Unexpected EIA redirect')
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    factory=opener_factory or (lambda:build_opener(SameOfficialURL()))
    for attempt in range(1,4):
        start=time.monotonic()
        try:
            request=Request(allowed,headers={'User-Agent':'VacaMuertaEnDatos/1.0 public-monthly-data'})
            with factory().open(request,timeout=45) as response:
                if response.url!=allowed:raise ValueError('Unexpected EIA URL')
                raw=response.read(MAX_BYTES+1)
                if len(raw)>MAX_BYTES:raise ValueError('EIA response exceeds budget')
            observe({'attempt':attempt,'status':'passed','seconds':round(time.monotonic()-start,3),'bytes':len(raw)})
            return raw
        except (HTTPError,URLError,TimeoutError,ConnectionError) as error:
            observe({'attempt':attempt,'status':'failed','seconds':round(time.monotonic()-start,3),
                     'error_type':type(error).__name__,'http_status':error.code if isinstance(error,HTTPError) else None})
            transient=not isinstance(error,HTTPError) or error.code in (429,500,502,503,504)
            if not transient or attempt==3:raise
            sleep(2**(attempt-1))
