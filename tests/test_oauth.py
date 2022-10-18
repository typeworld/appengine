import os
import time
import unittest
from ynlib.strings import Garbage
import requests
import typeworld.client
import urllib.parse

# Email
import re
import email
import imaplib


# Selenium
from selenium import webdriver

# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

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

SIGNINTEST_EMAIL = "signintest@type.world"
SIGNINTEST_ACCOUNT_PASSWORD = secret("SIGNINTEST_ACCOUNT_PASSWORD")
SIGNINTEST_EMAIL_PASSWORD = secret("SIGNINTEST_EMAIL_PASSWORD")
SIGNINTEST_EMAIL_SERVER = secret("SIGNINTEST_EMAIL_SERVER")


def delete_all_emails():

    # connect to the server and go to its inbox
    mail = imaplib.IMAP4_SSL(SIGNINTEST_EMAIL_SERVER)
    mail.login(SIGNINTEST_EMAIL, SIGNINTEST_EMAIL_PASSWORD)
    # we choose the inbox but you can select others
    mail.select("INBOX")

    # we'll search using the ALL criteria to retrieve
    # every message inside the inbox
    # it will return with its status and a list of ids
    status, data = mail.search(None, "ALL")
    # the list returned is a list of bytes separated
    # by white spaces on this format: [b'1 2 3', b'4 5 6']
    # so, to separate it first we create an empty list
    mail_ids = []
    # then we go through the list splitting its blocks
    # of bytes and appending to the mail_ids list
    for block in data:
        # the split function called without parameter
        # transforms the text or bytes into a list using
        # as separator the white spaces:
        # b'1 2 3'.split() => [b'1', b'2', b'3']
        mail_ids += block.split()

    # define the range for the operation
    # start = mail_ids[0].decode()
    # end = mail_ids[-1].decode()

    # mark the emails to be deleted
    if mail_ids:
        mail.store("1:*", "+FLAGS", "\\Deleted")

        # remove permanently the emails
        mail.expunge()

    # close the mailboxes
    mail.close()
    # close the connection
    mail.logout()

    return True


def number_of_emails():

    # connect to the server and go to its inbox
    mail = imaplib.IMAP4_SSL(SIGNINTEST_EMAIL_SERVER)
    mail.login(SIGNINTEST_EMAIL, SIGNINTEST_EMAIL_PASSWORD)
    # we choose the inbox but you can select others
    mail.select("INBOX")

    # we'll search using the ALL criteria to retrieve
    # every message inside the inbox
    # it will return with its status and a list of ids
    status, data = mail.search(None, "ALL")
    # the list returned is a list of bytes separated
    # by white spaces on this format: [b'1 2 3', b'4 5 6']
    # so, to separate it first we create an empty list
    mail_ids = []
    # then we go through the list splitting its blocks
    # of bytes and appending to the mail_ids list
    for block in data:
        # the split function called without parameter
        # transforms the text or bytes into a list using
        # as separator the white spaces:
        # b'1 2 3'.split() => [b'1', b'2', b'3']
        mail_ids += block.split()

    # define the range for the operation
    # start = mail_ids[0].decode()
    # end = mail_ids[-1].decode()

    # close the mailboxes
    mail.close()
    # close the connection
    mail.logout()

    return len(mail_ids)


