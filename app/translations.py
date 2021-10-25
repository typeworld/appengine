# project
import app
from app import webapp

# other
import re
import json
from flask import abort, g, redirect
from google.cloud import ndb
from google.cloud import translate_v2
import logging
import classes

app.app.config["modules"].append("translations")

###

translateClient = translate_v2.Client()


@app.app.route("/downloadLocalization", methods=["GET"])
def downloadLocalization():

    # Cheap access restriction to block random traffic
    if not g.form._get("authKey") == "8KW8jyBtEW3my2U":
        return abort(401)

    d = {"TranslatorName": {}}

    print("1")

    locales = []
    translationUsers = Translation_User.query().fetch(read_consistency=ndb.STRONG)
    for translationUser in translationUsers:
        locale = translationUser.key.parent().get(read_consistency=ndb.STRONG)
        if locale not in locales:
            locales.append(locale)

        # Translator Names
        name = translationUser.userKey.get(read_consistency=ndb.STRONG).name
        if name != "Type.World":
            if locale.ISO639_1 in d["TranslatorName"]:
                d["TranslatorName"][locale.ISO639_1] += ", " + name
            else:
                d["TranslatorName"][locale.ISO639_1] = name

    print("2")

    # 		locales = Language.query().order(Language.ISO639_1).fetch(read_consistency=ndb.STRONG)
    parameters = {
        "keywords": Translation_Keyword.query().fetch(read_consistency=ndb.STRONG),
        "translations": Translation_Translation.query()
        .order(-Translation_Translation.touched)
        .fetch(read_consistency=ndb.STRONG),
    }

    print("3")

    for keyword in parameters["keywords"]:

        d[keyword.keyword] = {}

        for locale in locales:
            translation = keyword.latestTranslationObject(locale.ISO639_1, parameters)
            if translation:
                d[keyword.keyword][locale.ISO639_1] = translation.translation

    print("4")

    return json.dumps(d), 200, {"Content-Type": "application/json; charset=utf-8"}


@app.app.route("/googleTranslate", methods=["GET", "POST"])
def googleTranslate():

    # print(g.form._get('targetLanguage'), g.form._get('keywordKey'))

    if not g.user and not g.form._get("targetLanguage") in [x.ISO639_1 for x in g.user.isTranslatorForLocales()]:
        return abort(401)

    keyword = ndb.Key(urlsafe=g.form._get("keywordKey").encode()).get(read_consistency=ndb.STRONG)
    source = keyword.currentTranslation("en").replace("\n", "<br />")
    results = translateClient.translate(source, source_language="en", target_language=g.form._get("targetLanguage"))

    # logging.warning('Sent: %s' % source)
    # logging.warning('Received: %s' % results['translatedText'])

    if "translatedText" in results:
        text = (
            results["translatedText"]
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("&lt;br /&gt;", "<br />")
            .replace("&lt;br&gt;", "<br />")
        )
        g.html.P()
        g.html.A(class_="button", onclick="copyGoogleTranslation();")
        g.html.T('<span class="material-icons-outlined">content_copy</span>Copy into text field above')
        g.html._A()
        g.html._P()

        g.html.CODE()
        g.html.INPUT(
            type="hidden",
            id="google_translation",
            name="google_translation",
            value=text,
        )
        g.html.T(text)
        g.html._CODE()

    return g.html.generate()


@app.app.route("/uploadTranslationKeywords", methods=["POST"])
def uploadTranslationKeywords():

    returns = []

    if not g.form._get("authorizationKey") != "ewfL2Crvj5u3DeQmCZVLkv3W":
        return abort(401)

    puts = []

    incomingKeywordList = g.form._get("keywords").split(",")
    oldKeywordObjects = Translation_Keyword.query().fetch(read_consistency=ndb.STRONG)
    oldKeywordList = [x.keyword for x in oldKeywordObjects]
    newKeywordObjects = []

    # Assemble list of new keywords
    newKeywordList = list(set(incomingKeywordList) - set(oldKeywordList))

    # returns.append('newKeywordList: %s' % newKeywordList)

    # if 'NoUserAccountLinked' in newKeywordList:
    # 	returns.append('NoUserAccountLinked in newKeywordList')

    # Store new keywords
    for keyword in newKeywordList:
        keywordObject = Translation_Keyword()
        keywordObject.keyword = keyword
        puts.append(keywordObject)
        newKeywordObjects.append(keywordObject)

    inactiveKeywordList = list(set(oldKeywordList) - set(incomingKeywordList))

    # Inactivate existing old keywords
    for keywordObject in oldKeywordObjects:
        if not keywordObject.base:
            if keywordObject.keyword in inactiveKeywordList:
                keywordObject.active = False
                puts.append(keywordObject)
            else:
                keywordObject.active = True
                puts.append(keywordObject)

    ndb.put_multi(puts)

    returns.append(f"New: {newKeywordList}")
    returns.append(f"Inactivated: {inactiveKeywordList}")

    return "\n".join(returns)


