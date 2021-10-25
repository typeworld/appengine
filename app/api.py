# project
import app
from app import mq
from app import definitions
from app import classes
from app import helpers

# other
from google.cloud import ndb
import logging
import typeworld
import time
import urllib
import re
import random
import json
import semver
import requests
from flask import abort, g, redirect, Response, request

app.app.config["modules"].append("api")


def verifyEmail(email):

    if email in definitions.KNOWNEMAILADDRESSES:
        return True

    response = requests.get(
        "https://api.mailgun.net/v4/address/validate",
        auth=("api", app.secret("MAILGUN_PRIVATEKEY")),
        params={"address": email},
    ).json()

    if response["result"] in ("deliverable", "unknown") and response["is_disposable_address"] is False:
        return True
    else:
        return False


a = 10


def getStat(domain="api"):
    month = time.strftime("%Y-%m")
    stat = classes.SystemStatistics.get_or_insert(month)  # get_or_insert
    keys = [domain]
    if domain == "api":
        keys.append("testing" if g.form._get("testing") == "true" else "live")
    stat.setDomain(keys)
    return stat


@app.app.route("/registerNewAPIEndpoint", methods=["POST"])
def registerNewAPIEndpoint():

    if not g.user:
        return abort(401)

    success, message = typeworld.client.urlIsValid(g.form._get("canonicalURL"))
    if not success:
        g.html.warning(message)
        return g.html.generate(), 900

    # Skipping this because server may not be reachable from here
    # success, message = twClient.getEndpointCommand(g.form._get('canonicalURL'))
    # if not success:
    # 	g.html.warning(message)
    # 	return g.html.generate(), 900

    endpoint = classes.APIEndpoint.get_or_insert(g.form._get("canonicalURL"))  # , read_consistency=ndb.STRONG

    if endpoint.userKey and endpoint.userKey != g.user.key:
        g.html.warning("This API Endpoint is already registered with another user account.")
        return g.html.generate(), 900

    endpoint.userKey = g.user.key
    endpoint.updateJSON()
    endpoint.put()

    if not g.form._get("dataContainer") and g.form._get("reloadURL"):
        g.html.SCRIPT()
        g.html.T(
            "AJAX('#stage', '%s');"
            % helpers.addAttributeToURL(urllib.parse.unquote(g.form._get("reloadURL")), "inline=true")
        )
        g.html._SCRIPT()

    return g.html.generate()


@app.app.route("/account", methods=["POST", "GET"])
def account():

    if not g.user:
        return redirect("/")

    # g.html.DIV(class_="tabs clear")
    # g.html.DIV(class_="tab selected")
    # g.html.T('<span class="material-icons-outlined">account_circle</span> General')
    # g.html._DIV()
    # g.html.DIV(class_="tab")
    # g.html.A(href="/account/developer")
    # g.html.T('<span class="material-icons-outlined">memory</span> Developer')
    # g.html._A()
    # g.html._DIV()
    # g.html._DIV()

    g.html.DIV(class_="content")

    g.html.area("Type.World Account")
    g.user.container("userAccountView")
    g.html._area()

    g.html.T('<script src="https://js.stripe.com/v3/"></script>')
    g.html.T('<script src="/static/js/billing-stripe.js?v=' + g.instanceVersion + '"></script>')

    g.html.area("Pro User Subscription")
    g.user.container(
        "accountSubscriptionsView",
        parameters={"products": ["world.type.professional_user_plan"]},
    )
    g.html._area()

    g.html._DIV()

    return g.html.generate()


@app.app.route("/addTestUserForAPIEndpoint", methods=["POST", "GET"])
def addTestUserForAPIEndpoint():

    # Security
    if not g.user:
        return abort(401)
    endpoint = classes.APIEndpoint.get_or_insert(g.form._get("canonicalURL"))  # , read_consistency=ndb.STRONG

    # Endpoint doesn't exist
    if not endpoint:
        return abort(404)
    # User doesn't hold endpoint
    if endpoint not in g.user.APIEndpoints():
        return abort(403)

    # Process
    testUsersForAPIEndpoint = endpoint.testUsers()
    testUsers = [x.userKey.get(read_consistency=ndb.STRONG) for x in testUsersForAPIEndpoint]

    if len(testUsers) >= definitions.AMOUNTTESTUSERSFORAPIENTPOINT:
        g.html.warning("Maximum amount of test users reached.")
        return g.html.generate()

    newUser = classes.User.query(classes.User.email == g.form._get("email")).get(read_consistency=ndb.STRONG)
    if not newUser:
        g.html.warning("User account doesn’t exist.")
        return g.html.generate()

    if newUser in testUsers:
        g.html.warning("User has already been added.")
        return g.html.generate()

    # Success:
    newTestUserForAPIEndpoint = classes.TestUserForAPIEndpoint(parent=endpoint.key, userKey=newUser.key)
    newTestUserForAPIEndpoint.put()

    if g.form._get("reloadURL"):
        g.html.SCRIPT()
        g.html.T(
            "AJAX('#stage', '%s');"
            % helpers.addAttributeToURL(urllib.parse.unquote(g.form._get("reloadURL")), "inline=true")
        )
        g.html._SCRIPT()

    return g.html.generate()


@app.app.route("/stat", defaults={"month": None}, methods=["GET", "POST"])
@app.app.route("/stat/<month>", methods=["GET", "POST"])
def statistics(month):

    if not g.admin:
        return abort(401)

    g.html.mediumSeparator()

    g.html.DIV(class_="content")

    g.html.area("Server")

    g.html.P()
    g.html.T(f"GAE: {app.GAE}")
    g.html.BR()
    g.html.T(f"LIVE: {app.LIVE}")
    g.html._P()

    g.html._area()

    allStats = classes.SystemStatistics.query().fetch(read_consistency=ndb.STRONG)
    allStats.sort(key=lambda x: x.key.id())

    g.html.area("Statistics")
    g.html.P()
    for stat in allStats:
        g.html.A(href=f"/statistics/{stat.key.id()}")
        g.html.T(stat.key.id())
        g.html._A()
        g.html.BR()
    g.html._P()
    g.html._area()

    if month:
        g.html.area(month)
        stat = classes.SystemStatistics.get_or_insert(month)

        g.html.PRE()
        g.html.T(json.dumps(stat.jsonStats, indent=4, sort_keys=True))
        g.html._PRE()

        g.html._area()

    g.html._DIV()

    return g.html.generate()


def billNonCumulativeMetrics():
    endpoints = classes.APIEndpoint.query().fetch()
    for endpoint in endpoints:
        if endpoint.user():
            endpoint.billNonCumulativeMetrics()


def saveStatistics():
    stat = getStat("statistics")
    stat.bump(["amountUsers"], equals=classes.User.query().count())
    stat.bump(["amountAPIEndpoint"], equals=classes.APIEndpoint.query().count())
    stat.put()
    return "done"


@app.app.route("/verifyemail/<code>", methods=["GET"])
def verifyemail(code):
    user = classes.User.query(classes.User.emailVerificationCode == code).get(read_consistency=ndb.STRONG)

    g.html.DIV(class_="content")
    if not user:
        g.html.T("No user could be found to verify for this code.")

    else:
        user.emailVerified = True
        user.emailVerificationCode = None
        user.email = user.emailToChange
        user.emailToChange = None
        user.putnow()
        user.propagateEmailChange()
        user.announceChange()
        g.html.T(
            "Your email address has been verified, thank you. You may close this and return to the Type.World App."
        )
    g.html._DIV()
    return g.html.generate()


