# project
import typeworldserver
from typeworldserver import definitions
from typeworldserver import billing_stripe
from typeworldserver import web
from typeworldserver import helpers
from typeworldserver import mq
from typeworldserver import translations

# other
import typeworld.client
import os
import bcrypt
import time
import json
import traceback
import urllib.parse
import urllib.request
import stripe
import datetime
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from flask import g, request
from google.cloud import ndb
import logging
import urllib.parse
import uuid

typeworldserver.app.config["modules"].append("classes")


###


class TWNDBModel(web.WebAppModel):
    pass


class User(TWNDBModel):
    email = web.EmailProperty(required=True, verbose_name="Email Address")
    name = web.StringProperty(required=True, verbose_name="Human Readable Name")
    passwordHash = web.StringProperty(required=True)
    secretKey = web.StringProperty(required=True)
    uuid = web.StringProperty()
    websiteToken = web.StringProperty()
    timezone = web.StringProperty()
    emailVerified = web.BooleanProperty(default=False)
    emailVerificationCode = web.StringProperty()
    emailVerificationRedirectURL = web.StringProperty()
    emailToChange = web.EmailProperty(verbose_name="New Email Address")
    lastSeenOnline = web.DateTimeProperty()
    lastLogin = web.DateTimeProperty()

    # Rights Management
    admin = web.BooleanProperty(default=False)
    blog = web.BooleanProperty(default=False)

    stripeCustomerId = web.StringProperty()
    stripeSubscribedProductsHistory = web.JsonProperty(default={})
    stripeSubscriptions = web.JsonProperty(default={})

    stripeTestCustomerId = web.StringProperty()
    stripeTestSubscriptions = web.JsonProperty(default={})
    stripeTestSubscribedProductsHistory = web.JsonProperty(default={})

    invoiceName = web.StringProperty(
        verbose_name=["First and Last Name", "Either <em>Name</em> or <em>Company</em> are reqired"]
    )
    invoiceCompany = web.StringProperty(
        verbose_name=["Company", "Either <em>Name</em> or <em>Company</em> are reqired"]
    )
    invoiceStreet = web.StringProperty(verbose_name=["Address", "Required"])
    invoiceStreet2 = web.StringProperty(verbose_name="Additional Address Information")
    # invoiceStreet3 = web.StringProperty(verbose_name="Additional Address Information")
    invoiceZIPCode = web.StringProperty(verbose_name=["ZIP Code", "Required for certain countries"])
    invoiceCity = web.StringProperty(verbose_name=["City/Town", "Required"])
    invoiceState = web.StringProperty(verbose_name=["State/Province", "Required for certain countries"])
    invoiceCountry = web.CountryProperty(verbose_name=["Country", "Required"])
    invoiceEUVATID = web.EUVATIDProperty(verbose_name=["EU VAT ID", "Required only for E.U. businesses"])

    invoiceFields = [
        "invoiceCompany",
        "invoiceName",
        "invoiceStreet",
        "invoiceStreet2",
        # "invoiceStreet3",
        "invoiceZIPCode",
        "invoiceCity",
        "invoiceState",
        "invoiceCountry",
        "invoiceEUVATID",
    ]

    def bill(self, plan, category, ID=None, note=None, quantity=1):

        if quantity == 0:
            return False, "Not billing, quantity is 0"

        if category not in definitions.PRODUCTS:
            return False, "unknownCategory"

        stripeSubscription = self.stripeSubscriptionByProductID(plan)
        if not stripeSubscription:
            return False, "unknownStripeSubscription"

        # Find price ID
        priceId = None
        for productId in billing_stripe.stripeProducts:
            if productId == plan:
                for price in billing_stripe.stripeProducts[productId]["prices"]:
                    if price["tw_id"] == category:
                        priceId = price["id"]
                        break
                # else:
                #     continue
                # break
        if not priceId:
            return False, "unknownPriceId"

        # Find SubscriptionItem
        subscriptionItemId = None
        for item in stripeSubscription["items"]["data"]:
            if item["price"]["id"] == priceId:
                subscriptionItemId = item["id"]
        if not subscriptionItemId:
            return False, "subscriptionItemId"

        # Cumulative
        if definitions.PRODUCTS[category]["type"] == "cumulative":

            stripe.SubscriptionItem.create_usage_record(
                subscriptionItemId,
                quantity=quantity,
                timestamp=int(time.time()),
                action="increment",
            )
            print(f"Billed {self.email} for {category}={quantity}")

        # Max
        elif definitions.PRODUCTS[category]["type"] == "maximal":

            stripe.SubscriptionItem.create_usage_record(
                subscriptionItemId,
                quantity=quantity,
                timestamp=int(time.time()),
                action="set",
            )
            print(f"Billed {self.email} for {category}={quantity}")

        else:
            return False, "Couldn't find billing method"

        return True, None

    def getUUID(self):
        if not self.uuid:
            self.uuid = str(uuid.uuid1())
            self.put()
        return self.uuid

    def rawJSONData(self, app, scopes, token=None):
        response = {
            "userdata": {
                "user_id": self.getUUID(),
                "edit_uri": (
                    f"{typeworldserver.HTTPROOT}/auth/edituserdata?scope={','.join(scopes)}"
                    f"&edit_token={token.editCode if token and token.editCode else '__place_for_edit_token__'}"
                    "&redirect_uri=__place_for_redirect_uri__"
                ),
                "scope": {},
            },
        }
        # Add data
        for scope in scopes:
            response["userdata"]["scope"][scope] = self.oauth(scope)
            # Add clientID
            if "edit_uri" in response["userdata"]["scope"][scope]:
                response["userdata"]["scope"][scope]["edit_uri"] += (
                    f"&edit_token={token.editCode if token and token.editCode else '__place_for_edit_token__'}"
                    "&redirect_uri=__place_for_redirect_uri__"
                )

        return response

    def oauth(self, scope):

        # See http://www.bitboost.com/ref/international-address-formats.html
        # for address formatting

        if scope == "account":
            data = {
                "name": definitions.SIGNINSCOPES["account"]["name"],
                "data": {"name": self.name, "email": self.email},
            }

            # Missing data
            missing = []
            if not self.name:
                missing.append("name")
            if not self.email:
                missing.append("name")
            data["missing_required_data"] = missing

            return data

        elif scope == "billingaddress":
            data = {
                "name": definitions.SIGNINSCOPES["billingaddress"]["name"],
                "edit_uri": f"{typeworldserver.HTTPROOT}/auth/edituserdata?scope=billingaddress",
                "data": {
                    "company": self.invoiceCompany or "",
                    "name": self.invoiceName or "",
                    "address": self.invoiceStreet or "",
                    "address_2": self.invoiceStreet2 or "",
                    # "address_3": self.invoiceStreet3 or "",
                    "zipcode": self.invoiceZIPCode or "",
                    "town": self.invoiceCity or "",
                    "state": self.invoiceState or "",
                    "country": definitions.COUNTRIES_DICT[self.invoiceCountry] if self.invoiceCountry else "",
                    "country_code": self.invoiceCountry or "",
                },
            }

            # Missing data
            missing = []
            if not self.invoiceName and not self.invoiceCompany:
                missing.append("name")
                missing.append("company")
            if not self.invoiceStreet:
                missing.append("address")
            if (
                self.invoiceCountry
                and self.invoiceCountry in definitions.COUNTRIES_THAT_REQUIRE_ZIP_CODE
                and not self.invoiceZIPCode
            ):
                missing.append("zipcode")
            if not self.invoiceCity:
                missing.append("town")
            if (
                self.invoiceCountry
                and self.invoiceCountry in definitions.COUNTRIES_THAT_REQUIRE_STATE_OR_PROVINCE
                and not self.invoiceState
            ):
                missing.append("state")
            if not self.invoiceCountry:
                missing.append("country")

            data["missing_required_data"] = missing

            # Formatted address
            if self.invoiceCountry:
                formattedData = definitions.ADDRESS_FORMAT[
                    self.invoiceCountry if self.invoiceCountry in definitions.ADDRESS_FORMAT else "default"
                ]
                for key in data["data"]:
                    formattedData = formattedData.replace(f"{{{key}}}", data["data"][key])
                # Strip beginning and end
                formattedData = formattedData.strip()
                # Strip each line
                formattedData = "\n".join([x.strip() for x in formattedData.splitlines() if x])
                # Remove leftovers (probably unnecessary at this point except for spaces)
                formattedData = (
                    formattedData.replace("\n\n", "\n")
                    .replace("\n\n", "\n")
                    .replace("\n\n", "\n")
                    .replace("  ", " ")
                    .replace("  ", " ")
                    .replace("  ", " ")
                    .replace(" \n", "\n")
                    .replace("\n ", "\n")
                )
                data["formatted_billing_address"] = formattedData

            return data

        elif scope == "euvatid":
            data = {
                "name": definitions.SIGNINSCOPES["euvatid"]["name"],
                "edit_uri": f"{typeworldserver.HTTPROOT}/auth/edituserdata?scope=euvatid",
                "data": {
                    "euvatid": self.invoiceEUVATID or "",
                },
            }

            # Missing data
            missing = []
            data["missing_required_data"] = missing

            return data

    def oauthInfo(self):
        return {
            "account": {
                "editable": [],
                "fields": {
                    "name": {"name": "Name", "dbMapping": "name"},
                    "email": {"name": "Email", "dbMapping": "email"},
                },
            },
            "billingaddress": {
                "editable": [
                    "invoiceCompany",
                    "invoiceName",
                    "invoiceStreet",
                    "invoiceStreet2",
                    # "invoiceStreet3",
                    "invoiceZIPCode",
                    "invoiceCity",
                    "invoiceState",
                    "invoiceCountry",
                ],
                "fields": {
                    "name": {"name": "First and Last Name", "dbMapping": "invoiceName"},
                    "company": {"name": "Company", "dbMapping": "invoiceCompany"},
                    "address": {"name": "Address", "dbMapping": "invoiceStreet"},
                    "address_2": {
                        "name": "Additional Address Information",
                        "dbMapping": "invoiceStreet2",
                    },
                    # "address_3": {
                    #     "name": "Additional Address Information",
                    #     "dbMapping": "invoiceStreet3",
                    # },
                    "zipcode": {"name": "ZIP Code", "dbMapping": "invoiceZIPCode"},
                    "town": {"name": "Town", "dbMapping": "invoiceCity"},
                    "state": {"name": "State/Province", "dbMapping": "invoiceState"},
                    "country": {"name": "Country", "dbMapping": "invoiceCountry"},
                },
            },
            "euvatid": {
                "editable": ["invoiceEUVATID"],
                "fields": {
                    "euvatid": {
                        "name": "European Union VAT ID <em>(if applicable)</em>",
                        "dbMapping": "invoiceEUVATID",
                    },
                },
            },
        }

    def reloadDataContainer(self, view, parameters):

        keyID, methodName, parameters = web.decodeDataContainer(view)

        if methodName == "editScopeView":
            return web.encodeDataContainer(
                self.publicID(), "rawJSONDataView", {"scopes": parameters["scopes"], "appKey": parameters["appKey"]}
            )

    def editScopeView(self, parameters={}, directCallParameters={}):
        scope = parameters["scope"]

        g.html.DIV(class_="scope")
        g.html.DIV(class_="head clear")
        g.html.DIV(class_="floatleft")
        g.html.T(
            "<span"
            f' class="material-icons-outlined">view_in_ar</span>&nbsp;&nbsp;{definitions.SIGNINSCOPES[scope]["name"]}'
        )
        g.html._DIV()  # .floatleft
        g.html.DIV(class_="floatright", style="font-size: inherit;")
        if self.oauthInfo()[scope]["editable"]:
            self.edit(
                propertyNames=self.oauthInfo()[scope]["editable"],
                hiddenValues={"edit_token": g.form.get("edit_token")} if g.form.get("edit_token") else {}
                # reloadURL="' + encodeURIComponent(window.location.href) + '",
            )
        g.html._DIV()  # .floatright
        g.html._DIV()  # .head
        g.html.DIV(class_="content")

        g.html.TABLE()
        oauth = self.oauth(scope)
        for key in oauth["data"]:
            if key in self.oauthInfo()[scope]["fields"]:
                g.html.TR()
                g.html.TD(style="width: 40%; text-align: right; color: #777; font-size: 10pt;")
                g.html.T(self.oauthInfo()[scope]["fields"][key]["name"] + ":")
                g.html._TD()
                g.html.TD()
                if "missing_required_data" in oauth and key in oauth["missing_required_data"]:
                    g.html.T('<span style="color: #ff8b47;">&lt;missing&gt;</span>')
                else:
                    g.html.T(oauth["data"][key] or '<span style="color: #777;">&lt;empty&gt;</span>')
                g.html._TD()
                g.html._TR()

        g.html._TABLE()

        g.html._DIV()  # .content
        g.html._DIV()  # .scope

        # Missing data
        if self.oauth_incompleteUserData(parameters["scopes"]):
            g.html.SCRIPT()
            g.html.T("$('.incomplete_user_data').show(); $('.complete_user_data').hide();")
            g.html._SCRIPT()
        else:
            g.html.SCRIPT()
            g.html.T("$('.incomplete_user_data').hide(); $('.complete_user_data').show();")
            g.html._SCRIPT()

    def rawJSONDataView(self, parameters={}, directCallParameters={}):
        scopes = parameters["scopes"]
        app = ndb.Key(urlsafe=parameters["appKey"].encode()).get(read_consistency=ndb.STRONG)

        g.html.DIV(class_="scope")
        g.html.DIV(class_="content")

        g.html.P()
        g.html.T(
            f'<span class="material-icons-outlined">view_in_ar</span> This is the precise data that <b>{app.name}</b>'
            " will receive. Nothing more, nothing less."
        )
        g.html._P()
        g.html.mediumSeparator()

        g.html.P()
        g.html.PRE()
        g.html.T(json.dumps(self.rawJSONData(app, scopes), indent=1))  # .replace("\n", "<br />")
        g.html._PRE()
        g.html._P()

        g.html._DIV()  # .content
        g.html._DIV()  # .scope

    def editScopes(self, scopes, completeData, app, rawDataLink=True):

        if completeData:

            # COMPLETE DATA
            g.html.DIV(class_="raw_data_off")
            if rawDataLink:
                g.html.DIV(style="text-align: right;")
                g.html.T(
                    "Show raw JSON data <a onclick=\"$('.raw_data_on').show(); $('.raw_data_off').hide();\">"
                    '<span class="material-icons-outlined">toggle_off</span></a>'
                )
                g.html._DIV()
                g.html.smallSeparator()

            for i, scope in enumerate(scopes):
                self.container(
                    "editScopeView", parameters={"scope": scope, "scopes": scopes, "appKey": app.publicID()}
                )

            g.html._DIV()  # .raw_data_off

            if rawDataLink:
                # RAW DATA
                g.html.DIV(class_="raw_data_on", style="display: none;")
                g.html.DIV(style="text-align: right;")
                g.html.T(
                    "Show raw JSON data <a onclick=\"$('.raw_data_on').hide(); $('.raw_data_off').show();\">"
                    '<span class="material-icons-outlined">toggle_on</span></a>'
                )
                g.html._DIV()

                g.html.smallSeparator()
                self.container("rawJSONDataView", parameters={"scopes": scopes, "appKey": app.publicID()})

                g.html._DIV()  # .raw_data_on

        else:
            # g.html.DIV(class_="scope")
            # g.html.DIV(class_="content")
            for i, scope in enumerate(scopes):
                g.html.P()
                g.html.T('<span class="material-icons-outlined">view_in_ar</span>&nbsp;&nbsp;')
                g.html.T(definitions.SIGNINSCOPES[scope]["name"])
                g.html._P()
            # g.html._DIV()  # .content
            # g.html._DIV()  # .scope

    def oauth_incompleteUserData(self, scopes, singleScope=None):
        # Missing data
        incompleteData = False
        for scope in scopes:
            if self.oauth(scope)["missing_required_data"]:
                incompleteData = True
        return incompleteData

    def editPermission(self, propertyNames=[]):
        allowed = list(set(["name", "email", "emailToChange"]) | set(self.invoiceFields))
        overlap = list(set(allowed) & set(propertyNames))
        return overlap and g.user == self

    def viewPermission(self, methodName):
        return methodName in ("accountSubscriptionsView", "userAccountView", "editScopeView", "rawJSONDataView")

    def checkPassword(self, password):
        return bcrypt.checkpw(password.encode(), self.passwordHash.encode())

    def setPassword(self, password):

        if len(password) < 8:
            return False, "Password must be at least 8 characters long."

        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        self.passwordHash = hashed

        return True, None

    def put(self):
        if not self.secretKey:
            self.secretKey = helpers.Garbage(40)
        return super().put()

    def invoiceDataComplete(self):
        return (
            self.invoiceName
            and self.invoiceStreet
            and self.invoiceZIPCode
            and self.invoiceCity
            and self.invoiceCountry
        )

    def stripeGetCustomerId(self):

        if typeworldserver.STRIPELIVE:
            if not self.stripeCustomerId:
                customer = stripe.Customer.create(email=self.email)
                self.stripeCustomerId = customer.id
                self.put()
            return self.stripeCustomerId
        else:
            if not self.stripeTestCustomerId:
                customer = stripe.Customer.create(email=self.email)
                self.stripeTestCustomerId = customer.id
                self.put()
            return self.stripeTestCustomerId

    def stripeTaxExemptStatus(self):
        if self.invoiceCountry == "DE":
            return "none"
        elif self.invoiceCountry in definitions.EU_COUNTRIES:
            if self.invoiceEUVATID:
                return "reverse"
            else:
                return "none"
        else:
            return "exempt"

    def stripeUpdateSubscriptions(self):
        if typeworldserver.STRIPELIVE:
            self.stripeSubscriptions = stripe.Subscription.list(customer=self.stripeGetCustomerId(), status="all")
        else:
            self.stripeTestSubscriptions = stripe.Subscription.list(customer=self.stripeGetCustomerId(), status="all")
        self.put()

    def stripeSubscriptionByProductID(self, productID, statuses=[]):
        if typeworldserver.STRIPELIVE:
            subscriptions = self.stripeSubscriptions
        else:
            subscriptions = self.stripeTestSubscriptions

        # When returned as pure JSON from database as opposed to freshly saved into
        # attribute as returned by stripe
        if "object" in subscriptions and subscriptions["object"] == "list":
            subscriptions = subscriptions["data"]

        for subscription in subscriptions:
            for price in billing_stripe.stripeProducts[productID]["prices"]:
                for item in subscription["items"]["data"]:
                    if item["price"]["id"] == price["id"]:
                        if not statuses or subscription["status"] in statuses:
                            return subscription

    def stripeSubscriptionReceivesService(self, productID):

        product = billing_stripe.stripeProducts[productID]

        if g.form._get("testScenario") == "simulateTestUser1IsPro" and self.email == "test1@type.world":
            return True
        if g.form._get("testScenario") == "simulateTestUser2IsPro" and self.email == "test2@type.world":
            return True

        # Test User
        if product["allowTestUsers"]:
            if TestUserForAPIEndpoint.query(TestUserForAPIEndpoint.userKey == self.key).count():
                return True

        subscription = self.stripeSubscriptionByProductID(productID)
        if not subscription:
            return False

        if subscription["status"] in ("active", "trialing"):
            return True

        else:
            if subscription["status"] == "canceled":
                if product["cancelTime"] == "endOfBillingPeriod":
                    if time.time() < subscription["current_period_end"]:
                        return True
                elif product["cancelTime"] == "immediately":
                    return False

        return False

    def stripePaymentMethod(self):
        if self.stripeGetCustomerId():
            stripeCustomer = stripe.Customer.retrieve(self.stripeGetCustomerId())
            if (
                stripeCustomer
                and stripeCustomer.invoice_settings
                and stripeCustomer.invoice_settings.default_payment_method
            ):
                return stripe.PaymentMethod.retrieve(stripeCustomer.invoice_settings.default_payment_method)

    def stripeSubscriptionPreviousRunningPeriodDays(self, productID):
        """
        Retrieve the number of seconds that a subscription has been previously running.
        Used to reducde trial period for now subscriptions.
        """
        if typeworldserver.STRIPELIVE:
            stripeSubscribedProductsHistory = self.stripeSubscribedProductsHistory
        else:
            stripeSubscribedProductsHistory = self.stripeTestSubscribedProductsHistory

        for key in stripeSubscribedProductsHistory:
            if key == productID:
                seconds = 0
                for period in stripeSubscribedProductsHistory[productID]:
                    if "running_period" in period:
                        seconds += period["running_period"]
                print("seconds", seconds)
                return int(seconds / (24 * 60 * 60))
        return 0

    def beforePut(self):

        if self.invoiceDataComplete():
            self.stripeGetCustomerId()

        # Address has changed
        if set(self._changed) & set(self.invoiceFields):
            if self.stripeGetCustomerId() and (self.invoiceDataComplete()):
                stripe.Customer.modify(
                    self.stripeGetCustomerId(),
                    name=self.invoiceName,
                    address={
                        "line1": self.invoiceStreet,
                        "line2": self.invoiceStreet2,
                        "postal_code": self.invoiceZIPCode,
                        "city": self.invoiceCity,
                        "state": self.invoiceState,
                        "country": self.invoiceCountry,
                    },
                    tax_exempt=self.stripeTaxExemptStatus(),
                )
                print("Updated Stripe Account")

        # VAT ID
        if "invoiceEUVATID" in self._changed:
            if self.invoiceEUVATID:

                exists = False
                for tax_id in stripe.Customer.list_tax_ids(
                    self.stripeGetCustomerId(),
                ):
                    if tax_id.type == "eu_vat" and tax_id.value == self.invoiceEUVATID:
                        exists = True

                if not exists:
                    stripe.Customer.create_tax_id(
                        self.stripeGetCustomerId(),
                        type="eu_vat",
                        value=self.invoiceEUVATID,
                    )
            else:
                for tax_id in stripe.Customer.list_tax_ids(
                    self.stripeGetCustomerId(),
                ):
                    stripe.Customer.delete_tax_id(
                        self.stripeGetCustomerId(),
                        tax_id.id,
                    )
                    print("Deleted Tax ID", tax_id.id)

        # Email has changed
        if "emailToChange" in self._changed:
            self.sendEmailVerificationLink()

    def canSave(self):
        if self.emailToChange == self.email:
            self.emailToChange = None
            return False, "The new email address is identical with the old one."

        if self.emailToChange:
            previousUser = User.query(User.email == self.emailToChange).get(read_consistency=ndb.STRONG)
            if previousUser and previousUser.email == self.emailToChange and self != previousUser:
                self.emailToChange = None
                return False, f"The email address {self.emailToChange} already exists."

        return True, None

    def propagateEmailChange(self):
        if self.stripeGetCustomerId():
            stripe.Customer.modify(self.stripeGetCustomerId(), email=self.email)

    def stripeElement(self):

        paymentMethods = [
            {
                "id": "card",
                "name": "Card",
                "countries": "all",
                "contract": None,
                "inputName": "Card Number",
            },
            {
                "id": "iban",
                "name": "SEPA Direct Debit",
                "countries": [
                    "AU",
                    "AT",
                    "BE",
                    "BG",
                    "CA",
                    "CY",
                    "CZ",
                    "DK",
                    "EE",
                    "FI",
                    "FR",
                    "DE",
                    "GR",
                    "HK",
                    "IE",
                    "IT",
                    "JP",
                    "LV",
                    "LT",
                    "LU",
                    "MT",
                    "MX",
                    "NL",
                    "NZ",
                    "NO",
                    "PL",
                    "PT",
                    "RO",
                    "SG",
                    "SK",
                    "SI",
                    "ES",
                    "SE",
                    "CH",
                    "UK",
                    "US",
                ],
                "contract": (
                    "By providing your payment information and confirming this payment,"
                    " you authorise<br />(A) Type.World/Jan Gerner and Stripe, our"
                    " payment service provider, to send instructions to your bank to"
                    " debit your account and<br />(B) your bank to debit your account"
                    " in accordance with those instructions. As part of your rights,"
                    " you are entitled to a refund from your bank under the terms and"
                    " conditions of your agreement with your bank. A refund must be"
                    " claimed within 8 weeks starting from the date on which your"
                    " account was debited. Your rights are explained in a statement"
                    " that you can obtain from your bank.<br />You agree to receive"
                    " notifications for future debits up to 2 days before they occur."
                ),
                "inputName": "IBAN",
            },
        ]

        def paymentMethodForUser():
            pm = []
            for paymentMethod in paymentMethods:
                if paymentMethod["countries"] == "all" or self.invoiceCountry in paymentMethod["countries"]:
                    pm.append(paymentMethod)
            return pm

        usePaymentMethods = paymentMethodForUser()

        # Tabs
        g.html.P()
        for i, paymentMethod in enumerate(usePaymentMethods):
            g.html.A(
                onclick=(
                    "$('.element-wrappers').slideUp(function()"
                    f" {{$('#{paymentMethod['id']}-element-wrapper').slideDown();}}); "
                    f" setupStripeElement('{paymentMethod['id']}');"
                )
            )
            g.html.T(paymentMethod["name"])
            g.html._A()
            if i < len(usePaymentMethods) - 1:
                g.html.BR()
        g.html._P()

        g.html.smallSeparator()

        # Actual elements
        for i, paymentMethod in enumerate(usePaymentMethods):
            g.html.DIV(
                id=f"{paymentMethod['id']}-element-wrapper",
                class_="element-wrappers " + ("hidden" if i > 0 else ""),
            )
            if paymentMethod["id"] == "iban":
                g.html.P()
                g.html.T("Account Holder Name")
                g.html.BR()
                g.html.INPUT(type="text", name="account-holder-name", id="account-holder-name")
                g.html._P()
            g.html.P()
            if paymentMethod["inputName"]:
                g.html.T(paymentMethod["inputName"])
                g.html.BR()
            g.html.DIV(id=f"{paymentMethod['id']}-element", class_="stripe-element")
            g.html._DIV()
            g.html._P()
            if paymentMethod["contract"]:
                g.html.P(style="font-size: 10pt; line-height: 110%; margin-top: 10px;")
                g.html.T(paymentMethod["contract"])
                g.html._P()
            g.html._DIV()

        g.html.smallSeparator()

        g.html.P()
        g.html.DIV(id="card-element-errors", class_="warning")
        g.html._DIV()
        g.html._P()
        g.html.T(
            """
        <script>

        $( document ).ready(function() {
            setupStripeElement("card");
        });

        </script>
        """
        )

    def accountSubscriptionsView(self, parameters={}, directCallParameters={}):

        # print("parameters", parameters)

        if g.admin or not typeworldserver.LIVE:
            web.reload()
        web.reload(style="hidden")

        g.html.DIV(class_="clear")
        g.html.FORM(id="payment-form")

        # COLUMN 1: BILLING ADDRESS
        g.html.DIV(class_="floatleft", style="width: 40%; ")

        g.html.P()
        g.html.B()
        g.html.T("Billing Address")
        g.html._B()
        g.html._P()

        oauth = self.oauth("billingaddress")
        if oauth["missing_required_data"]:
            g.html.P(class_="warning", id="adblockerwarning")
            g.html.T('<span class="material-icons-outlined">error_outline</span> Billing address is incomplete')
            g.html._P()
        else:
            g.html.P()
            g.html.T(oauth["formatted_billing_address"].replace("\n", "<br />"))
            if self.invoiceEUVATID:
                g.html._P()
                g.html.P()
                g.html.T(f"EU VAT ID: {self.invoiceEUVATID}")
            g.html._P()

        g.html.P()
        self.edit(text="Edit Billing Address", button=True, propertyNames=self.invoiceFields)
        g.html._P()

        g.html.separator()

        g.html.P()
        g.html.B()
        g.html.T("Payment Method")
        g.html._B()
        g.html._P()

        g.html.P()

        paymentMethod = self.stripePaymentMethod()

        if oauth["missing_required_data"]:
            g.html.P(class_="warning", id="adblockerwarning")
            g.html.T('<span class="material-icons-outlined">error_outline</span> Billing address is incomplete')
            g.html._P()
        else:

            if paymentMethod:
                g.html.DIV(id="paymentMethod")  # , class_="hidden" if not paymentMethod else ""

                if paymentMethod.type == "card":
                    g.html.P()
                    g.html.T(
                        f"{paymentMethod.card.brand[:1].upper()}"
                        f"{paymentMethod.card.brand[1:]} (••••"
                        f" {paymentMethod.card.last4}), expires"
                        f" {paymentMethod.card.exp_month}/{paymentMethod.card.exp_year}"
                    )
                    g.html._P()

                elif paymentMethod.type == "sepa_debit":
                    # print(paymentMethod)
                    g.html.P()
                    g.html.T(f"IBAN ({paymentMethod.sepa_debit.country} •••• {paymentMethod.sepa_debit.last4})")
                    g.html.BR()
                    g.html.T(f"Account Holder: {paymentMethod.billing_details.name}")
                    g.html._P()

                    if paymentMethod.billing_details.email != self.email:
                        g.html.P()
                        g.html.T(f"Account Email: {paymentMethod.billing_details.email}")
                        g.html._P()
                        g.html.P(class_="warning")
                        g.html.T(
                            "▲ The email address associated with this bank account is"
                            " not identical to your Type.World account’s email address."
                            " Make sure to update the payment method after you’ve"
                            " changed your Type.World account’s email address to"
                            " receive payment related information on the new email"
                            " address (your account’s new email address will be linked)."
                            " This process cannot be automated."
                        )
                        g.html._P()

                g.html.P()
                g.html.A(
                    class_="button",
                    onclick="enableButtons(); $('#updatePaymentMethod').show(); $('#paymentMethod').hide();",
                )
                g.html.T("Update Payment Method")
                g.html._A()
                g.html._P()

                g.html._DIV()  # paymentMethod

                # Update Payment method
                g.html.DIV(id="updatePaymentMethod", class_="hidden" if paymentMethod else "")

                # Payment
                self.stripeElement()

                g.html.P()
                g.html.A(class_="button", onclick="enableButtons(); updatePaymentMethod();")
                g.html.T("Update Payment Method")
                g.html._A()
                g.html._P()

                g.html._DIV()  # updatePaymentMethod

            # No subscriptions, new payment method
            else:
                # Payment
                self.stripeElement()

        g.html._P()

        g.html._DIV()  # .floatleft

        # COLUMN 3: SUBSCRIPTIONS
        g.html.DIV(class_="floatleft", style="width: 60%;")

        self.stripeUpdateSubscriptions()

        for productID in parameters["products"]:
            # print("productID", productID)
            subscription = self.stripeSubscriptionByProductID(productID)
            # print("subscription", subscription)

            g.html.P()
            g.html.B()
            g.html.T(billing_stripe.stripeProducts[productID]["name"])
            g.html._B()
            g.html._P()

            stripeSubscriptionPreviousRunningPeriodDays = (
                self.stripeSubscriptionPreviousRunningPeriodDays(productID) or 0
            )
            trial_period_days = max(
                0,
                billing_stripe.stripeProducts[productID]["trial_period_days"]
                - stripeSubscriptionPreviousRunningPeriodDays,
            )
            if g.user.email == "test@type.world":
                trial_period_days = 1
            g.html.P(style="color: #999;")
            g.html.T(
                billing_stripe.stripeProducts[productID]["description"].replace(
                    "%%trial_period_days%%", str(trial_period_days)
                )
            )

            # Tax
            g.html.BR()
            taxStatus = self.stripeTaxExemptStatus()
            if taxStatus == "none":
                g.html.T("Tax: Add 19% German VAT")
            elif taxStatus == "reverse":
                g.html.T(f"Tax: Reverse Charge; you owe VAT to {definitions.COUNTRIES_DICT[g.user.invoiceCountry]}")
            elif taxStatus == "exempt":
                g.html.T("Tax: No VAT owed")

            g.html._P()

            if subscription and subscription["status"] in (
                "active",
                "trialing",
                "canceled",
            ):
                g.html.P()
                g.html.T(f"Status: {subscription['status']}")

                fromtimestamp = datetime.datetime.fromtimestamp
                if subscription["status"] == "trialing":
                    g.html.BR()
                    g.html.T(f"Trial ends: {fromtimestamp(subscription['trial_end'])}")
                if subscription["status"] == "active":
                    g.html.BR()
                    g.html.T(f"Current billing period ends: {fromtimestamp(subscription['current_period_end'])}")
                if self.stripeSubscriptionReceivesService(productID) and subscription["status"] == "canceled":
                    g.html.BR()
                    g.html.T(f"Receives service until: {fromtimestamp(subscription['current_period_end'])}")
                g.html._P()

            else:
                if stripeSubscriptionPreviousRunningPeriodDays:
                    g.html.P(style="color: #999;")
                    g.html.T(f"Previously active: {stripeSubscriptionPreviousRunningPeriodDays} day(s)")
                    g.html._P()

            # Upcoming invoice
            if subscription and subscription["status"] == "active":
                if billing_stripe.stripeProducts[productID]["type"] == "metered":
                    invoice = stripe.Invoice.upcoming(subscription=subscription["id"])
                    # print(invoice)

                    g.html.smallSeparator()
                    g.html.P()
                    g.html.TABLE()
                    g.html.TR()
                    g.html.TH(style="width: 50%;")
                    g.html.T("Upcoming Invoice")
                    g.html._TH()
                    g.html.TH(style="width: 25%;")
                    g.html.T("Qty")
                    g.html._TH()
                    g.html.TH(style="width: 25%;")
                    g.html.T("Price")
                    g.html._TH()
                    g.html._TR()

                    for line in invoice["lines"]["data"]:
                        g.html.TR()

                        g.html.TD()
                        for price in billing_stripe.stripeProducts[productID]["prices"]:
                            if price["id"] == line["price"]["id"]:
                                g.html.T(price["name"])
                                break
                        g.html._TD()

                        g.html.TD()
                        g.html.T(line["quantity"])
                        g.html._TD()

                        g.html.TD()
                        g.html.T("%.2f&thinsp;€" % (line["amount"] / 100))
                        g.html._TD()

                        g.html._TR()

                    if invoice["tax"]:
                        g.html.TR()
                        g.html.TD()
                        g.html.B()
                        g.html.T("Subtotal")
                        g.html._B()
                        g.html._TD()
                        g.html.TD()
                        g.html._TD()
                        g.html.TD()
                        g.html.B()
                        g.html.T("%.2f&thinsp;€" % (invoice["subtotal"] / 100))
                        g.html._B()
                        g.html._TD()
                        g.html._TR()
                        g.html.TR()
                        g.html.TD()
                        g.html.B()
                        g.html.T(f"{invoice['default_tax_rates'][0]['percentage']}% VAT")
                        g.html._B()
                        g.html._TD()
                        g.html.TD()
                        g.html._TD()
                        g.html.TD()
                        g.html.B()
                        g.html.T("%.2f&thinsp;€" % (invoice["tax"] / 100))
                        g.html._B()
                        g.html._TD()
                        g.html._TR()
                    g.html.TR()
                    g.html.TD()
                    g.html.B()
                    g.html.T("Total")
                    g.html._B()
                    g.html._TD()
                    g.html.TD()
                    g.html._TD()
                    g.html.TD()
                    g.html.B()
                    g.html.T("%.2f&thinsp;€" % (invoice["total"] / 100))
                    g.html._B()
                    g.html._TD()
                    g.html._TR()

                    g.html._TABLE()
                    g.html._P()

            if subscription and subscription["status"] in ("active", "trialing"):
                g.html.P()
                g.html.A(
                    class_="button attention",
                    onclick=(
                        "enableButtons();"
                        f" if(confirm('{billing_stripe.stripeProducts[productID]['cancelWarning'] or 'Are you sure?'}"
                        f"')){{cancelSubscription('{productID}');}}"
                    ),
                )
                g.html.T("Cancel Plan")
                g.html._A()
                g.html._P()
            else:
                g.html.P()
                method = "createAdditionalSubscription" if paymentMethod else "createInitialSubscription"
                g.html.A(
                    class_="button " + ("dead" if not self.invoiceDataComplete() else ""),
                    onclick=(
                        "enableButtons(); if(confirm('Are you sure you want to subscribe to this product? Billing"
                        " will be activated after"
                        f" this.')){{{method}('{productID}');}}"
                        " else { enableButtons(); }"
                    ),
                )
                g.html.T("Subscribe to Plan")
                g.html._A()
                g.html._P()

            g.html.separator()

        g.html._DIV()  # .floatleft
        g.html._FORM()
        g.html._DIV()  # .clear

    def userAccountView(self, parameters={}, directCallParameters={}):

        g.html.DIV(class_="clear")
        g.html.DIV(class_="floatleft", style="width: 50%;")

        g.html.P()
        g.html.T(g.user.name)
        g.html.BR()
        self.edit(text="Change Name", button=True, propertyNames=["name"])
        g.html._P()

        g.html.P()
        g.html.T(self.email)
        g.html.BR()
        if self.emailToChange:
            g.html.SPAN(class_="warning")
            g.html.T(f"▲ The email address {self.emailToChange} is awaiting verification. Please check your inbox.")
            g.html._SPAN()
            g.html.BR()
        self.edit(
            text="Change Email Address",
            button=True,
            propertyNames=["emailToChange"],
            values={"emailToChange": self.emailToChange or self.email},
        )
        g.html._P()

        g.html._DIV()  # .floatleft
        g.html.DIV(class_="floatleft", style="width: 50%;")

        g.html.FORM()
        g.html.P()
        g.html.T("Choose a new password")
        g.html._P()
        g.html.P()
        g.html.T("New Password")
        g.html.BR()
        g.html.INPUT(id="reset_password", name="reset_password", type="password")
        g.html._P()
        g.html.P()
        g.html.T("Repeat New Password")
        g.html.BR()
        g.html.INPUT(id="reset_password2", name="reset_password2", type="password")
        g.html._P()
        g.html.P()
        g.html.A(
            class_="button",
            onclick=(
                "AJAX('#action', '/resetPasswordAction', {'password':"
                " $('#reset_password').val(), 'password2':"
                " $('#reset_password2').val(), 'inline': 'true', 'reload': 'false'});"
            ),
        )
        g.html.T("Save New Password")
        g.html._A()
        g.html._P()
        g.html._FORM()

        g.html._DIV()  # .floatleft
        g.html._DIV()  # .clear

    @classmethod
    def _pre_delete_hook(cls, key):
        puts = []
        deletes = []
        if key:
            deletes.extend(AppInstance.query(ancestor=key).fetch(keys_only=True))
            deletes.extend(Subscription.query(ancestor=key).fetch(keys_only=True))
            deletes.extend(Subscription.query(Subscription.invitedByUserKey == key).fetch(keys_only=True))
            deletes.extend(TestUserForAPIEndpoint.query(TestUserForAPIEndpoint.userKey == key).fetch(keys_only=True))
            for endpoint in APIEndpoint.query(APIEndpoint.userKey == key).fetch(read_consistency=ndb.STRONG):
                endpoint.userKey = None
                puts.append(endpoint)

                # TODO: Delete Stripe subscriptions
            deletes.extend(OAuthToken.query(OAuthToken.userKey == key).fetch(keys_only=True))

        if puts:
            ndb.put_multi(puts)
        if deletes:
            ndb.delete_multi(deletes)

        print("_pre_delete_hook DONE 1")

    def pubSubTopicID(self):
        return "user-%s" % self.publicID()

    def announceChange(self, sourceAnonymousAppID=""):

        parameters = {}
        parameters["topic"] = self.pubSubTopicID()
        parameters["command"] = "pullUpdates"
        if sourceAnonymousAppID:
            parameters["sourceAnonymousAppID"] = sourceAnonymousAppID

        success, response = mq.announceToMQ(parameters)

        if success:
            return True, None
        else:
            return False, response

    def appInstances(self):
        return AppInstance.query(ancestor=self.key).order(-AppInstance.lastUsed).fetch(read_consistency=ndb.STRONG)  #

    def subscriptions(self):
        return [x for x in Subscription.query(ancestor=self.key).fetch(read_consistency=ndb.STRONG) if x.key.id()]

    def subscriptionByURL(self, url, subscriptions=None):
        if subscriptions is None:
            subscriptions = self.subscriptions()
        for subscription in subscriptions:
            if subscription.url == url:
                return subscription

    def confirmedSubscriptions(self, subscriptions=None):
        if subscriptions is None:
            subscriptions = self.subscriptions()
        return [x for x in subscriptions if x and x.confirmed is True]

    def unconfirmedSubscriptions(self, subscriptions=None):
        if subscriptions is None:
            subscriptions = self.subscriptions()
        return [x for x in subscriptions if x and x.confirmed is False]

    def regularSubscriptions(self, subscriptions=None):
        if subscriptions is None:
            subscriptions = self.subscriptions()
        return [x for x in subscriptions if x and x.confirmed is True and x.type != "invitation"]

    def subscriptionInvitations(self, subscriptions=None):
        if subscriptions is None:
            subscriptions = self.subscriptions()
        return [x for x in subscriptions if x and x.type == "invitation"]

    def APIEndpoints(self):
        return APIEndpoint.query(APIEndpoint.userKey == self.key).fetch(read_consistency=ndb.STRONG)

    def sentInvitations(self):
        return Subscription.query(Subscription.invitedByUserKey == self.key).fetch(read_consistency=ndb.STRONG)

    def sendEmailVerificationLink(self, redirectURL=None):

        # TODO: avoid random duplicates
        self.emailVerificationCode = helpers.Garbage(40)
        if redirectURL:
            self.emailVerificationRedirectURL = redirectURL

        body = f"""\
Hello {self.name},

"""

        if self.email == self.emailToChange:
            body += "thank you for signing up for your Type.World account."
        else:
            body += "thank you for updating your Type.World email address."

        body += f"""

Please verify your email address by clicking on the following link:
{g.rootURL}/verifyemail/{self.emailVerificationCode}

IMPORTANT NOTE: Make sure that the link opens in the same browser that you created the account with.

"""
        body += definitions.EMAILFOOTER

        # Send email
        success, message = helpers.email(
            "Type.World <hq@mail.type.world>",
            [self.emailToChange or self.email],
            "Type.World: Confirm your email address",
            body,
        )

        if success:
            self.put()

        return success, message

    def isTranslator(self):
        if g.user:
            if translations.Translation_User.query(translations.Translation_User.userKey == self.key).fetch(
                read_consistency=ndb.STRONG
            ):
                return True

        return False

    def isTranslatorForLocales(self):
        return translations.Translation_User.query(translations.Translation_User.userKey == self.key).fetch(
            read_consistency=ndb.STRONG
        )


