# import googlecloudprofiler

# # Profiler initialization. It starts a daemon thread which continuously
# # collects and uploads profiles. Best done as early as possible.
# try:
#     # service and service_version can be automatically inferred when
#     # running on App Engine. project_id must be set if not running
#     # on GCP.
#     googlecloudprofiler.start(verbose=3)
# except (ValueError, NotImplementedError) as exc:
#     print(exc)  # Handle errors here

###############################################################################

import datetime
import logging
import os
import time
import urllib
import urllib.parse

# Type.World
from google.cloud import ndb, storage
from google.cloud import secretmanager
from google.cloud import translate_v2
from flask import Flask, Response, g, redirect, request
from flask import session as flaskSession

logging.basicConfig(level=logging.WARNING)

# Google
GAE = os.getenv("GAE_ENV", "").startswith("standard")
if GAE:
    client = ndb.Client()
    secretClient = secretmanager.SecretManagerServiceClient()
    storage_client = storage.Client()
    translateClient = translate_v2.Client()

else:
    keyfile = os.path.join(
        os.path.dirname(__file__), "..", ".secrets", "typeworld2-b3ba737e9bbc.json"
    )
    client = ndb.Client.from_service_account_json(keyfile)
    secretClient = secretmanager.SecretManagerServiceClient.from_service_account_json(
        keyfile
    )
    storage_client = storage.Client.from_service_account_json(keyfile)
    translateClient = translate_v2.Client.from_service_account_json(keyfile)

if GAE:
    HTTPROOT = "https://type.world"

else:
    HTTPROOT = "http://0.0.0.0"

print(GAE, HTTPROOT)

# Google Cloud Storage
bucket = storage_client.bucket("typeworld2")


GAE = os.getenv("GAE_ENV", "").startswith("standard")
LIVE = GAE
STRIPELIVE = True  # LIVE
print("LIVE:", LIVE)
print("STRIPELIVE:", STRIPELIVE)

# Flask
global app


def ndb_wsgi_middleware(wsgi_app):
    def middleware(environ, start_response):
        """
        This is necessary for "testing" the app (such as internally routed
        calls from typworld module). It would complain about context being
        already initiated.
        """
        try:
            with client.context():
                return wsgi_app(environ, start_response)
        except:  # noqa E722
            return wsgi_app(environ, start_response)

    return middleware


def secret(secret_id, version_id="latest"):
    """
    Access Google Cloud Secrets
    https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets#access
    """
    name = f"projects/889139710320/secrets/{secret_id}/versions/{version_id}"
    response = secretClient.access_secret_version(request={"name": name})
    payload = response.payload.data.decode("UTF-8")
    return payload


app = Flask(__name__)
app.wsgi_app = ndb_wsgi_middleware(app.wsgi_app)  # Wrap the app in middleware.

app.secret_key = secret("TYPE_WORLD_FLASK_SECRET_KEY")
app.config["modules"] = ["__main__"]
app.config.update(SESSION_COOKIE_NAME="typeworld")


# Local imports
# happen here because of circular imports,
# as individual modules add to app.config["modules"]
#
# All sub-modules need to be loaded here, even if unused,
# as otherwise they are invisible to the @app router.
#
from . import api  # noqa: E402
from . import auth  # noqa: E402,F401
from . import billing_stripe  # noqa: E402,F401
from . import blog  # noqa: E402,F401
from . import classes  # noqa: E402
from . import definitions  # noqa: E402,F401
from . import developer  # noqa: E402,F401
from . import helpers  # noqa: E402
from . import hypertext  # noqa: E402
from . import mq  # noqa: E402,F401
from . import translations  # noqa: E402,F401
from . import web  # noqa: E402,F401


@app.before_first_request
def run_on_start():
    g.user = None
    g.admin = None
    g.session = None


