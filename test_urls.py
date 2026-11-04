import unittest
from extract_bbplus import normalize
class UrlTests(unittest.TestCase):
    def test_canonical_public_routes_and_invalid_authorities(self):
        self.assertEqual(normalize('/courses/demo/?query=1#part'),'https://bbplus.plus/courses/demo/')
        self.assertEqual(normalize('http://bbplus.plus:80/courses/demo/'),'https://bbplus.plus/courses/demo/')
        for url in ['https://[bad','https://name:pass@bbplus.plus/courses/demo/','https://bbplus.plus:444/courses/demo/','https://other.invalid/courses/demo/',None]:self.assertIsNone(normalize(url))
