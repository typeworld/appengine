# project
from flask.json import jsonify
import typeworldserver
from typeworldserver import classes, helpers

# other
from flask import g, abort, request, Response, redirect
import jwt
import datetime
import urllib.parse
import json
import time

typeworldserver.app.config["modules"].append("auth")


def getToken(app):
    return classes.OAuthToken.query(
        classes.OAuthToken.userKey == g.user.key,
        classes.OAuthToken.signinAppKey == app.key,
        classes.OAuthToken.oauthScopes == ",".join(sorted(g.form._get("scope").split(","))),
        classes.OAuthToken.revoked == False,  # noqa E712
    ).get()


def signin_authorization(app):

    incompleteUserData = g.user.oauth_incompleteUserData(g.form._get("scope").split(","))

    g.html.DIV(class_="content")

    g.html.H1()
    g.html.T(f'Authorize <span class="black">{app.name}</span>')
    g.html._H1()

    if g.form._get("redirected_from") == "email_verification":
        g.html.P()
        g.html.T(
            '<span class="material-icons-outlined">check_circle</span> Thank you for verifying your email address.'
        )
        g.html._P()

    else:
        g.html.P()
        g.html.T(
            f'<span class="material-icons-outlined">account_circle</span> Not you, {g.user.name}? <a'
            ' onclick="logout();">Switch&nbsp;Accounts.</a>'
        )
        g.html._P()

    # g.html.smallSeparator()

    g.html.P()
    g.html.T('<span class="material-icons-outlined">view_in_ar</span> ')
    g.html.T(
        f"I authorize <b>{app.name}</b> to access the following data of my Type.World account:"
        # ' This authorization canbe revoked at any time in the <a href="/account">User&nbsp;Account</a>.'
    )
    g.html._P()

    g.html.mediumSeparator()

    # Reduced Data
    g.html.DIV(class_="reduced_data")
    g.html.DIV(style="text-align: right;")
    g.html.T(
        "Show full data <a onclick=\"$('.reduced_data').hide(); $('.full_data').show();\">"
        '<span class="material-icons-outlined">toggle_off</span></a>'
    )
    g.html._DIV()
    g.user.editScopes(g.form._get("scope").split(","), False, app)
    g.html._DIV()  # .reduced_data

    # Complete Data, show this by default if there is a problem
    g.html.DIV(class_="full_data")
    g.html.DIV(style="text-align: right;")
    g.html.T(
        "Show full data <a onclick=\"$('.reduced_data').show(); $('.full_data').hide();\">"
        '<span class="material-icons-outlined">toggle_on</span></a>'
    )
    g.html._DIV()
    g.user.editScopes(g.form._get("scope").split(","), True, app)
    g.html._DIV()  # .full_data

    g.html.SCRIPT()
    if incompleteUserData:
        g.html.T("$('.reduced_data').hide(); $('.full_data').show();")
    else:
        g.html.T("$('.reduced_data').show(); $('.full_data').hide();")
    g.html._SCRIPT()

    g.html.mediumSeparator()

    g.html.DIV(class_="message warning incomplete_user_data")
    g.html.T(
        '<span class="material-icons-outlined">error_outline</span> Your data is incomplete.<br />Please add'
        f" the relevant data, as <b>{app.name}</b> requires it for its service."
    )
    g.html._DIV()  # .incomplete_user_data

    g.html.DIV(class_="clear")
    g.html.SPAN(class_="noAnimation floatleft incomplete_user_data", style="margin-right: 10px;")
    g.html.BUTTON(
        class_="button dead",
        type="submit",
        value="submit",
        name="authorizeTokenButton",
        onclick=(
            f"$(this).addClass('disabled'); authorizeOAuthToken('{g.form._get('client_id')}',"
            f" '{g.form._get('response_type')}', '{g.form._get('redirect_uri')}', '{g.form._get('scope')}',"
            f" '{g.form._get('state')}'); return false;"
        ),
    )
    g.html.T("Authorize")
    g.html._BUTTON()
    g.html._SPAN()

    g.html.SPAN(class_="noAnimation floatleft complete_user_data", style="margin-right: 10px;")
    g.html.BUTTON(
        class_="button",
        type="submit",
        value="submit",
        name="authorizeTokenButton",
        onclick=(
            f"$(this).addClass('disabled'); authorizeOAuthToken('{g.form._get('client_id')}',"
            f" '{g.form._get('response_type')}', '{g.form._get('redirect_uri')}', '{g.form._get('scope')}',"
            f" '{g.form._get('state')}'); return false;"
        ),
    )
    g.html.T("Authorize")
    g.html._BUTTON()
    g.html._SPAN()

    g.html.SPAN(class_="floatleft", style="margin-right: 10px;")
    g.html.A(class_="button secondary", href=g.form._get("redirect_uri"))
    g.html.T("Cancel")
    g.html._A()
    g.html._SPAN()
    g.html._DIV()  # .clear

    g.html._DIV()  # .content

    # Missing data
    if incompleteUserData:
        g.html.SCRIPT()
        g.html.T("$('.incomplete_user_data').show(); $('.complete_user_data').hide();")
        g.html._SCRIPT()
    else:
        g.html.SCRIPT()
        g.html.T("$('.incomplete_user_data').hide(); $('.complete_user_data').show();")
        g.html._SCRIPT()