def translations_categories(parameters, directCallParameters):

    g.html.area("Categories")

    g.html.P()
    Translation_Category().new(text="+ Category")
    g.html._P()

    for category in Translation_Category.query().order(Translation_Category.name).fetch(read_consistency=ndb.STRONG):
        category.container("view")

    g.html._area()


def translations_uncategorized(parameters, directCallParameters):

    g.html.area("Uncategorized Keywords")

    Translation_Keyword().new(text="+ Keyword")

    for keyword in Translation_Keyword.query().order(Translation_Keyword.keyword).fetch(read_consistency=ndb.STRONG):
        if not keyword.categoryKey:
            keyword.view()

    g.html._area()


@app.app.route("/translations", methods=["GET", "POST"])
def translations():

    if not g.admin:
        return redirect("/")

    g.html.separator()

    g.html.DIV(class_="content")

    webapp.container("translations_uncategorized")
    webapp.container("translations_categories")

    g.html._DIV()

    return g.html.generate()


def translations_locales(parameters, directCallParameters):

    if not directCallParameters:
        directCallParameters = {"translators": Translation_User.query().fetch(read_consistency=ndb.STRONG)}

    g.html.area("Languages")

    g.html.P()
    Language().new(text="+ Locale")
    g.html._P()

    g.html.TABLE()

    g.html.TR()
    g.html.TH(style="width: 20%")
    g.html.T("Name")
    g.html._TH()
    g.html.TH(style="width: 10%")
    g.html.T("ISO 639-1")
    g.html._TH()
    g.html.TH(style="width: 20%")
    g.html.T("ISO 639-2/3")
    g.html._TH()
    g.html.TH(style="width: 10%")
    g.html.T("OpenType Tag")
    g.html._TH()
    g.html.TH(style="width: 30%")
    g.html.T("Translators")
    g.html._TH()
    g.html.TH(style="width: 10%")
    g.html._TH()
    g.html._TR()

    # class Language(WebAppModel):
    # 	ISO639_1 = StringProperty()
    # 	name = StringProperty(required = True)
    # 	opentypeTag = StringProperty()
    # 	ISO639_2_3 = StringProperty(repeated=True)

    for language in Language.query().order(Language.name).fetch(read_consistency=ndb.STRONG):

        g.html.TR()
        g.html.TD()
        g.html.T(language.name)
        g.html._TD()
        g.html.TD()
        if language.ISO639_1:
            g.html.T(language.ISO639_1)
        g.html._TD()
        g.html.TD()
        if language.ISO639_2_3:
            g.html.T(", ".join(language.ISO639_2_3))
        g.html._TD()
        g.html.TD()
        if language.opentypeTag:
            g.html.T(language.opentypeTag)
        g.html._TD()
        g.html.TD()
        if language.ISO639_1:
            Translation_User().new(
                text="+ Translator User",
                parentKey=language.key,
                propertyNames=["userKey", "publiclyCredited"],
            )
            users = language.users(directCallParameters)
            if users:
                g.html.DIV()
                for translationUser in users:
                    if translationUser:
                        user = translationUser.user()
                        if user:
                            g.html.T(translationUser.user().email)
                        translationUser.edit(text='<span class="material-icons-outlined">edit</span>')
                        translationUser.delete(text='<span class="material-icons-outlined">delete</span>')
                g.html._DIV()
        g.html._TD()
        g.html.TD()
        language.edit(text='<span class="material-icons-outlined">edit</span>')
        # 		language.delete()
        g.html._TD()
        g.html._TR()

    g.html._TABLE()

    g.html._area()


@app.app.route("/languages", methods=["GET", "POST"])
def languages():

    if not g.admin:
        return redirect("/")

    g.html.DIV(class_="content")

    webapp.container(
        "translations_locales",
        directCallParameters={"translators": Translation_User.query().fetch(read_consistency=ndb.STRONG)},
    )

    g.html._DIV()

    return g.html.generate()