@app.app.route("/v1/<commandName>", methods=["POST"])
def v1(commandName):

    # import cProfile

    # profile = cProfile.Profile()
    # profile.enable()

    # Log
    # stat = getStat()
    starttime = time.time()

    responses = {
        "response": "success",
    }

    testScenario = g.form._get("testScenario")

    if testScenario == "simulateCentralServerProgrammingError":
        assert ewrfgnorebg  # noqa F821

    if testScenario == "simulateCentralServerErrorInResponse":
        responses["response"] = "simulateCentralServerErrorInResponse"
        logging.warning("API Call Finished: %.2f s. Responses: %s" % (time.time() - starttime, responses))
        return Response(json.dumps(responses), mimetype="application/json")

    # Check if command exists
    if not commandName or commandName not in definitions.APICOMMANDS:
        responses["response"] = "commandUnknown"
        # stat.bump(['commandUnknown', '__undefined__'], 1)
        # stat.put()
        logging.warning("API Call Finished: %.2f s. Responses: %s" % (time.time() - starttime, responses))
        return Response(json.dumps(responses), mimetype="application/json")

    command = definitions.APICOMMANDS[commandName]

    print(
        "API Call: %s, Parameters: %s"
        % (
            commandName,
            ", ".join([f"{x}: {g.form._get(x)}" for x in list(command["parameters"])]),
        )
    )

    logging.warning(
        "API Call: %s, Parameters: %s"
        % (
            commandName,
            ", ".join([f"{x}: {g.form._get(x)}" for x in list(command["parameters"])]),
        )
    )

    # Version
    if (
        g.form._get("clientVersion")
        and "clientVersion" in command["parameters"]
        and command["parameters"]["clientVersion"]["required"] is True
    ):
        try:
            semver.parse(g.form._get("clientVersion"))
        except ValueError:
            responses["response"] = "clientVersionInvalid"
            # stat.bump(['clientVersionInvalid'], 1)
            # stat.put()
            logging.warning("API Call Finished: %.2f s. Responses: %s" % (time.time() - starttime, responses))
            return Response(json.dumps(responses), mimetype="application/json")
    # logging.warning('API Call %s after version was verified: %.2f s'
    # % (commandName, time.time() - starttime))

    parameterStrings = []
    for parameter in command["parameters"]:
        parameterStrings.append("%s=%s" % (parameter, g.form._get(parameter)))
        if command["parameters"][parameter]["required"] is True and not g.form._get(parameter):
            responses["response"] = "Required parameter %s is missing." % parameter
            # stat.bump(['command', commandName, 'failed', 'missingParameter',
            # parameter], 1)
            # stat.put()
            logging.warning(
                "API Call %s finished: %.2f s. Responses: %s" % (commandName, time.time() - starttime, responses)
            )
            return Response(json.dumps(responses), mimetype="application/json")
    # logging.warning('API Call %s after parameters were verified: %.2f s' %
    # (commandName, time.time() - starttime))

    # Call method
    if commandName in globals():
        globals()[commandName](responses)
        logging.warning("API Call %s after method was called: %.2f s" % (commandName, time.time() - starttime))
    else:
        responses["response"] = "commandUnknown"
        # stat.bump(['commandUnknown', commandName], 1)
        # stat.put()
        logging.warning(
            "API Call %s finished: %.2f s. Responses: %s" % (commandName, time.time() - starttime, responses)
        )
        return Response(json.dumps(responses), mimetype="application/json")

    # profile.disable()
    # profile.print_stats(sort="time")

    # stat.bump(['command', commandName, responses['response']], 1)
    # stat.put()
    logging.warning("API Call %s finished: %.2f s. Responses: %s" % (commandName, time.time() - starttime, responses))
    return Response(json.dumps(responses), mimetype="application/json")


def validateAPIEndpoint(responses):

    if g.instanceVersion:
        MOTHERSHIP = f"https://{g.instanceVersion}-dot-typeworld2.appspot.com/v1"
    else:
        MOTHERSHIP = "https://api.type.world/v1"

    profiles = g.form._get("profiles").split(",")
    import typeworld.tools.validator

    responses = typeworld.tools.validator.validateAPIEndpoint(
        g.form._get("subscriptionURL"),
        profiles,
        endpointURL=MOTHERSHIP,
        responses=responses,
    )


def linkTypeWorldUserAccount(responses):

    userKey = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
    if not userKey.id():
        responses["response"] = "userUnknown"
        return

    user = userKey.get(read_consistency=ndb.STRONG)

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"
        return

    elif (
        not user.stripeSubscriptionReceivesService("world.type.professional_user_plan")
        and len(user.appInstances()) == 1
    ):
        responses["response"] = "linkingMoreAppInstancesRequiresProUserAccount"
        return

    else:

        # Exists
        appInstance = classes.AppInstance(parent=userKey, id=g.form._get("anonymousAppID"))

        # Machine descriptor
        for keyword in (
            "machineModelIdentifier",
            "machineHumanReadableName",
            "machineSpecsDescription",
            "machineOSVersion",
            "machineNodeName",
        ):
            if g.form._get(keyword):
                setattr(appInstance, keyword, g.form._get(keyword))

        # AppEngine HTTP headers
        headers = dict(request.headers)
        for keyword in (
            "X-Appengine-City",
            "X-Appengine-Country",
            "X-Appengine-Region",
            "X-Appengine-Citylatlong",
        ):
            if keyword in headers:
                value = headers[keyword]
                if keyword == "X-Appengine-Citylatlong":
                    latitude, longitude = [float(x) for x in value.split(",")]
                    value = ndb.GeoPt(latitude, longitude)
                setattr(appInstance, keyword.replace("-", "_"), value)

        # Update timestamp
        appInstance.lastUsed = helpers.now()
        appInstance.put()

        responses["userEmail"] = user.email
        responses["userName"] = user.name

    print(user)
    print(user.appInstances())


def unlinkTypeWorldUserAccount(responses):

    if not g.form._get("anonymousUserID"):
        responses["response"] = "userUnknown"
        return

    k = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
    if not k.id() or not k.get(read_consistency=ndb.STRONG):
        responses["response"] = "userUnknown"
        return

    user = k.get(read_consistency=ndb.STRONG)

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"
        return

    else:

        deleted = False
        for appInstance in user.appInstances():
            if appInstance.key.id() == g.form._get("anonymousAppID"):
                appInstance.key.delete()
                deleted = True

        if not deleted:
            responses["response"] = "appInstanceUnknown"
            return


@ndb.transactional()
def createUserAccount(responses):

    previousUser = classes.User.query(classes.User.email == g.form._get("email")).get(read_consistency=ndb.STRONG)
    if previousUser:
        responses["response"] = "userExists"
        return

    # verify
    if verifyEmail(g.form._get("email")) is False:
        responses["response"] = "emailInvalid"
        return

    # actually create user
    user = classes.User()
    user.email = g.form._get("email")
    user.secretKey = helpers.Garbage(40)
    success, message = user.setPassword(g.form._get("password"))
    if not success:
        responses["response"] = message
        return
    user.name = g.form._get("name")

    # Email verification
    if g.form._get("SECRETKEY") == app.secret("TEST"):
        user.emailVerified = True
    else:
        user.emailToChange = g.form._get("email")
        user.sendEmailVerificationLink()
    user.put()

    responses["anonymousUserID"] = user.publicID()
    responses["secretKey"] = user.secretKey
    responses["name"] = user.name