@app.before_request
def before_request():

    # logging.warning("####################")

    # starttime = time.time()
    proto = (
        request.headers.get("X-Forwarded-Proto")
        or request.headers.get("proto")
        or "http"
    )
    if "type.world" in request.headers["Host"]:
        proto = "https"
    g.rootURL = f"{proto}://{request.headers['Host']}"

    if "GAE_VERSION" in os.environ:
        g.instanceVersion = os.environ["GAE_VERSION"]
    else:
        g.instanceVersion = str(int(time.time()))

    g.user = None
    g.admin = None
    g.session = None
    g.ndb_puts = []
    g.html = hypertext.HTML()

    # Init session
    if request.values.get("userAccountToken"):
        user = (
            classes.User.query()
            .filter(classes.User.websiteToken == request.values.get("userAccountToken"))
            .get(read_consistency=ndb.STRONG)
        )
        if user:
            performLogin(user)

    # Get user from edit_token
    if g.form.get("edit_token"):
        token = classes.OAuthToken.query(
            classes.OAuthToken.editCode == g.form.get("edit_token")
        ).get()
        if token:
            # Only attach user is token access is newer than an hour
            if token.lastAccess > datetime.datetime.now() - datetime.timedelta(hours=1):
                g.user = token.userKey.get()

    # Get user from session
    elif not g.user and "sessionID" in flaskSession:
        sessionID = flaskSession["sessionID"]
        if sessionID:

            g.session = ndb.Key(urlsafe=flaskSession["sessionID"].encode()).get(
                read_consistency=ndb.STRONG
            )

            # Init user
            if g.session:
                g.user = g.session.getUser()
                if not g.user:
                    g.session.key.delete()

    # Admin
    if g.user:
        g.admin = g.user.admin


@app.after_request
def after_request(response):

    if response.mimetype == "text/html":

        html = hypertext.HTML()

        if g.form._get("inline") == "true" or "</body>" in response.get_data().decode():

            # html.SCRIPT()
            # html.T(f"pushState(null, '{request.path}');")
            # html._SCRIPT()

            # print(request.path)

            pass

        else:

            response.direct_passthrough = False

            html.header()
            html.T("---replace---")
            html.footer()

            html = html.GeneratePage()
            html = html.replace("---replace---", response.get_data().decode())
            response.set_data(html)

    # logging.warning('finished after_request() in %.2f s' % (time.time() - starttime))

    if g.ndb_puts:
        ndb.put_multi(g.ndb_puts)
        for object in g.ndb_puts:
            object._cleanupPut()
        g.ndb_puts = []

    return response


