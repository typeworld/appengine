# project
from flask.json import jsonify
import typeworldserver
from typeworldserver import classes, definitions, helpers

# other
from flask import g, abort


def signin_authorization(app):

    """
    Log In or Sign Up
    """

    g.html.H1()
    g.html.T(f'Authorize <span class="black">{app.name}</span>')
    g.html._H1()

    g.html.P()
    g.html.T(f"I authorize <b>{app.name}</b> to access the following data of my Type.World account:")
    g.html._P()

    g.html.mediumSeparator()

    for i, scope in enumerate(g.form._get("scope").split(",")):
        g.html.DIV(class_="scope")
        g.html.DIV(class_="head clear")
        g.html.DIV(class_="floatleft")
        g.html.T(f"{definitions.SIGNINSCOPES[scope]['name']}")
        g.html._DIV()  # .floatleft
        g.html.DIV(class_="floatright", style="font-size: inherit;")
        if g.user.oauthInfo()[scope]["editable"]:
            g.user.edit(propertyNames=g.user.oauthInfo()[scope]["editable"])
        g.html._DIV()  # .floatright
        g.html._DIV()  # .head
        g.html.DIV(class_="content")

        oauth = g.user.oauth(scope)
        for key in oauth:
            if key in g.user.oauthInfo()[scope]["fields"]:
                g.html.P(class_="label")
                g.html.T(g.user.oauthInfo()[scope]["fields"][key]["name"])
                g.html._P()
                g.html.P(class_="data")
                g.html.T(oauth[key] or '<span style="color: #777;">&lt;empty&gt;</span>')
                g.html._P()

        g.html._DIV()  # .content
        g.html._DIV()  # .scope

    g.html.smallSeparator()

    g.html.P()
    g.html.T('This authorization can be revoked at any time in the <a href="/account">User Account</a>.')
    g.html._P()

    g.html.smallSeparator()

    g.html.DIV(class_="clear")
    g.html.SPAN(class_="noAnimation floatleft", style="margin-right: 10px;")
    g.html.BUTTON(
        class_="button",
        type="submit",
        value="submit",
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


@typeworldserver.app.route("/auth/authorize", methods=["POST"])
def auth_authorize():

    check, app = checkAuthorizationCredentialsForAuthorization()
    if check is not True:
        g.html.T(check)
        return abort(401)

    # Create token
    token = classes.OAuthToken()
    token.userKey = g.user.key
    token.signinAppKey = app.key
    token.oauthScopes = ",".join(sorted(g.form._get("scope").split(",")))
    token.code = helpers.Garbage(40)
    token.put()

    # Save last state
    app.lastState = g.form._get("state")
    app.put()

    return "<script>location.reload();</script>"


@typeworldserver.app.route("/auth/token", methods=["POST"])
def auth_token():

    check, app, token = checkAuthorizationCredentialsForToken()
    if check is not True:
        return jsonify({"error": check})

    response = {"access_token": token.encode_auth_token()}
    return jsonify(response)


def signin_login(app):

    """
    Log In or Sign Up
    """

    g.html.H1()
    g.html.T(f'Sign in to <span class="black">{app.name}</span>')
    g.html._H1()

    # Login form
    g.html.DIV(class_="loginContent")
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

    g.html.smallSeparator()

    g.html.P()
    g.html.A()
    g.html.T("Forgot password?")
    g.html._A()
    g.html.BR()
    g.html.T("New to Type.World? ")
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

    g.html._DIV()  # .loginContent

    # Signup form
    g.html.DIV(class_="createAccountContent")
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
        onclick=(
            "$(this).addClass('disabled'); createUserAccount($('#name').val(), $('#createaccount-email').val(),"
            " $('#newpassword').val(), $('#newpassword2').val()); return false;"
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

    g.html.smallSeparator()

    g.html.P()
    g.html.T("Already have an account? ")
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

    g.html._DIV()  # .createAccountContent


def signin_forward(app, token):

    url = f"{g.form._get('redirect_uri')}?code={token.code}&state={g.form._get('state')}"

    g.html.T(
        f'<p>You will be redirected back to <b>{app.name}</b>.</p><p><a href="{url}">Click here</a> if nothing'
        " happens.</p>"
    )


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
    if g.form._get("redirect_uri") not in app.redirectURLs:
        return "Missing or unknown redirect_uri", app, None

    # Check for valid code
    token = classes.OAuthToken.query(classes.OAuthToken.code == g.form._get("code")).get()
    if not token:
        return "Missing or unknown code", app, None

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
    if g.form._get("redirect_uri") not in app.redirectURLs:
        return "Missing or unknown redirect_uri", app

    # Check for valid state
    if not g.form._get("state"):
        return "Missing state", app
    if g.form._get("state") == app.lastState:
        return "Reusing state is not allowed", app

    # Check for valid scope
    if g.form._get("scope") != ",".join(app.oauthScopesList()):
        return "Missing or unknown or unauthorized scope", app

    return True, app


def getToken(app):
    return classes.OAuthToken.query(
        classes.OAuthToken.userKey == g.user.key,
        classes.OAuthToken.signinAppKey == app.key,
        classes.OAuthToken.oauthScopes == ",".join(sorted(g.form._get("scope").split(","))),
    ).get()


@typeworldserver.app.route("/signin", methods=["GET"])
def signin():

    check, app = checkAuthorizationCredentialsForAuthorization()
    if check is not True:
        g.html.T(check)
        return g.html.GeneratePage()

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

    # Header
    g.html.DIV(class_="accountbar clear")
    g.html.DIV(class_="floatright")
    if g.user:
        g.html.SPAN(class_="link", style="color: #777")
        g.html.T(g.user.email)
        g.html._SPAN()
        g.html.SPAN(class_="link")
        g.html.A(href="/account")
        g.html.T('<span class="material-icons-outlined">account_circle</span> Account')
        g.html._A()
        g.html._SPAN()
        g.html.SPAN(class_="link")
        g.html.A(onclick="logout();")
        g.html.T('<span class="material-icons-outlined">logout</span> Log Out')
        g.html._A()
        g.html._SPAN()
    g.html._DIV()
    g.html._DIV()  # .clear

    g.html.DIV(class_="centered panel")
    g.html.DIV(class_="header")
    g.html.IMG(src="/static/images/logo.svg", style="width: 80px; margin-bottom: 10px;")
    g.html.BR()
    g.html.T("Type.World Sign-In")
    g.html._DIV()  # .header

    g.html.DIV(class_="content")

    if g.user:
        token = getToken(app)
        if token:
            signin_forward(app, token)
        else:
            signin_authorization(app)
    else:
        signin_login(app)

    g.html._DIV()  # .content

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

    return g.html.GeneratePage()