@typeworldserver.app.route("/auth/authorize", methods=["POST"])
def auth_authorize():

    check, app = checkAuthorizationCredentialsForAuthorization()
    if check is not True:
        return check, 401

    # Check for valid state
    if not g.form._get("state"):
        return "Missing state", 401
    if g.form._get("state") == app.lastState:
        return "Reusing state is not allowed", 401

    # Create token
    token = classes.OAuthToken()
    token.userKey = g.user.key
    token.signinAppKey = app.key
    token.oauthScopes = ",".join(sorted(g.form._get("scope").split(",")))
    token.code = helpers.Garbage(40)
    payload = {
        # "exp": datetime.datetime.utcnow() + datetime.timedelta(days=0, seconds=5),
        "iat": datetime.datetime.utcnow(),
        "sub": g.user.getUUID(),
    }
    token.authToken = jwt.encode(payload, typeworldserver.secret("TYPE_WORLD_FLASK_SECRET_KEY"), algorithm="HS256")
    token.put()

    return "<script>location.reload();</script>"


def checkAuthorizationHeaderForToken():

    auth_header = request.headers.get("Authorization")
    if auth_header:
        auth_token = auth_header.split(" ")[1]
    else:
        auth_token = ""

    if not auth_token:
        response = {"status": "fail", "message": "Provide a valid auth token."}
        return False, response

    token = classes.OAuthToken.query(classes.OAuthToken.authToken == auth_token).get()
    if not token:
        response = {"status": "fail", "message": "Token couldn't be found"}
        return False, response

    if token and token.revoked:
        response = {"status": "fail", "message": "Token is revoked"}
        return False, response

    return True, token


@typeworldserver.app.route("/auth/userdata", methods=["POST"])
def auth_userdata():

    success, response = checkAuthorizationHeaderForToken()
    if not success:
        return jsonify(response), 401
    else:
        token = response

    app = token.getApp()
    payload = jwt.decode(auth_token, typeworldserver.secret("TYPE_WORLD_FLASK_SECRET_KEY"), algorithms=["HS256"])

    user = classes.User.query(classes.User.uuid == payload["sub"]).get()
    if not user:
        response = {"status": "fail", "message": "User is unknown"}
        return jsonify(response), 401

    response = user.rawJSONData(app, token.oauthScopes.split(","))
    response["status"] = "success"

    # Save last access time
    token.lastAccess = helpers.now()
    token.put()

    # return json.dumps(response), 200
    return Response(json.dumps(response), mimetype="application/json", status=200)


