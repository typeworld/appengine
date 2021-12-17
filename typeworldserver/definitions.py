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
US	United States of America
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

EU_COUNTRIES = (
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
    # "UK", welp
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
)

COUNTRIES = []
COUNTRIES_DICT = {}
for line in COUNTRIES_PLAIN.splitlines():
    line = line.strip()
    code, name = line.split("\t")
    COUNTRIES.append((code, name))
    COUNTRIES_DICT[code] = name
COUNTRIES = sorted(COUNTRIES, key=lambda country: country[1])

COUNTRIES_THAT_REQUIRE_ZIP_CODE = (
    "AR",
    "AU",
    "AT",
    "BG",
    "BR",
    "CA",
    "CN",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "UK",
    "GL",
    "IS",
    "IN",
    "ID",
    "IE",
    "IL",
    "IT",
    "JP",
    "KR",
    "LU",
    "MY",
    "NL",
    "NZ",
    "NO",
    "OM",
    "PL",
    "PT",
    "RO",
    "RU",
    "SG",
    "ZA",
    "ES",
    "SE",
    "CH",
    "UA",
    "US",
    "UY",
)

COUNTRIES_THAT_REQUIRE_STATE_OR_PROVINCE = (
    "US",
    "CA",
    "AU",
    "CN",
    "BR",
    "MX",
    "MY",
    "IT",
    "JP",
    "RO",
)

#
#
#  ADDRESSES
#
#

ADDRESS_FORMAT = {
    "default": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{state}
{country}""",
    "AR": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "AU": """{company}
{name}
{address}
{address_2}
{town} {state} {zipcode}
{country}""",
    "AT": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "BG": """{company}
{name}
{address}
{address_2}
B-{zipcode} {town}
{country}""",
    "BR": """{company}
{name}
{address}
{address_2}
{town}
{zipcode}
{country}""",
    "CA": """{company}
{name}
{address}
{address_2}
{town} {state} {zipcode}
{country}""",
    "CN": """{company}
{name}
{address}
{address_2}
{state}
{zipcode} {town}
{country}""",
    "TW": """{company}
{name}
{address}
{address_2}
{town} {zipcode}
{country}""",
    "CZ": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "DK": """{company}
{name}
{address}
{address_2}
DK-{zipcode} {town}
{country}""",
    "EE": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "FJ": """{company}
{name}
{address}
{address_2}
{state}
{town}
{country}""",
    "FI": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "FR": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "DE": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "UK": """{company}
{name}
{address}
{address_2}
{town}
{state}
{zipcode}
{country}""",
    "GL": """{company}
{name}
{address}
{address_2}
DK-{zipcode} {town}
{country}""",
    "HK": """{company}
{name}
{address}
{address_2}
{town}
{country}""",
    "IS": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "IN": """{company}
{name}
{address}
{address_2}
{town} {zipcode}
{country}""",
    "ID": """{company}
{name}
{address}
{address_2}
{town} {zipcode}
{country}""",
    "IE": """{company}
{name}
{address}
{address_2}
{town}
{zipcode}
{country}""",
    "IL": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "IT": """{company}
{name}
{address}
{address_2}
{zipcode} {town} {state}
{country}""",
    "JP": """{company}
{name}
{address}
{address_2}
{town} {state} {zipcode}
{country}""",
    "KR": """{company}
{name}
{address}
{address_2}
{town} {zipcode}
{country}""",
    "LU": """{company}
{name}
{address}
{address_2}
L-{zipcode} {town}
{country}""",
    "MY": """{company}
{name}
{address}
{address_2}
{town} {zipcode}, {state}
{country}""",
    "NL": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "NZ": """{company}
{name}
{address}
{address_2}
{town} {zipcode}
{country}""",
    "NO": """{company}
{name}
{address}
{address_2}
NO-{zipcode} {town}
{country}""",
    "OM": """{company}
{name}
{address}
{address_2}
{zipcode}
{town}
{country}""",
    "PK": """{company}
{name}
{address}
{address_2}
{town} {zipcode}
{country}""",
    "PL": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "PT": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "RO": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{state}
{country}""",
    "RU": """{company}
{name}
{address}
{address_2}
{town}
{state}
{zipcode}
{country}""",
    "SG": """{company}
{name}
{address}
{address_2}
{town} {zipcode}
{country}""",
    "ZA": """{company}
{name}
{address}
{address_2}
{town}
{zipcode}
{country}""",
    "ES": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "SE": """{company}
{name}
{address}
{address_2}
SE-{zipcode} {town}
{country}""",
    "CH": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
    "UA": """{company}
{name}
{address}
{address_2}
{town}
{zipcode}
{country}""",
    "US": """{company}
{name}
{address}
{address_2}
{town} {state} {zipcode}
{country}""",
    "UY": """{company}
{name}
{address}
{address_2}
{zipcode} {town}
{country}""",
}


