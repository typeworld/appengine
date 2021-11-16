# project
import typeworldserver
from typeworldserver import classes

# other
import stripe
import traceback
import json
import time
from flask import abort, jsonify, request, g
from google.cloud import ndb

typeworldserver.app.config["modules"].append("billing_stripe")


# Set your secret key. Remember to switch to your live secret key in production!
# See your keys here: https://dashboard.stripe.com/account/apikeys

# LIVE
if typeworldserver.STRIPELIVE:
    stripePrivateKey = typeworldserver.secret("STRIPE_PRIVATEKEY_LIVE")
    stripePublicKey = typeworldserver.secret("STRIPE_PUBLICKEY_LIVE")
    stripeProducts = {
        "world.type.professional_publisher_plan": {
            "ID": "prod_Ix1l3V2SyfLIT4",
            "name": "Font Publishing Through Type.World",
            "prices": [
                {
                    "id": "price_1IlCzHLUOp6Nnz1oCvGD8bt2",
                    "tw_id": "subscriptionUpdateWithAddedFonts",
                    "name": "Subscription Update (First Appearance or Added Fonts)",
                },
                {
                    "id": "price_1IlD1SLUOp6Nnz1or9EPr1iY",
                    "tw_id": "subscriptionUpdateWithAddedFontVersions",
                    "name": "Subscription Update (Added Font Versions)",
                },
                {
                    "id": "price_1IlD2oLUOp6Nnz1ogWqmwljU",
                    "tw_id": "users",
                    "name": "Active Users",
                },
            ],
            "description": (
                "Professional Type.World font subscription handling as per <a"
                " href='/developer/prices'>price list</a>. Billed monthly per usage."
                " Billing starts after %%trial_period_days%% days of free trial. You"
                " may pause the plan at any time to resume later."
            ),
            "trial_period_days": 180,
            "cancelWarning": "Are you sure? Since this is a metered plan, service will be terminated immediately.",
            "cancelTime": "immediately",  # endOfBillingPeriod/immediately
            "type": "metered",
            "allowTestUsers": True,
        },
        "world.type.signin_service_plan": {
            "ID": "prod_KbHcDcTYOYYmRS",
            "name": "Type.World Sign-In Service",
            "prices": [
                {
                    "id": "price_1Jw533LUOp6Nnz1oTrmsGA9A",
                    "tw_id": "signins",
                    "name": "Sign-Ins",
                },
            ],
            "description": (
                "Offer Type.World user accounts to the users of your app/website as a sign-in service, as per <a"
                " href='/developer/prices'>price list</a>. Billed monthly per usage."
                " Billing starts after %%trial_period_days%% days of free trial. You"
                " may pause the plan at any time to resume later."
            ),
            "trial_period_days": 180,
            "cancelWarning": "Are you sure? Since this is a metered plan, service will be terminated immediately.",
            "cancelTime": "immediately",  # endOfBillingPeriod/immediately
            "type": "metered",
            "allowTestUsers": False,
        },
        "world.type.professional_user_plan": {
            "ID": "prod_J7tRVmx5BDoocH",
            "name": "Professional User Plan",
            "prices": [
                {"id": "price_1IVdenLUOp6Nnz1oBeeKFaGu"},
            ],
            "description": "12€/year, billed yearly. Billing starts after %%trial_period_days%% days of free trial.",
            "trial_period_days": 30,
            "cancelWarning": (
                "Are you sure? (Your subscription will remain active until the end of the current billing period.)"
            ),
            "cancelTime": "endOfBillingPeriod",  # endOfBillingPeriod/immediately
            "type": "fixed",
            "allowTestUsers": True,
        },
    }
    stripeTaxRecord = "txr_1IL88pLUOp6Nnz1o92HkWpAN"
    webhook_secret = "whsec_GxJLluqc6JwGSNbcfmrb4kQkTDMKTrS2"


