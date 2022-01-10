"""

#
# CONTAINERS
#

Containers define areas in HTML code that correspond to a certain function
in Python code. The main purpose is to establish an easily reusable format
for reloading the HTML content of a specific micro-view only, without reloading
the entire page.

Unbound containers are called via the container() method:

```
def content_xyz():
    ...
container('content_xyz')
```

Class-bound containers are called via the classes’s container() method:

```
class ABC():
    def content_xyz(self):
        ...
abc = ABC()
abc.container('content_xyz')
```


#
# CONTAINER REPRESENTATION IN HTML
#

The method encodeDataContainer() turns
a reference to a (bound or unbound) method alongside a data dictionary into
a single string that can be embedded into HTML to be used an ID (by HTML class)
for an HTML element.

The idea is that an HTML container (a view) may exist simultaneously
in several places on a single web page, and using the unique encoded ID,
all instances of that view can be updated in one go.

Parameters may be encoded as a dictionary into that string, being passed back
to the server directly from the HTML without need for server-side data caching.




Classes may define HTML views in any method, such as .view()
They are simply called for rendering as Object.view()






They are accessible from the outside (for example for a reload)
and therefore need to be access-restricted. The permissions are
calculated in .viewPermission()

class Translation_Category(WebAppModel):
    name = StringProperty(required = True)

    def view(self, parameters = {}, directCallParameters = {}):
        g.html.DIV()
        ...
        g.html._DIV()

    def viewPermission(self, methodName):
        return False



"""

# project
import typeworldserver
from typeworldserver import classes
from typeworldserver import definitions
from typeworldserver import hypertext
from typeworldserver import helpers
from typeworldserver import api

# other
import typeworld.client
import os
import json
import semver
from flask import abort, g, request
from google.cloud.ndb.model import KeyProperty
import google.cloud.ndb.model
import importlib
import base64
from google.cloud import ndb
from urllib.parse import unquote, urlencode
import copy
import urllib.parse

typeworldserver.app.config["modules"].append("web")


#####

FORM_PREFIX = "dialogform_"
KEY_METHOD_SEPARATOR = "__---__"
KEY_PARAMETER_SEPARATOR = "__----__"

EMPTY = "__empty__"
NOTUPDATED = "__notupdated__"
NEW = "__new__"
UNDEFINED = "__undefined__"
UNCHANGED = "__unchanged__"

dataContainerJavaScriptIdentifier = "' + dataContainerJavaScriptIdentifier($(this)) + '"


def base64_encode(string):
    """
    Removes any `=` used as padding from the encoded string.
    """
    encoded = base64.urlsafe_b64encode(string.encode()).decode()
    return encoded.rstrip("=")


def base64_decode(string):
    """
    Adds back in the required padding before decoding.
    """
    padding = 4 - (len(string) % 4)
    string = string + ("=" * padding)
    return base64.urlsafe_b64decode(string.encode()).decode()


def encodeDataContainer(key, methodName, parameters={}):
    """
    Encode an object’s NDB key (optional for unbound methods as None),
    its method name, and a parameter dictionary
    for output as and HTML-safe identifier.
    Returns the encoded information as a single string.
    """
    parameterString = base64_encode(json.dumps(parameters))

    if key:
        return f"{key}{KEY_METHOD_SEPARATOR}{methodName}{KEY_PARAMETER_SEPARATOR}{parameterString}"
    else:
        return f"{methodName}{KEY_PARAMETER_SEPARATOR}{parameterString}"


def decodeDataContainer(string):
    """
    Inverse of encodeDataContainer().
    Returns (keyID, methodName, parameters) tuple,
    with keyID being None for unbound methods.
    """
    ID, parameterB64 = string.split(KEY_PARAMETER_SEPARATOR)
    if KEY_METHOD_SEPARATOR in ID:
        keyID, methodName = ID.split(KEY_METHOD_SEPARATOR)
    else:
        keyID = None
        methodName = ID

    parameters = json.loads(base64_decode(parameterB64))

    return keyID, methodName, parameters


def reload(text="↻", style="text", parameters={}, backgroundColor=None):
    """
    Renders a reload button to be used inside a data container
    for reloading a view from the server.
    """

    if parameters:
        p = str(parameters).replace('"', "'")
        js = f"reload($(this), {p});"
    else:
        js = "reload($(this));"

    if style in ("text", "button"):
        css = ""
        if backgroundColor:
            css += f"background-color: {backgroundColor};"
        g.html.A(class_="button" if style == "button" else None, onclick=js, style=css)
        g.html.T(text)
        g.html._A()
    elif style == "hidden":
        g.html.DIV(class_="reloadContainer", onclick=js)
        g.html._DIV()


def outerContainer(methodName, parameters, inline):
    if inline:
        style = "display: inline-block"
    else:
        style = None

    g.html.DIV(
        class_=f"dataContainer {encodeDataContainer(None, methodName, parameters)}",
        style=style,
    )


def innerContainer(methodName, parameters={}, directCallParameters={}):
    method = None

    for moduleName in typeworldserver.app.config["modules"]:
        if moduleName == "__main__":
            module = importlib.import_module(moduleName, package=None)
        else:
            module = importlib.import_module("typeworldserver." + moduleName, package=None)
        if hasattr(module, methodName):
            method = getattr(module, methodName)
            break

    if methodName in globals():
        method = globals()[methodName]
    elif methodName in locals():
        method = locals()[methodName]

    assert method

    method(parameters, directCallParameters)


def _outerContainer():
    g.html._DIV()


def container(methodName, parameters={}, directCallParameters={}, inline=False):
    outerContainer(methodName, parameters, inline)
    innerContainer(methodName, parameters, directCallParameters)
    _outerContainer()


class Form(dict):
    def _get(self, key):
        if key in self:
            return self[key]
        else:
            return None