@ndb.transactional()
def deleteUserAccount(responses):
    user = classes.User.query(classes.User.email == g.form._get("email")).get(read_consistency=ndb.STRONG)
    if user:
        if user.checkPassword(g.form._get("password")):
            # Delete

            # with client.transaction():
            user.key.delete()
            print("deleted key", user.key)

        else:
            responses["response"] = "passwordInvalid"
            return

    else:
        responses["response"] = "userUnknown"
        return

    user = classes.User.query(classes.User.email == g.form._get("email")).get(read_consistency=ndb.STRONG)
    if user:
        responses["response"] = "userStillExists"
        return


def logInUserAccount(responses):

    # time.sleep(5)

    user = classes.User.query(classes.User.email == g.form._get("email")).get(read_consistency=ndb.STRONG)
    if user:
        if user.checkPassword(g.form._get("password")):
            responses["anonymousUserID"] = user.publicID()
            responses["secretKey"] = user.secretKey
            responses["name"] = user.name

        else:
            responses["response"] = "passwordInvalid"
            return

    else:
        responses["response"] = "userUnknown"
        return


def versions(responses):
    responses["typeworld"] = typeworld.api.VERSION


def registerAPIEndpoint(responses):

    if typeworld.client.urlIsValid(g.form._get("url"))[0] is False:
        responses["response"] = "urlInvalid"
        return

    endpoint = classes.APIEndpoint.get_or_insert(g.form._get("url"))  # , read_consistency=ndb.STRONG
    updated, message = endpoint.updateJSON()
    if updated is True:
        endpoint.put()


def syncUserSubscriptions(responses):

    if not g.form._get("anonymousUserID"):
        responses["response"] = "userUnknown"
        return

    k = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
    if not k.id() or not k.get(read_consistency=ndb.STRONG):
        responses["response"] = "userUnknown"
        return
    user = k.get(read_consistency=ndb.STRONG)

    appInstance = classes.AppInstance.get_by_id(
        g.form._get("anonymousAppID"), parent=user.key, read_consistency=ndb.STRONG
    )

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"
        return

    elif not appInstance.key.id():
        responses["response"] = "appInstanceUnknown"
        return

    else:

        oldURLs = [x.url for x in user.regularSubscriptions() if x]
        if g.form._get("subscriptionURLs") != "empty":
            newURLs = g.form._get("subscriptionURLs").split(",")
        else:
            newURLs = []
        completeURLs = list(set(oldURLs) | set(newURLs))

        # Add new subscriptions
        for url in completeURLs:

            if url != "empty":

                # Save new subscription
                if url not in oldURLs:
                    subscription = classes.Subscription(parent=user.key)
                    subscription.url = url
                    subscription.putnow()

        # # Delete removed subscriptions
        # for subscription in appInstance.subscriptions():
        # 	if not subscription.get('url') in newURLs:
        # 		subscription.delete()

        responses["subscriptions"] = completeURLs

        # Update timestamp
        appInstance.lastUsed = helpers.now()
        appInstance.put()

        if user.stripeSubscriptionReceivesService("world.type.professional_user_plan"):
            if set(oldURLs) != set([x.url for x in user.regularSubscriptions() if x]):
                success, message = user.announceChange(g.form._get("sourceAnonymousAppID"))
                if not success:
                    responses["response"] = message
                    return


def uploadUserSubscriptions(responses):

    if not g.form._get("anonymousUserID"):
        responses["response"] = "userUnknown"
        return

    user = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode()).get(read_consistency=ndb.STRONG)
    if not user:
        responses["response"] = "userUnknown"
        return

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"
        return

    subscriptions = user.subscriptions()
    oldConfirmedSubscriptions = user.confirmedSubscriptions(subscriptions=subscriptions)
    oldConfirmedURLs = [x.url for x in oldConfirmedSubscriptions if x]
    oldUnsecretConfirmedURLs = [typeworld.client.URL(x).unsecretURL() for x in oldConfirmedURLs]
    oldUnconfirmedSubscriptions = user.unconfirmedSubscriptions(subscriptions=subscriptions)
    oldUnconfirmedURLs = [x.url for x in oldUnconfirmedSubscriptions if x]
    if g.form._get("subscriptionURLs") == "empty":
        newURLs = []
    else:
        newURLs = g.form._get("subscriptionURLs").split(",")
    # completeURLs = list(set(oldConfirmedURLs) | set(newURLs))
    changes = False

    # Add new subscriptions
    for url in newURLs:

        if url != "empty":

            # Change secret key
            if typeworld.client.URL(url).unsecretURL() in oldUnsecretConfirmedURLs:
                for subscription in oldConfirmedSubscriptions:
                    if typeworld.client.URL(subscription.url).unsecretURL() == typeworld.client.URL(url).unsecretURL():
                        subscription.url = url
                        subscription.putnow()
                        changes = True
                        break

            # Save new subscription
            elif url not in oldConfirmedURLs:

                # Update existing subscription (for instance elevate subscription
                # from pending invitation to confirmed)
                if url in oldUnconfirmedURLs:
                    for subscription in oldUnconfirmedSubscriptions:
                        if subscription.url == url:
                            subscription.type = ""
                            subscription.confirmed = True
                            subscription.invitedByUserKey = None
                            subscription.putnow()
                            changes = True
                            break

                # New subscription
                else:

                    subscription = classes.Subscription(parent=user.key)
                    subscription.url = url
                    subscription.confirmed = True
                    subscription.invitedByUserKey = None
                    subscription.putnow()
                    # subscription.rawSubscription()
                    changes = True

    # Delete
    for subscription in oldConfirmedSubscriptions:
        if subscription.url not in newURLs:

            success, message = subscription.sendDeletedEmail()
            if not success:
                responses["response"] = "sendDeletedEmail(): %s" % message
                return

            subscription.key.delete()
            changes = True

    # Update timestamp
    appInstance = classes.AppInstance.get_by_id(
        g.form._get("anonymousAppID"), parent=user.key, read_consistency=ndb.STRONG
    )
    if appInstance:
        appInstance.lastUsed = helpers.now()
        appInstance.put()

    if user.stripeSubscriptionReceivesService("world.type.professional_user_plan"):
        # if set(oldConfirmedURLs) != set([x.url for x in user.confirmedSubscriptions()
        #  if x]):
        if changes:
            success, message = user.announceChange(g.form._get("sourceAnonymousAppID"))
            if not success:
                responses["response"] = message
                return