@typeworldserver.app.route("/auth/edituserdata", methods=["GET"])
def auth_edituserdata():

    # Check for valid client_id
    app = classes.SignInApp.query(classes.SignInApp.clientID == g.form._get("client_id")).get()
    if not app:
        return "Missing or unknown client_id", 401

    # State
    if g.form._get("state") == app.lastState:
        return "Reusing state is not allowed", 401

    # Check for valid scopes
    if g.form._get("scope") not in app.oauthScopesList():
        return "Missing or unknown or unauthorized scope", 401

    # Check for valid redirect_uri
    matchedURL = False
    for url in [x.strip() for x in app.redirectURLs.splitlines()]:
        if url:
            if urllib.parse.unquote_plus(g.form._get("redirect_uri")).startswith(url):
                matchedURL = True
                break
    if matchedURL is False:
        return "Missing or unknown redirect_uri", 401

    ########################

    scopes = g.form._get("scope").split(",")

    signin_header(app)

    # TODO:
    # Check if signed in user (g.user) is identical to token’s user

    g.html.DIV(class_="content")

    g.html.H1()
    g.html.T("Edit my Type.World account")
    g.html._H1()

    g.user.editScopes(scopes, True, app, rawDataLink=False)

    g.html.mediumSeparator()

    g.html.DIV(class_="message warning incomplete_user_data")
    g.html.T(
        '<span class="material-icons-outlined">error_outline</span> Your data is incomplete.<br />Please add'
        f" the relevant data, as <b>{app.name}</b> requires it for its service."
    )
    g.html._DIV()  # .incomplete_user_data

    g.html.DIV(class_="clear complete_user_data")
    g.html.SPAN(class_="floatleft", style="margin-right: 10px;")
    g.html.A(
        name="returnButton",
        onclick="$(this).addClass('disabled')",
        class_="button",
        href=urllib.parse.unquote_plus(g.form._get("redirect_uri")),
    )
    g.html.T(f"Return to {app.name}")
    g.html._A()
    g.html._SPAN()
    g.html._DIV()  # .clear

    g.html.DIV(class_="clear incomplete_user_data")
    g.html.SPAN(class_="floatleft", style="margin-right: 10px;")
    g.html.A(name="returnButton", class_="button dead")
    g.html.T(f"Return to {app.name}")
    g.html._A()
    g.html._SPAN()
    g.html._DIV()  # .clear

    g.html._DIV()  # .content

    signin_footer(app)

    # Missing data
    if g.user.oauth_incompleteUserData(scopes):
        g.html.SCRIPT()
        g.html.T("$('.incomplete_user_data').show(); $('.complete_user_data').hide();")
        g.html._SCRIPT()
    else:
        g.html.SCRIPT()
        g.html.T("$('.incomplete_user_data').hide(); $('.complete_user_data').show();")
        g.html._SCRIPT()

    return g.html.GeneratePage()


@typeworldserver.app.route("/auth/revoketoken", methods=["POST"])
def auth_revoketoken():

    if not g.user:
        return abort(401)

    token = classes.OAuthToken.query(classes.OAuthToken.authToken == g.form._get("token")).get()
    if not token:
        return abort(401)

    token.revoked = True
    token.put()

    return "<script>location.reload();</script>"


@typeworldserver.app.route("/auth/token", methods=["POST"])
def auth_token():

    check, app, token = checkAuthorizationCredentialsForToken()
    if check is not True:
        return jsonify({"status": "fail", "message": check})

    response = {"status": "success", "access_token": token.authToken}
    return jsonify(response)