@typeworldserver.app.route("/env", methods=["POST", "GET"])
def env():

    if not g.admin:
        return abort(401)

    g.html.mediumSeparator()

    g.html.DIV(class_="content")
    g.html.P()
    g.html.T("ENV:")
    g.html._P()
    g.html.P()
    g.html.T(str(os.environ))
    g.html._P()
    g.html.P()
    g.html.T("HTTP Headers:")
    g.html._P()
    g.html.P()
    g.html.T(str(request.headers))
    g.html._P()
    g.html._DIV()

    return g.html.generate()


@typeworldserver.app.before_request
def before_request_web():

    g.form = Form()

    for key in request.values:
        if key.startswith(FORM_PREFIX):
            g.form[key[len(FORM_PREFIX) :]] = request.values.get(key)  # noqa E203
        else:
            g.form[key] = request.values.get(key)

    if g.form._get("propertyNames"):
        g.form["propertyNames"] = ",".join(
            [
                x[len(FORM_PREFIX) :] if x.startswith(FORM_PREFIX) else x  # noqa E203
                for x in g.form._get("propertyNames").split(",")
            ]
        )

    # for key in g.form:
    #     logging.debug(f'### {key}: {g.form._get(key)}')


#####


class Property(object):
    def __init__(self, *args, **kwargs):

        # Patch description
        self.description = None
        if "verbose_name" in kwargs and type(kwargs["verbose_name"]) in (list, tuple):
            self.description = kwargs["verbose_name"][1]
            kwargs["verbose_name"] = kwargs["verbose_name"][0]

        super().__init__(*args, **kwargs)

    def shape(self, value):
        return value

    def valid(self, value):
        return True, None

    def dialog(self, key, value, placeholder=None):
        g.html.textInput(key, value=value, type="text", placeholder=placeholder)

    # def create(self, values = {}):
    #     return True, None
    # def _prepare_for_put(self):
    #     super(Property, self)._prepare_for_put(*args, **kwargs)
    #     print(self, "_prepare_for_put()")


#####


class StringProperty(Property, ndb.StringProperty):
    def dialog(self, key, value, placeholder=None):
        g.html.textInput(key, value=value, type="text", placeholder=placeholder)


class BlobProperty(Property, ndb.BlobProperty):
    pass


class TextProperty(Property, ndb.TextProperty):
    def dialog(self, key, value, placeholder=None):
        g.html.textInput(key, value=value, type="textarea", placeholder=placeholder)


class EmailProperty(Property, ndb.StringProperty):
    def dialog(self, key, value, placeholder=None):
        g.html.textInput(key, value=value, type="email", placeholder=placeholder)

    def valid(self, value):
        if api.verifyEmail(value):
            return True, None
        else:
            return False, "Invalid email"


class HTTPURLProperty(Property, ndb.StringProperty):
    def valid(self, value):
        if value.startswith("http://") or value.startswith("https://"):
            return True, None
        else:
            return False, "Needs to start with http:// or https://"

    def dialog(self, key, value, placeholder=None):
        g.html.textInput(key, value=value, type="text", placeholder="http://")


class HTTPSURLProperty(Property, ndb.StringProperty):
    def valid(self, value):
        if value.startswith("https://"):
            return True, None
        else:
            return False, "Needs to start with https://"

    def dialog(self, key, value, placeholder=None):
        g.html.textInput(key, value=value, type="text", placeholder="https://")


class UserKeyProperty(KeyProperty):
    def valid(self, value):
        if value is None:
            return (
                False,
                "User doesn’t exist",
            )
        return True, None

    def shape(self, value):
        user = classes.User.query().filter(classes.User.email == value).get(read_consistency=ndb.STRONG)
        if user:
            return user.key

    def dialog(self, key, value, placeholder=None):
        email = None
        if value:
            user = value.get(read_consistency=ndb.STRONG)
            if user:
                email = user.email
        g.html.textInput(key, value=email, type="email", placeholder=placeholder)


class DateTimeProperty(Property, ndb.DateTimeProperty):
    def dialog(self, key, value, placeholder=None):
        pass


class GeoPtProperty(Property, ndb.GeoPtProperty):
    def dialog(self, key, value, placeholder=None):
        pass


class BooleanProperty(Property, ndb.BooleanProperty):
    def dialog(self, key, value, placeholder=None):
        g.html.DIV(style="display: block;")
        g.html.checkBox(key, value)
        g.html._DIV()

    def shape(self, value):
        return value == "on"


class JsonProperty(Property, ndb.JsonProperty):
    def dialog(self, key, value, placeholder=None):
        pass


class KeyProperty(Property, ndb.KeyProperty):
    def dialog(self, key, value, placeholder=None):
        pass

    def shape(self, value):
        return ndb.Key(urlsafe=value.encode())

    # def valid(self, value):

    # 	if self.kind:
    # 		logging.warning(f'### {self.kind}')
    # 	return True, None


class IntegerProperty(Property, ndb.IntegerProperty):
    def dialog(self, key, value, placeholder=None):
        g.html.INPUT(type="text", id=key, value=value)

    def shape(self, value):
        return int(value)


class SemVerProperty(Property, ndb.StringProperty):
    def dialog(self, key, value, placeholder=None):
        g.html.textInput(key, value=value, type="text", placeholder=placeholder)

    def valid(self, value):
        try:
            semver.parse(value)
            return True, None
        except ValueError:
            return False, f"{value} is not a valid semver version string"


class FloatProperty(Property, ndb.FloatProperty):
    def dialog(self, key, value, placeholder=None):
        g.html.INPUT(type="text", id=key, value=value)

    def shape(self, value):
        return float(value)


class CountryProperty(Property, ndb.StringProperty):
    def dialog(self, key, value, placeholder=None):
        g.html.SELECT(name=key, id=key, onchange="")
        for code, name in definitions.COUNTRIES:
            g.html.OPTION(value=code, selected=code == value)
            g.html.T(name)
            g.html._OPTION()
        g.html._SELECT()


