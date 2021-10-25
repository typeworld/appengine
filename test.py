# project
import main

# other
import sys
import urllib.request
import urllib.parse
import ssl
import certifi
import unittest
from google.cloud import ndb

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
    def test_server(self):
        url = f"{MOTHERSHIP}/setBuildStatusChange/world.type.guiapp/windows/test"
        r = http(f"{url}?APPBUILD_KEY={main.secret('APPBUILD')}")
        self.assertEqual(r, "ok")

    def test_cronsjobs(self):
        url = f"{MOTHERSHIP}/cron/daily"
        r = http(url)
        self.assertEqual(r, "ok")

        url = f"{MOTHERSHIP}/cron/hourly"
        r = http(url)
        self.assertEqual(r, "ok")

        url = f"{MOTHERSHIP}/cron/minutely"
        r = http(url)
        print(r)
        self.assertEqual(r, "ok")


if __name__ == "__main__":
    result = unittest.main(argv=["first-arg-is-ignored"], exit=False, failfast=True)
