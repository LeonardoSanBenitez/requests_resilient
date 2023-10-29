import unittest
import warnings
warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)
from unittest import IsolatedAsyncioTestCase

import requests_resilient


class TestConfig(IsolatedAsyncioTestCase):
    async def test_success(self):
        r = requests_resilient.get('https://google.com')
        assert r.status_code == 200

        r = requests_resilient.get(url='https://google.com')
        assert r.status_code == 200

        r = requests_resilient.get('https://google.com', max_retries=1)
        assert r.status_code == 200

        r = requests_resilient.get('https://google.com', headers={})
        assert r.status_code == 200

        r = requests_resilient.get('https://google.com', verify_function=lambda r: r.status_code//100 == 2)
        assert r.status_code == 200

    async def test_fail(self):
        self.assertRaises(Exception, requests_resilient.get, 'https://google.com', wait=0.01, max_retries=2, verify_function=lambda r: False)
        self.assertRaises(Exception, requests_resilient.get, 'https://google.com', wait=0.01, max_retries=2, verify_function=lambda r: r.status_code == 300)