class AppInstance(TWNDBModel):
    # key = anonymousAppID
    # 	userKey = web.KeyProperty(required = True)
    machineModelIdentifier = web.StringProperty()
    machineHumanReadableName = web.StringProperty()
    machineSpecsDescription = web.StringProperty()
    machineOSVersion = web.StringProperty()
    machineNodeName = web.StringProperty()
    lastUsed = web.DateTimeProperty(required=True)

    X_Appengine_City = web.StringProperty()
    X_Appengine_Country = web.StringProperty()
    X_Appengine_Region = web.StringProperty()
    X_Appengine_Citylatlong = web.GeoPtProperty()

    revoked = web.BooleanProperty()
    revokeResponse = web.StringProperty()
    revokedTime = web.DateTimeProperty()

    # def put(self):
    # 	if self.userKey:
    # 		user = self.userKey.get(read_consistency=ndb.STRONG)
    # 		if not self.key in user.appInstanceKeys:
    # 			user.appInstanceKeys.append(self.key)
    # 			user.put()

    # 	return super().put()

    # @classmethod
    # def _pre_delete_hook(cls, key):
    # 	if key:
    # 		self = key.get(read_consistency=ndb.STRONG)
    # 		if self:
    # 			if self.userKey:
    # 				user = self.userKey.get(read_consistency=ndb.STRONG)
    # 				user.appInstanceKeys.remove(self.key)
    # 				user.put()

    def updateUsage(self):

        # Machine
        for keyword in (
            "machineModelIdentifier",
            "machineHumanReadableName",
            "machineSpecsDescription",
            "machineOSVersion",
            "machineNodeName",
        ):
            if g.form._get(keyword):
                setattr(self, keyword, g.form._get(keyword))

        # Location
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
                setattr(self, keyword.replace("-", "_"), value)

        # Time
        self.lastUsed = helpers.now()

    def isVM(self):
        return (
            self.machineModelIdentifier
            and self.machineModelIdentifier.startswith("Parallels")
            or self.machineHumanReadableName
            and self.machineHumanReadableName.startswith("Parallels")
        )

    def machineImage(self):

        if self.isVM():
            return "other/brain.svg"

        elif self.machineOSVersion and self.machineOSVersion.startswith("Windows"):
            return "other/pc.svg"

        else:
            models = [
                ["MacBookPro", "002-macbook-pro-1.svg"],
                ["MacBook", "024-macbook.svg"],
                ["iMac", "040-imac.svg"],
                ["Macmini", "048-mac-mini.svg"],
                ["MacPro6", "049-mac-pro.svg"],
                ["MacPro", "021-mac-pro-1.svg"],
            ]

            for modelName, fileName in models:
                if self.machineModelIdentifier and self.machineModelIdentifier.startswith(modelName):
                    return "apple/" + fileName

        return "other/pc.svg"

    def revoke(self, status):

        failed = []

        user = self.key.parent().get(read_consistency=ndb.STRONG)
        for subscription in user.subscriptions():
            success, endpoint = subscription.rawSubscription().APIEndpoint()
            if not success:
                # print("No endpoint", endpoint)
                return False, endpoint
            if endpoint:

                if status == "revoked":
                    success, client = subscription.rawSubscription().client()
                    if not success:
                        return False, client

                    client.set("typeworldUserAccount", user.publicID())
                    success, message, publisher, subscription = client.addSubscription(subscription.url, remotely=True)
                    if not success:
                        return (
                            False,
                            f"Couldn’t revoke app instance. Adding subscription for revocation returned: {message}",
                        )
                    success, message = client.uninstallAllProtectedFonts(dryRun=True)
                    if not success:
                        return (
                            False,
                            f"Couldn’t revoke app instance. uninstallAllProtectedFonts() returned: {message}",
                        )
            else:
                return False, "noAPIEndpoint"

        self.revoked = True if status == "revoked" else False
        self.revokedTime = helpers.now()
        self.revokeResponse = "\n".join(map(str, failed))
        self.put()
        return True, None


