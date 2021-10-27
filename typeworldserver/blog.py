# project
import typeworldserver
from typeworldserver import web
from typeworldserver import helpers

# other
import markdown2
from flask import g

typeworldserver.app.config["modules"].append("blog")


@typeworldserver.app.route("/blog", methods=["GET", "POST"])
@typeworldserver.app.route("/blog/<blogEntryURL>", methods=["GET", "POST"])
def blog(blogEntryURL=None):

    g.html.DIV(class_="content", style="width: 1000px;")

    if g.admin:
        g.html.P()
        BlogEntry().new()
        g.html._P()

    # Find post
    blogEntry = BlogEntry.query(BlogEntry.url == blogEntryURL).get()
    if blogEntry:

        blogEntry.container("view", directCallParameters={"view": "long"})

    # All posts
    else:
        for blogEntry in BlogEntry.query().order(-BlogEntry.touched).fetch():
            if blogEntry.live or g.admin:
                blogEntry.container("view", directCallParameters={"view": "short"})

    g.html._DIV()

    return g.html.generate()


class BlogEntry(web.WebAppModel):
    title = web.StringProperty(required=True, verbose_name="Title")
    url = web.StringProperty(required=True, verbose_name="URL")
    content = web.TextProperty(required=True, verbose_name="Content (Markdown, HTML allowed), use --break--")
    live = web.BooleanProperty(verbose_name="Live")

    def beforePut(self):
        # Set new date when put live
        if "live" in self._changed and self.live and self._contentCache["live"] is False:
            self.created = helpers.now()
            self._changed.append("created")

    def view(self, parameters={}, directCallParameters={}):

        g.html.DIV(class_="blogentry")

        g.html.P(class_="date")
        g.html.T(self.created.strftime("%A %d %B %Y"))
        g.html._P()

        view = "long"
        if "view" in directCallParameters:
            view = directCallParameters["view"]

        if view == "long":
            g.html.P()
            g.html.A(href="/blog")
            g.html.T('<span class="material-icons-outlined">arrow_back</span> Back to Blog')
            g.html._A()
            g.html._P()

        g.html.H1(class_="title")
        g.html.T(self.title)
        if view != "long":
            g.html.SPAN()
            g.html.A(
                class_="permalink",
                href=f"/blog/{self.url}",
                title="Perma-Link to This Article",
                style="color: inherit; position: relative; top: -10px; margin-left: 20px;",
            )
            g.html.T('<span class="material-icons-outlined">link</span>')
            g.html._A()
            g.html._SPAN()
        g.html._H1()

        # g.html.P()

        # g.html.P()

        if g.admin:
            g.html.P()
            self.edit()
            g.html._P()

        if view == "long":
            content = self.content.replace("--break--", "")
        elif view == "short":
            content = self.content.split("--break--")[0]
        g.html.T(markdown2.markdown(content))

        if view == "short" and "--break--" in self.content:
            g.html.P()
            g.html.A(href=f"/blog/{self.url}")
            g.html.T('<span class="material-icons-outlined">menu_book</span> Read Full Article')
            g.html._A()
            g.html._P()

        g.html._DIV()  # .blogentry