# TEST
else:
    stripePrivateKey = typeworldserver.secret("STRIPE_PRIVATEKEY_TEST")
    stripePublicKey = typeworldserver.secret("STRIPE_PUBLICKEY_TEST")
    stripeProducts = {
        "world.type.professional_publisher_plan": {
            "ID": "prod_Iv7lZ5O5Jw9OO5",
            "name": "Professional Publisher Plan",
            "prices": [
                {
                    "id": "price_1IVGfWLUOp6Nnz1oQ5nr2ZI5",
                    "tw_id": "subscriptionUpdateWithAddedFonts",
                    "name": "Subscription Update (First Appearance or Added Fonts)",
                },
                {
                    "id": "price_1IVGfWLUOp6Nnz1oG5HUXMev",
                    "tw_id": "subscriptionUpdateWithAddedFontVersions",
                    "name": "Subscription Update (Added Font Versions)",
                },
                {
                    "id": "price_1IVGfWLUOp6Nnz1o6Ms7OzOM",
                    "tw_id": "users",
                    "name": "Active Users",
                },
            ],
            "description": (
                "Professional Type.World font subscription handling as per <a"
                " href='/developer/prices'>price list</a>. Billed monthly per usage."
                " Billing starts after %%trial_period_days%% days of free trial. You"
                " may pause the plan at any time to resume later."
            ),
            "trial_period_days": 180,
            "cancelWarning": "Are you sure? Since this is a metered plan, service will be terminated immediately.",
            "cancelTime": "immediately",  # endOfBillingPeriod/immediately
            "type": "metered",
        },
        "world.type.professional_user_plan": {
            "ID": "prod_J6pDlPqJEbPrww",
            "name": "Professional User Plan",
            "prices": [
                {"id": "price_1IUbZ8LUOp6Nnz1oURqGvI9N"},
            ],
            "description": "12€/year, billed yearly. Billing starts after %%trial_period_days%% days of free trial.",
            "trial_period_days": 30,
            "cancelWarning": (
                "Are you sure? (Your subscription will remain active until the end of the current billing period.)"
            ),
            "cancelTime": "endOfBillingPeriod",  # endOfBillingPeriod/immediately
            "type": "fixed",
        },
    }
    stripeTaxRecord = "txr_1IVGjCLUOp6Nnz1opfuAdafU"
    webhook_secret = "whsec_nsyHZx3EO65uVT68R9TbOkYGqWxA2eDa"

stripe.api_key = stripePrivateKey


#
#
#
#
#
#
#
#
#
#
# STRIPE ELEMENTS
#
#
#
#
#
#
#
#
#
#


@typeworldserver.app.route("/stripe-config", methods=["POST"])
def get_config():
    if not g.user:
        return abort(403)
    data = json.loads(request.data)

    clientSecret = None

    if data["paymentMethod"] == "iban":
        setupIntent = stripe.SetupIntent.create(
            customer=g.user.stripeGetCustomerId(),
            payment_method_types=["sepa_debit"],
            usage="off_session",
        )
        clientSecret = setupIntent.client_secret

    return jsonify(
        publishableKey=stripePublicKey,
        customerCountry=g.user.invoiceCountry,
        customerEmail=g.user.email,
        clientSecret=clientSecret,
    )


@typeworldserver.app.route("/create-subscription", methods=["POST"])
def createSubscription():
    if not g.user:
        return abort(403)
    data = json.loads(request.data)
    print(f"createSubscription({data})")
    try:

        # New payment method
        if not g.user.stripePaymentMethod() and "paymentMethodId" not in data:
            print("Missing paymentMethodId")
            return jsonify(error={"message": "Missing paymentMethodId"}), 200

        if not g.user.stripePaymentMethod() and "paymentMethodId" in data and data["paymentMethodId"]:

            stripe.PaymentMethod.attach(
                data["paymentMethodId"],
                customer=g.user.stripeGetCustomerId(),
            )
            # Set the default payment method on the customer
            stripe.Customer.modify(
                g.user.stripeGetCustomerId(),
                invoice_settings={
                    "default_payment_method": data["paymentMethodId"],
                },
            )

        # New subscription
        if not data["productId"] in stripeProducts:
            print("No known productId given")
            return jsonify(error={"message": "No known productId given"}), 200
        items = []
        for price in stripeProducts[data["productId"]]["prices"]:
            items.append({"price": price["id"]})
        print("items", items)

        trial_period_days = max(
            0,
            stripeProducts[data["productId"]]["trial_period_days"]
            - g.user.stripeSubscriptionPreviousRunningPeriodDays(data["productId"]),
        )
        if g.user.email == "test@type.world":
            trial_period_days = 1
        print("trial_period_days", trial_period_days)

        # Create the subscription
        subscription = stripe.Subscription.create(
            customer=g.user.stripeGetCustomerId(),
            items=items,
            default_tax_rates=[stripeTaxRecord],
            expand=["latest_invoice.payment_intent", "pending_setup_intent"],
            # payment_behavior="allow_incomplete",
            trial_period_days=trial_period_days,
        )

        g.user.stripeUpdateSubscriptions()

        print("about to return")
        return jsonify(subscription)
    except Exception:
        return jsonify(error={"message": traceback.format_exc()}), 200


