# Type.World Sign-In

### Document Date

Document last revised: %timestamp%

### Problems with the Documentation

If you have any problems in understanding the system that probably means that it hasn’t been explained well enough yet. In this case, please drop me a line at [hello@type.world](mailto:hello@type.world) and explain your limitations. I will try to improve the documentation.




# Introduction

Similar to well known sign-in solutions such as *Sign in with Google* or *Sign in with Apple*, Type.World also provides its own sign-in service. It makes the Type.World user accounts available to third party websites and apps for user authentication. The main beneficiaries are independent type foundries who want to offer a smooth font shopping user experience, streamlining the onboarding for users that already hold a Type.World user account. With time, *Sign in with Type.World* will become the preferred sign-in solution as Type.World establishes its brand among font users and shoppers.

At a glance:

* Users don’t need to create additional user accounts for each foundry in a decentralized font shopping ecosystem
* Third parties may choose to access the user’s billing address (requires user consent) to further streamline the onboarding process
* Onboarding the user onto the Type.World App becomes one and the same process with user authentication against the third party, as the Sign-In service also provides an anonymous Type.World user ID that can be utilized to invite the user to install fonts through the Type.World app, eliminating alternative onboarding routes

## Live Example: Awesome Fonts

Awesome Fonts is an imaginary font foundry that uses Type.World Sign-In for user authentication and onboarding to the Type.World app. Hop over to [awesomefonts.appspot.com](https://awesomefonts.appspot.com/) to try it out by fake-"purchasing" a number of fonts. Make sure you have the [Type.World App](https://type.world/app/) up and running and are logged in with the same user account you’ll use to authenticate at Awesome Fonts.

The source code of the imaginary Awesome Fonts Foundry is available for your reference at [github.com/typeworld/awesomefontsfoundry](https://github.com/typeworld/awesomefontsfoundry).

## Usage

### Initial access

Participating third party websites/apps would provide a ***Sign in with Type.World*** button to their users additionally to or replacing other sign-in solutions, such as the third party’s own user account system.

If the user chooses the service and clicks on the button, they are being redirected to the Type.World website for *authentication* (which Type.World user) and *authorization* (which data is being transmitted). The *authentication* step may include the sign-up for a Type.World user account (including an email verification step), or be completely transparent for users who are already signed in to the Type.World website.

The below screenshot shows the authentication step in the case of the user already being logging in to Type.World:

![](/static/docs/signin/authentication.png)

In the following *authorization* step, users are required to authorize the third party to access the user’s data depending on the *scopes* requested by the third party. This step may include the user having to fill out their billing address or tax ID, if applicable, with Type.World performing basic data validation. Additionally, on request, users are provided with the precise raw data (as *JSON* data) that the third party receives from Type.World for the sake of building trust through transparency.

The below screenshot shows the authorization step in the case of the requested data already being complete and validated. In this case, the scopes are mentioned only in summary. The full data view is only a click away, with the raw JSON data view requiring another click in the same dialog.

![](/static/docs/signin/authorization.png)

Upon completing the sign-in process, the user is redirected to the third party website or app. Subsequently, hidden from the user, the third party would receive the *access token* and use it to obtain the required data from the Type.World API.

### Editing of Existing Data for Returning Users

The third party may choose to mirror the obtained data in their own database and continue to use it going forward independently of the *Type.World Sign-In* service.

However, for a continued flawless user experience, third parties are encouraged to redirect users back to Type.World for editing data such as the user’s billing address; then obtaining the new data immediately once more from the API upon the user’s return to the third party website. This keeps the user’s data up-to-date centrally and eliminates subsequent repetition of data editing for the user at another website, resulting in the intended streamlined user experience.

For that, *Type.World Sign-In* provides ready-made edit URLs that third parties may use to redirect users to for data editing.

![](/static/docs/signin/edit.png)


## Scopes

Currently, *Type.World Sign-In* offers the following so calles *scopes* of data. Depending on the type or country of residence of your business, not all scopes may be required for your users.

To provide the best user experience for your users, restrict the scopes you request to the **absolutely necessary**. For example, a free font website requiring users to authorize access to their billing address may cause serious trust issues in the users and backfire on you. Professional font customers, however, may not find it untrustworthy to be asked for their billing address.

The scopes in detail:

* `account` contains the user’s **name**, **email address**, and **anonymous Type.World user ID**. If you choose to invite your users to install fonts through the Type.World app, this scope is the minumum one you want to use. Inviting a user through their anonymous Type.World user ID is the safest way to invite them, as email addresses can change. However, you are not required to use *Type.World Sign-In* for that. You can still choose to invite them via the API using their email address, or simply by providing a button on your website and leave it up to the user which Type.World user account to connect to your foundry.
* `billingaddress` contains the user’s **billing address**. Type.World performs basic data validation such as requiring ZIP codes or state/province data for countries that require it. Additionally, the user address is provided as a pre-formatted string following each country’s own address formatting conduct (where known), saving you the burden of correct formatting. A fallback formatting is provided for all other countries. If you find your country’s address formatting to be wrong or the ZIP code/state data obligation to be wrong, please get in touch at [hello@type.world](mailto:hello@type.world).
* `euvatid` contains the user’s **European Union VAT ID**, intended for third party businesses located in the European Union. The VAT ID (if present) has been validated to be correctly formatted and existing as is required by the European tax authorities. However, it has not been verified to match the billing address given by the user. Only third parties in the EU should request this scope; all others ignore it.

Are you missing a data scope that you might need for your business, such as your country’s tax ID? Get in touch at [hello@type.world](mailto:hello@type.world) to discuss whether we can add it.

## Security

*Type.World Sign-In* is a fully OAuth 2.0-compliant authentication and authorization solution.

The third party carries a small portion of the security responsibility by checking incoming redirects against the correct `state` code (see details further down). This is a part of the OAuth 2.0 protocol and must be observed by  the third party.

## Pricing

To prevent abuse, even the basic usage of *Type.World Sign-In* needs to cost a little bit. The prices are very competitive.

The access to *Type.World Sign-In* using the `account` scope (*Basic scope*) is priced between 0.01€ and 0.04€ per monthly active user, to be paid by the third party. See [price list](/developer/prices). The *Basic* scope may be used for basic user authentication and onboarding to the Type.World App.

Convenience functionality such as the `billingaddress` scope (*Extended scopes*) which greatly enhance the professional font shopping experience are priced between 0.02€ and 0.08€ per monthly active user, to be paid by the third party. See [price list](/developer/prices).

Access is counted as monthly active token access on the user data endpoint, so several requests per month for the same user is counted only once. Normally, the amount of monthly requests should correlate strongly with monthly font purchases.

Usage for the end user is free.

# How to Implement Type.World Sign-In for Your App

This section describes how to set up **Type.World Sign-In** for your website or app (generalized as "app"). It is based on [OAuth 2 Simplified](https://aaronparecki.com/oauth-2-simplified/) by Aaron Parecki.

## Create An App

After you’ve enabled [billing](/developer/billing/) on your administrator’s Type.World user account, you can create a sign-in app under [My Apps](/developer/myapps).

The redirect URLs asked there can be partial URLs, meaning it’s sufficient to supply your website’s root URL (e.g. `https://awesomefonts.appspot.com`). They can be online or local development URLs (e.g. `http://0.0.0.0:8080`), and they can be custom URL handlers (e.g. `typeworld://openapp`).

Please also choose the appropriate scopes for your app with regards to data restraint.

Once completed, you will be provided with your app’s Client ID, Client Secret (don’t give this one away), and a computer-readable representation of your chosen scopes.

The sign-in URL given there may be used as is with the exception of replacing the `redirect_uri` and `state` parameters to suit your setup.

## Use Type.World Sign-In for Your App

### Step 1: Authentication & Authorization

When the user clicks on the *Sign In with Type.World* button, redirect them to the following link: `https://type.world/signin?client_id=AhIpObOtEtZqsADsmrUMo57d8Kh1E21TilgkZ6gV &response_type=code&redirect_uri=https%3A%2F%2Fawesomefonts.appspot.com &scope=account,billingaddress,euvatid&state=1234zyx`

* `response_type=code` - Indicates that your server expects to receive an authorization code
* `client_id` - The client ID you received when you first created the application
* `redirect_uri` - Indicates the URI to return the user to after authorization is complete. This must be url-escaped.
* `scope` - One or more scope values indicating which parts of the user's account you wish to access
* `state` - A random string generated by your application, which you'll verify later

The user will be guided through the authentication and authorization process and once they complete it, they are being redirected to your app with an authorization code: `https://awesomefonts.appspot.com?code=AUTH_CODE_HERE&state=1234zyx`

* `code` - The server returns the authorization code in the query string
* `state` - The server returns the same state value that you passed

You should first compare the `state` value to ensure it matches the one you started with. You can typically store the state value in a cookie or session, and compare it when the user comes back. This helps ensure your redirection endpoint isn't able to be tricked into attempting to exchange arbitrary authorization codes.

If the `state` parameter doesn’t match yours, pretend like none of this ever happened and continue as if no user was logged in.


### Step 2: Getting an Access Token

Your server exchanges the authorization code for an access token by making a `POST` request to the authorization server’s token endpoint:

`POST https://type.world/auth/token` with the data `{"grant_type"="authorization_code", "code"="AUTH_CODE_HERE", "redirect_uri"="REDIRECT_URI", "client_id"="CLIENT_ID", "client_secret"="CLIENT_SECRET"}`
 
* `grant_type=authorization_code` - The grant type for this flow is authorization_code
* `code=AUTH_CODE_HERE` - This is the code you received in the query string
* `redirect_uri=REDIRECT_URI` - Must be identical to the redirect URI provided in the original link
* `client_id=CLIENT_ID` - The client ID you received when you first created the application
* `client_secret=CLIENT_SECRET` - Since this request is made from server-side code, the secret is included

The server replies with an access token

`{"access_token":"RsT5OjbzRn430zqMLgV3Ia"}`

or if there was an error

`{"error":"invalid_request"}`

Once you have the token, you store it safely in your database. This is your key to obtain user data.

### Step 3: Obtaining User Data

To obtain the user data, make an authenticated `POST` request using the token for authentication at the server’s user data endpoint: 

`POST https://type.world/auth/userdata ` with the HTTP headers `Authorization: Bearer RsT5OjbzRn430zqMLgV3Ia`

The server will response with the JSON data:

```
{
 "userdata": {
  "user_id": "cb3f5f-d6c5-4c41-b1fa-70349d56a9",
  "edit_uri": "https://type.world/auth/edituserdata?scope=account,billingaddress,euvatid&edit_token=70349d56a9b1fa&redirect_uri=__place_for_redirect_uri__",
  "scope": {
   "account": {
    "name": "Account Information",
    "data": {
     "name": "John Doe",
     "email": "johndoe@gmail.com"
    },
    "missing_required_data": []
   },
   "billingaddress": {
    "name": "Billing Address",
    "edit_uri": "https://type.world/auth/edituserdata?scope=billingaddress&edit_token=70349d56a9b1fa&redirect_uri=__place_for_redirect_uri__",
    "data": {
     "company": "",
     "name": "John Doe",
     "address": "Reindeer Way 8",
     "address_2": "",
     "zipcode": "01234",
     "town": "Springfield",
     "state": "MA",
     "country": "United States of America",
     "country_code": "US"
    },
    "missing_required_data": [],
    "formatted_billing_address": "John Doe\nReindeer Way 8\nSpringfield MA 01234\nUnited States of America"
   },
   "euvatid": {
    "name": "EU VAT ID",
    "edit_uri": "https://type.world/auth/edituserdata?scope=euvatid&edit_token=70349d56a9b1fa&redirect_uri=__place_for_redirect_uri__",
    "data": {
     "euvatid": ""
    },
    "missing_required_data": []
   }
  }
 }
}
```

## Send User Back to Edit Data

As previously mentioned, you are encouraged to have the user edit their data (e.g. billing address) centrally in the Type.World database so that their changes reflect for future usage in other third party apps.

The JSON data returned by the user data endpoint contains `edit_uri` fields for this purpose, one for each scope to edit a scope separately, and one at the root of the `userdata` branch for editing all scopes at once.

These links are ready to use with the exception of the string `__place_for_redirect_uri__` which you need to replace for your url-escaped return link.

The links contains a secret `edit_token` which is **valid only for one hour**. Therefore, if you want to send your user back to Type.World for editing their data, you must fetch a fresh copy of the user data to present the user with the correct links.

### Successful Editing

If the user has successfully edited their data, they are being redirected back to your app: `https://awesomefonts.appspot.com?redirect_reason=userdata_edit&status=success`

So if you encounter the parameters `redirect_reason=userdata_edit` and `status=success`, you want to redownload the user data from the user data endpoint and display the updated data to the user and continue your flow.

### Outdated Edit Token

In case the edit token is outdated (older than one hour), the user is being redirected back to your app: `https://awesomefonts.appspot.com?redirect_reason=userdata_edit&status=invalid_edit_token`

So if you encounter the parameters `redirect_reason=userdata_edit` and `status=invalid_edit_token`, you want to redownload the user data from the user data endpoint for fresh `edit_uri` containing the fresh edit token and inform your user via an alert that they need to repeat their previous action.

In any case, the best practise is to download fresh user data each time before displaying an editing link to the user to avoid this scenario.