class EUVATIDProperty(Property, ndb.StringProperty):
    def dialog(self, key, value, placeholder=None):
        g.html.textInput(key, value=value, type="text", placeholder=placeholder)

    def shape(self, value):
        value = value.replace(".", "")
        value = value.replace(" ", "")
        value = value.replace("#", "")
        value = value.replace("_", "")
        value = value.replace("-", "")
        return value.upper()

    def valid(self, value):
        value = self.shape(value)
        if not value:
            return True, None
        if value == "DE212651941":
            return True, None  # Yanone ID for testing
        if not value[:2] in definitions.EU_COUNTRIES:
            return False, f"Invalid Country Code: {value[:2]}"
        if g.form._get("invoiceCountry") != value[:2]:
            return False, "EU VAT ID and Country mismatch"
        if g.form._get("invoiceCountry") == "DE":
            return False, "No VAT ID needed for companies in Germany"
        # Shape
        # Validate
        url = "https://evatr.bff-online.de/evatrRPC?UstId_1=DE212651941&UstId_2=%s" % (value)
        success, responseContent, response = typeworld.client.request(url)
        if type(responseContent) != str:
            responseContent = responseContent.decode()
        if not success:
            return False, responseContent

        class VATXMLResponse(object):
            def __init__(self, xml):
                self.keys = []
                import xml.etree.ElementTree as ET

                root = ET.fromstring(xml)
                values = root.findall("./param/value/array/data/value/")
                for i in range(0, len(values), 2):
                    setattr(self, values[i].text, values[i + 1].text)
                    self.keys.append(values[i].text)

            def toStr(self):
                string = []
                for key in self.keys:
                    string.append("%s: %s" % (key, getattr(self, key)))
                return "\n".join(string)

        r = VATXMLResponse(responseContent)
        valid = ("200", "216", "218", "219", "222")
        emailForCodes = ("200", "205", "206", "207", "214", "215", "217", "220", "999")
        if r.ErrorCode in valid:
            return True, None
        # https://evatr.bff-online.de/eVatR/xmlrpc/codes

        responses = {
            "200": "Die angefragte USt-IdNr. ist gültig.",
            "201": "The VAT ID is invalid.",
            "202": (
                "The VAT ID is invalid. It is not registered in the business database"
                " of the respective EU member country. You may have to apply with your"
                " finance authorities to have your number registered in the respective"
                " database."
            ),
            "203": "The VAT ID is valid only starting %s." % (r.Gueltig_ab),
            "204": "The VAT ID was valid only between %s and %s." % (r.Gueltig_ab, r.Gueltig_bis),
            "205": "The request can’t be processed at the moment. Please try again later.",
            "206": "The German VAT ID of the seller is invalid.",
            "207": "The German VAT ID is not authorized to request VAT ID verifications.",
            "208": "Another request is currently running for this VAT ID. Please try again later.",
            "209": "The VAT ID does not comply with the VAT ID syntax of the respective EU member country.",
            "210": "The VAT ID does not pass the checksum rules of the respective EU member country.",
            "211": "The VAT ID contains illegal symbols.",
            "212": "The VAT ID contains an unknown country code",
            "213": "Verifying a German VAT ID is not possible.",
            "214": "The German VAT ID is malformed.",
            "215": "Either one of the two VAT IDs is missing.",
            "216": (
                "Ihre Anfrage enthält nicht alle notwendigen Angaben für eine"
                " qualifizierte Bestätigungsanfrage (Ihre deutsche USt-IdNr., die ausl."
                " USt-IdNr., Firmenname einschl. Rechtsform und Ort). Es wurde eine"
                " einfache Bestätigungsanfrage durchgeführt mit folgenden Ergebnis: Die"
                " angefragte USt-IdNr. ist gültig."
            ),
            "217": (
                "An error occurred while processing your VAT ID by the respective EU"
                " member country. Please try again later."
            ),
            "218": (
                "Eine qualifizierte Bestätigung ist zur Zeit nicht möglich. Es wurde"
                " eine einfache Bestätigungsanfrage mit folgendem Ergebnis"
                " durchgeführt: Die angefragte USt-IdNr. ist gültig."
            ),
            "219": (
                "Bei der Durchführung der qualifizierten Bestätigungsanfrage ist ein"
                " Fehler aufgetreten. Es wurde eine einfache Bestätigungsanfrage mit"
                " folgendem Ergebnis durchgeführt: Die angefragte USt-IdNr. ist gültig."
            ),
            "220": "An error occurred while processing the VAT ID.",
            "221": "The request was incomplete or contains invalid data types.",
            "222": (
                "Die angefragte USt-IdNr. ist gültig. Bitte beachten Sie die Umstellung"
                " auf ausschließlich HTTPS (TLS 1.2) zum 07.01.2019."
            ),
            "999": "The VAT ID cannot be veryfied at this point. Please try again later.",
        }
        sendEmail = False
        responseText = ""

        if r.ErrorCode in responses:
            responseText = responses[r.ErrorCode]
            if r.ErrorCode in emailForCodes:
                sendEmail = True
        else:
            responseText = "The request returned an unknown response code."
            sendEmail = True

        # Send email
        if sendEmail:
            responseText += " The administrator has been informed by email."
            body = r.toStr() + "\n"
            body += f"Error code {r.ErrorCode}: {responseText}"
            helpers.email(
                "hq@mail.type.world",
                "post@yanone.de",
                "Malformed VAT ID verification on type.world",
                body,
            )

        return False, responseText


