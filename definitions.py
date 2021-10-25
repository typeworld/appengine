import collections


DOMAIN = "mail.type.world"
MAILGUNACCESSPOINT = "https://api.mailgun.net/v3/%s" % DOMAIN
DOWNLOADSURL = "downloads.type.world"

KNOWNEMAILADDRESSES = [
    "test@type.world",
    "test1@type.world",
    "test2@type.world",
    "test3@type.world",
]

AMOUNTTESTUSERSFORAPIENTPOINT = 10

EMAILFOOTER = """\


--

Welcome to Type.World, the one-click font installer.
https://type.world

Download the app here:
https://type.world/app/
"""

COUNTRIES_PLAIN = """\
AD	Andorra
AE	United Arab Emirates
AF	Afghanistan
AG	Antigua and Barbuda
AI	Anguilla
AL	Albania
AM	Armenia
AO	Angola
AQ	Antarctica
AR	Argentina
AS	American Samoa
AT	Austria
AU	Australia
AW	Aruba
AX	Åland Islands
AZ	Azerbaijan
BA	Bosnia and Herzegovina
BB	Barbados
BD	Bangladesh
BE	Belgium
BF	Burkina Faso
BG	Bulgaria
BH	Bahrain
BI	Burundi
BJ	Benin
BL	Saint Barthélemy
BM	Bermuda
BN	Brunei Darussalam
BO	Bolivia, Plurinational State of
BQ	Bonaire, Sint Eustatius and Saba
BR	Brazil
BS	Bahamas
BT	Bhutan
BV	Bouvet Island
BW	Botswana
BY	Belarus
BZ	Belize
CA	Canada
CC	Cocos (Keeling) Islands
CD	Congo, the Democratic Republic of the
CF	Central African Republic
CG	Congo
CH	Switzerland
CI	Côte d’Ivoire
CK	Cook Islands
CL	Chile
CM	Cameroon
CN	China
CO	Colombia
CR	Costa Rica
CU	Cuba
CV	Cape Verde
CW	Curaçao
CX	Christmas Island
CY	Cyprus
CZ	Czech Republic
DE	Germany
DJ	Djibouti
DK	Denmark
DM	Dominica
DO	Dominican Republic
DZ	Algeria
EC	Ecuador
EE	Estonia
EG	Egypt
EH	Western Sahara
ER	Eritrea
ES	Spain
ET	Ethiopia
FI	Finland
FJ	Fiji
FK	Falkland Islands (Malvinas)
FM	Micronesia, Federated States of
FO	Faroe Islands
FR	France
GA	Gabon
UK	United Kingdom
GD	Grenada
GE	Georgia
GF	French Guiana
GG	Guernsey
GH	Ghana
GI	Gibraltar
GL	Greenland
GM	Gambia
GN	Guinea
GP	Guadeloupe
GQ	Equatorial Guinea
GR	Greece
GS	South Georgia and the South Sandwich Islands
GT	Guatemala
GU	Guam
GW	Guinea-Bissau
GY	Guyana
HK	Hong Kong
HM	Heard Island and McDonald Islands
HN	Honduras
HR	Croatia
HT	Haiti
HU	Hungary
ID	Indonesia
IE	Ireland
IL	Israel
IM	Isle of Man
IN	India
IO	British Indian Ocean Territory
IQ	Iraq
IR	Iran, Islamic Republic of
IS	Iceland
IT	Italy
JE	Jersey
JM	Jamaica
JO	Jordan
JP	Japan
KE	Kenya
KG	Kyrgyzstan
KH	Cambodia
KI	Kiribati
KM	Comoros
KN	Saint Kitts and Nevis
KP	Korea, Democratic People’s Republic of
KR	Korea, Republic of
KW	Kuwait
KY	Cayman Islands
KZ	Kazakhstan
LA	Lao People’s Democratic Republic
LB	Lebanon
LC	Saint Lucia
LI	Liechtenstein
LK	Sri Lanka
LR	Liberia
LS	Lesotho
LT	Lithuania
LU	Luxembourg
LV	Latvia
LY	Libya
MA	Morocco
MC	Monaco
MD	Moldova, Republic of
ME	Montenegro
MF	Saint Martin (French part)
MG	Madagascar
MH	Marshall Islands
MK	Macedonia, the former Yugoslav Republic of
ML	Mali
MM	Myanmar
MN	Mongolia
MO	Macao
MP	Northern Mariana Islands
MQ	Martinique
MR	Mauritania
MS	Montserrat
MT	Malta
MU	Mauritius
MV	Maldives
MW	Malawi
MX	Mexico
MY	Malaysia
MZ	Mozambique
NA	Namibia
NC	New Caledonia
NE	Niger
NF	Norfolk Island
NG	Nigeria
NI	Nicaragua
NL	Netherlands
NO	Norway
NP	Nepal
NR	Nauru
NU	Niue
NZ	New Zealand
OM	Oman
PA	Panama
PE	Peru
PF	French Polynesia
PG	Papua New Guinea
PH	Philippines
PK	Pakistan
PL	Poland
PM	Saint Pierre and Miquelon
PN	Pitcairn
PR	Puerto Rico
PS	Palestine
PT	Portugal
PW	Palau
PY	Paraguay
QA	Qatar
RE	Réunion
RO	Romania
RS	Serbia
RU	Russian Federation
RW	Rwanda
SA	Saudi Arabia
SB	Solomon Islands
SC	Seychelles
SD	Sudan
SE	Sweden
SG	Singapore
SH	Saint Helena, Ascension and Tristan da Cunha
SI	Slovenia
SJ	Svalbard and Jan Mayen
SK	Slovakia
SL	Sierra Leone
SM	San Marino
SN	Senegal
SO	Somalia
SR	Suriname
SS	South Sudan
ST	Sao Tome and Principe
SV	El Salvador
SX	Sint Maarten (Dutch part)
SY	Syrian Arab Republic
SZ	Swaziland
TC	Turks and Caicos Islands
TD	Chad
TF	French Southern Territories
TG	Togo
TH	Thailand
TJ	Tajikistan
TK	Tokelau
TL	Timor-Leste
TM	Turkmenistan
TN	Tunisia
TO	Tonga
TR	Turkey
TT	Trinidad and Tobago
TV	Tuvalu
TW	Taiwan, Province of China
TZ	Tanzania, United Republic of
UA	Ukraine
UG	Uganda
UM	United States Minor Outlying Islands
US	United States
UY	Uruguay
UZ	Uzbekistan
VA	Holy See (Vatican City State)
VC	Saint Vincent and the Grenadines
VE	Venezuela, Bolivarian Republic of
VG	Virgin Islands, British
VI	Virgin Islands, U.S.
VN	Viet Nam
VU	Vanuatu
WF	Wallis and Futuna
WS	Samoa
YE	Yemen
YT	Mayotte
ZA	South Africa
ZM	Zambia
ZW	Zimbabwe
"""

