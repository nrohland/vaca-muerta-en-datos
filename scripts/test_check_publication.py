import unittest
from check_publication import forbidden

class PublicationTests(unittest.TestCase):
    def test_environment_files_are_blocked_at_any_depth(self):
        for p in ['.env','apps/web/.env.local','transform/.env.production','.ENV','a/.secrets/key.json']:
            with self.subTest(path=p):self.assertIsNotNone(forbidden(p))
    def test_only_sanitized_example_filename_is_allowed(self):
        for p in ['.env.example','transform/.env.example','apps/web/next-env.d.ts','infra/terraform/.terraform.lock.hcl']:
            with self.subTest(path=p):self.assertIsNone(forbidden(p))
    def test_keys_and_local_state_cannot_be_committed(self):
        for p in ['a/private.key','credentials.json','terraform.tfstate','gha-creds-123.json','.terraform/providers/file']:
            with self.subTest(path=p):self.assertIsNotNone(forbidden(p))

if __name__=='__main__':unittest.main()