def signin_login(app):

    """
    Log In or Sign Up
    """

    g.html.DIV(class_="loginContent")
    g.html.DIV(class_="content")

    g.html.H1()
    g.html.T(f'Sign in to <span class="black">{app.name}</span>')
    g.html._H1()

    # Login form
    g.html.FORM()

    g.html.P()
    g.html.LABEL(for_="email")
    g.html.T("Email")
    g.html._LABEL()
    g.html.BR()
    g.html.INPUT(id="email", type="email", autocomplete="username", placeholder="johndoe@gmail.com")
    g.html._P()

    g.html.P()
    g.html.LABEL(for_="password")
    g.html.T("Password")
    g.html._LABEL()
    g.html.BR()
    g.html.INPUT(id="password", type="password", autocomplete="current-password")
    g.html._P()

    g.html.smallSeparator()

    g.html.DIV(class_="clear")
    g.html.SPAN(class_="noAnimation floatleft", style="margin-right: 10px;")
    g.html.BUTTON(
        class_="button",
        type="submit",
        value="submit",
        name="loginButton",
        onclick="$(this).addClass('disabled'); login($('#email').val(), $('#password').val()); return false;",
    )
    g.html.T("Sign In")
    g.html._BUTTON()
    g.html._SPAN()
    g.html.SPAN(class_="floatleft", style="margin-right: 10px;")
    g.html.A(class_="button secondary", href=g.form._get("redirect_uri"))
    g.html.T("Cancel")
    g.html._A()
    g.html._SPAN()
    g.html._DIV()  # .clear

    g.html._FORM()

    g.html._DIV()  # .content
    g.html.DIV(class_="supplemental")

    g.html.P()
    g.html.T('<span class="material-icons-outlined">password</span> ')
    g.html.A()
    g.html.T("Forgot password?")
    g.html._A()
    g.html.BR()
    g.html.T('<span class="material-icons-outlined">account_circle</span> New to Type.World? ')
    g.html.A(
        onclick=(
            "enableButtons(); $('.loginContent.noAnimation').hide(); $('.loginContent').slideUp();"
            " $('.createAccountContent.noAnimation').show(); $('.createAccountContent').slideDown();"
            " $('#createaccount-email').val($('#email').val());"
        )
    )
    g.html.T("Join Now.")
    g.html._A()
    g.html._P()

    g.html._DIV()  # .content
    g.html._DIV()  # .loginContent

    # Signup form
    g.html.DIV(class_="createAccountContent")
    g.html.DIV(class_="content")

    g.html.H1()
    g.html.T("Sign up for Type.World")
    g.html._H1()

    g.html.FORM()

    g.html.P()
    g.html.LABEL(for_="name")
    g.html.T("Name")
    g.html._LABEL()
    g.html.BR()
    g.html.INPUT(id="name", placeholder="John Doe")
    g.html._P()

    g.html.P()
    g.html.LABEL(for_="email")
    g.html.T("Email")
    g.html._LABEL()
    g.html.BR()
    g.html.INPUT(id="createaccount-email", type="email", autocomplete="username", placeholder="johndoe@gmail.com")
    g.html._P()

    g.html.P()
    g.html.LABEL(for_="newpassword")
    g.html.T("Password")
    g.html._LABEL()
    g.html.BR()
    g.html.INPUT(id="newpassword", type="password", autocomplete="new-password")
    g.html._P()

    g.html.P()
    g.html.LABEL(for_="newpassword2")
    g.html.T("Repeat Password")
    g.html._LABEL()
    g.html.BR()
    g.html.INPUT(id="newpassword2", type="password", autocomplete="new-password")
    g.html._P()

    g.html.smallSeparator()

    g.html.DIV(class_="clear")
    g.html.SPAN(class_="noAnimation floatleft", style="margin-right: 10px;")
    g.html.BUTTON(
        class_="button",
        type="submit",
        value="submit",
        name="createUserAccountButton",
        onclick=(
            "$(this).addClass('disabled'); createUserAccount($('#name').val(), $('#createaccount-email').val(),"
            " $('#newpassword').val(), $('#newpassword2').val(), 'email-verification'); return false;"
        ),
    )
    g.html.T("Create Account")
    g.html._BUTTON()
    g.html._SPAN()
    g.html.SPAN(class_="floatleft", style="margin-right: 10px;")
    g.html.A(class_="button secondary", href=g.form._get("redirect_uri"))
    g.html.T("Cancel")
    g.html._A()
    g.html._SPAN()
    g.html._DIV()  # .clear

    g.html._FORM()

    g.html._DIV()  # .content
    g.html.DIV(class_="supplemental")

    g.html.P()
    g.html.T('<span class="material-icons-outlined">account_circle</span> Already have an account? ')
    g.html.A(
        onclick=(
            "enableButtons(); $('.createAccountContent.noAnimation').hide(); $('.createAccountContent').slideUp();"
            " $('.loginContent.noAnimation').show(); $('.loginContent').slideDown();"
            " $('#email').val($('#createaccount-email').val());"
        )
    )
    g.html.T("Sign In.")
    g.html._A()
    g.html._P()

    g.html._DIV()  # .content
    g.html._DIV()  # .createAccountContent


def signin_emailverification(app):

    g.html.DIV(class_="content")

    redirectURL = (
        f"{g.rootURL}/signin?client_id={g.form._get('client_id')}"
        f"&response_type={g.form._get('response_type')}&redirect_uri={g.form._get('redirect_uri')}"
        f"&scope={g.form._get('scope')}&state={g.form._get('state')}&redirected_from=email_verification"
    )
    success, message = g.user.sendEmailVerificationLink(redirectURL)
    if not success:
        g.html.P()
        g.html.T("Sending email verification link: ")
        g.html.T(message)
        g.html._P()

    else:
        g.html.H1()
        g.html.T("Verify Your Email")
        g.html._H1()

        g.html.P()
        g.html.T(
            f"We’ve sent you an email to <b>{g.user.email}</b>.<br />"
            "Please follow the link in the email to verify your email address."
        )
        g.html._P()

        g.html.P()
        g.html.T("You may close this window/tab now.")
        g.html._P()

    g.html._DIV()  # .content