EU_COUNTRIES = [
    "AT",
    "BE",
    "BG",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    # "UK",
    "GR",
    "HR",
    "HU",
    "IE",
    "IM",
    "IT",
    "LT",
    "LU",
    "LV",
    "MT",
    "NL",
    "PL",
    "PT",
]


COUNTRIES = []
COUNTRIES_DICT = {}
for line in COUNTRIES_PLAIN.splitlines():
    line = line.strip()
    code, name = line.split("\t")
    COUNTRIES.append((code, name))
    COUNTRIES_DICT[code] = name
COUNTRIES = sorted(COUNTRIES, key=lambda country: country[1])

APICOMMANDS = collections.OrderedDict()

APICOMMANDS["validateAPIEndpoint"] = {
    "public": False,
    "description": (
        "Remotely validate your Type.World API endpoint to build error messages right into your own backend."
    ),
    "parameters": collections.OrderedDict(
        {
            "subscriptionURL": {
                "description": "Complete subscription URL with protocols.",
                "required": True,
            },
            "profiles": {
                "description": (
                    "Comma-separated list of profile keywords. See"
                    " [https://type.world/developer/validate](/developer/validate) for a complete list."
                ),
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "failure": (
                "Validation failed. Please see the additional data fields `information`, `warnings`, `errors`, and"
                " especially `stages` for details on the process."
            ),
        }
    ),
    "additionalReturn": collections.OrderedDict(
        {
            "information": "A list of non-critical information.",
            "warnings": "A list of warnings that you must pay attention to.",
            "errors": "A list of critical errors that must be fixed.",
            "stages": "Dictionary of test stages with detailed descriptions, results, and comments.",
        }
    ),
    "exampleParameters": collections.OrderedDict(
        {
            "subscriptionURL": (
                "typeworld://json+https//subscriptionID:secretKey@awesomefonts.com/typeworldapi/daz4Ub54mut2XDLz6vGx"
            ),
        }
    ),
    "exampleResponse": collections.OrderedDict(
        {
            "response": "failure",
            "errors": ["Invalid subscription URL"],
            "information": [],
            "warnings": ["Your API Endpoint does not use SSL (https://)."],
            "stages": ["Test stage details here."],
        }
    ),
}

APICOMMANDS["registerAPIEndpoint"] = {
    "public": False,
    "description": "The app calls this command when an endpoint is being accessed, for internal use.",
    "parameters": collections.OrderedDict(
        {
            "url": {
                "description": "API endpoint URL",
                "required": True,
            },
        }
    ),
    "return": None,
}

APICOMMANDS["linkTypeWorldUserAccount"] = {
    "public": False,
    "description": (
        "The app calls this command when a user links his/her user account to the app through the web site."
    ),
    "parameters": collections.OrderedDict(
        {
            "clientVersion": {
                "description": "Version number of client library",
                "required": True,
            },
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "User’s secret key",
                "required": True,
            },
            "anonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
            "machineModelIdentifier": {
                "description": "Machine model, machine readable",
                "required": False,
            },
            "machineHumanReadableName": {
                "description": "Machine model, human readable",
                "required": False,
            },
            "machineSpecsDescription": {
                "description": "Machine specs",
                "required": False,
            },
            "machineOSVersion": {
                "description": "Machine OS Version",
                "required": False,
            },
            "machineNodeName": {
                "description": "Machine node name",
                "required": False,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "userUnkown": "",
            "secretKeyInvalid": "",
            "linkingMoreAppInstancesRequiresProUserAccount": "",
        }
    ),
}

APICOMMANDS["unlinkTypeWorldUserAccount"] = {
    "public": False,
    "description": "The app calls this command when a user unlinks his/her user account from the app.",
    "parameters": collections.OrderedDict(
        {
            "clientVersion": {
                "description": "Version number of client library",
                "required": True,
            },
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "User’s secret key",
                "required": True,
            },
            "anonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
        }
    ),
    "userUnkown": "",
    "secretKeyInvalid": "",
    "appInstanceUnknown": "",
}

