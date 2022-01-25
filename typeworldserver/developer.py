# project
import typeworldserver
from typeworldserver import definitions
from typeworldserver import web
from typeworldserver import helpers
from typeworldserver import classes
from typeworldserver import billing_stripe

# other
import typeworld.client
import markdown2
import certifi
import ssl
import markdown
import os
import json
import semver
import functools
from flask import abort, g, Response, redirect
from currency_converter import CurrencyConverter
from google.cloud import ndb
import time
import collections
import base64

currencyConverter = CurrencyConverter()


typeworldserver.app.config["modules"].append("developer")

GOOGLE_PROJECT_ID = "typeworld2"

###


SSLCONTEXT = ssl.create_default_context(cafile=certifi.where())

# class AppBuild(classes.TWNDBModel):
# 	appID = web.StringProperty(required = True)
# 	platform = web.StringProperty(required = True)
# 	version = web.StringProperty(required = True)
# 	published = web.BooleanProperty(default = False)

# 	sparkleSignature = web.StringProperty()


class AppIDProperty(web.StringProperty, web.Property):
    def dialog(self, key, value, placeholder=None):
        g.html.textInput(key, value=value, type="text", placeholder=placeholder)

    def valid(self, value):
        if not value == "world.type.guiapp":
            return False, f"{value} is not a valid appID string"
        else:
            return True, None


class BuildPlatformProperty(web.StringProperty, web.Property):
    def dialog(self, key, value, placeholder=None):
        g.html.textInput(key, value=value, type="text", placeholder=placeholder)

    def valid(self, value):
        if value not in ["mac", "windows"]:
            return False, f"{value} is not a valid platform string"
        else:
            return True, None


class AppBuild(classes.TWNDBModel):
    platform = BuildPlatformProperty(required=True)
    active = web.BooleanProperty(default=False)
    published = web.BooleanProperty(default=False)
    publishedForDevelopers = web.BooleanProperty(default=False)
    sparkleSignature = web.StringProperty()
    buildCompletedTime = web.DateTimeProperty()

    def ending(self):
        if self.platform == "mac":
            return "dmg"
        if self.platform == "windows":
            return "exe"

    def buildable(self):
        return self.published is False and self.active is True and not self.blob()

    def reloadDataContainer(self, view, parameters):
        return web.encodeDataContainer(None, "viewLatestUnpublishedBuilds")

    def getParent(self):
        if not hasattr(self, "_parent"):
            self._parent = self.key.parent().get(read_consistency=ndb.STRONG)
        return self._parent

    def downloadLink(self):
        return f"https://{definitions.DOWNLOADSURL}/app/TypeWorldApp.{self.getParent().version}.{self.ending()}"

    def mainDownloadLink(self):
        return f"https://{definitions.DOWNLOADSURL}/app/TypeWorldApp.{self.ending()}"

    def view(self, parameters={}, directCallParameters={}):

        problems = list(self.problems())
        blob = self.blob()
        # buildable = self.buildable()

        # g.html.P()
        # g.html.T(f'active: {self.active}')
        # g.html.BR()
        # g.html.T(f'published: {self.published}')
        # g.html._P()

        # is published
        if self.published:
            g.html.P()
            g.html.T("Published")
            self.edit(propertyNames=["published"])
            g.html._P()

        elif self.publishedForDevelopers:
            g.html.P()
            g.html.T("Published (DEVELOPER)")
            self.edit(propertyNames=["publishedForDevelopers"])
            g.html._P()

        # not published
        else:

            # Edit active
            g.html.P()
            if self.active:
                g.html.T("Active ")
            else:
                g.html.T("Inactive ")
            self.edit(propertyNames=["active"])
            g.html._P()

            # no problems, can publish
            if not problems:
                g.html.P()
                g.html.T("Ready to publish ")
                self.edit(propertyNames=["published", "publishedForDevelopers"])
                g.html._P()

            # Ready to build
            if self.buildable():
                g.html.P()
                g.html.T("Ready to build")
                g.html._P()

            # Not ready to build
            else:
                g.html.P()
                g.html.T("Not ready to build")
                g.html.BR()
                self.execute("Prepare to build", methodName="prepareToBuild")
                g.html._P()

        def bytesto(bytes, to, bsize=1024):
            """convert bytes to megabytes, etc.
            sample code:
                print('mb= ' + str(bytesto(314575262000000, 'm')))
            sample output:
                mb= 300002347.946
            """

            a = {"k": 1, "m": 2, "g": 3, "t": 4, "p": 5, "e": 6}
            r = float(bytes)
            for i in range(a[to]):
                r = r / bsize

            return r

        # Download file
        if blob:
            g.html.P()
            g.html.A(href=f"https://{definitions.DOWNLOADSURL}/app/{os.path.basename(blob.name)}?t={time.time()}")
            g.html.T("Download file")
            g.html._A()
            g.html.T(f" ({int(bytesto(blob.size, 'm'))}MB)")

            mainBlob = self.mainBlob()
            g.html.BR()
            if mainBlob and blob.crc32c == mainBlob.crc32c:
                g.html.T("This file is the main download")
            else:
                self.execute("Propagate as main download", methodName="propagate")

            g.html._P()

    def appcastXML(self, versions, platform, profile):

        if self.publishedForDevelopers:
            notes = (
                "*Note: This in an unpublished developer build! Make sure you are"
                " prepared to lose your app data in case of bugs. The app’s preference"
                " file is located at"
                " ~/Library/Preferences/world.type.guiapp.plist*\n\n\n"
            )
        else:
            notes = ""

        i = 0
        for version in versions:
            if semver.compare(self.getParent().version, version.version) >= 0 and i < 5:
                build = version.build(platform)
                if build.published or profile == "developer" and build.publishedForDevelopers:
                    notes += f"**Version {version.version}**\n\n{version.notes or '*No description available*'}\n\n\n"
                    i += 1

        # notes += self.getParent().notes

        return f"""	<item>
        <title>{self.getParent().version}</title>
        <description><![CDATA[{markdown2.markdown(notes)}]]></description>
        <pubDate>{self.buildCompletedTime.strftime('%c')} +0000</pubDate>
        {'<sparkle:minimumSystemVersion>10.14</sparkle:minimumSystemVersion>' if self.platform == 'mac' else ''}
        <enclosure url="{self.downloadLink()}" sparkle:version="{self.getParent().version}" {'sparkle:installerArguments="/SILENT /SP- /NOICONS /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS" sparkle:os="windows"' if self.platform == 'windows' else ''} sparkle:shortVersionString="{self.getParent().version}" {self.sparkleSignature} type="application/octet-stream" />
    </item>
"""  # noqa E501

    def prepareToBuild(self):
        blob = self.blob()
        if blob:
            blob.delete()
        self.sparkleSignature = ""
        self.active = True
        self.put()

    def propagate(self):
        mainBlob = self.mainBlob()
        if mainBlob:
            mainBlob.delete()
        typeworldserver.bucket.copy_blob(self.blob(), typeworldserver.bucket, new_name=self.mainDownloadFile())

    def blob(self):
        blob = typeworldserver.bucket.get_blob(f"app/TypeWorldApp.{self.getParent().version}.{self.ending()}")
        if blob:
            blob.reload()
        return blob

    def mainDownloadFile(self):
        return f"app/TypeWorldApp.{self.ending()}"

    def mainBlob(self):
        blob = typeworldserver.bucket.get_blob(self.mainDownloadFile())
        if blob:
            blob.reload()
        return blob

    def problems(self):
        if not self.sparkleSignature:
            yield "No Sparkle signature"
        if not self.blob():
            yield "No file"

    def canPublish(self):
        if self.sparkleSignature:
            return True
        return False

    @classmethod
    def _pre_delete_hook(cls, key):
        puts = []
        deletes = []
        if key:
            self = key.get(read_consistency=ndb.STRONG)
            if self is not None:
                if self.blob():
                    self.blob().delete()

        ndb.put_multi(puts)
        ndb.delete_multi(deletes)


class AppVersion(classes.TWNDBModel):
    appID = AppIDProperty(required=True)
    version = web.SemVerProperty(required=True)
    notes = web.TextProperty()

    def view(self, parameters={}, directCallParameters={}):

        g.html.area(f"Version {self.version}")

        g.html.P()
        self.edit(propertyNames=["notes"])
        published = False
        for build in self.builds():
            if build.published:
                published = True
                break
        if not published:
            self.delete(text='<span class="material-icons-outlined">delete</span>')
        g.html._P()

        g.html.TABLE()
        g.html.TR()
        for platform in parameters["platforms"]:
            g.html.TH()
            g.html.T(platform)
            g.html._TH()
        g.html._TR()
        g.html.TR()
        for platform in platforms:
            g.html.TD()
            build = self.build(platform)
            build.container("view")
            g.html._TD()
        g.html.TR()
        g.html._TABLE()
        g.html._area()

    def builds(self):
        if not hasattr(self, "_builds"):
            self._builds = AppBuild.query(ancestor=self.key).fetch(read_consistency=ndb.STRONG)
        for i, build in enumerate(self._builds):
            self._builds[i]._parent = self
        return self._builds

    def build(self, platform):
        builds = self.builds()
        for build in builds:

            # Found
            if build.platform == platform:
                build._parent = self
                return build

        # Not found
        build = AppBuild(parent=self.key)
        build.platform = platform
        build.put()
        build._parent = self
        self._builds.append(build)

        return build

    @classmethod
    def _pre_delete_hook(cls, key):
        puts = []
        deletes = []
        if key:
            self = key.get(read_consistency=ndb.STRONG)
            if self is not None:
                for build in self.builds():
                    deletes.append(build.key)

        ndb.put_multi(puts)
        ndb.delete_multi(deletes)


def getVersions():
    versions = AppVersion.query().fetch(read_consistency=ndb.STRONG)

    def compare(item1, item2):
        return semver.VersionInfo.parse(item1.version).compare(item2.version)

    versions.sort(key=functools.cmp_to_key(compare), reverse=True)

    return versions


def getLatestUnpublishedVersion(platform, versions=None):

    if not versions:
        versions = getVersions()

    for version in versions:
        build = version.build(platform)
        if build.buildable():
            return version.version

    return "n/a"


platforms = ["mac", "windows"]


@typeworldserver.app.route("/latestUnpublishedVersion/<appKey>/<platform>/", methods=["GET"])
def latestUnpublishedVersion(appKey, platform):

    if g.form._get("APPBUILD_KEY") != typeworldserver.secret("APPBUILD"):
        return abort(401)

    return Response(getLatestUnpublishedVersion(platform), mimetype="text/plain; charset=utf-8")


@typeworldserver.app.route("/setSparkleSignature", methods=["POST"])
def setSparkleSignature():

    if g.form._get("APPBUILD_KEY") != typeworldserver.secret("APPBUILD"):
        return abort(401)

    if not g.form._get("platform") in platforms:
        return abort(401)

    if not g.form._get("appKey") == "world.type.guiapp":
        return abort(401)

    for version in getVersions():
        if version.version == g.form._get("version"):
            build = version.build(g.form._get("platform"))

            # Security
            if build.active and not build.published and not build.sparkleSignature:
                build.sparkleSignature = g.form._get("signature")
                build.buildCompletedTime = helpers.now()
                build.put()

                return Response("ok", mimetype="text/plain; charset=utf-8")

    return abort(401)