@app.route("/", methods=["GET", "POST"])
def index():
    """Return a friendly HTTP greeting."""

    g.html.DIV(class_="content", style="width: 800px;")

    g.html.H1()
    g.html.T("Welcome to Type.World, the One-Click Font Installer")
    g.html._H1()
    g.html.P()
    g.html.IMG(src="/static/images/keyvisual.svg")
    g.html._P()

    g.html.H2()
    g.html.T("1. One-Click Install")
    g.html._H2()
    g.html.P()
    g.html.T(
        "Once you’ve downloaded and installed the app, you can one-click-install fonts"
        " from participating foundries. Either directly from their website (for example"
        " after purchasing a font), or you get invited by your colleagues to share"
        " fonts."
    )
    g.html._P()

    g.html.H2()
    g.html.T("2. Receive Font Updates")
    g.html._H2()
    g.html.P()
    g.html.T(
        "Whenever a publisher issues updates of fonts that you own, you will receive an"
        " update notification through the app and can update all of them at once."
    )
    g.html._P()

    g.html.H2()
    g.html.T("3. Back Up & Restore")
    g.html._H2()
    g.html.P()
    g.html.T(
        "Automatically back up all your font subscriptions to your Type.World user"
        " account. Restoring them all after you lost or crashed your computer is as"
        " easy as re-downloading the app and logging in."
    )
    g.html._P()
    g.html.P()
    g.html.T(
        "<em>User accounts are mandatory for so-called <em>protected</em> fonts, such"
        " as commercial retail fonts.</em>"
    )
    g.html._P()

    g.html.H2()
    g.html.T("4. Invite Colleagues")
    g.html._H2()
    g.html.P()
    g.html.T(
        "In order to collaborate on projects, you may invite your colleagues to share"
        " your fonts, as far as the seat allowance of your font license goes. Your"
        " colleagues need to sport their own Type.World user account."
    )
    g.html._P()

    g.html.P()
    g.html.T("<em>Requires a Pro user account.</em>")
    g.html._P()

    g.html.mediumSeparator()

    g.html.P(style="text-align: center;")
    g.html.A(class_="button", href="/app")
    g.html.T('<span class="material-icons-outlined">download</span> Download App')
    g.html._A()
    g.html._P()

    g.html.separator()

    g.html.DIV(class_="clear", style="width: 100%;")

    g.html.DIV(
        class_="floatleft", style="width: 50%; background-color: white; height: 600px;"
    )
    g.html.DIV(style="padding-left: 30px; padding-right: 10px; padding-top: 20px;")
    g.html.H1(style="margin-top: 0px;")
    # g.html.H2(style="text-align: center;")
    g.html.T("Free")
    g.html._H1()
    g.html.P()
    g.html.T("Basic usage of the Type.World App is free, which includes:")
    g.html._P()
    g.html.UL()
    g.html.LI()
    g.html.T("Install fonts and receive font updates")
    g.html._LI()
    g.html.LI()
    g.html.T(
        "Gather font subscriptions in a Type.World user account & easily restore them"
        " after a computer crash"
    )
    g.html._LI()
    g.html.LI()
    g.html.T(
        "Get invited to share font subscriptions (notification by <b>email</b> only)"
    )
    g.html._LI()
    g.html._UL()
    g.html._DIV()
    g.html._DIV()  # .floatleft

    g.html.DIV(
        class_="floatleft",
        style="width: 50%; background-color: #00FFA8; margin-top: 20px; height: 560px;",
    )
    g.html.DIV(style="padding-left: 30px; padding-right: 10px; padding-top: 20px;")
    g.html.H1(style="margin-top: 0px;")
    # g.html.H2(style="text-align: center;")
    g.html.T("Pro")
    g.html._H1()
    g.html.P()
    g.html.T("Become a Pro user to enjoy these features:")
    g.html._P()
    g.html.UL()
    g.html.LI()
    g.html.T("Share font subscriptions with colleagues")
    g.html._LI()
    g.html.LI()
    g.html.T("Sync one Type.World user account across several computers")
    g.html._LI()
    g.html.LI()
    g.html.T("Get invited to share font subscriptions with <b>live</b> notifications")
    g.html._LI()
    g.html.LI()
    g.html.T("Support future development of Type.World")
    g.html._LI()
    g.html._UL()

    g.html.smallSeparator()

    g.html.P(style="text-align: center;")
    g.html.T("Just <b>1&hairsp;€ per month</b>, billed yearly")
    g.html.BR()
    g.html.T("30 days free trial period")
    g.html._P()

    if g.user:
        g.html.P(style="text-align: center;")
        g.html.A(class_="button", href="/account")
        g.html.T(
            '<span class="material-icons-outlined">account_circle</span> See User'
            " Account To Sign Up For Pro"
        )
        g.html._A()
        g.html._P()

    else:
        g.html.P(style="text-align: center;")
        g.html.A(class_="button", onclick="showLogin();")
        g.html.T('<span class="material-icons-outlined">login</span> Log In')
        g.html._A()
        g.html.BR()
        g.html.A(class_="button", onclick="showCreateUserAccount();")
        g.html.T(
            '<span class="material-icons-outlined">account_circle</span> Create Account'
        )
        g.html._A()
        g.html._P()

    g.html._DIV()
    g.html._DIV()  # .floatleft

    g.html._DIV()  # .clear

    g.html.H1()
    g.html.T("Relationships")
    g.html._H1()
    g.html.P()
    g.html.IMG(
        src="/static/images/relationship.svg",
        style="width: 70%; margin-left: auto; margin-right: auto;",
    )
    g.html._P()

    # g.html.H2()
    # g.html.T("1. One-Click Install")
    # g.html._H2()
    g.html.P()
    g.html.T(
        "The Type.World App is designed around around the principle of"
        " <b>decentrality</b>. "
    )
    g.html._P()
    g.html.P()
    g.html.T(
        "The fonts are <b>distributed directly</b> from the publisher’s servers to the"
        " user’s app. Other than downloading and using the app and its user account,"
        " users never interact with Type.World directly, only with the font publishers."
    )
    g.html._P()
    g.html.P()
    g.html.T(
        "The app only ever calls its own servers to handle the Type.World <b>user"
        " accounts</b>, which help users organize their various font subscriptions.<br"
        " />A user account is not required to handle free fonts. It is required,"
        " however, for so called <b>protected fonts</b>, such as commercial retail"
        " fonts, for a streamlined user experience around losing or crashing your"
        " computer. A re-installation of all your commercial fonts would affect the"
        " licenses that you hold, and through the user account you can deauthorize and"
        " free that old computer’s font licenses in one go."
    )
    g.html._P()

    g.html._DIV()

    return g.html.generate()