APICOMMANDS["syncUserSubscriptions"] = {
    "public": False,
    "description": "Update all the users subscriptions on the central database, return list",
    "parameters": collections.OrderedDict(
        {
            "clientVersion": {
                "description": "Version number of client library",
                "required": True,
            },
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "User’s secret key",
                "required": True,
            },
            "anonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
            "subscriptionURLs": {
                "description": "Comma-separated list of user subscription URLs",
                "required": True,
            },
        }
    ),
    "return": "Returns newly compiled complete list of subscriptions in dictionary under `subscriptions`",
}

APICOMMANDS["uploadUserSubscriptions"] = {
    "public": False,
    "description": (
        "Update all the users subscriptions on the central database, possibly delete subscription in the database"
    ),
    "parameters": collections.OrderedDict(
        {
            "clientVersion": {
                "description": "Version number of client library",
                "required": True,
            },
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "User’s secret key",
                "required": True,
            },
            "anonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
            "subscriptionURLs": {
                "description": "Comma-separated list of user subscription URLs",
                "required": True,
            },
        }
    ),
    "return": None,
}


APICOMMANDS["verifyCredentials"] = {
    "public": True,
    "description": (
        "Verify that a Type.World user account exists and that it is linked to a known app instance. In other words:"
        " Verify a valid user."
    ),
    "parameters": collections.OrderedDict(
        {
            "anonymousTypeWorldUserID": {
                "description": "Anonymous Type.World User ID",
                "required": True,
            },
            "anonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
            "APIKey": {
                "description": (
                    "Secret API Key for an API Endpoint, to be obtained through the Type.World user account"
                ),
                "required": True,
            },
            "subscriptionURL": {
                "description": (
                    "Complete subscription URL (Format C) that the user is trying to access. If this parameter is"
                    " given, the user must already hold the subscription for the verification to be valid. This"
                    ' conforms with "Security Level 2" of the developer documention.'
                ),
                "required": False,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "success": "This user and app are known and not revoked.",
            "invalid": (
                "The combination of anonymousAppID and anonymousTypeWorldUserID is either unkown or known and revoked."
            ),
            "unknownAnonymousTypeWorldUserID": "The user identified by unknownAnonymousTypeWorldUserID is unknown.",
            "unknownAPIKey": "The secret API Key for this API endpoint is unknown.",
        }
    ),
    "exampleParameters": collections.OrderedDict(
        {
            "anonymousTypeWorldUserID": "agp0eXBld29yQychELEgRVc2VyGIgPi9o4UJDA",
            "anonymousAppID": "ea4723c0-112e-11ea-9348-8c8590145181",
            "APIKey": "GBuzxMs32CgAIbofFp6c",
        }
    ),
}


APICOMMANDS["inviteUserToSubscription"] = {
    "public": True,
    "description": (
        "Invite an existing Type.World user (identified by his/her email address) to a subscription link. This is the"
        " only secure way to share a subscription between users. The inviter is identified either by a source email"
        " address, which must also be a valid Type.World user account and actually hold that subscription, or by a API"
        " endpoint secret key, in which case the subscription must originate from that same API endpoint."
    ),
    "parameters": collections.OrderedDict(
        {
            "targetUserEmail": {
                "description": "Email address of target Type.World user",
                "required": True,
            },
            "subscriptionURL": {
                "description": "Full subscription link including typeworld:// protocol and secret key and all.",
                "required": True,
            },
            "sourceUserEmail": {
                "description": (
                    "Email address of source Type.World user (not required, but either `sourceUserEmail` or `APIKey`"
                    " needs to be present)"
                ),
                "required": False,
            },
            "APIKey": {
                "description": (
                    "Secret API Key of inviting API endpoint (not required, but either `sourceUserEmail` or `APIKey`"
                    " needs to be present)"
                ),
                "required": False,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "invalidSubscriptionURL": "The subscription URL is of invalid format.",
            "invalidSource": "The system could not identify a valid source by either `sourceUserEmail` or `APIKey`.",
            "unknownTargetEmail": "The email of the invited user is unknown.",
            "sourceAndTargetIdentical": "The source user and the target user are identical.",
            "unknownSubscriptionForUser": "The source user doesn’t hold that subscription.",
            "invalidSourceAPIEndpoint": (
                "In case of an API Endpoint being the source of this request, it could not be identified by the APIKey"
                " parameter."
            ),
            "invitationsRequireProAccount": "Inviting users requires a Pro Plan for the user account.",
        }
    ),
    "exampleParameters": collections.OrderedDict(
        {
            "targetUserEmail": "johndoe@gmail.com",
            "subscriptionURL": "typeworld://json+https//awesomefonts.com/typeworldapi/daz4Ub54mut2XDLz6vGx",
            "APIKey": "GBuzxMs32CgAIbofFp6c",
        }
    ),
}


APICOMMANDS["revokeSubscriptionInvitation"] = {
    "public": True,
    "description": (
        "Revoke the invitation to a subscription for a Type.World user (identified by his/her email address). All"
        " subsequent invitation by that user to others will also be deleted."
    ),
    "parameters": collections.OrderedDict(
        {
            "targetUserEmail": {
                "description": "Email address of target Type.World user",
                "required": True,
            },
            "subscriptionURL": {
                "description": "Full subscription link including typeworld:// protocol and secret key and all.",
                "required": True,
            },
            "sourceUserEmail": {
                "description": (
                    "Email address of source Type.World user (not required, but either `sourceUserEmail` or `APIKey`"
                    " needs to be present)"
                ),
                "required": False,
            },
            "APIKey": {
                "description": (
                    "Secret API Key of inviting API endpoint (not required, but either `sourceUserEmail` or `APIKey`"
                    " needs to be present)"
                ),
                "required": False,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "invalidSubscriptionURL": "The subscription URL is of invalid format.",
            "invalidSource": "The system could not identify a valid source by either `sourceUserEmail` or `APIKey`.",
            "unknownTargetEmail": "The email of the invited user is unknown in the system.",
            "unknownSubscription": "No matching subscription could be identified to be revoked.",
        }
    ),
    "exampleParameters": collections.OrderedDict(
        {
            "targetUserEmail": "johndoe@gmail.com",
            "subscriptionURL": "typeworld://json+https//awesomefonts.com/typeworldapi/daz4Ub54mut2XDLz6vGx",
            "APIKey": "GBuzxMs32CgAIbofFp6c",
        }
    ),
}


APICOMMANDS["acceptInvitations"] = {
    "public": False,
    "description": "Confirm a number of invitations by ID",
    "parameters": collections.OrderedDict(
        {
            "clientVersion": {
                "description": "Version number of client library",
                "required": True,
            },
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "User’s secret key",
                "required": True,
            },
            "anonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
            "subscriptionIDs": {
                "description": "Comma-separated list of user subscription IDss",
                "required": True,
            },
        }
    ),
    "return": "Returns contents of downloadUserSubscriptions command.",
}

APICOMMANDS["declineInvitations"] = {
    "public": False,
    "description": "Confirm a number of invitations by ID",
    "parameters": collections.OrderedDict(
        {
            "clientVersion": {
                "description": "Version number of client library",
                "required": True,
            },
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "User’s secret key",
                "required": True,
            },
            "anonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
            "subscriptionIDs": {
                "description": "Comma-separated list of user subscription IDss",
                "required": True,
            },
        }
    ),
    "return": "Returns contents of downloadUserSubscriptions command.",
}

APICOMMANDS["userAppInstances"] = {
    "public": False,
    "description": "List all apps registered with a user",
    "parameters": collections.OrderedDict(
        {
            "anonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "User’s secret key",
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "userUnknown": "",
            "secretKeyInvalid": "",
            "appInstanceRevoked": "",
            "appInstanceUnknown": "",
        }
    ),
    "additionalReturn": collections.OrderedDict(
        {
            "appInstances": "A list of known app instances",
        }
    ),
}

APICOMMANDS["revokeAppInstance"] = {
    "public": False,
    "description": "Remotely revoke an app instance",
    "parameters": collections.OrderedDict(
        {
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "User’s secret key",
                "required": True,
            },
            # 'authorizationKey': {
            # 	'description': 'Secret, purpose-bound auth key',
            # 	'required': True,
            # },
            "anonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "appInstanceUnknown": "Unknown app instance",
            "authorizationKeyUnknown": "Unknown auth instance",
        }
    ),
}

