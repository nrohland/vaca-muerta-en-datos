import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('bundle_install',ROOT/'scripts/install_candidate_bundle.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


class CandidateBundleInstallTests(unittest.TestCase):
    def bundle(self, root):
        source=root/'candidate';source.mkdir()
        for name in installer.REQUIRED:(source/name).write_text('{}')
        (source/'export-receipt.json').write_text('{}')
        (source/'snapshots').mkdir();(source/'snapshots/shard.json.gz').write_bytes(b'new-shard')
        return source

    def test_replaces_all_assets_and_never_retains_old_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=self.bundle(root);dest=root/'public-data';dest.mkdir()
            (dest/'approval.json').write_text('old-approval')
            (dest/'snapshots').mkdir();(dest/'snapshots/old.gz').write_bytes(b'old')
            installer.install_bundle(source,dest)
            self.assertFalse((dest/'approval.json').exists())
            self.assertFalse((dest/'export-receipt.json').exists())
            self.assertFalse((dest/'snapshots/old.gz').exists())
            self.assertEqual((dest/'snapshots/shard.json.gz').read_bytes(),b'new-shard')

    def test_invalid_candidate_leaves_previous_bundle_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=self.bundle(root);dest=root/'public-data';dest.mkdir()
            (dest/'accepted').write_text('last-good');(source/'manifest.json').unlink()
            with self.assertRaisesRegex(ValueError,'Incomplete'):installer.install_bundle(source,dest)
            self.assertEqual((dest/'accepted').read_text(),'last-good')

    def test_failed_swap_rolls_back_previous_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=self.bundle(root);dest=root/'public-data';dest.mkdir()
            (dest/'accepted').write_text('last-good')
            original=installer.os.replace;count=0
            def fail_second(*args):
                nonlocal count
                count+=1
                if count==2:raise OSError('simulated failed swap')
                return original(*args)
            with patch.object(installer.os,'replace',side_effect=fail_second):
                with self.assertRaises(OSError):installer.install_bundle(source,dest)
            self.assertEqual((dest/'accepted').read_text(),'last-good')

    def test_unknown_public_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=self.bundle(root);(source/'credentials.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Unexpected'):installer.install_bundle(source,root/'dest')
