"Information page endpoints."

import couchdb2
import flask
import jinja2
import marko
import xlsxwriter

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
        url = flask.url_for(".text_edit", docid=doc['_id'])
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
        url = flask.url_for(".text_edit", docid=doc['_id'])
    else:
        url = None
    return flask.render_template("about/text.html", doc=doc, url=url)


@blueprint.route("/text_edit/<docid>", methods=["GET", "POST"])
@utils.admin_required
def text_edit(docid):
    "Edit the text."
    doc = flask.g.db[docid]
    if utils.http_GET():
        return flask.render_template("about/text_edit.html",
                                     doc=doc,
                                     url=flask.url_for(f".{docid}"))
    elif utils.http_POST():
        with utils.MetaSaver(doc=doc) as saver:
            saver["text"] = flask.request.form.get("text") or None
        return flask.redirect(flask.url_for(f".{docid}"))


@blueprint.route("/software")
def software():
    "Show the current software versions."
    software = [
        ("Anubis", constants.VERSION, constants.URL),
        ("Python", constants.PYTHON_VERSION, constants.PYTHON_URL),
        ("Flask", flask.__version__, constants.FLASK_URL),
        ("Jinja2", jinja2.__version__, constants.JINJA2_URL),
        ("CouchDB server", flask.g.db.server.version, constants.COUCHDB_URL),
        ("CouchDB2 interface", couchdb2.__version__, constants.COUCHDB2_URL),
        ("XslxWriter", xlsxwriter.__version__, constants.XLSXWRITER_URL),
        ("Marko", marko.__version__, constants.MARKO_URL),
        ("Bootstrap", constants.BOOTSTRAP_VERSION, constants.BOOTSTRAP_URL),
        ("jQuery", constants.JQUERY_VERSION, constants.JQUERY_URL),
        (
            "jQuery.localtime",
            constants.JQUERY_LOCALTIME_VERSION,
            constants.JQUERY_LOCALTIME_URL,
        ),
        ("DataTables", constants.DATATABLES_VERSION, constants.DATATABLES_URL),
        ("clipboard.js", constants.CLIPBOARD_VERSION, constants.CLIPBOARD_URL),
        ("Feather of Ma'at icon", constants.MAAT_VERSION, constants.MAAT_URL),
    ]
    return flask.render_template("about/software.html", software=software)