def viewLatestUnpublishedBuilds(parameters, directCallParameters):

    if "versions" in directCallParameters:
        versions = directCallParameters["versions"]
    else:
        versions = getVersions()

    g.html.P()
    g.html.T(f'Build target for Mac: <b>{getLatestUnpublishedVersion("mac", versions)}</b>')
    g.html.BR()
    g.html.T(f'Build target for Windows: <b>{getLatestUnpublishedVersion("windows", versions)}</b>')
    g.html._P()


@typeworldserver.app.route("/admin", methods=["GET", "POST"])
def admin():

    if not g.admin:
        return abort(401)

    g.html.DIV(class_="content")

    g.html.area("Preferences")

    g.html.DIV()
    classes.Preference().new(text="+ Preference")
    g.html._DIV()

    g.html.TABLE()
    for preference in classes.Preference.query().fetch(read_consistency=ndb.STRONG):
        g.html.TR()
        g.html.TD()
        g.html.T(preference.name)
        g.html._TD()
        g.html.TD()
        g.html.T(preference.content)
        g.html._TD()
        g.html.TD()
        preference.edit(text='<span class="material-icons-outlined">edit</span>')
        preference.delete(text='<span class="material-icons-outlined">delete</span>')
        g.html._TD()
        g.html._TR()

    g.html._TABLE()

    g.html._area()

    g.html.area("Endpoint Admins")
    admins = []
    endpoints = classes.APIEndpoint.query().fetch(read_consistency=ndb.STRONG)
    userKeys = []
    for endpoint in endpoints:
        if endpoint.userKey:
            userKeys.append(endpoint.userKey)
            if not endpoint.endpointCommand:
                endpoint.updateJSON(force=True)
        if endpoint.endpointCommand:
            endpointCommand = typeworld.api.EndpointResponse()
            endpointCommand.loadDict(endpoint.endpointCommand)
            if endpointCommand.adminEmail not in admins:
                admins.append(endpointCommand.adminEmail)
    users = ndb.get_multi(userKeys)
    for user in users:
        if user:
            if user.email not in admins:
                admins.append(user.email)
    g.html.T(", ".join(admins))
    g.html._area()

    g.html.area("Users")

    g.html.P()
    g.html.T("Enter a user email address here to show their profile")
    g.html._P()
    g.html.P()
    g.html.textInput("useremail", type="text", placeholder="johndoe@gmail.com")
    g.html._P()
    g.html.P()
    g.html.A(
        class_="button",
        onclick="window.location.href='/user?email=' + $('#useremail').val();",
    )
    g.html.T("Show Profile")
    g.html._A()
    g.html._P()

    g.html._area()

    g.html._DIV()

    return g.html.generate()


@typeworldserver.app.route("/user", methods=["GET", "POST"])
@typeworldserver.app.route("/user/<userKey>", methods=["GET"])
def user(userKey=None):

    if not g.admin:
        return abort(401)

    if g.form._get("email"):
        user = classes.User.query(classes.User.email == g.form._get("email")).get(read_consistency=ndb.STRONG)
        if user:
            return redirect(f"/user/{user.publicID()}")

    if userKey:
        user = ndb.Key(urlsafe=userKey.encode()).get(read_consistency=ndb.STRONG)

        g.html.DIV(class_="content")

        g.html.area(user.email)
        g.html.P()
        g.html.A(
            class_="button",
            onclick=f"window.location.href='/impersonateuser?userKey={userKey}'",
        )
        g.html.T("Impersonate this user")
        g.html._A()

        g.html.A(
            class_="button",
            onclick=f"AJAX('#action', '/notifyuser?userKey={userKey}&inline=true');",
        )
        g.html.T("Notify user of account update")
        g.html._A()

        g.html._P()
        g.html._area()

        g.html.area("Plans")
        for productID in billing_stripe.stripeProducts:
            subscription = user.stripeSubscriptionByProductID(productID)

            g.html.P()
            g.html.B()
            g.html.T(productID)
            g.html._B()
            g.html.BR()
            if subscription:
                g.html.T(f"Status: {subscription['status']}")
            stripeSubscriptionPreviousRunningPeriodDays = (
                user.stripeSubscriptionPreviousRunningPeriodDays(productID) or 0
            )
            if stripeSubscriptionPreviousRunningPeriodDays:
                g.html.BR()
                g.html.T(f"Previously active: {stripeSubscriptionPreviousRunningPeriodDays} days")
            g.html._P()

        g.html._area()

        g.html.area("Linked App Instances")
        instances = user.appInstances()
        g.html.TABLE()
        for instance in instances:
            g.html.TR()
            g.html.TD()
            for key in (
                "machineModelIdentifier",
                "machineHumanReadableName",
                "machineSpecsDescription",
                "machineOSVersion",
                "machineNodeName",
                "revoked",
            ):
                g.html.T(getattr(instance, key))
                g.html.BR()
            g.html._TD()
            g.html.TD()
            instance.delete()
            g.html._TD()
            g.html._TR()
        g.html._TABLE()
        g.html._area()

        g.html.area("Total Subscriptions")
        subscriptions = user.subscriptions()
        g.html.TABLE()
        for subscription in subscriptions:
            g.html.TR()
            g.html.TD()
            g.html.T(subscription.url)
            g.html.BR()
            g.html.T(f"Type: {subscription.type}")
            g.html.BR()
            g.html.T(f"Confirmed: {subscription.confirmed}")
            g.html.BR()
            g.html.T(f"Invited by: {subscription.invitedByAPIEndpointKey or subscription.invitedByUserKey}")
            g.html._TD()
            g.html.TD()
            subscription.delete()
            g.html._TD()
            g.html._TR()
        g.html._TABLE()
        g.html._area()

        g.html.area("Received Invitations")
        invitations = user.subscriptionInvitations()
        g.html.TABLE()
        for invitation in invitations:
            g.html.TR()
            g.html.TD()
            g.html.T(invitation.url)
            g.html.BR()
            g.html.T(f"Invited by: {invitation.invitedByAPIEndpointKey or invitation.invitedByUserKey}")
            g.html._TD()
            g.html.TD()
            invitation.delete()
            g.html._TD()
            g.html._TR()
        g.html._TABLE()
        g.html._area()

        g.html.area("Sent Invitations")
        invitations = user.sentInvitations()
        g.html.TABLE()
        for invitation in invitations:
            g.html.TR()
            g.html.TD()
            g.html.T(invitation.url)
            g.html._TD()
            g.html.TD()
            invitation.delete()
            g.html._TD()
            g.html._TR()
        g.html._TABLE()
        g.html._area()

        g.html._DIV()

        return g.html.generate()


@typeworldserver.app.route("/impersonateuser", methods=["GET"])
def impersonateuser():

    if not g.admin:
        return abort(401)

    if g.form._get("userKey"):
        user = ndb.Key(urlsafe=g.form._get("userKey").encode()).get(read_consistency=ndb.STRONG)
        if user:
            typeworldserver.performLogout()
            typeworldserver.performLogin(user)
            return redirect("/")


@typeworldserver.app.route("/notifyuser", methods=["GET", "POST"])
def notifyuser():

    if not g.admin:
        return abort(401)

    if g.form._get("userKey"):
        user = ndb.Key(urlsafe=g.form._get("userKey").encode()).get(read_consistency=ndb.STRONG)
        if user:
            user.announceChange()
            g.html.info("User was notified")

    return g.html.generate()


@typeworldserver.app.route("/app/", methods=["GET", "POST"])
def _app():

    g.html.DIV(class_="content")

    ##################################################

    versions = getVersions()

    if g.admin:

        g.html.area("App Versions")

        web.container("viewLatestUnpublishedBuilds", directCallParameters={"versions": versions})

        g.html.smallSeparator()
        g.html.P()
        AppVersion().new(
            text="+ Add New Version",
            propertyNames=["version", "notes"],
            hiddenValues={"appID": "world.type.guiapp"},
        )
        g.html._P()

        g.html._area()

        g.html.mediumSeparator()

        # Output
        for version in versions:
            version.container("view", parameters={"platforms": platforms})

    ##################################################

    output = []

    g.html.T(
        """

<style>
.downloadlink {
    width: calc(50% - 80px);
    padding: 30px;
    margin-right: 20px;
    background-color: rgba(255, 255, 255, .5);
    border-radius:5px; -moz-border-radius:5px; -webkit-border-radius:5px; -khtml-border-radius:5px;

}

.downloadlink .download {
    text-align: center;
    margin-bottom: 30px;
}

.button.openintypeworld .icon {
    width: 22px;
    height: 22px;
    top: 5px;
    position: relative;
    margin-top: -6px;
    margin-right: 3px;
}

</style>
    """
    )

    g.html.DIV(class_="clear", style="width: 100%;")

    for platform in platforms:
        for version in versions:
            build = version.build(platform)
            if build.published and platform not in output:
                output.append(platform)

                g.html.DIV(class_="downloadlink floatleft")

                g.html.DIV(class_="text-align: center; width: 100%;")
                g.html.DIV(class_="download", style=" ")

                g.html.H5(style="margin-top: 20px; margin-bottom: 20px;")
                g.html.T(f"Type.World App for {platform.capitalize()}")
                g.html._H5()

                g.html.P()
                g.html.IMG(
                    src="/static/images/machineModels/other/%s.svg" % (platform.replace("mac", "apple")),
                    style="height: 100px;",
                )
                g.html._P()

                g.html.P()
                g.html.A(class_="button", href=build.mainDownloadLink())
                g.html.T(
                    '<span class="material-icons-outlined">download</span> Download'
                    f" Type.World for {platform.capitalize()}"
                )
                g.html._A()
                g.html._P()

                g.html._DIV()  # .floatcenter
                g.html._DIV()  # .center

                g.html.P()
                g.html.T(f"Version {version.version}. ")
                g.html.BR()

                if platform == "mac":
                    g.html.T("For macOS 10.14 or newer.")
                    g.html._P()
                    g.html.P()
                    g.html.T(
                        "After download, open the installer image (.dmg) and copy the app to your Applications folder."
                    )

                if platform == "windows":
                    g.html.T("For Windows 10 or newer.")
                    g.html._P()
                    g.html.P()
                    g.html.T('After the download started, click on "Execute" to start the installer.')
                    g.html._P()
                    g.html.P()
                    g.html.T(
                        "<b>Security Warning:</b> You may be presented with an"
                        " information screen warning you about security. This is a"
                        " normal security mechanism for Windows for files that are not"
                        " commonly downloaded. After this download has become more"
                        " popular, this warning will disappear."
                    )
                    # g.html.P()
                    # g.html.T(
                    #     f'The protocol to follow here ')
                    # g.html._P()
                g.html._P()

                g.html._DIV()  # .downloadlink

    g.html._DIV()  # .clear

    g.html.H2()
    g.html.T("Quick Start: Access Your First Font Subscription")
    g.html._H2()

    g.html.DIV(class_="clear")
    g.html.DIV(class_="floatleft", style="width: 300px; margin-right: 40px; line-height: 12px;")
    g.html.IMG(
        src="/static/images/jenskutilekssubscriptions/file.svg",
        style="width: 150px; height: 150px; background-color: white;",
    )
    g.html.IMG(
        src="/static/images/jenskutilekssubscriptions/file-2.svg",
        style="width: 150px; height: 150px; background-color: white;",
    )
    g.html.IMG(
        src="/static/images/jenskutilekssubscriptions/file-1.svg",
        style="width: 150px; height: 150px; background-color: white;",
    )
    g.html.IMG(
        src="/static/images/jenskutilekssubscriptions/file-3.svg",
        style="width: 150px; height: 150px; background-color: white;",
    )
    g.html._DIV()  # .floatleft
    g.html.DIV(class_="floatleft", style="width: calc(100% - 350px);")
    g.html.P()
    g.html.T(
        "For a demonstration of a font subscription that contains only free fonts,"
        " please have a look at Jens Kutílek’s Free Fonts."
    )
    g.html._P()
    g.html.P()
    g.html.T("After you have installed the app, click on the button below to load the subscription into the app.")
    g.html._P()
    g.html.P()
    g.html.A(
        class_="button openintypeworld",
        href="typeworld://json+https//www.kutilek.de/typeworld/index.json",
    )
    g.html.IMG(class_="icon", src="/static/images/typeworld_smallicon.svg")
    g.html.T(" Open in Type.World App")
    g.html._A()
    g.html._P()
    g.html._DIV()  # .floatleft
    g.html._DIV()  # .clear

    g.html.H2()
    g.html.T("Version History")
    g.html._H2()

    for version in versions:
        for build in version.builds():
            if build.published or build.publishedForDevelopers and version.notes:

                g.html.H3()
                g.html.T(f"Version {version.version}")
                g.html._H3()

                g.html.P()
                g.html.T(f'Published: {build.buildCompletedTime.strftime("%c")} +0000')
                g.html._P()

                g.html.T(markdown2.markdown(version.notes))

                break

    g.html.P()
    g.html.T("To access a font subscription demo, click ")
    g.html.A(href="typeworld://json+https//typeworldserver.com/flatapi/bZA2JbWHEAkFjako0Mtz/")
    g.html.T("here")
    g.html._A()
    g.html.T(" after installing the app.")
    g.html._P()

    g.html._DIV()

    return g.html.generate()