class ChoicesProperty(Property, ndb.StringProperty):
    def __init__(self, *args, **kwargs):
        self.choicesData = kwargs["choices"]
        kwargs["choices"] = list(self.choicesData.keys())
        kwargs["repeated"] = True
        super().__init__(*args, **kwargs)

    def shape(self, value):
        if value in (UNDEFINED, ""):
            return []
        elif "," in value:
            return [x for x in value.split(",") if x.strip()]
        else:
            return [value]
        return value

    def dialog(self, key, value, placeholder=None):
        g.html.INPUT(type="hidden", id=key, value=",".join(value))
        g.html.DIV(style="margin: 5px;", class_="clear")
        for choice in self.choicesData:
            g.html.DIV(style="margin-bottom: 5px; width: 30px;", class_="floatleft")
            id = f"choice_{key}_{choice}"
            g.html.INPUT(
                type="checkbox",
                id=id,
                checked=choice in value,
                onchange=(
                    f"handleChoiceValue($('#{key}'), $('#{id}:checked'), '{choice}'); deRequiredMissing($(this));"
                ),
            )
            g.html._DIV()
            g.html.DIV(style="margin-bottom: 5px; width: calc(100% - 30px)", class_="floatleft")
            g.html.LABEL(for_=id)
            g.html.T(self.choicesData[choice]["name"])
            g.html._LABEL()
            if "description" in self.choicesData[choice]:
                g.html.DIV(style="font-size: 80%; opacity: 0.5;")
                g.html.T(self.choicesData[choice]["description"])
                g.html._DIV()
            g.html._DIV()
        g.html._DIV()


# class WebAppModelDelegate(object):
#     def before__init__(self):
#         pass
#     def after__init__(self):
#         pass