def print_all_emails():
    # connect to the server and go to its inbox
    mail = imaplib.IMAP4_SSL(SIGNINTEST_EMAIL_SERVER)
    mail.login(SIGNINTEST_EMAIL, SIGNINTEST_EMAIL_PASSWORD)
    # we choose the inbox but you can select others
    mail.select("INBOX")

    # we'll search using the ALL criteria to retrieve
    # every message inside the inbox
    # it will return with its status and a list of ids
    status, data = mail.search(None, "ALL")
    # the list returned is a list of bytes separated
    # by white spaces on this format: [b'1 2 3', b'4 5 6']
    # so, to separate it first we create an empty list
    mail_ids = []
    # then we go through the list splitting its blocks
    # of bytes and appending to the mail_ids list
    for block in data:
        # the split function called without parameter
        # transforms the text or bytes into a list using
        # as separator the white spaces:
        # b'1 2 3'.split() => [b'1', b'2', b'3']
        mail_ids += block.split()

    # now for every id we'll fetch the email
    # to extract its content
    for i in mail_ids:
        # the fetch function fetch the email given its id
        # and format that you want the message to be
        status, data = mail.fetch(i, "(RFC822)")

        # the content data at the '(RFC822)' format comes on
        # a list with a tuple with header, content, and the closing
        # byte b')'
        for response_part in data:
            # so if its a tuple...
            if isinstance(response_part, tuple):
                # we go for the content at its second element
                # skipping the header at the first and the closing
                # at the third
                message = email.message_from_bytes(response_part[1])

                # with the content we can extract the info about
                # who sent the message and its subject
                mail_from = message["from"]
                mail_subject = message["subject"]

                # then for the text we have a little more work to do
                # because it can be in plain text or multipart
                # if its not plain text we need to separate the message
                # from its annexes to get the text
                if message.is_multipart():
                    mail_content = ""

                    # on multipart we have the text message and
                    # another things like annex, and html version
                    # of the message, in that case we loop through
                    # the email payload
                    for part in message.get_payload():
                        # if the content type is text/plain
                        # we extract it
                        if part.get_content_type() == "text/plain":
                            mail_content += part.get_payload()
                else:
                    # if the message isn't multipart, just extract it
                    mail_content = message.get_payload()

                # and then let's show its result
                print(f"From: {mail_from}")
                print(f"Subject: {mail_subject}")
                print(f"Content: {mail_content}")

    # close the mailboxes
    mail.close()
    # close the connection
    mail.logout()


def get_first_email():
    # connect to the server and go to its inbox
    mail = imaplib.IMAP4_SSL(SIGNINTEST_EMAIL_SERVER)
    mail.login(SIGNINTEST_EMAIL, SIGNINTEST_EMAIL_PASSWORD)
    # we choose the inbox but you can select others
    mail.select("INBOX")

    # we'll search using the ALL criteria to retrieve
    # every message inside the inbox
    # it will return with its status and a list of ids
    status, data = mail.search(None, "ALL")
    # the list returned is a list of bytes separated
    # by white spaces on this format: [b'1 2 3', b'4 5 6']
    # so, to separate it first we create an empty list
    mail_ids = []
    # then we go through the list splitting its blocks
    # of bytes and appending to the mail_ids list
    for block in data:
        # the split function called without parameter
        # transforms the text or bytes into a list using
        # as separator the white spaces:
        # b'1 2 3'.split() => [b'1', b'2', b'3']
        mail_ids += block.split()

    # now for every id we'll fetch the email
    # to extract its content
    for i in reversed(mail_ids):
        # the fetch function fetch the email given its id
        # and format that you want the message to be
        status, data = mail.fetch(i, "(RFC822)")

        # the content data at the '(RFC822)' format comes on
        # a list with a tuple with header, content, and the closing
        # byte b')'
        for response_part in data:
            # so if its a tuple...
            if isinstance(response_part, tuple):
                # we go for the content at its second element
                # skipping the header at the first and the closing
                # at the third
                message = email.message_from_bytes(response_part[1])

                # with the content we can extract the info about
                # who sent the message and its subject
                # mail_from = message["from"]
                # mail_subject = message["subject"]

                # then for the text we have a little more work to do
                # because it can be in plain text or multipart
                # if its not plain text we need to separate the message
                # from its annexes to get the text
                if message.is_multipart():
                    mail_content = ""

                    # on multipart we have the text message and
                    # another things like annex, and html version
                    # of the message, in that case we loop through
                    # the email payload
                    for part in message.get_payload():
                        # if the content type is text/plain
                        # we extract it
                        if part.get_content_type() == "text/plain":
                            mail_content += part.get_payload()
                else:
                    # if the message isn't multipart, just extract it
                    mail_content = message.get_payload()

                # close the mailboxes
                mail.close()
                # close the connection
                mail.logout()
                return mail_content
                # # and then let's show its result
                # print(f"From: {mail_from}")
                # print(f"Subject: {mail_subject}")
                # print(f"Content: {mail_content}")

    # close the mailboxes
    mail.close()
    # close the connection
    mail.logout()


# delete_all_emails()
# print_all_emails()


def return_first_email():

    while get_first_email() is None:
        time.sleep(1)

    return get_first_email()