@typeworldserver.app.route("/appcast/<appKey>/<platform>/<profile>/appcast.xml", methods=["GET"])
def appcast(appKey, platform, profile):

    xml = """<?xml version="1.0" standalone="yes"?>
<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle" version="2.0">
<channel>
    <title>Type.World</title>"""
    versions = getVersions()
    for version in versions:
        build = version.build(platform)
        if build.published or profile == "developer" and build.publishedForDevelopers:
            xml += build.appcastXML(versions, platform, profile)
    xml += """
</channel>
</rss>"""

    return Response(xml, mimetype="application/xml")


def countDownload(url):
    pass


developerTabs = [
    ["/developer", '<span class="material-icons-outlined">description</span> Docs'],
    [
        "/developer/protocol",
        '<span class="material-icons-outlined">schema</span> Protocol',
    ],
    [
        "/developer/myapps",
        '<span class="material-icons-outlined">app_registration</span> My Apps',
    ],
    ["/developer/api", '<span class="material-icons-outlined">smart_toy</span> API'],
    [
        "/developer/validate",
        '<span class="material-icons-outlined">checklist</span> Validate',
    ],
    [
        "/developer/prices",
        '<span class="material-icons-outlined">receipt</span> Prices',
    ],
    [
        "/developer/billing",
        '<span class="material-icons-outlined">credit_card</span> Billing',
    ],
]


@typeworldserver.app.route("/developer/protocol", methods=["POST", "GET"])
@typeworldserver.app.route("/developer/protocol/", methods=["POST", "GET"])
def developer_protocol():

    g.html.tabs(developerTabs, "/developer/protocol")

    g.html.DIV(class_="content")

    g.html.P()
    g.html.T(
        "For the time being, you will find the Type.World JSON Protocol definition"
        " under the link below.<br />Later I will incorporate that document into this"
        " page right here."
    )
    g.html._P()

    g.html.P()
    g.html.A(
        class_="button",
        href="https://github.com/typeworld/typeworld/tree/main/Lib/typeworld/api",
        target="_blank",
    )
    g.html.T("Open github.com/typeworld/typeworld")
    g.html._A()
    g.html._P()

    g.html._DIV()

    return g.html.generate()


@typeworldserver.app.route("/developer", methods=["POST", "GET"])
@typeworldserver.app.route("/developer/", methods=["POST", "GET"])
def developer_docs():

    g.html.tabs(developerTabs, "/developer")

    g.html.DIV(class_="content", style="width: 1200px;")

    blob = typeworldserver.bucket.get_blob("developer/index.md")
    text = blob.download_as_string().decode()

    html = markdown.markdown(text)

    # html_withtoc = markdown.markdown("[TOC]\n" + text, extensions=[TocExtension(toc_depth="1-2")])

    # i = html_withtoc.find("<h1 id=")
    # html = html_withtoc[i:]
    # toc = html_withtoc[:i]

    # dt_object = (blob.updated or blob.time_created).strftime("%c")
    # html = html.replace("%timestamp%", dt_object + " +0000")

    # # Add scroll detection areas
    # for tag in ("h1", "h2"):
    #     html = html.replace(f"<{tag}", f'</div><div class="scrolldetection"><{tag}')
    # html = '<div class="scrolldetection">' + html + "</div>"

    # toc = toc.replace('<a id="#', '<a id="')

    # # Add links
    # for tag in ("h1", "h2"):
    #     html = html.replace(
    #         f"</{tag}>",
    #         '<span><a class="permalink" title="">#</a> <a title="Scroll to top"'
    #         " onclick=\"$('html, body').animate({scrollTop: 0}, 500);"
    #         " history.pushState(stateObj, '',"
    #         f" '/developer');\">↑</a></span></{tag}>",
    #     )

    # g.html.DIV(class_="tocwrapper stickToTheTop")
    # g.html.T(toc)
    # g.html._DIV()

    g.html.DIV(class_="doc")
    g.html.T(html)
    g.html._DIV()

    # g.html._DIV() #.clear

    g.html._DIV()

    # g.html.STYLE()
    # g.html.T(
    #     """

    # """
    # )
    # g.html._STYLE()

    g.html.SCRIPT()
    g.html.T(
        """


function makeLink(a, id) {
a.attr('href', '/developer#' + id);
a.attr('title', 'Permalink to #' + id);
}

function makeScrollDetection(div, id) {
div.attr('id', id);
}

const stateObj = { foo: 'bar' };

$(document).ready(function() {

// Add permalinks to titles
$(".doc h1").each(function(index) {
    makeLink($(this).find('span a.permalink'), $(this).attr("id"));
});

$(".doc h2").each(function(index) {
    makeLink($(this).find('span a.permalink'), $(this).attr("id"));
});

$(".toc a").each(function(index) {
    $(this).attr('id', $(this).attr("href").slice(1));
    $(this).removeAttr("href");
});

$(".toc a").click(function() {
    history.pushState(stateObj, '', '/developer');
    $("html, body").animate({scrollTop: $('div#' + $(this).attr('id')).offset().top - 20}, 500);
});

$(".doc h1").each(function(index) {
    makeScrollDetection($(this).parent(), $(this).attr("id"));
});
$(".doc h2").each(function(index) {
    makeScrollDetection($(this).parent(), $(this).attr("id"));
});

});



        """
    )

    g.html._SCRIPT()

    g.html.SCRIPT()
    g.html.T(
        """

function track() {
    mostVisible = $(".scrolldetection").mostVisible();
    if (mostVisible) {
        console.log(mostVisible);
        $(".toc a").removeClass("selected");
        console.log($(".toc a#" + mostVisible.attr("id") + ""));
        $(".toc a#" + mostVisible.attr("id") + "").addClass("selected");
    }
    else {
        $("tr.visibilityChange").removeClass("selected");
    }
}

$( window ).scroll(function() {
track();
});

track();

"""
    )
    g.html._SCRIPT()

    return g.html.generate()


@typeworldserver.app.route("/developer/docs/fontdistribution", methods=["POST", "GET"])
@typeworldserver.app.route("/developer/docs/fontdistribution/", methods=["POST", "GET"])
def developer_docs_fontdistribution():

    g.html.tabs(developerTabs, "/developer", activeIsClickable=True)

    g.html.DIV(class_="content", style="width: 1200px;")

    blob = typeworldserver.bucket.get_blob("developer/fontdistribution.md")
    text = blob.download_as_string().decode()

    from markdown.extensions.toc import TocExtension

    html_withtoc = markdown.markdown("[TOC]\n" + text, extensions=[TocExtension(toc_depth="1-2")])

    i = html_withtoc.find("<h1 id=")
    html = html_withtoc[i:]
    toc = html_withtoc[:i]

    dt_object = (blob.updated or blob.time_created).strftime("%c")
    html = html.replace("%timestamp%", dt_object + " +0000")

    # Add scroll detection areas
    for tag in ("h1", "h2"):
        html = html.replace(f"<{tag}", f'</div><div class="scrolldetection"><{tag}')
    html = '<div class="scrolldetection">' + html + "</div>"

    toc = toc.replace('<a id="#', '<a id="')

    # Add links
    for tag in ("h1", "h2"):
        html = html.replace(
            f"</{tag}>",
            '<span><a class="permalink" title="">#</a> <a title="Scroll to top"'
            " onclick=\"$('html, body').animate({scrollTop: 0}, 500);"
            " history.pushState(stateObj, '',"
            f" '/developer');\">↑</a></span></{tag}>",
        )

    g.html.DIV(class_="tocwrapper stickToTheTop")
    g.html.T(toc)
    g.html._DIV()

    g.html.DIV(class_="doc")
    g.html.T(html)
    g.html._DIV()

    # g.html._DIV() #.clear

    g.html._DIV()

    # g.html.STYLE()
    # g.html.T(
    #     """

    # """
    # )
    # g.html._STYLE()

    g.html.SCRIPT()
    g.html.T(
        """


function makeLink(a, id) {
a.attr('href', '/developer#' + id);
a.attr('title', 'Permalink to #' + id);
}

function makeScrollDetection(div, id) {
div.attr('id', id);
}

const stateObj = { foo: 'bar' };

$(document).ready(function() {

// Add permalinks to titles
$(".doc h1").each(function(index) {
    makeLink($(this).find('span a.permalink'), $(this).attr("id"));
});

$(".doc h2").each(function(index) {
    makeLink($(this).find('span a.permalink'), $(this).attr("id"));
});

$(".toc a").each(function(index) {
    $(this).attr('id', $(this).attr("href").slice(1));
    $(this).removeAttr("href");
});

$(".toc a").click(function() {
    history.pushState(stateObj, '', '/developer');
    $("html, body").animate({scrollTop: $('div#' + $(this).attr('id')).offset().top - 20}, 500);
});

$(".doc h1").each(function(index) {
    makeScrollDetection($(this).parent(), $(this).attr("id"));
});
$(".doc h2").each(function(index) {
    makeScrollDetection($(this).parent(), $(this).attr("id"));
});

});



        """
    )

    g.html._SCRIPT()

    g.html.SCRIPT()
    g.html.T(
        """

function track() {
    mostVisible = $(".scrolldetection").mostVisible();
    if (mostVisible) {
        console.log(mostVisible);
        $(".toc a").removeClass("selected");
        console.log($(".toc a#" + mostVisible.attr("id") + ""));
        $(".toc a#" + mostVisible.attr("id") + "").addClass("selected");
    }
    else {
        $("tr.visibilityChange").removeClass("selected");
    }
}

$( window ).scroll(function() {
track();
});

track();

"""
    )
    g.html._SCRIPT()

    return g.html.generate()