def signin_forward(app, token):

    check, app = checkAuthorizationCredentialsForAuthorization()
    if check is not True:
        return check, 401

    g.html.DIV(class_="content")

    token = getToken(app)
    url = f"{g.form._get('redirect_uri')}?code={token.code}&state={g.form._get('state')}"

    # Brand-new token or recent login
    if (
        token.created.timestamp() > time.time() - 15
        or g.user.lastLogin
        and g.user.lastLogin.timestamp() > time.time() - 15
    ):

        g.html.H1()
        g.html.T(f'You’re signed in to {app.name.replace(" ", "&nbsp;")}')
        g.html._H1()

        g.html.P()
        g.html.T(
            '<p>You’ll be sent back in <span id="counter">3</span></p><p><a'
            f' href="{url}">Click here</a> if nothing happens.</p>'
        )
        g.html._P()

        g.html.SCRIPT()
        g.html.T(
            """

    function countdown() {
        var i = document.getElementById('counter');
        if (parseInt(i.innerHTML)!=0) {
            i.innerHTML = parseInt(i.innerHTML)-1;
        }
        if (parseInt(i.innerHTML)<=0) {
            i.classList.add("blink");
            window.location.href = window.location.href + '&redirect=true';
            return false;
        }
        else {
            setTimeout(function(){ countdown(); },1000);
        }
    }
    setTimeout(function(){ countdown(); },1000);

        """
        )

        g.html._SCRIPT()

    # Old token, been logged in already
    else:

        g.html.H1()
        g.html.T(f"Sign in to {app.name.replace(' ', '&nbsp;')}")
        g.html._H1()

        g.html.P()
        g.html.T(
            f'<span class="material-icons-outlined">account_circle</span> Not you, {g.user.name}? <a'
            ' onclick="logout();">Switch&nbsp;Accounts.</a>'
        )
        g.html._P()

        g.html.mediumSeparator()

        g.html.DIV(class_="clear")
        g.html.SPAN(class_="noAnimation floatleft", style="margin-right: 10px;")
        g.html.BUTTON(
            class_="button",
            type="submit",
            value="submit",
            name="redirectButton",
            onclick="window.location.href = window.location.href + '&redirect=true'; return false;",
        )
        g.html.T("Sign In")
        g.html._BUTTON()
        g.html._SPAN()
        g.html.SPAN(class_="floatleft", style="margin-right: 10px;")
        g.html.A(class_="button secondary", href=g.form._get("redirect_uri"))
        g.html.T("Cancel")
        g.html._A()
        g.html._SPAN()
        g.html._DIV()  # .clear

    g.html._DIV()  # .content


# https://aaronparecki.com/oauth-2-simplified/


def checkAuthorizationCredentialsForToken():

    # Check for valid client_id
    app = classes.SignInApp.query(classes.SignInApp.clientID == g.form._get("client_id")).get()
    if not app:
        return "Missing or unknown client_id", app, None

    # Check for valid client_secret
    app = classes.SignInApp.query(classes.SignInApp.clientSecret == g.form._get("client_secret")).get()
    if not app:
        return "Missing or unknown client_secret", app, None

    # Check for valid grant_type
    if g.form._get("grant_type") != "authorization_code":
        return "Missing or unknown grant_type", app, None

    # Check for valid redirect_uri
    matchedURL = False
    for url in [x.strip() for x in app.redirectURLs.splitlines()]:
        if url:
            if g.form._get("redirect_uri").startswith(url):
                matchedURL = True
                break
    if matchedURL is False:
        return "Missing or unknown redirect_uri", app, None

    # Check for valid code
    token = classes.OAuthToken.query(classes.OAuthToken.code == g.form._get("code")).get()
    if not token:
        return "Missing or unknown code", app, None

    # Token is revoked
    if token.revoked:
        return "Token is revoked", app, token

    return True, app, token