def performLogin(user):
    # Create session
    session = classes.Session()
    session.userKey = user.key
    session.putnow()

    g.user = user
    g.admin = g.user.admin

    flaskSession["sessionID"] = session.key.urlsafe().decode()


def performLogout():
    if g.session:
        g.session.key.delete()
    g.session = None
    g.user = None
    g.admin = False

    flaskSession.clear()


@app.route("/login", methods=["POST"])
def login():

    user = (
        classes.User.query()
        .filter(classes.User.email == request.values.get("username"))
        .get(read_consistency=ndb.STRONG)
    )

    if not user:
        return "<script>warning('Unknown user');</script>"

    if not user.checkPassword(request.values.get("password")):
        return "<script>warning('Wrong password');</script>"

    user.lastLogin = helpers.now()
    user.put()
    performLogin(user)
    return "<script>location.reload();</script>"


@app.route("/logout", methods=["POST"])
def logout():
    performLogout()
    return "<script>location.reload();</script>"


@app.route("/linkRedirect")
def linkRedirect():
    """
    Placeholder for future security features such as
    for checking for phishing attacks.
    """

    if request.values.get("url"):
        url = urllib.parse.unquote(request.values.get("url"))

        return redirect(url, code=302)
    else:
        raise ValueError("No url")


@app.route("/cron/daily", methods=["GET", "POST"])
def cron_daily():
    api.saveStatistics()
    api.billNonCumulativeMetrics()
    return Response("ok", mimetype="text/plain")


@app.route("/cron/hourly", methods=["GET", "POST"])
def cron_hourly():
    # saveBilling()
    return Response("ok", mimetype="text/plain")


@app.route("/cron/30minutely", methods=["GET", "POST"])
def cron_30minutely():
    return Response("ok", mimetype="text/plain")


@app.route("/cron/10minutely", methods=["GET", "POST"])
def cron_10minutely():
    return Response("ok", mimetype="text/plain")


@app.route("/cron/minutely", methods=["GET", "POST"])
def cron_minutely():
    return Response("ok", mimetype="text/plain")


@app.route("/privacy", methods=["POST", "GET"])
def privacy():
    g.html.DIV(class_="content")
    g.html.T(
        '<a href="https://www.iubenda.com/privacy-policy/43981672" class="iubenda-white'
        " no-brand iubenda-noiframe iubenda-embed iub-no-markup iubenda-noiframe"
        ' iub-body-embed" title="Privacy Policy">Privacy Policy</a><script'
        ' type="text/javascript">(function (w,d) {var loader = function () {var s ='
        ' d.createElement("script"), tag = d.getElementsByTagName("script")[0];'
        ' s.src="https://cdn.iubenda.com/iubenda.js";'
        " tag.parentNode.insertBefore(s,tag);};"
        ' if(w.addEventListener){w.addEventListener("load", loader, false);}else'
        ' if(w.attachEvent){w.attachEvent("onload", loader);}else{w.onload ='
        " loader;}})(window, document);</script>"
    )
    g.html._DIV()
    return g.html.generate()