class WebAppModel(ndb.Model):

    created = DateTimeProperty()
    createdBy = KeyProperty()
    touched = DateTimeProperty(auto_now=True)
    defaultValues = {}

    def __init__(self, *args, **kwargs):

        super(WebAppModel, self).__init__(*args, **kwargs)

        # print(self.__class__.__name__, "__init__")
        self.delegate = None

        # self.delegate = WebAppModelDelegate()
        self._contentCache = {}
        self._updateContentCache()
        # Necessary when creating new object, not loading from DB
        # self._contentCacheUpdated = False
        self.initialize()
        self._currentlyPutting = False

    # @classmethod
    # def _pre_delete_hook(cls, key):
    #     if key:
    #         self = key.get(read_consistency=ndb.STRONG)
    #         if self is not None:
    #             self.

    # Not implemented here because being detected by hasattr()
    # def beforeDelete(self):
    #     pass

    @classmethod
    def _post_get_hook(cls, key, future):
        # print(cls.__name__, "_post_get_hook")

        self = future.result()
        if self:
            self._updateContentCache()

    # user facing
    def initialize(self):
        pass

    # user facing
    def beforePut(self):
        pass

    # user facing
    def afterPut(self):
        pass

    def _prepareToPut(self):
        # print(self.__class__.__name__, "_prepareToPut")

        if self.created is None:
            self.created = helpers.now()

        if self.createdBy is None and hasattr(g, "user") and g.user:
            self.createdBy = g.user.key

        self._currentlyPutting = True

        # Calculate changed properties
        if self._contentCacheUpdated:
            # print("Calculate changed properties")
            for key in self.__properties():
                # print(f"{key}: -{getattr(self, key)}- -{self._contentCache[key]}-")
                if getattr(self, key) != self._contentCache[key]:
                    self._changed.append(key)
            # print("self._changed", self._changed)

        self.beforePut()

    def _cleanupPut(self):

        self.afterPut()
        self._updateContentCache()
        self._currentlyPutting = False

    def put(self, **kwargs):

        if self._currentlyPutting:
            super(WebAppModel, self).put(**kwargs)
        else:
            self._prepareToPut()

            # Actually save
            if self._contentCacheUpdated is False or self._changed:

                # New behavior: Save on @typeworldserver.app.after_request
                super(WebAppModel, self).put(**kwargs)
                if self not in g.ndb_puts:
                    g.ndb_puts.append(self)

    def putnow(self, **kwargs):

        self.put(**kwargs)

        # if self._currentlyPutting:
        #     super(WebAppModel, self).put(**kwargs)
        # else:

        #     self._prepareToPut()

        #     # # Actually save
        #     # if self._contentCacheUpdated is False or self._changed:
        #         # Old behavior: Save immediately
        #     super(WebAppModel, self).put(**kwargs)
        #         # print(self.__class__.__name__, "super(WebAppModel, self).put(**kwargs)")

        #     self._cleanupPut()

        #     if self in g.ndb_puts:
        #         g.ndb_puts.remove(self)

    def _updateContentCache(self):
        # print(self.__class__.__name__, "_updateContentCache")

        for key in self.__properties():
            self._contentCache[key] = copy.deepcopy(getattr(self, key))
        self._changed = []
        self._contentCacheUpdated = True

    def publicID(self):
        if self.key is None:
            self.putnow()
        return self.key.urlsafe().decode()

    def reloadDataContainer(self, view, parameters):
        return None

    def __properties(self):

        _p = []

        for key in self.__class__.__dict__:
            attr = getattr(self.__class__, key)

            if Property in attr.__class__.__bases__ or Property in attr.__class__.__bases__[0].__bases__:

                # 			if hasattr(attr, 'dialog'):# and isinstance(getattr(attr, 'dialog'), types.FunctionType):
                _p.append(key)

        return _p

    def editPermission(self, propertyNames=[]):
        return False

    def executeMethodPermission(self, methodName=""):
        return False

    def deletePermission(self):
        return False

    def canSave(self):
        return True, None

    def viewPermission(self, methodName):
        return False

    def container(self, methodName, parameters={}, directCallParameters={}, inline=False):
        self.outerContainer(methodName, parameters, inline)
        self.innerContainer(methodName, parameters, directCallParameters)
        self._outerContainer()

    def outerContainer(self, methodName, parameters, inline):
        if inline:
            style = "display: inline-block"
        else:
            style = None

        g.html.DIV(
            class_=f"dataContainer {encodeDataContainer(self.key.urlsafe().decode(), methodName, parameters)}",
            style=style,
        )

    def innerContainer(self, methodName, parameters={}, directCallParameters={}):
        method = getattr(self, methodName)
        if method:
            method(parameters, directCallParameters)

    def _outerContainer(self):
        g.html._DIV()

    def dialog(
        self,
        dialogType="popup",
        title=None,
        propertyNames=[],
        values={},
        hiddenValues={},
        dataContainer="",
        reloadURL=None,
        new=False,
        parentKey=None,
    ):

        g.html.DIV(class_="title")
        g.html.P()
        g.html.T(title or "%s %s" % ("New" if new else "Edit", self.__class__.__name__))
        g.html._P()
        g.html._DIV()

        g.html.DIV(class_="dialogInnerWrapper")
        g.html.DIV(class_="dialogInnerInnerWrapper")
        g.html.DIV(class_="dialogInnerInnerInnerWrapper")

        visiblePropertyNames = propertyNames or self.__properties()

        if not new:
            hiddenValues["key"] = self.key.urlsafe().decode()
        hiddenValues["class"] = self.__class__.__name__
        if dataContainer:
            hiddenValues["dataContainer"] = dataContainer
        if reloadURL:
            hiddenValues["reloadURL"] = helpers.addAttributeToURL(reloadURL, "inline=true")
        if parentKey:
            hiddenValues["parentKey"] = parentKey

        # Set default values
        for key in values:
            # setattr(self, key, values[key])

            # Shape values
            if hasattr(self.__class__, key):
                attr = getattr(self.__class__, key)

                if Property in attr.__class__.__bases__ or Property in attr.__class__.__bases__[0].__bases__:
                    value = attr.shape(values[key])
                    setattr(self, key, value)

        # Set defaultValues
        for key in self.defaultValues:
            if self.defaultValues[key][-2:] == "()":
                method = getattr(self, self.defaultValues[key][:-2])
                setattr(self, key, method())
            else:
                setattr(self, key, self.defaultValues[key])

        for propertyName in visiblePropertyNames:
            attribute = getattr(self, propertyName)

            attr = getattr(self.__class__, propertyName)
            g.html.P()
            g.html.label(
                propertyName,
                attr._verbose_name or propertyName,
                required=attr._required,
            )
            if attr.description:
                g.html.SPAN(class_="labelDescription")
                g.html.T(attr.description)
                g.html._SPAN()
            g.html.BR()
            attr.dialog(f"{FORM_PREFIX}{propertyName}", attribute)
            g.html._P()

        # Hidden fields
        for propertyName in hiddenValues:
            g.html.INPUT(
                type="hidden",
                id=f"{FORM_PREFIX}{propertyName}",
                value=hiddenValues[propertyName],
            )

        combinedPropertyNames = [
            f"{FORM_PREFIX}{x}" for x in list(set(hiddenValues.keys()) | set(visiblePropertyNames))
        ]

        # g.html.mediumSeparator()

        actionDIV = "#action"
        if dataContainer:
            actionDIV = f".dataContainer.{dataContainer}"

        g.html._DIV()  # .dialogInnerInnerInnerWrapper
        g.html._DIV()  # .dialogInnerInnerWrapper

        g.html.DIV(class_="dialogButtonArea")
        g.html.DIV(class_="clear")

        g.html.SPAN(class_="floatleft", style="margin-right: 10px;")
        g.html.A(
            class_="button",
            onclick="AJAX('%s', '/editProperties', {'inline': 'true', 'propertyNames': '%s'}, [%s]);"
            % (
                actionDIV,
                ",".join(combinedPropertyNames),
                ", ".join(["'%s'" % x for x in combinedPropertyNames]),
            ),
        )
        g.html.T("Save")
        g.html._A()
        g.html._SPAN()
        g.html.SPAN(class_="floatleft", style="margin-right: 10px;")
        g.html.A(class_="button secondary", onclick="hideDialog();")
        g.html.T("Cancel")
        g.html._A()
        g.html._SPAN()

        g.html._DIV()  # .clear
        g.html._DIV()  # .dialogButtonArea
        g.html._DIV()  # .dialogInnerWrapper

        g.html.SCRIPT()
        g.html.T("$('#dialog .dialogInnerWrapper').ready(function() {")
        g.html.T("$('#dialog').css('height', 'auto');")
        g.html.T(
            "$('#dialog').css('height', ($('#dialog .dialogInnerInnerInnerWrapper').outerHeight()) + 180) + 'px';"
        )
        g.html.T("});")
        g.html._SCRIPT()

    def new(
        self,
        text=None,
        propertyNames=[],
        useCreateFunction=False,
        values={},
        hiddenValues={},
        parentKey=None,
        button=False,
    ):

        url = f"/createDialog?inline=true&new=true&class={self.__class__.__name__}"

        # logging.debug('Values in new(): %s' % values)

        # Add default values
        if values:
            url += "&values=%s" % ",".join(values.keys())
        for key in values:
            url += "&" + key + "=" + values[key]
        if parentKey:
            url += "&parentKey=%s" % parentKey.urlsafe().decode()
        if propertyNames:
            url += "&propertyNames=%s" % ",".join(propertyNames)
        url += "&reloadURL=' + encodeURIComponent(window.location.href) + '"
        url += f"&dataContainer={dataContainerJavaScriptIdentifier}"

        if useCreateFunction:
            url += "&useCreateFunction=true"

        if hiddenValues:
            url += "&hiddenValues=" + ",".join(hiddenValues.keys())
            for key in hiddenValues:
                url += "&%s=%s" % (key, hiddenValues[key])

        g.html.A(class_="button" if button else "", onclick="dialog('%s');" % url)
        g.html.T(text or ("+ Add %s" % self.__class__.__name__))
        g.html._A()

    def edit(self, text=None, button=False, propertyNames=[], values={}, hiddenValues={}, reloadURL=None):

        url = "/createDialog?inline=true&class=%s" % (self.__class__.__name__)
        url += "&key=%s" % self.key.urlsafe().decode()
        if propertyNames:
            url += "&propertyNames=%s" % ",".join(propertyNames)
        if reloadURL:
            url += f"&reloadURL={reloadURL}"
        else:
            url += f"&dataContainer={dataContainerJavaScriptIdentifier}"
        if values:
            url += f"&values={','.join(values.keys())}&{urlencode(values)}"
        if hiddenValues:
            url += "&hiddenValues=" + ",".join(hiddenValues.keys())
            for key in hiddenValues:
                url += "&%s=%s" % (key, hiddenValues[key])

        g.html.A(class_="button" if button else "", onclick="dialog('%s');" % url)
        g.html.T(text or '<span class="material-icons-outlined">edit</span>')
        g.html._A()

    def execute(self, text, button=False, methodName=""):

        url = "/executeMethod?inline=true&class=%s" % (self.__class__.__name__)
        url += "&key=%s" % self.key.urlsafe().decode()
        if methodName:
            url += "&methodName=%s" % methodName
        url += f"&dataContainer={dataContainerJavaScriptIdentifier}"

        g.html.A(
            class_="button" if button else "",
            onclick=f"AJAX('.{dataContainerJavaScriptIdentifier}', '{url}');",
        )
        g.html.T(text)
        g.html._A()

    def reload(self):

        url = "/reloadContainer?inline=true&class=%s" % (self.__class__.__name__)
        url += "&key=%s" % self.key.urlsafe().decode()
        # 		url += '&containerName=%s' % containerName
        url += f"&dataContainer={dataContainerJavaScriptIdentifier}"

        g.html.A(onclick=f"AJAX('.{dataContainerJavaScriptIdentifier}', '{url}');")
        g.html.T("↻")
        g.html._A()

    def delete(self, text=None, button=False):

        url = "/deleteObject?inline=true&class=%s" % (self.__class__.__name__)
        url += "&key=%s" % self.key.urlsafe().decode()
        url += "&reloadURL=' + encodeURIComponent(window.location.href) + '"

        g.html.A(
            class_="button" if button else "",
            onclick=f"dialogConfirm('Do you really want to delete this object?', '#action', '{url}');",
        )
        g.html.T(text or "🗑")
        g.html._A()