@typeworldserver.app.route("/developer/docs/signin", methods=["POST", "GET"])
@typeworldserver.app.route("/developer/docs/signin/", methods=["POST", "GET"])
def developer_docs_signin():

    g.html.tabs(developerTabs, "/developer", activeIsClickable=True)

    g.html.DIV(class_="content", style="width: 1200px;")

    blob = typeworldserver.bucket.get_blob("developer/signin.md")
    text = blob.download_as_string().decode()

    from markdown.extensions.toc import TocExtension

    html_withtoc = markdown.markdown("[TOC]\n" + text, extensions=[TocExtension(toc_depth="1-2")])

    i = html_withtoc.find("<h1 id=")
    html = html_withtoc[i:]
    toc = html_withtoc[:i]

    dt_object = (blob.updated or blob.time_created).strftime("%c")
    html = html.replace("%timestamp%", dt_object + " +0000")

    # Add scroll detection areas
    for tag in ("h1", "h2"):
        html = html.replace(f"<{tag}", f'</div><div class="scrolldetection"><{tag}')
    html = '<div class="scrolldetection">' + html + "</div>"

    toc = toc.replace('<a id="#', '<a id="')

    # Add links
    for tag in ("h1", "h2"):
        html = html.replace(
            f"</{tag}>",
            '<span><a class="permalink" title="">#</a> <a title="Scroll to top"'
            " onclick=\"$('html, body').animate({scrollTop: 0}, 500);"
            " history.pushState(stateObj, '',"
            f" '/developer');\">↑</a></span></{tag}>",
        )

    g.html.DIV(class_="tocwrapper stickToTheTop")
    g.html.T(toc)
    g.html._DIV()

    g.html.DIV(class_="doc")
    g.html.T(html)
    g.html._DIV()

    # g.html._DIV() #.clear

    g.html._DIV()

    # g.html.STYLE()
    # g.html.T(
    #     """

    # """
    # )
    # g.html._STYLE()

    g.html.SCRIPT()
    g.html.T(
        """


function makeLink(a, id) {
a.attr('href', '/developer#' + id);
a.attr('title', 'Permalink to #' + id);
}

function makeScrollDetection(div, id) {
div.attr('id', id);
}

const stateObj = { foo: 'bar' };

$(document).ready(function() {

// Add permalinks to titles
$(".doc h1").each(function(index) {
    makeLink($(this).find('span a.permalink'), $(this).attr("id"));
});

$(".doc h2").each(function(index) {
    makeLink($(this).find('span a.permalink'), $(this).attr("id"));
});

$(".toc a").each(function(index) {
    $(this).attr('id', $(this).attr("href").slice(1));
    $(this).removeAttr("href");
});

$(".toc a").click(function() {
    history.pushState(stateObj, '', '/developer');
    $("html, body").animate({scrollTop: $('div#' + $(this).attr('id')).offset().top - 20}, 500);
});

$(".doc h1").each(function(index) {
    makeScrollDetection($(this).parent(), $(this).attr("id"));
});
$(".doc h2").each(function(index) {
    makeScrollDetection($(this).parent(), $(this).attr("id"));
});

});



        """
    )

    g.html._SCRIPT()

    g.html.SCRIPT()
    g.html.T(
        """

function track() {
    mostVisible = $(".scrolldetection").mostVisible();
    if (mostVisible) {
        console.log(mostVisible);
        $(".toc a").removeClass("selected");
        console.log($(".toc a#" + mostVisible.attr("id") + ""));
        $(".toc a#" + mostVisible.attr("id") + "").addClass("selected");
    }
    else {
        $("tr.visibilityChange").removeClass("selected");
    }
}

$( window ).scroll(function() {
track();
});

track();

"""
    )
    g.html._SCRIPT()

    return g.html.generate()