class APILog(TWNDBModel):
    # parent = APIEndpoint
    command = web.StringProperty(required=True)
    reason = web.StringProperty()
    incoming = web.JsonProperty(required=True)
    response = web.JsonProperty(required=True)
    billedAs = web.StringProperty()


class APIEndpoint(TWNDBModel):
    """
    APIEndpoint is registered per Type.World user (as role as developer).
    Developers must create an APIEndpoint in the user account on the website
    in order to receive a secret APIKey to use for querying the API.
    """

    # ID = url
    endpointCommand = web.JsonProperty()
    userKey = web.KeyProperty()
    APIKey = web.StringProperty()

    # sentInvitationSubscriptionKeys = web.KeyProperty(repeated = True)
    # aliveSeconds = 1 * 7 * 24 * 60 * 60 # older than one week

    def viewPermission(self, methodName):
        return methodName in ("logView")

    @classmethod
    def _pre_delete_hook(cls, key):
        puts = []
        deletes = []
        if key:
            self = key.get(read_consistency=ndb.STRONG)
            if self is not None:
                for testUser in self.testUsers():
                    deletes.append(testUser.key)

        if puts:
            ndb.put_multi(puts)
        if deletes:
            ndb.delete_multi(deletes)

    def user(self):
        if self.userKey:
            if not hasattr(self, "_user"):
                self._user = self.userKey.get(read_consistency=ndb.STRONG)
            return self._user

    def getAPIKey(self):
        if not self.APIKey:
            self.APIKey = helpers.Garbage(40)
            self.put()
        return self.APIKey

    def deletePermission(self):
        return self.userKey and self.userKey == g.user.key

    def getEndpointCommand(self, update=False):
        if not self.endpointCommand:
            success, message = self.updateJSON(force=True)
            if not success:
                return False, message
        endpoint = typeworld.api.EndpointResponse()
        endpoint.loadDict(self.endpointCommand)
        return True, endpoint

    def client(self):
        if "GAE_VERSION" in os.environ:
            mothership = f"https://{os.environ['GAE_VERSION']}-dot-typeworld2.appspot.com/v1"
            client = typeworld.client.APIClient(
                online=True,
                mothership=mothership,
                secretTypeWorldAPIKey=self.APIKey,
                commercial=True,
                appID="world.type.app",
            )
        else:
            client = typeworld.client.APIClient(
                online=True,
                secretTypeWorldAPIKey=self.APIKey,
                commercial=True,
                appID="world.type.app",
            )
        # client.set("typeworldUserAccount", typeworldserver.secret("TEST_TYPEWORLDUSERACCOUNTID"))
        # # test@type.world
        g.instanceVersion

        if g.form._get("testScenario"):
            client.testScenario = g.form._get("testScenario")

        return True, client

    def updateJSON(self, force=False):
        # Fetch JSON Root
        # Return True if new info was fetched (for saving) upstream

        url = self.key.id()

        if not self.endpointCommand or force:
            # or not self.touched or (self.touched and
            # ((helpers.now() - self.touched).seconds > self.aliveSeconds))

            success, client = self.client()
            if not success:
                return False, client

            success, endpointCommand = client.endpointCommand(url)

            if success:
                self.endpointCommand = endpointCommand.dumpDict(validate=False)
                self.put()
                return True, None
            else:
                return False, "%s: %s" % (endpointCommand, url)

        else:
            return False, "notUpdated"

    def testUsers(self):
        """
        Find and return all TestUserForAPIEndpoint for this APIEndpoint
        """
        users = []
        # Add self
        # if self.userKey:
        #     users.append(TestUserForAPIEndpoint(userKey=self.userKey))
        # Add others
        for user in TestUserForAPIEndpoint.query(ancestor=self.key).fetch(read_consistency=ndb.STRONG):
            if user:
                users.append(user)
        return users

    def hasSubscriptionUpdateQuota(self):
        """
        Returns True if APIEndpoint is billable or monthly free quota hasn't been reached yet.
        """

        # Quota reached simulation
        if g.form._get("testScenario") == "simulateUpdateSubscriptionQuotaReached":
            return False

        # Stripe Subscriptions
        user = self.user()
        return user.stripeSubscriptionReceivesService("world.type.professional_publisher_plan")

    def billNonCumulativeMetrics(self):

        # Stripe subscription
        user = self.user()
        print(self.key, user.email)
        stripeSubscription = user.stripeSubscriptionByProductID("world.type.professional_publisher_plan")
        if not stripeSubscription:
            return False, "APIEndpoint.billNonCumulativeMetrics():unknownStripeSubscription"
        assert stripeSubscription["current_period_start"], "No invoice period start value available"

        # Users
        subscriptions = Subscription.query(Subscription.endpointKey == self.key).fetch(read_consistency=ndb.STRONG)
        userKeys = []
        activeUsers = []
        for subscription in subscriptions:
            userKey = subscription.key.parent()
            if userKey and userKey not in userKeys:
                userKeys.append(userKey)
        # Fetch users
        # month, year = self.getMonthAndYear()
        users = ndb.get_multi(userKeys)
        # See if they were active
        for activeUser in users:
            if activeUser:
                if activeUser.lastSeenOnline and activeUser.lastSeenOnline >= datetime.datetime.fromtimestamp(
                    stripeSubscription["current_period_start"]
                ):
                    # print("Last seen online:", user)
                    activeUsers.append(activeUser)

        success, message = user.bill("world.type.professional_publisher_plan", "users", quantity=len(activeUsers))
        if not success:
            return False, message

        return True, None

    def logView(self, parameters={}, directCallParameters={}):

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

        g.html.P()
        g.html.T("Last 20 items are shown. Records older than April 13th 2021 are not available.")
        g.html._P()

        buttonColor = "purple"
        g.html.P()
        g.html.T("Load/reload: ")
        web.reload(
            text="All",
            style="button",
            backgroundColor=buttonColor if "command" not in parameters else None,
        )
        # g.html._P()

        # Unique used commands
        categories = APILog.query(ancestor=self.key, distinct_on=["command"]).fetch(read_consistency=ndb.STRONG)
        commands = sorted(list(set([data.command for data in categories])))

        # g.html.P()
        for command in commands:
            web.reload(
                text=command,
                style="button",
                parameters={"command": command},
                backgroundColor=buttonColor
                if ("command" in parameters and parameters["command"] == command)
                else None,
            )
        g.html._P()

        if "command" in parameters:
            logs = (
                APILog.query(APILog.command == parameters["command"], ancestor=self.key)
                .order(-APILog.touched)
                .fetch(20, read_consistency=ndb.STRONG)
            )
        else:
            logs = APILog.query(ancestor=self.key).order(-APILog.touched).fetch(20, read_consistency=ndb.STRONG)
        if logs:

            for log in logs:
                g.html.separator()

                g.html.P()
                g.html.T(
                    f"Command: <b>{log.command}</b> <a"
                    f" href='/developer/api/#{log.command}' target='_blank'><span"
                    " class='material-icons-outlined'>open_in_new</span></a>"
                )
                g.html.BR()
                g.html.T(f"Time: {log.touched} (GMT)")
                if log.billedAs:
                    g.html.BR()
                    name = definitions.PRODUCTS[log.billedAs]["name"]
                    g.html.T(f"Billed as: <b>{name}</b>")
                    if log.reason:
                        g.html.BR()
                        if log.reason == "firstAppearance":
                            g.html.T("Reason: <b>First Appearance</b>")
                        elif log.reason == "addedFonts":
                            g.html.T("Reason: <b>Added Fonts</b>")

                g.html._P()

                g.html.P()
                g.html.T("Incoming Parameters:")
                g.html._P()
                _highlight = highlight(
                    json.dumps(log.incoming, indent=2, sort_keys=True),
                    PythonLexer(),
                    HtmlFormatter(),
                )
                g.html.T(_highlight)

                g.html.P()
                g.html.T("Response:")
                g.html._P()
                _highlight = highlight(
                    json.dumps(log.response, indent=2, sort_keys=True),
                    PythonLexer(),
                    HtmlFormatter(),
                )
                g.html.T(_highlight)

        else:
            g.html.P()
            g.html.T("The logs are still empty.")
            g.html._P()