def getClass(key, className, parentKey=None):
    # Construct object
    item = None
    if key:
        for moduleName in typeworldserver.app.config["modules"]:
            if moduleName == "__main__":
                module = importlib.import_module(moduleName, package=None)
            else:
                module = importlib.import_module("typeworldserver." + moduleName, package=None)
            if hasattr(module, className):
                item = ndb.Key(urlsafe=key.encode()).get(read_consistency=ndb.STRONG)
                break

        # new = False
    # New
    else:
        # new = True
        if parentKey is not None:
            parentKey = ndb.Key(urlsafe=g.form._get("parentKey").encode())
        for moduleName in typeworldserver.app.config["modules"]:
            if moduleName == "__main__":
                module = importlib.import_module(moduleName, package=None)
            else:
                module = importlib.import_module("typeworldserver." + moduleName, package=None)
            if hasattr(module, className):

                if parentKey:
                    item = getattr(module, className)(parent=parentKey)
                else:
                    item = getattr(module, className)()
                break

    return item


@typeworldserver.app.route("/createDialog", methods=["POST", "GET"])
def createDialog():

    if not g.form._get("class"):
        return abort(400)

    propertyNames = []
    if g.form._get("propertyNames"):
        propertyNames = g.form._get("propertyNames").split(",")

    item = getClass(g.form._get("key"), g.form._get("class"), g.form._get("parentKey"))

    hiddenValues = {}

    # access_token
    if g.form.get("access_token"):
        hiddenValues["access_token"] = g.form.get("access_token")

    # Default values
    if g.form._get("hiddenValues"):
        for key in g.form._get("hiddenValues").split(","):
            if key not in hiddenValues:
                attr = getattr(item.__class__, key)
                value = attr.shape(g.form._get(key))
                setattr(item, key, value)
                hiddenValues[key] = g.form._get(key)

    values = {}
    if g.form._get("values"):
        for key in g.form._get("values").split(","):
            attr = getattr(item.__class__, key)
            value = attr.shape(g.form._get(key))
            setattr(item, key, value)
            values[key] = g.form._get(key)

    # Edit permissions
    if g.admin or item.editPermission(propertyNames):

        dialogType = g.form._get("type") or "popup"
        item.dialog(
            propertyNames=propertyNames,
            title=g.form._get("title"),
            dialogType=dialogType,
            values=values,
            hiddenValues=hiddenValues,
            dataContainer=g.form._get("dataContainer"),
            reloadURL=g.form._get("reloadURL"),
            new=g.form._get("new") == "true",
            parentKey=g.form._get("parentKey"),
        )

        if dialogType == "popup":
            g.html.SCRIPT()
            g.html.T("$('#dialog').fadeIn();")
            g.html._SCRIPT()

        return g.html.generate()

    else:
        return abort(401)


def dataContainerReloadSpecific(dataContainer):

    keyID, methodName, parameters = decodeDataContainer(dataContainer)
    if g.form._get("parameters"):
        parameters = json.loads(g.form._get("parameters"))

    # print("dataContainerReloadSpecific", keyID, methodName, parameters)

    otherItem = None

    if keyID:
        key = ndb.Key(urlsafe=keyID.encode())

        # logging.warning('dataContainerReload(%s)' % [key, methodName, parameters])

        otherItem = key.get(read_consistency=ndb.STRONG)
        if otherItem:
            if g.admin or otherItem.viewPermission(methodName):
                otherItem.innerContainer(methodName, parameters)
            else:
                return False, "noPermission"
    else:
        innerContainer(methodName, parameters)

        # logging.warning('dataContainerReload(%s)' % [methodName, parameters])

    return True, otherItem