def get_link():
    body = return_first_email()

    newline = r"(?:\n|\r\n?)"
    compiled = re.compile(
        rf"Please verify your email address by clicking on the following link:{newline}(.+?){newline}", re.MULTILINE
    )
    match = compiled.search(body)
    return match.group(1).strip()


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

    url = link + "&state=" + state
    url = url.replace("__place_for_redirect_uri__", redirect_url)
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
            time.sleep(0.2)
    raise Exception("Timeout waiting for {}".format(condition_function.__name__))


# class wait_for_page_load(object):
#     def __init__(self, browser):
#         self.browser = browser

#     def __enter__(self):
#         # self.old_page = self.browser.find_element(By.TAG_NAME, "body")

#         self.old_page = WebDriverWait(self.browser, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

#     def page_has_loaded(self):
#         new_page = WebDriverWait(self.browser, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
#         return new_page.id != self.old_page.id

#     def __exit__(self, *_):
#         wait_for(self.page_has_loaded)


class wait_for_page_load(object):
    def __init__(self, browser):
        self.browser = browser

    def __enter__(self):
        self.old_page = self.browser.find_element(By.TAG_NAME, "html")

    def page_has_loaded(self):
        time.sleep(0.1)
        new_page = self.browser.find_element(By.TAG_NAME, "html")
        return new_page.id != self.old_page.id

    def __exit__(self, *_):
        start_time = time.time()
        while time.time() < start_time + 10:
            if self.page_has_loaded():
                return True
            else:
                time.sleep(0.1)
        raise Exception("Timeout waiting for page load.")