APICOMMANDS["reactivateAppInstance"] = {
    "public": False,
    "description": "Remotely reactivate an app instance",
    "parameters": collections.OrderedDict(
        {
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "User’s secret key",
                "required": True,
            },
            # 'authorizationKey': {
            # 	'description': 'Secret, purpose-bound auth key',
            # 	'required': True,
            # },
            "anonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "appInstanceUnknown": "Unknown app instance",
            "authorizationKeyUnknown": "Unknown auth instance",
        }
    ),
}

APICOMMANDS["createUserAccount"] = {
    "public": False,
    "description": "Remotely create a new user",
    "parameters": collections.OrderedDict(
        {
            "name": {
                "description": "Name",
                "required": True,
            },
            "email": {
                "description": "Email Address",
                "required": True,
            },
            "password": {
                "description": "Hashed Password",
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "userExists": "User already exists",
            "emailInvalid": "Email address is invalid",
        }
    ),
}

APICOMMANDS["deleteUserAccount"] = {
    "public": False,
    "description": "Remotely delete a user",
    "parameters": collections.OrderedDict(
        {
            "email": {
                "description": "Email Address",
                "required": True,
            },
            "password": {
                "description": "Hashed Password",
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "userExists": "User already exists",
            "emailInvalid": "Email address is invalid",
        }
    ),
}

APICOMMANDS["logInUserAccount"] = {
    "public": False,
    "description": "Log user in (verify credentials)",
    "parameters": collections.OrderedDict(
        {
            "email": {
                "description": "Email Address",
                "required": True,
            },
            "password": {
                "description": "Password",
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "userUnknown": "User does not exist",
            "passwordInvalid": "Password is wrong",
        }
    ),
}

APICOMMANDS["versions"] = {
    "public": False,
    "description": "Output version of used Python module",
    "parameters": {},
    "return": None,
}


APICOMMANDS["downloadUserSubscriptions"] = {
    "public": False,
    "description": "Compiles list of URLs and returns them to client",
    "parameters": collections.OrderedDict(
        {
            "clientVersion": {
                "description": "Version number of client library",
                "required": True,
            },
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "User’s secret key",
                "required": True,
            },
            "anonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "userUnknown": "User does not exist",
            "secretKeyInvalid": "",
            "appInstanceUnknown": "",
        }
    ),
}

APICOMMANDS["addAPIEndpointToUserAccount"] = {
    "public": False,
    "description": "Adds an API endpoint to a user account for the purpose of obtaining an APIkey",
    "parameters": collections.OrderedDict(
        {
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "",
                "required": True,
            },
            "canonicalURL": {
                "description": "API endpoints canoncical URL",
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "userUnknown": "",
            "secretKeyInvalid": "",
            "APIEndpointTaken": "",
        }
    ),
}

APICOMMANDS["listAPIEndpointsForUserAccount"] = {
    "public": False,
    "description": "Adds an API endpoint to a user account for the purpose of obtaining an APIkey",
    "parameters": collections.OrderedDict(
        {
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": True,
            },
            "secretKey": {
                "description": "",
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "userUnknown": "",
            "secretKeyInvalid": "",
            "endpoints": "",
        }
    ),
}

APICOMMANDS["updateSubscription"] = {
    "public": True,
    "description": (
        "Announce to all participating users that this particular subscription has changed and fresh data needs to be"
        " pulled by the client app from the publisher server.\n\nUsing this command is only available to publishers"
        " participating in the Pro Publisher Plan, available from your user account at"
        " [https://type.world/account/developer](/account/developer) (after login).\n\nCurrently not yet implemented:"
        " If you supply the timeStretch parameter, all users of this subscription that are currently online with the"
        " app will be notified with a delay chosen randomly within your given time window. This way you can spread"
        " your server load according to the number of users of your subscription. However, since the delay is"
        " randomized, peaks may still occur."
    ),
    "parameters": collections.OrderedDict(
        {
            "APIKey": {
                "description": (
                    "Secret API Key for an API Endpoint, to be obtained through the Type.World user account"
                ),
                "required": True,
            },
            "subscriptionURL": {
                "description": "Full subscription link including typeworld:// protocol and secret key and all.",
                "required": True,
            },
            "timeStretch": {
                "description": (
                    "Number of minutes (0—60) for which client apps will randomly wait to pull updated data from the"
                    " publisher’s server. (Currently not implemented)"
                ),
                "required": False,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "invalidSubscriptionURL": "Subscription URL is invalid.",
            "invalidTimeStretchValue": "Time stretch value is invalid.",
            "unknownAPIKey": "API key in unkown",
            "unknownSubscriptionURL": "No subscription under this URL exists.",
            "paidSubscriptionRequired": "Please set up your paid publisher subscription at https://type.world/account",
        }
    ),
    "exampleParameters": collections.OrderedDict(
        {
            "APIKey": "GBuzxMs32CgAIbofFp6c",
            "subscriptionURL": "typeworld://json+https//awesomefonts.com/typeworldapi/daz4Ub54mut2XDLz6vGx",
            "timeStretch": 5,
        }
    ),
}

APICOMMANDS["handleTraceback"] = {
    "public": False,
    "description": "Record a traceback from an app instance and possibly notify code authors by email",
    "parameters": collections.OrderedDict(
        {
            "payload": {
                "description": "Traceback payload",
                "required": True,
            },
            "supplementary": {
                "description": "Additional Information",
                "required": False,
            },
        }
    ),
    "return": None,
}

APICOMMANDS["downloadSettings"] = {
    "public": False,
    "description": "Downloads centrally decided settings for users",
    "parameters": collections.OrderedDict(
        {
            "clientVersion": {
                "description": "Version number of client library",
                "required": True,
            },
            "anonymousUserID": {
                "description": "Anonymous User ID",
                "required": False,
            },
            "secretKey": {
                "description": "User’s secret key",
                "required": False,
            },
            "sourceAnonymousAppID": {
                "description": "Anonymous App ID",
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "userUnknown": "User does not exist",
            "secretKeyInvalid": "",
            "appInstanceUnknown": "",
        }
    ),
}

APICOMMANDS["resendEmailVerification"] = {
    "public": False,
    "description": "Resend email verification link",
    "parameters": collections.OrderedDict(
        {
            "email": {
                "description": "User email",
                "required": True,
            },
        }
    ),
    "return": collections.OrderedDict(
        {
            "userUnknown": "User does not exist",
            "userIsVerified": "User is already verified, did nothing",
        }
    ),
}

APICOMMANDS["reportAPIEndpointError"] = {
    "public": False,
    "description": (
        "Notify the central server of a API Endpoint error, in order to have the server check the endpoint and notify"
        " the author."
    ),
    "parameters": collections.OrderedDict(
        {
            "subscriptionURL": {
                "description": "Full subscription link including typeworld:// protocol and secret key and all.",
                "required": True,
            },
        }
    ),
    "return": None,
}