def dataContainerReload(item=None):

    # Return new HTML for dataContainer
    # logging.warning(f'g.form._get("dataContainer"): {g.form._get("dataContainer")}')
    if g.form._get("dataContainer"):

        keyID, methodName, parameters = decodeDataContainer(g.form._get("dataContainer"))

        if g.form._get("parameters"):
            parameters = json.loads(g.form._get("parameters"))

        success, message = dataContainerReloadSpecific(g.form._get("dataContainer"))

        # print("dataContainerReload", keyID, methodName, parameters, success, message)

        if not success:
            return success, message

        else:

            if item or message:
                if message and not item:
                    item = message

                additionalReloadDataContainer = item.reloadDataContainer(g.form._get("dataContainer"), parameters)

                # logging.warning('%s.additionalReloadDataContainer()=%s' % (item, additionalReloadDataContainer))

                if additionalReloadDataContainer and additionalReloadDataContainer != g.form._get("dataContainer"):
                    oldHTML = g.html
                    g.html = hypertext.HTML()

                    dataContainerReloadSpecific(additionalReloadDataContainer)

                    html = g.html.generate()

                    html = html.replace("\n", "\\n")

                    if "\n" in html:
                        raise ValueError("Returned code contains new line character, which breaks JS handling.")

                    g.html = oldHTML
                    g.html.SCRIPT()
                    js = "$('.%s').html('%s'.replace('\\\\n', '\\n'));" % (
                        additionalReloadDataContainer,
                        html.replace("'", "\\'"),
                    )
                    g.html.T(js)
                    g.html._SCRIPT()

    # 					logging.warning(js)

    g.html.SCRIPT()
    if not g.form._get("dataContainer") and g.form._get("reloadURL"):
        g.html.T("AJAX('#stage', '%s');" % helpers.addAttributeToURL(unquote(g.form._get("reloadURL")), "inline=true"))
    g.html.T("hideDialog();")
    g.html._SCRIPT()

    return True, None


@typeworldserver.app.route("/executeMethod", methods=["POST"])
def executeMethod():

    if not g.form._get("class"):
        return abort(400)

    item = getClass(g.form._get("key"), g.form._get("class"), g.form._get("parentKey"))

    if not hasattr(item, g.form._get("methodName")):
        return abort(401)

    # Edit permissions
    if g.admin or item.executeMethodPermission(g.form._get("methodName")):
        method = getattr(item, g.form._get("methodName"))

        # Run
        method()

        dataContainerReload(item)

    return g.html.generate()


@typeworldserver.app.route("/editProperties", methods=["POST"])
def editProperties():

    if not g.form._get("class"):
        return abort(400)

    propertyNames = []
    if g.form._get("propertyNames"):
        propertyNames = g.form._get("propertyNames").split(",")

    item = getClass(g.form._get("key"), g.form._get("class"), g.form._get("parentKey"))

    # Put data
    changed = False
    for propertyName in propertyNames:

        if hasattr(item, propertyName):

            oldValue = getattr(item, propertyName)

            if g.form._get(propertyName) == EMPTY:
                setattr(item, propertyName, None)

            else:

                # Shape values
                if hasattr(item.__class__, propertyName):
                    attr = getattr(item.__class__, propertyName)
                    value = g.form._get(propertyName)

                    # print(attr.__class__.__bases__, attr.__class__.__bases__[0].__bases__)

                    # if google.cloud.ndb.model.Property in attr.__class__.__bases__ or google.cloud.ndb.model.
                    # Property in attr.__class__.__bases__[0].__bases__ or Property in attr.__class__.__bases__
                    #  or Property in attr.__class__.__bases__[0].__bases__:
                    if (
                        google.cloud.ndb.model.Property in attr.__class__.__bases__[0].__bases__
                        or Property in attr.__class__.__bases__[0].__bases__
                        or Property in attr.__class__.__bases__
                    ):

                        # Shape
                        value = attr.shape(value)

                        # Validate
                        success, message = attr.valid(value)

                        if not success:
                            g.html.SCRIPT()
                            g.html.T(f"$('.dialogform_{propertyName}'').addClass('requiredmissing');")
                            g.html._SCRIPT()
                            g.html.warning(f"{propertyName}: {message}")
                            return g.html.generate(), 900

                        # Set the value
                        setattr(item, propertyName, value)

                    # Required check
                    if attr._required and not value:
                        g.html.SCRIPT()
                        g.html.T(f"$('.dialogform_{propertyName}').addClass('requiredmissing');")
                        g.html._SCRIPT()
                        g.html.warning(f"{propertyName} is a required value.")
                        return g.html.generate(), 900

            if getattr(item, propertyName) != oldValue:
                changed = True

    # Validate
    success, message = item.canSave()

    if not success:
        g.html.warning(f"{message}")
        return g.html.generate(), 900

    # Return empty
    if not changed:
        return "", 204

    # Edit permissions
    if g.admin or item.editPermission(propertyNames):
        item.putnow()

        if g.form._get("dataContainer"):
            dataContainerReload(item)
        elif g.form._get("reloadURL"):
            g.html.SCRIPT()
            g.html.T(f"window.location.href='{urllib.parse.unquote_plus(g.form._get('reloadURL'))}';")
            g.html._SCRIPT()

    else:
        return abort(401)

    html = g.html.generate()

    # logging.warning(html)

    return html


@typeworldserver.app.route("/reloadContainer", methods=["POST", "GET"])
def reloadContainer():
    """
    Reload a data container using its HTML-encoded reference (`dataContainer` parameter).
    Additionally, a new parameter dictionary can be supplied via the `parameters` parameter.
    """

    success, message = dataContainerReload()

    if not success and message == "noPermission":
        return abort(401)

    return g.html.generate()