@typeworldserver.app.route("/developer/prices/", methods=["POST", "GET"])
@typeworldserver.app.route("/developer/prices", methods=["POST", "GET"])
def developer_prices():

    g.html.tabs(developerTabs, "/developer/prices")

    contract = classes.APIEndpointContract()
    prices = definitions.PRODUCTS

    textfields = []
    for price in prices:
        for key, text in prices[price]["textfields"]:
            textfields.append(key)

    j = f"""

textfields = ['{"', '".join(textfields)}'];

function url() {{
    parts = [];
    make_url = window.location.href.split("?")[0] + '?';
    textfields.forEach(element => {{
        if ($("#"+element).val()) {{
            parts.push(element + "=" + $("#"+element).val());
        }}
    }});
    if ($("#currencyConverter").val() != "undefined") {{
        parts.push("currency=" + $("#currencyConverter").val())
    }}
    make_url += parts.join("&");
    return make_url;
}}

function reloadPage() {{
    make_url = url();
    AJAX("#stage", make_url + "&inline=true");

     window.history.pushState({{"html":null,"pageTitle":null}},"", make_url);

}}


$( document ).ready(function() {{
    resize();
}});

    """

    def calculateSum(price):
        for key, text in price["textfields"]:
            exec(f"{key}={g.form._get(key) or 0}")
        sum = eval(price["calculation"])
        return sum

    g.html.SCRIPT()
    g.html.T(j)
    g.html._SCRIPT()

    g.html.DIV(class_="content", style="width: 1200px;")
    g.html.DIV(class_="clear")
    g.html.DIV(style="width: 400px; margin-top: 15px;", class_="floatright stickToTheTop")  # summary

    g.html.area("Calculation Summary")

    g.html.smallSeparator()

    g.html.TABLE()
    g.html.TR()
    g.html.TH(style="width: 60%;")
    g.html.T("Category")
    g.html._TH()
    g.html.TH(style="width: 40%;")
    g.html.T("Monthly Costs")
    g.html._TH()
    g.html._TR()

    def modifiedBill(totalusers):

        # Set up input
        quantityByCategory = {}
        for price in prices:
            quantityByCategory[price] = calculateSum(prices[price])

        # modify
        q = int(int(g.form._get("averagesales") or 0) + totalusers)
        quantityByCategory["subscriptionUpdateWithAddedFonts"] = q

        # Create bill
        bill = contract.billingCalculation(quantityByCategory)

        return bill

    # Create bills
    # rollout = modifiedBill(int(g.form._get("totalusers") or 0))
    running = modifiedBill(0)

    complete = 0
    available = 0
    for category in prices:
        if prices[category]["visible"]:
            for textfieldID, textfieldDesc in prices[category]["textfields"]:
                available += 1
                if g.form._get(textfieldID) is not None:
                    complete += 1
    # allFieldsCompleted = complete == available

    #        Returns dict {"positions": [[category, name, quantity, freeQuota, quantityAfterFreeQuota,
    # singlePrice, sum]], "total": 0.0}

    for i, position in enumerate(running["positions"]):

        if prices[position[0]]["visible"]:

            g.html.TR(class_=f"visibilityChange {position[0]}")
            g.html.TD()
            g.html.A(onclick=f"$('html, body').animate({{scrollTop: $('#{position[0]}').offset().top - 20}}, 500);")
            g.html.T(running["positions"][i][1])
            g.html._A()
            g.html._TD()

            complete = 0
            for textfieldID, textfieldDesc in prices[position[0]]["textfields"]:
                if g.form._get(textfieldID) is not None:
                    complete += 1

            g.html.TD()
            if complete < len(prices[position[0]]["textfields"]):
                g.html.SPAN(
                    class_="warning",
                    title="Fill out this value to complete the calculation",
                )
                g.html.T("▲")
                g.html.T("%.2f&thinsp;€" % running["positions"][i][6])
                g.html._SPAN()
            else:
                g.html.T("%.2f&thinsp;€" % running["positions"][i][6])
            g.html._TD()
            g.html._TR()

    g.html.TR()
    g.html.TD(style="font-weight: bold;")
    g.html.T("Total ex. VAT")
    g.html._TD()
    g.html.TD(style="font-weight: bold;")
    g.html.T("%.2f&thinsp;€" % running["total"])
    g.html._TD()
    g.html._TR()

    currency = g.form._get("currency")
    if currency in currencyConverter.currencies:
        g.html.TR()
        g.html.TD(style="font-style: italic;")
        g.html.T(f"Total ex. VAT ({currency})")
        g.html._TD()
        g.html.TD(style="font-style: italic;")
        g.html.T("%.2f&thinsp;%s" % (currencyConverter.convert(running["total"], "EUR", currency), currency))
        g.html._TD()
        g.html._TR()
    g.html._TABLE()

    # Currency Converter
    g.html.mediumSeparator()
    g.html.P()
    g.html.T("Currency Converter (FYI):")
    g.html._P()
    g.html.P()
    g.html.SELECT(id="currencyConverter", onchange="reloadPage();")
    g.html.OPTION(value="undefined")
    g.html.T("Choose Currency...")
    g.html._OPTION()
    currencies = sorted(list(currencyConverter.currencies))
    northAmerica = ("North America", ["USD", "CAD"])
    europe = (
        "Europe",
        [
            "ALL",
            "AMD",
            "AZN",
            "BYN",
            "BAM",
            "BGN",
            "HRK",
            "CZK",
            "DKK",
            "GEL",
            "HUF",
            "ISK",
            "CHF",
            "MDL",
            "MKD",
            "NOK",
            "PLN",
            "RON",
            "RUB",
            "RSD",
            "SEK",
            "TRY",
            "UAH",
            "GBP",
        ],
    )
    # Regional
    for region, regionalCurrencies in (northAmerica, europe):
        g.html.OPTGROUP(label=region)
        regionalCurrencies = sorted(regionalCurrencies)
        for currency in regionalCurrencies:
            if currency in currencies:
                g.html.OPTION(value=currency, selected=g.form._get("currency") == currency)
                g.html.T(currency)
                g.html._OPTION()
                currencies.remove(currency)
        g.html._OPTGROUP()
    # Other
    g.html.OPTGROUP(label="Other")
    for currency in currencies:
        g.html.OPTION(value=currency, selected=g.form._get("currency") == currency)
        g.html.T(currency)
        g.html._OPTION()
    g.html._OPTGROUP()
    g.html._SELECT()
    g.html._P()
    g.html.P()
    g.html.T(
        "Rates are provided by the European Central Bank and come without warranty.<br />Bills are in EUR regardless."
    )
    g.html._P()
    g.html._area()

    # MAIN PART

    g.html._DIV()  # .floatright # summary
    g.html.DIV(style="width: 750px; margin-right: 20px;", class_="floatright")

    g.html.DIV(style="padding: 20px;")
    g.html.H2()
    g.html.T("Monthly Cost Calculator for Publishers")
    g.html._H2()
    g.html.P()
    g.html.T(
        "With Type.World essentially being a cloud technology provider, it will bill"
        " its customers (font publishers) by transactions on the system as outlined"
        " below. </p><p><b>Why billing?</b> Please make sure to read the <a"
        ' href="/developer#free-vs-paid">Free vs. Paid</a> and <a'
        ' href="/developer#costs">Costs</a> sections in the Developer Information page'
        " to understand what you are being billed for and why, given that Type.World is"
        " an open source project. The gist of it: Basic usage of the system is free,"
        " and only certain professional convenience features cost us real money and are"
        " therefore being billed to publishers as well as end users.</p><p><b>6 Months"
        " Free Trial Period:</b> You’ll get ample time for developing your Type.World"
        " integration with a <em>6-month free trial period</em>. Make sure to fit the"
        " initial onboarding of all your existing customer’s user accounts into this"
        " period to avoid higher roll-out costs. </p><p><b>VAT:</b> Customers in the"
        " European Union need to add VAT which is either 19% German VAT or provide"
        " their VAT ID number and then pay VAT to their own respective country of"
        " residence. Customers outside of the European Union are exempted from paying"
        " VAT on these prices.</p><p><b>Price Calculation</b>: Each metric’s prices are"
        " calculated using a graduated price scale. Each metric’s price is a summation"
        " of each tier bracket’s quota until the final amount has been"
        " reached.</p><p><b>Tip:</b> Your input gets appended to the browser URL. You"
        " can copy the URL to send a filled sample calculation to your"
        " colleagues.</p><p><b>Privacy Notice:</b> The values you put into the"
        " calculation below are anonymous and don’t get stored on server."
    )
    g.html._P()
    g.html._DIV()
    g.html.smallSeparator()
    g.html.smallSeparator()

    for price in prices:

        if prices[price]["visible"]:
            g.html.area(prices[price]["name"], id_=price, class_="scheme1 priceCategories")

            # Create bill
            quantityByCategory = {}
            quantityByCategory[price] = calculateSum(prices[price])
            actualCalculationBill = contract.billingCalculation(quantityByCategory)
            assert len(actualCalculationBill["positions"]) == 1
            (category, name, freeQuota, quantity, tiers, singlePrice, singleTotal,) = actualCalculationBill[
                "positions"
            ][0]

            if "definition" in prices[price] and prices[price]["definition"]:
                g.html.P()
                g.html.T("<b>Definition:</b>")
                g.html._P()
                g.html.P()
                g.html.T(prices[price]["definition"])
                g.html._P()
                g.html.mediumSeparator()

            if freeQuota:
                g.html.P()
                g.html.T(f"Free monthly quota: <b>{freeQuota}</b>")
                g.html._P()
                g.html.mediumSeparator()

            if "description" in prices[price] and prices[price]["description"]:
                g.html.P()
                g.html.T("<b>Description:</b>")
                g.html._P()
                g.html.P()
                g.html.T(prices[price]["description"])
                g.html._P()
                g.html.mediumSeparator()

            # Input fields

            g.html.P()
            g.html.T("<b>Example Calculation:</b>")
            g.html._P()

            if "calculationDescription" in prices[price] and prices[price]["calculationDescription"]:
                g.html.P()
                g.html.T(prices[price]["calculationDescription"])
                g.html._P()

            g.html.P()

            for key, text in prices[price]["textfields"]:
                if g.form._get(key) is None:
                    g.html.SPAN(class_="warning")
                    g.html.T("▲ ")
                    g.html.T(text)
                    g.html.BR()
                    g.html.T("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(Enter 0 if not applicable)")
                    g.html._SPAN()
                else:
                    g.html.T(text)
                g.html.BR()
                g.html.textInput(
                    key,
                    value=g.form._get(key),
                    type="text",
                    placeholder="0",
                    focusForFirstFormElement=False,
                )
            g.html.A(class_="button", onclick="reloadPage();")
            g.html.T("Update Calculation")
            g.html._A()
            g.html._P()

            if quantity and len(prices[price]["textfields"]) > 1:
                g.html.separator()
                g.html.P()
                g.html.T(f"Quantity used for calculation: <b>{quantity}</b>")
                g.html._P()

            g.html.separator()
            g.html.P()
            g.html.T("<b>Price List:</b>")
            g.html._P()
            g.html.smallSeparator()

            g.html.TABLE()
            g.html.TR()
            g.html.TH()
            g.html.T("Tier")
            g.html._TH()
            g.html.TH()
            if quantity:
                g.html.T("Calculation")
            else:
                g.html.T("Unit Price")
            g.html._TH()
            if quantity:
                g.html.TH()
                g.html.T("Price")
                g.html._TH()
            g.html._TR()

            for i, tier in enumerate(prices[price]["tiers"]):

                g.html.TR()
                g.html.TD()

                if i <= len(tiers) - 1:
                    qty = tiers[i]["quantity"]
                else:
                    qty = 0

                tier = prices[price]["tiers"][i]
                if i > 0:
                    previousTier = prices[price]["tiers"][i - 1]
                else:
                    previousTier = None

                if tier["quantity"] > 0:
                    if previousTier:
                        g.html.T("%s to %s" % (previousTier["quantity"] + 1, tier["quantity"]))
                    else:
                        g.html.T("%s to %s" % (1, tier["quantity"]))
                else:
                    g.html.T("%s to %s" % (previousTier["quantity"] + 1, "infinity"))

                g.html._TD()
                g.html.TD()
                if tier["price"]:
                    if qty:
                        g.html.B()
                        g.html.T(f"{qty}")
                        g.html._B()
                        g.html.T(" × ")
                    g.html.T("%.5f€" % tier["price"])
                else:
                    if qty:
                        g.html.B()
                        g.html.T(f"{qty}")
                        g.html._B()
                        g.html.T(" × ")
                    g.html.T("free")
                g.html._TD()
                if quantity:
                    g.html.TD()
                    if tiers[i]["price"]:
                        g.html.T("%.5f€" % tiers[i]["price"])
                    g.html._TD()
                g.html._TR()

            if quantity:
                g.html.TR()
                g.html.TD()
                g.html._TD()
                g.html.TD()
                g.html._TD()
                g.html.TD()
                g.html.B()
                g.html.T("Sum:")
                g.html.BR()
                g.html.T("%.5f€" % singleTotal)
                g.html._B()
                g.html._TD()
                g.html._TR()

            g.html._TABLE()

            #             # Graphs
            #             if False:
            #                 g.html.T("""<script type="text/javascript"
            # src="https://www.gstatic.com/charts/loader.js"></script>""")
            #                 g.html.T('''

            #     <div id="''' + price + '''_singlepriceprogression_chart" style="width: 100%; height: 500px"></div>
            #     <div id="''' + price + '''_priceprogression_chart" style="width: 100%; height: 500px"></div>

            #     <script type="text/javascript">

            # google.charts.load('current', {packages: ['corechart', 'line']});
            # google.charts.setOnLoadCallback(drawBasic);

            # function drawBasic() {

            #     var datasingle = new google.visualization.DataTable();
            #     datasingle.addColumn('number', 'Quantity');
            #     datasingle.addColumn('number', 'Price');

            #     var data = new google.visualization.DataTable();
            #     data.addColumn('number', 'Quantity');
            #     data.addColumn('number', 'Price');

            #     ''')

            #                 for i in range(0, int(prices[price]["tiers"][-2]["quantity"]*1.2), int(prices[price]
            # ["tiers"][-2]["quantity"] / 100)):

            #                     quantityByCategory = {}
            #                     quantityByCategory[price] = i

            #                     # Create bill
            #                     bill = contract.billingCalculation(quantityByCategory)
            #                     assert len(bill["positions"]) == 1

            #                     category, name, freeQuota, quantity, tiers, singlePrice, singleTotal =
            # bill["positions"][0]

            #                     g.html.T(f"datasingle.addRows([[{i}, {singlePrice}]]);")
            #                     g.html.T(f"data.addRows([[{i}, {bill['total']}]]);")

            #                 g.html.T('''

            #         var chartsingle = new google.visualization.LineChart(document.getElementById("''' + price +
            # '''_singlepriceprogression_chart"));
            #         chartsingle.draw(datasingle, {
            #         hAxis: {
            #         title: 'Quantity'
            #         },
            #         vAxis: {
            #         title: 'Single Quantity Price'
            #         }
            #     });

            #         var chart = new google.visualization.LineChart(document.getElementById("''' + price +
            # '''_priceprogression_chart"));
            #         chart.draw(data, {
            #         hAxis: {
            #         title: 'Quantity'
            #         },
            #         vAxis: {
            #         title: 'Total Price'
            #         }
            #     });
            #     }
            #     </script>
            #                 ''')

            g.html._area()

    g.html._DIV()  # .floatright

    g.html._DIV()  # .clear

    g.html._DIV()  # .content

    g.html.SCRIPT()
    g.html.T(
        """

function track() {
mostVisible = $(".priceCategories").mostVisible();
if (mostVisible) {
    $("tr.visibilityChange").removeClass("selected");
    $("tr." + mostVisible.attr("id") + ".visibilityChange").addClass("selected");
}
else {
    $("tr.visibilityChange").removeClass("selected");
}
}

$( window ).scroll(function() {
track();
});

track();

"""
    )
    g.html._SCRIPT()

    return g.html.generate()


