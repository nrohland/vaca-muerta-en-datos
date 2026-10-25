"""Transport recovery must never accept partial bytes or downgrade TLS."""
from pathlib import Path
import ssl
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import source_history_pipeline as source


class DownloadRecoveryTests(unittest.TestCase):
    def test_retries_discard_partial_bytes_and_preserve_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp)/'2026.csv'
            calls = []
            receipt = {'downloaded_at': '2026-10-21T12:00:00+00:00'}
            def attempt(year, path):
                self.assertFalse(path.exists())
                calls.append(year)
                path.write_bytes(b'complete' if len(calls) == 3 else b'partial')
                if len(calls) < 3:
                    raise TimeoutError('read timeout')
                return receipt
            with patch.object(source, '_retrieve_once', side_effect=attempt), patch.object(source.time, 'sleep') as sleep:
                self.assertEqual(source.retrieve(2026, destination), receipt)
            self.assertEqual(destination.read_bytes(), b'complete')
            self.assertEqual(calls, [2026]*3)
            self.assertEqual([x.args[0] for x in sleep.call_args_list], [1, 2])
            self.assertFalse(destination.with_suffix('.csv.partial').exists())

    def test_permanent_http_and_tls_errors_never_retry(self):
        for error in [HTTPError('https://official.invalid',403,'Forbidden',{},None),
                      URLError(ssl.SSLCertVerificationError('certificate rejected'))]:
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as tmp:
                dest=Path(tmp)/'2026.csv'
                def attempt(year, path):
                    path.write_bytes(b'partial')
                    raise error
                with patch.object(source, '_retrieve_once', side_effect=attempt) as fetch, patch.object(source.time, 'sleep') as sleep:
                    with self.assertRaises(type(error)): source.retrieve(2026,dest)
                self.assertEqual(fetch.call_count,1)
                sleep.assert_not_called()
                self.assertFalse(dest.exists())
                self.assertFalse(dest.with_suffix('.csv.partial').exists())

    def test_retry_exhaustion_leaves_no_published_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'2026.csv'
            with patch.object(source,'_retrieve_once',side_effect=TimeoutError), patch.object(source.time,'sleep'):
                with self.assertRaises(TimeoutError): source.retrieve(2026,dest)
            self.assertFalse(dest.exists())

    def test_existing_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'2026.csv';dest.write_bytes(b'accepted')
            with self.assertRaises(ValueError):source.retrieve(2026,dest)
            self.assertEqual(dest.read_bytes(),b'accepted')
