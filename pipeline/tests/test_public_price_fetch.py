import sys
from pathlib import Path
from io import BytesIO
from types import SimpleNamespace
from urllib.error import HTTPError
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from public_price_fetch import fetch,MAX_BYTES
URL='https://www.eia.gov/dnav/ng/hist/rngwhhdm.htm'
class Response(BytesIO):
    url=URL
class PublicPriceFetchTests(unittest.TestCase):
    def test_unreviewed_url_never_opens_transport(self):
        with self.assertRaisesRegex(ValueError,'exact reviewed'):fetch('https://evil.test/',opener_factory=lambda:self.fail('No transport'))
    def test_transient_timeout_retries_without_reusing_a_failed_response(self):
        events=[];sleeps=[];calls=[]
        def open(request,timeout):
            calls.append((request.full_url,timeout))
            if len(calls)==1:raise TimeoutError('private diagnostic not emitted')
            return Response(b'valid-body')
        raw=fetch(URL,opener_factory=lambda:SimpleNamespace(open=open),sleep=sleeps.append,observe=events.append)
        self.assertEqual(raw,b'valid-body');self.assertEqual(len(calls),2);self.assertEqual(sleeps,[1]);self.assertEqual(events[0]['error_type'],'TimeoutError');self.assertNotIn('private',str(events))
    def test_access_denied_and_wrong_redirect_never_retry(self):
        for error in [HTTPError(URL,403,'private',{},None),ValueError('Unexpected EIA redirect')]:
            calls=[]
            def open(*a,**k):calls.append(1);raise error
            with self.assertRaises(type(error)):fetch(URL,opener_factory=lambda:SimpleNamespace(open=open),sleep=lambda _:None)
            self.assertEqual(len(calls),1)
    def test_total_attempts_bounded_and_oversize_is_not_retried(self):
        calls=[]
        def open(*a,**k):calls.append(1);raise HTTPError(URL,503,'private',{},None)
        with self.assertRaises(HTTPError):fetch(URL,opener_factory=lambda:SimpleNamespace(open=open),sleep=lambda _:None)
        self.assertEqual(len(calls),3)
        with self.assertRaisesRegex(ValueError,'budget'):fetch(URL,opener_factory=lambda:SimpleNamespace(open=lambda *a,**k:Response(b'x'*(MAX_BYTES+1))),sleep=lambda _:self.fail('No retry on size failure'))