@typeworldserver.app.route("/update-payment-method", methods=["POST"])
def updatePaymentMethod():
    if not g.user:
        return abort(403)
    data = json.loads(request.data)
    print(f"updatePaymentMethod({data})")
    try:

        stripeCustomer = stripe.Customer.retrieve(g.user.stripeGetCustomerId())

        # Detach default payment method
        if stripeCustomer.invoice_settings and stripeCustomer.invoice_settings.default_payment_method:
            stripe.PaymentMethod.detach(stripeCustomer.invoice_settings.default_payment_method)
            print("detached default payment method")

        stripe.PaymentMethod.attach(
            data["paymentMethodId"],
            customer=g.user.stripeGetCustomerId(),
        )

        # Set the default payment method on the customer
        stripe.Customer.modify(
            g.user.stripeGetCustomerId(),
            invoice_settings={
                "default_payment_method": data["paymentMethodId"],
            },
        )

        if typeworldserver.STRIPELIVE:
            subscription = g.user.stripeSubscriptions[0]
        else:
            subscription = g.user.stripeTestSubscriptions[0]

        return jsonify(subscription)
    except Exception as e:
        return jsonify(error={"message": str(e)}), 200


def deleteSubscription(user, stripeSubscription, productId):
    if typeworldserver.STRIPELIVE:
        stripeSubscribedProductsHistory = dict(user.stripeSubscribedProductsHistory)
    else:
        stripeSubscribedProductsHistory = dict(user.stripeTestSubscribedProductsHistory)

    if productId not in stripeSubscribedProductsHistory:
        stripeSubscribedProductsHistory[productId] = []
    stripeSubscribedProductsHistory[productId].append(
        {
            "cancelled_on": int(time.time()),
            "running_period": int(time.time()) - stripeSubscription.created,
        }
    )
    if typeworldserver.STRIPELIVE:
        user.stripeSubscribedProductsHistory = stripeSubscribedProductsHistory
    else:
        user.stripeTestSubscribedProductsHistory = stripeSubscribedProductsHistory
    user.putnow()

    return True, None


@typeworldserver.app.route("/cancel-subscription", methods=["POST"])
def cancelSubscription():
    if not g.user:
        return abort(403)
    data = json.loads(request.data)
    print(f"cancelSubscription({data})")
    try:

        id = g.user.stripeSubscriptionByProductID(data["productId"])["id"]
        if id:

            # Cancel the subscription by deleting it
            deletedSubscription = stripe.Subscription.delete(id, invoice_now=True)
            deleteSubscription(g.user, deletedSubscription, data["productId"])

            g.user.stripeUpdateSubscriptions()

            return jsonify(deletedSubscription)
        else:
            return jsonify(error="Subscription doesn't exist"), 403

    except Exception as e:
        print(traceback.format_exc())
        return jsonify(error=str(e)), 403