class TestUserForAPIEndpoint(TWNDBModel):
    """
    Each API Endpoint may define up to 10 test users for evaluating the system.
    They will be hung to the APIEndpoint by parent property.
    """

    userKey = web.KeyProperty(required=True)

    def deletePermission(self):
        return g.user == self.key.parent().get(read_consistency=ndb.STRONG).userKey.get(read_consistency=ndb.STRONG)


class APIEndpointContract(TWNDBModel):
    # keyword = web.StringProperty(required=True)
    # name = web.StringProperty(required=True)
    # priceStructure = web.JsonProperty(required=True)

    def calculatePrices(self, category, quantity):
        def Interpolate(a, b, p, limit=False):
            """\
            Interpolate between values a and b at float position p (0-1)
            Limit: No extrapolation
            """
            i = a + (b - a) * p
            if limit and i < a:
                return a
            elif limit and i > b:
                return b
            else:
                return i

        def calculateSinglePrice(price, qty):
            # minPrice = price["tiers"][0]["price"]
            # maxPrice = price["tiers"][-1]["price"]
            # minQty = price["tiers"][0]["quantity"]
            # maxQty = price["tiers"][-1]["quantity"]

            sum = 0

            for tier in price["tiers"]:

                # Normal price, not infinity
                if tier["quantity"] != -1:
                    if qty <= tier["quantity"]:
                        sum += qty * tier["price"]
                        return sum
                    else:
                        sum += tier["quantity"] * tier["price"]
                        qty -= tier["quantity"]

                # Last price to infinity
                else:
                    sum += qty * tier["price"]
                    return sum

        prices = self.priceStructure[category]
        calculatedPrice = calculateSinglePrice(prices, quantity)

        return calculatedPrice

    def billingCalculation(self, quantityByCategory):
        """
        Calculate an invoice from readily accumulated input data.
        Returns dict {"positions": [[category, name, freeQuota, quantity, tiers, sum]], "total": 0.0}
        """

        def roundDecimals(number):
            return float("%.8f" % number)

        bill = {
            "positions": [],
            "total": 0,
        }
        for incidentCategory in self.priceStructure:
            if incidentCategory in quantityByCategory:

                category = self.priceStructure[incidentCategory]

                description = category["name"]
                quantity = quantityByCategory[incidentCategory]
                freeQuota = category["tiers"][0]["quantity"] if category["tiers"][0]["price"] == 0 else 0
                # quantityAfterFreeQuota = max(0, (quantity - freeQuota))
                singlePrice = roundDecimals(self.calculatePrices(incidentCategory, quantity))
                tiers = []
                total = 0

                quantityLeft = quantity
                # free quota tier

                singlePrice = 0
                # singleTotal = 0

                # other prices
                for i, tier in enumerate(category["tiers"]):

                    # this tier and previous tier
                    tier = category["tiers"][i]
                    if i > 0:
                        previousTier = category["tiers"][i - 1]
                    else:
                        previousTier = None

                    # not last tier
                    if tier["quantity"] > 0:
                        if previousTier:
                            _from = previousTier["quantity"] + 1
                        else:
                            _from = 1
                        _to = tier["quantity"]
                        _tierRange = _to - _from + 1
                    # last tier
                    else:
                        _from = previousTier["quantity"] + 1
                        _to = -1
                        _tierRange = -1

                    if _tierRange > 0:
                        _quantity = min(quantityLeft, _tierRange)
                    else:
                        _quantity = quantityLeft
                    _unitPrice = tier["price"]
                    _price = float("%.5f" % (_quantity * tier["price"]))
                    tiers.append(
                        {
                            "from": _from,
                            "to": _to,
                            "range": _tierRange,
                            "quantity": _quantity,
                            "unitPrice": _unitPrice,
                            "price": _price,
                        }
                    )

                    if tier["quantity"] == -1:
                        quantityLeft = 0
                    else:
                        quantityLeft -= _quantity
                    total += _price

                    for tier in tiers:
                        if tier["quantity"] > 0:
                            singlePrice = tier["unitPrice"]

                # singleTotal = float("%.2f" % (singleTotal))
                bill["positions"].append(
                    [
                        incidentCategory,
                        description,
                        freeQuota,
                        quantity,
                        tiers,
                        singlePrice,
                        sum([x["price"] for x in tiers]),
                    ]
                )
                bill["total"] += total

        return bill