#
#
#  API
#
#


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
            "emailNotVerified": "The user’s email address isn’t verified. A new verification email has been sent.",
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


GCPlinks = [
    [
        "Johannesburg, South Africa",
        [[-33.9248685, 18.4240553], [-33.9248685, 10.32441], [-0.79606, 0.48066]],
        "Lagos, Nigeria",
    ],
    [
        "Lagos, Nigeria",
        [[-0.79606, 0.48066], [-0.79606, -17.01473], [21.42239, -25.18856], [34.85889, -20.26669]],
        "Lisbon, Portugal",
    ],
    [
        [[34.85889, -20.26669]],
        "London, UK",
    ],
    [
        [[34.85889, -20.26669], [35.94434, -5.92006], [37.88646, 5.36978]],
        "Marseille, France",
    ],
    [
        "Lisbon, Portugal",
        "Madrid, Spain",
    ],
    [
        "Madrid, Spain",
        "Marseille, France",
    ],
    [
        "Madrid, Spain",
        "Paris, France",
    ],
    [
        "Marseille, France",
        "Paris, France",
    ],
    [
        "Marseille, France",
        "Frankfurt, Germany",
    ],
    [
        "Paris, France",
        "Frankfurt, Germany",
    ],
    [
        "Rome, Metropolitan City of Rome, Italy",
        "Milan, Metropolitan City of Milan, Italy",
    ],
    [
        "Milan, Metropolitan City of Milan, Italy",
        "Zürich, Switzerland",
    ],
    [
        "Zürich, Switzerland",
        "Frankfurt, Germany",
    ],
    [
        "Munich, Germany",
        "Prague, Czechia",
    ],
    [
        "Munich, Germany",
        "Zürich, Switzerland",
    ],
    [
        "Frankfurt, Germany",
        "Prague, Czechia",
    ],
    [
        "Frankfurt, Germany",
        "Hamburg, Germany",
    ],
    [
        "Sofia, Bulgaria",
        "Budapest, Hungary",
    ],
    [
        "Budapest, Hungary",
        "Warsaw, Poland",
    ],
    [
        "Warsaw, Poland",
        "Frankfurt, Germany",
    ],
    [
        "Milan, Metropolitan City of Milan, Italy",
        "Sofia, Bulgaria",
    ],
    [
        "Budapest, Hungary",
        "Hamburg, Germany",
    ],
    [
        "Warsaw, Poland",
        "Kyiv, Ukraine, 02000",
    ],
    [
        "Kyiv, Ukraine, 02000",
        "Moscow, Russia",
    ],
    [
        "St Petersburg, Russia",
        "Moscow, Russia",
    ],
    [
        "St Petersburg, Russia",
        "Stockholm, Sweden",
    ],
    [
        "Stockholm, Sweden",
        "Hamburg, Germany",
    ],
    [
        "St Petersburg, Russia",
        "Warsaw, Poland",
    ],
    [
        "St Petersburg, Russia",
        "Hamburg, Germany",
    ],
    [
        "Stockholm, Sweden",
        "Warsaw, Poland",
    ],
    [
        "Hamburg, Germany",
        "London, UK",
    ],
    [
        "Hamburg, Germany",
        "Amsterdam, Netherlands",
    ],
    [
        "Amsterdam, Netherlands",
        "Paris, France",
    ],
    [
        "Amsterdam, Netherlands",
        "London, UK",
    ],
    [
        "Budapest, Hungary",
        "Zagreb, Croatia",
    ],
    [
        "Munich, Germany",
        "Zagreb, Croatia",
    ],
    [
        "Munich, Germany",
        "Zagreb, Croatia",
    ],
    [
        "Bucharest, Romania",
        "Sofia, Bulgaria",
    ],
    [
        "Bucharest, Romania",
        "Kyiv, Ukraine, 02000",
    ],
    [
        "London, UK",
        "Dublin, Ireland",
    ],
    [
        "Dublin, Ireland",
        "New York, NY, USA",
    ],
    [
        "London, UK",
        "New York, NY, USA",
    ],
    [
        "Paris, France",
        "Ashburn, VA, USA",
    ],
    [
        "Paris, France",
        "New York, NY, USA",
    ],
    [
        "New York, NY, USA",
        "Montreal, QC, Canada",
    ],
    [
        "New York, NY, USA",
        "Toronto, ON, Canada",
    ],
    [
        "Toronto, ON, Canada",
        "Montreal, QC, Canada",
    ],
    [
        "New York, NY, USA",
        "Ashburn, VA, USA",
    ],
    [
        "Toronto, ON, Canada",
        "Ashburn, VA, USA",
    ],
    [
        "Chicago, IL, USA",
        "New York, NY, USA",
    ],
    [
        "Chicago, IL, USA",
        "Toronto, ON, Canada",
    ],
    [
        "Chicago, IL, USA",
        "Atlanta, GA, USA",
    ],
    [
        "Atlanta, GA, USA",
        "Ashburn, VA, USA",
    ],
    [
        "Atlanta, GA, USA",
        "Miami, FL, USA",
    ],
    [
        "Miami, FL, USA",
        "Bogotá, Bogota, Colombia",
    ],
    [
        "Miami, FL, USA",
        [[-4.01051, -27.50141]],
        "São Paulo, State of São Paulo, Brazil",
    ],
    [
        "Miami, FL, USA",
        [[-4.01051, -27.50141]],
        "Rio de Janeiro, State of Rio de Janeiro, Brazil",
    ],
    [
        "São Paulo, State of São Paulo, Brazil",
        "Rio de Janeiro, State of Rio de Janeiro, Brazil",
    ],
    [
        "São Paulo, State of São Paulo, Brazil",
        "Buenos Aires, Argentina",
    ],
    [
        "Santiago, Santiago Metropolitan Region, Chile",
        "Buenos Aires, Argentina",
    ],
    [
        "Santiago, Santiago Metropolitan Region, Chile",
        [[21.94941, -94.41002]],
        "New York, NY, USA",
    ],
    [
        "Santiago, Santiago Metropolitan Region, Chile",
        [[23.98512, -120.62679]],
        "Los Angeles, CA, USA",
    ],
    [
        "Santiago de Querétaro, Qro., Mexico",
        "Dallas, TX, USA",
    ],
    [
        "Miami, FL, USA",
        "Los Angeles, CA, USA",
    ],
    [
        "Dallas, TX, USA",
        "Denver, CO, USA",
    ],
    [
        "Dallas, TX, USA",
        "Atlanta, GA, USA",
    ],
    [
        "Dallas, TX, USA",
        "Chicago, IL, USA",
    ],
    [
        "Denver, CO, USA",
        "Los Angeles, CA, USA",
    ],
    [
        "Denver, CO, USA",
        "Seattle, WA, USA",
    ],
    [
        "Denver, CO, USA",
        "Chicago, IL, USA",
    ],
    [
        "Denver, CO, USA",
        "San Jose, CA, USA",
    ],
    [
        "Palo Alto, CA, USA",
        "Chicago, IL, USA",
    ],
    [
        "San Jose, CA, USA",
        "Los Angeles, CA, USA",
    ],
    [
        "Palo Alto, CA, USA",
        "Seattle, WA, USA",
    ],
    [
        "Palo Alto, CA, USA",
        "Santa Clara, CA, USA",
        "San Jose, CA, USA",
    ],
    [
        "Chicago, IL, USA",
        "Seattle, WA, USA",
    ],
    [
        "Los Angeles, CA, USA",
        "Sydney NSW, Australia",
    ],
    [
        "Sydney NSW, Australia",
        "Melbourne VIC, Australia",
    ],
    [
        "Sydney NSW, Australia",
        [[-31.9523123, 115.861309]],
        "Singapore",
    ],
    [
        "Singapore",
        "Kuala Lumpur, Federal Territory of Kuala Lumpur, Malaysia",
    ],
    [
        "Singapore",
        "Chennai, Tamil Nadu, India",
    ],
    [
        "Singapore",
        [[2.03465, 74.44271]],
        "Mumbai, Maharashtra, India",
    ],
    [
        "Mumbai, Maharashtra, India",
        "Delhi, India",
    ],
    [
        "Chennai, Tamil Nadu, India",
        "Delhi, India",
    ],
    [
        "Chennai, Tamil Nadu, India",
        "Mumbai, Maharashtra, India",
    ],
    [
        "Mumbai, Maharashtra, India",
        [[24.34033, 63.63196]],
        "Fujairah - United Arab Emirates",
    ],
    [
        [[24.34033, 63.63196]],
        "Muscat, Oman",
    ],
    [
        [[24.34033, 63.63196]],
        [[15.67844, 57.6556]],
        [[-4.0434771, 44.73568]],
        [[-26.2041028, 39.19857]],
        "Johannesburg, South Africa",
    ],
    [
        [[-4.0434771, 44.73568]],
        "Mombasa, Kenya",
    ],
    [
        [[15.67844, 57.6556]],
        [[11.83765, 43.76888]],
        [[29.69986, 32.47494]],
        [[31.55981, 32.29998]],
        [[37.45742, 11.20945]],
        [[37.88646, 5.32909]],
        # Marseille
    ],
    [
        [[37.45742, 11.20945]],
        "Milan, Metropolitan City of Milan, Italy",
    ],
    [
        "Singapore",
        "Hong Kong",
        "Taipei City, Taiwan",
        "Osaka, Japan",
        "Tokyo, Japan",
    ],
    [
        "Tokyo, Japan",
        "Los Angeles, CA, USA",
    ],
    [
        "Osaka, Japan",
        "Los Angeles, CA, USA",
    ],
    [
        "Tokyo, Japan",
        "Seattle, WA, USA",
    ],
    [
        "Taipei City, Taiwan",
        "Los Angeles, CA, USA",
    ],
    [
        "Singapore",
        "Taipei City, Taiwan",
    ],
    [
        "Singapore",
        "Seoul, South Korea",
    ],
    [
        "Seoul, South Korea",
        "Tokyo, Japan",
    ],
    [
        "Seoul, South Korea",
        "Osaka, Japan",
    ],
    [
        "Singapore",
        "Tokyo, Japan",
    ],
    [
        "Singapore",
        "Jakarta, Indonesia",
    ],
    [
        "Tokyo, Japan",
        [[-8.27653, 167.20147]],
        "Sydney NSW, Australia",
    ],
]