@typeworldserver.app.route("/deleteObject", methods=["POST", "GET"])
def deleteObject():

    if not g.form._get("class"):
        return abort(400)

    item = getClass(g.form._get("key"), g.form._get("class"), g.form._get("parentKey"))

    # Edit permissions
    if g.admin or item.deletePermission():

        item.key.delete()

        g.html.SCRIPT()
        if g.form._get("reloadURL"):
            g.html.T(
                "AJAX('#stage', '%s');" % helpers.addAttributeToURL(unquote(g.form._get("reloadURL")), "inline=true")
            )
        g.html._SCRIPT()

    else:
        return abort(401)

    return g.html.generate()


class PasswordReset(WebAppModel):
    userKey = KeyProperty(required=True)


@typeworldserver.app.route("/resetpassword", methods=["GET"])
@typeworldserver.app.route("/resetpassword/<urlsafe>", methods=["GET"])
def resetpassword(urlsafe=None):

    g.html.DIV(class_="content")

    if urlsafe:

        pwr = ndb.Key(urlsafe=urlsafe.encode()).get(read_consistency=ndb.STRONG)

        if not pwr:
            return abort(401)

        user = pwr.userKey.get(read_consistency=ndb.STRONG)

        g.html.area(f"Reset Password for {user.email}")
        g.html.FORM()
        g.html.P()
        g.html.T("Please choose a new password for your Type.World user account.")
        g.html._P()
        g.html.P()
        g.html.T("New Password")
        g.html.BR()
        g.html.INPUT(id="password", name="password", type="password")
        g.html._P()
        g.html.P()
        g.html.T("Repeat New Password")
        g.html.BR()
        g.html.INPUT(id="password2", name="password2", type="password")
        g.html._P()
        g.html.P()
        g.html.A(
            class_="button",
            onclick=(
                "AJAX('#action', '/resetPasswordAction', {'password':"
                " $('#password').val(), 'password2': $('#password2').val(), 'urlsafe':"
                f" '{urlsafe}', 'inline': 'true'}});"
            ),
        )
        g.html.T("Save New Password")
        g.html._A()
        g.html._P()
        g.html._FORM()
        g.html._area()

    else:
        g.html.area("Reset Password")
        g.html.FORM()
        g.html.P()
        g.html.T(
            "Please enter your user Type.World user account’s email address below and"
            " we’ll send you an email with a link to reset your password."
        )
        g.html._P()
        g.html.P()
        g.html.T(
            "Please note that for reasons of privacy there will be no feedback on"
            " whether this email is actually registered as a Type.World user account."
        )
        g.html._P()
        g.html.P()
        g.html.T("Email Address")
        g.html.BR()
        g.html.INPUT(id="email", placeholder="johndoe@gmail.com")
        g.html._P()
        g.html.P()
        g.html.A(
            class_="button",
            onclick="AJAX('#action', '/requestPasswortReset', {'email': $('#email').val(), 'inline': 'true'});",
        )
        g.html.T("Request")
        g.html._A()
        g.html._P()
        g.html._FORM()
        g.html._area()

    g.html._DIV()

    return g.html.generate()


@typeworldserver.app.route("/resetPasswordAction", methods=["POST"])
def resetPasswordAction():

    # if not g.form._get('urlsafe') and not g.form._get('userKey'):
    #     return abort(401)

    if not g.form._get("password") or not g.form._get("password2"):
        g.html.warning("At least one of the two passwords is empty.")
        return g.html.generate()

    if g.form._get("password") != g.form._get("password2"):
        g.html.warning("The two passwords are not identical.")
        return g.html.generate()

    # Reset from within user account
    if g.form._get("userKey"):
        user = ndb.Key(urlsafe=g.form._get("userKey").encode()).get(read_consistency=ndb.STRONG)

        if not user or user != g.user:
            return abort(401)

        pwr = None

    # Reset from email link
    elif g.form._get("urlsafe"):
        pwr = ndb.Key(urlsafe=g.form._get("urlsafe").encode()).get(read_consistency=ndb.STRONG)

        if not pwr:
            return abort(401)

        user = pwr.userKey.get(read_consistency=ndb.STRONG)

    else:
        user = g.user
        pwr = None

    if user:

        if user.checkPassword(g.form._get("password")):
            g.html.warning("Old and new password are identical. Please choose another password.")
            return g.html.generate()

        success, message = user.setPassword(g.form._get("password"))
        if not success:
            g.html.warning(message)
            return g.html.generate()

        # Success
        user.put()

        if pwr:
            pwr.key.delete()

        g.html.info("The password has been successfully reset.")

        if g.form._get("reload") and g.form._get("reload") == "false":
            pass
        else:
            g.html.SCRIPT()
            g.html.T("window.location.href='/';")
            g.html._SCRIPT()

    return g.html.generate()


@typeworldserver.app.route("/requestPasswortReset", methods=["POST"])
def requestPasswortReset():

    if not g.form._get("email"):
        return abort(400)

    from classes import User

    user = User.query(User.email == g.form._get("email")).get(read_consistency=ndb.STRONG)

    if user:

        pwr = PasswordReset()
        pwr.userKey = user.key
        pwr.putnow()

        body = f"""\
Hi {user.name},

It appears that you have requested to reset the password for your Type.World user account.
(If it wasn’t you, then please don’t do anything!)

You can reset your password under the following link: https://type.world/resetpassword/{pwr.key.urlsafe().decode()}

Peace,
Type.World HQ

"""

        helpers.email(
            "Type.World <resetpassword@mail.type.world>",
            [user.email],
            "Reset your Type.World user account password",
            body,
        )

    g.html.info("The email has been sent to you. Please follow the link you’ll find in it.")

    return g.html.generate()