class RawSubscription(TWNDBModel):
    """
    One RawSubscription object exists for each real subscription out there.
    They are referenced from Subscription objects which are held by users.
    """

    secretURL = web.StringProperty()
    canonicalURL = web.StringProperty()
    subscriptionName = web.JsonProperty()
    fonts = web.IntegerProperty(default=0)
    families = web.IntegerProperty(default=0)
    foundries = web.IntegerProperty(default=0)
    contentLastUpdated = web.DateTimeProperty()
    installableFontsCommand = web.JsonProperty()
    lastErrorReported = web.DateTimeProperty()  # by api.type.world/v1/reportAPIEndpointError

    def __repr__(self):
        return f"<RawSubscription '{self.key.urlsafe().decode()}'>"

    @staticmethod
    def keyURL(url):
        return typeworld.client.URL(url).shortUnsecretURL()

    def pubSubTopicID(self):
        """
        Short URL without secretKey and accessToken
        """
        return "subscription-%s" % urllib.parse.quote_plus(typeworld.client.URL(self.secretURL).shortUnsecretURL())

    def announceChange(self, delay, sourceAnonymousAppID):

        parameters = {}
        parameters["topic"] = self.pubSubTopicID()
        parameters["command"] = "pullUpdates"
        if self.contentLastUpdated:
            parameters["serverTimestamp"] = int(self.contentLastUpdated.timestamp())
        parameters["sourceAnonymousAppID"] = sourceAnonymousAppID
        parameters["delay"] = int(delay)

        success, response = mq.announceToMQ(parameters)

        if success:
            return True, None
        else:
            return False, response

    def client(self, withAPIKey=True):

        APIKey = None
        if withAPIKey:
            success, endpoint = self.APIEndpoint()
            if success:
                APIKey = endpoint.APIKey
            else:
                return False, endpoint

        # TODO: This hsoul dowrk, but it doesn't.
        # This script can't access itself through a https request.
        # if 'GAE_VERSION' in os.environ:
        #     if LIVE:
        #         mothership = f"https://{os.environ['GAE_VERSION']}-dot-typeworld2.appspot.com/v1"
        #     else:
        #         mothership = f"https://api.type.world/v1"
        #     client = typeworld.client.APIClient(online=True, mothership=mothership,
        # secretTypeWorldAPIKey=APIKey, commercial=True, appID="world.type.app")
        # else:
        client = typeworld.client.APIClient(
            online=True,
            secretTypeWorldAPIKey=APIKey,
            commercial=True,
            appID="world.type.app",
        )

        if g.form._get("testScenario"):
            client.testScenario = g.form._get("testScenario")

        return True, client

    def updateJSON(self, force=False, save=True):

        if (
            force
            or not self.contentLastUpdated
            or (self.contentLastUpdated and ((helpers.now() - self.contentLastUpdated).seconds > 24 * 60 * 60))
        ):  # 1 day

            # start = time.time()

            success, client = self.client()
            if not success:
                return False, client, {}

            success, message, publisher, subscription = client.addSubscription(self.secretURL, remotely=True)
            if not success:
                if type(message) in (
                    typeworld.api.MultiLanguageText,
                    typeworld.api.MultiLanguageLongText,
                ):
                    message = message.getText()
                return False, message, {}

            print("updateJSON() 3")

            # Previously saved
            if self.installableFontsCommand:

                oldInstallableFontsCommand = typeworld.api.InstallableFontsResponse()
                try:
                    oldInstallableFontsCommand.loadDict(self.installableFontsCommand)
                except Exception:
                    logging.warning(f"Couldn't parse: {self.installableFontsCommand}")
                    logging.warning(traceback.format_exc())
                    oldInstallableFontsCommand = None
            else:
                oldInstallableFontsCommand = None

            print("updateJSON() 4")

            # Save installableFontsCommand
            (
                success,
                installableFontsCommand,
            ) = subscription.protocol.installableFontsCommand()
            if not success:
                return False, installableFontsCommand, {}
            self.installableFontsCommand = installableFontsCommand.dumpDict(validate=False)

            # Save canonicalURL
            success, endpointCommand = subscription.protocol.endpointCommand()
            if not success:
                return False, endpointCommand, {}
            self.canonicalURL = (
                f"typeworld://{subscription.protocol.url.protocol}+{endpointCommand.canonicalURL.replace('://', '//')}"
            )

            print("updateJSON() 5")

            # Save subscription name
            if installableFontsCommand.name.getText():
                self.subscriptionName = installableFontsCommand.name.dumpDict(validate=False)

            # Changes
            if oldInstallableFontsCommand:
                changes = oldInstallableFontsCommand.getContentChanges(
                    installableFontsCommand, calculateOverallChanges=False
                )
            else:
                changes = {}

            print("updateJSON() 6")

            # Parse details
            foundries = len(installableFontsCommand.foundries)
            families = 0
            fonts = 0
            for foundry in installableFontsCommand.foundries:
                families += len(foundry.families)
                for family in foundry.families:
                    fonts += len(family.fonts)
            self.fonts = fonts
            self.families = families
            self.foundries = foundries

            self.contentLastUpdated = helpers.now()

            if save:
                self.put()

            print("updateJSON() 7")

            return True, None, changes

        return True, None, {}

    def APIEndpoint(self):

        if not self.canonicalURL or typeworld.client.urlIsValid(self.canonicalURL)[0] is False:

            success, protocol = typeworld.client.getProtocol(self.secretURL)
            if not success:
                return False, protocol

            success, endpoint = protocol.endpointCommand()
            if not success:
                return False, endpoint
            self.canonicalURL = (
                f"typeworld://{typeworld.client.URL(self.secretURL).protocol}"
                f"+{endpoint.canonicalURL.replace('://', '//')}"
            )
            self.put()

        else:
            success = True
            message = None

        if success and self.canonicalURL or success is False and message == "notUpdated":
            return True, APIEndpoint.get_or_insert(self.canonicalURL)  # , read_consistency=ndb.STRONG
        else:
            return False, message

    def descriptionForEmail(self):

        body = ""

        origin = "Type.World"
        success, apiEndpoint = self.APIEndpoint()
        if success:
            success, endpointCommand = apiEndpoint.getEndpointCommand()
            if not success:
                return False, endpointCommand, None, None
            origin = endpointCommand.name.getText()
            body += "Fonts are provided by: %s (%s)\n" % (
                origin,
                endpointCommand.websiteURL,
            )

        if self.subscriptionName:
            body += "Subscription Name: %s\n" % (typeworld.api.MultiLanguageText(dict=self.subscriptionName).getText())
        if self.foundries != 0 and self.families != 0 and self.fonts != 0:
            body += "With %s font/s in %s family/ies from %s foundry/ies\n" % (
                self.fonts,
                self.families,
                self.foundries,
            )

        return True, None, body, origin


