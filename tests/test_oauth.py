import os
import time
import unittest
from ynlib.strings import Garbage
import requests
import typeworld.client
import urllib.parse

# Selenium
from selenium import webdriver

# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Flask
from flask import Flask, g, request, redirect
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


ORIGINAL_MOTHERSHIP = "https://type.world"
MOTHERSHIP = os.environ.get("TEST_MOTHERSHIP", ORIGINAL_MOTHERSHIP)
print("MOTHERSHIP", MOTHERSHIP)

app = Flask(__name__)
app.secret_key = Garbage(40)
app.config.update(SESSION_COOKIE_NAME="world.type.oauth2test")

print("Fetching passwords...")
OAUTH_TEST_CLIENTID = secret("OAUTH_TEST_CLIENTID")
OAUTH_TEST_CLIENTSECRET = secret("OAUTH_TEST_CLIENTSECRET")
print("Done")


class Form(dict):
    def get(self, key):
        if key in self:
            return self[key]
        else:
            return None


@app.before_request
def before_request_web():

    g.user = None

    # Set up form
    g.form = Form()
    for key in request.values:
        g.form[key] = request.values.get(key)

    # Initial setting of state
    if "state" not in flaskSession:
        flaskSession["state"] = Garbage(40)
        print("Initial setting of state to", flaskSession["state"])

    # Log in user
    if g.form.get("code") and g.form.get("state") and g.form.get("state") == flaskSession["state"]:

        # Get token with code
        getTokenResponse = requests.post(
            MOTHERSHIP + "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": g.form.get("code"),
                "redirect_uri": "http://127.0.0.1:5000",
                "client_id": OAUTH_TEST_CLIENTID,
                "client_secret": OAUTH_TEST_CLIENTSECRET,
            },
        ).json()

        # Redeem token for user data
        if getTokenResponse["status"] == "success":

            # Save token to session
            flaskSession["token"] = getTokenResponse["access_token"]
            flaskSession.modified = True

    if g.form.get("testcase") in (
        "no_clientid",
        "wrong_clientid",
        "correct_clientid",
        "wrong_response_type",
        "correct_response_type",
        "wrong_redirect_uri",
        "correct_redirect_uri",
        "wrong_authorization_scope",
        "correct_authorization_scope",
    ):
        flaskSession["token"] = None
        flaskSession.modified = True

    # Log in user
    if "token" in flaskSession and flaskSession["token"]:
        getUserDataResponse = requests.post(
            MOTHERSHIP + "/auth/userdata",
            headers={"Authorization": "Bearer " + flaskSession["token"]},
        ).json()

        # Create user if necessary and save token
        if getUserDataResponse["status"] == "success":
            g.user = getUserDataResponse


@app.route("/reset", methods=["GET", "POST"])
def reset():
    flaskSession["state"] = Garbage(40)
    print("Reset state to", flaskSession["state"])
    flaskSession.modified = True
    return redirect("/")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    flaskSession["token"] = None
    flaskSession.modified = True
    return redirect("/")


@app.route("/", methods=["GET", "POST"])
def index():

    # Bare URL
    loginURL = MOTHERSHIP + "/signin"

    # Test cases
    if g.form.get("testcase") == "no_clientid":
        pass

    elif g.form.get("testcase") == "wrong_clientid":
        loginURL += "?client_id=" + Garbage(40)

    elif g.form.get("testcase") == "correct_clientid":
        loginURL += "?client_id=" + OAUTH_TEST_CLIENTID

    elif g.form.get("testcase") == "wrong_response_type":
        loginURL += "?client_id=" + OAUTH_TEST_CLIENTID + "&response_type=unknown"

    elif g.form.get("testcase") == "correct_response_type":
        loginURL += "?client_id=" + OAUTH_TEST_CLIENTID + "&response_type=code"

    elif g.form.get("testcase") == "wrong_redirect_uri":
        loginURL += (
            "?client_id="
            + OAUTH_TEST_CLIENTID
            + "&response_type=code&redirect_uri="
            + urllib.parse.quote_plus("http://0.0.0.0:5000")
        )

    elif g.form.get("testcase") == "correct_redirect_uri":
        loginURL += (
            "?client_id="
            + OAUTH_TEST_CLIENTID
            + "&response_type=code&redirect_uri="
            + urllib.parse.quote_plus("http://127.0.0.1:5000")
        )

    elif g.form.get("testcase") == "wrong_authorization_scope":
        loginURL += (
            "?client_id="
            + OAUTH_TEST_CLIENTID
            + "&response_type=code&redirect_uri="
            + urllib.parse.quote_plus("http://127.0.0.1:5000")
            + "&scope=unknown"
        )

    elif g.form.get("testcase") == "correct_authorization_scope":
        loginURL += (
            "?client_id="
            + OAUTH_TEST_CLIENTID
            + "&response_type=code&redirect_uri="
            + urllib.parse.quote_plus("http://127.0.0.1:5000")
            + "&scope=account,billingaddress,euvatid"
        )

    else:

        loginURL += (
            "?client_id="
            + OAUTH_TEST_CLIENTID
            + "&response_type=code&redirect_uri="
            + urllib.parse.quote_plus("http://127.0.0.1:5000")
            + "&scope=account,billingaddress,euvatid&state="
            + flaskSession["state"]
        )

    html = "<html><body>"
    if g.user:
        html += f"Logged in as {g.user['userdata']['scope']['account']['data']['email']}"
        html += '<br /><a href="/account" name="accountButton">User Account</a>'
        html += '<br /><a href="/logout" name="logoutButton">Sign Out</a>'
        print(g.user)
    else:
        html += f'<a href="{loginURL}" name="loginButton">Sign In With Type.World</a>'

    html += "</body></html>"

    return html