def downloadUserSubscriptions(responses):

    k = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
    if not k.id():
        responses["response"] = "userUnknown"
        return
    user = k.get(read_consistency=ndb.STRONG)

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"
        return

    appInstance = classes.AppInstance.get_by_id(
        g.form._get("anonymousAppID"), parent=user.key, read_consistency=ndb.STRONG
    )

    if not appInstance or not appInstance.key.id():
        responses["response"] = "appInstanceUnknown"
        return

    else:

        responses["appInstanceIsRevoked"] = appInstance.revoked
        responses["userAccountEmailIsVerified"] = user.emailVerified
        responses["userAccountStatus"] = (
            "pro" if user.stripeSubscriptionReceivesService("world.type.professional_user_plan") else "normal"
        )

        # Token
        if not user.websiteToken:
            user.websiteToken = helpers.Garbage(40)
        responses["typeWorldWebsiteToken"] = user.websiteToken

        # Timezone
        if g.form._get("userTimezone"):
            user.timezone = g.form._get("userTimezone")
        # Last seen online
        user.lastSeenOnline = helpers.now()
        user.put()

        # subscriptions = user.subscriptions()

        # Normal subscriptions
        oldSubscriptions = user.confirmedSubscriptions()
        responses["heldSubscriptions"] = []
        for subscription in oldSubscriptions:
            s = {}
            s["url"] = subscription.url
            if subscription.rawSubscription().contentLastUpdated:
                s["serverTimestamp"] = int(subscription.rawSubscription().contentLastUpdated.timestamp())
            responses["heldSubscriptions"].append(s)
        # Old API < 0.2.3-beta
        # TODO: Delete later
        responses["subscriptions"] = [x["url"] for x in responses["heldSubscriptions"]]

        # Invitations
        # For the time being, don't attempt to hand over subscriptions to this method here
        # it breaks the unit tests
        invitations = user.subscriptionInvitations()
        responses["pendingInvitations"] = []
        responses["acceptedInvitations"] = []
        responses["sentInvitations"] = []
        for subscription in invitations:
            s = {}
            success, endpoint = subscription.rawSubscription().APIEndpoint()
            endpoint.updateJSON()

            sourceUserKey = None
            if subscription.invitedByUserKey:
                sourceUserKey = subscription.invitedByUserKey
            if subscription.invitedByAPIEndpointKey:
                sourceUserKey = subscription.invitedByAPIEndpointKey.get(read_consistency=ndb.STRONG).userKey
            sourceUser = sourceUserKey.get(read_consistency=ndb.STRONG)

            s["url"] = typeworld.client.URL(subscription.url).unsecretURL()
            s["ID"] = subscription.publicID()
            s["invitedByUserName"] = sourceUser.name
            s["invitedByUserEmail"] = sourceUser.email
            s["time"] = int(subscription.touched.timestamp())
            s["canonicalURL"] = subscription.rawSubscription().canonicalURL
            s["subscriptionName"] = subscription.rawSubscription().subscriptionName or ""
            s["fonts"] = subscription.rawSubscription().fonts
            s["families"] = subscription.rawSubscription().families
            s["foundries"] = subscription.rawSubscription().foundries

            if success:
                endpointCommand = typeworld.api.EndpointResponse()
                if not endpoint.endpointCommand:
                    success, message = endpoint.updateJSON(force=True)
                if not success:
                    responses["response"] = f"Error updating endpoint: {message}"
                    return
                endpointCommand.loadDict(endpoint.endpointCommand)

                s["publisherName"] = endpointCommand.name.dumpDict() or ""
                s["logoURL"] = endpointCommand.logoURL
                s["backgroundColor"] = endpointCommand.backgroundColor
                s["websiteURL"] = endpointCommand.websiteURL

            if subscription.confirmed:
                responses["acceptedInvitations"].append(s)

            else:
                responses["pendingInvitations"].append(s)

        for subscription in user.sentInvitations():

            s = {}

            s["url"] = typeworld.client.URL(subscription.url).unsecretURL()

            s["invitedUserName"] = subscription.key.parent().get(read_consistency=ndb.STRONG).name
            s["invitedUserEmail"] = subscription.key.parent().get(read_consistency=ndb.STRONG).email
            s["invitedTime"] = int(subscription.touched.timestamp())
            s["acceptedTime"] = (
                int(subscription.invitationAcceptedTime.timestamp()) if subscription.invitationAcceptedTime else ""
            )
            s["confirmed"] = subscription.confirmed

            responses["sentInvitations"].append(s)

        # Update timestamp
        appInstance.lastUsed = helpers.now()
        appInstance.put()


def verifyCredentials(responses):

    endpoint = classes.APIEndpoint.query(classes.APIEndpoint.APIKey == g.form._get("APIKey")).get(
        read_consistency=ndb.STRONG
    )
    if endpoint:

        log = classes.APILog(parent=endpoint.key)
        log.command = "verifyCredentials"
        log.incoming = dict(g.form)

        # User
        if g.form._get("anonymousTypeWorldUserID") == app.secret("TEST_TYPEWORLDUSERACCOUNTID"):
            pass  # simulate success

        else:
            k = ndb.Key(urlsafe=g.form._get("anonymousTypeWorldUserID").encode())
            user = k.get(read_consistency=ndb.STRONG)

            if not user:
                responses["response"] = "unknownAnonymousTypeWorldUserID"
                responses["explanation"] = "The parameter `anonymousTypeWorldUserID` did not yield a known user"
                log.response = responses
                log.put()
                # stat.bump([endpoint.key.id(), 'command', 'verifyCredentials',
                #  'unknownAnonymousTypeWorldUserID'], 1)
                return

            # Check if user holds subscription
            if g.form._get("subscriptionURL"):
                if not g.form._get("subscriptionURL") in [x.url for x in user.confirmedSubscriptions()]:
                    responses["response"] = "invalid"
                    responses["explanation"] = "The user doesn’t hold the subscription given in `subscriptionURL`"
                    log.response = responses
                    log.put()
                    # stat.bump([endpoint.key.id(), 'command', 'verifyCredentials',
                    # 'userIsMissingSubscription'], 1)
                    return

            if not user.emailVerified:
                user.sendEmailVerificationLink()
                responses["response"] = "invalid"
                responses[
                    "explanation"
                ] = "The user’s email address isn’t verified. A new verification email has been sent."
                log.response = responses
                log.put()
                # stat.bump([endpoint.key.id(), 'command', 'verifyCredentials',
                # 'userIsNotVerified'], 1)
                return

            # Check for app for user by app ID
            appFound = False
            for appInstance in user.appInstances():
                if appInstance.key.id() == g.form._get("anonymousAppID"):
                    appFound = True
                    if appInstance.revoked:
                        responses["response"] = "invalid"
                        responses["explanation"] = "The app instance identified by `anonymousAppID` is revoked"
                        log.response = responses
                        log.put()
                        # stat.bump([endpoint.key.id(), 'command', 'verifyCredentials',
                        # 'appInstanceIsRevoked'], 1)
                        return
                    break

            if not appFound:
                responses["response"] = "invalid"
                responses["explanation"] = "The app instance identified by `anonymousAppID` doesn't exist"
                log.response = responses
                log.put()
                # stat.bump([endpoint.key.id(), 'command', 'verifyCredentials',
                # 'appInstanceNotFound'], 1)
                return

        # Success
        # stat.bump([endpoint.key.id(), 'command', 'verifyCredentials', 'success'], 1)
        log.response = responses
        log.put()

    else:
        responses["response"] = "unknownAPIKey"
        responses["explanation"] = "The app instance identified by `anonymousAppID` doesn't exist"
        # stat.bump(['command', 'verifyCredentials', 'unknownAPIKey'], 1)
        return


