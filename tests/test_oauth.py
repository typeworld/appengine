import os
import time
import unittest
from ynlib.strings import Garbage
import requests
import typeworld.client

# Selenium
from selenium import webdriver

# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.by import By

# Flask
from flask import Flask, g, request
from flask import session as flaskSession
import flask_unittest

# Google
from google.cloud import secretmanager

keyfile = os.path.join(os.path.dirname(__file__), "..", ".secrets", "typeworld2-b3ba737e9bbc.json")
secretClient = secretmanager.SecretManagerServiceClient.from_service_account_json(keyfile)


def secret(secret_id, version_id="latest"):
    """
    Access Google Cloud Secrets
    https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets#access
    """
    name = f"projects/889139710320/secrets/{secret_id}/versions/{version_id}"
    response = secretClient.access_secret_version(request={"name": name})
    payload = response.payload.data.decode("UTF-8")
    return payload


MOTHERSHIP = os.environ.get("TEST_MOTHERSHIP", "https://type.world")

app = Flask(__name__)
app.secret_key = Garbage(40)
app.config.update(SESSION_COOKIE_NAME="world.type.oauth2test")

print("Fetching passwords...")
OAUTH_TEST_CLIENTID = secret("OAUTH_TEST_CLIENTID")
OAUTH_TEST_CLIENTSECRET = secret("OAUTH_TEST_CLIENTSECRET")
print("Done")


class Form(dict):
    def _get(self, key):
        if key in self:
            return self[key]
        else:
            return None


@app.before_request
def before_request_web():
    g.form = Form()
    for key in request.values:
        g.form[key] = request.values.get(key)

    if "state" not in flaskSession:
        flaskSession["state"] = Garbage(40)


@app.route("/", methods=["GET", "POST"])
def index():

    # Bare URL
    loginURL = MOTHERSHIP + "/signin"

    # Test cases
    if g.form.get("testcase") == "wrong_clientid":
        loginURL += "?client_id=" + Garbage(40)

    elif g.form.get("testcase") == "correct_clientid":
        loginURL += "?client_id=" + OAUTH_TEST_CLIENTID

    elif g.form.get("testcase") == "wrong_response_type":
        loginURL += "?client_id=" + OAUTH_TEST_CLIENTID + "&response_type=unknown"

    elif g.form.get("testcase") == "correct_response_type":
        loginURL += "?client_id=" + OAUTH_TEST_CLIENTID + "&response_type=code"

    elif g.form.get("testcase") == "wrong_redirect_uri":
        loginURL += "?client_id=" + OAUTH_TEST_CLIENTID + "&response_type=code&redirect_uri=http://0.0.0.0"

    elif g.form.get("testcase") == "correct_redirect_uri":
        loginURL += "?client_id=" + OAUTH_TEST_CLIENTID + "&response_type=code&redirect_uri=http://127.0.0.1:5000"

    elif g.form.get("testcase") == "wrong_authorization_scope":
        loginURL += (
            "?client_id="
            + OAUTH_TEST_CLIENTID
            + "&response_type=code&redirect_uri=http://127.0.0.1:5000&scope=unknown"
        )

    elif g.form.get("testcase") == "correct_authorization_scope":
        loginURL += (
            "?client_id="
            + OAUTH_TEST_CLIENTID
            + "&response_type=code&redirect_uri=http://127.0.0.1:5000&scope=account,billingaddress,euvatid"
        )

    elif g.form.get("testcase") == "correct_state":
        loginURL += (
            "?client_id="
            + OAUTH_TEST_CLIENTID
            + "&response_type=code&redirect_uri=http://127.0.0.1:5000&scope=account,billingaddress,euvatid&state="
            + flaskSession["state"]
        )

    html = f"""

<a href="{loginURL}">Sign In With Type.World</a>





"""

    return html


# https://www.cloudbees.com/blog/get-selenium-to-wait-for-page-load


def wait_for(condition_function):
    start_time = time.time()
    while time.time() < start_time + 3:
        if condition_function():
            return True

        else:
            time.sleep(0.1)
    raise Exception("Timeout waiting for {}".format(condition_function.__name__))


