# project
import main
import definitions

# other
import sys
import os
import datetime
import typeworld.client
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))


def now():
    return datetime.datetime.now()


def unsecretURL(url):
    # URL without secret key

    (
        customProtocol,
        protocol,
        transportProtocol,
        subscriptionID,
        secretKey,
        domain,
    ) = typeworld.client.splitJSONURL(url)
    if subscriptionID and secretKey:
        return (
            customProtocol
            + protocol
            + "+"
            + transportProtocol.replace("://", "//")
            + subscriptionID
            + ":"
            + "secretKey"
            + "@"
            + domain
        )
    elif subscriptionID and not secretKey:
        return (
            customProtocol
            + protocol
            + "+"
            + transportProtocol.replace("://", "//")
            + subscriptionID
            + "@"
            + domain
        )
    else:
        return (
            customProtocol
            + protocol
            + "+"
            + transportProtocol.replace("://", "//")
            + domain
        )


def email(from_, to, subject, body, replyTo=None):

    assert type(from_) == str
    assert type(to) in (list, tuple)
    assert type(subject) == str
    assert type(body) == str
    if replyTo:
        assert type(replyTo) == str

    url = "%s/messages" % definitions.MAILGUNACCESSPOINT
    parameters = {
        "from": from_,
        "to": to,
        "subject": subject,
        "text": body,
    }
    if replyTo:
        parameters["h:Reply-To"] = replyTo

    auth = ("api", main.secret("MAILGUN_PRIVATEKEY"))
    response = requests.post(
        url, data=parameters, auth=requests.auth.HTTPBasicAuth(*auth)
    )
    if response.status_code != 200:
        return False, f"HTTP Error {response.status_code}"

    # logging.warning(f"Sent email ({subject}) to {to}, request status: {response.status_code}")

    return True, None


def Garbage(length, uppercase=True, lowercase=True, numbers=True, punctuation=False):
    """\
    Return string containing garbage.
    """

    import random

    uppercaseparts = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    lowercaseparts = "abcdefghijklmnopqrstuvwxyz"
    numberparts = "0123456789"
    punctuationparts = ".-_"

    pool = ""
    if uppercase:
        pool += uppercaseparts
    if lowercase:
        pool += lowercaseparts
    if numbers:
        pool += numberparts
    if punctuation:
        pool += punctuationparts

    if not pool:
        pool = lowercaseparts

    garbage = ""

    while len(garbage) < length:
        garbage += random.choice(pool)

    return garbage


def addAttributeToURL(url, attributes):

    from urllib.parse import urlparse

    o = urlparse(url)

    for attribute in attributes.split("&"):

        key, value = attribute.split("=")

        replaced = False
        queryParts = o.query.split("&")
        if queryParts:
            for i, query in enumerate(queryParts):
                if "=" in query and query.startswith(key + "="):
                    queryParts[i] = attribute
                    replaced = True
                    break
        if not replaced:
            if queryParts[0]:
                queryParts.append(attribute)
            else:
                queryParts[0] = attribute
        o = o._replace(query="&".join(queryParts))

    return o.geturl()