def inviteUserToSubscription(responses):

    url = urllib.parse.unquote(g.form._get("subscriptionURL"))

    if g.form._get("APIKey"):
        sourceAPIEndpoint = classes.APIEndpoint.query(classes.APIEndpoint.APIKey == g.form._get("APIKey")).get(
            read_consistency=ndb.STRONG
        )
        if sourceAPIEndpoint:
            log = classes.APILog(parent=sourceAPIEndpoint.key)
            log.command = "inviteUserToSubscription"
            log.incoming = dict(g.form)
        else:
            log = None
    else:
        sourceAPIEndpoint = None
        log = None

    success, message = typeworld.client.urlIsValid(url)
    if not success:
        responses["response"] = "invalidSubscriptionURL"
        responses["explanation"] = f"The `subscriptionURL` is of an invalid format: {message}"
        if log:
            log.response = responses
            log.put()
        return

    if g.form._get("APIKey") and not sourceAPIEndpoint:
        responses["response"] = "invalidSourceAPIEndpoint"
        responses["explanation"] = "The `APIKey` does not yield a valid API Endpoint"
        if log:
            log.response = responses
            log.put()
        return

    targetUser = classes.User.query(classes.User.email == g.form._get("targetUserEmail")).get(
        read_consistency=ndb.STRONG
    )
    if not targetUser:
        responses["response"] = "unknownTargetEmail"
        responses["explanation"] = "The `targetUserEmail` does not yield a valid user account"
        if log:
            log.response = responses
            log.put()
        return

    if g.form._get("sourceUserEmail"):
        sourceUser = classes.User.query(classes.User.email == g.form._get("sourceUserEmail")).get(
            read_consistency=ndb.STRONG
        )
    else:
        sourceUser = None

    if g.form._get("sourceUserEmail") and not sourceUser:
        responses["response"] = "unknownSourceEmail"
        responses["explanation"] = "The `sourceUserEmail` does not yield a valid user account"
        if log:
            log.response = responses
            log.put()
        return

    if not sourceUser and not sourceAPIEndpoint:
        responses["response"] = "invalidSource"
        responses["explanation"] = "A valid source could not be identified either by `sourceUserEmail` or by `APIKey`"
        if log:
            log.response = responses
            log.put()
        return

    if (
        sourceUser
        and not sourceAPIEndpoint
        and not sourceUser.stripeSubscriptionReceivesService("world.type.professional_user_plan")
    ):
        responses["response"] = "invitationsRequireProAccount"
        responses["explanation"] = (
            "Source user needs to be subscripted to a Pro account in order to invite"
            " other users. Subscribe at https://type.world/account"
        )
        if log:
            log.response = responses
            log.put()
        return

    # Check if API endpoint has been claimed by a user (must be, because otherwise they
    # wouldn't have the API key)
    if sourceAPIEndpoint:
        if sourceAPIEndpoint and sourceAPIEndpoint.userKey:
            APIEndpointUser = sourceAPIEndpoint.userKey.get(read_consistency=ndb.STRONG)
        else:
            responses["response"] = "invalidSourceAPIEndpoint"
            responses["explanation"] = (
                "Source API Endpoint is not associated with a user account. Claim your"
                " API Endpoint at https://type.world/account/developer"
            )
            if log:
                log.response = responses
                log.put()
            return
    else:
        APIEndpointUser = None

    tempSubscription = classes.Subscription()  # parent=targetUser.key leads to error down the stream
    tempSubscription.url = url

    # success, endpoint = subscription.rawSubscription().APIEndpoint()
    # endpoint.updateJSON()

    success, endpoint = tempSubscription.rawSubscription().APIEndpoint()
    if not success:
        responses["response"] = endpoint
        responses[
            "explanation"
        ] = "Error while retrieving subscription’s associated API Endpoint object. See `response` field for details."
        if log:
            log.response = responses
            log.put()
        return

    # ID by user, but source user doesn't hold the subscription
    if sourceUser and not sourceUser.subscriptionByURL(url):
        responses["response"] = "unknownSubscriptionForUser"
        responses["explanation"] = "Source user does not hold this subscription"
        if log:
            log.response = responses
            log.put()
        return

    # ID by API endpoint, but subscription's canonical url
    # does not point to same API endpoint
    elif endpoint and sourceAPIEndpoint and endpoint != sourceAPIEndpoint:
        responses["response"] = "invalidSourceAPIEndpoint"
        responses[
            "explanation"
        ] = "Subscription’s canonical URL does not point at API Endpoint yielded by `APIKey` field"
        if log:
            log.response = responses
            log.put()
        return

    elif sourceUser and targetUser and sourceUser == targetUser:
        responses["response"] = "sourceAndTargetIdentical"
        responses["explanation"] = "Source and target users are identical"
        if log:
            log.response = responses
            log.put()
        return

    elif APIEndpointUser and targetUser and APIEndpointUser == targetUser:
        responses["response"] = "sourceAndTargetIdentical"
        responses["explanation"] = "Source and target users are identical"
        if log:
            log.response = responses
            log.put()
        return

    else:

        assert endpoint
        assert targetUser
        assert sourceUser or sourceAPIEndpoint

        oldSubscriptions = targetUser.subscriptions()
        oldURLs = [x.url for x in oldSubscriptions if (x is not None and x.key is not None)]

        # Save new subscription
        if url in oldURLs:
            print("ALERT: targetUser already holds subscription")
        if url not in oldURLs:

            subscription = classes.Subscription(parent=targetUser.key)
            subscription.url = url

            subscription.type = "invitation"
            subscription.confirmed = False
            if sourceUser:
                subscription.invitedByUserKey = sourceUser.key
            elif sourceAPIEndpoint:
                subscription.invitedByAPIEndpointKey = sourceAPIEndpoint.key

            subscription.putnow()

            # TODO
            # It's not clear why the below block is necessary.
            # However, without it, invitation revocations are working only on second
            # attempt, which is the weirdest thing ever. I pulled my hair out for this.
            # Before adding this block (taken from downloadUserSubscriptions()),
            # revoking an invitation would only work on first attempt after the
            # target user has reloaded their user account after the invitation was sent.
            success, endpoint = subscription.rawSubscription().APIEndpoint()
            endpoint.updateJSON()
            if success:
                endpointCommand = typeworld.api.EndpointResponse()
                if not endpoint.endpointCommand:
                    success, message = endpoint.updateJSON(force=True)
                if success:
                    endpointCommand.loadDict(endpoint.endpointCommand)

            success, message = subscription.sendInvitationEmail()
            if not success:
                responses["response"] = message
                responses[
                    "explanation"
                ] = "Error while sending invitation notification email. See `response` field for details."
                if log:
                    log.response = responses
                    log.put()
                return

            if targetUser.stripeSubscriptionReceivesService("world.type.professional_user_plan"):
                success, message = targetUser.announceChange(g.form._get("sourceAnonymousAppID"))
                if not success:
                    responses["response"] = message
                    responses[
                        "explanation"
                    ] = "Error while announcing invitation to target user. See `response` field for details."
                    if log:
                        log.response = responses
                        log.put()
                    return

    if log:
        log.response = responses
        log.put()


