# project
import sys
import os

# other
import copy
import unittest
from google.cloud import ndb

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typeworldserver import classes, web  # noqa E402
import typeworldserver  # noqa E402


# Google
client = ndb.Client()


class WebAppModelDelegate(object):
    def before__init__(self):
        pass

    def after__init__(self):
        pass


class ClassTest(classes.TWNDBModel):
    string = web.StringProperty()
    json = web.JsonProperty()


class TestNDB(unittest.TestCase):
    def test_ndb(self):
        with typeworldserver.app.app_context():
            with client.context():

                # Init
                print("Stage 1")
                test = ClassTest()
                self.assertTrue(test._contentCacheUpdated)
                self.assertEqual(test._changed, [])
                self.assertEqual(test.key, None)
                self.assertEqual(test._contentCache["string"], None)
                self.assertEqual(test._contentCache["json"], None)

                test.string = "ABC"
                test.json = {"test": "ABC"}

                # Put
                test._prepareToPut()
                self.assertTrue(test._contentCacheUpdated)
                self.assertEqual(test._changed, ["string", "json"])

                super(web.WebAppModel, test).put()
                self.assertTrue(test.key)

                test._cleanupPut()
                self.assertTrue(test._contentCacheUpdated)
                self.assertEqual(test._changed, [])
                self.assertEqual(test._contentCache["string"], "ABC")
                self.assertEqual(test._contentCache["json"], {"test": "ABC"})

                # Stage 2, get from DB
                print("Stage 2")
                key = copy.deepcopy(test.key)
                test = key.get(read_consistency=ndb.STRONG)
                self.assertTrue(test._contentCacheUpdated)
                self.assertEqual(test._changed, [])
                self.assertTrue(test.key)
                self.assertEqual(test.string, "ABC")
                self.assertEqual(test.json, {"test": "ABC"})
                self.assertEqual(test._contentCache["string"], "ABC")
                self.assertEqual(test._contentCache["json"], {"test": "ABC"})

                test.string = "DEF"
                test.json = {"test": "DEF"}
                self.assertEqual(test.string, "DEF")
                self.assertEqual(test.json, {"test": "DEF"})

                # Put
                test._prepareToPut()
                self.assertTrue(test._contentCacheUpdated)
                self.assertEqual(test._changed, ["string", "json"])

                super(web.WebAppModel, test).put()
                self.assertTrue(test.key)

                test._cleanupPut()
                self.assertTrue(test._contentCacheUpdated)
                self.assertEqual(test._changed, [])
                self.assertEqual(test._contentCache["string"], "DEF")
                self.assertEqual(test._contentCache["json"], {"test": "DEF"})

                test.key.delete()


if __name__ == "__main__":
    result = unittest.main(argv=["first-arg-is-ignored"], exit=False, failfast=True)