@typeworldserver.app.route("/developer/api/", methods=["POST", "GET"])
@typeworldserver.app.route("/developer/api", methods=["POST", "GET"])
def developer_api():

    g.html.tabs(developerTabs, "/developer/api")

    displayAPIKey = None
    if g.user:
        endpoints = g.user.APIEndpoints()
        if endpoints:
            displayAPIKey = endpoints[0].APIKey

    MOTHERSHIP = "https://api.type.world/v1"

    from pygments import highlight
    from pygments.lexers import PythonLexer, JsonLexer
    from pygments.formatters import HtmlFormatter

    g.html.T("<style>")
    g.html.T(HtmlFormatter().get_style_defs(".highlight"))
    g.html.T(
        """
        .highlight {
        max-width: 100%;
        overflow-x: auto;
        padding: 10px;
        }

        """
    )
    g.html.T("</style>")

    g.html.DIV(class_="content")

    g.html.P()
    g.html.T(
        "The Type.World service operates its own API, and if you’re a font publisher of"
        " sorts who serves their own fonts under the Type.World JSON Protocol, chances"
        " are you want to interact with the central Type.World server using the API"
        " calls documented here."
    )
    g.html._P()

    commands = definitions.APICOMMANDS

    for commandName in commands:

        command = commands[commandName]

        if command["public"] or g.admin:

            g.html.A(name=commandName)
            g.html._A()

            g.html.mediumSeparator()

            g.html.area(
                ("HIDDEN: " if command["public"] is False and g.admin else "") + commandName,
                class_="whitescheme" if command["public"] else "scheme1",
            )

            if "description" in command:
                g.html.P()
                g.html.T(markdown.markdown(command["description"]))
                g.html._P()
                # g.html.P()
                # g.html.T('Allowed request methods: <b>%s</b>' % '</b>, <b>'.join(command['methods']))
                # g.html._P()

            g.html.mediumSeparator()
            g.html.P()
            g.html.T("<em>Parameters: </em>")
            g.html._P()
            g.html.P()
            g.html.TABLE()
            # g.html.TR()
            # g.html.TD()
            # g.html.T(markdown.markdown('`command`'))
            # g.html._TD()
            # g.html.TD()
            # g.html.T(markdown.markdown('**Required**'))
            # g.html._TD()
            # g.html.TD()
            # g.html.T(markdown.markdown(f'`{commandName}`'))
            # g.html._TD()
            # g.html._TR()

            if "parameters" in command:

                for key in command["parameters"]:
                    g.html.TR()
                    g.html.TD()
                    g.html.T(markdown.markdown("`%s`" % (key)))
                    g.html._TD()
                    g.html.TD()
                    if command["parameters"][key]["required"]:
                        g.html.T(markdown.markdown("**Required**"))
                    g.html._TD()
                    g.html.TD()
                    g.html.T(markdown.markdown(command["parameters"][key]["description"]))
                    g.html._TD()
                    g.html._TR()

            g.html._TABLE()

            g.html._P()

            if "return" in command:

                g.html.P()
                g.html.T("<em>Return value: </em>")
                g.html._P()

                if type(command["return"]) == str:
                    if command["return"]:
                        g.html.T(markdown.markdown(command["return"]))
                    else:
                        g.html.T("No return value")

                elif type(command["return"]) in (dict, collections.OrderedDict):
                    g.html.P()
                    g.html.TABLE()
                    if "success" not in command["return"]:
                        g.html.TR()
                        g.html.TD()
                        g.html.T(markdown.markdown("`success`"))
                        g.html._TD()
                        g.html.TD()
                        g.html.T("The request returned successfully")
                        g.html._TD()
                        g.html._TR()
                    for returnValueKey in command["return"].keys():
                        g.html.TR()
                        g.html.TD()
                        g.html.T(markdown.markdown(f"`{returnValueKey}`"))
                        g.html._TD()
                        g.html.TD()
                        g.html.T(markdown.markdown(command["return"][returnValueKey]))
                        g.html._TD()
                        g.html._TR()
                    g.html._TABLE()
                    g.html._P()

            if "additionalReturn" in command:

                g.html.P()
                g.html.T("<em>Additionally, the response contains the following data: </em>")
                g.html._P()

                if type(command["additionalReturn"]) == str:
                    if command["additionalReturn"]:
                        g.html.T(markdown.markdown(command["additionalReturn"]))
                    else:
                        g.html.T("No return value")

                elif type(command["additionalReturn"]) in (
                    dict,
                    collections.OrderedDict,
                ):
                    g.html.P()
                    g.html.TABLE()
                    # if not 'success' in command['additionalReturn']:
                    # 	g.html.TR()
                    # 	g.html.TD()
                    # 	g.html.T('success')
                    # 	g.html._TD()
                    # 	g.html.TD()
                    # 	g.html.T('The request returned successfully')
                    # 	g.html._TD()
                    # 	g.html._TR()
                    for returnValueKey in command["additionalReturn"].keys():
                        g.html.TR()
                        g.html.TD()
                        g.html.T(markdown.markdown(f"`{returnValueKey}`"))
                        g.html._TD()
                        g.html.TD()
                        g.html.T(markdown.markdown(command["additionalReturn"][returnValueKey]))
                        g.html._TD()
                        g.html._TR()
                    g.html._TABLE()
                    g.html._P()

            if "exampleParameters" in command:

                g.html.mediumSeparator()

                g.html.P()
                g.html.T("Python 3 Example:")
                g.html._P()

                import pprint

                pp = pprint.PrettyPrinter(indent=4)
                parameters = command["exampleParameters"]

                if displayAPIKey and "APIKey" in parameters:
                    parameters["APIKey"] = displayAPIKey

                parameters = pp.pformat(dict(parameters))  # .replace('\n', ' \\\n')

                if displayAPIKey:
                    parameters = parameters.split("\n")
                    for i, line in enumerate(parameters):
                        if "APIKey" in line:
                            parameters[i] = (
                                parameters[i]
                                + " # <-- this is your first API Endpoint’s actual API Key, don’t give it away"
                            )
                    parameters = "\n".join(parameters)

                _highlight = highlight(
                    f"""\
import json, urllib.request, urllib.parse
response = json.loads(urllib.request.urlopen('{MOTHERSHIP}/{commandName}', urllib.parse.urlencode( \\
{parameters} \\
).encode('ascii')).read().decode())
print(response)""",
                    PythonLexer(),
                    HtmlFormatter(),
                )
                g.html.T(_highlight)

            g.html.mediumSeparator()
            g.html.P()
            g.html.T("Response:")
            g.html._P()
            g.html.T(highlight('{"response": "success"}', JsonLexer(), HtmlFormatter()))
            if "exampleResponse" in command:
                g.html.T("or")
                g.html.T(
                    highlight(
                        json.dumps(dict(command["exampleResponse"])),
                        JsonLexer(),
                        HtmlFormatter(),
                    )
                )
            else:
                if "return" in command:
                    if type(command["return"]) == str:
                        g.html.P()
                        g.html.T("or")
                        g.html._P()
                        g.html.T(command["return"])
                    elif command["return"] is None:
                        pass
                    else:
                        g.html.P()
                        g.html.T("or")
                        g.html._P()
                        g.html.T(
                            highlight(
                                '{"response": "%s"}'
                                % list(command["return"].keys())[1 if "success" in command["return"] else 0],
                                JsonLexer(),
                                HtmlFormatter(),
                            )
                        )

            g.html._area()

    g.html._DIV()

    return g.html.generate()


@typeworldserver.app.route("/_validateAPIEndpoint", methods=["POST"])
def _validateAPIEndpoint():

    import typeworld.tools.validator

    if not g.form._get("subscriptionURL"):
        return abort(400)

    parameters = {
        "subscriptionURL": g.form._get("subscriptionURL"),
        "profiles": g.form._get("profiles"),
    }

    if not g.form._get("profiles"):
        g.html.warning("At least one profile must be selected")
        return g.html.generate()

    success, response, responseObject = typeworld.client.request(
        "https://api.type.world/v1/validateAPIEndpoint", parameters
    )
    if success:
        g.html.info("See below for validation results")
    else:
        g.html.warning(response.decode())
        return g.html.generate()

    response = json.loads(response.decode())

    # logging.warning(response)

    # if response['response'] != 'success':
    # 	g.html.warning(response['response'])
    # 	return g.html.generate()

    g.html.area("Validation Results")

    g.html.P()
    g.html.T("In Summary:")
    g.html._P()
    g.html.P()
    g.html.TABLE()
    g.html.TR()
    g.html.TH()
    g.html.T("Name")
    g.html._TH()
    g.html.TH()
    g.html.T("Result")
    g.html._TH()
    g.html._TR()
    for stage in response["stages"]:
        g.html.TR()
        g.html.TD()
        g.html.T(stage["name"])
        g.html._TD()
        g.html.TD()
        if stage["result"] == "passed":
            g.html.EM(style="color: green;")
        elif stage["result"] == "failed":
            g.html.EM(style="color: red;")
        elif stage["result"] == "incomplete":
            g.html.EM(style="color: orange;")
        else:
            g.html.EM()
        g.html.T(stage["result"])
        g.html._EM()
        g.html._TD()
        g.html._TR()
    g.html._TABLE()
    g.html._P()

    g.html.P()
    g.html.T("In Detail:")
    g.html._P()
    g.html.smallSeparator()
    g.html.P()
    g.html.TABLE()
    for stage in response["stages"]:
        if stage["log"]:
            g.html.TR()
            g.html.TH(colspan="3")
            g.html.T(stage["name"])
            g.html._TH()
            g.html._TR()
            for log in stage["log"]:
                g.html.TR()
                g.html.TD(style="width:45%")
                if log["description"]:
                    g.html.T(markdown.markdown(log["description"]))
                g.html._TD()
                g.html.TD(style="width:10%")
                if log["result"] == "passed":
                    g.html.EM(style="color: green;")
                if log["result"] == "failed":
                    g.html.EM(style="color: red;")
                g.html.T(log["result"])
                g.html._EM()
                g.html._TD()
                g.html.TD(style="width:45%")
                if log["comments"]:
                    g.html.T(markdown.markdown(log["comments"]))
                g.html._TD()
                g.html._TR()
    g.html._TABLE()
    g.html._P()

    if response["warnings"]:

        g.html.smallSeparator()

        g.html.TABLE()
        g.html.TR()
        g.html.TH()
        g.html.T("Warnings")
        g.html._TH()
        g.html._TR()
        for warning in response["warnings"]:
            g.html.TR()
            g.html.TD(style="color: red;")
            g.html.T(markdown.markdown(warning))
            g.html._TD()
            g.html._TR()
        g.html._TABLE()

    if response["information"]:

        g.html.smallSeparator()

        g.html.TABLE()
        g.html.TR()
        g.html.TH()
        g.html.T("Information")
        g.html._TH()
        g.html._TR()
        for warning in response["information"]:
            g.html.TR()
            g.html.TD()
            g.html.T(markdown.markdown(warning))
            g.html._TD()
            g.html._TR()
        g.html._TABLE()

    g.html._area()

    return g.html.generate()


@typeworldserver.app.route("/developer/myapps/", methods=["POST", "GET"])
@typeworldserver.app.route("/developer/myapps", methods=["POST", "GET"])
def developer_myapps():

    g.html.tabs(developerTabs, "/developer/myapps")

    g.html.DIV(class_="content")

    if not g.user:
        g.html.T("Please log in to the website to access this page.")
    else:

        endpoints = g.user.APIEndpoints()

        g.html.area("My API Endpoints")
        g.html.FORM()
        g.html.P()
        g.html.T(
            "To interact with the Type.World service, your API Endpoint needs a private"
            " API key for authorization. Please enter you API Endpoint’s <b>Canonical"
            " URL</b> here, complete with protocol handlers."
        )
        g.html._P()
        g.html.P()
        g.html.T(
            "Note: The database is designed so that an API Endpoint can exist only"
            " once. That includes development servers on local networks which you still"
            " need to register here because you need to be able to verify users using"
            " the API key to be obtained here. So it’s possible that someone else has"
            " already registered the URL http://0.0.0.0:8080 (or similar) here. In that"
            " case, please customize the URL of your development API Endpoint to be"
            " unique, such as http://0.0.0.0:8080/myfoundrysapiendpoint"
        )
        g.html._P()
        g.html.P()
        g.html.T("Canonical URL")
        g.html.BR()
        g.html.INPUT(id="canonicalURL", placeholder="typeworld://json+https//...")
        g.html._P()
        g.html.P()
        g.html.A(
            class_="button",
            onclick=(
                "AJAX('#action', '/registerNewAPIEndpoint', {'canonicalURL':"
                " $('#canonicalURL').val(), 'reloadURL':"
                " encodeURIComponent(window.location.href), 'inline': 'true'});"
            ),
        )
        g.html.T("Register New API Endpoint")
        g.html._A()
        g.html._P()
        g.html._FORM()

        g.html.mediumSeparator()

        g.html.TABLE()
        g.html.TR()
        g.html.TH()
        g.html.T("Canonical URL")
        g.html._TH()
        g.html.TH(style="width: 20%;")
        g.html._TH()
        g.html._TR()
        for endpoint in endpoints:
            success, endpointCommand = endpoint.getEndpointCommand()
            g.html.TR()
            if not success:
                g.html.TD()
                g.html.T(f"Error retrieving endpointcommand: {endpointCommand}")
                g.html._TD()
            else:
                g.html.TD()
                g.html.DIV(style="font-weight: bold;")
                g.html.T(endpointCommand.name.en)
                g.html._DIV()
                g.html.DIV()
                g.html.T(endpointCommand.canonicalURL)
                g.html._DIV()
                g.html._TD()
            g.html.TD()
            g.html.A(href=f"/developer/endpoints/{base64.b64encode(endpoint.key.id().encode()).decode()}")
            g.html.T('<span class="material-icons-outlined">edit</span>')
            g.html._A()
            g.html.T(" ")
            endpoint.delete(text='<span class="material-icons-outlined">delete</span>')
            g.html._TD()
            g.html._TR()
        g.html._TABLE()

        g.html._area()

        g.html.area("My Sign-In Apps")
        g.html.P()
        if g.user.stripeSubscriptionReceivesService("world.type.signin_service_plan"):
            classes.SignInApp().new(
                text="Register New App/Website",
                hiddenValues={"userKey": g.user.publicID()},
                button=True,
                propertyNames=["name", "websiteURL", "logoURL", "redirectURLs", "oauthScopes"],
            )
        else:
            g.html.T(
                "Please activate the <em>Type.World Sign-In Service</em> plan on the <a"
                ' href="/developer/billing">billing page</a> in order to add apps here.'
            )
        g.html._P()

        signinApps = classes.SignInApp.query(classes.SignInApp.userKey == g.user.key).fetch()

        if signinApps:
            g.html.mediumSeparator()
            g.html.TABLE()
            g.html.TR()
            g.html.TH()
            g.html.T("Name")
            g.html._TH()
            g.html.TH(style="width: 20%;")
            g.html._TH()
            g.html._TR()
            g.html._TABLE()
            for signinApp in signinApps:
                signinApp.container("overview")

        g.html._area()

    g.html._DIV()

    return g.html.generate()


