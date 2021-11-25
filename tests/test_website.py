# project

# other
import os
import urllib.request
import urllib.parse
import ssl
import certifi
import unittest
from google.cloud import ndb
import requests

MOTHERSHIP = os.environ["TEST_MOTHERSHIP"]
assert MOTHERSHIP
assert MOTHERSHIP != "test.py"
print("MOTHERSHIP:", MOTHERSHIP)

# Google
client = ndb.Client()


def http(url, data=None):
    if data:
        data = urllib.parse.urlencode(data).encode("ascii")
    request = urllib.request.Request(url, data=data)
    sslcontext = ssl.create_default_context(cafile=certifi.where())
    response = urllib.request.urlopen(request, context=sslcontext)
    return response.read().decode()


class TestServer(unittest.TestCase):
    def test_pages(self):
        urls = [
            "/cron/daily",
            "/cron/hourly",
            "/cron/minutely",
            "/cron/10minutely",
            "/",
            "/app",
            "/developer",
            "/developer/protocol",
            "/developer/myapps",
            "/developer/api",
            "/developer/validate",
            "/developer/prices",
            "/developer/billing",
            "/developer/protocol",
            "/blog",
            "/blog.rss",
            "/map",
        ]

        for url in urls:
            print(url)
            response = requests.get(MOTHERSHIP + url)
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    result = unittest.main(argv=["first-arg-is-ignored"], exit=False, failfast=True)
