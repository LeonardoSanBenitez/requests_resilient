import unittest
import warnings
warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)
from unittest import IsolatedAsyncioTestCase

import requests_resilient


class TestConfig(IsolatedAsyncioTestCase):
    async def test_all(self):
        r = await requests_resilient.async_get('https://google.com')
        assert r.status_code == 200
        
        r = await requests_resilient.async_get('https://gist.githubusercontent.com/oliveratgithub/0bf11a9aff0d6da7b46f1490f86a71eb/raw/')
        assert r.status_code == 200
        assert type(r.json()) == dict