def revokeSubscriptionInvitation(responses):

    url = urllib.parse.unquote(g.form._get("subscriptionURL"))

    if g.form._get("APIKey"):
        sourceAPIEndpoint = classes.APIEndpoint.query(classes.APIEndpoint.APIKey == g.form._get("APIKey")).get(
            read_consistency=ndb.STRONG
        )
        if sourceAPIEndpoint:
            log = classes.APILog(parent=sourceAPIEndpoint.key)
            log.command = "revokeSubscriptionInvitation"
            log.incoming = dict(g.form)
        else:
            log = None
    else:
        sourceAPIEndpoint = None
        log = None

    success, message = typeworld.client.urlIsValid(url)
    if not success:
        responses["response"] = "invalidSubscriptionURL"
        responses["explanation"] = f"The `subscriptionURL` is of an invalid format: {message}"
        if log:
            log.response = responses
            log.put()
        return

    if g.form._get("APIKey") and not sourceAPIEndpoint:
        responses["response"] = "invalidSourceAPIEndpoint"
        responses["explanation"] = "The `APIKey` does not yield a valid API Endpoint"
        if log:
            log.response = responses
            log.put()
        return

    if g.form._get("targetUserEmail"):
        targetUser = classes.User.query(classes.User.email == g.form._get("targetUserEmail")).get(
            read_consistency=ndb.STRONG
        )
    else:
        targetUser = None

    if not targetUser:
        responses["response"] = "unknownTargetEmail"
        responses["explanation"] = "The `targetUserEmail` does not yield a valid user account"
        if log:
            log.response = responses
            log.put()
        return

    if g.form._get("sourceUserEmail"):
        sourceUser = classes.User.query(classes.User.email == g.form._get("sourceUserEmail")).get(
            read_consistency=ndb.STRONG
        )
    else:
        sourceUser = None

    if g.form._get("APIKey"):
        sourceAPIEndpoint = classes.APIEndpoint.query(classes.APIEndpoint.APIKey == g.form._get("APIKey")).get(
            read_consistency=ndb.STRONG
        )
    else:
        sourceAPIEndpoint = None

    # sourceUser = User.query(User.email == g.form._get('sourceUserEmail'))
    # .get(read_consistency=ndb.STRONG)
    # sourceAPIEndpoint = APIEndpoint.query(APIEndpoint.APIKey == g.form._get('APIKey'))
    # .get(read_consistency=ndb.STRONG)

    if not sourceUser and not sourceAPIEndpoint:
        responses["response"] = "invalidSource"
        responses["explanation"] = "A valid source could not be identified either by `sourceUserEmail` or by `APIKey`"
        if log:
            log.response = responses
            log.put()
        return

    subscription = targetUser.subscriptionByURL(url, subscriptions=targetUser.subscriptionInvitations())

    # TODO:

    # not sure if this is good.
    # Should iviters hold the subscription or not when they revoke an invitation?
    # Subsequently, will invitees need to be revoked when a user deletes a subscription?

    # ID by user, but source user doesn't hold the subscription
    # elif sourceUser.exists and not sourceUser.subscriptionByURL(url):
    # 	responses = {'response': 'invalidSource'}

    # if subscription:
    # ID by API endpoint, but subscription's canonical url does
    # not point to same API endpoint
    if subscription:
        success, endpoint = subscription.rawSubscription().APIEndpoint()
        if sourceAPIEndpoint and subscription and endpoint and (endpoint != sourceAPIEndpoint):
            responses["response"] = "invalidSourceAPIEndpoint"
            responses[
                "explanation"
            ] = "Subscription’s canonical URL does not point at API Endpoint yielded by `APIKey` field"
            if log:
                log.response = responses
                log.put()
            return

    if not subscription:
        responses["response"] = "unknownSubscription"
        responses["explanation"] = "Subscription does not exist"
        if log:
            log.response = responses
            log.put()
        return

    targetUserHoldsSubscription = subscription.key.parent() == targetUser.key
    invitedBySourceUser = sourceUser and subscription.invitedByUserKey == sourceUser.key
    invitedByAPIEndpoint = sourceAPIEndpoint and subscription.invitedByAPIEndpointKey == sourceAPIEndpoint.key

    if not targetUserHoldsSubscription:
        responses["response"] = "unknownSubscription"
        responses["explanation"] = "Target user does not hold this subscription"
        if log:
            log.response = responses
            log.put()
        return

    if not invitedBySourceUser and not invitedByAPIEndpoint:
        responses["response"] = "unknownSubscription"
        responses["explanation"] = "Sender of invitation is unclear"
        if log:
            log.response = responses
            log.put()
        return

    if sourceUser:
        subscription.invitationRevokedByUserKey = sourceUser.key
    elif sourceAPIEndpoint:
        subscription.invitationRevokedByAPIEndpointKey = sourceAPIEndpoint.key

    success, message = subscription.sendRevokedEmail()
    if not success:
        responses["response"] = message
        responses["explanation"] = "Error while sending invitation revocation email. See `response` field for details."
        if log:
            log.response = responses
            log.put()
        return

    subscription.key.delete()

    if targetUser.stripeSubscriptionReceivesService("world.type.professional_user_plan"):
        success, message = targetUser.announceChange(g.form._get("sourceAnonymousAppID"))
        if not success:
            responses["response"] = message
            responses[
                "explanation"
            ] = "Error while announcing invitation revocation to target user. See `response` field for details."
            if log:
                log.response = responses
                log.put()
            return

    if log:
        log.response = responses
        log.put()


def acceptInvitations(responses):

    if not g.form._get("anonymousUserID"):
        responses["response"] = "userUnknown"
        return

    k = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
    if not k.id() or not k.get(read_consistency=ndb.STRONG):
        responses["response"] = "userUnknown"
        return
    user = k.get(read_consistency=ndb.STRONG)

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"
        return

    appInstance = classes.AppInstance.get_by_id(
        g.form._get("anonymousAppID"), parent=user.key, read_consistency=ndb.STRONG
    )

    if not appInstance.key.id():
        responses["response"] = "appInstanceUnknown"
        return

    else:

        # Add new subscriptions
        keys = [ndb.Key(urlsafe=x.encode()) for x in g.form._get("subscriptionIDs").split(",") if x and x != "empty"]
        for subscription in user.subscriptions():

            if subscription.key in keys:
                subscription.confirmed = True
                subscription.invitationAcceptedTime = helpers.now()
                subscription.putnow()

                success, message = subscription.sendAcceptedEmail()
                if not success:
                    responses["response"] = "sendAcceptedEmail(): %s" % message
                    return

        downloadUserSubscriptions(responses)

        if user.stripeSubscriptionReceivesService("world.type.professional_user_plan"):
            success, message = user.announceChange(g.form._get("sourceAnonymousAppID"))
            if not success:
                responses["response"] = message
                return


def declineInvitations(responses):

    if not g.form._get("anonymousUserID"):
        responses["response"] = "userUnknown"
        return

    k = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
    if not k.id():
        responses["response"] = "userUnknown"
        return
    user = k.get(read_consistency=ndb.STRONG)

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"

    appInstance = classes.AppInstance.get_by_id(
        g.form._get("anonymousAppID"), parent=user.key, read_consistency=ndb.STRONG
    )

    if not appInstance.key.id():
        responses["response"] = "appInstanceUnknown"
        return

    else:

        # Delete subscriptions
        keys = [ndb.Key(urlsafe=x.encode()) for x in g.form._get("subscriptionIDs").split(",") if x and x != "empty"]
        for subscription in user.subscriptions():

            if subscription.key in keys:
                subscription.key.delete()

                success, message = subscription.sendDeletedEmail()
                if not success:
                    responses["response"] = "sendDeletedEmail(): %s" % message
                    return

        downloadUserSubscriptions(responses)

        if user.stripeSubscriptionReceivesService("world.type.professional_user_plan"):
            success, message = user.announceChange(g.form._get("sourceAnonymousAppID"))
            if not success:
                responses["response"] = message
                return