@typeworldserver.app.route("/stripe-webhook", methods=["POST"])
def webhook_received():

    # You can use webhooks to receive information about asynchronous payment events.
    # For more about our webhook events check out https://stripe.com/docs/webhooks.
    request_data = json.loads(request.data)

    if webhook_secret:
        # Retrieve the event by verifying the signature using the raw body and secret
        # if webhook signing is configured.
        signature = request.headers.get("stripe-signature")
        try:
            event = stripe.Webhook.construct_event(payload=request.data, sig_header=signature, secret=webhook_secret)
            data = event["data"]
        except Exception as e:
            return e
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event["type"]
    else:
        data = request_data["data"]
        event_type = request_data["type"]

    data_object = data["object"]

    if event_type == "customer.updated":

        if data_object["livemode"]:
            user = classes.User.query(classes.User.stripeCustomerId == data_object["id"]).get(
                read_consistency=ndb.STRONG
            )
        else:
            user = classes.User.query(classes.User.stripeTestCustomerId == data_object["id"]).get(
                read_consistency=ndb.STRONG
            )

        print(data_object)

        if user:
            if "address" in data_object:
                if "line1" in data_object["address"] and data_object["address"]["line1"] != user.invoiceStreet:
                    user.invoiceStreet = data_object["address"]["line1"]
                    print("Adjusted", "line1")
                if "line2" in data_object["address"] and data_object["address"]["line2"] != user.invoiceStreet2:
                    user.invoiceStreet2 = data_object["address"]["line2"]
                    print("Adjusted", "line2")
                if (
                    "postal_code" in data_object["address"]
                    and data_object["address"]["postal_code"] != user.invoiceZIPCode
                ):
                    user.invoiceZIPCode = data_object["address"]["postal_code"]
                    print("Adjusted", "postal_code")
                if "city" in data_object["address"] and data_object["address"]["city"] != user.invoiceCity:
                    user.invoiceCity = data_object["address"]["city"]
                    print("Adjusted", "city")
                if "state" in data_object["address"] and data_object["address"]["state"] != user.invoiceState:
                    user.invoiceState = data_object["address"]["state"]
                    print("Adjusted", "state")
                if "country" in data_object["address"] and data_object["address"]["country"] != user.invoiceCountry:
                    user.invoiceCountry = data_object["address"]["country"]
                    print("Adjusted", "country")
                user.put()

    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.deleted",
        "customer.subscription.updated",
    ):
        print(event_type)

        if data_object["livemode"]:
            user = classes.User.query(classes.User.stripeCustomerId == data_object["customer"]).get(
                read_consistency=ndb.STRONG
            )
        else:
            user = classes.User.query(classes.User.stripeTestCustomerId == data_object["customer"]).get(
                read_consistency=ndb.STRONG
            )

        user.stripeUpdateSubscriptions()

    # elif event_type == 'customer.tax_id.created':

    #     if data_object["livemode"]:
    #         user = classes.User.query(classes.User.stripeCustomerId==
    # data_object["customer"]).get(read_consistency=ndb.STRONG)
    #     else:
    #         user = classes.User.query(classes.User.stripeTestCustomerId==
    # data_object["customer"]).get(read_consistency=ndb.STRONG)

    #     if user:
    #         if data_object["type"] == "eu_vat" and data_object["value"]:
    #             user.invoiceEUVATID = data_object["value"]
    #             user.put()

    # elif event_type == 'customer.tax_id.updated':

    #     print(event_type, data_object)

    #     if data_object["livemode"]:
    #         user = classes.User.query(classes.User.stripeCustomerId==
    # data_object["customer"]).get(read_consistency=ndb.STRONG)
    #     else:
    #         user = classes.User.query(classes.User.stripeTestCustomerId==
    # data_object["customer"]).get(read_consistency=ndb.STRONG)

    #     if user:
    #         if data_object["type"] == "eu_vat" and data_object["value"]:
    #             user.invoiceEUVATID = data_object["value"]
    #             user.put()

    # elif event_type == 'customer.tax_id.deleted':

    #     if data_object["livemode"]:
    #         user = classes.User.query(classes.User.stripeCustomerId==
    # data_object["customer"]).get(read_consistency=ndb.STRONG)
    #     else:
    #         user = classes.User.query(classes.User.stripeTestCustomerId==
    # data_object["customer"]).get(read_consistency=ndb.STRONG)

    #     if user:
    #         if data_object["type"] == "eu_vat" and data_object["value"]:
    #             user.invoiceEUVATID = None
    #             user.put()

    elif event_type == "invoice.paid":
        # Used to provision services after the trial has ended.
        # The status of the invoice will show up as paid. Store the status in your
        # database to reference when a user accesses your service to avoid hitting rate
        # limits.
        print(event_type)

    elif event_type == "invoice.payment_failed":
        # If the payment fails or the customer does not have a valid payment method,
        # an invoice.payment_failed event is sent, the subscription becomes past_due.
        # Use this webhook to notify your user that their payment has
        # failed and to retrieve new card details.
        print(event_type)

    elif event_type == "invoice.finalized":
        # If you want to manually send out invoices to your customers
        # or store them locally to reference to avoid hitting Stripe rate limits.
        print(event_type)

    elif event_type == "customer.subscription.created":
        print(event_type)

    elif event_type == "customer.subscription.trial_will_end":
        # Send notification to your user that the trial will end
        print(event_type)

    else:
        print(event_type)

    return jsonify({"status": "success"})