class Subscription(TWNDBModel):
    """
    Subscription object represents a subscription that is being held by a user,
    therefore it is attached to a user account by the object’s parent.

    It holds information about being an invitation etc.

    The RawSubscription object in turn is a single object
    that all user subscriptions point to.
    It can be retrieved with self.rawSubscription()
    """

    # parent = user.key
    url = web.StringProperty(required=True)

    # Invitations
    type = web.StringProperty()
    confirmed = web.BooleanProperty(default=False)
    invitedByUserKey = web.KeyProperty()
    invitedByAPIEndpointKey = web.KeyProperty()
    invitedTime = web.DateTimeProperty()
    invitationAcceptedTime = web.DateTimeProperty()
    invitationRevokedByUserKey = web.KeyProperty()
    invitationRevokedByAPIEndpointKey = web.KeyProperty()
    endpointKey = web.KeyProperty()

    def rawSubscription(self):
        if not hasattr(self, "_rawSubscription"):
            self._rawSubscription = RawSubscription.get_or_insert(
                RawSubscription.keyURL(self.url)
            )  # , read_consistency=ndb.STRONG
            self._rawSubscription.secretURL = self.url

            # Link directly to APIEndpoint
            if not self.endpointKey:
                success, endpoint = self._rawSubscription.APIEndpoint()
                if success:
                    self.endpointKey = endpoint.key
                    self.put()

        return self._rawSubscription

    def sendInvitationEmail(self):

        user = self.key.parent().get(read_consistency=ndb.STRONG)

        if user.email not in definitions.KNOWNEMAILADDRESSES:
            rawSubscription = self.rawSubscription()
            getEndpointSuccess, endpoint = rawSubscription.APIEndpoint()
            if not getEndpointSuccess:
                return False, endpoint

            invitedByUser = (
                self.invitedByUserKey or self.invitedByAPIEndpointKey.get(read_consistency=ndb.STRONG).userKey
            ).get(read_consistency=ndb.STRONG)

            body = f"""\
Hi {user.name} ({user.email}),

you’ve been invited by {invitedByUser.name} ({invitedByUser.email}) to use a font subscription in the Type.World app.
Here are the details:

"""

            success, message, desc, origin = rawSubscription.descriptionForEmail()
            if not success:
                return False, message

            body += desc

            body += """\

Open the Type.World App now to access the fonts in the subscription: typeworldapp://open

"""

            body += definitions.EMAILFOOTER

            # Send email
            success, message = helpers.email(
                "Type.World Subscriptions <subscriptions@mail.type.world>",
                [user.email],
                f"Type.World App: Invitation to share {origin} font subscription",
                body,
                replyTo=invitedByUser.email,
            )
            if not success:
                return False, f"Email: {message}"

        return True, None

    def sendAcceptedEmail(self):

        user = self.key.parent().get(read_consistency=ndb.STRONG)

        if user.email not in definitions.KNOWNEMAILADDRESSES:
            rawSubscription = self.rawSubscription()
            getEndpointSuccess, endpoint = rawSubscription.APIEndpoint()
            if not getEndpointSuccess:
                return False, endpoint
            invitedByUser = (
                self.invitedByUserKey or self.invitedByAPIEndpointKey.get(read_consistency=ndb.STRONG).userKey
            ).get(read_consistency=ndb.STRONG)
            reason = "accepted"

            body = f"""\
Hi {invitedByUser.name} ({invitedByUser.email}),

the user {user.name} ({user.email}) who you have invited to share a font subscription has {reason} your invitation.
Here are the details:

"""

            success, message, desc, origin = rawSubscription.descriptionForEmail()
            if not success:
                return False, message
            body += desc
            body += definitions.EMAILFOOTER

            # Send email
            success, message = helpers.email(
                "Type.World Subscriptions <subscriptions@mail.type.world>",
                [invitedByUser.email],
                f"Type.World App: Invitation {reason}",
                body,
                replyTo=user.email,
            )
            if not success:
                return False, f"Email: {message}"

        return True, None

    def sendDeletedEmail(self):

        # Send Email
        if self.confirmed is True:
            reason = "removed"
        else:
            reason = "declined"

        return self.sendDeclinedEmail(reason)

    def sendDeclinedEmail(self, reason):

        user = self.key.parent().get(read_consistency=ndb.STRONG)

        if user.email not in definitions.KNOWNEMAILADDRESSES and (
            self.invitedByUserKey or self.invitedByAPIEndpointKey
        ):
            rawSubscription = self.rawSubscription()
            getEndpointSuccess, endpoint = rawSubscription.APIEndpoint()
            if not getEndpointSuccess:
                return False, endpoint
            invitedByUser = (
                self.invitedByUserKey or self.invitedByAPIEndpointKey.get(read_consistency=ndb.STRONG).userKey
            ).get(read_consistency=ndb.STRONG)

            body = f"""\
Hi {invitedByUser.name} ({invitedByUser.email}),

the user {user.name} ({user.email}) who you have invited to share a font subscription has {reason} your invitation.
Here are the details:

"""

            success, message, desc, origin = rawSubscription.descriptionForEmail()
            if not success:
                return False, message
            body += desc
            body += definitions.EMAILFOOTER

            # Send email
            success, message = helpers.email(
                "Type.World Subscriptions <subscriptions@mail.type.world>",
                [invitedByUser.email],
                f"Type.World App: Invitation {reason}",
                body,
                replyTo=user.email,
            )
            if not success:
                return False, f"Email: {message}"

        return True, None

    def sendRevokedEmail(self):

        reason = "revoked"
        user = self.key.parent().get(read_consistency=ndb.STRONG)

        if user.email not in definitions.KNOWNEMAILADDRESSES:
            rawSubscription = self.rawSubscription()
            getEndpointSuccess, endpoint = rawSubscription.APIEndpoint()
            if not getEndpointSuccess:
                return False, endpoint
            invitedByUser = (
                self.invitedByUserKey or self.invitedByAPIEndpointKey.get(read_consistency=ndb.STRONG).userKey
            ).get(read_consistency=ndb.STRONG)

            body = f"Hi {user.name} ({user.email}),\n\n"

            if (
                self.invitationRevokedByUserKey == self.invitedByUserKey
                or self.invitationRevokedByAPIEndpointKey == self.invitedByAPIEndpointKey
            ):

                body += (
                    f"the user {invitedByUser.name} ({invitedByUser.email}) who has invited you share a font"
                    f" subscription has {reason} your invitation.\n"
                )

            else:

                body += (
                    "the original inviter to the subscription to which you’ve been invited by"
                    f" {invitedByUser.name} ({invitedByUser.email}) has revoked the invitation.\nSubsequently, your"
                    " invitation to this subscription has also been revoked.\n"
                )

            body += "Here are the details:\n\n"

            success, message, desc, origin = rawSubscription.descriptionForEmail()
            if not success:
                return False, message
            body += desc
            body += definitions.EMAILFOOTER

            # Send email
            success, message = helpers.email(
                "Type.World Subscriptions <subscriptions@mail.type.world>",
                [user.email],
                f"Type.World App: Invitation {reason}",
                body,
                replyTo=invitedByUser.email,
            )
            if not success:
                return False, f"Send email: {message}"

        return True, None