GCPedgenodes = {
    "Ashburn, VA, USA": [39.0437567, -77.4874416],
    "Atlanta, GA, USA": [33.7489954, -84.3879824],
    "Chicago, IL, USA": [41.8781136, -87.6297982],
    "Denver, CO, USA": [39.7392358, -104.990251],
    "Dallas, TX, USA": [32.7766642, -96.79698789999999],
    "Los Angeles, CA, USA": [34.0522342, -118.2436849],
    "Miami, FL, USA": [25.7616798, -80.1917902],
    "Montreal, QC, Canada": [45.5016889, -73.567256],
    "New York, NY, USA": [40.7127753, -74.0059728],
    "Palo Alto, CA, USA": [37.4418834, -122.1430195],
    "San Jose, CA, USA": [37.3382082, -121.8863286],
    "Santa Clara, CA, USA": [37.3541079, -121.9552356],
    "Seattle, WA, USA": [47.6062095, -122.3320708],
    "Santiago de Querétaro, Qro., Mexico": [20.5887932, -100.3898881],
    "Toronto, ON, Canada": [43.653226, -79.3831843],
    "Bogotá, Bogota, Colombia": [4.710988599999999, -74.072092],
    "Buenos Aires, Argentina": [-34.6036844, -58.3815591],
    "Rio de Janeiro, State of Rio de Janeiro, Brazil": [-22.9068467, -43.1728965],
    "Santiago, Santiago Metropolitan Region, Chile": [-33.4488897, -70.6692655],
    "São Paulo, State of São Paulo, Brazil": [-23.5557714, -46.6395571],
    "Amsterdam, Netherlands": [52.3675734, 4.9041389],
    "Budapest, Hungary": [47.497912, 19.040235],
    "Bucharest, Romania": [44.4267674, 26.1025384],
    "Dublin, Ireland": [53.3498053, -6.2603097],
    "Frankfurt, Germany": [50.1109221, 8.6821267],
    "Hamburg, Germany": [53.5510846, 9.9936819],
    "Kyiv, Ukraine, 02000": [50.4501, 30.5234],
    "Lisbon, Portugal": [38.7222524, -9.1393366],
    "London, UK": [51.5072178, -0.1275862],
    "Madrid, Spain": [40.4167754, -3.7037902],
    "Marseille, France": [43.296482, 5.36978],
    "Milan, Metropolitan City of Milan, Italy": [45.4642035, 9.189982],
    "Munich, Germany": [48.1351253, 11.5819805],
    "Moscow, Russia": [55.755826, 37.6172999],
    "Paris, France": [48.856614, 2.3522219],
    "Prague, Czechia": [50.0755381, 14.4378005],
    "Rome, Metropolitan City of Rome, Italy": [41.9027835, 12.4963655],
    "St Petersburg, Russia": [59.9310584, 30.3609096],
    "Sofia, Bulgaria": [42.6977082, 23.3218675],
    "Stockholm, Sweden": [59.32932349999999, 18.0685808],
    "Warsaw, Poland": [52.2296756, 21.0122287],
    "Zagreb, Croatia": [45.8150108, 15.9819189],
    "Zürich, Switzerland": [47.3768866, 8.541694],
    "Fujairah - United Arab Emirates": [25.1288099, 56.3264849],
    "Muscat, Oman": [23.5880307, 58.3828717],
    "Chennai, Tamil Nadu, India": [13.0826802, 80.2707184],
    "Hong Kong": [22.3193039, 114.1693611],
    "Jakarta, Indonesia": [-6.2087634, 106.845599],
    "Kuala Lumpur, Federal Territory of Kuala Lumpur, Malaysia": [3.139003, 101.686855],
    "Delhi, India": [28.7040592, 77.10249019999999],
    "Osaka, Japan": [34.6937249, 135.5022535],
    "Mumbai, Maharashtra, India": [19.0759837, 72.8776559],
    "Seoul, South Korea": [37.566535, 126.9779692],
    "Singapore": [1.352083, 103.819836],
    "Taipei City, Taiwan": [25.0329636, 121.5654268],
    "Tokyo, Japan": [35.6761919, 139.6503106],
    "Sydney NSW, Australia": [-33.8688197, 151.2092955],
    "Melbourne VIC, Australia": [-37.8136276, 144.9630576],
    "Johannesburg, South Africa": [-26.2041028, 28.0473051],
    "Mombasa, Kenya": [-4.0434771, 39.6682065],
    "Lagos, Nigeria": [6.5243793, 3.3792057],
}

# Zones and place names: https://cloud.google.com/compute/docs/regions-zones
GCPzones = {
    "us-east": {"name": "Moncks Corner, South Carolina, USA", "geolocation": [33.1960027, -80.01313739999999]},
}


SIGNINSCOPES = {
    "account": {
        "name": "Account Information",
        "description": "Basic user account information such as the display name and email address",
    },
    "billingaddress": {
        "name": "Billing Address",
        "description": "Official billing address",
    },
    "euvatid": {
        "name": "EU VAT ID",
        "description": "European Union VAT ID <em>(optional)</em>",
    },
}
