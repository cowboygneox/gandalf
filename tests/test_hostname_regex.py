import unittest

from app import should_allow_host


class HostnameRegexTest(unittest.TestCase):
    def test_fails_regex(self):
        self.assertFalse(should_allow_host('localhost', ''))
        self.assertFalse(should_allow_host('localhost', 'app'))
        self.assertFalse(should_allow_host('localhost', 'bogus'))
        self.assertFalse(should_allow_host('localhost', 'bogus*'))
        self.assertFalse(should_allow_host('localhost', 'local'))
        self.assertFalse(should_allow_host('api-4001912865-7c7es', 'api'))
        self.assertFalse(should_allow_host('api-4001912865-7c7es', 'api-[0-9]*'))

    def test_passes_regex(self):
        self.assertTrue(should_allow_host('localhost', 'localhost'))
        self.assertTrue(should_allow_host('api-4001912865-7c7es', 'api-[a-z0-9\-]*'))
        self.assertTrue(should_allow_host('localhost', '(localhost|api-[a-z0-9\-]*)'))
        self.assertTrue(should_allow_host('api-4001912865-7c7es', '(localhost|api-[a-z0-9\-]*)'))