def checkAuthorizationCredentialsForAuthorization():

    # Check for valid client_id
    app = classes.SignInApp.query(classes.SignInApp.clientID == g.form._get("client_id")).get()
    if not app:
        return "Missing or unknown client_id", app

    # Check for valid response_type
    if g.form._get("response_type") != "code":
        return "Missing or unknown response_type", app

    # Check for valid redirect_uri
    matchedURL = False
    for url in [x.strip() for x in app.redirectURLs.splitlines()]:
        if url:
            if g.form._get("redirect_uri") and g.form._get("redirect_uri").startswith(url):
                matchedURL = True
                break
    if matchedURL is False:
        return "Missing or unknown redirect_uri", app

    # Check for valid scope
    if g.form._get("scope") != ",".join(app.oauthScopesList()):
        return "Missing or unknown or unauthorized scope", app

    # State
    if not g.form._get("state"):
        return "Missing state", app
    if g.form._get("state") == app.lastState:
        return "Reusing state is not allowed", app

    return True, app


def signin_header(app):
    g.html.title = f"Type.World Sign-In (via {app.name})"

    g.html.JSLink("https://code.jquery.com/jquery-3.4.1.min.js")
    g.html.CSSLink("/static/css/default.css?v=" + g.instanceVersion)
    g.html.CSSLink("/static/css/typeworld.css?v=" + g.instanceVersion)
    g.html.CSSLink("/static/css/signin.css?v=" + g.instanceVersion)
    g.html.CSSLink("https://fonts.googleapis.com/icon?family=Material+Icons+Outlined")
    g.html.JSLink("/static/js/default.js?v=" + g.instanceVersion)

    g.html.DIV(id="action")
    g.html._DIV()

    g.html.DIV(id="dialog", class_="dialog centered widget")
    g.html.DIV(class_="dialogContent")
    g.html._DIV()
    g.html._DIV()

    g.html.DIV(class_="panelOuter")
    g.html.DIV(class_="panelMiddle")
    g.html.DIV(class_="panel")
    g.html.DIV(class_="header")
    g.html.IMG(src="/static/images/logo.svg", style="width: 80px; height: 80px; margin-bottom: 10px;")
    g.html.BR()
    g.html.T("Type.World Sign-In")
    g.html._DIV()  # .header


def signin_footer(app):

    g.html.DIV(class_="footer")
    g.html.P()
    g.html.T("<b>What is Type.World Sign-In?</b>")
    g.html._P()
    g.html.P()
    g.html.T(
        "<b>Type.World</b> is serving the font industry, best known for its open-source font installer app of the same"
        " name."
    )
    g.html._P()
    g.html.P()
    g.html.T(
        f"<b>{app.name}</b> uses the Type.World user accounts as a sign-in service to reduce the need for"
        " you to create separate user accounts for each font website or app that you use."
    )
    g.html._P()
    g.html.mediumSeparator()
    g.html.P()
    g.html.A(href="https://type.world/privacy", target="_blank", style="margin-right: 10px;")
    g.html.T("Privacy Policy")
    g.html._A()
    g.html.A(href="https://type.world/terms", target="_blank")
    g.html.T("Terms of Service")
    g.html._A()
    g.html._P()
    g.html._DIV()  # .footer

    g.html._DIV()  # .panel
    g.html._DIV()  # .panelMiddle
    g.html._DIV()  # .panelOuter


@typeworldserver.app.route("/signin", methods=["GET"])
def signin():

    check, app = checkAuthorizationCredentialsForAuthorization()
    if check is not True:
        g.html.T(check)
        return g.html.GeneratePage()

    ###

    ########################

    signin_header(app)

    if g.user:

        # Trigger email verification
        if not g.user.emailVerified:
            signin_emailverification(app)

        else:

            token = getToken(app)

            if token:

                # redirect
                if g.form._get("redirect") == "true":
                    url = f"{g.form._get('redirect_uri')}?code={token.code}&state={g.form._get('state')}"

                    # Save last state
                    app.lastState = g.form._get("state")
                    app.put()

                    return redirect(url)
                else:
                    signin_forward(app, token)
            else:
                signin_authorization(app)
    else:
        signin_login(app)

    signin_footer(app)

    return g.html.GeneratePage()