class Session(TWNDBModel):
    userKey = web.KeyProperty(required=True)

    def getUser(self):
        if self.userKey:
            return self.userKey.get(read_consistency=ndb.STRONG)


class AppTraceback(TWNDBModel):
    payload = web.StringProperty(required=True)
    supplementary = web.BlobProperty()
    fixed = web.BooleanProperty(default=False)


class Preference(TWNDBModel):
    name = web.StringProperty(required=True)
    content = web.TextProperty()


class SystemStatistics(TWNDBModel):
    jsonStats = web.JsonProperty()

    def bump(self, keys, addition=0, equals=None):

        assert self.domain

        jsonStats = self.jsonStats
        if jsonStats is None:
            jsonStats = {}
        if type(jsonStats) != dict:
            jsonStats = {}

        if type(self.domain) == str:
            keys.insert(0, self.domain)
        elif type(self.domain) in (list, tuple):
            for key in sorted(self.domain, reverse=True):
                keys.insert(0, key)

        stats = jsonStats
        for i, key in enumerate(keys):
            if type(key) in (list, tuple):
                key = key[0]

            if i < len(keys) - 1:
                if key not in stats:
                    stats[key] = {}
            else:
                if key not in stats:
                    stats[key] = 0

                if addition:
                    stats[key] += addition
                elif equals:
                    stats[key] = equals
            stats = stats[key]
        self.jsonStats = jsonStats

    def setDomain(self, args):
        self.domain = args