class TestFoo(flask_unittest.LiveTestCase):
    @classmethod
    def setup_class(cls):
        # Initiate the selenium webdriver

        cls.driver = webdriver.Safari()
        cls.root_url = "http://127.0.0.1:5000"
        cls.std_wait = WebDriverWait(cls.driver, 5)

        # Create Type.World user account
        cls.client = typeworld.client.APIClient(
            zmqSubscriptions=False, online=True, commercial=True, appID="world.type.app", mothership=MOTHERSHIP + "/v1"
        )
        # success, message = cls.client.deleteUserAccount(SIGNINTEST_EMAIL, SIGNINTEST_ACCOUNT_PASSWORD)

        with wait_for_page_load(cls.driver):
            cls.driver.get(MOTHERSHIP)

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

        # Delete user account
        success, message = self.client.deleteUserAccount(SIGNINTEST_EMAIL, SIGNINTEST_ACCOUNT_PASSWORD)
        # self.assertTrue(success)

        self.assertTrue(delete_all_emails())
        self.assertEqual(number_of_emails(), 0)

        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url)
        self.assertIn("Sign In With Type.World", self.driver.page_source)

        with wait_for_page_load(self.driver):
            self.driver.find_element(By.LINK_TEXT, "Sign In With Type.World").click()
        self.assertIn("Type.World Sign-In (via OAuth UnitTest)", self.driver.page_source)

        # Create user account
        success, message = self.client.createUserAccount(
            "Test OAuth User",
            SIGNINTEST_EMAIL,
            SIGNINTEST_ACCOUNT_PASSWORD,
            SIGNINTEST_ACCOUNT_PASSWORD,
            {"redirected_from": "email-verification"},
        )
        self.assertTrue(success)

        # Log in
        email = self.driver.find_element(By.ID, "email")
        email.send_keys(SIGNINTEST_EMAIL)
        password = self.driver.find_element(By.ID, "password")
        password.send_keys(SIGNINTEST_ACCOUNT_PASSWORD)
        # self.driver.find_element(By.XPATH("//html")).click()
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "loginButton").click()

        # Wait for email link
        email_confirmation_link = get_link()
        print(email_confirmation_link)
        self.assertIn(MOTHERSHIP, email_confirmation_link)

        with wait_for_page_load(self.driver):
            self.driver.get(email_confirmation_link)
        self.assertNotIn("No user could be found to verify for this code.", self.driver.page_source)

        # Insert missing data
        # print(self.driver.page_source)
        # with wait_for_page_load(self.driver):
        time.sleep(2)
        self.driver.execute_script("document.getElementById('edit_billingaddress').scrollIntoView();")
        self.driver.execute_script("document.getElementById('edit_billingaddress').click();")
        # self.driver.find_element(By.ID, "edit_billingaddress").click()
        time.sleep(2)
        self.driver.find_element(By.ID, "dialogform_invoiceName").send_keys("Test User")
        self.driver.find_element(By.ID, "dialogform_invoiceStreet").send_keys("Downing Str 10")
        self.driver.find_element(By.ID, "dialogform_invoiceZIPCode").send_keys("01234")
        self.driver.find_element(By.ID, "dialogform_invoiceCity").send_keys("Kabul")
        self.driver.find_element(By.LINK_TEXT, "Save").click()
        time.sleep(3)

        # with wait_for_page_load(self.driver):
        self.driver.execute_script("document.getElementsByName('authorizeTokenButton')[1].click();")
        # self.driver.find_element(By.LINK_TEXT, "Authorize").click()
        # self.driver.find_element(By.NAME, "authorizeTokenButton").click()
        with wait_for_page_load(self.driver):
            self.assertNotIn("Reusing state is not allowed", self.driver.page_source)
        # with wait_for_page_load(self.driver):
        #     self.driver.find_element(By.NAME, "redirectButton").click()
        time.sleep(10)

        # Log in success
        self.assertIn(f"Logged in as {SIGNINTEST_EMAIL}", self.driver.page_source)

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
        time.sleep(10)

        # Log in success
        self.assertIn(f"Logged in as {SIGNINTEST_EMAIL}", self.driver.page_source)

        # User Account
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/account")
        self.assertIn(SIGNINTEST_EMAIL, self.driver.page_source)

        # Edit data
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "edit_billingaddress").click()
        self.assertIn("Reusing state is not allowed", self.driver.page_source)

        # Reset
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/reset")
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/account")
        self.assertIn(SIGNINTEST_EMAIL, self.driver.page_source)

        self.assertIn("Test User", self.driver.page_source)
        self.assertIn("Downing Str 10", self.driver.page_source)
        self.assertIn("01234", self.driver.page_source)
        self.assertIn("Kabul", self.driver.page_source)
        self.assertIn("Afghanistan", self.driver.page_source)

        # Edit data
        self.driver.find_element(By.NAME, "edit_billingaddress").click()
        with wait_for_page_load(self.driver):
            self.assertIn("Edit my Type.World account", self.driver.page_source)

        # Edit data here
        self.driver.execute_script("document.getElementById('edit_billingaddress').scrollIntoView();")
        self.driver.execute_script("document.getElementById('edit_billingaddress').click();")
        time.sleep(2)
        self.driver.find_element(By.ID, "dialogform_invoiceName").send_keys("Test User 2")
        self.driver.find_element(By.ID, "dialogform_invoiceStreet").send_keys("Downing Str 11")
        self.driver.find_element(By.ID, "dialogform_invoiceZIPCode").send_keys("01235")
        self.driver.find_element(By.ID, "dialogform_invoiceCity").send_keys("Kabull")
        self.driver.find_element(By.LINK_TEXT, "Save").click()
        time.sleep(3)

        # Return
        self.driver.find_element(By.NAME, "returnButton").click()
        with wait_for_page_load(self.driver):
            self.assertIn("Test User 2", self.driver.page_source)
            self.assertIn("Downing Str 11", self.driver.page_source)
            self.assertIn("01235", self.driver.page_source)
            self.assertIn("Kabull", self.driver.page_source)
            # self.assertIn("Afghanistan", self.driver.page_source)

        # Test cases
        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/account?testcase=account_wrong_redirect_uri")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "edit_billingaddress").click()
        self.assertIn("Missing or unknown redirect_uri", self.driver.page_source)

        with wait_for_page_load(self.driver):
            self.driver.get(self.root_url + "/account?testcase=account_wrong_scope")
        with wait_for_page_load(self.driver):
            self.driver.find_element(By.NAME, "edit_billingaddress").click()
        self.assertIn("Missing or unknown or unauthorized scope", self.driver.page_source)


suite = flask_unittest.LiveTestSuite(app, timeout=60)
# suite.addTest(unittest.makeSuite(TestFoo))
unittest.TextTestRunner(verbosity=0).run(suite)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
