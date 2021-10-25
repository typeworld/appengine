# project
import main
import webapp

# other
import markdown2
from flask import g

main.app.config["modules"].append("blog")


@main.app.route("/blog", methods=["GET", "POST"])
@main.app.route("/blog/<blogEntryURL>", methods=["GET", "POST"])
def blog(blogEntryURL=None):

    g.html.DIV(class_="content", style="width: 800px;")

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
            blogEntry.container("view", directCallParameters={"view": "short"})

    g.html._DIV()

    return g.html.generate()


class BlogEntry(webapp.WebAppModel):
    title = webapp.StringProperty(required=True, verbose_name="Title")
    url = webapp.StringProperty(required=True, verbose_name="URL")
    content = webapp.TextProperty(
        required=True, verbose_name="Content (Markdown, HTML allowed), use --break--"
    )
    live = webapp.BooleanProperty(verbose_name="Live")

    def view(self, parameters={}, directCallParameters={}):

        view = "long"
        if "view" in directCallParameters:
            view = directCallParameters["view"]

        if view == "long":
            g.html.P()
            g.html.A(href="/blog")
            g.html.T(
                '<span class="material-icons-outlined">arrow_back</span> Back to Blog'
            )
            g.html._A()
            g.html._P()

        g.html.H1()
        g.html.T(self.title)
        if view != "long":
            g.html.SPAN()
            g.html.A(
                class_="permalink",
                href=f"/blog/{self.url}",
                title="Perma-Link to This Article",
                style=(
                    "color: inherit; position: relative; top: -10px; margin-left: 20px;"
                ),
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
            g.html.T(
                '<span class="material-icons-outlined">menu_book</span> Read Full'
                " Article"
            )
            g.html._A()
            g.html._P()