@typeworldserver.app.route("/developer/endpoints/<apiEndpointKey>", methods=["POST", "GET"])
def developer_editapiendpoint(apiEndpointKey):

    # Security
    if not g.user:
        return redirect("/")

    g.html.tabs(developerTabs, "/developer/endpoints", activeIsClickable=True)

    endpoint = classes.APIEndpoint.get_or_insert(
        base64.b64decode(apiEndpointKey).decode()
    )  # , read_consistency=ndb.STRONG

    if not endpoint:
        return abort(404)
    if endpoint not in g.user.APIEndpoints():
        return abort(403)

    g.html.DIV(class_="content")

    success, endpointCommand = endpoint.getEndpointCommand()
    if not success:
        g.html.P()
        g.html.T(f"Error retrieving endpointcommand: {endpointCommand}")
        g.html._P()
    else:

        g.html.H2()
        g.html.T(endpointCommand.name.en)
        g.html._H2()
        g.html.P()
        g.html.T(endpointCommand.canonicalURL)
        g.html._P()
        g.html.separator()

    g.html.area("API Key")
    g.html.P()
    g.html.T(
        "Your secret API Key that you must use for API calls such as"
        f" <code>verifyCredentials</code> is: <pre>{endpoint.getAPIKey()}</pre>"
    )
    g.html._P()
    g.html._area()

    # billing = endpoint.monthlyBilling()
    # billing.container('accountView')

    g.html.area("Test Users for Pro accounts")
    g.html.P()
    g.html.T(
        f"You may register up to {definitions.AMOUNTTESTUSERSFORAPIENTPOINT} users here for"
        " fake Pro accounts. This is particularly useful for development when your"
        " billing isn’t activated yet.<br />These users will enjoy the usual"
        " benefits of Pro accounts such as account synching and inviting other"
        " users to share subscriptions.<br />Only existing Type.World user"
        " accounts can be added."
    )
    g.html._P()

    g.html.mediumSeparator()

    testUsersForAPIEndpoint = endpoint.testUsers()

    if testUsersForAPIEndpoint:
        g.html.TABLE()
        g.html.TR()
        g.html.TH()
        g.html.T("Type.World User Account")
        g.html._TH()
        g.html.TH()
        g.html._TH()
        g.html._TR()

        for testUserForAPIEndpoint in testUsersForAPIEndpoint:
            testUser = testUserForAPIEndpoint.userKey.get(read_consistency=ndb.STRONG)
            g.html.TR()
            g.html.TD()
            g.html.T(testUser.email)
            g.html._TD()
            g.html.TD()
            # if testUser == g.user:
            #     g.html.T("<em>automatically added</em>")
            # else:
            testUserForAPIEndpoint.delete(text='<span class="material-icons-outlined">delete</span>')
            g.html._TD()
            g.html._TR()
        g.html._TABLE()

        g.html.mediumSeparator()

    g.html.P()
    g.html.T(
        f"You may add {definitions.AMOUNTTESTUSERSFORAPIENTPOINT - len(testUsersForAPIEndpoint)} more test users."
    )
    g.html._P()

    if len(testUsersForAPIEndpoint) < definitions.AMOUNTTESTUSERSFORAPIENTPOINT:
        # g.html.P()
        # g.html.FORM()
        g.html.P()
        g.html.T("Add Type.World User Account:")
        g.html.BR()
        g.html.INPUT(id="email", placeholder="johndoe@gmail.com")
        g.html._P()
        g.html.P()
        g.html.A(
            class_="button",
            onclick="AJAX('#action', '/addTestUserForAPIEndpoint', {'email': $('#email').val(), 'canonicalURL': '"
            + endpoint.key.id()
            + "', 'reloadURL': encodeURIComponent(window.location.href), 'inline': 'true'});",
        )
        g.html.T("Add Test User")
        g.html._A()
        g.html._P()
        # g.html._FORM()
        # g.html._P()

    g.html._area()

    g.html.area("Type.World API Logs")
    endpoint.container("logView")
    g.html._area()

    g.html._DIV()

    return g.html.generate()


@typeworldserver.app.route("/developer/billing", methods=["POST", "GET"])
@typeworldserver.app.route("/developer/billing/", methods=["POST", "GET"])
def developer_billing():

    g.html.tabs(developerTabs, "/developer/billing")

    g.html.DIV(class_="content")
    if not g.user:
        g.html.T("Please log in to the website to access this page.")
    else:
        g.html.T('<script src="https://js.stripe.com/v3/"></script>')
        g.html.T('<script src="/static/js/billing-stripe.js?v=' + g.instanceVersion + '"></script>')

        g.html.area("Billing & Subscriptions")
        g.user.container(
            "accountSubscriptionsView",
            parameters={"products": ["world.type.professional_publisher_plan", "world.type.signin_service_plan"]},
        )
        g.html._area()

    g.html._DIV()

    return g.html.generate()


@typeworldserver.app.route("/developer/validate/", methods=["POST", "GET"])
@typeworldserver.app.route("/developer/validate", methods=["POST", "GET"])
def developer_validate():

    g.html.tabs(developerTabs, "/developer/validate")

    g.html.DIV(class_="content")

    g.html.P()
    g.html.T(
        "The online validator that used to be here is currently out of service. Please"
        " follow the instructions below for how to validate your API Endpoint from your"
        " own computer."
    )
    g.html._P()

    g.html.H2()
    g.html.T("Make sure you’re sporting Python 3")
    g.html._H2()

    g.html.P()
    g.html.T(
        "All Type.World code is written for Python 3 and is not backwards compatible"
        " with Python 2. Make sure you’re using Python 3 by running <code>python3"
        " -V</code> on your command line. "
    )
    g.html.T(
        "(Macs come with Python 3 pre-installed, but the default <code>python</code>"
        " command points to Python 2. Instead, <code>python3</code> points to the"
        " correct one.)"
    )
    g.html._P()

    g.html.H2()
    g.html.T("Make sure you have PIP 3")
    g.html._H2()

    g.html.P()
    g.html.T(
        "PIP is Python’s package service, and sadly, it’s not always bundled with"
        " Python. See if you have it by running <code>pip3 -V</code>."
    )
    g.html._P()

    g.html.P()
    g.html.T(
        "If not already installed, download PIP’s installer with <code>curl"
        " https://bootstrap.pypa.io/get-pip.py -o get-pip.py</code>, then install it"
        " with <code>python3 get-pip.py</code>. Afterwards, confirm with <code>pip3"
        " -V</code>."
    )
    g.html._P()

    g.html.H2()
    g.html.T("Validate an API Endpoint from your computer")
    g.html._H2()

    g.html.OL()

    g.html.LI()
    g.html.T("Install the Python <b>typeworld</b> module using <code>pip3 install typeworld</code>. ")
    g.html.T(
        "Make sure to keep the module up to date by running <code>pip3 install -U"
        " typeworld</code> every time you use it as changes may occur at any time."
    )
    g.html._LI()

    g.html.LI()
    g.html.T("For help, run <code>validateTypeWorldEndpoint -h</code>, which will print the following output:")
    g.html._LI()

    g.html.LI()
    g.html.T(
        "Run the validator using <code>validateTypeWorldEndpoint"
        " typeworld://json+https//awesomefonts.com/api all</code>"
    )
    g.html._LI()

    g.html._OL()

    g.html.mediumSeparator()
    g.html.P()
    g.html.T("The following profiles are available:")
    g.html._P()

    g.html.P()
    g.html.B()
    g.html.T("All Profiles")
    g.html._B()
    g.html.BR()
    g.html.T("Keyword: ")
    g.html.CODE()
    g.html.B()
    g.html.T("all")
    g.html._B()
    g.html._CODE()
    g.html.BR()
    g.html.P()
    g.html.T("Runs available profiles")
    g.html._P()
    g.html._P()
    g.html.smallSeparator()

    import typeworld.tools.validator

    for keyword, title, description in typeworld.tools.validator.profiles:
        g.html.P()
        g.html.B()
        g.html.T(title)
        g.html._B()
        g.html.BR()
        g.html.T("Keyword: ")
        g.html.CODE()
        g.html.B()
        g.html.T(keyword)
        g.html._B()
        g.html._CODE()
        g.html.BR()
        g.html.T(markdown.markdown(description))
        g.html._P()
        g.html.smallSeparator()

    g.html._DIV()

    return g.html.generate()


# def _developer_validate():

#     g.html.tabs(developerTabs, "/developer/validate/")

#     MOTHERSHIP = "https://type.world/api"

#     g.html.mediumSeparator()

#     g.html.DIV(class_="content")

#     g.html.area("API Validator")
#     g.html.FORM()
#     g.html.P()
#     g.html.T(
#         "Here you can have your Type.World JSON Protocol-savvy API Endpoint’s function"
#         " validated. Depending on whether free or protected fonts are found, or fonts"
#         " with expiry dates (trial fonts), the validator will run routines matching the"
#         " types of fonts found. To make good use of this validator, you need to supply"
#         " a subscription that is modified to meet certain criteria as outlined below."
#     )
#     g.html._P()
#     g.html.P()
#     g.html.T("The following tests are currently implemented:")
#     g.html._P()

#     g.html.P()
#     g.html.TABLE()

#     import typeworld.tools.validator

#     g.html.TR()
#     g.html.TH(style="width: 20%;")
#     g.html.T("Name")
#     g.html._TH()
#     g.html.TH(style="width: 10%;")
#     g.html.T("Keyword")
#     g.html._TH()
#     g.html.TH(style="width: 70%;")
#     g.html.T("Description")
#     g.html._TH()
#     g.html._TR()

#     profileJavascript = ""
#     profileHTML = ""
#     profiles = [x[0] for x in typeworld.tools.validator.profiles]
#     for keyword, title, description in typeworld.tools.validator.profiles:
#         profileJavascript += f'if ($("#{keyword}").val()) {{{{ profiles.push("{keyword}"); }}}} '
#         g.html.TR()
#         g.html.TD()
#         g.html.T(title)
#         g.html._TD()
#         g.html.TD()
#         g.html.T(markdown.markdown(f"`{keyword}`"))
#         g.html._TD()
#         g.html.TD()
#         g.html.T(markdown.markdown(description))
#         g.html._TD()
#         g.html._TR()

#     g.html._TABLE()
#     g.html._P()

