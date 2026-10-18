import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import check_public_sources as check
class TransportDiagnostic(unittest.TestCase):
    def setUp(self):
        self.dns=patch.object(check.socket,'getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',0))])
        self.dns.start();self.addCleanup(self.dns.stop)
    def test_exact_redirect_is_accepted_without_following_or_tls_bypass(self):
        payload={'http_code':301,'redirect_url':check.PATHS['production_http'],'time_connect':.1}
        with patch.object(check.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(payload))) as run:
            result=check.transport_probe('production_https')
        self.assertEqual(result['status'],'reachable')
        args=run.call_args.args[0]
        self.assertNotIn('-k',args);self.assertNotIn('-L',args);self.assertNotIn('--location',args)
        self.assertNotIn('redirect_url',result)
    def test_timeouts_and_foreign_redirects_are_not_success(self):
        for code,payload in [(28,{'http_code':0}),(0,{'http_code':301,'redirect_url':'https://private.test/?token=secret'})]:
            with patch.object(check.subprocess,'run',return_value=SimpleNamespace(returncode=code,stdout=json.dumps(payload))):
                result=check.transport_probe('production_https')
            self.assertEqual(result['status'],'unavailable');self.assertNotIn('secret',json.dumps(result))
