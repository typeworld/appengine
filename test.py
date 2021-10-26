# project

# other
import sys
import urllib.request
import urllib.parse
import ssl
import certifi
import unittest
from google.cloud import ndb
import typeworld.client

print(sys.version)

MOTHERSHIP = sys.argv[-1]
assert MOTHERSHIP != "test.py"
print(MOTHERSHIP)

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
    def test_cronsjobs(self):
        url = f"{MOTHERSHIP}/cron/daily"
        success, content, headers = typeworld.client.request(url)
        self.assertEqual(headers["status_code"], 200)

        url = f"{MOTHERSHIP}/cron/hourly"
        success, content, headers = typeworld.client.request(url)
        self.assertEqual(headers["status_code"], 200)

        url = f"{MOTHERSHIP}/cron/minutely"
        success, content, headers = typeworld.client.request(url)
        self.assertEqual(headers["status_code"], 200)

    def test_normalpages(self):
        urls = [
            "/",
            "/app",
            "/developer",
            "/developer/protocol",
            "/developer/endpoints",
            "/developer/api",
            "/developer/validate",
            "/developer/prices",
            "/developer/billing",
            "/developer/protocol",
            "/blog",
        ]

        for url in urls:
            success, content, headers = typeworld.client.request(MOTHERSHIP + url)
            self.assertEqual(headers["status_code"], 200)


if __name__ == "__main__":
    result = unittest.main(argv=["first-arg-is-ignored"], exit=False, failfast=True)