#     g.html.P()
#     g.html.T("Please enter a complete subscription URL below, with protocols and user credentials.")
#     g.html._P()
#     g.html.P()
#     g.html.T("Subscription URL")
#     g.html.BR()
#     g.html.INPUT(id="subscriptionURL", placeholder="typeworld://json+https//...")
#     g.html._P()

#     g.html.P()
#     g.html.T("<b>Test Profiles:</b>")
#     g.html.BR()
#     for keyword, title, description in typeworld.tools.validator.profiles:
#         g.html.checkBox(
#             keyword,
#             checked=keyword in g.form._get("profiles") if g.form._get("profiles") else True,
#         )
#         g.html.label(keyword, title)
#         g.html.BR()
#     g.html.T(profileHTML)
#     g.html._P()

#     g.html.SCRIPT()
#     g.html.T(
#         f"""

# profileKeywords = ['{"', '".join(profiles)}'];

# function getProfiles() {{

# _p = [];
# for (let i=0; i<profileKeywords.length; i++) {{
#     keyword = profileKeywords[i];
#     if ($("#" + keyword + ":checked").val()) {{
#             _p.push(keyword);
#     }}
# }}
# return _p;
# }}

# """
#     )
#     g.html._SCRIPT()

#     g.html.P()
#     g.html.T("Please be patient. This process may take a moment.")
#     g.html._P()
#     g.html.P()
#     g.html.A(
#         class_="button progress",
#         onclick=(
#             f"$('#validationResult').html(''); AJAX('#validationResult',"
#             f" '/_validateAPIEndpoint', {{'subscriptionURL':"
#             f" $('#subscriptionURL').val(), 'profiles': getProfiles().join(','),"
#             f" 'inline': 'true'}});"
#         ),
#     )
#     g.html.T("Validate")
#     g.html._A()
#     g.html._P()
#     g.html._FORM()
#     g.html._area()

#     g.html.area("API Validator API")
#     g.html.P()
#     g.html.T(
#         "This API Validator has its own API, so you can build an API into your API."
#         ' Check the API docs <a href="/developer/api#validateAPIEndpoint">here</a>. In'
#         " fact, this online API Validator here just queries the exact same API and"
#         " displays the data to you."
#     )
#     g.html._P()
#     g.html._area()

#     g.html.DIV(id="validationResult")
#     g.html._DIV()

#     g.html._DIV()

#     return g.html.generate()


def traceBackOutput():

    tracebacks = classes.AppTraceback.query(classes.AppTraceback.fixed is False).fetch(read_consistency=ndb.STRONG)
    if tracebacks:

        for traceback in tracebacks:
            g.html.P()
            g.html.area("Traceback")
            g.html.PRE()
            g.html.T(
                traceback.payload.replace(" ", "&nbsp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br />")
            )
            g.html._PRE()
            g.html._P()

            g.html.P()
            g.html.A(class_="button", href="/tracebacks/" + traceback.key.urlsafe().decode())
            g.html.T("View")
            g.html._A()
            g.html.A(
                class_="button",
                onclick=(
                    "AJAX('#stage', '/editProperties', {'class': 'AppTraceback', 'key':"
                    " '%s', 'propertyNames': 'fixed', 'fixed': 'on', 'reloadURL':"
                    " encodeURIComponent(window.location.href), 'inline': 'true'});"
                )
                % (traceback.key.urlsafe().decode()),
            )
            g.html.T("Close (traceback will not re-surface)")
            g.html._A()
            traceback.delete(text="Delete (allow this traceback to re-surface)", button=True)
            g.html._P()

            g.html._area()

    else:
        g.html.T("No open tracebacks found")


@typeworldserver.app.route("/tracebacks", defaults={"ID": None}, methods=["GET", "POST"])
@typeworldserver.app.route("/tracebacks/<ID>", methods=["GET", "POST"])
def tracebacks(ID):

    if not g.admin:
        return abort(401)

    g.html.mediumSeparator()

    g.html.DIV(class_="content")

    if ID:

        traceback = ndb.Key(urlsafe=ID.encode()).get(read_consistency=ndb.STRONG)
        if traceback:

            g.html.area("Status")
            if not traceback.fixed:
                g.html.P()
                g.html.T("Status: Open")
                g.html._P()

                g.html.P()
                g.html.A(
                    class_="button",
                    onclick=(
                        "AJAX('#stage', '/editProperties', {'class': 'AppTraceback',"
                        " 'key': '%s', 'propertyNames': 'fixed', 'fixed': 'on',"
                        " 'reloadURL': encodeURIComponent(window.location.href),"
                        " 'inline': 'true'});"
                    )
                    % (traceback.key.urlsafe().decode()),
                )
                g.html.T("Close (traceback will not re-surface)")
                g.html._A()
                traceback.delete(text="Delete (allow this traceback to re-surface)", button=True)
                g.html._P()

            else:
                g.html.T("Status: Closed")
            g.html._area()

            g.html.area("Traceback")
            g.html.PRE()
            g.html.T(
                traceback.payload.replace(" ", "&nbsp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br />")
            )
            g.html._PRE()
            g.html._area()

            if traceback.supplementary:
                g.html.area("Supplementary Information")
                g.html.PRE()
                j = json.loads(traceback.supplementary.decode())
                g.html.T(
                    json.dumps(j, indent=4, sort_keys=True)
                    .replace(" ", "&nbsp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                g.html._PRE()
                g.html._area()

        else:
            traceBackOutput()

    else:

        traceBackOutput()

    g.html._DIV()

    return g.html.generate()


@typeworldserver.app.route("/map", methods=["GET", "POST"])
def map():

    query_set = classes.AppInstance.query(projection=["X_Appengine_Citylatlong"], distinct=True)
    geoPoints = [data.X_Appengine_Citylatlong for data in query_set]

    g.html.T(
        """
<!DOCTYPE html>
<html>
  <head>
    <title>Type.World Network Map</title>
    <meta name="viewport" content="initial-scale=1.0">
    <meta charset="utf-8">
      <style>
      /* Always set the map height explicitly to define the size of the div
       * element that contains the map. */
      #map {
        height: 100%;
      }
      /* Optional: Makes the sample page fill the window. */
      html, body {
        height: 100%;
        margin: 0;
        padding: 0;
      }

      #stage {
        height: 100%;
      }

#legend {
  font-family: Arial, sans-serif;
  background: #1B1B1B;
  padding: 15px;
  margin: 10px;
  color: #666;
}

#legend h3 {
  margin-top: 0;
}

#legend img {
  vertical-align: middle;
}

#legend div {
  margin-bottom: 3px;
}

    </style>
  </head>
  <body>

    <div id="map"></div>
    <div id="legend">
    <div style="text-align: center; margin-bottom: 10px;">
    <a href="/">
    <img style="width:200px;" src="/static/images/logowithlogotype.svg">
    </a>
    </div>
    <h3>Legend</h3></div>
    <script>
      var map;
      function initMap() {
        const map = new google.maps.Map(document.getElementById('map'), {
          center: {lat: 15, lng: 0},
          zoom: Math.ceil(Math.log2(window.outerWidth)) - 8.5,
          mapId: 'ea29f9a01d8af362',
          disableDefaultUI: true,
          fullscreenControl: true,
        });

    """
    )

    g.html.T(
        """
const iconBase = "/static/images/map/";
const icons = {
    edgenode: {
      icon: {
          url: iconBase + "edgenode.png",
          size: new google.maps.Size(16, 16),
          anchor: new google.maps.Point(8, 8),
          name: "Google Cloud Network Endpoint",
      },
    },
    typeworldserver: {
      icon: {
          url: iconBase + "typeworldserver.png",
          size: new google.maps.Size(16, 16),
          anchor: new google.maps.Point(8, 8),
          name: "Type.World Network Server",
      },
    },
    placewithusers: {
      icon: {
          url: iconBase + "placewithusers.png",
          size: new google.maps.Size(16, 16),
          anchor: new google.maps.Point(8, 8),
          name: "Town With Type.World User(s)",
      },
    },
  };
const features = ["""
    )

    for city in definitions.GCPedgenodes:
        g.html.T(
            f"""
    {{
      position: new google.maps.LatLng({definitions.GCPedgenodes[city][0]}, {definitions.GCPedgenodes[city][1]}),
      type: "edgenode",
      title: "{city}",
    }},
    """
        )

    # Type.World Servers
    # type.world
    g.html.T(
        f"""
    {{
      position: new google.maps.LatLng({definitions.GCPzones["us-east"]["geolocation"][0]},
      {definitions.GCPzones["us-east"]["geolocation"][1]}),
      type: "typeworldserver",
      title: "Type.World Central Server, {definitions.GCPzones['us-east']['name']}"
    }},
    """
    )

    # Draw app instances
    for appInstance in geoPoints:

        g.html.T(
            f"""
    {{
      position: new google.maps.LatLng({appInstance.latitude}, {appInstance.longitude}),
      type: "placewithusers",
    }},
    """
        )

    g.html.T(
        """
  ];

  var markers = new Array();

  // Create markers.
  for (let i = 0; i < features.length; i++) {
    var marker = new google.maps.Marker({
      position: features[i].position,
      icon: icons[features[i].type].icon,
      map: map,
      title: features[i].title,
    });
    markers.push(marker);
  }


function setIcons() {
    //change the size of the icon
    markers.forEach(element => setIcon(element));

}

setIcons();

function setIcon(marker) {
    var zoom = map.getZoom();
    var iconSize = zoom * 2;
    marker.icon.size = new google.maps.Size(iconSize, iconSize);
    marker.icon.scaledSize = new google.maps.Size(iconSize, iconSize);
    marker.icon.anchor = new google.maps.Point(iconSize/2, iconSize/2);
}


//when the map zoom changes, resize the icon based on the zoom level so the marker covers the same geographic area
google.maps.event.addListener(map, 'zoom_changed', function() {
    setIcons();
});



    """
    )

    for link in definitions.GCPlinks:
        g.html.T("flightPlanCoordinates = [")
        for leg in link:
            if type(leg) == str:
                g.html.T(
                    f"new google.maps.LatLng({definitions.GCPedgenodes[leg][0]}, {definitions.GCPedgenodes[leg][1]}),"
                )
            else:
                for lat, long in leg:
                    g.html.T(f"new google.maps.LatLng({lat}, {long}),")
        g.html.T("];")
        g.html.T(
            """
flightPath = new google.maps.Polyline({
    path: flightPlanCoordinates,
    geodesic: true,
    strokeColor: "#3C3C3B",
    strokeOpacity: 1.0,
    strokeWeight: 1,
  });

  flightPath.setMap(map);
"""
        )

    apikey = typeworldserver.secret("GOOGLE_MAPS_APIKEY")
    g.html.T(
        f"""


const legend = document.getElementById("legend");

  for (const key in icons) {{
    const type = icons[key];
    const name = type.icon.name;
    const icon = type.icon.url;

    const div = document.createElement("div");
    div.innerHTML = '<img src="' + icon + '" style="width: 12px; height: 12px; margin: 2px;"> ' + name;
    legend.appendChild(div);
  }}

  map.controls[google.maps.ControlPosition.LEFT_TOP].push(legend);




      }}
    </script>
    <script src="https://maps.googleapis.com/maps/api/js?key={apikey}&callback=initMap"
    async defer></script>
</body>
</html>

    """
    )

    return g.html.GenerateBody()