def translate_keywords(keywords, locale, parameters, directCallParameters):
    g.html.TABLE()
    g.html.TR()
    # g.html.TH(style="width: 20%")
    # g.html.T('Keyword')
    # g.html._TH()
    g.html.TH(style="width: 40%")
    g.html.T("English Original")
    g.html._TH()
    g.html.TH(style="width: 40%")
    g.html.T("Translation")
    g.html._TH()
    # g.html.TH(style="width: 20%")
    # g.html.T('Description')
    # g.html._TH()
    g.html._TR()

    for keyword in keywords:
        if keyword.active and (
            ("showBaseKeywords" in parameters and parameters["showBaseKeywords"] and keyword.base) or not keyword.base
        ):

            originalTranslation = keyword.currentTranslation("en", directCallParameters)

            g.html.TR()
            # g.html.TD(style="font-size: 10pt; text-align: left;")
            # g.html.T(keyword.keyword)
            # if g.admin:
            #     keyword.edit(text='<span class="material-icons-outlined">edit</span>')
            # g.html._TD()
            g.html.TD(style="text-align: left;")

            g.html.DIV()
            g.html.SPAN(style="font-size: 10pt; text-align: left;")
            g.html.T(keyword.keyword)
            if g.admin:
                keyword.edit(text='<span class="material-icons-outlined">edit</span>')
            g.html._SPAN()
            g.html._DIV()

            g.html.DIV(
                style="padding: 8px; background-color: white;"
            )  # style=f"padding: 10px; background-color: #ddd;"
            g.html.T(originalTranslation.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br />"))
            g.html._DIV()
            if g.admin and locale != "en":
                Translation_Translation().new(
                    text='<span class="material-icons-outlined">edit</span>',
                    propertyNames=["translation"],
                    values={"locale": "en", "keywordKey": keyword.publicID()},
                    hiddenValues={
                        "userKey": g.user.publicID(),
                        "locale": "en",
                        "keywordKey": keyword.publicID(),
                    },
                )

            if keyword.description:
                g.html.DIV()
                g.html.SPAN(style="font-size: 10pt; line-height: 10px; text-align: left;")
                g.html.T("<b>Note:</b>")
                g.html.BR()
                g.html.T(keyword.description)
                g.html._SPAN()
                g.html._DIV()

            g.html._TD()
            g.html.TD(style="text-align: left;")
            keyword.container("translationView", parameters, directCallParameters)
            g.html._TD()
            # g.html.TD(style="font-size: 10pt; text-align: left;")
            # g.html.T(keyword.description or '')
            # g.html._TD()
            g.html._TR()
    g.html._TABLE()


def translate_normal(parameters, directCallParameters):

    g.html.DIV(class_="autotoc category", title="Basic Translations")
    g.html.area("Basic Translations")

    g.html.P()
    g.html.T(
        "The keywords hereunder need to be translated first. Future plan (currently not yet implemented): They form"
        " the basis of the automatic Google Translate translations that will be shown to you as suggestions for yet"
        " untranslated content."
    )
    g.html._P()
    g.html.P()
    g.html.T(
        "Please pay utmost attention to these basic translations. They are words that could be automatically"
        " translated into very unwanted words in different languages when out of context. These basics create the"
        " necessary context."
    )
    g.html._P()
    g.html.mediumSeparator()

    if not directCallParameters:
        directCallParameters = getTranslationEntities(parameters["locale"])

    if not hasattr(g, "translateLocale"):
        g.translateLocale = Language.query(Language.ISO639_1 == parameters["locale"]).get(read_consistency=ndb.STRONG)

    keywords = [x for x in directCallParameters["keywords"] if x.base]

    parameters["showBaseKeywords"] = True
    translate_keywords(keywords, parameters["locale"], parameters, directCallParameters)

    g.html._area()
    g.html._DIV()  # .autotoc category

    if True:
        # if g.translateLocale.baseKeywordsCompleted(g.translateLocale.ISO639_1, directCallParameters):

        # reload()

        g.html.DIV(class_="autotoc category", title="Uncategorized Keywords")
        g.html.area("Uncategorized Keywords")
        keywords = [x for x in directCallParameters["keywords"] if not x.categoryKey]
        parameters["showBaseKeywords"] = False
        if keywords:
            translate_keywords(keywords, g.translateLocale.ISO639_1, parameters, directCallParameters)
        g.html._area()
        g.html._DIV()  # .autotoc category

        for category in directCallParameters["categories"]:
            g.html.DIV(class_="autotoc category", title=category.name)
            g.html.area(category.name)
            keywords = [x for x in directCallParameters["keywords"] if x.categoryKey == category.key]
            parameters["showBaseKeywords"] = False
            if keywords:
                translate_keywords(
                    keywords,
                    g.translateLocale.ISO639_1,
                    parameters,
                    directCallParameters,
                )

            for subCategory in [x for x in directCallParameters["subCategories"] if x.key.parent() == category.key]:

                g.html.DIV(class_="autotoc subcategory", title=subCategory.name)
                g.html.area(subCategory.name)
                keywords = [x for x in directCallParameters["keywords"] if x.categoryKey == subCategory.key]
                parameters["showBaseKeywords"] = False
                if keywords:
                    translate_keywords(
                        keywords,
                        g.translateLocale.ISO639_1,
                        parameters,
                        directCallParameters,
                    )
                g.html._area()
                g.html._DIV()  # .autotoc subcategory

            g.html._area()
            g.html._DIV()  # .autotoc category


def getTranslationEntities(locale):
    return {
        "keywords": Translation_Keyword.query().order(Translation_Keyword.keyword).fetch(read_consistency=ndb.STRONG),
        "categories": Translation_Category.query().order(Translation_Category.name).fetch(read_consistency=ndb.STRONG),
        "subCategories": Translation_SubCategory.query()
        .order(Translation_SubCategory.name)
        .fetch(read_consistency=ndb.STRONG),
        "translations": Translation_Translation.query(Translation_Translation.locale == locale)
        .order(-Translation_Translation.touched)
        .fetch(read_consistency=ndb.STRONG),
        "originalTranslations": Translation_Translation.query(Translation_Translation.locale == "en")
        .order(-Translation_Translation.touched)
        .fetch(read_consistency=ndb.STRONG),
    }


@app.app.route("/translationemail", methods=["GET", "POST"])
def translationEmail():

    emails = []

    for translationUser in Translation_User.query().fetch(read_consistency=ndb.STRONG):
        language = translationUser.key.parent().get(read_consistency=ndb.STRONG)
        user = translationUser.user()

        changed = 0
        missing = 0
        keywords = getTranslationEntities(language.ISO639_1)
        for keyword in keywords["keywords"]:

            if keyword.active:

                # originalTranslation = keyword.currentTranslation("en", keywords)
                originalTranslationObject = keyword.latestTranslationObject("en", keywords)
                latestTranslationObject = keyword.latestTranslationObject(language.ISO639_1, keywords)

                if latestTranslationObject:
                    outdated = None
                    if latestTranslationObject and originalTranslationObject:
                        if originalTranslationObject.touched > latestTranslationObject.touched:
                            outdated = True
                    if outdated:
                        changed += 1
                else:
                    missing += 1

        if changed or missing:
            emails.append(
                (
                    user.email,
                    f"Type.World: Translations needed for {language.name}",
                    f"""Dear {user.name},

you are receiving this email because you are registered as a translator for {language.name} with Type.World.

We are currently working on an upcoming release and would like to ask you
to improve our {language.name} translations within the coming week.
There are currently {changed} outdated and {missing} missing translations for you to review.

Please open https://type.world in your browser, log in, and review the translations
at https://type.world/translate (link will appear in title bar after login).
""",
                )
            )

    for email, subject, body in emails:
        g.html.P()
        g.html.T(email)
        g.html.BR()
        g.html.T(subject)
        g.html.BR()
        g.html.T(body)
        g.html._P()

    return g.html.generate()


@app.app.route("/translate", methods=["GET", "POST"])
@app.app.route("/translate/<locale>", methods=["GET", "POST"])
def translate(locale=None):

    # User is translator at all
    if not g.user or not g.user.isTranslator():
        return abort(401)

    # User is not set to edit this language
    localesForUser = g.user.isTranslatorForLocales()
    if locale and locale not in [x.key.parent().get(read_consistency=ndb.STRONG).ISO639_1 for x in localesForUser]:
        return abort(401)

    g.html.DIV(class_="content", style="width: 1200px;")

    #     g.html.SCRIPT()
    #     g.html.T("""
    # $( document ).ready(function() {{
    #     resize();
    # }});
    # """)
    #     g.html._SCRIPT()

    g.html.DIV(class_="tocwrapper stickToTheTop")
    g.html.DIV(id="autotoc", class_="toc")
    g.html._DIV()
    g.html._DIV()

    g.html.DIV(class_="doc")

    if len(localesForUser) > 1:

        g.html.area()
        g.html.P()
        g.html.T("You are listed to translate the following languages:")
        g.html._P()
        for u in localesForUser:
            language = u.key.parent().get(read_consistency=ndb.STRONG)
            g.html.P(style="font-weight: %s" % ("bold" if language.ISO639_1 == locale else "inherit"))
            g.html.A(href=f"/translate/{language.ISO639_1}")
            g.html.T(language.name)
            g.html._A()
            g.html._P()
        g.html._area()

    g.html.DIV(class_="autotoc category", title="Instructions")
    g.html.area("Instructions")

    g.html.UL()

    g.html.LI()
    g.html.T(
        "Keep the language <b>informal</b>. If your language offers both <em>formal</em> and <em>informal</em>"
        " addressing of a person (like <em>Du</em> and <em>Sie</em> in German), always choose the informal. Keep this"
        " in mind when using the translation suggestions by Google, as they may be held in formal language."
    )
    g.html._LI()

    g.html.LI()
    g.html.T(
        "<b>Decolonize</b> your language. We are not here to please the sensitivities of former or current colonizers."
        " If you are from a colonized place, please find a language style that is a middle ground for all speakers of"
        " that language worldwide (including original speakers) to agree on."
    )
    g.html._LI()

    g.html.LI()
    g.html.T(
        '<span style="background-color: red;">Red background</span> means a missing translation. Translate only if the'
        " original English makes any sense. If the English shows a cryptical keyword such as"
        " <b>response.appInstanceRevoked</b>, postpone this translation until the English has been properly filled."
    )
    g.html._LI()

    g.html.LI()
    g.html.T(
        '<span style="background-color: orange;">Orange background</span> means that the original English <em>may have'
        " </em> changed since you last edited your translation. This requires a review."
    )
    g.html._LI()

    g.html.LI()
    g.html.T(
        "The translation widget offers to have Google auto-translate from the English. A second click is required to"
        " copy the text into the text field. <b>Always review the translations carefully.</b>"
    )
    g.html._LI()
    g.html.LI()
    g.html.T(
        "Google Translate is known to mess up <b>HTML code</b> and <b>punctuation</b> in the responses. Malformed HTML"
        " and string replacement notations are checked upon saving, but you need to edit them back into shape yourself"
        " before saving regarding whitespace and order. This can’t be automated."
    )
    g.html._LI()

    g.html.LI()
    g.html.T(
        "All HTML code must use single quotes instead of double quotes for attributes, so <code>&lt;a"
        " href=''&gt;</code> instead of the commonly used <code>&lt;a href=\"\"&gt;</code>."
    )
    g.html._LI()

    g.html._UL()

    g.html._area()
    g.html._DIV()  # .autotoc category

    if locale:

        g.translateLocale = Language.query(Language.ISO639_1 == locale).get(read_consistency=ndb.STRONG)

        g.html.H2()
        g.html.T(f"Translation for <b>{g.translateLocale.name}</b>")
        g.html._H2()

        g.translateLocale = Language.query(Language.ISO639_1 == locale).get(read_consistency=ndb.STRONG)

        entities = getTranslationEntities(locale)

        webapp.container("translate_normal", {"locale": locale}, entities)

    g.html._DIV()  # .doc
    g.html._DIV()  # .content

    return g.html.generate()


class Translation_Category(webapp.WebAppModel):
    name = webapp.StringProperty(required=True)

    def view(self, parameters={}, directCallParameters={}):

        g.html.DIV(class_="autotoc category", title=self.name)
        g.html.area(self.name, class_="scheme2")

        g.html.DIV()
        self.edit(text='<span class="material-icons-outlined">edit</span>')
        self.delete(text='<span class="material-icons-outlined">delete</span>')
        g.html._DIV()

        g.html.DIV()
        Translation_Keyword().new(text="+ Keyword", values={"categoryKey": self.publicID()})
        g.html._DIV()
        for keyword in self.keywords():
            keyword.view()

        g.html.DIV()
        Translation_SubCategory().new(text="+ Sub Category", parentKey=self.key)
        g.html._DIV()
        for subCategory in self.subCategories():
            subCategory.view()
        # g.html.separator()

        g.html._area()
        g.html._DIV()  # .autotoc category

    def keywords(self):
        return (
            Translation_Keyword.query(ndb.GenericProperty("categoryKey") == self.key)
            .order(Translation_Keyword.keyword)
            .fetch(read_consistency=ndb.STRONG)
        )

    def subCategories(self):
        return (
            Translation_SubCategory.query(ancestor=self.key)
            .order(Translation_SubCategory.name)
            .fetch(read_consistency=ndb.STRONG)
        )


class Translation_SubCategory(webapp.WebAppModel):
    name = webapp.StringProperty(required=True, indexed=True)

    def view(self, parameters={}, directCallParameters={}):

        g.html.DIV(class_="autotoc subcategory", title=self.name)
        g.html.area(self.name, class_="scheme3")

        g.html.DIV()
        self.edit(text='<span class="material-icons-outlined">edit</span>')
        self.delete(text='<span class="material-icons-outlined">delete</span>')
        g.html._DIV()

        # g.html.DIV()
        # g.html.H5()
        # g.html.T(self.name)
        # self.edit(text='<span class="material-icons-outlined">edit</span>')
        # self.delete(text='<span class="material-icons-outlined">delete</span>')
        # g.html._H5()
        # g.html._DIV()
        g.html.DIV()
        Translation_Keyword().new(text="+ Keyword", values={"categoryKey": self.publicID()})
        g.html._DIV()

        for keyword in self.keywords():
            keyword.view()

        g.html._area()
        g.html._DIV()  # .autotoc subcategory

    def keywords(self):
        return (
            Translation_Keyword.query(ndb.GenericProperty("categoryKey") == self.key)
            .order(Translation_Keyword.keyword)
            .fetch(read_consistency=ndb.STRONG)
        )


class Language(webapp.WebAppModel):
    ISO639_1 = webapp.StringProperty()
    name = webapp.StringProperty(required=True)
    opentypeTag = webapp.StringProperty()
    ISO639_2_3 = webapp.StringProperty(repeated=True)

    def users(self, directCallParameters):

        if "translators" in directCallParameters:
            return [x for x in directCallParameters["translators"] if x.key.parent() == self.key]
        else:
            return Translation_User.query(ancestor=self.key).fetch(read_consistency=ndb.STRONG)

    def baseKeywords(self, directCallParameters={}):
        if "keywords" in directCallParameters:
            return [x for x in directCallParameters["keywords"] if x.base is True]
        else:
            return (
                Translation_Keyword.query(Translation_Keyword.base is True)
                .order(Translation_Keyword.keyword)
                .fetch(read_consistency=ndb.STRONG)
            )

    def baseKeywordsCompleted(self, locale, directCallParameters={}):
        completed = True
        for keyword in self.baseKeywords(directCallParameters):
            completed = completed and keyword.latestTranslation(locale, directCallParameters) is not None
        return completed


class CategoryKeyProperty(webapp.KeyProperty):
    def dialog(self, key, value, placeholder=None):

        g.html.DIV(style="display: block;")

        g.html.SELECT(name=key, id=key, onchange="deRequiredMissing($(this));")
        g.html.OPTION(value=webapp.EMPTY, selected=value is None)
        g.html.T("&lt;undefined&gt;")
        g.html._OPTION()

        for category in (
            Translation_Category.query().order(Translation_Category.name).fetch(read_consistency=ndb.STRONG)
        ):
            g.html.OPTION(value=category.publicID(), selected=value == category.key)
            g.html.T(category.name)
            g.html._OPTION()

            for subCategory in category.subCategories():
                g.html.OPTION(value=subCategory.publicID(), selected=value == subCategory.key)
                g.html.T("—" + subCategory.name)
                g.html._OPTION()
        g.html._SELECT()

        g.html._DIV()


class Translation_Keyword(webapp.WebAppModel):
    keyword = webapp.StringProperty(required=True)
    active = webapp.BooleanProperty(default=True)
    base = webapp.BooleanProperty(default=False)
    categoryKey = CategoryKeyProperty()
    description = webapp.TextProperty()

    def viewPermission(self, methodName):
        if methodName in ["translationView"]:
            return True

        return False

    def mainCategoryKey(self):
        if self.categoryKey:
            if self.categoryKey.parent():
                return self.categoryKey.parent()
            else:
                return self.categoryKey

    def translationView(self, parameters={}, directCallParameters={}):

        originalTranslationObject = self.latestTranslationObject("en", directCallParameters)
        latestTranslationObject = self.latestTranslationObject(parameters["locale"], directCallParameters)
        outdated = None
        if latestTranslationObject and originalTranslationObject:
            if originalTranslationObject.touched > latestTranslationObject.touched:
                outdated = True
        if latestTranslationObject:

            g.html.DIV(style=f"padding: 8px; background-color: {'orange' if outdated else 'white'};")  # padding: 10px;
            g.html.T(
                latestTranslationObject.translation.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br />")
            )
            g.html._DIV()
            latestTranslationObject.edit(
                propertyNames=["translation"],
                hiddenValues={
                    "userKey": g.user.publicID(),
                    "locale": parameters["locale"],
                    "keywordKey": self.publicID(),
                },
            )
        else:
            g.html.DIV(style="padding: 8px; background-color: red;")  # padding: 10px;
            g.html.T("—")
            g.html._DIV()
            Translation_Translation().new(
                text='<span class="material-icons-outlined">edit</span>',
                propertyNames=["translation"],
                values={"locale": parameters["locale"], "keywordKey": self.publicID()},
                hiddenValues={
                    "userKey": g.user.publicID(),
                    "locale": parameters["locale"],
                    "keywordKey": self.publicID(),
                },
            )

    def view(self, parameters={}, directCallParameters={}):
        g.html.DIV()
        if self.base:
            g.html.SPAN(style="color: red; font-weight: bold;")
        if not self.active:
            g.html.SPAN(style="opacity: 0.4; text-decoration: line-through;")
        g.html.T(self.keyword)
        if self.base or not self.active:
            g.html._SPAN()
        self.edit(text='<span class="material-icons-outlined">edit</span>')
        self.delete(text='<span class="material-icons-outlined">delete</span>')
        g.html._DIV()

    def currentTranslation(self, locale="en", directCallParameters={}):
        latestTranslationObject = self.latestTranslationObject(locale, directCallParameters)
        if latestTranslationObject:
            return latestTranslationObject.translation
        latestTranslationObject = self.latestTranslationObject("en", directCallParameters)
        if latestTranslationObject:
            return latestTranslationObject.translation
        else:
            return self.keyword

    def latestTranslationObject(self, locale, directCallParameters={}):

        if "translations" in directCallParameters:
            translations = [
                x for x in directCallParameters["translations"] if x.keywordKey == self.key and x.locale == locale
            ]
            if translations:
                return translations[0]
        if "originalTranslations" in directCallParameters:
            translations = [
                x
                for x in directCallParameters["originalTranslations"]
                if x.keywordKey == self.key and x.locale == locale
            ]
            if translations:
                return translations[0]
        else:
            return (
                Translation_Translation.query(
                    Translation_Translation.locale == locale,
                    Translation_Translation.keywordKey == self.key,
                )
                .order(-Translation_Translation.touched)
                .get(read_consistency=ndb.STRONG)
            )

    def latestTranslation(self, locale, directCallParameters={}):

        latestTranslationObject = self.latestTranslationObject(locale, directCallParameters)
        if latestTranslationObject:
            return latestTranslationObject.translation

    def reloadDataContainer(self, view, parameters):

        logging.warning("Translation_Keyword.reloadDataContainer(%s, %s)" % (view, parameters))

        keyID, methodName, parameters = webapp.decodeDataContainer(view)

        if methodName == "view":

            mainCategoryKey = self.mainCategoryKey()
            if mainCategoryKey:
                return webapp.encodeDataContainer(mainCategoryKey.urlsafe().decode(), "view", parameters)
            else:
                return webapp.encodeDataContainer(None, "translations_uncategorized", parameters)

        if methodName == "translateView" and self.base:
            return webapp.encodeDataContainer(None, "translate_normal", parameters)


class Translation_User(webapp.WebAppModel):
    # parent = language
    userKey = webapp.UserKeyProperty(required=True)
    publiclyCredited = webapp.BooleanProperty()

    def user(self):
        if self.userKey:
            return self.userKey.get(read_consistency=ndb.STRONG)


def User_IsTranslator(self):
    if g.user:
        if Translation_User.query(Translation_User.userKey == self.key).fetch(read_consistency=ndb.STRONG):
            return True

    return False


classes.User.isTranslator = User_IsTranslator


def User_IsTranslatorForLocales(self):
    return Translation_User.query(Translation_User.userKey == self.key).fetch(read_consistency=ndb.STRONG)


classes.User.isTranslatorForLocales = User_IsTranslatorForLocales


class TranslationProperty(webapp.TextProperty):
    def dialog(self, key, value, placeholder=None):
        g.html.textInput(key, value=value, type="textarea", placeholder=placeholder)

        g.html.P()
        g.html.T("Translation by Google:")
        g.html._P()
        ID = "googleTranslate_%s" % key
        g.html.P(id=ID)
        g.html.A(
            class_="button",
            onclick=(
                "$('#%s').html(''); AJAX('#%s', '/googleTranslate', {'inline': 'true', 'targetLanguage':"
                " $('#dialogform_locale').val(), 'keywordKey': $('#dialogform_keywordKey').val()});"
            )
            % (ID, ID),
        )
        g.html.T('<span class="material-icons-outlined">translate</span> Pull Google Translation')
        g.html._A()
        g.html._P()

        keyword = ndb.Key(urlsafe=g.form._get("keywordKey").encode()).get(read_consistency=ndb.STRONG)
        g.html.P()
        g.html.T("Original English:")
        g.html.BR()
        g.html.CODE()
        g.html.T(keyword.currentTranslation("en").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br />"))
        g.html._CODE()
        g.html._P()


class Translation_Translation(webapp.WebAppModel):
    keywordKey = webapp.KeyProperty(required=True)
    userKey = webapp.KeyProperty(required=True)
    translation = TranslationProperty(required=True)
    locale = webapp.StringProperty(required=True)

    defaultValues = {"translation": "latestTranslation()"}

    def editPermission(self, propertyNames):
        # print(propertyNames)
        if "translation" in propertyNames:
            languagesForUser = Translation_User.query(Translation_User.userKey == g.user.key).fetch(
                read_consistency=ndb.STRONG
            )
            if languagesForUser:
                return True
            # print(self.locale)
            # for languageForUser in languagesForUser:
            #     language = languageForUser.key.parent().get(read_consistency=ndb.STRONG)
            #     # print(language, self.locale)
            #     if language and language.ISO639_1 == self.locale:
            #         return True
        return False

    def latestTranslationObject(self):
        return (
            Translation_Translation.query(
                Translation_Translation.locale == self.locale,
                Translation_Translation.keywordKey == self.keywordKey,
            )
            .order(-Translation_Translation.touched)
            .get(read_consistency=ndb.STRONG)
        )

    def latestTranslation(self):
        latestTranslationObject = self.latestTranslationObject()
        if latestTranslationObject:
            return latestTranslationObject.translation

    def reloadDataContainer(self, view, parameters):

        logging.warning("Translation_Translation.reloadDataContainer(%s, %s)" % (view, parameters))

        keyword = self.keywordKey.get(read_consistency=ndb.STRONG)

        keyID, methodName, parameters = webapp.decodeDataContainer(view)

        if methodName == "translateView" and keyword.base:
            return webapp.encodeDataContainer(None, "translate_normal", {"locale": parameters["locale"]})

    def canSave(self):

        keyword = self.keywordKey.get(read_consistency=ndb.STRONG)
        english = keyword.currentTranslation("en")

        if self.locale != "en":

            # variables
            originalSet = re.findall(r"%(.+?)%", english)
            newSet = re.findall(r"%(.+?)%", self.translation)
            if not set(originalSet) == set(newSet) or len(originalSet) != len(newSet):
                return (
                    False,
                    "The variables (%xyz%) of the translation don’t match with the original.",
                )

            # HTML
            originalSet = re.findall(r"(<.+?>)", english)
            newSet = re.findall(r"(<.+?>)", self.translation)
            if not set(originalSet) == set(newSet) or len(originalSet) != len(newSet):
                return (
                    False,
                    "The HTML tags of the translation don’t match with the original.",
                )

            # New lines
            originalSet = re.findall(r"(\n)", english)
            newSet = re.findall(r"(\n)", self.translation)
            if not set(originalSet) == set(newSet) or len(originalSet) != len(newSet):
                return (
                    False,
                    "The text formatting (line breaks) of the translation don’t match with the original.",
                )

        return True, None