class SignInApp(TWNDBModel):

    # User editable
    name = web.StringProperty(required=True, verbose_name="Application/Website Name")
    websiteURL = web.HTTPURLProperty(required=True, verbose_name="Website URL")
    logoURL = web.HTTPURLProperty(required=True, verbose_name="Logo URL")
    redirectURLs = web.TextProperty(required=True, verbose_name="Redirect URLs (one per line)")
    oauthScopes = web.ChoicesProperty(choices=definitions.SIGNINSCOPES, verbose_name="OAuth Scopes")

    # Internal
    userKey = web.KeyProperty(required=True)
    clientID = web.StringProperty(required=True)
    clientSecret = web.StringProperty(required=True)
    lastState = web.StringProperty()

    def oauthScopesList(self):
        return sorted(self.oauthScopes)

    def beforePut(self):
        if not self.clientID:
            self.clientID = helpers.Garbage(40)
        if not self.clientSecret:
            self.clientSecret = helpers.Garbage(40)

    def viewPermission(self, methodName):
        if methodName in ["overview"] and self.userKey == g.user.key:
            return True
        return False

    def editPermission(self, propertyNames=[]):
        allowed = ["name", "websiteURL", "logoURL", "redirectURLs", "userKey", "oauthScopes"]
        return (
            (propertyNames and set(allowed) & set(propertyNames)) or not propertyNames
        ) and g.user.key == self.userKey

    def deletePermission(self):
        return g.user.key == self.userKey

    def overview(self, parameters={}, directCallParameters={}):
        g.html.TABLE()
        g.html.TR()
        g.html.TD(style="text-align: left;")
        # g.html.DIV()
        g.html.P()
        g.html.B()
        g.html.T(self.name)
        g.html._B()
        g.html._P()
        g.html.P()
        g.html.T(f"Client ID: <code>{self.clientID}</code>")
        g.html.BR()
        g.html.T(f"Client Secret: <code>{self.clientSecret}</code>")
        g.html.BR()
        g.html.T(f"OAuth Scopes: <code>{','.join(self.oauthScopesList())}</code>")
        g.html._P()
        g.html.P()
        redirectURL = "__YOUR_URL__"
        if self.redirectURLs:
            redirectURL = [x for x in self.redirectURLs.splitlines() if x][0]
        g.html.T(
            'Example of Sign-In URL (replace <span style="color: red;">red</span> with your actual values):'
            " <pre>https://type.world/signin<br />"
            f"?client_id={self.clientID}<br />"
            "&response_type=code<br />"
            f'&redirect_uri=<span style="color: red;">{urllib.parse.quote_plus(redirectURL)}</span><br />'
            f'&scope={",".join(self.oauthScopesList())}<br />'
            '&state=<span style="color: red;">__YOUR_STATE__</span></pre>'
        )
        g.html._P()
        # g.html._DIV()
        g.html._TD()
        g.html.TD(style="width: 20%;")
        self.edit(propertyNames=["name", "websiteURL", "logoURL", "redirectURLs", "oauthScopes"])
        self.delete(text='<span class="material-icons-outlined">delete</span>')
        g.html._TD()
        g.html._TR()
        g.html._TABLE()

    def billNonCumulativeMetrics(self):

        # Stripe subscription
        user = self.userKey.get()
        stripeSubscription = user.stripeSubscriptionByProductID("world.type.signin_service_plan")
        if not stripeSubscription:
            return False, "SignInApp.billNonCumulativeMetrics():unknownStripeSubscription"
        assert stripeSubscription["current_period_start"], "No invoice period start value available"

        basic = 0
        extended = 0

        # Tokens
        tokens = OAuthToken.query(
            OAuthToken.signinAppKey == self.key,
            OAuthToken.lastAccess >= datetime.datetime.fromtimestamp(stripeSubscription["current_period_start"]),
        ).fetch(read_consistency=ndb.STRONG)
        for token in tokens:
            if token.oauthScopes == "account":
                basic += 1
            else:
                extended += 1

        success, message = user.bill("world.type.signin_service_plan", "typeworldsignins_basic", quantity=basic)
        print(success, message)

        success, message = user.bill("world.type.signin_service_plan", "typeworldsignins_extended", quantity=extended)
        print(success, message)

        return True, None


class OAuthToken(TWNDBModel):
    userKey = web.KeyProperty(required=True)
    signinAppKey = web.KeyProperty(required=True)
    oauthScopes = web.StringProperty(required=True)

    code = web.StringProperty()  # One-time code to be returned
    editCode = web.StringProperty()
    revoked = web.BooleanProperty(default=False)
    authToken = web.StringProperty()
    lastAccess = web.DateTimeProperty()

    def getApp(self):
        return self.signinAppKey.get()