def makeAccountLink(link):

    redirect_url = urllib.parse.quote_plus("http://127.0.0.1:5000/account")
    state = flaskSession["state"]

    if g.form.get("testcase") == "account_wrong_redirect_uri":
        redirect_url = urllib.parse.quote_plus("http://0.0.0.0:5000/account")
    elif g.form.get("testcase") == "account_wrong_client_id":
        link = link.replace("client_id=", "client_id=aaa")
    elif g.form.get("testcase") == "account_wrong_scope":
        link = link.replace("scope=", "scope=aaa")
    else:
        redirect_url = urllib.parse.quote_plus("http://127.0.0.1:5000/account")

    url = link + "&redirect_uri=" + redirect_url + "&state=" + state
    url = url.replace(ORIGINAL_MOTHERSHIP, MOTHERSHIP)
    print(g.form.get("testcase"), url)
    return url


@app.route("/account", methods=["GET", "POST"])
def account():

    html = "<html><body>"

    if g.user:
        print(g.user)
        html += f"<h1>Account for {g.user['userdata']['scope']['account']['data']['email']}</h1>"

        for scope in g.user["userdata"]["scope"]:
            html += f'<h3>{g.user["userdata"]["scope"][scope]["name"]}'
            if "edit_uri" in g.user["userdata"]["scope"][scope]:
                html += (
                    f' <a class="edit_button" name="edit_{scope}"'
                    f' href="{makeAccountLink(g.user["userdata"]["scope"][scope]["edit_uri"])}">Edit</a>'
                )
            html += "</h3>"

            html += "<p>"
            for value in g.user["userdata"]["scope"][scope]["data"]:
                if value not in ["country_code"]:
                    html += (
                        g.user["userdata"]["scope"][scope]["data"][value]
                        or '<span style="opacity: .5;">&lt;empty&gt;</span>'
                    )
                    html += "<br />"
            html += "</p>"

    else:
        html += 'You’re not logged in. <a href="/">Sign In</a>.'

    html += "</body></html>"

    return html


# https://www.cloudbees.com/blog/get-selenium-to-wait-for-page-load


def wait_for(condition_function):
    start_time = time.time()
    while time.time() < start_time + 5:
        if condition_function():
            return True

        else:
            time.sleep(0.1)
    raise Exception("Timeout waiting for {}".format(condition_function.__name__))