def userAppInstances(responses):

    if not g.form._get("anonymousUserID"):
        responses["response"] = "userUnknown"
        return

    k = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
    if not k.id():
        responses["response"] = "userUnknown"
        return

    user = k.get(read_consistency=ndb.STRONG)

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"
        return

    appInstance = classes.AppInstance.get_by_id(
        g.form._get("anonymousAppID"), parent=user.key, read_consistency=ndb.STRONG
    )
    if not appInstance.key.id():
        responses["response"] = "appInstanceUnknown"
        return

    if appInstance.revoked:
        responses["response"] = "appInstanceRevoked"
        return

    responses["appInstances"] = []
    instances = user.appInstances()

    for instance in instances:
        i = {}
        i["anonymousAppID"] = instance.key.id()

        for key in (
            "machineModelIdentifier",
            "machineHumanReadableName",
            "machineSpecsDescription",
            "machineOSVersion",
            "machineNodeName",
            "revoked",
        ):
            i[key] = getattr(instance, key)

        for key in ("lastUsed", "revokedTime"):
            if getattr(instance, key):
                i[key] = int(getattr(instance, key).timestamp())
            else:
                i[key] = ""

        i["VM"] = instance.isVM()
        i["image"] = instance.machineImage()

        responses["appInstances"].append(i)


# class AppInstance(TWNDBModel):
# 	# key = anonymousAppID
# #	userKey = KeyProperty(required = True)
# 	machineModelIdentifier = StringProperty()
# 	machineHumanReadableName = StringProperty()
# 	machineSpecsDescription = StringProperty()
# 	machineOSVersion = StringProperty()
# 	machineNodeName = StringProperty()
# 	lastUsed = DateTimeProperty(required = True)

# 	revoked = BooleanProperty()
# 	revokeResponse = StringProperty()
# 	revokedTime = DateTimeProperty()


def revokeAppInstance(responses):

    if not g.form._get("anonymousUserID"):
        responses["response"] = "userUnknown"
        return

    k = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
    if not k.id() or not k.get(read_consistency=ndb.STRONG):
        responses["response"] = "userUnknown"
        return
    user = k.get(read_consistency=ndb.STRONG)

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"

    appInstance = classes.AppInstance.get_by_id(
        g.form._get("anonymousAppID"), parent=user.key, read_consistency=ndb.STRONG
    )

    if not appInstance.key.id():
        responses["response"] = "appInstanceUnknown"
        return

    success, message = appInstance.revoke("revoked")

    if success:

        success, message = user.announceChange(g.form._get("sourceAnonymousAppID"))
        if not success:
            responses["response"] = "Announce change failure: %s" % message
            return

    else:
        responses["response"] = message


def reactivateAppInstance(responses):

    if not g.form._get("anonymousUserID"):
        responses["response"] = "userUnknown"
        return

    k = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
    if not k.id() or not k.get(read_consistency=ndb.STRONG):
        responses["response"] = "userUnknown"
        return
    user = k.get(read_consistency=ndb.STRONG)

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"

    appInstance = classes.AppInstance.get_by_id(
        g.form._get("anonymousAppID"), parent=user.key, read_consistency=ndb.STRONG
    )

    if not appInstance.key.id():
        responses["response"] = "appInstanceUnknown"
        return

    success, message = appInstance.revoke("active")

    if success:

        success, message = user.announceChange(g.form._get("sourceAnonymousAppID"))
        if not success:
            responses["response"] = "Announce change failure: %s" % message
            return

    else:
        responses["response"] = message


def addAPIEndpointToUserAccount(responses):

    k = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
    if not k.id() or not k.get(read_consistency=ndb.STRONG):
        responses["response"] = "userUnknown"
        return
    user = k.get(read_consistency=ndb.STRONG)

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"
        return

    if typeworld.client.urlIsValid(g.form._get("canonicalURL"))[0] is False:
        responses["response"] = "urlInvalid"
        return

    endpoint = classes.APIEndpoint.get_or_insert(g.form._get("canonicalURL"))  # , read_consistency=ndb.STRONG

    if endpoint.userKey and endpoint.userKey != user.key:
        responses["response"] = "APIEndpointTaken"
        return

    elif endpoint.userKey and endpoint.userKey == user.key:
        responses["response"] = "success"
        return

    else:
        endpoint.userKey = user.key
        endpoint.updateJSON()
        endpoint.put()
        # user.APIEndpointKeys.append(endpoint.key)
        # user.put()


def listAPIEndpointsForUserAccount(responses):

    k = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
    if not k.id():
        responses["response"] = "userUnknown"
        return
    user = k.get(read_consistency=ndb.STRONG)

    if g.form._get("secretKey") != user.secretKey:
        responses["response"] = "secretKeyInvalid"
        return

    else:
        responses["endpoints"] = []
        for endpoint in user.APIEndpoints():
            d = {}
            d["canonicalURL"] = endpoint.key.id()
            d["APIKey"] = endpoint.APIKey
            responses["endpoints"].append(d)


def updateSubscription(responses):

    # TODO:
    # Implement that this can be called by the app directly,
    # checking validity via sourceAnonymousAppID. It should lead to a user account
    # that holds this subscription

    # TODO:
    # Make sure that subscription URLs don't contain an access token,
    # otherwise reject

    # Check for endpoint by API key
    endpoint = classes.APIEndpoint.query(classes.APIEndpoint.APIKey == g.form._get("APIKey")).get(
        read_consistency=ndb.STRONG
    )
    if not endpoint:
        responses["response"] = "unknownAPIKey"
        return

    log = classes.APILog(parent=endpoint.key)
    log.command = "updateSubscription"
    log.incoming = dict(g.form)

    # Check URL
    url = urllib.parse.unquote(g.form._get("subscriptionURL"))
    success, message = typeworld.client.urlIsValid(url)
    if not success:
        responses["response"] = "invalidSubscriptionURL"
        responses["explanation"] = "The `subscriptionURL` is of an invalid format"
        log.response = responses
        log.put()
        return

    delay = g.form._get("timeStretch")
    if delay:
        try:
            delay = int(delay)
        except ValueError:
            responses["response"] = "invalidDelayValue"
            log.response = responses
            log.put()
            return
    else:
        delay = 0

    # Quota
    if not endpoint.hasSubscriptionUpdateQuota():
        responses["response"] = "paidSubscriptionRequired"
        responses["explanation"] = (
            "This API command is only available to publishers subscribed to the"
            " Professional Publisher Plan. Subscribe at"
            " https://type.world/account/developer"
        )
        log.response = responses
        log.put()
        return

    rawSubscription = classes.RawSubscription.get_or_insert(
        classes.RawSubscription.keyURL(g.form._get("subscriptionURL"))
    )  # , read_consistency=ndb.STRONG
    rawSubscription.secretURL = typeworld.client.URL(g.form._get("subscriptionURL")).secretURL()
    if rawSubscription.key:
        new = False
    else:
        new = True

    # Update content
    success, message, changes = rawSubscription.updateJSON(force=True, save=True)
    if not success:
        responses["response"] = message
        responses[
            "explanation"
        ] = "An error occurred while accessing the API Endpoint. See `response` field for details."
        log.response = responses
        log.put()
        return

    # Announce change
    success, message = rawSubscription.announceChange(int(delay), g.form._get("sourceAnonymousAppID") or "")
    if not success:
        responses["response"] = message
        responses["explanation"] = (
            "An error occurred while announcing the subscription change to"
            " participating app instances. See `response` field for details."
        )
        log.response = responses
        log.put()
        return

    # Billing
    if "addedFonts" in changes or new:
        log.billedAs = "subscriptionUpdateWithAddedFonts"
        if new:
            log.reason = "firstAppearance"
        else:
            log.reason = "addedFonts"
        success, message = endpoint.bill("subscriptionUpdateWithAddedFonts", g.form._get("subscriptionURL"))
        if not success:
            responses["response"] = message
            responses[
                "explanation"
            ] = "An error occurred while billing the API call to the publisher. See `response` field for details."
            log.response = responses
            log.put()
            return

    # print("8")

    if "fontsWithAddedVersions" in changes:
        log.billedAs = "subscriptionUpdateWithAddedFontVersions"
        success, message = endpoint.bill("subscriptionUpdateWithAddedFontVersions", g.form._get("subscriptionURL"))
        if not success:
            responses["response"] = message
            responses[
                "explanation"
            ] = "An error occurred while billing the API call to the publisher. See `response` field for details."
            log.response = responses
            log.put()
            return

    # print("9")

    log.response = responses
    log.put()