@app.route("/cookies", methods=["POST", "GET"])
def cookies():
    g.html.DIV(class_="content")
    g.html.T(
        '<a href="https://www.iubenda.com/privacy-policy/43981672/cookie-policy"'
        ' class="iubenda-white no-brand iubenda-noiframe iubenda-embed iub-no-markup'
        ' iubenda-noiframe iub-body-embed" title="Cookie Policy">Cookie'
        ' Policy</a><script type="text/javascript">(function (w,d) {var loader ='
        ' function () {var s = d.createElement("script"), tag ='
        ' d.getElementsByTagName("script")[0];'
        ' s.src="https://cdn.iubenda.com/iubenda.js";'
        " tag.parentNode.insertBefore(s,tag);};"
        ' if(w.addEventListener){w.addEventListener("load", loader, false);}else'
        ' if(w.attachEvent){w.attachEvent("onload", loader);}else{w.onload ='
        " loader;}})(window, document);</script>"
    )
    g.html._DIV()
    return g.html.generate()


@app.route("/terms", methods=["POST", "GET"])
def terms():
    g.html.DIV(class_="content")
    g.html.T(
        '<a href="https://www.iubenda.com/terms-and-conditions/43981672"'
        ' class="iubenda-white no-brand iubenda-noiframe iubenda-embed iub-no-markup'
        ' iubenda-noiframe iub-body-embed" title="Terms and Conditions">Terms and'
        ' Conditions</a><script type="text/javascript">(function (w,d) {var loader ='
        ' function () {var s = d.createElement("script"), tag ='
        ' d.getElementsByTagName("script")[0];'
        ' s.src="https://cdn.iubenda.com/iubenda.js";'
        " tag.parentNode.insertBefore(s,tag);};"
        ' if(w.addEventListener){w.addEventListener("load", loader, false);}else'
        ' if(w.attachEvent){w.attachEvent("onload", loader);}else{w.onload ='
        " loader;}})(window, document);</script>"
    )
    g.html._DIV()
    return g.html.generate()


@app.route("/impressum", methods=["POST", "GET"])
def impressum():
    g.html.DIV(class_="content")
    g.html.T(
        """
<h1>Impressum</h1>

<p>
<b>Angaben gemäß § 5 TMG:</b><br />
Jan Gerner<br />
Altmobschatz 8<br />
01156 Dresden<br />
</p>

<p>
<b>Kontakt:</b><br />
Telefon: +49 (176) 24023268<br />
E-Mail: hello@type.world<br />
</p>

<p>
<b>Umsatzsteuer-ID:</b><br />
Umsatzsteuer-Identifikationsnummer<br />
gemäß §27 a Umsatzsteuergesetz:<br />
DE212651941<br />
</p>

<p>
<b>Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV:</b><br />
Jan Gerner<br />
Altmobschatz 8<br />
01156 Dresden<br />
</p>

"""
    )
    g.html._DIV()
    return g.html.generate()


@app.route("/about", methods=["POST", "GET"])
def about():
    g.html.DIV(class_="content")
    g.html.T(
        """
<h1>About Type.World</h1>

<p>
Type.World is currently developed by type designer and multi media artist
<a href='https://yanone.de'>Yanone</a>.
</p>

<p>
The Type.World App and future projects aim to improve both the user experience of
frequent font users as well as the market position of independent font foundries alike.
</p>

<p>
All code is open source, and is therefore open for discussion and contributions.
The central resource for developers is located at
<a href='https://type.world/developer'>type.world/developer</a>.
The code is hosted on <a href='http://github.com/typeworld'>Github</a>.
To contribute, please see <a href='https://type.world/developer#contribute'>here</a>.
</p>

<p>
Please visit the project on <a href='https://type.world'>type.world</a> and make sure
to follow <a href='https://twitter.com/typeDotWorld'>@typeDotWorld</a> on Twitter
for the latest developments.
</p>

<p>
Become our Patron on <a href='https://patreon.com/typeworld'>patreon.com/typeworld</a>.
</p>
</p>

"""
    )
    g.html._DIV()
    return g.html.generate()


# @app.errorhandler(500)
# def server_error(e):
#     logging.exception('An error occurred during a request.')
#     return """
#     An internal error occurred: <pre>{}</pre>
#     See logs for full stacktrace.
#     """.format(e), 500

if __name__ == "__main__":
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    app.run(host="0.0.0.0", port=8080, debug=False)
    # [END gae_python37_app]

print("READY...")
