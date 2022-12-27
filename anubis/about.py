"Information page endpoints."

import os.path

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
    return flask.render_template(
        "about/contact.html", text=utils.get_site_text("contact.md")
    )


@blueprint.route("/gdpr")
def gdpr():
    "Display the personal data policy page."
    return flask.render_template("about/gdpr.html", text=utils.get_site_text("gdpr.md"))


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


@blueprint.route("/settings")
@utils.login_required
def settings():
    "Display all configuration settings."
    if not (flask.g.am_admin or flask.g.am_staff):
        return utils.error(
            "You are not allowed to view configuration settings.", flask.url_for("home")
        )
    config = flask.current_app.config.copy()
    config["ROOT"] = constants.ROOT
    for key in ["SECRET_KEY", "COUCHDB_PASSWORD", "MAIL_PASSWORD"]:
        if config[key]:
            config[key] = "<hidden>"
    return flask.render_template("about/settings.html", items=sorted(config.items()))