def handleTraceback(responses):

    # Check for endpoint by API key
    payload = g.form._get("payload")[:1500]
    traceback = classes.AppTraceback.query(classes.AppTraceback.payload == payload).get(read_consistency=ndb.STRONG)

    # Parse incoming version number
    incomingVersion = payload.splitlines()[0].split(":")[1].strip()
    if not incomingVersion:
        responses["response"] = f"Couldn’t fetch incoming version: {incomingVersion}"
        return
    try:
        semver.VersionInfo.parse(incomingVersion)
    except ValueError:
        responses["response"] = f"Couldn’t fetch incoming version: {incomingVersion}"
        return

    # Get handleTracebackMinimumVersion
    minimumVersion = classes.Preference.query(classes.Preference.name == "handleTracebackMinimumVersion").get(
        read_consistency=ndb.STRONG
    )
    if minimumVersion:
        minimumVersion = minimumVersion.content
    else:
        responses["response"] = "Couldn’t fetch handleTracebackMinimumVersion"
        return

    # Compare version numbers, create only if shall be handled
    if semver.compare(incomingVersion, minimumVersion) >= 0:

        # Doesn't exist, create new
        if not traceback:
            traceback = classes.AppTraceback()
            traceback.payload = payload
            if g.form._get("supplementary"):
                traceback.supplementary = g.form._get("supplementary").encode()
            traceback.putnow()

            body = (
                f"View error on server: https://type.world/tracebacks/{traceback.key.urlsafe().decode()}\n\n"
                + traceback.payload
            )
            helpers.email(
                "Type.World Errors <errors@mail.type.world>",
                ["post@yanone.de"],
                "Type.World App Traceback",
                body,
            )


def downloadSettings(responses):

    # User is known
    user = None
    if g.form._get("anonymousUserID") and g.form._get("secretKey"):
        k = ndb.Key(urlsafe=g.form._get("anonymousUserID").encode())
        if not k.id():
            responses["response"] = "userUnknown"
            return
        user = k.get(read_consistency=ndb.STRONG)
        if not user:
            responses["response"] = "userUnknown"
            return

        if g.form._get("secretKey") != user.secretKey:
            responses["response"] = "secretKeyInvalid"
            return

        # Last seen online
        user.lastSeenOnline = helpers.now()
        user.put()

    IP = random.choice([x.ip for x in mq.availableMQInstances()])
    settings = {
        "messagingQueue": f"tcp://{IP}:5556",
        "breakingAPIVersions": typeworld.api.BREAKINGVERSIONS,
    }

    responses["settings"] = settings


def resendEmailVerification(responses):

    user = classes.User.query(classes.User.email == g.form._get("email")).get(read_consistency=ndb.STRONG)
    if not user:
        responses["response"] = "userUnknown"
        return

    if user.emailVerified:
        responses["response"] = "userIsVerified"
        return

    user.sendEmailVerificationLink()


def reportAPIEndpointError(responses):

    rawSubscription = classes.RawSubscription.get_or_insert(
        classes.RawSubscription.keyURL(g.form._get("subscriptionURL"))
    )  # , read_consistency=ndb.STRONG
    rawSubscription.secretURL = typeworld.client.URL(g.form._get("subscriptionURL")).secretURL()

    if (
        rawSubscription.lastErrorReported is None
        or rawSubscription.lastErrorReported is not None
        and (helpers.now() - rawSubscription.lastErrorReported).seconds > 7 * 24 * 60 * 60
    ):  # once per week:

        print("Investigating error")

        client = rawSubscription.client()
        success, message, publisher, subscription = client.addSubscription(
            g.form._get("subscriptionURL"), remotely=True, reportErrors=False
        )
        if not success:

            emails = []
            if type(message) in (
                typeworld.api.MultiLanguageText,
                typeworld.api.MultiLanguageLongText,
            ):
                message = message.getText()

            success, endpoint = rawSubscription.APIEndpoint()

            # Successful, pull email from APIEndpoint object
            if success and endpoint.userKey:
                emails.append(endpoint.userKey.get().email)

            # Failed, find endpoint directly
            else:
                success, content, response = typeworld.client.request(
                    typeworld.client.URL(g.form._get("subscriptionURL")).HTTPURL()
                )
                # content = content.decode()
                if success:

                    # Catch email
                    match = re.search(r'.*"adminEmail".+?"(.+?)".*', content, re.M)
                    if match:
                        emails.append(match.group(1))

                    # Catch canonical URL
                    match = re.search(r'.*"canonicalURL".+?"(.+?)".*', content, re.M)
                    if match:
                        canonicalURL = match.group(1)
                        endpoint = classes.APIEndpoint.get_or_insert(canonicalURL)
                        if endpoint:
                            if endpoint.userKey:
                                emails.append(endpoint.userKey.get().email)

            # Add HQ
            emails.append("hello@type.world")
            emails = list(set(emails))

            if emails:

                subscriptionURL = g.form._get("subscriptionURL")
                body = f"The subscription {subscriptionURL} showed the following error:\n\n"
                body += message
                body += (
                    "\n\nThis page describes how to validate your API Endpoint before"
                    " publication: https://type.world/developer/validate\n I hope to be"
                    " able to offer you an online validator again soon under that same"
                    " URL.\n\nThis is an automated email which you will receive at most"
                    " once per week.\n\nYours truly, Type.World HQ"
                )

                success, message = helpers.email(
                    "Type.World <hq@mail.type.world>",
                    emails,  # email
                    "Error in a Type.World font subscription that you host",
                    body,
                )

                rawSubscription.lastErrorReported = helpers.now()
                rawSubscription.put()

                print("success, sent email")
            else:

                print("Couln't find email")
