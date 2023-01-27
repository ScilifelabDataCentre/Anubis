"Information page endpoints."

import couchdb2
import flask

import anubis.database
from anubis import constants
from anubis import utils


blueprint = flask.Blueprint("about", __name__)


@blueprint.route("/contact")
def contact():
    "Display the contact information page."
    try:
        doc = flask.g.db["contact"]
    except couchdb2.NotFoundError:
        doc = {"_id": "contact"}
    if flask.g.am_admin:
        url = flask.url_for("about.text_edit", docid=doc["_id"])
    else:
        url = None
    return flask.render_template("about/text.html", doc=doc, url=url)


@blueprint.route("/data_policy")
def data_policy():
    "Display the data policy page."
    try:
        doc = flask.g.db["data_policy"]
    except couchdb2.NotFoundError:
        doc = {"_id": "data_policy"}
    if flask.g.am_admin:
        url = flask.url_for("about.text_edit", docid=doc["_id"])
    else:
        url = None
    return flask.render_template("about/text.html", doc=doc, url=url)


@blueprint.route("/text_edit/<docid>", methods=["GET", "POST"])
@utils.admin_required
def text_edit(docid):
    "Edit the text."
    doc = flask.g.db[docid]
    if utils.http_GET():
        return flask.render_template(
            "about/text_edit.html", doc=doc, url=flask.url_for(f".{docid}")
        )
    elif utils.http_POST():
        with anubis.database.MetaSaver(doc=doc) as saver:
            saver["text"] = flask.request.form.get("text") or None
        return flask.redirect(flask.url_for(f".{docid}"))


@blueprint.route("/software")
def software():
    "Show the current software versions."
    return flask.render_template("about/software.html", software=utils.get_software())