class wait_for_page_load(object):
    def __init__(self, browser):
        self.browser = browser

    def __enter__(self):
        self.old_page = self.browser.find_element_by_tag_name("html")

    def page_has_loaded(self):
        new_page = self.browser.find_element_by_tag_name("html")
        return new_page.id != self.old_page.id

    def __exit__(self, *_):
        wait_for(self.page_has_loaded)


class TestFoo(flask_unittest.LiveTestCase):
    @classmethod
    def setup_class(cls):
        # Initiate the selenium webdriver

        cls.driver = webdriver.Safari()
        cls.root_url = "http://127.0.0.1:5000"
        cls.std_wait = WebDriverWait(cls.driver, 10)

        # Create Type.World user account
        cls.client = typeworld.client.APIClient(
            zmqSubscriptions=False,
            online=True,
            commercial=True,
            appID="world.type.app",
        )
        success, message = cls.client.deleteUserAccount("test1@type.world", "0123456789")

        # Wait for server to come online
        while True:
            try:
                requests.get(cls.root_url, timeout=1)
                break
            except ConnectionRefusedError:
                time.sleep(1)
        time.sleep(20)

    @classmethod
    def teardown_class(cls):
        # Quit the webdriver
        cls.driver.quit()

    def test_authorization_barelink(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url)
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_link_text("Sign In With Type.World").click()
        self.assertIn("Missing or unknown client_id", self.driver.page_source)

    def test_authorization_wrong_clientid(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=wrong_clientid")
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_link_text("Sign In With Type.World").click()
        self.assertIn("Missing or unknown client_id", self.driver.page_source)

    def test_authorization_correct_clientid(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=correct_clientid")
        self.assertIn(OAUTH_TEST_CLIENTID, self.driver.page_source)
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_link_text("Sign In With Type.World").click()
        self.assertIn("Missing or unknown response_type", self.driver.page_source)

    def test_authorization_wrong_response_type(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=wrong_response_type")
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_link_text("Sign In With Type.World").click()
        self.assertIn("Missing or unknown response_type", self.driver.page_source)

    def test_authorization_correct_response_type(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=correct_response_type")
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_link_text("Sign In With Type.World").click()
        self.assertIn("Missing or unknown redirect_uri", self.driver.page_source)

    def test_authorization_wrong_redirect_uri(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=wrong_redirect_uri")
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_link_text("Sign In With Type.World").click()
        self.assertIn("Missing or unknown redirect_uri", self.driver.page_source)

    def test_authorization_correct_redirect_uri(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=correct_redirect_uri")
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_link_text("Sign In With Type.World").click()
        self.assertIn("Missing or unknown or unauthorized scope", self.driver.page_source)

    def test_authorization_wrong_authorization_scope(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=wrong_authorization_scope")
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_link_text("Sign In With Type.World").click()
        self.assertIn("Missing or unknown or unauthorized scope", self.driver.page_source)

    def test_authorization_correct_authorization_scope(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=correct_authorization_scope")
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_link_text("Sign In With Type.World").click()
        self.assertIn("Missing state", self.driver.page_source)

    # First complete successful run-through
    def test_authorization_correct_state(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=correct_state")
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_link_text("Sign In With Type.World").click()
        self.assertIn("Type.World Sign-In (via OAuth UnitTest)", self.driver.page_source)

        success, message = self.client.createUserAccount(
            "Test OAuth User", "test1@type.world", "0123456789", "0123456789"
        )
        self.assertTrue(success)

        # Log in
        email = self.driver.find_element_by_id("email")
        email.send_keys("test1@type.world")
        password = self.driver.find_element_by_id("password")
        password.send_keys("0123456789")
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_name("loginButton").click()
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_name("authorizeTokenButton").click()
        time.sleep(10)

        # Delete user account
        success, message = self.client.deleteUserAccount("test1@type.world", "0123456789")
        self.assertTrue(success)


suite = flask_unittest.LiveTestSuite(app, timeout=60)
# suite.addTest(unittest.makeSuite(TestFoo))
unittest.TextTestRunner(verbosity=0).run(suite)