class wait_for_page_load(object):
    def __init__(self, browser):
        self.browser = browser

    def __enter__(self):
        # self.old_page = self.browser.find_element(By.TAG_NAME, "body")

        self.old_page = WebDriverWait(self.browser, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    def page_has_loaded(self):
        new_page = WebDriverWait(self.browser, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        return new_page.id != self.old_page.id

    def __exit__(self, *_):
        wait_for(self.page_has_loaded)


class TestFoo(flask_unittest.LiveTestCase):
    @classmethod
    def setup_class(cls):
        # Initiate the selenium webdriver

        cls.driver = webdriver.Safari()
        cls.root_url = "http://127.0.0.1:5000"
        cls.std_wait = WebDriverWait(cls.driver, 5)

        # Create Type.World user account
        cls.client = typeworld.client.APIClient(
            zmqSubscriptions=False,
            online=True,
            commercial=True,
            appID="world.type.app",
        )
        success, message = cls.client.deleteUserAccount("test1@type.world", "0123456789")

        # cls.driver.get(cls.root_url + "/reset")

    @classmethod
    def teardown_class(cls):
        # Quit the webdriver
        cls.driver.quit()

    def test_authorization_barelink(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=no_clientid")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Missing or unknown client_id", self.driver.page_source)

    def test_authorization_wrong_clientid(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=wrong_clientid")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Missing or unknown client_id", self.driver.page_source)

    def test_authorization_correct_clientid(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=correct_clientid")
        self.assertIn(OAUTH_TEST_CLIENTID, self.driver.page_source)
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Missing or unknown response_type", self.driver.page_source)

    def test_authorization_wrong_response_type(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=wrong_response_type")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Missing or unknown response_type", self.driver.page_source)

    def test_authorization_correct_response_type(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=correct_response_type")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Missing or unknown redirect_uri", self.driver.page_source)

    def test_authorization_wrong_redirect_uri(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=wrong_redirect_uri")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Missing or unknown redirect_uri", self.driver.page_source)

    def test_authorization_correct_redirect_uri(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=correct_redirect_uri")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Missing or unknown or unauthorized scope", self.driver.page_source)

    def test_authorization_wrong_authorization_scope(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=wrong_authorization_scope")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Missing or unknown or unauthorized scope", self.driver.page_source)

    def test_authorization_correct_authorization_scope(self):
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "?testcase=correct_authorization_scope")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Missing state", self.driver.page_source)

    # First complete successful run-through
    def test_authorization_complete(self):

        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url)
        self.assertIn("Sign In With Type.World", self.driver.page_source)

        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Type.World Sign-In (via OAuth UnitTest)", self.driver.page_source)

        # Create user account
        success, message = self.client.createUserAccount(
            "Test OAuth User", "test1@type.world", "0123456789", "0123456789"
        )
        self.assertTrue(success)

        # Log in
        email = self.driver.find_element(By.ID, "email")
        email.send_keys("test1@type.world")
        password = self.driver.find_element(By.ID, "password")
        password.send_keys("0123456789")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "loginButton").click()
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "authorizeTokenButton").click()
        self.assertNotIn("Reusing state is not allowed", self.driver.page_source)
        # with wait_for_page_load(self.driver):
        #     self.driver.find_element(By.NAME, "redirectButton").click()
        time.sleep(7)

        # Log in success
        self.assertIn("Logged in as test1@type.world", self.driver.page_source)

        # Log out
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign Out").click()

        # Start Over
        self.assertIn("Sign In With Type.World", self.driver.page_source)

        # Reusing state is not allowed
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Reusing state is not allowed", self.driver.page_source)

        # Reset state
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/reset")
        self.assertIn("Sign In With Type.World", self.driver.page_source)
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "redirectButton").click()

        # Log in success
        self.assertIn("Logged in as test1@type.world", self.driver.page_source)

        # User Account
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/account")
        self.assertIn("test1@type.world", self.driver.page_source)

        # Edit data
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "edit_billingaddress").click()
        self.assertIn("Reusing state is not allowed", self.driver.page_source)

        # Reset
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/reset")
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/account")
        self.assertIn("test1@type.world", self.driver.page_source)

        # Edit data
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "edit_billingaddress").click()
        self.assertIn("Edit my Type.World account", self.driver.page_source)

        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "returnButton").click()
        self.assertIn("test1@type.world", self.driver.page_source)

        # Test cases
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/account?testcase=account_wrong_redirect_uri")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "edit_billingaddress").click()
        self.assertIn("Missing or unknown redirect_uri", self.driver.page_source)

        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/account?testcase=account_wrong_client_id")
        with wait_for_page_load(self.driver):
            print("123", self.driver.page_source)
            self.driver.find_element(By.NAME, "edit_billingaddress").click()
        self.assertIn("Missing or unknown client_id", self.driver.page_source)

        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/account?testcase=account_wrong_scope")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "edit_billingaddress").click()
        self.assertIn("Missing or unknown or unauthorized scope", self.driver.page_source)

        # Delete user account
        success, message = self.client.deleteUserAccount("test1@type.world", "0123456789")
        self.assertTrue(success)


suite = flask_unittest.LiveTestSuite(app, timeout=60)
# suite.addTest(unittest.makeSuite(TestFoo))
unittest.TextTestRunner(verbosity=0).run(suite)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
